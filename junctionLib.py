# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 13:02:59 2020

@author: sasha

Library for drawing standard junctions and other relevant components (contact tabs, etc)
"""

import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const

from dxfwrite.vector2d import vadd, midpoint ,vsub, vector2angle, magnitude, distance
from dxfwrite.algebra import rotate_2d

from maskLib.Entities import SolidPline, SkewRect, CurveRect, InsideCurve

import math

# ===============================================================================
# contact pad functions (for ground plane)
# ===============================================================================

def JcalcTabDims(gapw=3,gapl=0,tabw=2,tabl=0,taboffs=0,r_out=None,r_ins=None):
    #returns length, half width
    return 2*r_out+gapl+taboffs+2*r_ins+tabl,(gapw/2+r_out+tabw+r_ins)

def JContact_slot(chip,structure,rotation=0,absoluteDimensions=False,gapw=3,gapl=0,tabw=2,tabl=0,taboffs=0,r_out=None,r_ins=None,hflip=False,bgcolor=None,debug=False,**kwargs):
    '''
    Creates shapes forming a negative space puzzle piece slot (tab) with rounded corners, and adjustable angles. 
    No overlap : XOR mode compatible
    Centered on outside midpoint of gap
    
    gap: {width (gapw),height (gapl),r_out}
    tab: {slot width, (tabw),height (tabl), height offset (taboffs),r_ins}

    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,start=structure,direction=rotation)
        else:
            return chip.structure(structure)
    if r_out is None:
        try:
            r_out = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_out = 0
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_ins = 0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    #determine stem and tab lengths
    if absoluteDimensions:
        if gapl >= 2*r_out:
            gapl = gapl-2*r_out
        else:
            print('\x1b[33mWarning:\x1b[0m gap too short in ',chip.chipID,'!')
        if tabl >= 2*r_ins:
            tabl = tabl-2*r_ins
        else:
            print('\x1b[33mWarning:\x1b[0m tab too short in ',chip.chipID,'!')
    
    
    tot_length,half_width = JcalcTabDims(gapw,gapl,tabw,tabl,taboffs,r_out,r_ins)
    
    if hflip:
        struct().shiftPos(tot_length,angle=180)
    
    if taboffs==0:
        theta=90
    else:
        theta = math.degrees(math.atan2(
            (r_ins + r_out)*(taboffs + r_ins + r_out)+ abs(tabw)*math.sqrt(tabw**2 + taboffs*(taboffs + 2*(r_ins + r_out))),
            tabw*(-r_ins - r_out)+(taboffs + r_ins + r_out)*math.sqrt(tabw**2 + taboffs*(taboffs + 2*(r_ins + r_out)))*abs(tabw)/tabw))
    inside_ptx = tot_length-tabl-r_ins*(1+math.sin(math.radians(theta))- (1- math.cos(math.radians(theta)))/math.tan(math.radians(theta)))
    
    chip.add(SolidPline(struct().getPos(),rotation=struct().direction,points=[(gapl+r_out,gapw/2+r_out),
                                                                              (gapl+r_out*(1+math.sin(math.radians(theta))),gapw/2+r_out*(1-math.cos(math.radians(theta)))),
                                                                              (inside_ptx,half_width),(0,half_width),(0,gapw/2+r_out)],bgcolor=bgcolor,**kwargs))
    chip.add(SolidPline(struct().getPos(),rotation=struct().direction,points=[(gapl+r_out,-gapw/2-r_out),
                                                                              (gapl+r_out*(1+math.sin(math.radians(theta))),-gapw/2-r_out*(1-math.cos(math.radians(theta)))),
                                                                              (inside_ptx,-half_width),(0,-half_width),(0,-gapw/2-r_out)],bgcolor=bgcolor,**kwargs))
    
    if r_out>0:
        if debug:
            chip.add(dxf.circle(r_out,struct().getPos((r_out+gapl,gapw/2+r_out)),layer='FRAME',**kwargs))
            chip.add(dxf.circle(r_out,struct().getPos((r_out+gapl,-gapw/2-r_out)),layer='FRAME',**kwargs))
        chip.add(CurveRect(struct().getPos((r_out,gapw/2+r_out)), r_out, r_out,ralign=const.TOP,hflip=True,vflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        chip.add(CurveRect(struct().getPos((r_out,-gapw/2-r_out)), r_out, r_out,ralign=const.TOP,hflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        if gapl > 0:
            chip.add(dxf.rectangle(struct().getPos((r_out,gapw/2)),gapl,r_out,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(struct().getPos((r_out,-gapw/2)),gapl,-r_out,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(CurveRect(struct().getPos((r_out+gapl,gapw/2+r_out)), r_out, r_out,ralign=const.TOP,angle=theta,vflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        chip.add(CurveRect(struct().getPos((r_out+gapl,-gapw/2-r_out)), r_out, r_out,ralign=const.TOP,angle=theta,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
    
    if r_ins>0:
        if debug:
            chip.add(dxf.circle(r_ins,struct().getPos((tot_length-r_ins-tabl,half_width-r_ins)),layer='FRAME',**kwargs))
            chip.add(dxf.circle(r_ins,struct().getPos((tot_length-r_ins-tabl,-half_width+r_ins)),layer='FRAME',**kwargs))
        chip.add(InsideCurve(struct().getPos((tot_length,half_width)), r_ins, rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((tot_length,-half_width)), r_ins, vflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        
        chip.add(InsideCurve(struct().getPos((inside_ptx,half_width)), r_ins,angle=180-theta,hflip=True, rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((inside_ptx,-half_width)), r_ins,angle=180-theta,hflip=True, vflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    
    if hflip:
        struct().shiftPos(0,angle=180)
    else:
        struct().shiftPos(tot_length)
    
    
def JContact_tab(chip,structure,rotation=0,absoluteDimensions=False,stemw=3,steml=0,tabw=2,tabl=0,taboffs=0,r_out=None,r_ins=None,hflip=False,bgcolor=None,debug=False,**kwargs):
    '''
    Creates shapes forming a puzzle piece tab with rounded corners, and adjustable angles. 
    No overlap : XOR mode compatible
    Centered on bottom midpoint of stem
    
    stem: {width (stemw),height (steml),r_out}
    tab: {slot width, (tabw),height (tabl), height offset (taboffs),r_ins}
    
    by default, absolute dimensions are off, so stem / tab lengths are determined by radii. steml and tabl will then determine extra space between rounded corners.
    if absolute dimensions are on, then tab / stem lengths are determined only by steml and tabl.

    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,start=structure,direction=rotation)
        else:
            return chip.structure(structure)
    if r_out is None:
        try:
            r_out = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_out = 0
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_ins = 0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    #determine stem and tab lengths
    if absoluteDimensions:
        if steml >= 2*r_ins:
            steml = steml-2*r_ins
        else:
            print('\x1b[33mWarning:\x1b[0m stem too short in ',chip.chipID,'!')
        if tabl >= 2*r_out:
            tabl = tabl-2*r_out
        else:
            print('\x1b[33mWarning:\x1b[0m tab too short in ',chip.chipID,'!')
    
    tot_length,half_width = JcalcTabDims(stemw,steml,tabw,tabl,taboffs,r_out,r_ins)
    
    if hflip:
        struct().shiftPos(tot_length,angle=180)
    
    if taboffs==0:
        theta=90
    else:
        theta = math.degrees(math.atan2(
            (r_out + r_ins)*(taboffs + r_out + r_ins)+ abs(tabw)*math.sqrt(tabw**2 + taboffs*(taboffs + 2*(r_out + r_ins))),
            tabw*(-r_out - r_ins)+(taboffs + r_out + r_ins)*math.sqrt(tabw**2 + taboffs*(taboffs + 2*(r_out + r_ins)))*abs(tabw)/tabw))
    inside_ptx = r_ins + steml + r_ins*(math.sin(math.radians(theta))- (1- math.cos(math.radians(theta)))/math.tan(math.radians(theta)))
    
    chip.add(SolidPline(struct().getPos(),rotation=struct().direction,points=[(tot_length-tabl-r_out,half_width-r_out),
                                                                              (tot_length-tabl-r_out*(1+math.sin(math.radians(theta))),half_width-r_out*(1-math.cos(math.radians(theta)))),
                                                                              (inside_ptx,stemw/2),(tot_length,stemw/2),(tot_length,half_width-r_out)],bgcolor=bgcolor,**kwargs))
    chip.add(SolidPline(struct().getPos(),rotation=struct().direction,points=[(tot_length-tabl-r_out,-half_width+r_out),
                                                                              (tot_length-tabl-r_out*(1+math.sin(math.radians(theta))),-half_width+r_out*(1-math.cos(math.radians(theta)))),
                                                                              (inside_ptx,-stemw/2),(tot_length,-stemw/2),(tot_length,-half_width+r_out)],bgcolor=bgcolor,**kwargs))
    
    chip.add(dxf.rectangle(struct().getPos(),tot_length,stemw,valign=const.MIDDLE,bgcolor=bgcolor,rotation=struct().direction,**kwargs))
    
    if r_out>0:
        if debug:
            chip.add(dxf.circle(r_out,struct().getPos((tot_length-r_out-tabl,half_width-r_out)),layer='FRAME',**kwargs))
            chip.add(dxf.circle(r_out,struct().getPos((tot_length-r_out-tabl,-half_width+r_out)),layer='FRAME',**kwargs))
            
        chip.add(CurveRect(struct().getPos((tot_length-r_out,half_width-r_out)), r_out, r_out,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        chip.add(CurveRect(struct().getPos((tot_length-r_out,-half_width+r_out)), r_out, r_out,ralign=const.TOP,vflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        if tabl > 0:
            chip.add(dxf.rectangle(struct().getPos((tot_length-r_out,half_width-r_out)),-tabl,r_out,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(struct().getPos((tot_length-r_out,-half_width+r_out)),-tabl,-r_out,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(CurveRect(struct().getPos((2*r_ins + steml + taboffs + r_out,half_width-r_out)), r_out, r_out,ralign=const.TOP,angle=theta,hflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        chip.add(CurveRect(struct().getPos((2*r_ins + steml + taboffs + r_out,-half_width+r_out)), r_out, r_out,ralign=const.TOP,angle=theta,hflip=True,vflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        
        
    if r_ins>0:
        if debug:
            chip.add(dxf.circle(r_ins,struct().getPos((r_ins+steml,stemw/2+r_ins)),layer='FRAME',**kwargs))
            chip.add(dxf.circle(r_ins,struct().getPos((r_ins+steml,-stemw/2-r_ins)),layer='FRAME',**kwargs))
        chip.add(InsideCurve(struct().getPos((0,stemw/2)), r_ins, hflip=True,vflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((0,-stemw/2)), r_ins, hflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        
        chip.add(InsideCurve(struct().getPos((inside_ptx,stemw/2)), r_ins, angle=180-theta,vflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((inside_ptx,-stemw/2)), r_ins, angle=180-theta,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    
    if hflip:
        struct().shiftPos(0,angle=180)
    else:
        struct().shiftPos(tot_length)