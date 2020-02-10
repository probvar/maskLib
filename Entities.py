# -*- coding: utf-8 -*-
"""
Created on Mon Oct  7 10:09:40 2019

@author: slab
"""
import math

from dxfwrite.mixins import SubscriptAttributes
from dxfwrite import const
from dxfwrite.algebra import rotate_2d
from dxfwrite.base import DXFList,dxfstr
from dxfwrite.entities import Polyline, Solid
from dxfwrite.vector2d import vadd, vsub

class SolidPline(SubscriptAttributes):
    ''' Shape consisting of a Polyline and solid background** if polyline has 4 points or less
            acts like a Polyline, quacks like a Polyline, but generates a polyline + solid when dxf tags are called
    '''
    name = 'SOLIDPLINE'
    
    def __init__(self,insert,rotation=0.,color=const.BYLAYER,bgcolor=None,layer='0',linetype=None, points=None, **kwargs):
        self.insert = insert
        self.rotation = math.radians(rotation)
        self.color = color
        self.bgcolor = bgcolor
        self.layer = layer
        self.linetype = linetype
        
        if points is None:
            points = []
        self.points = points
        
        self.transformed_points = self.points

    
    def _build(self):
        data = DXFList()
        self.transformed_points = self._transform_points(self.points)
        if self.color is not None:
            data.append(self._build_polyline())
        if self.bgcolor is not None and len(self.points) <= 4:
            data.append(self._build_solid())
        return data
        
    def _transform_points(self,points):
        return [vadd(self.insert,  # move to insert point
                            rotate_2d(  # rotate at origin
                                point, self.rotation))
                       for point in points]
        
    def _build_polyline(self):
        '''Build the polyline (key component)'''
        polyline = Polyline(self.transformed_points, color=self.color, layer=self.layer,flags=0)
        polyline.close() #redundant in most cases
        if self.linetype is not None:
            polyline['linetype'] = self.linetype
        return polyline

    #polyline classes here
    def add_vertices(self,points,**kwargs):
        ''' add list of vertices, dump kwargs '''
        for point in points:
            self.add_vertex(point,**kwargs)
            
    def add_vertex(self,point,**kwargs):
        '''add a vertex located at point, dump kwargs'''
        self.points.append(point)

    def _build_solid(self):
        """ build the background solid """
        return Solid(self.transformed_points, color=self.bgcolor, layer=self.layer)    
    
    def __dxf__(self):
        ''' get the dxf string '''
        return dxfstr(self.__dxftags__())
    
    def __dxftags__(self):
        return self._build()



    
class SkewRect(SolidPline):
    ''' new and improved version of mmWaveLib's skewRect. Can be added directly to DXF
            quadrangle drawn counterclockwise starting from bottom left
            edges are indexed 0-3 correspondingly
            edge 1 is default (east edge )
    '''
    name = 'SKEWRECT'
    #corner,width,height,offset,newLength,edge=1,**kwargs
    def __init__(self,insert,width,height,offset,newLength,edge=1,halign=const.LEFT,valign=const.BOTTOM,edgeAlign=const.MIDDLE, **kwargs):
        self.width=width
        self.height=height
        self.halign=halign
        self.valign=valign
        self.ealign=edgeAlign
        SolidPline.__init__(self,insert,points=self._calc_corners(offset,newLength,edge), **kwargs)
        
    def _calc_corners(self,offset,newLength,edge):
        pts = [(0,0),(self.width,0),(self.width,self.height),(0,self.height)]
        
        direction = edge//2 > 0 and -1 or 1
        if(edge%2==0): #horizontal
            delta = 0.5*(newLength-self.width)*direction
            dOffset = self._get_offset(delta)
            pts[edge] = (pts[edge][0]+offset[0]-delta+dOffset,pts[edge][1]+offset[1])
            pts[(edge+1)%4] = (pts[(edge+1)%4][0]+offset[0]+delta+dOffset,pts[(edge+1)%4][1]+offset[1])
        else: #vertical
            delta = 0.5*(newLength-self.height)*direction
            dOffset = self._get_offset(delta)
            pts[edge] = (pts[edge][0]+offset[0],pts[edge][1]+offset[1]-delta+dOffset)
            pts[(edge+1)%4] = (pts[(edge+1)%4][0]+offset[0],pts[(edge+1)%4][1]+offset[1]+delta+dOffset)
        
        align_vector=self._get_align_vector()
        pts = [vadd(pt,align_vector) for pt in pts]
        
        return pts
    
    def _get_align_vector(self):
        #note: alignment is done to the parent rectangle, not the skewed side
        if self.halign == const.CENTER:
            dx = -self.width/2.
        elif self.halign == const.RIGHT:
            dx = -self.width
        else:  # const.LEFT
            dx = 0.

        #note: vertical alignment is flipped from regular rectangle
        if self.valign == const.MIDDLE:
            dy = -self.height/2.
        elif self.valign == const.TOP:
            dy = -self.height
        else:  # const.BOTTOM
            dy = 0.

        return (dx, dy)
    
    def _get_offset(self,delta):
        #labelled like vertical offset, but can technically be applied to any 
        if self.ealign == const.TOP:
            dy = -delta
        elif self.ealign == const.BOTTOM:
            dy = delta
        else:  # const.MIDDLE
            dy = 0.

        return dy
    
