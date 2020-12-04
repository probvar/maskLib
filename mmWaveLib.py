# -*- coding: utf-8 -*-
"""
Created on Tue Mar 26 13:46:48 2019

@author: sasha
"""
import numpy as np
import math

import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const

from maskLib.Entities import SolidPline, RoundRect, SkewRect
from maskLib.utilities import kwargStrip


# ===============================================================================
#  BLANK CENTERED WR10 CHIP CLASS  
#       chip with a rectangle marking dimensions of wr10 waveguide
# ===============================================================================

class BlankCenteredWR10(m.Chip):
    def __init__(self,wafer,chipID,layer,offset=(0,0)):
        m.Chip.__init__(self,wafer,chipID,layer)
        self.center = self.centered(offset)
        if wafer.frame:
            self.add(dxf.rectangle(self.centered((-1270,-635)),2540,1270,layer=wafer.lyr('FRAME')))  

# ===============================================================================
#  VIVALDI TAPER CHIP CLASS + subclasses 
#       chip designed for 1st version of transverse holder
#       two structures on either end designed for vivaldi taper functions
#       NOTE: chip size still needs to be set in the wafer settings, this just determines structure location
# ===============================================================================


class VivaldiTaperChip(m.Chip):
    def __init__(self,wafer,chipID,layer,left=False,right=False,defaults=None,structures=None):
        m.Chip.__init__(self,wafer,chipID,layer)
        self.defaults = {'w':80, 's':5, 'radius':25,'r_out':0,'r_ins':0}
        if defaults is not None:
            #self.defaults = defaults.copy()
            for d in defaults:
                self.defaults[d]=defaults[d]
        if structures is not None:
            #override default structures
            self.structures = structures
        else:
            self.structures = [#hardwired structures
                    m.Structure(self,start=(0,self.height/2),direction=0,defaults=self.defaults),
                    m.Structure(self,start=(self.width,self.height/2),direction=180,defaults=self.defaults)]
        if wafer.frame:
            self.add(RoundRect(self.centered((-3450/2,0)),870,1270,400,roundCorners=[0,1,1,0],valign=const.MIDDLE,layer=wafer.lyr('FRAME')))
            self.add(RoundRect(self.centered((3450/2,0)),870,1270,400,roundCorners=[1,0,0,1],halign=const.RIGHT,valign=const.MIDDLE,layer=wafer.lyr('FRAME')))
            self.add(RoundRect(self.center,2270,2110,400,halign=const.CENTER,valign=const.MIDDLE,layer=wafer.lyr('FRAME')))
        
        if left:
            Slot_vivaldi_taper(self,0)
        if right:
            Slot_vivaldi_taper(self,1)
            
class VivaldiTaperChipThru(VivaldiTaperChip):
    def __init__(self,wafer,chipID,layer,defaults=None,structures=None):
        VivaldiTaperChip.__init__(self,wafer,chipID,layer,left=True,right=True,defaults=defaults,structures=structures)
        Slot_straight(self,0,self.width-2*870)
        
class VivaldiTaperChipReflect(VivaldiTaperChip):
    def __init__(self,wafer,chipID,layer,defaults=None,structures=None):
        VivaldiTaperChip.__init__(self,wafer,chipID,layer,left=True,right=False,defaults=defaults,structures=structures)
        Slot_straight(self,0,(self.width-2*870)/2)

# ===============================================================================
# Basic slot functions
# ===============================================================================

