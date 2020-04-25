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

from maskLib.utilities import kwargStrip



# ===============================================================================
# global functions to setup global variables in an arbitrary wafer object
# ===============================================================================

def setupXORlayer(wafer,XLAYER='XOR',xcolor=6):
    '''
    Sets a layer for XOR operations on all other layers. 
    OUT = ( LAYER1 or LAYER2 ... or LAYERN ) xor XLAYER 
    '''
    wafer.XLAYER=XLAYER
    wafer.addLayer(XLAYER, xcolor)

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
    
    