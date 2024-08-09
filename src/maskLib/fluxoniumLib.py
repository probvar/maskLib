# -*- coding: utf-8 -*-
"""
Created on Thu Aug 8 15:11:27 2024

@author: chuyao and paul 
"""
import sys
import os
current_dir = os.getcwd()
import maskLib
from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
import math
import sys, subprocess, os, time
import numpy as np
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.entities import Polyline

import maskLib.MaskLib as m
import maskLib.microwaveLib as mw
from maskLib.utilities import curveAB
from maskLib.markerLib import AlphaNumStr

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

    for count, n in enumerate(n_junc_array):

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
                # undercut amount = 0.3 approximate
                UNDERCUT = 0.3
                chip.add(dxf.rectangle(struct().getPos((0, factor*s)), w + gap, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Jlayer))
                chip.add(dxf.rectangle(struct().getPos((w + gap, factor*s)), UNDERCUT, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((-UNDERCUT, (factor+1)*s)), UNDERCUT, s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                struct().translatePos((0, direction * s), angle=180)
            elif finalpiece:
                chip.add(dxf.rectangle(struct().getPos((0, factor*s)), w + gap, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Jlayer))
                chip.add(dxf.rectangle(struct().getPos((w + gap, factor*s)), UNDERCUT, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((-UNDERCUT, (factor+1)*s)), UNDERCUT, s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                struct().translatePos((0, direction * s), angle=180)
    

    struct().translatePos((0, +s/2))

def smallJ(chip, structure, start, j_length, Jlayer, Ulayer, gap=0.14, lead = 1, **kwargs):

    x, y = start

    tmp = round(200 * (lead - j_length) / 2) / 200 # rounding to make sure it falls in 5nm grid

    j_quad = dxf.polyline(points=[[x, y], [x+0.5, y-tmp], [x+0.5, y-tmp-j_length], [x, y-lead], [x, y]], bgcolor=chip.wafer.bg(), layer=Jlayer)
    j_quad.close()
    chip.add(j_quad)

    # u_quad = dxf.polyline(points=[[x, y], [x+0.5, y-tmp], [x+0.5, y-tmp-j_length], [x, y-lead], [x, y]], bgcolor=chip.wafer.bg(), layer=Ulayer)
    # u_quad.close()
    # chip.add(u_quad)

    structure.translatePos((0.5, - j_length/2), angle=0)
    
    finger_length = 1.36 # specified by LL 
    chip.add(dxf.rectangle(structure.getPos((0, 0)), finger_length, j_length,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Jlayer))
    chip.add(dxf.rectangle(structure.getPos((finger_length, 0)), gap, j_length,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Ulayer))
    structure.translatePos((finger_length + gap, j_length/2), angle=0)

# checker_board for resolution tests
def checker_board(chip, structure, start, num, square_size, layer=None):
    x, y = start
    for i in range(num):
        for j in range(num):
            if (i+j) % 2 == 0:
                chip.add(dxf.rectangle(structure.getPos((x + i * square_size, y + j * square_size)), square_size, square_size,
                                       rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=layer))

# clover_leaf for 4-pt_probe measurement
def clover_leaf(chip, structure, start, diameter, layer=None, ptDensity=64):
    x, y = start
    # init polyline
    size = diameter/2
    poly = dxf.polyline(points=[[x+size/10, y+size/4]], bgcolor=chip.wafer.bg(), layer=layer)

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
        M1_checkerboard = [0.5, 1, 2, 4, 8, 16, 32]
    # checkerboard Metal
    for i, size in enumerate(M1_checkerboard):
        structure = m.Structure(chip, start = vadd(loc, (np.sum([(num_checkers+2)*size_sq for size_sq in M1_checkerboard[:i]]), clover_leaf_size+2*spacing+text_size[1])))  
        checker_board(chip, structure, (0,0), num_checkers, size, layer=M1_layer)
    
    if JLayer_checkerboard is None:
        JLayer_checkerboard = [0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.5, 1, 2]
    # checkerboard Junction
    for i, size in enumerate(JLayer_checkerboard):
        structure = m.Structure(chip, start = vadd(loc, (np.sum([(num_checkers+2)*size_sq for size_sq in JLayer_checkerboard[:i]]), clover_leaf_size+2*spacing+text_size[1]+JLayer_ch_offset)))  
        checker_board(chip, structure, (0,0), num_checkers, size, layer=jlayer)

    for i in range(3):
        structure = m.Structure(chip, start = vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, 1.5*clover_leaf_size+4*spacing+2*text_size[1]+np.max(M1_checkerboard)*num_checkers)))
        clover_leaf(chip, structure, vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, 1.5*clover_leaf_size+4*spacing+2*text_size[1]+np.max(M1_checkerboard)*num_checkers)), 
                    clover_leaf_size, layer=jlayer)
    label_struct = m.Structure(chip, start = vadd(loc, (0, 1*clover_leaf_size+3*spacing+text_size[1]+np.max(M1_checkerboard)*num_checkers)))
    AlphaNumStr(chip, label_struct, f'{jlayer}', size=text_size)

