# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 11:53:13 2020

@author: sasha
"""
from dxfwrite import DXFEngine as dxf
from dxfwrite.algebra import rotate_2d
from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
import math

# ===============================================================================
#  UTILITY FUNCTIONS  
# ===============================================================================
     

def curveAB(a,b,clockwise=True,angleDeg=90,ptdensity=120):
    # generate a segmented curve from A to B specified by angle. Point density = #pts / revolution
    # return list of points
    # clockwise can be boolean {1,0} or sign type {1,-1}
    
    if clockwise == 0:
        clockwise = -1
        
    angle = math.radians(angleDeg)
    segments = int(angle/(2*math.pi) *ptdensity)
    center = vadd(midpoint(a,b),vmul_scalar(rotate_2d(vsub(b,a),-clockwise*math.pi/2),0.5/math.tan(angle/2)))
    points = []
    for i in range(segments+1):
        points.append(vadd(center,rotate_2d(vsub(a,center),-clockwise*i*angle/segments)))
    return points

def cornerRound(vertex,quadrant,radius,clockwise=True,ptdensity=120):
    #quadrant corresponds to quadrants 1-4
    #generate a curve to replace the vertex
    ptA = vadd(vertex,rotate_2d((0,radius),quadrant * math.pi/2))
    ptB = vadd(vertex,rotate_2d((0,radius),(quadrant+1) * math.pi/2))

    return clockwise>0 and curveAB(ptA,ptB,1,ptdensity=ptdensity) or curveAB(ptB,ptA,-1,ptdensity=ptdensity)

def transformedQuadrants(vflip=False,hflip=False):
    #return quadrant list with vertical and horizontal flips applied. Updated to match dxfwrite style
    # default quadrants:
        
    #    ^y
    #  2 | 1
    #  --+--->x
    #  3 | 4
    
    return vflip==False and (hflip==False and [0,1,2,3,4] or [0,2,1,4,3]) or (hflip==False and [0,4,3,2,1] or [0,3,4,1,2])