class CurveRect(SubscriptAttributes):
    ''' Curved rectangle consisting of a single Polyline and a number of background solids
    '''
    name = 'CURVERECT'
    
    def __init__(self,insert,height,radius,roffset=0,angle=90,ptDensity=60,rotation=0.,color=const.BYLAYER,bgcolor=None,layer='0',linetype=None,ralign=const.BOTTOM,valign=const.BOTTOM,vflip=False,hflip=False, **kwargs):
        self.insert = insert
        self.rotation = math.radians(rotation)
        self.color = color
        self.bgcolor = bgcolor
        self.layer = layer
        self.linetype = linetype
        
        self.points = []
        self.valign = valign
        self.ralign = ralign
        self.height = height
        
        self.roffset=roffset
        self.angle = math.radians(angle)
        self.segments = max(int(ptDensity*angle/360),1)
        
        self.vflip = vflip and -1 or 1
        self.hflip = hflip and -1 or 1
        
        self.r0 = radius
        
    def _get_radius_align(self):

        #by default the radius is defined as the inner radius
        if self.ralign == const.MIDDLE:
            dr = -self.height/2.
        elif self.ralign == const.TOP:
            dr = -self.height
        else:  # const.BOTTOM
            dr = 0.

        return (0, dr)

    def _get_align_vector(self):

        #note: vertical alignment is flipped from regular rectangle
        if self.valign == const.MIDDLE:
            dy = -self.height/2.
        elif self.valign == const.TOP:
            dy = -self.height
        else:  # const.BOTTOM
            dy = 0.

        return (0, dy)
    
    def _build(self):
        data = DXFList()
        ralign = self._get_radius_align()
        self.points = self._calc_points(ralign)
        align_vector = self._get_align_vector()
        self._transform_points(align_vector)
        if self.color is not None:
            data.append(self._build_polyline())
        if self.bgcolor is not None:
            #if _calc_points has been run, rmin is already set
            if self.rmin <= 0:
                #if self.angle%(2*math.pi) == math.radians(90): #rounded corner case
                for i in range(self.segments+1):
                    data.append(self._build_solid_triangle(i))
            else: #rmin>0, normal operation
                for i in range(self.segments+1):
                    data.append(self._build_solid_quad(i))
        return data
        
    def _transform_points(self,align):
        self.points = [vadd(self.insert,  # move to insert point
                            rotate_2d(  # rotate at origin
                                ((point[0]+align[0])*self.hflip,(point[1]+align[1])*self.vflip), self.rotation))
                       for point in self.points]
    
    def _calc_points(self,align):
        #align=self._get_align_vector()
        self.rmin=self.r0+align[1]+self.roffset
        self.rmax=self.r0+self.height+align[1]+self.roffset
        
        dTheta = self.angle/self.segments
        pts = []
        if self.rmin <=0:
            if self.angle%(2*math.pi) != math.radians(90):  #not designed for doing more than one nicely rounded corner at a time
                self.rmin = 0
            pts = [(0,self.rmin-self.r0),(self.rmax*math.sin(self.angle)-self.rmin,self.rmax*math.cos(self.angle)-self.r0+self.rmin)]
            pts = pts + [(self.rmax*math.sin(self.angle-(i+0.5)*dTheta)-self.rmin,self.rmax*math.cos(self.angle-(i+0.5)*dTheta)-self.r0) for i in range(self.segments)] + [(0,self.rmax - self.r0)]
        else:
            pts = [(0,self.rmin-self.r0)]+[(self.rmin*math.sin((i+0.5)*dTheta),self.rmin*math.cos((i+0.5)*dTheta)-self.r0) for i in range(self.segments)]+[(self.rmin*math.sin(self.angle),self.rmin*math.cos(self.angle)-self.r0)]
            pts = pts + [(self.rmax*math.sin(self.angle),self.rmax*math.cos(self.angle)-self.r0)] + [(self.rmax*math.sin(self.angle-(i+0.5)*dTheta),self.rmax*math.cos(self.angle-(i+0.5)*dTheta)-self.r0) for i in range(self.segments)] + [(0,self.rmax - self.r0)]
        
        
        return [vsub(pt,align) for pt in pts]
    
    def _build_polyline(self):
        '''Build the polyline (key component)'''
        polyline = Polyline(self.points, color=self.color, layer=self.layer,flags=0)
        polyline.close() #redundant in most cases
        if self.linetype is not None:
            polyline['linetype'] = self.linetype
        return polyline
    
    def _build_solid_quad(self,i,center=None):
        ''' build a single background solid quadrangle segment '''
        solidpts = [self.points[j] for j in [i,i+1,-i-2,-i-1]]
        return Solid(solidpts, color=self.bgcolor, layer=self.layer)  

    
    def _build_solid_triangle(self,i):
        ''' build a single background solid quadrangle segment '''
        solidpts = [self.points[j] for j in [0,i+1,i+2]]
        return Solid(solidpts, color=self.bgcolor, layer=self.layer)  
    
    def __dxf__(self):
        ''' get the dxf string '''
        return dxfstr(self.__dxftags__())
    
    def __dxftags__(self):
        return self._build()    
        

