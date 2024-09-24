#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 31 15:12:01 2021

@author: sasha

Library for drawing resonators (both microwave and mm-wave)
General philosophy:
    - when possible draw everything in one layer
    - for related resonator types, add functionality to existing functions (preserve backwards compatibility)
"""

import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.vector2d import vadd, midpoint


from maskLib.microwaveLib import Strip_bend,Strip_straight,Strip_stub_open,Strip_stub_short
from maskLib.microwaveLib import CPW_bend,CPW_straight,CPW_stub_open,CPW_stub_round,CPW_stub_short
from maskLib.microwaveLib import wiggle_calc,Inductor_wiggles

from maskLib.Entities import SolidPline, SkewRect, CurveRect, RoundRect, InsideCurve
from maskLib.utilities import kwargStrip


# ===============================================================================
# lumped element resonators
# ===============================================================================

def JellyfishResonator(chip,structure,width,height,l_ind=None,tiny_cap=False,no_cap=False,w_cap=None,s_cap=None,w_ind=3,r_ind=6,ialign=const.BOTTOM,nTurns=None,maxWidth=None,CCW=True,bgcolor=None,debug=False,**kwargs):
    #inductor params: wire width = w_ind, radius (sets pitch) = r_ind, total inductor wire length = l_ind. ialign determines where the inductor should align to, (TOP = bunch at capacitor)
    #capacitor params: wire width = w_cap, gap to ground = s_cap, nominal horseshoe bend radius = r_cap (). Width determines overall resonator width assuming jellyfish shape, height determines height of capacitor only
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
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
    #hard-code r_cap
    r_cap=s_cap+w_cap/2
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
        CPW_stub_open(chip,s_0,w=w_ind,s=(width - (w_cap+2*s_cap)-w_ind)/2,r_ins=w_ind/2,length=2*s_cap+w_cap-w_ind,r_out=0,flipped=True,**kwargs)
        CPW_straight(chip,s_0,w=w_ind,s=(width - (w_cap+2*s_cap)-w_ind)/2,length=w_ind,**kwargs)
    else:
        chip.add(dxf.rectangle(struct().start,s_cap,max((width - 2*(w_cap+2*s_cap)) * (not tiny_cap),w_ind+2*s_cap),valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    
    s_r = struct().cloneAlong((s_cap+w_cap/2,-max((width/2 - 2*s_cap - w_cap) * (not (tiny_cap or no_cap)),w_ind/2+s_cap)),newDirection=-90)
    s_l = struct().cloneAlong((s_cap+w_cap/2,max((width/2 - 2*s_cap - w_cap) * (not (tiny_cap or no_cap)),w_ind/2+s_cap)),newDirection=90)
    
    if no_cap:
        s_l.shiftPos(min(s_cap+w_cap/2+width,width/2-2*s_cap-w_cap/2-w_ind/2))
        s_r.shiftPos(min(s_cap+w_cap/2+width,width/2-2*s_cap-w_cap/2-w_ind/2))
        #extend outsides with a cpw
        chip.add(RoundRect(s_l.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,0,1,0],valign=const.MIDDLE,rotation=s_l.direction,bgcolor=bgcolor,**kwargs),structure=s_l,length=w_cap/2+s_cap)
        chip.add(RoundRect(s_r.start,w_cap/2+s_cap,2*s_cap+w_cap,w_cap/2+s_cap,roundCorners=[0,1,0,0],valign=const.MIDDLE,rotation=s_r.direction,bgcolor=bgcolor,**kwargs),structure=s_r,length=w_cap/2+s_cap)
    else:
        if height-3*s_cap-w_cap*3/2 >= 0:
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
            CPW_stub_round(chip,s_l,round_left = (inductor_pad >= 0) or (height-3*s_cap-w_cap*3/2 < 0),round_right=False,**kwargs) 
            CPW_stub_round(chip,s_r,round_right = (inductor_pad >= 0) or (height-3*s_cap-w_cap*3/2 < 0),round_left=False,**kwargs)
        
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
        CPW_stub_short(chip,s_0,s=max(((width - 2*(w_cap+2*s_cap)-w_ind)/2) * (not tiny_cap),s_cap),r_out=r_cap-w_cap/2,curve_out=False,flipped=True,**kwargs)
    
    if width < 2*w_cap + 4*s_cap + 2*maxWidth:
        iwidth = width - (w_cap+2*s_cap)-w_ind
    else:
        iwidth = width - 2*(w_cap+2*s_cap)-w_ind
    
    if inductor_pad > 0:
        if ialign is const.BOTTOM:
            CPW_straight(chip,s_0,inductor_pad,s=iwidth/2,**kwargs)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=iwidth/2,**kwargs)
    Inductor_wiggles(chip,s_0,length=l_ind,maxWidth=maxWidth,Width=(iwidth+w_ind)/2,nTurns=nTurns,pad_to_width=True,CCW=CCW,bgcolor=bgcolor,debug=debug,**kwargs)
    if inductor_pad > 0:
        if ialign is const.TOP:
            CPW_straight(chip,s_0,inductor_pad,s=iwidth/2,**kwargs)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=iwidth/2,**kwargs)
    CPW_stub_short(chip,s_0,s=iwidth/2,r_out=r_cap-w_cap/2,curve_out=False,**kwargs)
    #update parent structure position, if callable
    structure.updatePos(s_0.start,newDir=s_0.direction)
    
def DoubleJellyfishResonator(chip,structure,width,height,l_ind,w_cap=None,s_cap=None,r_cap=None,w_ind=3,r_ind=6,ialign=const.BOTTOM,nTurns=None,maxWidth=None,CCW=True,bgcolor=None,**kwargs):
    #WARNING- untested since 2020, may not work perfectly
    #inductor params: wire width = w_ind, radius (sets pitch) = r_ind, total inductor wire length = l_ind. ialign determines where the inductor should align to, (TOP = bunch at capacitor)
    #capacitor params: wire width = w_cap, gap to ground = s_cap, nominal horseshoe bend radius = r_cap ()
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
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

def CingularResonator(chip,structure,l_ind,w_ind=3,w_cap=None,s_cap=None,w_bridge=None,r_bridge=None,w_taper=6,l_taper=None,r_taper=None,ralign=const.BOTTOM,bgcolor=None,debug=False,**kwargs):
    '''
    Draws a resonator shaped like the cingular logo. 
    l_ind: inductor length
    w_ind: inductor width
    w_cap: equivalent to the fillet radius of inner metal
    s_cap: gap to ground
    w_bridge: overrides overall width of inductor bridge (must satisfy 2*r_bridge+w_taper <= w_bridge)
    r_bridge: overrides flare-out radius of inductor bridge (must satisfy 2*r_bridge + 2*l_taper+l_ind <= s_cap)
    w_taper: width of wide section of inductor
    l_taper: set to a length to override inductor-bridge contact rounding with a taper function (must satisfy 2*l_taper+l_ind <= s_cap)
    r_taper: overrides the inductor-bridge contact rounding radius (must satisfy 2*r_taper+w_ind <= w_taper && 2*r_taper+l_ind <= s_cap)
    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
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
    #assign manual inputs but override dumb inputs       
    l_ind = min(s_cap,l_ind)
    if l_taper is not None and 2*l_taper + l_ind <= s_cap:
        r_taper = 0 #don't round the contact
    else:
        #set l_taper manually, and round the contact
        l_taper = max(min((s_cap-l_ind)/2.0,w_taper/2),0)#default to w_taper/2
        if r_taper is None: r_taper = l_taper #default to l_taper
        r_taper = max(min(r_taper,l_taper,(w_taper-w_ind)/2.0),0)
    
    if w_bridge is not None and w_bridge >= w_taper:
        #w_bridge specified, constrain r_bridge
        if r_bridge is None: r_bridge = (s_cap-l_ind-2*l_taper)/2.0 #default to max space
        r_bridge = max(min(r_bridge,(s_cap-l_ind-2*l_taper)/2.0,(w_bridge-w_taper)/2.0),0)
    else:
        #w_bridge not specified.
        r_bridge = max((s_cap-l_ind-2*l_taper)/2.0,0)
        w_bridge = w_taper+2*r_bridge
    
    #internal variables
    r_0 = w_cap/2 + s_cap/2
    
    #by default the radius is defined as the inner radius
    if ralign == const.MIDDLE:
        dr = 0
    elif ralign == const.TOP: #anchored at TOP
        dr = -s_cap/2.
    else:  # const.BOTTOM (anchored at BOTTOM)
        dr = s_cap/2.
    
    #effective radii 
    r_ins=r_0-dr
    r_out=r_0+dr
    
    #define sub-structures
    offset=2*r_0 + s_cap/2
    struct().shiftPos(offset)
    s_r = struct().cloneAlong((0,w_bridge/2),newDirection=90,defaults={'w':s_cap})
    s_l = struct().cloneAlong((0,-w_bridge/2),newDirection=-90,defaults={'w':s_cap})
    
    #debug
    if debug:
        chip.add(dxf.rectangle(struct().getPos(distance=dr), 2*r_0, 2*r_0+w_bridge,valign=const.MIDDLE,rotation=struct().direction,layer='FRAME'))
    
    #draw center, left right arms
    chip.add(dxf.rectangle(struct().start, s_cap, w_bridge,valign=const.MIDDLE,halign=const.CENTER,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    
    Strip_bend(chip, s_r,CCW=False,radius=r_ins,bgcolor=bgcolor,**kwargs)
    Strip_bend(chip, s_r,CCW=True,angle=270,radius=r_out,bgcolor=bgcolor,**kwargs)
    Strip_bend(chip, s_r,CCW=False,angle=180,radius=r_ins,bgcolor=bgcolor,**kwargs)
    Strip_bend(chip, s_r,CCW=True,angle=270,radius=r_out,bgcolor=bgcolor,**kwargs)
    Strip_bend(chip, s_r,CCW=False,angle=90,radius=r_ins,bgcolor=bgcolor,**kwargs)
    
    Strip_bend(chip, s_l,CCW=True,radius=r_ins,bgcolor=bgcolor,**kwargs)
    Strip_bend(chip, s_l,CCW=False,angle=270,radius=r_out,bgcolor=bgcolor,**kwargs)
    Strip_bend(chip, s_l,CCW=True,angle=180,radius=r_ins,bgcolor=bgcolor,**kwargs)
    Strip_bend(chip, s_l,CCW=False,angle=270,radius=r_out,bgcolor=bgcolor,**kwargs)
    Strip_bend(chip, s_l,CCW=True,angle=90,radius=r_ins,bgcolor=bgcolor,**kwargs)
    
    if r_bridge >0:
        Strip_stub_open(chip,s_r,r_out=r_bridge)
        Strip_stub_open(chip,s_l,r_out=r_bridge)
        
    Strip_stub_short(chip,s_r,r_ins=r_taper,w=l_ind,flipped=True,**kwargs)
    Strip_stub_short(chip,s_l,r_ins=r_taper,w=l_ind,flipped=True,**kwargs)
    Strip_straight(chip,s_r,(w_taper-w_ind)/2.,w=l_ind,**kwargs)
    Strip_straight(chip,s_l,(w_taper-w_ind)/2.,w=l_ind,**kwargs)
    
def SierpinskiResonator(chip,structure,l_ind,w_ind=3,recursions=2,w_cap=None,s_cap=None,w_bridge=None,r_bridge=None,w_taper=6,l_taper=None,r_taper=None,ralign=const.BOTTOM,bgcolor=None,debug=False,**kwargs):
    '''
    Draws a resonator following a modified sierpinski curve. 
    l_ind: inductor length
    w_ind: inductor width
    w_cap: equivalent to the fillet radius of inner metal
    s_cap: gap to ground
    w_bridge: overrides overall width of inductor bridge (must satisfy 2*r_bridge+w_taper <= w_bridge)
    r_bridge: overrides flare-out radius of inductor bridge (must satisfy 2*r_bridge + 2*l_taper+l_ind <= s_cap)
    w_taper: width of wide section of inductor
    l_taper: set to a length to override inductor-bridge contact rounding with a taper function (must satisfy 2*l_taper+l_ind <= s_cap)
    r_taper: overrides the inductor-bridge contact rounding radius (must satisfy 2*r_taper+w_ind <= w_taper && 2*r_taper+l_ind <= s_cap)
    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
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
    #assign manual inputs but override dumb inputs       
    l_ind = min(s_cap,l_ind)
    if l_taper is not None and 2*l_taper + l_ind <= s_cap:
        r_taper = 0 #don't round the contact
    else:
        #set l_taper manually, and round the contact
        l_taper = max(min((s_cap-l_ind)/2.0,w_taper/2),0)#default to w_taper/2
        if r_taper is None: r_taper = l_taper #default to l_taper
        r_taper = max(min(r_taper,l_taper,(w_taper-w_ind)/2.0),0)
    
    if w_bridge is not None and w_bridge >= w_taper:
        #w_bridge specified, constrain r_bridge
        if r_bridge is None: r_bridge = (s_cap-l_ind-2*l_taper)/2.0 #default to max space
        r_bridge = max(min(r_bridge,(s_cap-l_ind-2*l_taper)/2.0,(w_bridge-w_taper)/2.0),0)
    else:
        #w_bridge not specified.
        r_bridge = max((s_cap-l_ind-2*l_taper)/2.0,0)
        w_bridge = w_taper+2*r_bridge
    
    #internal variables
    r_0 = 3*(w_cap/2 + s_cap/2)
    
    #by default the radius is defined as the inner radius
    if ralign == const.MIDDLE:
        dr = 0
    elif ralign == const.TOP: #anchored at TOP
        dr = -s_cap/2.
    else:  # const.BOTTOM (anchored at BOTTOM)
        dr = s_cap/2.
        
    #determine effective radius
    r_eff = r_0 * (2**int(recursions))/(2**(int(recursions)+1)-1)

    #debug
    if debug:
        chip.add(dxf.rectangle(struct().getPos(distance=(dr+s_cap/2)), 2*r_0, 2*r_0+w_bridge,valign=const.MIDDLE,rotation=struct().direction,layer='FRAME'))
    
    #define sub-structures
    offset=s_cap/2 + r_0 - r_0 /(2**(int(recursions)+1)-1)
    struct().shiftPos(offset)
    s_r = struct().cloneAlong((0,w_bridge/2),newDirection=90,defaults={'w':s_cap})
    s_l = struct().cloneAlong((0,-w_bridge/2),newDirection=-90,defaults={'w':s_cap})
    
    #draw center, left right arms
    chip.add(dxf.rectangle(struct().start, s_cap, w_bridge,valign=const.MIDDLE,halign=const.CENTER,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    
    #subfunctions, defined by right hand side (CCW0=True)
    def vertex_out(structure,CCW0,radius,count=0):
        if radius-dr<=0 or radius+dr<=0:    #abort if curve would be too tight
            count=0
        if count <= 0:  # The base case
            #draw curve
            Strip_bend(chip, structure,CCW=CCW0,radius=radius+dr,bgcolor=bgcolor,**kwargs)
        else:
            count -=1
            vertex_ins(structure,CCW0,radius/2.0,count)
            vertex_out(structure,CCW0,radius/2.0,count)
            vertex_out(structure,CCW0,radius/2.0,count)
            vertex_out(structure,CCW0,radius/2.0,count)
            vertex_ins(structure,CCW0,radius/2.0,count)
            
    def vertex_ins(structure,CCW0,radius,count=0):
        if radius-dr<=0 or radius+dr<=0:    #abort if curve would be too tight
            count=0
        if count <=0:   #The base case
            #draw curve
            Strip_bend(chip, structure,CCW=not CCW0,radius=radius-dr,bgcolor=bgcolor,**kwargs)
        else:
            count -=1
            vertex_ins(structure,CCW0,radius/2.0,count)
            vertex_out(structure,CCW0,radius/2.0,count)
            vertex_ins(structure,CCW0,radius/2.0,count)
    
    #0th order is square
    vertex_out(s_r,CCW0=True,radius=r_eff,count=recursions)
    vertex_out(s_r,CCW0=True,radius=r_eff,count=recursions)
    
    vertex_out(s_l,CCW0=False,radius=r_eff,count=recursions)
    vertex_out(s_l,CCW0=False,radius=r_eff,count=recursions)
    
    
    #draw inductor bridge
    if r_bridge >0:
        Strip_stub_open(chip,s_r,r_out=r_bridge)
        Strip_stub_open(chip,s_l,r_out=r_bridge)
        
    Strip_stub_short(chip,s_r,r_ins=r_taper,w=l_ind,flipped=True,**kwargs)
    Strip_stub_short(chip,s_l,r_ins=r_taper,w=l_ind,flipped=True,**kwargs)
    Strip_straight(chip,s_r,(w_taper-w_ind)/2.,w=l_ind,**kwargs)
    Strip_straight(chip,s_l,(w_taper-w_ind)/2.,w=l_ind,**kwargs)
    
    
def HotdogResonator(chip,structure,res_width,l_ind,w_ind=3,w_cap=None,s_cap=None,r_bridge=None,w_taper=6,l_taper=None,r_taper=None,bgcolor=None,debug=False,**kwargs):
    '''
    Draws a resonator shaped like a hotdog.
    res_width: overall width of resonator (must satisfy 2*s_)
    l_ind: inductor length
    w_ind: inductor width
    w_cap: equivalent to the fillet radius of inner metal
    s_cap: gap to ground
    r_bridge: overrides flare-out radius of inductor bridge (must satisfy 2*r_bridge + 2*l_taper+l_ind <= s_cap)
    w_taper: width of wide section of inductor
    l_taper: set to a length to override inductor-bridge contact rounding with a taper function (must satisfy 2*l_taper+l_ind <= s_cap)
    r_taper: overrides the inductor-bridge contact rounding radius (must satisfy 2*r_taper+w_ind <= w_taper && 2*r_taper+l_ind <= s_cap)
    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
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
    #assign manual inputs but override dumb inputs
    
    l_ind = min(s_cap,l_ind)
    if l_taper is not None and 2*l_taper + l_ind <= s_cap:
        r_taper = 0 #don't round the contact
    else:
        #set l_taper manually, and round the contact
        l_taper = max(min((s_cap-l_ind)/2.0,w_taper/2),0)#default to w_taper/2
        if r_taper is None: r_taper = l_taper #default to l_taper
        r_taper = max(min(r_taper,l_taper,(w_taper-w_ind)/2.0),0)
    
    #w_bridge not specified.
    r_bridge = max((s_cap-l_ind-2*l_taper)/2.0,0)
    w_bridge = w_taper+2*r_bridge
    
    res_width=max(res_width,w_bridge+w_cap+2*s_cap)
    straight_length=res_width-(w_bridge+w_cap+2*s_cap)
    r_0=w_cap/2+s_cap/2
    
    #define sub-structures
    offset=s_cap/2
    struct().shiftPos(offset)
    s_r = struct().cloneAlong((0,w_bridge/2+straight_length/2),newDirection=90,defaults={'w':s_cap})
    s_l = struct().cloneAlong((0,-w_bridge/2-straight_length/2),newDirection=-90,defaults={'w':s_cap})
    
    
    #draw center, left right arms
    chip.add(dxf.rectangle(struct().start, s_cap, w_bridge+straight_length,valign=const.MIDDLE,halign=const.CENTER,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    
    Strip_bend(chip, s_r,CCW=True,angle=180,radius=r_0,bgcolor=bgcolor,**kwargs)

    Strip_bend(chip, s_l,CCW=False,angle=180,radius=r_0,bgcolor=bgcolor,**kwargs)
    
    if straight_length>0:
        Strip_straight(chip,s_r,(straight_length)/2.,**kwargs)
        Strip_straight(chip,s_l,(straight_length)/2.,**kwargs)
    
    if r_bridge >0:
        Strip_stub_open(chip,s_r,r_out=r_bridge)
        Strip_stub_open(chip,s_l,r_out=r_bridge)
    
    Strip_stub_short(chip,s_r,r_ins=r_taper,w=l_ind,flipped=True,**kwargs)
    Strip_stub_short(chip,s_l,r_ins=r_taper,w=l_ind,flipped=True,**kwargs)
    Strip_straight(chip,s_r,(w_taper-w_ind)/2.,w=l_ind,**kwargs)
    Strip_straight(chip,s_l,(w_taper-w_ind)/2.,w=l_ind,**kwargs)    
        
    
        
        