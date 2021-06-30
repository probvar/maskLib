#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 17 14:38:27 2021

@author: sasha
"""
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.vector2d import vadd

from maskLib.utilities import kwargStrip

# ===============================================================================
#  MARKER FUNCTIONS
# ===============================================================================

#Define High Visiblity Marker Function for numbers 0-9
#High visibility markers composed of a grid of six squares
def HiVisMarker09(dwg,xpos,ypos,number,width,bg=None,**kwargs):
    shapes = [[],  [[0,0]],  [[0,0],[1,1]],    [[0,0],[1,1],[0,1]],  [[0,0],[0,1],[2,0],[2,1]],
             [[0,1],[1,0],[2,1]],  [[0,0],[1,0],[2,0],[1,1]],   [[0,0],[0,1],[1,0],[1,1],[2,1]], [[0,0],[0,1],[1,0],[1,1]],
             [[0,0],[1,0],[1,1],[2,1]]]
    number = number % len(shapes)
    for v in shapes[number]:
        dwg.add(dxf.rectangle((xpos+v[0]*width,ypos+v[1]*width),width,width,bgcolor=bg,**kwargs))
        
def MarkerRect(w,pos,width,height,bgcolor=None,layer=None,**kwargs):
    if layer is None:
        layer = w.defaultLayer
    else:
        layer = w.lyr(layer)
    if bgcolor is None:
        bgcolor = w.bg(layer)
    w.add(dxf.rectangle(pos,width,height,valign=const.MIDDLE,halign=const.CENTER,bgcolor=bgcolor,layer=layer,**kwargStrip(kwargs)))
    
def MarkerSquare(w,pos,width=80,bgcolor=None,layer=None,**kwargs):
    MarkerRect(w,pos,width,width,bgcolor=bgcolor,layer=layer,**kwargs)

def MarkerCross(w,pos,size=(200,200),linewidth=80,bgcolor=None,layer=None,**kwargs):
    if layer is None:
        layer = w.defaultLayer
    else:
        layer = w.lyr(layer)
    if bgcolor is None:
        bgcolor = w.bg(layer)
    w.add(dxf.rectangle(pos,size[0],linewidth,valign=const.MIDDLE,halign=const.CENTER,bgcolor=bgcolor,layer=layer,**kwargStrip(kwargs)))
    w.add(dxf.rectangle(vadd(pos,(0,linewidth/2)),linewidth,size[1]/2-linewidth/2,valign=const.BOTTOM,halign=const.CENTER,bgcolor=bgcolor,layer=layer,**kwargStrip(kwargs)))
    w.add(dxf.rectangle(vadd(pos,(0,-linewidth/2)),linewidth,size[1]/2-linewidth/2,valign=const.TOP,halign=const.CENTER,bgcolor=bgcolor,layer=layer,**kwargStrip(kwargs)))