class InsideCurve(SubscriptAttributes):
    ''' Filled inside corner rounded to radius r consisting of a single Polyline and a number of background solids
    '''
    name = 'INSIDECURVE'
    
    def __init__(self,insert,radius,angle=90,ptDensity=60,rotation=0.,color=const.BYLAYER,bgcolor=None,layer='0',linetype=None,halign=const.RIGHT,vflip=False,hflip=False, **kwargs):
        self.insert = insert
        self.rotation = math.radians(rotation)
        self.color = color
        self.bgcolor = bgcolor
        self.layer = layer
        self.linetype = linetype
        
        self.points = []
        self.halign = halign
        self.r0 = radius
        self.angle = math.radians(angle)
        self.curve_angle = math.radians(180-angle)
        self.segments = int(ptDensity*abs(180-angle)/360)
        
        self.vflip = vflip and -1 or 1
        self.hflip = hflip and -1 or 1
        
    def _get_align_vector(self):

        #note: vertical alignment is flipped from regular rectangle
        if self.halign == const.CENTER:
            dx = -self.height/2.
        elif self.halign == const.LEFT:
            dx = -self.height
        else:  # const.RIGHT
            dx = 0.

        return (0, dx)
    
    def _build(self):
        data = DXFList()
        self.points = self._calc_points()
        self._transform_points()
        if self.color is not None:
            data.append(self._build_polyline())
        if self.bgcolor is not None:
            #if _calc_points has been run, rmin is already set
            for i in range(self.segments):
                data.append(self._build_solid_triangle(i))
        return data
        
    def _transform_points(self):
        align = self._get_align_vector()
        self.points = [vadd(self.insert,  # move to insert point
                            rotate_2d(  # rotate at origin
                                vadd((point[0]*self.hflip,point[1]*self.vflip),align), self.rotation))
                       for point in self.points]
    
    def _calc_points(self):
        #align=self._get_align_vector()
        center = (-self.r0/math.tan(self.angle/2),-self.r0)
        
        dTheta = self.curve_angle/self.segments
        pts = []
        pts = [(0,0)]+[vadd((self.r0*math.sin(i*dTheta),self.r0*math.cos(i*dTheta)),center) for i in range(self.segments+1)]
        
        return pts
    
    def _build_polyline(self):
        '''Build the polyline (key component)'''
        polyline = Polyline(self.points, color=self.color, layer=self.layer,flags=0)
        polyline.close() #redundant in most cases
        if self.linetype is not None:
            polyline['linetype'] = self.linetype
        return polyline

    def _build_solid_triangle(self,i):
        ''' build a single background solid quadrangle segment '''
        solidpts = [self.points[j] for j in [0,i+1,i+2]]
        return Solid(solidpts, color=self.bgcolor, layer=self.layer)  
    
    def __dxf__(self):
        ''' get the dxf string '''
        return dxfstr(self.__dxftags__())
    
    def __dxftags__(self):
        return self._build() 
        
        
        
        
        
        
        