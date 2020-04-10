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

from maskLib.Entities import SolidPline, SkewRect, CurveRect, RoundRect, InsideCurve

import math

# ===============================================================================
# functions to setup global variables in wafer object
# ===============================================================================

def setupJunctionLayers(wafer,JLAYER='JUNCTION',jcolor=1,ULAYER='UNDERCUT',ucolor=2,bandaid=False,BLAYER='BANDAID',bcolor=3):
    #add correct layers to wafer, and cache layer
    wafer.addLayer(JLAYER,jcolor)
    wafer.JLAYER=JLAYER
    wafer.addLayer(ULAYER,ucolor)
    wafer.ULAYER=ULAYER
    if bandaid:
        wafer.addLayer(BLAYER,bcolor)
        wafer.BLAYER=BLAYER

def setupJunctionAngles(wafer,JANGLES=[0,90]):
    '''
    Angles are defined as the angle in degrees *from which the evaporation is coming*.
    For example, if the first evaporation comes from the East, and the second from the north,
    the angles would be [0,90]. Add more angles to the list as needed.
    '''
    wafer.JANGLES = [angle % 360 for angle in JANGLES]

# ===============================================================================
# contact pad functions (for ground plane)
# ===============================================================================
                                #stemw=3,steml=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5
def JcalcTabDims(chip,structure,gapw=3,gapl=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5,absoluteDimensions=False,stemw=None,steml=None,**kwargs):
    if stemw is not None:
        gapw = stemw
    if steml is not None:
        gapl = steml
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,start=structure,direction=0)
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
    #determine stem and tab lengths
    if absoluteDimensions:
        if gapl >= 2*r_out:
            gapl = gapl-2*r_out
        if tabl >= 2*r_ins:
            tabl = tabl-2*r_ins
            
    #returns length, half width
    return 2*r_out+gapl+taboffs+2*r_ins+tabl,(gapw/2+r_out+tabw+r_ins)
    
                                                                    #stemw=3,steml=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5
