# -*- coding: utf-8 -*-
"""
Created on Thu Aug 8 15:11:27 2024

@author: chuyao and paul 
"""
import sys
import os
current_dir = os.getcwd()
file_dir = os.path.dirname(__file__)

import maskLib
from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
import math
import sys, subprocess, os, time
import numpy as np
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.entities import Polyline
import ezdxf
import datetime

from pya import Layout
import gdspy
import cv2
from matplotlib import pyplot as plt

import maskLib.MaskLib as m
import maskLib.microwaveLib as mw
from maskLib.utilities import curveAB
from maskLib.markerLib import AlphaNumStr

from maskLib.markerLib import MarkerSquare, MarkerCross
from maskLib.utilities import doMirrored

def est_exposure_time(exposed_area, avg_dose, beam_current=5):
    """
    Estimate exposure time in minutes given the exposed area, average dose, and beam current.

    Args:
        exposed_area (float): area to be exposed in um^2
        avg_dose (float): average dose in uC/cm^2
        beam_current (float): beam current in nA, typically 5 nA
    """
    total_charge = avg_dose * exposed_area / (1e4)**2 # uC

    exposure_time = total_charge / (beam_current * 1e-3) / 60 # min

    return exposure_time

def round_sf(value, n):
    """
    Round a value to n significant figures
    
    Args:
        value (float): value to round
        n (int): number of significant figures
    """
    try:
        rounded_val = round(value, -int(np.floor(np.log10(abs(value)))) + (n - 1))
        # if rounded_val has >= n digits to the left of the decimal point, return int
        if len(str(rounded_val).split('.')[0]) >= n:
            rounded_val = int(rounded_val)
        return rounded_val
    except:
        return value


def grid_from_row(row, no_row):
    return [row for _ in range(no_row)]

def grid_from_column(column, no_column, no_row):
    return [[column[i] for _ in range(no_column)] for i in range(no_row)]

def grid_from_entry(entry, no_row, no_column):
    return [entry * np.ones(no_column) for _ in range(no_row)]