def Slot_vivaldi_taper(chip,structure,length=870,w0=1270,w1=None,overhang=70,bgcolor=None,ptDensity=100,**kwargs): #note: uses CPW conventions
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
    if w1 is None:
        try:
            w1 = struct().defaults['w']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
            
    chip.add(SkewRect(struct().start,overhang,w0+2*overhang,(0,0),w0,halign=const.RIGHT,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    chip.add(SolidPline(struct().start,rotation=struct().direction,bgcolor=bgcolor,
                       points=[(x*length,(w0/2-w1/2)*(x*math.sqrt(2-x**2))-w0/2) for x in np.arange(0,1+1/ptDensity,1/ptDensity)]+
                       [((1-x)*length,w0/2-(w0/2-w1/2)*((1-x)*math.sqrt(2-(1-x)**2))) for x in np.arange(0,1+1/ptDensity,1/ptDensity)],
                       solidFillQuads=True,**kwargs),structure=structure,length=length)
    
    
def Slot_straight(chip,structure,length,w=None,bgcolor=None,**kwargs): #note: uses CPW conventions
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
    
    chip.add(dxf.rectangle(struct().start,length,w,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=structure,length=length)


# ===============================================================================
# old function definitions
# ===============================================================================

#CPS dipole resonator
def CPS_Resonator(dwg,xy,w,s,L_res,L_rabbit,bg=None,w_rabbit=None):
    if w_rabbit is None:
        w_rabbit = w
    #draw a cps resonator, dipole origin centered on (x,y) facing right
    dwg.add(dxf.rectangle((xy[0],xy[1]+s/2),L_res,w,bgcolor=bg))
    dwg.add(dxf.rectangle((xy[0],xy[1]-s/2),L_res,-w,bgcolor=bg))
    dwg.add(dxf.rectangle((xy[0]+L_res,xy[1]-s/2-w),w,2*w+s,bgcolor=bg))
    if L_rabbit > 0:
        dwg.add(dxf.rectangle((xy[0],xy[1]+s/2+w),w_rabbit,L_rabbit+(w_rabbit - w),bgcolor=bg))
        dwg.add(dxf.rectangle((xy[0],xy[1]-s/2-w),w_rabbit,-L_rabbit-(w_rabbit - w),bgcolor=bg))
    
#CPS dipole resonator with rounded edges
def CPS_Rounded(dwg,xy,w,s,L_res,L_rabbit,r_ins,RL,line_color,half=False,curve_pts=30,w_rabbit=None):
    
    if w_rabbit is None:
        w_rabbit = w
    #print(half)
    #RL = 1 if right, -1 if left
        
    q = m.transformedQuadrants(LR=RL)
    #draw a cps resonator, dipole origin centered on (x,y) facing right
    pline = dxf.polyline(points = [(xy[0]+L_res*RL,xy[1])],color = line_color,flags=0)#1
    pline.add_vertices(r_ins > 0 and m.corner((xy[0]+L_res*RL,xy[1]+s/2),q[1],-1*RL,r_ins,curve_pts//2) or [(xy[0]+L_res*RL,xy[1]+s/2)])#2
    if L_rabbit >= w/3: #draw top antenna
        pline.add_vertices(half and [(xy[0]+RL*w_rabbit/2,xy[1] + s/2)] or m.corner((xy[0],xy[1] + s/2),q[3],1*RL,w_rabbit,curve_pts))#3
        pline.add_vertices(half and [(xy[0]+RL*w_rabbit/2,xy[1] + s/2 + w_rabbit + L_rabbit)] or m.corner((xy[0],xy[1] + s/2 + w_rabbit + L_rabbit),q[2],1*RL,w_rabbit/3,curve_pts))#4
        pline.add_vertices(m.corner((xy[0]+w_rabbit*RL,xy[1] + s/2 + w_rabbit + L_rabbit),q[1],1*RL,w_rabbit/3,curve_pts))#5
        pline.add_vertices(r_ins > 0 and m.corner((xy[0]+w_rabbit,xy[1]+s/2+w),q[3],-1*RL,r_ins,curve_pts//2) or [(xy[0]+w_rabbit*RL,xy[1]+s/2+w)])#6
    else: #top stub only
        pline.add_vertices(half and [(xy[0]+RL*w/2,xy[1] + s/2)] or m.corner((xy[0],xy[1] + s/2),q[3],1*RL,w/3,curve_pts))#3
        pline.add_vertices(half and [(xy[0]+RL*w/2,xy[1] + s/2 + w)] or m.corner((xy[0],xy[1] + s/2 + w),q[2],1*RL,w/3,curve_pts))#4
    pline.add_vertices(m.corner((xy[0]+ (L_res + w)*RL,xy[1] + s/2 + w),q[1],1*RL,w,curve_pts))#7
    pline.add_vertices(m.corner((xy[0]+ (L_res + w)*RL,xy[1] - s/2 - w),q[4],1*RL,w,curve_pts))#8
    if L_rabbit >= w/3: #draw bottom antenna
        pline.add_vertices(r_ins > 0 and m.corner((xy[0]+w_rabbit*RL,xy[1]-s/2-w),q[2],-1*RL,r_ins,curve_pts//2) or [(xy[0]+w_rabbit*RL,xy[1]-s/2-w)])#9
        pline.add_vertices(m.corner((xy[0]+w_rabbit*RL,xy[1] - s/2 - w_rabbit - L_rabbit),q[4],1*RL,w_rabbit/3,curve_pts))#10
        pline.add_vertices(half and [(xy[0]+RL*w_rabbit/2,xy[1] - s/2 - w_rabbit - L_rabbit)] or m.corner((xy[0],xy[1] - s/2 - w_rabbit - L_rabbit),q[3],1*RL,w_rabbit/3,curve_pts))#11
        pline.add_vertices(half and [(xy[0]+RL*w_rabbit/2,xy[1] - s/2)] or m.corner((xy[0],xy[1] - s/2),q[2],1*RL,w_rabbit,curve_pts))#12
    else: #bottom stub only
        pline.add_vertices(half and [(xy[0]+RL*w/2,xy[1] - s/2 - w)] or m.corner((xy[0],xy[1] - s/2 - w),q[3],1*RL,w/3,curve_pts))#11
        pline.add_vertices(half and [(xy[0]+RL*w/2,xy[1] - s/2)] or m.corner((xy[0],xy[1] - s/2),q[2],1*RL,w/3,curve_pts))#12
    pline.add_vertices(r_ins > 0 and m.corner((xy[0]+L_res*RL,xy[1]-s/2),q[4],-1*RL,r_ins,curve_pts//2) or [(xy[0]+L_res*RL,xy[1]-s/2)])#13
    pline.close()
    dwg.add(pline)

#Vertical CPS resonator, no dipole antenna, ends rotated 90deg for coupling. Rounded edges.
def Paperclip_Rounded(dwg,xy,w,s,L_res,gap,r_ins,UD,line_color,curve_pts=30):
    #UD = 1 if gap on top, -1 if gap on bottom
    RL=1
    q = m.transformedQuadrants(UD=UD)
    #draw 
    pline = dxf.polyline(points = [(xy[0],xy[1])],color = line_color)
    pline.add_vertices(r_ins > 0 and m.corner((xy[0]-RL*s/2,xy[1]),q[2],-1*UD,r_ins,curve_pts//2) or [(xy[0]-RL*s/2,xy[1])])
    pline.add_vertices(r_ins > 0 and m.corner((xy[0]-RL*s/2,xy[1]-UD*L_res),q[3],-1*UD,r_ins,curve_pts//2) or [(xy[0]-RL*s/2,xy[1]-UD*L_res)])
    pline.add_vertices(r_ins > 0 and m.corner((xy[0]+RL*s/2,xy[1]-UD*L_res),q[4],-1*UD,r_ins,curve_pts//2) or [(xy[0]+RL*s/2,xy[1]-UD*L_res)])
    pline.add_vertices(m.corner((xy[0]+RL*s/2,xy[1]-UD*gap),q[2],1*UD,w/3,curve_pts))
    pline.add_vertices(m.corner((xy[0]+RL*(s/2+w),xy[1]-UD*gap),q[1],1*UD,w/3,curve_pts))
    pline.add_vertices(m.corner((xy[0]+RL*(s/2+w),xy[1]-UD*(L_res+w)),q[4],1*UD,w,curve_pts))
    pline.add_vertices(m.corner((xy[0]-RL*(s/2+w),xy[1]-UD*(L_res+w)),q[3],1*UD,w,curve_pts))
    pline.add_vertices(m.corner((xy[0]-RL*(s/2+w),xy[1]+UD*w),q[2],1*UD,w,curve_pts))
    pline.add_vertices(m.corner((xy[0]+RL*(s/2+w),xy[1]+UD*w),q[1],1*UD,w/3,curve_pts))
    pline.add_vertices(m.corner((xy[0]+RL*(s/2+w),xy[1]),q[4],1*UD,w/3,curve_pts))
    
    pline.close()

    dwg.add(pline)
    
#One link of a spiral
def Spiral_Link_Rounded(dwg,xy,w,s,width,height,UD,line_color,r_ins=0,LR=1,curve_pts=30):
    #LR = 1 if coil goes clockwise and to the right, -1 if counterclockwise and to the left
    #UD = 1 if gap on top, -1 if gap on bottom
    q =  m.transformedQuadrants(UD=UD,LR=LR)
    #draw 
    pline = dxf.polyline(points = [(xy[0],xy[1]-UD*(w+s/2))],color = line_color,flags=0) #start offset by w/2
    pline.add_vertices(m.corner((xy[0],xy[1]+UD*height/2),q[2],1*UD*LR,w/3,curve_pts))
    pline.add_vertices(m.corner((xy[0]+LR*width,xy[1]+UD*height/2),q[1],1*UD*LR,w/3,curve_pts))
    pline.add_vertices(m.corner((xy[0]+LR*width,xy[1]-UD*height/2),q[4],1*UD*LR,w/3,curve_pts))
    pline.add_vertices(m.corner((xy[0]+LR*2*(w+s),xy[1]-UD*height/2),q[3],1*UD*LR,w/3,curve_pts))
    pline.add_vertices([(xy[0]+LR*2*(w+s),xy[1]-UD*(w+s/2)),
                        (xy[0]+LR*(3*w+2*s),xy[1]-UD*(w+s/2)),
                        (xy[0]+LR*(3*w+2*s),xy[1]-UD*(height/2-w)),
                        (xy[0]+LR*(-w + width),xy[1]-UD*(height/2-w)),
                        (xy[0]+LR*(-w + width),xy[1]+UD*(height/2-w)),
                        (xy[0]+LR*w,xy[1]+UD*(height/2-w)),
                        (xy[0]+LR*w,xy[1]-UD*(w+s/2))])    #start offset by w/2
    
    pline.close()

    dwg.add(pline)
 
#return double spiral height
def GetDoubleSpiralHeight(w,s,turns):
    return (2*w+s)+2*(2*turns-1)*(w+s)

#complete double spiral
def DoubleSpiral(dwg,xy,w,s,width,turns,UD,line_color,r_ins=0,LR=1,curve_pts=30):
    #set up close packed width + height
    height=GetDoubleSpiralHeight(w,s,turns)
    width = max(width,height+w+s)
    #do number of selected loops
    for n in range(turns):
        Spiral_Link_Rounded(dwg,(xy[0]+LR*(n*2*(w+s)),xy[1]),w,s,width-4*n*(w+s),height-4*n*(w+s),UD,line_color,r_ins=r_ins,LR=LR,curve_pts=curve_pts)#outer spiral
    for n in range(turns-1):
        Spiral_Link_Rounded(dwg,(xy[0]+LR*(w+s+n*2*(w+s)),xy[1]),w,s,width-4*n*(w+s)-2*w-2*s,height-4*n*(w+s)-2*w-2*s,UD,line_color,r_ins=r_ins,LR=LR)#inner spiral
    
    #UD = 1 if gap on top, -1 if gap on bottom
    q = m.transformedQuadrants(UD=UD,LR=LR)
    #recenter
    xy = (xy[0]+LR*(w+s+(turns-1)*2*(w+s)),xy[1]-UD*(w+s/2))
    #draw 
    pline = dxf.polyline(points = [(xy[0],xy[1])],color = line_color,flags=0) #start offset by w/2
    pline.add_vertices(m.corner((xy[0],xy[1]+UD*(2*w+s)),q[2],1*UD*LR,w/3,curve_pts))
    pline.add_vertices(m.corner((xy[0]+LR*(width-2*(2*turns-1)*(w+s)),xy[1]+UD*(2*w+s)),q[1],1*UD*LR,w/3,curve_pts))
    pline.add_vertices(m.corner((xy[0]+LR*(width-2*(2*turns-1)*(w+s)),xy[1]),q[4],1*UD*LR,w/3,curve_pts))
    pline.add_vertices([(xy[0]+LR*(w+s),xy[1])])
    pline.add_vertices(m.corner((xy[0]+LR*(w+s),xy[1]+UD*w),q[2],1*UD*LR,w/3,curve_pts))
    pline.add_vertices([(xy[0]+LR*(width-2*(2*turns-1)*(w+s)-w),xy[1]+UD*w),
                        (xy[0]+LR*(width-2*(2*turns-1)*(w+s)-w),xy[1]+UD*(w+s)),
                        (xy[0]+LR*w,xy[1]+UD*(w+s)),
                        (xy[0]+LR*w,xy[1])])
    pline.close()

    dwg.add(pline)

#mushroom resonator
def MushrooomResonator(dwg,xy,w,s,nTurns,capFingerLength,nCapFingers,color,capw=2,caps=2,LR=1,curve_pts=30):
    IDcapWidth=nCapFingers*2*(capw+caps)-caps
    
    DoubleSpiral(dwg,(xy[0],xy[1]+GetDoubleSpiralHeight(w,s,nTurns)/2+w+s+capFingerLength/2+caps/2),w,s,IDcapWidth+w+s,nTurns,1,color,LR=LR,curve_pts=curve_pts)
    DoubleSpiral(dwg,(xy[0],xy[1]-GetDoubleSpiralHeight(w,s,nTurns)/2-w-s-capFingerLength/2-caps/2),w,s,IDcapWidth+w+s,nTurns,-1,color,LR=LR,curve_pts=curve_pts)
    dwg.add(dxf.rectangle((xy[0],xy[1]),LR*w,GetDoubleSpiralHeight(w,s,nTurns)+s+caps+capFingerLength,valign=const.MIDDLE))
    dwg.add(dxf.rectangle((xy[0]+LR*(w+s),xy[1]+w+0.5*caps+capFingerLength/2),LR*w,GetDoubleSpiralHeight(w,s,nTurns)/2-w+s/2))
    dwg.add(dxf.rectangle((xy[0]+LR*(w+s),xy[1]-w-0.5*caps-capFingerLength/2),LR*w,-GetDoubleSpiralHeight(w,s,nTurns)/2+w-s/2))
    dwg.add(dxf.rectangle((xy[0]+LR*(w+s),xy[1]+caps/2+capFingerLength/2),LR*IDcapWidth,w))
    dwg.add(dxf.rectangle((xy[0]+LR*(w+s),xy[1]-caps/2-capFingerLength/2),LR*IDcapWidth,-w))
    for n in range(nCapFingers):
        dwg.add(dxf.rectangle((xy[0]+LR*((capw+caps)*(2*n)+w+s),xy[1]+caps/2),LR*capw,capFingerLength,valign=const.MIDDLE))
        dwg.add(dxf.rectangle((xy[0]+LR*((capw+caps)*(2*n+1)+w+s),xy[1]-caps/2),LR*capw,capFingerLength,valign=const.MIDDLE))
   
# ===============================================================================
# Chip definitions
# ===============================================================================    

class GroundedWR10(m.BlankCenteredWR10):
    def __init__(self,wafer,chipID,pad,notch,globalOffset=(0,0)):
        m.BlankCenteredWR10.__init__(self,wafer,chipID,wafer.defaultLayer,globalOffset)
        self.wr10x = 2540+2*pad
        self.wr10y = 1270+2*pad
        color = wafer.bg(wafer.defaultLayer)
        #positive regions define metal
        self.add(dxf.rectangle((self.cx(-self.wr10x/2),0),self.wr10x,self.cy(-self.wr10y/2),bgcolor=color))
        self.add(dxf.rectangle((0,self.height),self.width,self.cy(self.wr10y/2-self.height),bgcolor=color))
        self.add(dxf.rectangle((0,notch),self.cx(-self.wr10x/2),self.cy(self.wr10y/2 - notch),bgcolor=color))
        self.add(dxf.rectangle((self.cx(self.wr10x/2),0),-self.cx(self.wr10x/2-self.width),self.cy(self.wr10y/2),bgcolor=color))

class StuddedWR10(m.BlankCenteredWR10):
    def __init__(self,wafer,chipID,studSize,globalOffset=(0,0)):
        m.BlankCenteredWR10.__init__(self,wafer,chipID,wafer.defaultLayer,globalOffset)
        #assume a marker on lower left. add 3 studs on opposite corners to make the chip evenly balanced
        self.add(dxf.rectangle((0,self.height),studSize,-studSize,bgcolor=wafer.bg(wafer.defaultLayer)))
        self.add(dxf.rectangle((self.width,0),-studSize,studSize,bgcolor=wafer.bg(wafer.defaultLayer)))
        self.add(dxf.rectangle((self.width,self.height),-studSize,-studSize,bgcolor=wafer.bg(wafer.defaultLayer)))
        
class ResistancePad(m.BlankCenteredWR10):
    #for metal defining mask
    def __init__(self,wafer,chipID,w=40,l=1500,pad_extend=1000,offset=(0,0)):
        m.BlankCenteredWR10.__init__(self,wafer,chipID,wafer.defaultLayer,offset)
        #put in a resistance bar
        self.add(dxf.rectangle((-pad_extend+offset[0],0),pad_extend+self.width/2-l/2,self.height,bgcolor=wafer.bg(wafer.defaultLayer)))
        self.add(dxf.rectangle((self.width/2 + l/2+offset[0],0),pad_extend+self.width/2-l/2,self.height,bgcolor=wafer.bg(wafer.defaultLayer)))
        self.add(dxf.rectangle(self.centered((-l/2,-w/2)),l,w,bgcolor=wafer.bg(wafer.defaultLayer)))
        
class InverseResistancePad(m.BlankCenteredWR10):
    #for etch defining mask
    def __init__(self,wafer,chipID,w=40,l=1500,pad_extend=1000,offset=(0,0),overhang=80):
        m.BlankCenteredWR10.__init__(self,wafer,chipID,wafer.defaultLayer,offset)
        #put in holes to define a resistance bar
        #self.add(dxf.rectangle((-pad_extend+offset[0],0),pad_extend+self.width/2-l/2,self.height,bgcolor=wafer.bg(wafer.defaultLayer)))
        #self.add(dxf.rectangle((self.width/2 + l/2+offset[0],0),pad_extend+self.width/2-l/2,self.height,bgcolor=wafer.bg(wafer.defaultLayer)))
        self.add(dxf.rectangle(self.centered((0,-w/2)),l,self.height/2-w/2+overhang,halign=const.CENTER,valign=const.BOTTOM,bgcolor=wafer.bg(wafer.defaultLayer)))
        self.add(dxf.rectangle(self.centered((0,w/2)),l,self.height/2-w/2+overhang,halign=const.CENTER,valign=const.TOP,bgcolor=wafer.bg(wafer.defaultLayer)))
        
        
        
        