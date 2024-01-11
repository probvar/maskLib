# -*- coding: utf-8 -*-
"""
Created on Fri Oct  4 17:29:02 2019

@author: Sasha

Library for drawing standard components for DC measurements (Four probe resistance bars, etc)
"""

import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from maskLib.microwaveLib import Strip_straight, Strip_stub_open
from maskLib.microwaveLib import CPW_stub_open,CPW_stub_short,CPW_straight,CPW_taper
from maskLib.Entities import SolidPline, SkewRect, CurveRect, RoundRect, InsideCurve
import numpy as np


# ===============================================================================
# resistance bar chip (default designed for 7x7, but fully configurable for other sizes)
# ===============================================================================

class Rbar(m.Chip):
    def __init__(self,wafer,chipID,layer,bar_width = 40,bar_length = 1500, pad_x = 1000, pad_y = 800, pad_sep = 1000, bar_offs = 500):
        m.Chip7mm.__init__(self,wafer,chipID,layer)

        self.add(dxf.rectangle((0,0),pad_x,self.height,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
        self.add(dxf.rectangle((self.width-pad_x,0),pad_x,self.height,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
        self.add(dxf.rectangle((pad_x,0),self.width-2*pad_x,pad_y,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
        self.add(dxf.rectangle((pad_x,self.height),self.width-2*pad_x,pad_y,valign=const.BOTTOM,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
        
        self.add(dxf.rectangle(self.center,pad_sep,self.height - 2*pad_y,halign=const.CENTER,valign=const.MIDDLE,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
        #inner
        if bar_offs > bar_width/2:
            #right
            self.add(dxf.rectangle(self.centered((bar_offs,0)),bar_offs - bar_width/2,bar_length,valign=const.MIDDLE,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
            #left
            self.add(dxf.rectangle(self.centered((-bar_offs,0)),bar_offs - bar_width/2,bar_length,halign=const.RIGHT,valign=const.MIDDLE,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
        else:
            bar_offs = bar_width/2
            print('Warning: bar offset too low in Rbar. Adjusting offset')
        #outer
        self.add(dxf.rectangle(self.centered((bar_offs + pad_sep/2 +bar_width/2,0)),self.width/2 - bar_offs - pad_x - pad_sep/2 - bar_width/2,bar_length,valign=const.MIDDLE,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
        self.add(dxf.rectangle(self.centered((-bar_offs - pad_sep/2 -bar_width/2,0)),self.width/2 - bar_offs - pad_x - pad_sep/2 - bar_width/2,bar_length,halign=const.RIGHT,valign=const.MIDDLE,bgcolor=wafer.bg(),layer=wafer.defaultLayer))
        
def ResistanceBarBilayer(chip,structure,length=1500,width=40,pad=600,gap=50,r_out=None,secondlayer='SECONDLAYER',bgcolor=None):
    #write a resistance bar centered on the structure or position specified. Defaults to pointing in direction of current structure
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if r_out is None:
        r_out = gap
    
    struct().shiftPos(-length/2-pad-gap)
    srBar=struct().clone(defaults={'w':pad,'s':gap,'r_out':gap})
    Strip_stub_open(chip,srBar,flipped=True,w=pad+2*gap)
    srBar2 = srBar.cloneAlong()
    Strip_straight(chip,srBar,pad,w=pad+2*gap)
    Strip_stub_open(chip,srBar,flipped=False,w=pad+2*gap)
    Strip_straight(chip, srBar, length-2*gap, w=width+2*gap)
    Strip_stub_open(chip,srBar,flipped=True,w=pad+2*gap)
    Strip_straight(chip,srBar,pad,w=pad+2*gap)
    Strip_stub_open(chip,srBar,w=pad+2*gap)
    
    Strip_straight(chip,srBar2,pad,w=pad,layer=secondlayer)
    Strip_straight(chip, srBar2, length, w=width,layer=secondlayer)
    Strip_straight(chip,srBar2,pad,w=pad,layer=secondlayer)
    
def ResistanceBarNegative(chip,structure,length=1500,width=40,pad=600,gap=50,r_out=None,bgcolor=None):
    #write a resistance bar centered on the structure or position specified. Defaults to pointing in direction of current structure
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if r_out is None:
        r_out = gap
    
    struct().shiftPos(-length/2-pad-gap)
    srBar=struct().clone(defaults={'w':pad,'s':gap,'r_out':r_out})
    CPW_stub_open(chip,srBar,flipped=True)
    CPW_straight(chip,srBar,pad)
    CPW_stub_short(chip,srBar,flipped=False,w=width,s=(pad+2*gap-width)/2,curve_ins=False)
    CPW_straight(chip, srBar, length-2*gap, w=width)
    CPW_stub_short(chip,srBar,flipped=True,w=width,s=(pad+2*gap-width)/2,curve_ins=False)
    CPW_straight(chip,srBar,pad)
    CPW_stub_open(chip,srBar)
    
def ResistanceBar(chip,structure,length=1500,width=40,pad=600,r_out=50,secondlayer='SECONDLAYER',bgcolor=None):
    #write a resistance bar centered on the structure or position specified. Defaults to pointing in direction of current structure
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    struct().shiftPos(-length/2-pad)
    srBar=struct().clone(defaults={'w':pad,'r_out':r_out})
    
    Strip_straight(chip,srBar,pad,w=pad,layer=secondlayer)
    Strip_straight(chip, srBar, length, w=width,layer=secondlayer)
    Strip_straight(chip,srBar,pad,w=pad,layer=secondlayer)

# ===============================================================================
# Flux line tips
# ===============================================================================

def FluxLineLTee(chip, structure, tee_width, tee_offset, tee_extend, tee_left=True, w=None, s=None, **kwargs):
    '''
    tee_width: total width of top part of tee
    tee_offset: offset of center of top of tee from center of cpw
    tee_extend: vertical distance of tee from last segment of cpw
    tee_left: determines whether the current is pushed to the left (True) or right (False)
    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            w=0
            print('\x1b[33mw not defined in ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')

    if tee_left: s_extend = struct().cloneAlong(vector=(0, s/2 + w/2))
    else: s_extend = struct().cloneAlong(vector=(0, -s/2 - w/2))
    
    Strip_straight(chip, s_extend, length=tee_extend, w=s, **kwargs)

    s_tee = struct().cloneAlong(vector=(tee_extend + s/2, tee_offset - tee_width/2), newDirection=90)
    Strip_straight(chip, s_tee, length=tee_width, w=s, **kwargs)


def FluxLineFlagTee(chip, structure, tee_width, tee_extend, w=None, s=None, r_out=0, r_corner=None, **kwargs):
    '''
    tee_width: total width of top part of tee
    tee_offset: offset of center of top of tee from center of cpw
    tee_extend: vertical distance of tee from last segment of cpw
    tee_left: determines whether the current is pushed to the left (True) or right (False)
    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            w=0
            print('\x1b[33mw not defined in ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')


    taper_length = tee_extend - r_out
    theta = np.arctan(taper_length/(tee_width - s))

    r_corner = r_out / (1 + np.sin(np.pi/2 - theta))
    dx = r_corner * np.cos(np.pi/2 - theta)
    dy = r_corner * np.sin(np.pi/2 - theta)

    CPW_taper(chip, struct(), length=taper_length, w0=w, s0=s, w1=w, s1=tee_width, **kwargs)

    CPW_taper(chip, struct().clone(), length=dy, w0=w+2*(tee_width-dx), s0=dx, w1=w+2*(tee_width-dx), s1=0, **kwargs)

    s_left = struct().cloneAlong(vector=(0, w/2+tee_width/2))
    s_right = struct().cloneAlong(vector=(0,-(w/2+tee_width/2)))

    # Strip_stub_open(chip, s_left, w=tee_width, r_out=r_out)
    chip.add(RoundRect(s_right.getPos((0, dx/2)), r_out, tee_width-dx, r_out, roundCorners=[0,0,1,0],hflip=False,valign=const.MIDDLE,rotation=s_right.direction,**kwargs), structure=s_right.clone(), length=r_out)
    chip.add(CurveRect(s_right.getPos((dy, -tee_width/2+dx)), r_corner, r_corner, ralign=const.TOP,angle=90+(90-theta*180/np.pi), hflip=True, vflip=True, rotation=s_right.direction + 90, **kwargs), structure=s_right.clone(), length=r_out)

    # Strip_stub_open(chip, s_right, w=tee_width, r_out=r_out)
    chip.add(RoundRect(s_left.getPos((0, -dx/2)), r_out, tee_width-dx, r_out, roundCorners=[0,1,0,0],hflip=False,valign=const.MIDDLE,rotation=s_left.direction,**kwargs), structure=s_left.clone(), length=r_out)
    chip.add(CurveRect(s_left.getPos((dy, tee_width/2-dx)), r_corner, r_corner, ralign=const.TOP,angle=90+(90-theta*180/np.pi), hflip=False, vflip=True, rotation=s_left.direction + 90, **kwargs), structure=s_left.clone(), length=r_out)

