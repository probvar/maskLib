#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 14:48:45 2020

@author: sasha
"""
import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const

import maskLib.junctionLib as j
from maskLib.Entities import RoundRect, InsideCurve
from maskLib.microwaveLib import CPW_stub_open, Strip_straight, Strip_bend
from maskLib.junctionLib import DolanJunction, JContact_tab

from maskLib.utilities import kwargStrip



# ===============================================================================
# global functions to setup global variables in an arbitrary wafer object
# ===============================================================================

def setupXORlayer(wafer,XLAYER='XOR',xcolor=6):
    '''
    >>>>>>>>>>>>>>> Deprecated! Use wafer.setupXORlayer instead <<<<<<<<<<<<<<<<<<
    Sets a layer for XOR operations on all other layers. 
    OUT = ( LAYER1 or LAYER2 ... or LAYERN ) xor XLAYER 
    '''
    wafer.XLAYER=XLAYER
    wafer.addLayer(XLAYER, xcolor)

# ===============================================================================
# 3D transmon qubit functions (composite entities)
# ===============================================================================

qubit_defaults= {'sharp_jContactTab':{'r_out':0,'r_ins':0,'taboffs':3,'gapl':0,'tabl':0,'gapw':3,'tabw':2},
                 'sharp_junction':{'jpadr':0}}

def TransmonPad(chip,pos,padwidth=250,padheight=None,padradius=25,tab=False,tabShoulder = False,tabShoulderWidth=30,tabShoulderLength=80,tabShoulderRadius=None,flipped=False,rotation=0,bgcolor=None,**kwargs):
    '''
    Creates a rectangular pad with rounded corners, and a JContactTab on one end (defaults to right)
    No overlap : XOR mode compatible
    
    Optionally set tabShoulder to True to extend a thinner lead from the main contact pad.
    '''
    def struct():
        if isinstance(pos,m.Structure):
            return pos
        elif isinstance(pos,tuple):
            return m.Structure(chip,start=pos,direction=rotation)
        else:
            return chip.structure(pos)
    if tabShoulderRadius is None:
        try:
            tabShoulderRadius = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            tabShoulderRadius = 0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    if padheight is None:
        padheight=padwidth
        
    if padradius is None:
        try:
            padradius = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            padradius = 0
    
    tablength,tabhwidth = j.JcalcTabDims(chip,pos,**kwargs)    
    
    if tab:
        #positive tab
        if not flipped:
            chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=padwidth)
            if tabShoulder:
                chip.add(RoundRect(struct().start,tabShoulderLength,tabShoulderWidth,tabShoulderRadius,roundCorners=[0,1,1,0],valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=tabShoulderLength)
        j.JContact_tab(chip,struct(),hflip = flipped,**kwargs)
        if flipped:
            if tabShoulder:
                chip.add(RoundRect(struct().start,tabShoulderLength,tabShoulderWidth,tabShoulderRadius,roundCorners=[1,0,0,1],valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=tabShoulderLength)
            chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    else:
        #slot
        if not flipped:
            if tabShoulder:
                chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=padwidth)
                chip.add(RoundRect(struct().getPos((0,tabhwidth)),tabShoulderLength,tabShoulderWidth/2 - tabhwidth,min(tabShoulderRadius,(tabShoulderWidth/2 - tabhwidth)/2),roundCorners=[0,0,1,0],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(RoundRect(struct().getPos((0,-tabhwidth)),tabShoulderLength,tabShoulderWidth/2 - tabhwidth,min(tabShoulderRadius,(tabShoulderWidth/2 - tabhwidth)/2),roundCorners=[0,1,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(dxf.rectangle(struct().start,tabShoulderLength-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=tabShoulderLength-tablength)
            else:
                chip.add(RoundRect(struct().getPos((0,tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[0,0,1,1],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(RoundRect(struct().getPos((0,-tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[1,1,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(dxf.rectangle(struct().start,padwidth-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=padwidth-tablength)
        j.JContact_slot(chip,struct(),hflip = not flipped,**kwargs)
        if flipped:
            if tabShoulder:
                chip.add(RoundRect(struct().getPos((-tablength,tabhwidth)),tabShoulderLength,tabShoulderWidth/2 - tabhwidth,min(tabShoulderRadius,(tabShoulderWidth/2 - tabhwidth)/2),roundCorners=[0,0,0,1],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(RoundRect(struct().getPos((-tablength,-tabhwidth)),tabShoulderLength,tabShoulderWidth/2 - tabhwidth,min(tabShoulderRadius,(tabShoulderWidth/2 - tabhwidth)/2),roundCorners=[1,0,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(dxf.rectangle(struct().start,tabShoulderLength-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=tabShoulderLength-tablength)
                chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=padwidth)
            else:
                chip.add(RoundRect(struct().getPos((-tablength,tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[0,0,1,1],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(RoundRect(struct().getPos((-tablength,-tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[1,1,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(dxf.rectangle(struct().start,padwidth-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))



def Transmon3D(chip,pos,rotation=0,bgcolor=None,padh=200,padh2=200,padw=3000,padw2=3000,
               taperw=0,taperw2=0,leadw=85,leadw2=85,leadh=20,leadh2=20,separation=20,
               r_out=0.75,r_ins=0.75,taboffs=-0.05,steml=1.5,gapl=1.5,tabl=2,stemw=3,gapw=3,tabw=0.5,
               jpadTaper=10,jpadw=25,jpadh=16,jpadSeparation=28,jfingerl=4.5,jfingerex=1.5,jleadw=1,**kwargs):
    '''
    Generates transmon paddles with a manhattan junction at the center. 
    Junction and contact tab parameters are monkey patched to Junction function through kwargs.
    
    padh, padh2: left,right transmon pad height
    padw, padw2: left,right  transmon pad width (or length)
    taperw, taperw2: left,right taper length from pad to lead
    leadw, leadw2: left,right lead width
    leadh, leadh2: left,right lead height
    separation: separation between leads (where junction goes)

    '''
    thisStructure = None
    if isinstance(pos,tuple):
        thisStructure = m.Structure(chip,start=pos,direction=rotation)
        
    def struct():
        if isinstance(pos,m.Structure):
            return pos
        elif isinstance(pos,tuple):
            return thisStructure
        else:
            return chip.structure(pos)
     
    if bgcolor is None: #color for junction, not undercut
        bgcolor = chip.wafer.bg()
    
    j_struct = struct().start
        
    #start where the junction is, move left to where left pad starts
    struct().shiftPos(-separation/2-leadw-padw)
    j.JSingleProbePad(chip,struct(),padwidth=padw,padheight=padh,tabShoulder=True,tabShoulderWidth=leadh,tabShoulderLength=leadw,flipped=False,padradius=None,
                      r_out=r_out,r_ins=r_ins,taboffs=taboffs,gapl=gapl,tabl=tabl,gapw=gapw,tabw=tabw,absoluteDimensions=True,**kwargs)
    struct().shiftPos(separation)
    j.JSingleProbePad(chip,struct(),padwidth=padw2,padheight=padh2,tabShoulder=True,tabShoulderWidth=leadh2,tabShoulderLength=leadw2,flipped=True,padradius=None,
                      r_out=r_out,r_ins=r_ins,taboffs=taboffs,gapl=gapl,tabl=tabl,gapw=gapw,tabw=tabw,absoluteDimensions=True,**kwargs)
                    #r_out=0,r_ins=0,taboffs=3,gapl=0,tabl=0,gapw=gapw,tabw=2,absoluteDimensions=True,**kwargs)
    
    #write the junction
    j.ManhattanJunction(chip, j_struct,rotation=struct().direction,jpadTaper=jpadTaper,jpadw=jpadw,jpadh=jpadh,separation=jpadSeparation+jpadTaper,jfingerl=jfingerl,jfingerex=jfingerex,leadw=jleadw,**kwargs)
    
    

# ===============================================================================
# Planar (2D) qubit functions (composite entities)
# ===============================================================================

def Hamburgermon(chip,pos,rotation=0,
                   qwidth=1120,qheight=795,qr_out=200, minQbunToGnd=100,
                   qbunwidth=960,qbunthick=0,qbunr=60,qbunseparation=69.3751,
                   qccap_padw=40,qccap_padl=170,qccap_padr_out=10,qccap_padr_ins=4.5,qccap_gap=30,
                   qccapl=210,qccapw=0,qccapr_ins=30,qccapr_out=15,
                   qccap_steml=70,qccap_stemw=None,
                   XLAYER=None,bgcolor=None,**kwargs):
    '''
    Generates a hamburger shaped qubit. Needs XOR layers to define base metal layer. 
    Junction and contact tab parameters are monkey patched to Junction function through kwargs.
    '''
    thisStructure = None
    if isinstance(pos,tuple):
        thisStructure = m.Structure(chip,start=pos,direction=rotation)
        
    def struct():
        if isinstance(pos,m.Structure):
            return pos
        elif isinstance(pos,tuple):
            return thisStructure
        else:
            return chip.structure(pos)
        
    if bgcolor is None: #color for junction, not undercut
        bgcolor = chip.wafer.bg()
    
    #get layers from wafer
    if XLAYER is None:
        try:
            XLAYER = chip.wafer.XLAYER
        except AttributeError:
            chip.wafer.setupXORlayer()
            XLAYER = chip.wafer.XLAYER
            
    if qccap_stemw is None:
        try:
            qccap_stemw = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID,'!\x1b[0m')
            qccap_stemw = 6
    
    #increase thicknesses if radii are too large
    qccapw = max(qccapw,2*qccapr_out)
    qbunthick = max(qbunthick,2*qbunr)
    qccap_padw = max(qccap_padw,2*qccap_padr_out)
    qccap_padl = max(qccap_padl,2*qccap_padr_out)
    
    #increase qubit width and height if buns are too close to ground
    qwidth = max(qwidth,qbunwidth+2*minQbunToGnd)
    qheight = max(qheight,max(qccap_steml+qccap_padl,qccap_gap+qccapl)+2*max(2*qbunr,qbunthick)+qbunseparation+minQbunToGnd)
    
    #cache junction position and figure out if we're using structures or not
    jxpos = qccap_steml+qccap_padl+qccap_gap+qbunthick+qbunseparation/2
    if thisStructure is not None:
        #not using structures
        struct().shiftPos(-jxpos)
    centerPos = struct().getPos((jxpos,0))
    
    #hole in basemetal (negative)
    chip.add(RoundRect(struct().start,qheight,qwidth,qr_out,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    
    #xor defined qubit (positive)
    if qccap_padr_ins >0 and qccap_stemw+2*qccap_padr_ins < qccap_padw - 2*qccap_padr_out:
        chip.add(InsideCurve(struct().getPos((qccap_steml,qccap_stemw/2)),qccap_padr_ins,vflip=True,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        chip.add(InsideCurve(struct().getPos((qccap_steml,-qccap_stemw/2)),qccap_padr_ins,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        
    chip.add(dxf.rectangle(struct().start,qccap_steml,qccap_stemw,valign=const.MIDDLE,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargStrip(kwargs)))
    chip.add(RoundRect(struct().getPos((qccap_steml,0)),qccap_padl,qccap_padw,qccap_padr_out,valign=const.MIDDLE,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
    
    if qccapr_ins > 0:
        chip.add(InsideCurve(struct().getPos((jxpos-qbunseparation/2-qbunthick,qccap_padw/2+qccap_gap)),qccapr_ins,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        chip.add(InsideCurve(struct().getPos((jxpos-qbunseparation/2-qbunthick,qccap_padw/2+qccap_gap+qccapw)),qccapr_ins,vflip=True,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        
        chip.add(InsideCurve(struct().getPos((jxpos-qbunseparation/2-qbunthick,-qccap_padw/2-qccap_gap)),qccapr_ins,vflip=True,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        chip.add(InsideCurve(struct().getPos((jxpos-qbunseparation/2-qbunthick,-qccap_padw/2-qccap_gap-qccapw)),qccapr_ins,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        
    chip.add(RoundRect(struct().getPos((jxpos-qbunseparation/2-qbunthick,qccap_padw/2+qccap_gap)),qccapl,qccapw,qccapr_out,roundCorners=[1,0,0,1],halign=const.RIGHT,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
    chip.add(RoundRect(struct().getPos((jxpos-qbunseparation/2-qbunthick,-qccap_padw/2-qccap_gap)),qccapl,qccapw,qccapr_out,roundCorners=[1,0,0,1],halign=const.RIGHT,vflip=True,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
    
    j.JProbePads(chip, centerPos,rotation=struct().direction,padwidth=qbunthick,padheight=qbunwidth,padradius=qbunr,separation=qbunseparation,
                 layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs)
    
    j.ManhattanJunction(chip, centerPos, rotation=struct().direction,separation=qbunseparation, **kwargs)
    
    return centerPos,struct().direction
    
def Elephantmon(
    chip, structure, rotation=0, totalw=0, totall=0,
    tpad_width=200, tpad_height=300, tpad_gap_gnd=50,
    tpad_gap=100, rpad=10, **kwargs):

    """
    Generates an Elephantmon, which is similar to the Hamburgermon but does NOT use
    an XOR layer and uses a Dolan junction. Additional params can be passed to
    junctions used kwargs.
    If totalw, totall are specified to be non-zero, tpad_width and tpad_height are
        re-calculated based on tpad_gap and tpad_gap_gnd.
    """
    s = structure.clone()
    s.direction += rotation

    if totalw > 0:
        tpad_width = totalw-2*tpad_gap_gnd
    if totall > 0:
        tpad_height = (totall-2*tpad_gap_gnd-tpad_gap)/2
    

    s.shiftPos(tpad_width/2+tpad_gap_gnd)

    s_right = s.clone()
    s_right.direction += 90
    CPW_stub_open(chip, s_right, tpad_gap/2, r_ins=rpad, w=tpad_width, s=tpad_gap_gnd, flipped=True, **kwargs)
    JContact_tab(chip, s_right)

    s_right = s.cloneAlongLast()
    s_right.shiftPos(tpad_gap_gnd/2)
    s_right.direction += 90
    s_right.shiftPos(tpad_gap/2)
    Strip_straight(chip, s_right, length=tpad_height-rpad, w=tpad_gap_gnd, **kwargs)
    Strip_bend(chip, s_right, CCW=True, w=tpad_gap_gnd, radius=rpad+tpad_gap_gnd/2, **kwargs)
    Strip_straight(chip, s_right, length=tpad_width-2*rpad, w=tpad_gap_gnd, **kwargs)
    Strip_bend(chip, s_right, CCW=True, w=tpad_gap_gnd, radius=rpad+tpad_gap_gnd/2, **kwargs)
    Strip_straight(chip, s_right, length=tpad_height-rpad, w=tpad_gap_gnd, **kwargs)

    s_left = s.clone()
    s_left.direction -= 90
    CPW_stub_open(chip, s_left, tpad_gap/2, r_ins=rpad, w=tpad_width, s=tpad_gap_gnd, flipped=True, **kwargs)
    JContact_tab(chip, s_left, **kwargs)

    s_left = s.cloneAlongLast()
    s_left.shiftPos(tpad_gap_gnd/2)
    s_left.direction -= 90
    s_left.shiftPos(tpad_gap/2)
    Strip_straight(chip, s_left, length=tpad_height-rpad, w=tpad_gap_gnd, **kwargs)
    Strip_bend(chip, s_left, CCW=False, w=tpad_gap_gnd, radius=rpad+tpad_gap_gnd/2, **kwargs)
    Strip_straight(chip, s_left, length=tpad_width-2*rpad, w=tpad_gap_gnd, **kwargs)
    Strip_bend(chip, s_left, CCW=False, w=tpad_gap_gnd, radius=rpad+tpad_gap_gnd/2, **kwargs)
    Strip_straight(chip, s_left, length=tpad_height-rpad, w=tpad_gap_gnd, **kwargs)

    s.direction -= 90
    DolanJunction(chip, s, junctionl=tpad_gap, **kwargs)