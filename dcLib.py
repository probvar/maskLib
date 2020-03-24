# -*- coding: utf-8 -*-
"""
Created on Fri Oct  4 17:29:02 2019

@author: Sasha

Library for drawing standard microwave components (CPW parts, inductors, capacitors etc)
"""

import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const


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