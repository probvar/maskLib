# -*- coding: utf-8 -*-
"""
Created on Fri Aug 31 16:45:06 2018

@author: slab
"""

import maskLib.MaskLib as m
from maskLib.microwaveLib import *
from maskLib.Entities import SolidPline, SkewRect, CurveRect, RoundRect, InsideCurve
from maskLib.junctionLib import JContact_slot,JContact_tab,JcalcTabDims
import numpy as np
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.entities import *
from dxfwrite.vector2d import vadd

# ===============================================================================
# wafer setup
# ===============================================================================

w = m.Wafer('StructureTest01','DXF/',7000,7000,waferDiameter=m.waferDiameters['2in'],sawWidth=m.sawWidths['8A'],
                frame=1,solid=1,multiLayer=1)
# w.frame: draw frame layer?
# w.solid: draw things solid?
# w.multiLayer: draw in multiple layers?

w.SetupLayers([
    ['BASEMETAL',4]
    ])

#initialize the wafer
w.init()

#do dicing border
w.DicingBorder()

curve_pts = 30  #point resolution of all curves

#=============================
class FancyChip(m.Chip7mm):
    def __init__(self,wafer,chipID,layer):
        m.Chip7mm.__init__(self,wafer,chipID,layer,defaults={'w':10, 's':5, 'radius':50,'r_out':5,'r_ins':5})
        
        for s in self.structures:
            self.add(dxf.rectangle(s.start,80,20,rotation=s.direction,layer='FRAME',halign = const.RIGHT,valign = const.MIDDLE))
            
        self.add(dxf.rectangle(self.getStart(3),200,40,rotation = self.getDir(3),valign = const.MIDDLE),structure=3,length=200,angle=-90)
        self.add(dxf.rectangle(self.getStart(3),200,40,rotation = self.getDir(3),valign = const.MIDDLE),structure=3,length=200)
        
        #launcher subcomponents
        CPW_stub_open(self,1,r_out=100,r_ins=50,w=300,s=160,flipped=True)
        CPW_straight(self,1,300,w=300,s=160)
        CPW_taper(self,1,w0=300,s0=160)
        #
        CPW_straight(self,1,600)
        
        
        
        JellyfishResonator(self,self.structures[1].cloneAlongLast((300,40),newDirection=90),520,480,5565,w_cap=40,s_cap=20,maxWidth=100)
        
        
        CPW_bend(self,1,angle=45)
        CPW_straight(self,1,600)
        
        DoubleJellyfishResonator(self,self.structures[1].cloneAlongLast((100,40),newDirection=90),520,480,2565,w_cap=40,s_cap=20,maxWidth=70,ialign=const.MIDDLE)
        DoubleJellyfishResonator(self,self.structures[1].cloneAlongLast((-200,640),newDirection=90),480,200,2565,w_ind=2,w_cap=40,s_cap=20,maxWidth=60,ialign=const.MIDDLE)
        
        #clone position for new structure
        s0 = m.Structure(self,start=self.structures[1].getLastPos((300,-40)),defaults={'w':20, 's':10, 'radius':100,'r_out':5,'r_ins':5})
        
        CPW_stub_short(self,1,s=10,r_out=2.5,curve_out=False)
        self.structure(1).shiftPos(40)
        CPW_stub_short(self,1,s=10,r_out=2.5,curve_ins=False,flipped=True)
        CPW_straight(self,1,200)
        
        DoubleJellyfishResonator(self,self.structures[1].cloneAlongLast((100,40),newDirection=90),520,80,2565,w_cap=40,s_cap=20,maxWidth=70,ialign=const.MIDDLE)
        
        CPW_bend(self,1,angle=20,radius=200)
        CPW_straight(self,1,200,10,5)
        CPW_wiggles(self,1,length=3750,maxWidth=200,CCW=False)
        CPW_straight(self,1,200)
        CPW_bend(self,1,angle=55,CCW=False,radius=200)
        CPW_wiggles(self,1,length=2350,maxWidth=300,CCW=False,stop_bend=False)
        CPW_wiggles(self,1,length=1205,maxWidth=100,CCW=False,stop_bend=False,start_bend=False)
        CPW_wiggles(self,1,length=2350,maxWidth=300,CCW=False,start_bend=False,stop_bend=False)
        CPW_straight(self,1,600)
        
        #s1 = m.Structure(self,start=self.structures[1].getLastPos((300,-50)),direction=self.structures[1].direction,defaults=self.defaults)
        s1 = self.structures[1].cloneAlongLast((300,-50))
        s2 = m.Structure(self,start=self.structures[1].getLastPos((300,-100)),direction=self.structures[1].direction,defaults=self.defaults)
        s3 = m.Structure(self,start=self.structures[1].getLastPos((300,-150)),direction=self.structures[1].direction,defaults=self.defaults)
        
        CPW_wiggles(self,1,length=1200,maxWidth=200,start_bend=False,stop_bend=False)
        CPW_wiggles(self,1,length=1200,maxWidth=200,radius=10,start_bend=False,stop_bend=True)
        CPW_straight(self,1,20,s=195)
        #CPW_straight(self,1,200)
        Inductor_wiggles(self,1,length=200,Width=200,nTurns=10,radius=20,start_bend=True,stop_bend=False,pad_to_width=True)
        #CPW_stub_open(self,1,r_out=0)
        
        CPW_launcher(self,2)
        
        
        #continue independent structure
        CPW_stub_open(self,s0,flipped=True)
        CPW_straight(self,s0,200)
        CPW_taper(self,s0,50,w1=self.structures[2].defaults['w'],s1=self.structures[2].defaults['s'])
        s0.defaults['w']=self.structures[2].defaults['w']
        s0.defaults['s']=self.structures[2].defaults['s']
        CPW_directTo(self,s0,self.structures[2],radius=200)
        
        #continue independent structure 2
        
        CPW_stub_open(self,s1,flipped=True,w=20,s=10)
        CPW_straight(self,s1,100,w=20,s=10)
        CPW_taper(self,s1,w0=20,s0=10)
        CPW_straight(self,s1,400)
        
        CPW_stub_open(self,s2,flipped=True,w=20,s=10)
        CPW_straight(self,s2,100,w=20,s=10)
        CPW_taper(self,s2,w0=20,s0=10)
        
        CPW_stub_open(self,s3,flipped=True,w=20,s=10)
        CPW_straight(self,s3,100,w=20,s=10)
        CPW_taper(self,s3,w0=20,s0=10)
        #CPW_bend(self,s3,30,radius=200)
        
        CPW_launcher(self,8)
        CPW_launcher(self,5)
        CPW_launcher(self,4)
        
        CPW_directTo(self,s1,self.structures[8],radius=200)
        CPW_directTo(self,s2,self.structures[5],radius=200)
        CPW_directTo(self,s3,self.structures[4],radius=200)
        
        #>>>>>>>>>>> test cpw_tee functions <<<<<<<<<<<<<<<
        
        s4=m.Structure(self,start=self.centered((-100,-2800)),direction=15,defaults={'w':10, 's':5, 'radius':50,'r_out':5})
        CPW_stub_open(self,s4,flipped=True,w=20,s=10)
        CPW_straight(self,s4,100,w=20,s=10)
        CPW_taper(self,s4,w0=20,s0=10)
        CPW_straight(self,s4,80)
        s4a,s4b = CPW_tee(self,s4,radius=3)#continue CPW off of each tee end
        CPW_straight(self,s4a,30)
        CPW_straight(self,s4b,50)
        
        s4.shiftPos(60)#flipped
        s4a,s4b =CPW_tee(self,s4,hflip=True)
        CPW_straight(self,s4,20)
        CPW_straight(self,s4a,30)
        CPW_straight(self,s4b,40)
        
        s4.shiftPos(40)#w different
        CPW_straight(self,s4,20)
        s4a,s4b = CPW_tee(self,s4,w1=20)
        CPW_straight(self,s4a,30) #branching structure defaults are automatically redefined
        CPW_taper(self,s4b,30,w1=10,s1=3)
        
        s4.shiftPos(60)#s1<s
        CPW_straight(self,s4,20)
        s4a,s4b = CPW_tee(self,s4,w1=4,s1=3)
        CPW_straight(self,s4a,30) #branching structure defaults are automatically redefined
        CPW_straight(self,s4b,20)
        
        s4.shiftPos(40)#s1>s
        CPW_straight(self,s4,20)
        s4a,s4b = CPW_tee(self,s4,w1=15,s1=15,r_ins=0)
        CPW_straight(self,s4a,30) #branching structure defaults are automatically redefined
        CPW_straight(self,s4b,20)
        
        s4.shiftPos(80)#flipped AND s1<s
        s4a,s4b = CPW_tee(self,s4,w1=4,s1=3,hflip=True,r_ins=20)
        CPW_straight(self,s4,20)
        CPW_straight(self,s4a,30) #branching structure defaults are automatically redefined
        CPW_straight(self,s4b,20)
        
        s4.shiftPos(60)#flipped AND s1>s
        s4a,s4b = CPW_tee(self,s4,w1=15,s1=15,hflip=True)
        CPW_straight(self,s4,20)
        CPW_straight(self,s4a,30) #branching structure defaults are automatically redefined
        CPW_straight(self,s4b,20)
        #test left oriented CPW tee
        s4a=CPW_tee(self,s4,branch_off=const.LEFT)
        CPW_straight(self,s4,30)
        CPW_straight(self,s4a,50) #continue off left branch
        CPW_straight(self,s4,30)
        
        s4b=CPW_tee(self,s4,branch_off=const.RIGHT)
        CPW_straight(self,s4b,50) #continue off right branch
        CPW_straight(self,s4,30)
        
        #>>>>>>>>>>> test junction pad functions <<<<<<<<<<<<<<<
        # slot functions
        s5=m.Structure(self,start=self.centered((100,2800)),direction=-15,defaults={'w':20, 's':10, 'radius':100,'r_out':1.5,'r_ins':1.5})
        self.add(dxf.rectangle(s5.getPos((0,0)),-100,13,valign=const.MIDDLE,rotation=s5.direction,bgcolor=w.bg()))
        self.add(dxf.rectangle(s5.getPos((8.5,6.5)),-100-8.5,50,rotation=s5.direction,bgcolor=w.bg()))
        self.add(dxf.rectangle(s5.getPos((8.5,-6.5)),-100-8.5,-50,rotation=s5.direction,bgcolor=w.bg()))
        JContact_slot(self,s5,gapl=1,tabl=2,tabw=2,taboffs=-0.5,hflip=True)
        s5.shiftPos(50)

        JContact_slot(self,s5,gapl=1,tabl=1,tabw=2,taboffs=1.5)
        self.add(dxf.rectangle(s5.getPos((0,0)),100,13,valign=const.MIDDLE,rotation=s5.direction,bgcolor=w.bg()))
        self.add(dxf.rectangle(s5.getPos((-9.5,6.5)),100+9.5,50,rotation=s5.direction,bgcolor=w.bg()))
        self.add(dxf.rectangle(s5.getPos((-9.5,-6.5)),100+9.5,-50,rotation=s5.direction,bgcolor=w.bg()))
        
        #works without structure as well
        JContact_slot(self,self.centered((100,2600)),gapl=1,tabl=1,tabw=2,taboffs=0,r_out=1.5,r_ins=1.5)
        self.add(dxf.rectangle(self.centered((109.5,2600)),20,13,valign=const.MIDDLE,bgcolor=w.bg()))
        
        # tab functons
        s6=m.Structure(self,start=self.centered((600,2800)),direction=-15,defaults={'w':20, 's':10, 'radius':100,'r_out':1.5,'r_ins':1.0})
        self.add(dxf.rectangle(s6.getPos((0,0)),-100,100,valign=const.MIDDLE,rotation=s5.direction,bgcolor=w.bg()))
        JContact_tab(self,s6,steml=1,tabw=2,taboffs=-0.5)
        s6.shiftPos(40)

        JContact_tab(self,s6,steml=1,tabl=1,tabw=2,taboffs=1.5,hflip=True)
        self.add(dxf.rectangle(s6.getPos((0,0)),100,100,valign=const.MIDDLE,rotation=s5.direction,bgcolor=w.bg()))
        
        #>>>>>>>>>>> test solid pline functions <<<<<<<<<<<<<<<
        
        pline = SolidPline(self.centered((1000,500)),points = [(0,0)],color=2,bgcolor=2,rotation=30,flags=0)#1
        pline.add_vertices([(1000,0),(1000,500),(800,600),(0,600)])
        #don't need to close
        self.add(pline)
        
        pline = SolidPline(self.centered((300,-600)),points = [(300,-600)],bgcolor=w.bg(),rotation=-30,flags=0)#1
        pline.add_vertices([(300,0),(100,400),(0,-600)])
        #don't need to close
        self.add(pline)
        
        #>>>>>>>>>>> test roundRect functions <<<<<<<<<<<<<<<<<<
        self.add(dxf.line(self.centered((-10,2300)),self.centered((210,2300)),color=1))
        self.add(RoundRect(self.centered((0,2300)),200,130,radius=40,roundCorners=[1,1,0,1],rotation=15,valign=const.MIDDLE,bgcolor=w.bg()))
        self.add(RoundRect(self.centered((-10,2300)),200,130,radius=40,roundCorners=[1,1,0,1],rotation=15,hflip=True,valign=const.MIDDLE,bgcolor=w.bg()))
        self.add(RoundRect(self.centered((210,2300)),200,130,radius=40,roundCorners=[1,1,0,1],rotation=15,vflip=True,valign=const.MIDDLE,bgcolor=self.bg()))
        
        #demonstrate skewrect
        self.add(SkewRect(self.centered((-1600,-650)),100,80,(20,-30),10,bgcolor=w.bg(),valign=const.MIDDLE))
        self.add(dxf.rectangle(self.centered((-1600,-650)),100,80,color=1,valign=const.MIDDLE))
        self.add(dxf.line(self.centered((-1600 + 100,-650)),self.centered(( -1600 + 100 +20,-680)),color=2))
        
        #test alignment
        self.add(dxf.line(self.centered((-1600,-500)),self.centered((0,-500)),color=1))
        self.add(dxf.line(self.centered((-1200,-540)),self.centered((0,-540)),color=1))
        
        self.add(SkewRect(self.centered((-1200,-500)),100,80,(0,-40),20,valign=const.BOTTOM,edgeAlign=const.BOTTOM,bgcolor=w.bg()))
        self.add(SkewRect(self.centered((-1000,-500)),100,80,(0,-40),20,valign=const.TOP,edgeAlign=const.TOP,bgcolor=w.bg()))
        self.add(SkewRect(self.centered((-800,-500)),100,80,(0,-40),20,valign=const.MIDDLE,edgeAlign=const.MIDDLE,bgcolor=w.bg()))
        
        #test alignment and rotation
        self.add(dxf.line(self.centered((-1400,-800)),self.centered((0,-800)),color=1))
        self.add(dxf.line(self.centered((-1200,-840)),self.centered((0,-840)),color=1))
        
        self.add(SkewRect(self.centered((-1200,-800)),100,80,(0,-40),20,rotation=30,valign=const.BOTTOM,edgeAlign=const.BOTTOM,bgcolor=w.bg()))
        self.add(SkewRect(self.centered((-1000,-800)),100,80,(0,-40),20,rotation=30,valign=const.TOP,edgeAlign=const.TOP,bgcolor=w.bg()))
        self.add(SkewRect(self.centered((-800,-800)),100,80,(0,-40),20,rotation=30,valign=const.MIDDLE,edgeAlign=const.MIDDLE,bgcolor=w.bg()))
        
        #curverect testing
        self.add(dxf.line(self.centered((-2000,650)),self.centered((-100,650)),color=1))
        
        self.add(CurveRect(self.centered((-2400,650)),80,200,angle=140,rotation=30,bgcolor=2,valign=const.BOTTOM,hflip=True))
        
        self.add(CurveRect(self.centered((-1800,650)),30,60,angle=140,rotation=30,bgcolor=2,valign=const.BOTTOM))
        self.add(CurveRect(self.centered((-1800,650)),30,60,angle=140,rotation=30,bgcolor=3,hflip=True,valign=const.TOP))
        
        self.add(CurveRect(self.centered((-1600,650)),30,60,angle=140,rotation=30,valign=const.TOP,vflip=True))
        
        self.add(CurveRect(self.centered((-1400,650)),60,30,ralign=const.TOP,bgcolor=3))
        self.add(CurveRect(self.centered((-1400,650)),60,30,ralign=const.TOP,hflip=True,bgcolor=2))
        
        self.add(CurveRect(self.centered((-1200,650)),60,30,angle=200,valign=const.TOP,bgcolor=2))
        
        #cpw bend test
        self.add(CurveRect(self.centered((-1000,650)),30,90,angle=140,roffset=15,ralign=const.BOTTOM,rotation=30,vflip=True))
        self.add(CurveRect(self.centered((-1000,650)),30,90,angle=140,roffset=15,ralign=const.BOTTOM,rotation=30))
        self.add(CurveRect(self.centered((-1000,650)),30,90,angle=140,roffset=-15,ralign=const.TOP,valign=const.TOP,rotation=30,vflip=True))
        
        
        #inside corner test
        self.add(dxf.rectangle(self.centered((-500,0)),1000,100,valign=const.MIDDLE,halign=const.CENTER,bgcolor=w.bg()))
        self.add(dxf.rectangle(self.centered((-300,0)),800,100,valign=const.MIDDLE,halign=const.CENTER,rotation=50,bgcolor=w.bg()))
        self.add(dxf.rectangle(self.centered((-700,0)),800,100,valign=const.MIDDLE,halign=const.CENTER,rotation=90,bgcolor=w.bg()))
        
        self.add(InsideCurve(self.centered((-750,-50)),50,bgcolor=2))
        self.add(InsideCurve(self.centered((-650,-50)),50,bgcolor=2,hflip=True))
        self.add(InsideCurve(self.centered((-750,50)),50,bgcolor=2,vflip=True))
        self.add(InsideCurve(self.centered((-650,50)),50,bgcolor=2,hflip=True,vflip=True))
        
        x1 = 50/np.tan(np.radians(50))
        x2 = 50/np.sin(np.radians(50))
        self.add(InsideCurve(self.centered((-300 - x1 - x2,-50)),50,angle=50,bgcolor=2))
        self.add(InsideCurve(self.centered((-300 - x1 + x2,-50)),50,angle=130,bgcolor=2,hflip=True))
        self.add(InsideCurve(self.centered((-300 + x1 - x2,50)),50,angle=130,bgcolor=2,vflip=True))
        self.add(InsideCurve(self.centered((-300 + x1 + x2,50)),50,angle=50,bgcolor=2,hflip=True,vflip=True))
        
        
        #----------------------- test CPW launcher ---------------
        
   
        
myFancyChip = FancyChip(w,'FANCYCHIP','BASEMETAL')
#waffle(myFancyChip, 176.3, width=80,bleedRadius=1,padx=500,layer='MARKERS')


myFancyChip.save(w,drawCopyDXF=True,dicingBorder=True)

for i in range(8,16):
    w.chips[i]=myFancyChip

# write all chips
w.populate()
w.save()