def create_test_grid(chip, grid, x_var, y_var, x_key, y_key, ja_length, j_length,
                     gap_width, window_width, ubridge_width, no_gap, start_grid_x,
                     start_grid_y, M1_pads, ulayer_edge, test_JA, test_smallJ,
                     dose_Jlayer_row, dose_Ulayer_column, no_column, pad_w, pad_s,
                     ptDensity, pad_l, lead_length, cpw_s, **kwargs):

    if M1_pads:
        row_sep = 490
        column_sep = 1000

    elif not M1_pads:
        row_sep = 150
        column_sep = 200

    if dose_Jlayer_row:
        jlayer = []

        #TODO: add checking if layer already exists, use that instead

        for i in range(len(grid)):
            jlayer.append('2'+str(f"{i:02}")+'_SE1_dose_'+str(f"{i:02}"))
            chip.wafer.addLayer(jlayer[i],221)
    else:
        jlayer = ['20_SE1'] * len(grid)
    
    if dose_Ulayer_column:
        ulayer = []

        #TODO: add checking if layer already exists, use that instead

        for i in range(grid[0]):
            ulayer.append('6'+str(f"{i:02}")+'_SE1_JJ_dose_'+str(f"{i:02}"))
            chip.wafer.addLayer(ulayer[i],150)
    else:
        ulayer = ['60_SE1_JJ'] * no_column

    for row, column in enumerate (grid):

        row_label = m.Structure(chip, start = (start_grid_x-250, start_grid_y + row * row_sep),)

        AlphaNumStr(chip, row_label, y_key, size=(40,40), centered=False)
        row_label.translatePos((-120, -60))
        AlphaNumStr(chip, row_label, str(round(y_var[row][0],2)), size=(40,40), centered=False)

        if row == 0:
            for i in range(column):
                column_label = m.Structure(chip, start = (start_grid_x + i * column_sep-40, start_grid_y - 300),)
                AlphaNumStr(chip, column_label, x_key, size=(40,40), centered=False)
                column_label.translatePos((-120, 60))
                AlphaNumStr(chip, column_label, str(round(x_var[0][i],2)), size=(40,40), centered=False)

        for i in range(column):

            s_test = m.Structure(chip, start = (start_grid_x + i * column_sep, start_grid_y + row * row_sep))
            
            s_test_gnd = s_test.clone()
            
            if test_JA:
                lead = ja_length[row][i]
            elif test_smallJ:
                lead = j_length[row][i]+1

            # Left pad
            if M1_pads:
                mw.CPW_stub_round(chip, s_test, w = pad_w, s = pad_s, ptDensity = ptDensity, flipped = True)
                mw.CPW_straight(chip, s_test, w = pad_w, s = pad_s, length = pad_l, ptDensity = ptDensity)
                
                mw.CPW_taper(chip, s_test, length=lead_length, w0 = pad_w, s0=pad_s, w1 = lead + 3, s1=pad_s)

                s_test_gnd = s_test.clone()
                s_test.translatePos((-lead_length, 0))
                s_test_ubridge = s_test.clone()

                mw.Strip_taper(chip, s_test, length=lead_length, w0 = pad_w/4, w1 = lead, layer = jlayer[row])
                mw.Strip_straight(chip, s_test, length=lead_length, w = lead, layer = jlayer[row])
                
                if ulayer_edge:
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length, w0 = pad_w/4, w1 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[i])
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length, layer = ulayer[i])
            else:
                s_test_ubridge = s_test.clone()

                mw.Strip_taper(chip, s_test, length=lead_length/5, w0 = pad_w/10, w1 = lead, layer = jlayer[row])
                mw.Strip_straight(chip, s_test, length=lead_length/5, w = lead, layer = jlayer[row])

                if ulayer_edge:
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length/5, w0 = pad_w/10, w1 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[i])
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length/5, layer = ulayer[i])

            if test_JA:
                junction_chain(chip, s_test, n_junc_array=no_gap, w=window_width[row][i], s=lead, gap=gap_width[row][i], CW = True, finalpiece = False, Jlayer = jlayer[row], Ulayer=ulayer[i])
            
            elif test_smallJ:
                x, y = s_test.getPos((0, +lead/2))
                smallJ(chip, s_test, (x, y), j_length[row][i], Jlayer = jlayer[row], Ulayer = ulayer[i], lead = lead)
            
            s_test_ubridge = s_test.clone()

            # Right pad
            if M1_pads:
                if ulayer_edge:
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length, layer = ulayer[i])
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length, w1 = pad_w/4, w0 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[i])

                mw.Strip_straight(chip, s_test, length=lead_length, w = lead, s = cpw_s, layer = jlayer[row])
                mw.Strip_taper(chip, s_test, length=lead_length, w1 = pad_w/4, w0 = lead, layer = jlayer[row])

                s_test.translatePos((-lead_length, 0))
                
                mw.CPW_taper(chip, s_test, length=lead_length, w1 = pad_w, w0 = lead, s0 = pad_s, s1 = pad_s)
                mw.CPW_straight(chip, s_test, w = pad_w, s = pad_s, length = pad_l, ptDensity = ptDensity)
            
                mw.CPW_stub_round(chip, s_test, w = pad_w, s = pad_s, ptDensity = ptDensity, flipped = False)
    
            else:
                if ulayer_edge:
                    s_test_ubridge = s_test.clone()
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length/5, layer = ulayer[i])
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length/5, w1 = pad_w/10, w0 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[i])

                mw.Strip_straight(chip, s_test, length=lead_length/5, w = lead, s = cpw_s, layer = jlayer[row])
                mw.Strip_taper(chip, s_test, length=lead_length/5, w1 = pad_w/10, w0 = lead, layer = jlayer[row])
                
            # Ground window for structure 
            if test_JA:

                if len(no_gap) <= 1:
                    gnd_width = lead_length*2 + (gap_width[row][i] + window_width[row][i]) * no_gap[0] - window_width[row][i]

                elif len(no_gap) >= 2:
                    arraylength = 0
                    for j in range(len(no_gap)):
                        arraylength += (-1)**j*no_gap[j]

                    gnd_width = lead_length*2 + (gap_width[row][i] + window_width[row][i]) * arraylength - window_width[row][i]

            elif test_smallJ:
                gnd_width = lead_length*2 + 0.5 + 1.36 + 0.14

            if not M1_pads:
                position = (-(lead_length)*(2-4/5)/2, -40)
            elif M1_pads:
                position = (0, -40)

            chip.add(dxf.rectangle(s_test_gnd.getPos(position), gnd_width, 80,
                        bgcolor=chip.wafer.bg(), layer="5_M1"))
            
class testChip(m.ChipHelin):
    def __init__(self, wafer, chipID, layer, params, test=True, do_clv_and_cb=True, chipWidth=6800, chipHeight=6800):
        super().__init__(wafer, chipID, layer)

        # Top left no metal strip
        s = m.Structure(self, start=(0, chipHeight - 50), direction=0)
        mw.Strip_straight(self, s, length=300, w=100)

        # Chip ID
        s = m.Structure(self, start=(chipWidth/2, chipHeight-200))
        AlphaNumStr(self, s, chipID, size=(100, 100), centered=True)

        # add standard clover leaf and checkerboard
        if do_clv_and_cb:
            create_clover_leaf_checkerboard(self, loc=(chipWidth-800, chipWidth-1000))

        if test:
            for i in range(len(params)):
               create_test_grid(self, **params[i])
            #    print(i)