# -*- coding: utf-8 -*-
"""
Created on Fri Oct  4 17:29:02 2019

@author: Sasha

Library for drawing standard microwave components (CPW parts, inductors, capacitors etc)
"""

import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.entities import Polyline
from dxfwrite.vector2d import vadd, midpoint ,vsub, vector2angle, magnitude, distance
from dxfwrite.algebra import rotate_2d

from maskLib.Entities import SolidPline, SkewRect, CurveRect, RoundRect, InsideCurve
from maskLib.utilities import kwargStrip

from copy import deepcopy
from matplotlib.path import Path
from matplotlib.transforms import Bbox
import math
from copy import copy

# ===============================================================================
# perforate the ground plane with a grid of squares, which avoid any polylines 
# ===============================================================================

def waffle(chip, grid_x, grid_y=None,width=10,height=None,exclude=None,padx=0,pady=None,bleedRadius=1,layer='0'):
    radius = max(int(bleedRadius),0)
    
    if exclude is None:
        exclude = ['FRAME']
    else:
        exclude.append('FRAME')
        
    if grid_y is None:
        grid_y = grid_x
    
    if height is None:
        height = width
        
    if pady is None:
        pady=padx
        
    nx, ny = list(map(int, [(chip.width) / grid_x, (chip.height) / grid_y]))
    occupied = [[False]*ny for i in range(nx)]
    for i in range(nx):
        occupied[i][0] = True
        occupied[i][-1] = True
    for i in range(ny):
        occupied[0][i] = True
        occupied[-1][i] = True
    
    for e in chip.chipBlock.get_data():
        if isinstance(e.__dxftags__()[0], Polyline):
            if e.layer not in exclude:
                o_x_list = []
                o_y_list = []
                plinePts = [v.__getitem__('location').__getitem__('xy') for v in e.__dxftags__()[0].get_data()]
                plinePts.append(plinePts[0])
                for p in plinePts:
                    o_x, o_y = list(map(int, (p[0] / grid_x, p[1] / grid_y)))
                    if 0 <= o_x < nx and 0 <= o_y < ny:
                        o_x_list.append(o_x)
                        o_y_list.append(o_y)
                        
                        #this will however ignore a rectangle with corners outside the chip...
                if o_x_list:
                    path = Path([[pt[0]/grid_x,pt[1]/grid_y] for pt in plinePts],closed=True)
                    for x in range(min(o_x_list)-1, max(o_x_list)+2):
                        for y in range(min(o_y_list)-1, max(o_y_list)+2):
                            try:
                                if path.contains_point([x+.5,y+.5]):
                                    occupied[x][y]=True
                                elif path.intersects_bbox(Bbox.from_bounds(x,y,1.,1.),filled=True):
                                    occupied[x][y]=True
                            except IndexError:
                                pass
       

    second_pass = deepcopy(occupied)
    for r in range(radius):
        for i in range(nx):
            for j in range(ny):
                if occupied[i][j]:
                    for ip, jp in [(i+1,j), (i-1,j), (i,j+1), (i,j-1)]:
                        try:
                            second_pass[ip][jp] = True
                        except IndexError:
                            pass
        second_pass = deepcopy(second_pass)
   
    for i in range(int(padx/grid_x),nx-int(padx/grid_x)):
        for j in range(int(pady/grid_y),ny-int(pady/grid_y)):
            if not second_pass[i][j]:
                pos = i*grid_x + grid_x/2., j*grid_y + grid_y/2.
                chip.add(dxf.rectangle(pos,width,height,bgcolor=chip.wafer.bg(),halign=const.CENTER,valign=const.MIDDLE,layer=layer) )   

# ===============================================================================
# basic NEGATIVE CPW function definitions
# ===============================================================================