def JContact_slot(chip,structure,rotation=0,absoluteDimensions=False,gapw=3,gapl=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5,hflip=False,bgcolor=None,debug=False,**kwargs):
    '''
    Creates shapes forming a negative space puzzle piece slot (tab) with rounded corners, and adjustable angles. 
    No overlap : XOR mode compatible
    Centered on outside midpoint of gap
    
    gap: {width (gapw),height (gapl),r_out}
    tab: {slot width, (tabw),height (tabl), height offset (taboffs),r_ins}
    
    by default, absolute dimensions are off, so gap / tab lengths are determined by radii. gapl and tabl will then determine extra space between rounded corners.
    if absolute dimensions are on, then tab / gap lengths are determined only by gapl and tabl.
    
    set r_ins or r_out to None to inherit defaults from chip/structure
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
    
    tot_length,half_width = JcalcTabDims(chip,structure,gapw,gapl,tabw,tabl,taboffs,r_out,r_ins,absoluteDimensions)
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
    
    
def JContact_tab(chip,structure,rotation=0,absoluteDimensions=False,stemw=3,steml=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5,hflip=False,bgcolor=None,debug=False,**kwargs):
    '''
    Creates shapes forming a puzzle piece tab with rounded corners, and adjustable angles. 
    No overlap : XOR mode compatible
    Centered on bottom midpoint of stem
    
    stem: {width (stemw),height (steml),r_out}
    tab: {slot width, (tabw),height (tabl), height offset (taboffs),r_ins}
    
    by default, absolute dimensions are off, so stem / tab lengths are determined by radii. steml and tabl will then determine extra space between rounded corners.
    if absolute dimensions are on, then tab / stem lengths are determined only by steml and tabl.
    
    set r_ins or r_out to None to inherit defaults from chip/structure
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
    
    tot_length,half_width = JcalcTabDims(chip,structure,stemw,steml,tabw,tabl,taboffs,r_out,r_ins,absoluteDimensions)
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
        
    
def JSingleProbePad(chip,pos,padwidth=250,padheight=None,padradius=25,tab=False,tabShoulder = False,tabShoulderWidth=30,tabShoulderLength=80,tabShoulderRadius=None,flipped=False,rotation=0,bgcolor=None,**kwargs):
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
    
    tablength,tabhwidth = JcalcTabDims(chip,pos,**kwargs)    
    
    if tab:
        #positive tab
        if not flipped:
            chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=padwidth)
            if tabShoulder:
                chip.add(RoundRect(struct().start,tabShoulderLength,tabShoulderWidth,tabShoulderRadius,roundCorners=[0,1,1,0],valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=tabShoulderLength)
        JContact_tab(chip,struct(),hflip = flipped,**kwargs)
        if flipped:
            if tabShoulder:
                chip.add(RoundRect(struct().start,tabShoulderLength,tabShoulderWidth,tabShoulderRadius,roundCorners=[1,0,0,1],valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=tabShoulderLength)
            chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    else:
        #slot
        if not flipped:
            chip.add(RoundRect(struct().getPos((0,tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[0,0,1,1],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(RoundRect(struct().getPos((0,-tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[1,1,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(struct().start,padwidth-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=padwidth-tablength)
        JContact_slot(chip,struct(),hflip = not flipped,**kwargs)
        if flipped:
            chip.add(RoundRect(struct().getPos((-tablength,tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[0,0,1,1],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(RoundRect(struct().getPos((-tablength,-tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[1,1,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            chip.add(dxf.rectangle(struct().start,padwidth-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
            
            
def JProbePads(chip,pos,padwidth=250,separation=40,rotation=0,**kwargs):
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
    
    struct().shiftPos(-separation/2-padwidth)
    JSingleProbePad(chip,struct(),padwidth=padwidth,flipped=False,**kwargs)
    struct().shiftPos(separation)
    JSingleProbePad(chip,struct(),padwidth=padwidth,flipped=True,**kwargs)          
    
    
def ManhattanJunction(chip,pos,rotation=0,separation=40,jpadw=20,jpadr=2,jpadh=None,jpadOverhang=5,jpadTaper=0,
                      jfingerw=0.13,jfingerl=5.0,jfingerex=1.0,
                      leadw=2.0,leadr=0.5,
                      undercutdist=0.6,
                      JANGLE1=None,JANGLE2=None,directionFlipAlowed=False,
                      JLAYER=None,ULAYER=None,bgcolor=None,**kwargs):
    '''
    Set jpadr to None to use chip-wide defaults (r_out)
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
    if jpadr is None:
        try:
            jpadr = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            jpadr = 0
    if jpadh is None:
        jpadh = jpadw
    if bgcolor is None: #color for junction, not undercut
        bgcolor = chip.wafer.bg()
    #get layers from wafer
    if JLAYER is None:
        try:
            JLAYER = chip.wafer.JLAYER
        except AttributeError:
            setupJunctionLayers(chip.wafer)
            JLAYER = chip.wafer.JLAYER
    if ULAYER is None:
        try:
            ULAYER = chip.wafer.ULAYER
        except AttributeError:
            setupJunctionLayers(chip.wafer)
            ULAYER = chip.wafer.ULAYER
    
    #cache start position and figure out if we're using structures or not
    if thisStructure is None:
        #using structures
        struct().shiftPos(separation/2)
    centerPos = struct().start
    
    # -------------------- junction pads --------------------
    # do undercut layer
    
    # do junction layer
    chip.add(RoundRect(struct().getPos((-separation/2+jpadOverhang,0)),jpadw,jpadh,jpadr,roundCorners = (jpadTaper > 0) and [1,0,0,1] or [1,1,1,1],
                       valign=const.MIDDLE,halign=const.RIGHT,rotation=struct().direction,bgcolor=bgcolor,layer=JLAYER,**kwargs))
    chip.add(RoundRect(struct().getPos((separation/2-jpadOverhang,0)),jpadw,jpadh,jpadr,roundCorners = (jpadTaper > 0) and [0,1,1,0] or [1,1,1,1],
                       valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,layer=JLAYER,**kwargs))
    
    if JANGLE2 is None:
        try:
            JANGLE2 = chip.wafer.JANGLES[1]
        except AttributeError:
            setupJunctionAngles(chip.wafer)
            JANGLE2 = chip.wafer.JANGLES[1]
    else:
        JANGLE2 = JANGLE2 % 360
    JANGLE1 = JANGLE2-90
        
    
    # -------------------- junction fingers --------------------
    # do undercut layer
    chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((-jfingerex,0),#rotate about center
                                                    math.radians(JANGLE2))), -undercutdist, min(3*jfingerw,2*jfingerex), rotation=JANGLE2,
                           valign=const.MIDDLE,layer=ULAYER,bgcolor=bgcolor,**kwargs))
    chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((-jfingerex,0),#rotate about center
                                                    math.radians(JANGLE1))), -undercutdist, min(3*jfingerw,2*jfingerex), rotation=JANGLE1,
                           valign=const.MIDDLE,layer=ULAYER,bgcolor=bgcolor,**kwargs))
    # do junction layer
    chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((-jfingerex,0),#rotate about center
                                                    math.radians(JANGLE2))), jfingerl, jfingerw, rotation=JANGLE2,
                           valign=const.MIDDLE,layer=JLAYER,bgcolor=bgcolor,**kwargs))
    chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((-jfingerex,0),#rotate about center
                                                    math.radians(JANGLE1))), jfingerex-jfingerw/2, jfingerw, rotation = JANGLE1,
                           valign=const.MIDDLE,layer=JLAYER,bgcolor=bgcolor,**kwargs))
    chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((jfingerw/2,0),#rotate about center
                                                    math.radians(JANGLE1))), jfingerl-jfingerex-jfingerw/2, jfingerw, rotation = JANGLE1,
                           valign=const.MIDDLE,layer=JLAYER,bgcolor=bgcolor,**kwargs))
    
    # determine angle of structure relative to junction fingers
    angle = (struct().direction - (JANGLE2 - 90)) % 360
    if angle > 180:
        struct().shiftPos(0,angle=180)
        angle = angle % 180
    #angle should now be between [0,180)
    if angle <= 45:
        left_top = False
        right_top = True
        right_switch = False
    elif angle <= 90:
        left_top = True
        right_top = False
        right_switch = False
    else:
        left_top = True
        right_top = True
        right_switch = True
        
    # adjust overhang to account for taper
    if jpadTaper > 0:
        jpadOverhang = jpadOverhang + jpadTaper
    
    # -------------------- junction leads --------------------
    # do undercut layer
    
    # do junction layer
    if left_top:
        # j finger stems from top of left lead
        chip.add(SolidPline(centerPos, points=[
            rotate_2d((-separation/2+jpadOverhang,
                       -(jfingerl-jfingerex)*math.sin(math.radians(angle))-leadw-jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction)),
            rotate_2d(((jfingerl-jfingerex)*math.cos(math.radians(angle))+jfingerw*math.sin(math.radians(angle))/2,
                       -(jfingerl-jfingerex)*math.sin(math.radians(angle))-leadw-jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction)),
            rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE1)),
            rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE1)),
            rotate_2d((-separation/2+jpadOverhang,
                       -(jfingerl-jfingerex)*math.sin(math.radians(angle))-jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction))
            ],bgcolor=bgcolor,layer=JLAYER))
        if jpadTaper > 0:
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((-separation/2+jpadOverhang-jpadTaper,jpadh/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang-jpadTaper,-jpadh/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(math.radians(angle))-leadw-jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(math.radians(angle))-jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))
    else:
        # j finger stems from bottom of left lead
        chip.add(SolidPline(centerPos, points=[
            rotate_2d((-separation/2+jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(math.radians(angle))+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction)),
            rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
            rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE2)),
            rotate_2d(((jfingerl-jfingerex)*math.sin(math.radians(angle))+jfingerw*math.cos(math.radians(angle))/2,
                       (jfingerl-jfingerex)*math.cos(math.radians(angle))+leadw+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction)),
            rotate_2d((-separation/2+jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(math.radians(angle))+leadw+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction))
            ],bgcolor=bgcolor,layer=JLAYER))
        if jpadTaper > 0:
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((-separation/2+jpadOverhang-jpadTaper,jpadh/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang-jpadTaper,-jpadh/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(math.radians(angle))+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(math.radians(angle))+leadw+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))
    
    if right_top:
        # j finger stems from top of right lead
        if not right_switch:
            # JANGLE1 is our finger
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(math.radians(angle))-leadw+jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction)),
                rotate_2d(((jfingerl-jfingerex)*math.cos(math.radians(angle))-jfingerw*math.sin(math.radians(angle))/2,
                           -(jfingerl-jfingerex)*math.sin(math.radians(angle))-leadw+jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction)),
                rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE1)),
                rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE1)),
                rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(math.radians(angle))+jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))
            if jpadTaper > 0:
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(math.radians(angle))-leadw+jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(math.radians(angle))+jfingerw*math.cos(math.radians(angle))/2),math.radians(struct().direction))
                    ],bgcolor=bgcolor,layer=JLAYER))
        else:
            # JANGLE2 is our finger
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(math.radians(angle))-leadw+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction)),
                rotate_2d(((jfingerl-jfingerex)*math.sin(math.radians(angle))+jfingerw*math.cos(math.radians(angle))/2,
                           (jfingerl-jfingerex)*math.cos(math.radians(angle))-leadw+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction)),
                rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE2)),
                rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
                rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(math.radians(angle))+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))
            if jpadTaper > 0:
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(math.radians(angle))-leadw+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(math.radians(angle))+jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction))
                    ],bgcolor=bgcolor,layer=JLAYER))
    else:
        # j finger stems from bottom of right lead
        # JANGLE2 is our finger
        chip.add(SolidPline(centerPos, points=[
            rotate_2d((separation/2-jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(math.radians(angle))+leadw-jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction)),
            rotate_2d(((jfingerl-jfingerex)*math.sin(math.radians(angle))-jfingerw*math.cos(math.radians(angle))/2,
                       (jfingerl-jfingerex)*math.cos(math.radians(angle))+leadw-jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction)),
            rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
            rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE2)),
            rotate_2d((separation/2-jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(math.radians(angle))-jfingerw*math.sin(math.radians(angle))/2),math.radians(struct().direction))
            ],bgcolor=bgcolor,layer=JLAYER))