def junction_chain(chip, structure, n_junc_array=None, w=None, s=None, gap=None,
                   bgcolor=None, CW=True, finalpiece=True, Jlayer=None,
                   Ulayer=None, **kwargs):
    def struct():
        if isinstance(structure, m.Structure):
            return structure
        elif isinstance(structure, tuple):
            return m.Structure(chip, structure)
        else:
            return chip.structure(structure)

    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ', chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ', chip.chipID)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()

    struct().translatePos((0, -s/2))

    # undercut amount = 0.3 approximate
    UNDERCUT = 0.3

    for count, n in enumerate(n_junc_array):
        undercut = struct().clone()
        # undercut on outside of JJ array
        undercut.translatePos((0, s/2), angle=0)

        mw.CPW_straight(chip, undercut, w = s, s = UNDERCUT, length = n*gap + (n-1)*w, 
                        layer = Ulayer, rotation = struct().direction)

        chip.add(dxf.rectangle(struct().getPos((0, 0)), gap, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Ulayer),
                                   structure=structure, length= gap)
        for i in range(n-1):
            chip.add(dxf.rectangle(struct().getPos((0, 0)), w, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Jlayer),
                                   structure=structure, length= w)

            chip.add(dxf.rectangle(struct().getPos((0, 0)), gap, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Ulayer),
                                   structure=structure, length= gap)
        if len(n_junc_array) >= 1:

            if CW:
                if count % 2 == 0:
                    factor = -2
                    direction = -1
                else:
                    factor = 0
                    direction = 3
            else:
                if count % 2 == 0:
                    factor = 0
                    direction = 3
                else:
                    factor = -2
                    direction = -1

            if count + 1 < len(n_junc_array):
                chip.add(dxf.rectangle(struct().getPos((0, factor*s)), w + gap, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Jlayer))
                chip.add(dxf.rectangle(struct().getPos((w + gap, factor*s)), UNDERCUT, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((0, abs(direction)*s)), w + gap + UNDERCUT, UNDERCUT, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((0, factor*s-UNDERCUT)), w + gap + UNDERCUT, UNDERCUT, rotation=struct().direction,
                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((-UNDERCUT, (factor+1)*s+UNDERCUT)), UNDERCUT, s-2*UNDERCUT, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                struct().translatePos((0, direction * s), angle=180)

                # undercut.translatePos((0, s/2))
                # chip.add(dxf.rectangle(undercut.getPos((0, 0)), w+gap+UNDERCUT, UNDERCUT,
                #                    rotation=undercut.direction, bgcolor=bgcolor, layer=Ulayer),
                #                    structure=structure, length= gap)

            elif finalpiece:
                chip.add(dxf.rectangle(struct().getPos((0, factor*s)), w + gap, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Jlayer))
                chip.add(dxf.rectangle(struct().getPos((w + gap, factor*s)), UNDERCUT, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((-UNDERCUT, (factor+1)*s)), UNDERCUT, s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                struct().translatePos((0, direction * s), angle=180)
    

    struct().translatePos((0, +s/2))

def smallJ(chip, structure, start, j_length, Jlayer, Ulayer, gap=0.14, lead = 1, ubridge_width=0.3, **kwargs):

    x, y = start

    tmp = round(200 * (lead - j_length) / 2) / 200 # rounding to make sure it falls in 5nm grid

    j_quad = dxf.polyline(points=[[x, y], [x+0.5, y-tmp], [x+0.5, y-tmp-j_length], [x, y-lead], [x, y]], bgcolor=chip.wafer.bg(), layer=Jlayer)
    j_quad.close()
    chip.add(j_quad)

    # u_quad = dxf.polyline(points=[[x, y], [x+0.5, y-tmp], [x+0.5, y-tmp-j_length], [x, y-lead], [x, y]], bgcolor=chip.wafer.bg(), layer=Ulayer)
    # u_quad.close()
    # chip.add(u_quad)

    structure.translatePos((0.5, - j_length/2), angle=0)

    undercut = structure.clone()
    
    finger_length = 1.36 # specified by LL 
    chip.add(dxf.rectangle(structure.getPos((0, 0)), finger_length, j_length,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Jlayer))
    chip.add(dxf.rectangle(structure.getPos((finger_length, -ubridge_width-lead/2 +j_length/2)), gap, 2*ubridge_width + lead,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Ulayer))
    structure.translatePos((finger_length + gap, j_length/2), angle=0)

    # do undercut for U layer 
    undercut.translatePos((-0.5, j_length/2), angle=0)
    mw.CPW_taper(chip, undercut, length=0.5, w1 = j_length, w0 = lead, s0 = ubridge_width, s1 = ubridge_width, layer = Ulayer)
    mw.CPW_straight(chip, undercut, w = j_length, s = ubridge_width, length = finger_length, layer = Ulayer)

    # do second undercut near bridge
    if gap < ubridge_width:
        undercut.translatePos((-(ubridge_width-gap), 0), angle=0)
        mw.CPW_straight(chip, undercut, w = j_length+2*ubridge_width, s = (lead - j_length)/2, length = (ubridge_width-gap), layer = Ulayer)

# checker_board for resolution tests
def checker_board(chip, structure, start, num, square_size, layer=None):
    x, y = start
    for i in range(num):
        for j in range(num):
            if (i+j) % 2 == 0:
                chip.add(dxf.rectangle(structure.getPos((x + i * square_size, y + j * square_size)), square_size, square_size,
                                       rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=layer))

# clover_leaf for 4-pt_probe measurement
def clover_leaf(chip, structure, start, diameter, layer=None, ptDensity=64, sf=1.05, ground_plane=True):
    x, y = start
    # init polyline
    size = diameter/2

    if ground_plane:
        poly = dxf.polyline(points=[], bgcolor=chip.wafer.bg(), layer=layer)

        ## first quadrant
        # big circle
        poly.add_vertices(curveAB((x+size/10, y+size), (x+size, y+size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x+size/4, y+size/10), (x+size/4, y-size/10), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## second quadrant
        # big circle
        poly.add_vertices(curveAB((x+size, y-size/10), (x+size/10, y-size), ptDensity=ptDensity))

        # finish 1st poly object
        poly.add_vertices([(x+size/10, y-sf*size), (x+sf*size, y-sf*size), (x+sf*size, y+sf*size), (x+size/10, y+sf*size)])

        poly.close()

        chip.add(poly)

        # second poly object
        poly = dxf.polyline(points=[(x+size/10, y-size)], bgcolor=chip.wafer.bg(), layer=layer)

        # small circle
        poly.add_vertices(curveAB((x+size/10, y-size/4), (x-size/10, y-size/4), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## third quadrant
        # big circle
        poly.add_vertices(curveAB((x-size/10, y-size), (x-size, y-size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x-size/4, y-size/10), (x-size/4, y+size/10), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## fourth quadrant
        # big circle
        poly.add_vertices(curveAB((x-size, y+size/10), (x-size/10, y+size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x-size/10, y+size/4), (x+size/10, y+size/4), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        # finish 2nd poly object
        poly.add_vertices([(x+size/10, y+sf*size), (x-sf*size, y+sf*size), (x-sf*size, y-sf*size), (x+size/10, y-sf*size)])

        poly.close() 

        chip.add(poly)
    else:
        poly = dxf.polyline(points=[], bgcolor=chip.wafer.bg(), layer=layer)        
        
        ## first quadrant
        # big circle
        poly.add_vertices(curveAB((x+size/10, y+size), (x+size, y+size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x+size/4, y+size/10), (x+size/4, y-size/10), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## second quadrant
        # big circle
        poly.add_vertices(curveAB((x+size, y-size/10), (x+size/10, y-size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x+size/10, y-size/4), (x-size/10, y-size/4), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## third quadrant
        # big circle
        poly.add_vertices(curveAB((x-size/10, y-size), (x-size, y-size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x-size/4, y-size/10), (x-size/4, y+size/10), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## fourth quadrant
        # big circle
        poly.add_vertices(curveAB((x-size, y+size/10), (x-size/10, y+size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x-size/10, y+size/4), (x+size/10, y+size/4), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        poly.close() 

        chip.add(poly)

# create chip which has 10 clover leafs for each metal layer
# also has checkerboard pattern from 0.5um to 50um as [0.5, 1, 2, 4, 8, 16, 32, 50] um, with label on '5_M1' layer
# checkerboard from 0.004 to 2um as [0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.5, 1, 2] um, with label on '???' layer

def create_clover_leaf_checkerboard(chip, loc, jlayer='20_SE1', M1_layer="5_M1",
                                    clover_leaf_size=250, spacing=20, 
                                    M1_checkerboard=None, JLayer_checkerboard=None,
                                    do_JClover=False,
                                    JLayer_ch_offset=50, text_size=(40,40),
                                    num_checkers=10):
    # clover leaf
    for i in range(3):
        structure = m.Structure(chip, start = vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, clover_leaf_size/2)))
        clover_leaf(chip, structure, vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, clover_leaf_size/2)), 
                    clover_leaf_size, layer=M1_layer)
    label_struct = m.Structure(chip, start = vadd(loc, (0, (clover_leaf_size + spacing))))
    AlphaNumStr(chip, label_struct, f'{M1_layer}', size=text_size)

    if M1_checkerboard is None:
        M1_checkerboard = [0.5, 1, 2, 4, 8, 16]
    # checkerboard Metal
    for i, size in enumerate(M1_checkerboard):
        structure = m.Structure(chip, start = vadd(loc, (np.sum([(num_checkers+2)*size_sq for size_sq in M1_checkerboard[:i]]), clover_leaf_size+2*spacing+text_size[1])))  
        checker_board(chip, structure, (0,0), num_checkers, size, layer=M1_layer)
    
    if JLayer_checkerboard is None:
        # JLayer_checkerboard = [0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.5, 1, 2]
        JLayer_checkerboard = [0.016, 0.032, 0.064, 0.128, 0.256, 0.5, 1, 2]
    # checkerboard Junction
    for i, size in enumerate(JLayer_checkerboard):
        structure = m.Structure(chip, start = vadd(loc, (np.sum([(num_checkers+2)*size_sq for size_sq in JLayer_checkerboard[:i]]), clover_leaf_size+2*spacing+text_size[1]+JLayer_ch_offset)))  
        checker_board(chip, structure, (0,0), num_checkers, size, layer=jlayer)

    if do_JClover:
        for i in range(3):
            structure = m.Structure(chip, start = vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, 1.5*clover_leaf_size+4*spacing+2*text_size[1]+np.max(M1_checkerboard)*num_checkers)))
            clover_leaf(chip, structure, vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, 1.5*clover_leaf_size+4*spacing+2*text_size[1]+np.max(M1_checkerboard)*num_checkers)), 
                        clover_leaf_size, layer=jlayer, ground_plane=False)
        label_struct = m.Structure(chip, start = vadd(loc, (0, 1*clover_leaf_size+3*spacing+text_size[1]+np.max(M1_checkerboard)*num_checkers)))
        AlphaNumStr(chip, label_struct, f'{jlayer}', size=text_size)

def create_test_grid(chip, no_column, no_row, x_var, y_var, x_key, y_key, ja_length, j_length,
                     gap_width_ja, gap_width_j, window_width, ubridge_width, no_gap, start_grid_x,
                     start_grid_y, M1_pads, ulayer_edge, test_JA, test_smallJ,
                     dose_Jlayer_row, dose_Ulayer_column, pad_w, pad_s,
                     ptDensity, pad_l, lead_length, cpw_s, doseU, doseJ, jgrid_skip=1, ugrid_skip=1,
                     do_e_beam_label= True, arb_struct=False, arb_path=None, arb_ulayer=None,
                     arb_jlayer=None, do_bandage=True, arb_gnd_width=None, do_ccut=True, do_ebeam=True, **kwargs):

    if M1_pads:
        row_sep = 490
        column_sep = 1000

    elif not M1_pads:
        row_sep = 150
        column_sep = 200

    if dose_Jlayer_row:
        jlayer = []

        for i in range(no_column):
            jlayer.append(f"2{i*jgrid_skip:02}_SE1_dose_{i*jgrid_skip:02}_{round(doseJ[0][i])}_uC")
            chip.wafer.addLayer(jlayer[i],221)
    else:
        jlayer = ['20_SE1'] * no_column

    # for layer in jlayer:
    #     print(layer)
    
    if dose_Ulayer_column:
        ulayer = []

        for i in range(no_row):
            ulayer.append(f"6{i*ugrid_skip:02}_SE1_JJ_dose_{i*ugrid_skip:02}_{round(doseU[i][0])}_uC")
            chip.wafer.addLayer(ulayer[i],150)
    else:
        ulayer = ['60_SE1_JJ'] * no_row

    if do_bandage:
        bandage_ulayer = '699_JJ_bandage_Ucut'
        bandage_jlayer = '299_JJ_bandage_Jcut'
        chip.wafer.addLayer(bandage_ulayer, 255)
        chip.wafer.addLayer(bandage_jlayer, 1)

    for row in range(no_row):

        row_label = m.Structure(chip, start = (start_grid_x-250, start_grid_y + row * row_sep),)

        AlphaNumStr(chip, row_label, y_key, size=(40,40), centered=False)
        row_label.translatePos((-120, -60))
        AlphaNumStr(chip, row_label, str(round_sf(y_var[row][0],3)), size=(40,40), centered=False)

        if row == 0:
            for i in range(no_column):
                column_label = m.Structure(chip, start = (start_grid_x + i * column_sep-40, start_grid_y - 300),)
                AlphaNumStr(chip, column_label, x_key, size=(40,40), centered=False)
                column_label.translatePos((-120, 60))
                AlphaNumStr(chip, column_label, str(round_sf(x_var[0][i],3)), size=(40,40), centered=False)

        for i in range(no_column):

            s_test = m.Structure(chip, start = (start_grid_x + i * column_sep, start_grid_y + row * row_sep))
            
            s_test_gnd = s_test.clone()
            
            if test_JA:
                lead = ja_length[row][i]
                
            elif test_smallJ:
                lead = 1.5 # set equal to a constant for even resistivity. Small enough for bandaging
                if j_length[row][i] > 1.2:
                    lead = j_length[row][i] + 0.8
                
            # Left pad
            if M1_pads:
                mw.CPW_stub_round(chip, s_test, w = pad_w, s = pad_s, ptDensity = ptDensity, flipped = True)
                mw.CPW_straight(chip, s_test, w = pad_w, s = pad_s, length = pad_l, ptDensity = ptDensity)
                
                mw.CPW_taper(chip, s_test, length=lead_length, w0 = pad_w, s0=pad_s, w1 = pad_w/4, s1=pad_s)
                if do_ccut:
                    mw.CPW_straight(chip, s_test, w = pad_w/4, s = (80-pad_w/4)/2, length = 2)
                    s_test.translatePos((-2, 0))
                    mw.Strip_straight(chip, s_test, length=2, w = 7)

                    mw.CPW_straight(chip, s_test, w = pad_w/4, s = (80-pad_w/4)/2, length = 3)
                    s_test.translatePos((-3, 0))
                    mw.Strip_straight(chip, s_test, length=3, w = 3)

                    s_test.translatePos((1*lead_length/6,0))

                s_test_gnd = s_test.clone()
                if do_ccut:
                    s_test_gnd.translatePos((-1*lead_length/6, 0))

                s_test.translatePos((-lead_length/2, 0))

                if do_ebeam:
                    s_test_ubridge = s_test.clone()
                    s_bandage = s_test.clone()

                    mw.Strip_taper(chip, s_test, length=lead_length/2, w0 = pad_w/5, w1 = lead, layer = jlayer[i])
                    mw.Strip_straight(chip, s_test, length=lead_length, w = lead, layer = jlayer[i])
                
                    if ulayer_edge:
                        s_test_ubridge.translatePos((-3*ubridge_width[row][i], 0))
                        mw.Strip_straight(chip, s_test_ubridge, length=3*ubridge_width[row][i], w = pad_w/5+2*ubridge_width[row][i], layer = ulayer[row])
                        mw.CPW_taper(chip, s_test_ubridge, length=lead_length/2, w0 = pad_w/5, w1 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[row])
                        mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length, layer = ulayer[row])
            
                    if do_bandage:
                        s_bandage.translatePos((-lead_length/8-ubridge_width[row][i], 0))
                        mw.Strip_straight(chip, s_bandage, length=ubridge_width[row][i], w = pad_w/10+2*ubridge_width[row][i], s = cpw_s, layer = bandage_ulayer)
                        mw.Strip_straight(chip, s_bandage, length=lead_length/4, w = pad_w/10, s = cpw_s, layer = bandage_jlayer)
                        s_bandage.translatePos((-lead_length/4, 0))
                        mw.CPW_straight(chip, s_bandage, w = pad_w/10, s = ubridge_width[row][i], length = lead_length/4, layer = bandage_ulayer)
                        mw.Strip_straight(chip, s_bandage, length=ubridge_width[row][i], w = pad_w/10+2*ubridge_width[row][i], s = cpw_s, layer = bandage_ulayer)

            
            elif not arb_struct and do_ebeam:
                s_test_ubridge = s_test.clone()

                mw.Strip_taper(chip, s_test, length=lead_length/5, w0 = pad_w/10, w1 = lead, layer = jlayer[i])
                mw.Strip_straight(chip, s_test, length=lead_length/5, w = lead, layer = jlayer[i])

                if ulayer_edge:
                    s_test_ubridge.translatePos((-ubridge_width[row][i], 0))
                    mw.Strip_straight(chip, s_test_ubridge, length=ubridge_width[row][i], w = pad_w/10+2*ubridge_width[row][i], layer = ulayer[row])
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length/5, w0 = pad_w/10, w1 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[row])
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length/5, layer = ulayer[row])

            if do_e_beam_label and do_ebeam:
                e_beam_label = s_test.clone()
                e_beam_label.translatePos((-13, 10))
                AlphaNumStr(chip, e_beam_label, y_key, size=(4,4), centered=False, layer='20_SE1')
                e_beam_label.translatePos((4, 0))
                AlphaNumStr(chip, e_beam_label, str(round_sf(y_var[row][0],3)), size=(4,4), centered=False, layer='20_SE1')

                e_beam_label.translatePos((-24, 8))
                AlphaNumStr(chip, e_beam_label, x_key, size=(4,4), centered=False, layer='20_SE1')
                e_beam_label.translatePos((4, 0))
                AlphaNumStr(chip, e_beam_label, str(round_sf(x_var[0][i],3)), size=(4,4), centered=False, layer='20_SE1')

            if test_JA and do_ebeam:
                junction_chain(chip, s_test, n_junc_array=no_gap, w=window_width[row][i], s=lead, gap=gap_width_ja[row][i], CW = True, finalpiece = False, Jlayer = jlayer[i], Ulayer=ulayer[row])

            elif test_smallJ and do_ebeam:
                x, y = s_test.getPos((0, +lead/2))
                smallJ(chip, s_test, (x, y), j_length[row][i], Jlayer = jlayer[i], Ulayer = ulayer[row], lead = lead, gap=gap_width_j[row][i], ubridge_width=ubridge_width[row][i])
            
            elif arb_struct and do_ebeam:
                x, y = s_test.getPos((0, 0))
                add_imported_polyLine(chip, start=(x, y), file_name=arb_path, rename_dict={arb_jlayer: jlayer[i], arb_ulayer: ulayer[row]}, scale=1.0)

            s_test_ubridge = s_test.clone()
            s_bandage = s_test.clone()

            # Ground window for structure 
            if test_JA:

                if len(no_gap) <= 1:
                    gnd_width = lead_length*2 + (gap_width_ja[row][i] + window_width[row][i]) * no_gap[0] - window_width[row][i]

                elif len(no_gap) >= 2:
                    arraylength = 0
                    for j in range(len(no_gap)):
                        arraylength += (-1)**j*no_gap[j]

                    gnd_width = lead_length*2 + (gap_width_ja[row][i] + window_width[row][i]) * arraylength - window_width[row][i]

            elif test_smallJ:
                # 0.5 = LL taper length
                # 1.36 = LL finger length
                gnd_width = lead_length*2 + 0.5 + 1.36 + gap_width_j[row][i]

            elif arb_struct:
                # 0.5 = LL taper length
                # 1.36 = LL finger length
                gnd_width = arb_gnd_width

            if do_ccut:
                gnd_width += 2*lead_length/6

            if not M1_pads:
                position = (-(lead_length)*(2-4/5)/2, -40)
            elif M1_pads:
                position = (0, -40)

            chip.add(dxf.rectangle(s_test_gnd.getPos(position), gnd_width, 80,
                        bgcolor=chip.wafer.bg(), layer="5_M1"))

            # Right pad
            if M1_pads:
                if do_ebeam:
                    if ulayer_edge:
                        mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length, layer = ulayer[row])
                        mw.CPW_taper(chip, s_test_ubridge, length=lead_length/2, w1 = pad_w/5, w0 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[row])
                        mw.Strip_straight(chip, s_test_ubridge, length=ubridge_width[row][i], w = pad_w/5+2*ubridge_width[row][i], layer = ulayer[row])

                    mw.Strip_straight(chip, s_test, length=lead_length, w = lead, s = cpw_s, layer = jlayer[i])
                    mw.Strip_taper(chip, s_test, length=lead_length/2, w1 = pad_w/5, w0 = lead, layer = jlayer[i])

                    s_test.translatePos((-lead_length/2, 0))

                else:
                    s_test.translatePos((gnd_width+1*lead_length/6, 0))

                if do_ccut:
                    s_test.translatePos((+1*lead_length/6, 0))
                    mw.CPW_straight(chip, s_test, w = pad_w/4, s = (80-pad_w/4)/2, length = 3)
                    s_test.translatePos((-3, 0))
                    mw.Strip_straight(chip, s_test, length=3, w = 3)

                    mw.CPW_straight(chip, s_test, w = pad_w/4, s = (80-pad_w/4)/2, length = 2)
                    s_test.translatePos((-2, 0))
                    mw.Strip_straight(chip, s_test, length=2, w = 7)
                
                mw.CPW_taper(chip, s_test, length=lead_length, w1 = pad_w, w0 = pad_w/4, s0 = pad_s, s1 = pad_s)
                mw.CPW_straight(chip, s_test, w = pad_w, s = pad_s, length = pad_l, ptDensity = ptDensity)
            
                mw.CPW_stub_round(chip, s_test, w = pad_w, s = pad_s, ptDensity = ptDensity, flipped = False)

                if do_bandage and do_ebeam:
                    s_bandage.translatePos((-ubridge_width[row][i]+lead_length+3*lead_length/8, 0))
                    mw.Strip_straight(chip, s_bandage, length=ubridge_width[row][i], w = pad_w/10+2*ubridge_width[row][i], s = cpw_s, layer = bandage_ulayer)
                    mw.Strip_straight(chip, s_bandage, length=lead_length/4, w = pad_w/10, s = cpw_s, layer = bandage_jlayer)
                    s_bandage.translatePos((-lead_length/4, 0))
                    mw.CPW_straight(chip, s_bandage, w = pad_w/10, s = ubridge_width[row][i], length = lead_length/4, layer = bandage_ulayer)
                    mw.Strip_straight(chip, s_bandage, length=ubridge_width[row][i], w = pad_w/10+2*ubridge_width[row][i], s = cpw_s, layer = bandage_ulayer)

            elif not arb_struct and do_ebeam:
                if ulayer_edge:
                    s_test_ubridge = s_test.clone()
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length/5, layer = ulayer[row])
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length/5, w1 = pad_w/10, w0 = lead, s0 = 3*ubridge_width[row][i], s1 = 3*ubridge_width[row][i], layer = ulayer[row])
                    mw.Strip_straight(chip, s_test_ubridge, length=3*ubridge_width[row][i], w = pad_w/10+2*ubridge_width[row][i], layer = ulayer[row])

                mw.Strip_straight(chip, s_test, length=lead_length/5, w = lead, s = cpw_s, layer = jlayer[i])
                mw.Strip_taper(chip, s_test, length=lead_length/5, w1 = pad_w/10, w0 = lead, layer = jlayer[i])
            
class TestChip(m.Chip):
    def __init__(self, wafer, chipID, layer, params, test=True, do_clv_and_cb=True,
                 chipWidth=6800, chipHeight=6800, lab_logo=True, do_chip_title=True,
                 do_e_beam_alignment_marks=True):
        super().__init__(wafer, chipID, layer)

        # # Top left no metal strip
        # s = m.Structure(self, start=(0, chipHeight - 50), direction=0)
        # mw.Strip_straight(self, s, length=300, w=100)

        # Chip ID
        if do_chip_title:
            s = m.Structure(self, start=(chipWidth/2, chipHeight-520))
            AlphaNumStr(self, s, chipID, size=(500, 500), centered=True)

        # add standard clover leaf and checkerboard
        if do_clv_and_cb:
            create_clover_leaf_checkerboard(self, loc=(chipWidth-1300, chipHeight-490))

        # add lab logo
        if lab_logo:
            add_imported_polyLine(self, start=(1000, chipHeight-280),
                                file_name=os.path.join(file_dir, 'slab_logo.dxf'),
                                rename_dict={'L1D0': layer}, scale=0.6)
        
        if do_e_beam_alignment_marks:
            poses = [(chipWidth-100, chipHeight-100), (100, chipHeight-100), (100, 100), (chipWidth-100, 100)]
            for pos in poses:
                MarkerSquare(w=self, pos=pos, layer=layer)
                MarkerSquare(w=self, pos=pos, layer="EBEAM_MARK")
            # print(f'e-beam alignment marks added to chip at positions: {poses}')

        if test:
            for i in range(len(params)):
               create_test_grid(self, **params[i])
            #    print(i)

class Fluxonium4inWafer(m.Wafer):
    def __init__(self, waferID, directory=current_dir+'\\', **kwargs):
        super().__init__(waferID, directory, chipWidth=6800, chipHeight=6800, 
                waferDiameter=m.waferDiameters['4in'], sawWidth=200, frame=True, markers=True, solid=False, **kwargs)

        self.SetupLayers([  # [layernumber_name, color (autocad index colors)] https://gohtx.com/acadcolors.php
            ['5_M1', 2], #Al base metal
            #['10_M2', 2], #TiN base metal
            ['20_SE1', 221], #Fine shadow-evaporated features
            ['55_SEB1', 221], #Coarse shadow-evaporated features
            ['60_SE1_JJ', 150], #Auxiliary layer for SE1_JJ DRC checks
        ])

        self.setupJunctionLayers(JLAYER='20_SE1', ULAYER='60_SE1_JJ')
        #w.setupAirbridgeLayers(BRLAYER='31_BR', RRLAYER='30_RR', IBRLAYER='131_IBR', IRRLAYER='130_IRR', brcolor=41, rrcolor=32) #CHECK why only on interposer layer

        self.init(FRAME_LAYER=['703_ChipEdge', 7])
        self.DicingBorder(thin=20, long=10, dash=500)
        self.DicingBorder(thin=20, long=10, dash=500, layer='5_M1')
        self.DicingBorder(thin=20, long=10, dash=500, layer='55_SEB1')
        self.DicingBorder(thin=20, long=10, dash=500, layer='299_JJ_bandage_Jcut')

        # WARNING: hardcoded to be in default locations
        markerpts = [(-13800,-34800),(-13800, 28200),(14200, 28200),(14200, -34800)]
        for pt in markerpts:
            #(note: mirrorX and mirrorY are true by default)
            MarkerSquare(self, pt, 80, layer='EBEAM_MARK')

    # chip labels in specified location on wafer
    def add_chip_labels(self, loc=(100,100), height=600, layer='MARKERS'):
        """
        Add chip labels to all chips on wafer at specified location
        WARNING: Text size is not naturally visible on klayout, make sure it doesn't intersect

        Args:
            loc (tuple): location of chip labels
            height (int): height of chip labels
            layer (str): layer of chip labels
        """
        for i in range(len(self.chips)):
            #identifying marks
            self.add(dxf.text(str(i),vadd(self.chipPts[i],loc),height=height,layer=layer))

    # add wafer name to every chip on wafer
    def add_wafer_name(self, loc=(3500,100), height=200, layer='MARKERS'):
        """
        Add wafer name to all chips on wafer at specified location
        WARNING: Text size is not naturally visible on klayout, make sure it doesn't intersect

        Args:
            loc (tuple): location of wafer name
            height (int): height of wafer name
            layer (str): layer of wafer name
        """
        for i in range(len(self.chips)):
            #identifying marks
            self.add(dxf.text(self.fileName,vadd(self.chipPts[i],loc),height=height,layer=layer))

# import image, binarize based on threshold
def binarize_image(image_path, threshold=0.5, show=False, save=False):
    # Read the image with alpha channel
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        raise ValueError("Image not found or unable to read.")
    
    # convert image to grayscale
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # binarize
    _, binary = cv2.threshold(img_gray, threshold*255, 1, cv2.THRESH_BINARY)

    # invert binary
    binary = 1 - binary

    # Check if the image has an alpha channel
    if img.shape[2] == 4:
        print("The image has an alpha channel. Setting equal to 0")

        # Extract the alpha channel
        alpha_channel = img[:,:,3]

        # Create a mask: 0 for transparent pixels (alpha == 0), 1 for non-transparent
        mask = np.where(alpha_channel == 0, 0, 1).astype(np.uint8)

        # combine the binary image with the mask
        binarized_with_alpha = 255*cv2.bitwise_and(binary, mask)

    else:
        binarized_with_alpha = 255*binary

    # invert the image 255 -> 0, 0 -> 255
    binarized_with_alpha = 255 - binarized_with_alpha

    if show:
        # plt.imshow(binary, cmap='gray')
        plt.imshow(binarized_with_alpha, cmap='gray')
        plt.show()

    if save:
        cv2.imwrite(image_path[:-4] + '_bw.png', binarized_with_alpha)

    return binarized_with_alpha

def image_to_gds_file(fileName, layerNum, outputFileName=None, mergeShapes=True, extent=300, outputDXF=False):
    """Convert an image file (fileName) to a GDS file
    """
    img = cv2.imread(fileName)

    if img is None:
        raise ValueError("Image not found or unable to read.")
 
    width = img.shape[1]
    height = img.shape[0]

    # Convert an image to grayscale one
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    _, binaryImage = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)
    
    # The GDSII file is called a library, which contains multiple cells.
    lib = gdspy.GdsLibrary()
    gdspy.current_library=gdspy.GdsLibrary()

    polygons = []

    grid = lib.new_cell("GRID")

    for x in range(width):
        for y in range(height):
            if binaryImage.item(y, x) == 0:
                polygons.append([(x, y), (x + 1, y),(x + 1, y + 1), (x, y + 1)])

    polygonSet = gdspy.PolygonSet(polygons)

    polygonSet.mirror((1, 0))

    # translate to origin
    ((xmin,ymin),(xmax,ymax)) = polygonSet.get_bounding_box()
    polygonSet.translate(-(xmax+xmin)/2,-(ymax+ymin)/2)

    # scale max dimension to extent
    scale = extent/max(xmax-xmin,ymax-ymin)
    polygonSet.scale(scale)

    if mergeShapes is True:
        polygonSet = gdspy.boolean(polygonSet, None, 'or')

    grid.add(polygonSet)

    if outputFileName is None:
        outputFileName = fileName[:-4] + ".gds"

    lib.write_gds(outputFileName)
    print(f"GDS file saved as '{outputFileName}'")

    if outputDXF:
        # Load the GDS file
        layout = Layout()
        layout.read(outputFileName)

        # layout.write("output.dxf")

        # Create a new layout for DXF (DXF doesn't support hierarchy)
        flat_layout = Layout()
        flat_layout.dbu = layout.dbu  # Set the database unit

        new_cell = flat_layout.create_cell('TOP')
        # Flatten the layout and copy all cells to the new layout
        for i, cell in enumerate(layout.each_cell()):
            cell.flatten(-1)
            new_cell.copy_tree(cell)

        # Write the flattened layout to DXF
        flat_layout.write(outputFileName[:-4] + ".dxf")

        print(f"DXF file saved as '{outputFileName[:-4]}.dxf'")

class ImportedChip(m.Chip):
    def __init__(self,wafer,chipID,layer,file_name,rename_dict={},
                 chipWidth=6800, chipHeight=6800, surpress_warnings=False,
                 do_chip_title=True, do_e_beam_alignment_marks=True, centered=True):
        super().__init__(wafer,chipID,layer)

        layout = Layout()
        layout.read(file_name)
        
        # Create a new layout for DXF (DXF doesn't support hierarchy)
        flat_layout = Layout()
        flat_layout.dbu = layout.dbu  # Set the database unit

        new_cell = flat_layout.create_cell('TOP')
        # Flatten the layout and copy all cells to the new layout
        for i, cell in enumerate(layout.each_cell()):
            cell.flatten(-1)
            new_cell.copy_tree(cell)

        # Write the flattened layout to DXF
        flattened_filename = file_name[:-4] + '_flattened.dxf'
        flat_layout.write(flattened_filename)
            
        # read in with ezdxf
        doc = ezdxf.readfile(flattened_filename)
        doc.header['$INSUNITS'] = 13 
        msp = doc.modelspace()

        defaultChipWidth = 6800
        defaultChipHeight = 6800

        # Chip ID
        if do_chip_title:
            s = m.Structure(self, start=(defaultChipWidth/2, defaultChipHeight-200))
            AlphaNumStr(self, s, chipID, size=(100, 100), centered=True)

        # if chipWidth and chipHeight are not default, shift all points by the difference/2
        offset = (defaultChipWidth/2, defaultChipHeight/2)

        if not centered:
            # assume left bottom corner is (0,0)
            offset = (0, 0)

        for entity in msp:
            if entity.dxf.layer in rename_dict:
                layer_updated = rename_dict[entity.dxf.layer]
            else:
                layer_updated = entity.dxf.layer
            
            if entity.dxftype() == 'LINE':
                self.add(dxf.line(
                    start=vadd(entity.dxf.start, offset),
                    end=vadd(entity.dxf.end, offset),
                    color=entity.dxf.color,
                    layer=layer_updated
                ))
            elif entity.dxftype() == 'CIRCLE':
                self.add(dxf.circle(
                    center=vadd(entity.dxf.center, offset),
                    radius=entity.dxf.radius,
                    color=entity.dxf.color,
                    layer=layer_updated
                ))
            elif entity.dxftype() == 'POLYLINE':
                pts = list(entity.points())
                if len(pts) == 0:
                    continue

                pts.append(pts[0])
                pts = [vadd(pt, offset) for pt in pts]
                poly = dxf.polyline(
                    points=pts,
                    color=entity.dxf.color,
                    layer=layer_updated,
                    bgcolor=self.wafer.bg(layer)
                )
                poly.POLYLINE_CLOSED = True
                poly.close()

                self.add(poly)
            elif entity.dxftype() == 'INSERT':
                raise NotImplementedError('INSERT not supported. Please "Flatten Cells" in klayout before importing')
            else:
                print(f'Unsupported entity type: {entity.dxftype()}, skipping')
                continue
        
        if do_e_beam_alignment_marks:
            poses = [(chipWidth-100, chipHeight-100), (100, chipHeight-100), (100, 100), (chipWidth-100, 100)]
            for pos in poses:
                MarkerSquare(w=self, pos=pos, layer=layer)
                # MarkerSquare(w=self, pos=pos, layer="EBEAM_MARK")
            # print(f'e-beam alignment marks added to chip at positions: {poses}')

def add_imported_polyLine(chip, start, file_name, scale=1.0, rename_dict=None):
    doc = ezdxf.readfile(file_name)
    doc.header['$INSUNITS'] = 13 
    msp = doc.modelspace()

    # check that there is only one layer
    for entity in msp:
        if entity.dxf.layer in rename_dict:
            layer_updated = rename_dict[entity.dxf.layer]
        else:
            layer_updated = entity.dxf.layer

        if entity.dxftype() != 'POLYLINE':
            print(f'Unsupported entity type: {entity.dxftype()}, skipping. Only POLYLINE supported')
            continue
        
        pts = list(entity.points())
        pts = [vmul_scalar(pt, scale) for pt in pts]
        # shift points to start
        pts = [vadd(start, pt) for pt in pts]
        try:
            pts.append(pts[0])
        except:
            #print(f'No points in POLYLINE, skipping')
            continue
        poly = dxf.polyline(
            points=pts,
            color=entity.dxf.color,
            layer=layer_updated,
            bgcolor=chip.wafer.bg(layer_updated)
        )
        poly.POLYLINE_CLOSED = True
        poly.close()

        chip.add(poly)

class StandardTestChip(TestChip):
    def __init__(self, wafer, test_index, default_params, x_low=None, x_high=None, y_low=None,
                 y_high=None, no_row=None, no_column=None, probe_pads=None, metal_layer="5_M1", verbose=False, do_only_params=False, **kwargs):
        """
        Test chip with standard parameters for different tests. Use these as
        witness chips riding along on a wafer. The test_index determines the
        test to be run. The default_params are the parameters that are standard
        
        """
        self.chip_labels = [
               'DOSE',
               'DOSE_JJA',
               'DOSE_JJ',
               'BRIDGE1',
               'BRIDGE2',
               'WINDOW1',
               'WINDOW2',
               'JJ_SIZE1',
               'JJ_SIZE2',
               'JJ_PROB',
               'ARR_PROB',
               'JJ_SIZE3',
               'ARR_PROB2',
            ]

        self.init_default_row_column_probe_pads(test_index)
        
        if no_row is None:
            no_row = self.no_row_default
        if no_column is None:
            no_column = self.no_column_default
        if probe_pads is None:
            probe_pads = self.probe_pads_default

        self.init_default_x_y(test_index)
            
        if x_low is None:
            x_low = self.x_low_default
        if x_high is None:
            x_high = self.x_high_default
        if y_low is None:
            y_low = self.y_low_default
        if y_high is None:
            y_high = self.y_high_default

        params = [self.params_TestChip(no_column, no_row, default_params)]

        x_swept = np.linspace(x_low, x_high, no_column)
        # have shorted and open in the center for test chips 9, 10, 11, 12
        if test_index in [9, 10, 11, 12]:
            x_swept[2] = 0
            x_swept[3] = 0.6 
        x_var = grid_from_row(x_swept, no_row)
        y_swept = np.linspace(y_low, y_high, no_row)
        y_var = grid_from_column(y_swept, no_column, no_row)

        if verbose:
            print(f"x_key: {self.x_key} x_swept: {x_swept}")
            print(f"y_key: {self.y_key} y_swept: {y_swept}")
        
        params[0]['x_var'] = x_var
        params[0]['y_var'] = y_var
        params[0]['M1_pads'] = probe_pads
        params[0]['x_key'] = self.x_key
        params[0]['y_key'] = self.y_key

        self.chipID = self.chip_labels[test_index]

        if test_index == 0:
            params[0]['dose_Jlayer_row'] = True
            params[0]['dose_Ulayer_column'] = True
            params[0]['test_smallJ'] = True
            params[0]['doseJ'] = x_var
            params[0]['doseU'] = y_var

            # deep copy params[0] to params2
            params.append(params[0].copy())
            params[1]['test_smallJ'] = False
            params[1]['test_JA'] = True
            params[1]['start_grid_y'] = 3500

            self.save_dose_table(x_swept, y_swept, self.chipID, default_params['dose_J'], default_params['dose_U'], PEC_factor=params[0]['PEC_factor'])
        elif test_index == 1:
            params[0]['dose_Jlayer_row'] = True
            params[0]['dose_Ulayer_column'] = True
            params[0]['test_JA'] = True
            params[0]['doseJ'] = x_var
            params[0]['doseU'] = y_var
            params[0]['jgrid_skip'] = 5

            self.save_dose_table(x_swept, y_swept, self.chipID, default_params['dose_J'], default_params['dose_U'], jgrid_skip=5, PEC_factor=params[0]['PEC_factor'])
        elif test_index == 2:
            params[0]['dose_Jlayer_row'] = True
            params[0]['dose_Ulayer_column'] = True
            params[0]['test_smallJ'] = True
            params[0]['doseJ'] = x_var
            params[0]['doseU'] = y_var
            params[0]['jgrid_skip'] = 5

            self.save_dose_table(x_swept, y_swept, self.chipID, default_params['dose_J'], default_params['dose_U'], jgrid_skip=5, PEC_factor=params[0]['PEC_factor'])
        elif test_index in [3, 4, 10, 12]:
            params[0]['test_JA'] = True
            params[0]['gap_width_ja'] = x_var
            params[0]['ja_length'] = y_var
        elif test_index in [5, 6]:
            params[0]['test_JA'] = True
            params[0]['gap_width_ja'] = x_var
            params[0]['window_width'] = y_var
        elif test_index in [7, 8, 9, 11]:
            params[0]['test_smallJ'] = True
            params[0]['gap_width_j'] = x_var
            params[0]['j_length'] = y_var

        if not do_only_params:
            super().__init__(wafer, self.chipID, metal_layer, params, **kwargs)
        
        self.params = params

    def init_default_row_column_probe_pads(self, test_index):
        if test_index in [1, 2, 4, 6, 8, 9, 10, 11, 12]:
            # cases when we have a probe pads
            self.no_row_default = 12
            self.no_column_default = 6
            self.probe_pads_default = True
        elif test_index == 0:
            # case with 
            self.no_row_default = 12
            self.no_column_default = 26
            self.probe_pads_default = False
        else:
            # no probe pads
            self.no_row_default = 38
            self.no_column_default = 30 
            self.probe_pads_default = False


    def init_default_x_y(self, test_index):
        """
        Initialize default x and y keys and values for test chips.
        These values were chosen to have failure on both sides.
        
        To adjust these values, change the x_low, x_high, y_low, y_high values
        in the __init__ method.
        """
        if test_index in [0, 1, 2]:
            # doseJ, doseU
            self.x_key = 'DJ'
            self.x_low_default = 500
            self.x_high_default = 2000

            self.y_key = 'DU'
            self.y_low_default = 100
            self.y_high_default = 600
            
        elif test_index in [3, 4]:
            # bridge_gap, bridge_len
            self.x_key = 'gap'
            self.x_low_default = 0.00
            self.x_high_default = 0.32

            self.y_key = 'len'
            self.y_low_default = 1.0
            self.y_high_default = 6.0
            
        elif test_index in [5, 6]:
            # window_gap, window_width
            self.x_key = 'gap'
            self.x_low_default = 0.10
            self.x_high_default = 0.68

            self.y_key = 'win'
            self.y_low_default = 0.10
            self.y_high_default = 0.84

        elif test_index in [7, 8]:
            # JJ_gap, JJ_len
            self.x_key = 'gap'
            self.x_low_default = 0.00 # start at 0 for shorts
            self.x_high_default = 0.32

            self.y_key = 'len'
            self.y_low_default = 0.10
            self.y_high_default = 0.50
        
        elif test_index == 9:
            # JJ_gap, JJ_len
            self.x_key = 'gap'
            self.x_low_default = 0.20 # standard bridge width PalWoopW 2/3/25
            self.x_high_default = self.x_low_default # same value

            self.y_key = 'len'
            self.y_low_default = 0.15 # smallest JJ
            self.y_high_default = 0.55 # large JJ

        elif test_index == 10:
            # JJ_gap, JJ_len
            self.x_key = 'gap'
            self.x_low_default = 0.20 # standard bridge width PalWoopW 2/3/25
            self.x_high_default = self.x_low_default # same value

            self.y_key = 'len'
            self.y_low_default = 2.5 # short bridges
            self.y_high_default = 4.5 # long bridges

        elif test_index in [11, 12]:
            # JJ_gap, JJ_len
            self.x_key = 'gap'
            self.x_low_default = 0.20 # standard bridge width PalWoopW 2/3/25
            self.x_high_default = self.x_low_default # same value

            self.y_key = 'len'
            self.y_low_default = .15 # short bridges
            self.y_high_default = 4.5 # long bridges

    
    def save_dose_table(self, doseJ_range, doseU_range, chipID, dose_J_default,
                        dose_U_default, PEC_factor=0.25, jgrid_skip=1, ugrid_skip=1, save_klayout_rename=True,
                        print_file_location=True):
        """
        Assignment for BEAMER dose table. Saves klayout renamed layers as well
        as default, (i.e. 20_SE1 and 60_SE1_JJ -> L20D0_SE1 and L60D0_SE1_JJ 
        if the dxf file is edited in klayout)

        # LAYER ASSIGNMENT TABLE 
        # Layer/Datatype	,	Assignment Value
        200_SE1_dose_00	,	500
        201_SE1_dose_01	,	500
        """
        # get cwd
        cwd = os.getcwd()
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(f'{cwd}\\dose_table_{chipID}_{date}.txt', 'w') as f:
            f.write('# LAYER ASSIGNMENT TABLE\n')
            f.write('# Layer/Datatype, Assignment Value\n')
            
            for i, doseJ in enumerate(doseJ_range):
                f.write(f'2{i*jgrid_skip:02}_SE1_dose_{i*jgrid_skip:02}_{round(doseJ)}_uC, {doseJ}\n')
            for j, doseU in enumerate(doseU_range):
                updated_doseU = doseU / PEC_factor # PEC factor as we assign PEC in BEAMER
                f.write(f'6{j*ugrid_skip:02}_SE1_JJ_dose_{j*ugrid_skip:02}_{round(doseU)}_uC, {updated_doseU}\n')
            
            # assign 20_SE1' and '60_SE1_JJ' to default values:
            f.write(f'20_SE1, {dose_J_default}\n')
            f.write(f'60_SE1_JJ, {dose_U_default / PEC_factor}\n')

            # assign bandage layers to default values
            f.write(f'299_JJ_bandage_Jcut, {dose_J_default}\n')
            f.write(f'699_JJ_bandage_Ucut, {dose_U_default / PEC_factor}\n')

            # accounts for klayout renaming dose layers
            if save_klayout_rename:
                for i, doseJ in enumerate(doseJ_range):
                    f.write(f'L2{i*jgrid_skip:02}D0_SE1_dose_{i*jgrid_skip:02}_{round(doseJ)}_uC, {doseJ}\n')
                for j, doseU in enumerate(doseU_range):
                    updated_doseU = doseU / PEC_factor # PEC factor as we assign PEC in BEAMER
                    f.write(f'L6{j*ugrid_skip:02}D0_SE1_JJ_dose_{j*ugrid_skip:02}_{round(doseU)}_uC, {updated_doseU}\n')
                
                # assign bandage layers to default values
                f.write(f'L299D0_JJ_bandage_Jcut, {dose_J_default}\n')
                f.write(f'L699D0_JJ_bandage_Ucut, {dose_U_default / PEC_factor}\n')

                f.write(f"L20D0_SE1, {dose_J_default}\n")
                f.write(f"L60D0_SE1_JJ, {dose_U_default / PEC_factor}\n")

        if print_file_location:
            print(f"Dose table saved to: {cwd}\\dose_table_{chipID}_{date}.txt")

    
    def params_TestChip(self, no_column, no_row, default_params):
        """
        init standard params for all test chips in proper shape for TestChip
        """
        doseJ = grid_from_entry(default_params['dose_J'], no_row, no_column)
        doseU = grid_from_entry(default_params['dose_U'], no_row, no_column)
        
        ubridge_width = grid_from_entry(default_params['ubridge_width'], no_row, no_column)
        window_width = grid_from_entry(default_params['window_width'], no_row, no_column)
        ja_length = grid_from_entry(default_params['ja_length'], no_row, no_column)
        j_length = grid_from_entry(default_params['j_length'], no_row, no_column)
        gap_width_ja = grid_from_entry(default_params['gap_width_ja'], no_row, no_column)
        gap_width_j = grid_from_entry(default_params['gap_width_j'], no_row, no_column)
        
        params = {
            'M1_pads': False,   # Probe pads? No -> tigher packing

            # Choose the tested structure, can only have one True
            'test_smallJ': False, # Small JJ structure
            'test_JA': False, # Junction array structure

            'no_gap': default_params['no_gap'], # number of bridges in JJ array, list includes overlap

            # Vary dose (hence separate layers) for Jlayer (each row) or Ulayer (each column)
            'dose_Jlayer_row': False,
            'dose_Ulayer_column': False,

            'ulayer_edge': True,  # Ulayer edge gap TODO: remove?
            'start_grid_x' : default_params['start_grid_x'], # x position of bottom left of grid
            'start_grid_y' : default_params['start_grid_y'], # y position of bottom left of grid
            
            'ja_length': ja_length,
            'j_length': j_length,
            'gap_width_ja': gap_width_ja,
            'gap_width_j': gap_width_j,
            'window_width': window_width,
            'ubridge_width': ubridge_width,
            'doseJ': doseJ,
            'doseU': doseU,
            'no_column': no_column,
            'no_row': no_row,

            'pad_w': default_params['pad_w'],
            'pad_l': default_params['pad_l'],
            'pad_s': default_params['pad_s'],
            'ptDensity': default_params['ptDensity'],
            'lead_length': default_params['lead_length'],
            'cpw_s': default_params['cpw_s'],
            'PEC_factor': default_params['PEC_factor']
        }

        return params