def CPW_straight(chip,structure,length,w=None,s=None,bgcolor=None,**kwargs): #note: uses CPW conventions
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    
    
    chip.add(dxf.rectangle(struct().getPos((0,-w/2)),length,-s,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    chip.add(dxf.rectangle(struct().getPos((0,w/2)),length,s,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=structure,length=length)
        
    
def CPW_taper(chip,structure,length=None,w0=None,s0=None,w1=None,s1=None,bgcolor=None,**kwargs): #note: uses CPW conventions
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w0 is None:
        try:
            w0 = struct().defaults['w']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if s0 is None:
        try:
            s0 = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if w1 is None:
        try:
            w1 = struct().defaults['w']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if s1 is None:
        try:
            s1 = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    #if undefined, make outer angle 30 degrees
    if length is None:
        length = math.sqrt(3)*abs(w0/2+s0-w1/2-s1)
    
    chip.add(SkewRect(struct().getPos((0,-w0/2)),length,s0,(0,w0/2-w1/2),s1,rotation=struct().direction,valign=const.TOP,edgeAlign=const.TOP,bgcolor=bgcolor,**kwargs))
    chip.add(SkewRect(struct().getPos((0,w0/2)),length,s0,(0,w1/2-w0/2),s1,rotation=struct().direction,valign=const.BOTTOM,edgeAlign=const.BOTTOM,bgcolor=bgcolor,**kwargs),structure=structure,length=length)
    
def CPW_stub_short(chip,structure,flipped=False,curve_ins=True,curve_out=True,r_out=None,w=None,s=None,bgcolor=None,**kwargs):
    allow_oversize = (curve_ins != curve_out)
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if r_out is None:
        try:
            if allow_oversize:
                r_out = struct().defaults['r_out']
            else:
                r_out = min(struct().defaults['r_out'],s/2)
        except KeyError:
            print('r_out not defined in ',chip.chipID,'!\x1b[0m')
            r_out=0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    
    if r_out > 0:
        
        dx = 0.
        if flipped:
            if allow_oversize:
                dx = r_out
            else:
                dx = min(s/2,r_out)
        
        if allow_oversize:
            l=r_out
        else:
            l=min(s/2,r_out)

        chip.add(RoundRect(struct().getPos((dx,w/2)),l,s,l,roundCorners=[0,curve_ins,curve_out,0],hflip=flipped,valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(RoundRect(struct().getPos((dx,-w/2)),l,s,l,roundCorners=[0,curve_out,curve_ins,0],hflip=flipped,valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=structure,length=l)
    else:
        CPW_straight(chip,structure,s/2,w=w,s=s,bgcolor=bgcolor,**kwargs)
        
def CPW_stub_open(chip,structure,length=0,r_out=None,r_ins=None,w=None,s=None,flipped=False,bgcolor=None,**kwargs):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID,'!\x1b[0m')
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if length <= 0:
        length = s #length = max(length,s)
    if r_out is None:
        try:
            r_out = struct().defaults['r_out']
        except KeyError:
            print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_out=0
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            #print('r_ins not defined in ',chip.chipID,'!\x1b[0m')
            r_ins=0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    dx = 0.
    if flipped:
        dx = length

    if r_ins > 0:
        chip.add(InsideCurve(struct().getPos((dx,w/2)),r_ins,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((dx,-w/2)),r_ins,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor,**kwargs))

    chip.add(RoundRect(struct().getPos((dx,0)),length,w+2*s,r_out,roundCorners=[0,1,1,0],hflip=flipped,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=structure,length=length)

def CPW_cap(chip,structure,gap,r_ins=None,w=None,s=None,bgcolor=None,angle=90,**kwargs):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID,'!\x1b[0m')
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            #print('r_ins not defined in ',chip.chipID,'!\x1b[0m')
            r_ins=0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()

    if r_ins > 0:
        chip.add(InsideCurve(struct().getPos((0,w/2)),r_ins,rotation=struct().direction + 90,vflip=True,angle=angle,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((0,-w/2)),r_ins,rotation=struct().direction - 90,angle=angle,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((gap,w/2)),r_ins,rotation=struct().direction + 90,angle=angle,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((gap,-w/2)),r_ins,rotation=struct().direction - 90,vflip=True,angle=angle,bgcolor=bgcolor,**kwargs))

    chip.add(dxf.rectangle(struct().start,gap,w+2*s,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=structure,length=gap)

        
def CPW_stub_round(chip,structure,w=None,s=None,round_left=True,round_right=True,flipped=False,bgcolor=None,**kwargs):
    #same as stub_open, but preserves gap width along turn (so radii are defined by w, s)
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    dx = 0.
    if flipped:
        dx = s+w/2

    if False:#round_left and round_right:
        chip.add(CurveRect(struct().getPos((dx,w/2)),s,w/2,angle=180,ralign=const.BOTTOM,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor,**kwargs),structure=structure,length=s+w/2)
    else:
        if round_left:
            chip.add(CurveRect(struct().getPos((dx,w/2)),s,w/2,angle=90,ralign=const.BOTTOM,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor,**kwargs))
        else:
            chip.add(dxf.rectangle(struct().getPos((0,w/2)),s+w/2,s,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(InsideCurve(struct().getPos((flipped and s or w/2,w/2)),w/2,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(struct().getPos((s+w/2-dx,w/2)),-s,-w/2,rotation=struct().direction,halign = flipped and const.RIGHT or const.LEFT, bgcolor=bgcolor,**kwargStrip(kwargs)))
        if round_right:
            chip.add(CurveRect(struct().getPos((dx,-w/2)),s,w/2,angle=90,ralign=const.BOTTOM,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor,**kwargs),structure=structure,length=s+w/2)
        else:
            chip.add(dxf.rectangle(struct().getPos((0,-w/2)),s+w/2,-s,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(InsideCurve(struct().getPos((flipped and s or w/2,-w/2)),w/2,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(struct().getPos((s+w/2-dx,-w/2)),-s,w/2,rotation=struct().direction,halign = flipped and const.RIGHT or const.LEFT, bgcolor=bgcolor,**kwargStrip(kwargs)),structure=structure,length=s+w/2)
    
def CPW_bend(chip,structure,angle=90,CCW=True,w=None,s=None,radius=None,ptDensity=120,bgcolor=None,**kwargs):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('\x1b[33mradius not defined in ',chip.chipID,'!\x1b[0m')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
        
    while angle < 0:
        angle = angle + 360
    angle = angle%360
        
    chip.add(CurveRect(struct().start,s,radius,angle=angle,ptDensity=ptDensity,roffset=w/2,ralign=const.BOTTOM,rotation=struct().direction,vflip=not CCW,bgcolor=bgcolor,**kwargs))
    chip.add(CurveRect(struct().start,s,radius,angle=angle,ptDensity=ptDensity,roffset=-w/2,ralign=const.TOP,valign=const.TOP,rotation=struct().direction,vflip=not CCW,bgcolor=bgcolor,**kwargs))
    struct().updatePos(newStart=struct().getPos((radius*math.sin(math.radians(angle)),(CCW and 1 or -1)*radius*(math.cos(math.radians(angle))-1))),angle=CCW and -angle or angle)

def Wire_bend(chip,structure,angle=90,CCW=True,w=None,radius=None,bgcolor=None,**kwargs):
    #only defined for 90 degree bends
    if angle%90 != 0:
        return
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('\x1b[33mradius not defined in ',chip.chipID,'!\x1b[0m')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
        
    while angle < 0:
        angle = angle + 360
    angle = angle%360
        
    if radius-w/2 > 0:
        chip.add(CurveRect(struct().start,radius-w/2,radius,angle=angle,roffset=-w/2,ralign=const.TOP,valign=const.TOP,rotation=struct().direction,vflip=not CCW,bgcolor=bgcolor,**kwargs))
    for i in range(angle//90):
        chip.add(InsideCurve(struct().getPos(vadd(rotate_2d((radius+w/2,(CCW and 1 or -1)*(radius+w/2)),(CCW and -1 or 1)*math.radians(i*90)),(0,CCW and -radius or radius))),radius+w/2,rotation=struct().direction+(CCW and -1 or 1)*i*90,bgcolor=bgcolor,vflip=not CCW,**kwargs))
    struct().updatePos(newStart=struct().getPos((radius*math.sin(math.radians(angle)),(CCW and 1 or -1)*radius*(math.cos(math.radians(angle))-1))),angle=CCW and -angle or angle)

def CPW_tee(chip,structure,w=None,s=None,radius=None,r_ins=None,w1=None,s1=None,ptDensity=60,bgcolor=None,hflip=False,branch_off=const.CENTER,**kwargs):
    
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID)
    if radius is None:
        try:
            radius = 2*struct().defaults['s']
        except KeyError:
            print('\x1b[33mradius not defined in ',chip.chipID,'!\x1b[0m')
            return
    if r_ins is None: #check if r_ins is defined in the defaults
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError: # quiet catch
            r_ins = None   
    
    #default to left and right branches identical to original structure
    if w1 is None:
        w1 = w
    if s1 is None:
        s1 = s
        
    #clone structure defaults
    defaults1 = copy(struct().defaults)
    #update new defaults if defined
    defaults1.update({'w':w1})
    defaults1.update({'s':s1})
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
        
    #long curves not allowed if gaps differ
    if s!=s1:
        radius = min(abs(radius),min(s,s1))
    
    #assign a inside curve radius if not defined
    if r_ins is None:
        r_ins = radius
    
    s_rad = max(radius,s1)
    
    #figure out if tee is centered, or offset
    if branch_off == const.LEFT:
        struct().translatePos((s_rad+w1/2 - 2*hflip*(s_rad+w1/2),w/2+max(radius,s)),angle=-90)
    elif branch_off == const.RIGHT:
        struct().translatePos((s_rad+w1/2 - 2*hflip*(s_rad+w1/2),-w/2-max(radius,s)),angle=90)

    chip.add(dxf.rectangle(struct().getPos((s_rad+w1 - 2*hflip*(s_rad+w1),0)),hflip and -s1 or s1,2*max(radius,s)+w,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    if s==s1:
        chip.add(CurveRect(struct().getPos((0,-w/2-s)),s,radius,hflip=hflip,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(CurveRect(struct().getPos((0,w/2+s)),s,radius,hflip=hflip,vflip=True,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    else:
        if s1>s:
            chip.add(dxf.rectangle(struct().getPos((0,-w/2)),hflip and s-s1 or s1-s,-s,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(dxf.rectangle(struct().getPos((0,w/2)),hflip and s-s1 or s1-s,s,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(CurveRect(struct().getPos((hflip and s-s1 or s1-s,-w/2-s)),radius,radius,hflip=hflip,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(CurveRect(struct().getPos((hflip and s-s1 or s1-s,w/2+s)),radius,radius,hflip=hflip,vflip=True,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        else:#s1<s
            chip.add(CurveRect(struct().getPos((0,-w/2-radius)),radius,radius,hflip=hflip,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(CurveRect(struct().getPos((0,w/2+radius)),radius,radius,hflip=hflip,vflip=True,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(struct().getPos((0,-w/2-radius)),hflip and -radius or radius,-(s-s1),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(dxf.rectangle(struct().getPos((0,w/2+radius)),hflip and -radius or radius,(s-s1),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    if radius <= min(s,s1) and r_ins > 0:
        #inside edges are square
        chip.add(InsideCurve(struct().getPos((0,w/2+s)),r_ins,hflip=hflip,vflip=True,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((0,-w/2-s)),r_ins,hflip=hflip,vflip=False,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    
    
    if branch_off == const.CENTER:  
        s_l = struct().cloneAlong((s_rad+w1/2 - 2*hflip*(s_rad+w1/2),w/2+max(radius,s)),newDirection=90,defaults=defaults1)
        s_r = struct().cloneAlong((s_rad+w1/2 - 2*hflip*(s_rad+w1/2),-w/2-max(radius,s)),newDirection=-90,defaults=defaults1)
    
        return s_l,s_r
    elif branch_off == const.LEFT:
        s_l = struct().cloneAlong((0,0),newDirection=180)
        struct().translatePos((w/2+max(radius,s),s_rad+w1/2 - 2*hflip*(s_rad+w1/2)),angle=90)
        return s_l
    elif branch_off == const.RIGHT:
        s_r = struct().cloneAlong((0,0),newDirection=180)
        struct().translatePos((w/2+max(radius,s),-s_rad-w1/2 + 2*hflip*(s_rad+w1/2)),angle=-90)
        return s_r

# ===============================================================================
# composite CPW function definitions
# ===============================================================================

def CPW_launcher(chip,struct,l_taper=None,l_pad=0,l_gap=0,padw=300,pads=160,w=None,s=None,r_ins=0,r_out=0,bgcolor=None,**kwargs):
    CPW_stub_open(chip,struct,length=max(l_gap,pads),r_out=r_out,r_ins=r_ins,w=padw,s=pads,flipped=True,**kwargs)
    CPW_straight(chip,struct,max(l_pad,padw),w=padw,s=pads,**kwargs)
    CPW_taper(chip,struct,length=l_taper,w0=padw,s0=pads,**kwargs)

def CPW_taper_cap(chip,structure,gap,width,l_straight=0,l_taper=None,s1=None,**kwargs):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if s1 is None:
        try:
            s = struct().defaults['s']
            w = struct().defaults['w']
            s1 = width*s/w
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID)
            print('\x1b[33ms not defined in ',chip.chipID)
    if l_taper is None:
        l_taper = 3*width
    if l_straight<=0:
        try:
            tap_angle = math.degrees(math.atan(2*l_taper/(width-struct().defaults['w'])))
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID)
            tap_angle = 90
    else:
        tap_angle = 90
        
    CPW_taper(chip,structure,length=l_taper,w1=width,s1=s1,**kwargs)
    if l_straight > 0 :
        CPW_straight(chip,structure,length=l_straight,w=width,s=s1,**kwargs)
    CPW_cap(chip, structure, gap, w=width, s=s1, angle=tap_angle, **kwargs)
    if l_straight > 0 :
        CPW_straight(chip,structure,length=l_straight,w=width,s=s1,**kwargs)
    CPW_taper(chip,structure,length=l_taper,w0=width,s0=s1,**kwargs)
    

def CPW_wiggles(chip,structure,length=None,nTurns=None,minWidth=None,maxWidth=None,CCW=True,start_bend = True,stop_bend=True,w=None,s=None,radius=None,bgcolor=None,**kwargs):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('\x1b[33mradius not defined in ',chip.chipID,'!\x1b[0m')
            return
    #prevent dumb entries
    if nTurns is None:
        nTurns = 1
    elif nTurns < 1:
        nTurns = 1
    #is length constrained?
    if length is not None:
        if nTurns is None:
            nTurns = 1
        h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
        #is width constrained?
        if maxWidth is not None:
            while h>max(maxWidth,radius):
                nTurns = nTurns+1
                h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
        
    if (length is None) or (h is None) or (nTurns is None):
        print('not enough params specified for CPW_wiggles!')
        return
    if start_bend:
        CPW_bend(chip,structure,angle=90,CCW=CCW,w=w,s=s,radius=radius,bgcolor=bgcolor,**kwargs)
        if h > radius:
            CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor,**kwargs)
    else:
        CPW_straight(chip,structure,h,w=w,s=s,bgcolor=bgcolor,**kwargs)
    CPW_bend(chip,structure,angle=180,CCW=not CCW,w=w,s=s,radius=radius,bgcolor=bgcolor,**kwargs)
    CPW_straight(chip,structure,h+radius,w=w,s=s,bgcolor=bgcolor,**kwargs)
    if h > radius:
        CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor,**kwargs)
    CPW_bend(chip,structure,angle=180,CCW=CCW,w=w,s=s,radius=radius,bgcolor=bgcolor,**kwargs)
    if h > radius:
        CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor,**kwargs)
    for n in range(nTurns-1):
        CPW_straight(chip,structure,h+radius,w=w,s=s,bgcolor=bgcolor,**kwargs)
        CPW_bend(chip,structure,angle=180,CCW=not CCW,w=w,s=s,radius=radius,bgcolor=bgcolor,**kwargs)
        CPW_straight(chip,structure,h+radius,w=w,s=s,bgcolor=bgcolor,**kwargs)
        if h > radius:
            CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor,**kwargs)
        CPW_bend(chip,structure,angle=180,CCW=CCW,w=w,s=s,radius=radius,bgcolor=bgcolor,**kwargs)
        if h > radius:
            CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor,**kwargs)
    if stop_bend:
        CPW_bend(chip,structure,angle=90,CCW=not CCW,w=w,s=s,radius=radius,bgcolor=bgcolor,**kwargs)
    else:
        CPW_straight(chip,structure,radius,w=w,s=s,bgcolor=bgcolor,**kwargs)

def CPW_directTo(chip,from_structure,to_structure,to_flipped=True,w=None,s=None,radius=None,CW1_override=None,CW2_override=None,flip_angle=False,debug=False,**kwargs):
    def struct1():
        if isinstance(from_structure,m.Structure):
            return from_structure
        else:
            return chip.structure(from_structure)
    if radius is None:
        try:
            radius = struct1().defaults['radius']
        except KeyError:
            print('\x1b[33mradius not defined in ',chip.chipID,'!\x1b[0m')
            return
    #struct2 is only a local copy
    struct2 = isinstance(to_structure,m.Structure) and to_structure or chip.structure(to_structure)
    if to_flipped:
        struct2.direction=(struct2.direction+180.)%360
    
    CW1 = vector2angle(struct1().getGlobalPos(struct2.start)) < 0
    CW2 = vector2angle(struct2.getGlobalPos(struct1().start)) < 0

    target1 = struct1().getPos((0,CW1 and -2*radius or 2*radius))
    target2 = struct2.getPos((0,CW2 and -2*radius or 2*radius))
    
    #reevaluate based on center positions
    
    CW1 = vector2angle(struct1().getGlobalPos(target2)) < 0
    CW2 = vector2angle(struct2.getGlobalPos(target1)) < 0
    
    if CW1_override is not None:
        CW1 = CW1_override
    if CW2_override is not None:
        CW2 = CW2_override

    center1 = struct1().getPos((0,CW1 and -radius or radius))
    center2 = struct2.getPos((0,CW2 and -radius or radius))
    
    if debug:
        chip.add(dxf.line(struct1().getPos((-3000,0)),struct1().getPos((3000,0)),layer='FRAME'))
        chip.add(dxf.line(struct2.getPos((-3000,0)),struct2.getPos((3000,0)),layer='FRAME'))
        chip.add(dxf.circle(center=center1,radius=radius,layer='FRAME'))
        chip.add(dxf.circle(center=center2,radius=radius,layer='FRAME'))
    
    correction_angle=math.asin(abs(2*radius*(CW1 - CW2)/distance(center2,center1)))
    angle1 = abs(struct1().direction - math.degrees(vector2angle(vsub(center2,center1)))) + math.degrees(correction_angle)
    if flip_angle:
        angle1 = 360-abs(struct1().direction - math.degrees(vector2angle(vsub(center2,center1)))) + math.degrees(correction_angle)
    
    if debug:
        print(CW1,CW2,angle1,math.degrees(correction_angle))
    
    if angle1 > 270:
        if debug:
            print('adjusting to shorter angle')
        angle1 = min(angle1,abs(360-angle1))
    '''
    if CW1 - CW2 == 0 and abs(angle1)>100:
        if abs((struct1().getGlobalPos(struct2.start))[1]) < 2*radius:
            print('adjusting angle')
            angle1 = angle1 + math.degrees(math.asin(abs(2*radius/distance(center2,center1))))
            '''
    CPW_bend(chip,from_structure,angle=angle1,w=w,s=s,radius=radius, CCW=CW1,**kwargs)
    CPW_straight(chip,from_structure,distance(center2,center1)*math.cos(correction_angle),w=w,s=s,**kwargs)
    
    angle2 = abs(struct1().direction-struct2.direction)
    if angle2 > 270:
        angle2 = min(angle2,abs(360-angle2))
    CPW_bend(chip,from_structure,angle=angle2,w=w,s=s,radius=radius,CCW=CW2,**kwargs)

def wiggle_calc(chip,structure,length=None,nTurns=None,maxWidth=None,Width=None,start_bend = True,stop_bend=True,w=None,s=None,radius=None):
    #figure out 
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('\x1b[33mradius not defined in ',chip.chipID,'!\x1b[0m')
            return
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID,'!\x1b[0m')
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    #prevent dumb entries
    if nTurns is None:
        nTurns = 1
    elif nTurns < 1:
        nTurns = 1
    #is length constrained?
    if length is not None:
        if nTurns is None:
            nTurns = 1
        h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
        #is width constrained?
        if Width is not None:
            #maxWidth corresponds to the wiggle width, while Width corresponds to the total width filled
            if maxWidth is not None:
                maxWidth = min(maxWidth,Width)
            else:
                maxWidth = Width
            while h+radius+w/2>maxWidth:
                nTurns = nTurns+1
                h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
    h = max(h,radius)
    return {'nTurns':nTurns,'h':h,'length':length}

def Inductor_wiggles(chip,structure,length=None,nTurns=None,maxWidth=None,Width=None,CCW=True,start_bend = True,stop_bend=True,pad_to_width=False,w=None,s=None,radius=None,bgcolor=None,**kwargs):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('\x1b[33mradius not defined in ',chip.chipID,'!\x1b[0m')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID,'!\x1b[0m')
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    #prevent dumb entries
    if nTurns is None:
        nTurns = 1
    elif nTurns < 1:
        nTurns = 1
    #is length constrained?
    if length is not None:
        if nTurns is None:
            nTurns = 1
        h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
        #is width constrained?
        if Width is not None:
            #maxWidth corresponds to the wiggle width, while Width corresponds to the total width filled
            if maxWidth is not None:
                maxWidth = min(maxWidth,Width)
            else:
                maxWidth = Width
            while h+radius+w/2>maxWidth:
                nTurns = nTurns+1
                h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
    else: #length is not contrained
        h= maxWidth-radius-w/2
    if h < radius:
        print('\x1b[33mWarning:\x1b[0m Wiggles too tight. Adjusting length')
    h = max(h,radius)
    if (h is None) or (nTurns is None):
        print('not enough params specified for CPW_wiggles!')
        return
    pm = (CCW - 0.5)*2
    
    #put rectangles on either side to line up with max width
    if pad_to_width:
        if Width is None:
            print('ERROR: cannot pad to width with Width undefined!')
        if start_bend:
            chip.add(dxf.rectangle(struct().getPos((0,h+radius+w/2)),(2*radius)+(nTurns)*4*radius,Width-(h+radius+w/2),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(dxf.rectangle(struct().getPos((0,-h-radius-w/2)),(stop_bend)*(radius+w/2)+(nTurns)*4*radius + radius-w/2,(h+radius+w/2)-Width,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        else:
            chip.add(dxf.rectangle(struct().getPos((-h-radius-w/2,w/2)),(h+radius+w/2)-Width,(radius-w/2)+(nTurns)*4*radius,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(dxf.rectangle(struct().getPos((h+radius+w/2,-radius)),Width-(h+radius+w/2),(stop_bend)*(radius+w/2)+(nTurns)*4*radius + w/2,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    #begin wiggles
    if start_bend:
        chip.add(dxf.rectangle(struct().getPos((0,pm*w/2)),radius+w/2,pm*(h+radius),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        Wire_bend(chip,structure,angle=90,CCW=CCW,w=w,radius=radius,bgcolor=bgcolor,**kwargs)
        if h > radius:
            chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),h+w/2,pm*(radius-w/2),valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=h-radius)
        else:
            chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),radius+w/2,pm*(radius-w/2),valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    else:
        chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),2*radius+w/2,pm*(radius-w/2),valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=radius)
        #struct().shiftPos(h)
    chip.add(dxf.rectangle(struct().getPos((0,pm*w/2)),-h-max(h,radius)-radius-w/2,pm*(2*radius-w),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    Wire_bend(chip,structure,angle=180,CCW=not CCW,w=w,radius=radius,bgcolor=bgcolor,**kwargs)
    struct().shiftPos(h+radius)
    if h > radius:
        struct().shiftPos(h-radius)
    chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),-h-max(h,radius)-radius-w/2,pm*(-2*radius+w),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    Wire_bend(chip,structure,angle=180,CCW=CCW,w=w,radius=radius,bgcolor=bgcolor,**kwargs)
    if h > radius:
        struct().shiftPos(h-radius)
    for n in range(nTurns-1):
        struct().shiftPos(h+radius)
        chip.add(dxf.rectangle(struct().getPos((0,pm*w/2)),-h-max(h,radius)-radius-w/2,pm*(2*radius-w),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        Wire_bend(chip,structure,angle=180,CCW=not CCW,w=w,radius=radius,bgcolor=bgcolor,**kwargs)
        struct().shiftPos(2*h)
        chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),-h-max(h,radius)-radius-w/2,pm*(-2*radius+w),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        Wire_bend(chip,structure,angle=180,CCW=CCW,w=w,radius=radius,bgcolor=bgcolor,**kwargs)
        struct().shiftPos(h-radius)
    chip.add(dxf.rectangle(struct().getLastPos((-radius-w/2,pm*w/2)),w/2+h,pm*(radius-w/2),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct())
    if stop_bend:
        chip.add(dxf.rectangle(struct().getPos((radius+w/2,-pm*w/2)),h+radius,pm*(radius+w/2),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        Wire_bend(chip,structure,angle=90,CCW=not CCW,w=w,radius=radius,bgcolor=bgcolor,**kwargs)
    else:
        #CPW_straight(chip,structure,radius,w=w,s=s,bgcolor=bgcolor)
        chip.add(dxf.rectangle(struct().getPos((0,pm*w/2)),radius,pm*(radius-w/2),rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=radius)

def JellyfishResonator(chip,structure,width,height,l_ind=None,tiny_cap=False,no_cap=False,w_cap=None,s_cap=None,r_cap=None,w_ind=3,r_ind=6,ialign=const.BOTTOM,nTurns=None,maxWidth=None,CCW=True,bgcolor=None,debug=False,**kwargs):
    #inductor params: wire width = w_ind, radius (sets pitch) = r_ind, total inductor wire length = l_ind. ialign determines where the inductor should align to, (TOP = bunch at capacitor)
    #capacitor params: wire width = w_cap, gap to ground = s_cap, nominal horseshoe bend radius = r_cap (). Width determines overall resonator width assuming jellyfish shape, height determines height of capacitor only
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if r_cap is None:
        try:
            r_cap = struct().defaults['radius']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w_cap is None:
        try:
            w_cap = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID,'!\x1b[0m')
    if s_cap is None:
        try:
            s_cap = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if nTurns is None:
        nTurns = wiggle_calc(chip,struct(),length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/2,w=w_ind,radius=r_ind)['nTurns']
    #override dumb inputs
    r_cap=min(s_cap+w_cap/2,r_cap)
    if height > 2*s_cap+w_cap:
        tiny_cap = False
    height = max(height,2*s_cap+w_cap)
    if maxWidth is not None:
        if maxWidth > (width - w_cap - 2*s_cap)/2 and debug:
            print('Warning: inductor maxWidth ',maxWidth,' is too high! reset to ',(width - w_cap - 2*s_cap)/2)
        maxWidth = min(maxWidth,(width - w_cap - 2*s_cap)/2)

    struct().defaults['w']=w_cap
    struct().defaults['s']=s_cap
    
    #calculate extra length
    inductor_pad = height - w_cap - 3*s_cap - (nTurns+0.5)*4*r_ind
    
    #assume structure starts in correct orientation  
    if no_cap:
        #cover the entire area where the capacitor would be
        #chip.add(dxf.rectangle(struct().start,2*s_cap+w_cap,width - (w_cap+2*s_cap)-w_ind,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        s_0 = struct().cloneAlong(distance=0)
        CPW_stub_open(chip,s_0,w=w_ind,s=(width - (w_cap+2*s_cap)-w_ind)/2,r_ins=w_ind/2,length=2*s_cap+w_cap-w_ind,r_out=0,flipped=True)
        CPW_straight(chip,s_0,w=w_ind,s=(width - (w_cap+2*s_cap)-w_ind)/2,length=w_ind)
    else:
        chip.add(dxf.rectangle(struct().start,s_cap,max((width - 2*(w_cap+2*s_cap)) and not tiny_cap,w_ind+2*s_cap),valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    
    s_r = struct().cloneAlong((s_cap+w_cap/2,-max((width/2 - 2*s_cap - w_cap) and not (tiny_cap or no_cap),w_ind/2+s_cap)),newDirection=-90)
    s_l = struct().cloneAlong((s_cap+w_cap/2,max((width/2 - 2*s_cap - w_cap) and not (tiny_cap or no_cap),w_ind/2+s_cap)),newDirection=90)
    
    if no_cap:
        s_l.shiftPos(min(s_cap+w_cap/2+width,width/2-2*s_cap-w_cap/2-w_ind/2))
        s_r.shiftPos(min(s_cap+w_cap/2+width,width/2-2*s_cap-w_cap/2-w_ind/2))
        #extend outsides with a cpw
        chip.add(RoundRect(s_l.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,0,1,0],valign=const.MIDDLE,rotation=s_l.direction,bgcolor=bgcolor,**kwargs),structure=s_l,length=w_cap/2+s_cap)
        chip.add(RoundRect(s_r.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,1,0,0],valign=const.MIDDLE,rotation=s_r.direction,bgcolor=bgcolor,**kwargs),structure=s_r,length=w_cap/2+s_cap)
    else:
        if height-3*s_cap-w_cap*3/2 > 0:
            #bend capacitor to form jellyfish outline
            CPW_bend(chip,s_l,radius=r_cap,**kwargs)
            CPW_bend(chip,s_r,CCW=False,radius=r_cap,**kwargs)
            CPW_straight(chip,s_l,height-3*s_cap-w_cap*3/2,**kwargs)
            CPW_straight(chip,s_r,height-3*s_cap-w_cap*3/2,**kwargs)
        else:
            #extend capacitor to fit width
            CPW_straight(chip,s_l,min(s_cap+w_cap/2+width*tiny_cap,width/2-2*s_cap-w_cap/2-w_ind/2),**kwargs)
            CPW_straight(chip,s_r,min(s_cap+w_cap/2+width*tiny_cap,width/2-2*s_cap-w_cap/2-w_ind/2),**kwargs)
        if tiny_cap:
            #round off capacitor immediately
            chip.add(InsideCurve(s_l.getLastPos((s_cap,w_cap/2)),s_cap,rotation=s_l.direction,hflip=False,bgcolor=bgcolor,**kwargs))
            chip.add(InsideCurve(s_l.getLastPos((s_cap,-w_cap/2)),s_cap,rotation=s_l.direction,hflip=False,vflip=True,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(s_l.getLastPos((s_cap,0)),width/2-w_ind/2-3*s_cap-w_cap/2,w_cap,valign=const.MIDDLE,rotation=s_l.direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            
            chip.add(InsideCurve(s_r.getLastPos((s_cap,w_cap/2)),s_cap,rotation=s_r.direction,hflip=False,bgcolor=bgcolor,**kwargs))
            chip.add(InsideCurve(s_r.getLastPos((s_cap,-w_cap/2)),s_cap,rotation=s_r.direction,hflip=False,vflip=True,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(s_r.getLastPos((s_cap,0)),width/2-w_ind/2-3*s_cap-w_cap/2,w_cap,valign=const.MIDDLE,rotation=s_r.direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            #extend outsides with a cpw
            chip.add(RoundRect(s_l.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,0,1,0],valign=const.MIDDLE,rotation=s_l.direction,bgcolor=bgcolor,**kwargs),structure=s_l,length=w_cap/2+s_cap)
            chip.add(RoundRect(s_r.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,1,0,0],valign=const.MIDDLE,rotation=s_r.direction,bgcolor=bgcolor,**kwargs),structure=s_r,length=w_cap/2+s_cap)
        else:
            #round off ends of capacitor
            CPW_stub_round(chip,s_l,round_left = (inductor_pad > 0) or (height-3*s_cap-w_cap*3/2 < 0),round_right=False,**kwargs) 
            CPW_stub_round(chip,s_r,round_right = (inductor_pad > 0) or (height-3*s_cap-w_cap*3/2 < 0),round_left=False,**kwargs)
        
    if height-3*s_cap-w_cap*3/2 < 0:
        #move left and right structures where capacitor bend would noramlly end
        s_l.updatePos(newStart=s_l.getPos((-s_cap -w_cap/2,-s_cap-w_cap/2)),angle=-90)
        s_r.updatePos(newStart=s_r.getPos((-s_cap -w_cap/2,s_cap+w_cap/2)),angle=90)
        if width < 2*w_cap + 4*s_cap + 2*maxWidth:
            #inductor is trying to extend into the capacitor gap, but the capacitor doesn't bend around so it's ok.
            s_l.translatePos((0,w_cap/2+s_cap))
            s_r.translatePos((0,-w_cap/2-s_cap))
    
    if inductor_pad < -s_cap-w_cap/2:
        #the inductor is longer than the specified height of capacitor in excess of one outside radius
        if debug:
            print('WARNING: capacitor is not long enough to cover inductor.',inductor_pad)
        if width < 2*w_cap + 4*s_cap + 2*maxWidth:
            #inductor is trying to extend into the capacitor gap, but the capacitor doesn't bend around so it's ok.
            chip.add(dxf.rectangle(s_l.start,-inductor_pad-s_cap-w_cap/2,s_cap+w_cap/2,rotation=s_l.direction,valign=const.BOTTOM,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=s_l,length=-inductor_pad-s_cap-w_cap/2)
            chip.add(dxf.rectangle(s_r.start,-inductor_pad-s_cap-w_cap/2,s_cap+w_cap/2,rotation=s_r.direction,valign=const.TOP,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=s_r,length=-inductor_pad-s_cap-w_cap/2)
        else:
            chip.add(dxf.rectangle(s_l.start,-inductor_pad-s_cap-w_cap/2,2*s_cap+w_cap,rotation=s_l.direction,valign=const.MIDDLE,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=s_l,length=-inductor_pad-s_cap-w_cap/2)
            chip.add(dxf.rectangle(s_r.start,-inductor_pad-s_cap-w_cap/2,2*s_cap+w_cap,rotation=s_r.direction,valign=const.MIDDLE,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=s_r,length=-inductor_pad-s_cap-w_cap/2)
    if inductor_pad < 0:
        if width < 2*w_cap + 4*s_cap + 2*maxWidth:
            #inductor is trying to extend into the capacitor gap, but the capacitor doesn't bend around so it's ok.
            chip.add(RoundRect(s_l.start,w_cap/2+s_cap,s_cap+w_cap/2,w_cap/2+s_cap,roundCorners=[0,0,1,0],valign=const.TOP,rotation=s_l.direction,bgcolor=bgcolor,**kwargs))
            chip.add(RoundRect(s_r.start,w_cap/2+s_cap,s_cap+w_cap/2,w_cap/2+s_cap,roundCorners=[0,1,0,0],valign=const.BOTTOM,rotation=s_r.direction,bgcolor=bgcolor,**kwargs))
        else:
            chip.add(RoundRect(s_l.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,0,1,0],valign=const.MIDDLE,rotation=s_l.direction,bgcolor=bgcolor,**kwargs))
            chip.add(RoundRect(s_r.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,1,0,0],valign=const.MIDDLE,rotation=s_l.direction,bgcolor=bgcolor,**kwargs))
        inductor_pad = inductor_pad + s_cap + w_cap/2 #in case extra length from capacitor stub is too much length
    
    s_0 = struct().cloneAlong((s_cap+w_cap,0))
    s_0.defaults['w']=w_ind
    s_0.defaults['radius']=r_ind
    if no_cap:
        s_0.shiftPos(r_cap-w_cap/2)
    else:
        CPW_stub_short(chip,s_0,s=max(((width - 2*(w_cap+2*s_cap)-w_ind)/2) and not tiny_cap,s_cap),r_out=r_cap-w_cap/2,curve_out=False,flipped=True,**kwargs)
    
    if width < 2*w_cap + 4*s_cap + 2*maxWidth:
        iwidth = width - (w_cap+2*s_cap)-w_ind
    else:
        iwidth = width - 2*(w_cap+2*s_cap)-w_ind
    
    if inductor_pad > 0:
        if ialign is const.BOTTOM:
            CPW_straight(chip,s_0,inductor_pad,s=iwidth/2,**kwargs)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=iwidth/2,**kwargs)
    Inductor_wiggles(chip,s_0,length=l_ind,maxWidth=maxWidth,Width=(iwidth+w_ind)/2,nTurns=nTurns,pad_to_width=True,CCW=CCW,bgcolor=bgcolor,**kwargs)
    if inductor_pad > 0:
        if ialign is const.TOP:
            CPW_straight(chip,s_0,inductor_pad,s=iwidth/2,**kwargs)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=iwidth/2,**kwargs)
    CPW_stub_short(chip,s_0,s=iwidth/2,r_out=r_cap-w_cap/2,curve_out=False,**kwargs)
    #update parent structure position, if callable
    structure.updatePos(s_0.start,newDir=s_0.direction)
    
def DoubleJellyfishResonator(chip,structure,width,height,l_ind,w_cap=None,s_cap=None,r_cap=None,w_ind=3,r_ind=6,ialign=const.BOTTOM,nTurns=None,maxWidth=None,CCW=True,bgcolor=None,**kwargs):
    #inductor params: wire width = w_ind, radius (sets pitch) = r_ind, total inductor wire length = l_ind. ialign determines where the inductor should align to, (TOP = bunch at capacitor)
    #capacitor params: wire width = w_cap, gap to ground = s_cap, nominal horseshoe bend radius = r_cap ()
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if r_cap is None:
        try:
            r_cap = struct().defaults['radius']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w_cap is None:
        try:
            w_cap = struct().defaults['w']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if s_cap is None:
        try:
            s_cap = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if l_ind is not None:
        if nTurns is None:
            nTurns = wiggle_calc(chip,struct(),length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/4,w=w_ind,radius=r_ind)['nTurns']
        else:
            #l_ind given, nTurns given
            nTurns = max(nTurns,wiggle_calc(chip,struct(),length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/4,w=w_ind,radius=r_ind)['nTurns'])
    #override dumb inputs
    r_cap=min(s_cap+w_cap/2,r_cap)
    height = max(height,2*s_cap+w_cap)

    struct().defaults['w']=w_cap
    struct().defaults['s']=s_cap
    
    #calculate extra length
    inductor_pad = height - w_cap - 3*s_cap - (nTurns+0.5)*4*r_ind
    
    #assume structure starts in correct orientation
    chip.add(dxf.rectangle(struct().start,s_cap,width - 2*(w_cap+2*s_cap),valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    
    s_r = struct().cloneAlong((s_cap+w_cap/2,-width/2 + 2*s_cap+w_cap),newDirection=-90)
    s_l = struct().cloneAlong((s_cap+w_cap/2,width/2 - 2*s_cap - w_cap),newDirection=90)
    
    if height-3*s_cap-w_cap*3/2 > 0:
        CPW_bend(chip,s_l,radius=r_cap,**kwargs)
        CPW_bend(chip,s_r,CCW=False,radius=r_cap,**kwargs)
        CPW_straight(chip,s_l,height-3*s_cap-w_cap*3/2,**kwargs)
        CPW_straight(chip,s_r,height-3*s_cap-w_cap*3/2,**kwargs)
    else:
        CPW_straight(chip,s_l,s_cap+w_cap/2,**kwargs)
        CPW_straight(chip,s_r,s_cap+w_cap/2,**kwargs)
    CPW_stub_round(chip,s_l,round_left = (inductor_pad > 0) or (height-3*s_cap-w_cap*3/2 < 0),round_right=False,**kwargs) 
    CPW_stub_round(chip,s_r,round_right = (inductor_pad > 0) or (height-3*s_cap-w_cap*3/2 < 0),round_left=False,**kwargs)
    
    if height-3*s_cap-w_cap*3/2 < 0:
        s_l.updatePos(newStart=s_l.getPos((-s_cap -w_cap/2,-s_cap-w_cap/2)),angle=-90)
        s_r.updatePos(newStart=s_r.getPos((-s_cap -w_cap/2,s_cap+w_cap/2)),angle=90)
    
    s_0 = struct().cloneAlong((s_cap+w_cap,(width - 2*(w_cap+2*s_cap))/4))
    s_0.defaults['w']=w_ind
    s_0.defaults['radius']=r_ind
    CPW_stub_short(chip,s_0,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,r_out=r_cap-w_cap/2,curve_out=False,flipped=True,**kwargs)
    
    s_1 = struct().cloneAlong((s_cap+w_cap,-(width - 2*(w_cap+2*s_cap))/4))
    s_1.defaults['w']=w_ind
    s_1.defaults['radius']=r_ind
    CPW_stub_short(chip,s_1,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,r_out=r_cap-w_cap/2,curve_out=False,flipped=True,**kwargs)
    
    if inductor_pad < -s_cap-w_cap/2:
        #print('WARNING: capacitor is not long enough to cover inductor.')
        chip.add(dxf.rectangle(s_l.start,-inductor_pad-s_cap-w_cap/2,2*s_cap+w_cap,rotation=s_l.direction,valign=const.MIDDLE,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=s_l,length=-inductor_pad-s_cap-w_cap/2)
        chip.add(dxf.rectangle(s_r.start,-inductor_pad-s_cap-w_cap/2,2*s_cap+w_cap,rotation=s_r.direction,valign=const.MIDDLE,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=s_r,length=-inductor_pad-s_cap-w_cap/2)
    if inductor_pad < 0:
        '''
        chip.add(dxf.rectangle(s_l.start,w_cap/2+s_cap,-s_cap-w_cap/2,rotation=s_l.direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        chip.add(dxf.rectangle(s_r.start,w_cap/2+s_cap,s_cap+w_cap/2,rotation=s_r.direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        chip.add(CurveRect(s_l.start,w_cap/2+s_cap,w_cap/2+s_cap,ralign=const.TOP,rotation=s_l.direction,bgcolor=bgcolor,**kwargs),structure=s_l,length=s_cap+w_cap/2)
        chip.add(CurveRect(s_r.start,w_cap/2+s_cap,w_cap/2+s_cap,ralign=const.TOP,rotation=s_r.direction,vflip=True,bgcolor=bgcolor,**kwargs),structure=s_r,length=s_cap+w_cap/2)
        '''
        chip.add(RoundRect(s_l.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,0,1,0],valign=const.MIDDLE,rotation=s_l.direction,bgcolor=bgcolor,**kwargs))
        chip.add(RoundRect(s_r.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,1,0,0],valign=const.MIDDLE,rotation=s_l.direction,bgcolor=bgcolor,**kwargs))
        inductor_pad = inductor_pad + s_cap + w_cap/2 #in case extra length from capacitor stub is too much length
    
    if inductor_pad > 0:
        if ialign is const.BOTTOM:
            CPW_straight(chip,s_0,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,**kwargs)
            CPW_straight(chip,s_1,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,**kwargs)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,**kwargs)
            CPW_straight(chip,s_1,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,**kwargs)
    Inductor_wiggles(chip,s_0,length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/4,nTurns=nTurns,pad_to_width=True,CCW=True,bgcolor=bgcolor,**kwargs)
    Inductor_wiggles(chip,s_1,length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/4,nTurns=nTurns,pad_to_width=True,CCW=False,bgcolor=bgcolor,**kwargs)
    if inductor_pad > 0:
        if ialign is const.TOP:
            CPW_straight(chip,s_0,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,**kwargs)
            CPW_straight(chip,s_1,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,**kwargs)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,**kwargs)
            CPW_straight(chip,s_1,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,**kwargs)
    CPW_stub_short(chip,s_0,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,r_out=r_cap-w_cap/2,curve_out=False,**kwargs)
    CPW_stub_short(chip,s_1,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,r_out=r_cap-w_cap/2,curve_out=False,**kwargs)
    #update parent structure position, if callable
    structure.updatePos(midpoint(s_0.start,s_1.start),newDir=s_0.direction)
    
# ===============================================================================
# basic TWO-LAYER CPS function definitions
# ===============================================================================

    