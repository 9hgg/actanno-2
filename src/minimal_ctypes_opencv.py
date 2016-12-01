#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
*****************************************************************************
Minimal ctypes_opencv

Usefull links :
http://docs.python.org/library/ctypes.html
http://code.google.com/p/ctypes-opencv/
 

Authors: Eric Lombardi

Changelog:
30.09.11 CW: add Mac OS X support
22.09.11 EL: begin development
*****************************************************************************
"""

import ctypes
import os
import platform
from ctypes.util import find_library


############################################################

# from ctype_opencv/cxcore.py

class ByRefArg(object):
    '''Just like a POINTER but accept an argument and pass it byref'''
    def __init__(self, atype):
        self.atype = atype

    def from_param(self, param):
        return ctypes.byref(param) if isinstance(param, self.atype) else param

def pointee(ptr, *depends_args):
    """Returns None if ptr is NULL else ptr's object with dependency tuple associated"""
    if bool(ptr):
        z = ptr[0]
        z._depends = depends_args
        return z
    return None
    


c_int_p = ctypes.POINTER(ctypes.c_int)
c_int8_p = ctypes.POINTER(ctypes.c_int8)
c_ubyte_p = ctypes.POINTER(ctypes.c_ubyte)
c_float_p = ctypes.POINTER(ctypes.c_float)
c_double_p = ctypes.POINTER(ctypes.c_double)
c_void_p_p = ctypes.POINTER(ctypes.c_void_p)
c_short_p = ctypes.POINTER(ctypes.c_short)

#
IPL_DEPTH_SIGN = -0x80000000

IPL_DEPTH_1U =  1
IPL_DEPTH_8U =  8
IPL_DEPTH_16U = 16
IPL_DEPTH_32F = 32
IPL_DEPTH_64F = 64

IPL_DEPTH_8S = IPL_DEPTH_SIGN + IPL_DEPTH_8U
IPL_DEPTH_16S = IPL_DEPTH_SIGN + IPL_DEPTH_16U
IPL_DEPTH_32S = IPL_DEPTH_SIGN + 32


# IplTileInfo
class IplTileInfo(ctypes.Structure):
    _fields_ = []
    
IplTileInfo_p = ctypes.POINTER(IplTileInfo)

# IplROI
class IplROI(ctypes.Structure):
    _fields_ = [
        ('coi', ctypes.c_int),
        ('xOffset', ctypes.c_int),
        ('yOffset', ctypes.c_int),
        ('width', ctypes.c_int),
        ('height', ctypes.c_int),
    ]    

IplROI_p = ctypes.POINTER(IplROI)

# CvArr
class CvArr(ctypes.Structure):
    _fields_ = []
    
CvArr_p = ctypes.POINTER(CvArr)
CvArr_r = ByRefArg(CvArr)

# IplImage
class IplImage(CvArr):
    def __del__(self):
        if self._owner == 1: # own header only
            _cvReleaseImageHeader(IplImage_p(self))
        elif self._owner == 2: # own data but not header
            _cvReleaseData(self)
        elif self._owner == 3: # own header and data
            _cvReleaseImage(IplImage_p(self))

IplImage_p = ctypes.POINTER(IplImage)

IplImage._fields_ = [("nSize", ctypes.c_int),
        ("ID", ctypes.c_int),
        ("nChannels", ctypes.c_int),
        ("alphaChannel", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("colorModel", ctypes.c_char * 4),
        ("channelSeq", ctypes.c_char * 4),
        ("dataOrder", ctypes.c_int),
        ("origin", ctypes.c_int),
        ("align", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("roi", IplROI_p),
        ("maskROI", IplImage_p),
        ("imageID", ctypes.c_void_p),
        ("tileInfo", IplTileInfo_p),
        ("imageSize", ctypes.c_int),
        ("imageData", c_int8_p),
        ("widthStep", ctypes.c_int),
        ("BorderMode", ctypes.c_int * 4),
        ("BorderConst", ctypes.c_int * 4),
        ("imageDataOrigin", c_int8_p)]

#
def detect_opencv():
    def find_lib(name):
        z = ctypes.util.find_library(name)
        print "using library ", z #EL+
        if z is None:
            raise ImportError("OpenCV's shared library '%s' is not found. Make sure you have its path included in your PATH variable." % name)
        return z
        
    print "your os:",os.name, platform.system()
        
    if os.name == 'posix':
    
        # ---- Mac Os
        if platform.system() == 'Darwin':
            # cxDLL = ctypes.cdll.LoadLibrary(find_lib('opencv_core'))
            cxDLL = ctypes.cdll.LoadLibrary('/opt/local/lib/libopencv_core.dylib')            
            cvDLL = None
            hgDLL = None    
    
        # ---- Linux
        else:
            try:
                cxDLL = ctypes.cdll.LoadLibrary(find_lib('cxcore'))
            except:
                cxDLL = ctypes.cdll.LoadLibrary(find_lib('opencv_core'))
            #cvDLL = ctypes.cdll.LoadLibrary(find_lib('cv'))
            #hgDLL = ctypes.cdll.LoadLibrary(find_lib('highgui'))
            cvDLL = None
            hgDLL = None

    # ---- Windows
    elif os.name == 'nt':
        try:
            cxDLL = ctypes.cdll.cxcore110
            #cvDLL = ctypes.cdll.cv110
            #hgDLL = ctypes.cdll.highgui110
            cvDLL = None
            hgDLL = None
        except:
            try:
                cxDLL = ctypes.cdll.cxcore100
                #cvDLL = ctypes.cdll.cv100
                #hgDLL = ctypes.cdll.highgui100
                cvDLL = None
                hgDLL = None
            except:
                raise ImportError("Cannot import OpenCV's .DLL files. Make sure you have their paths included in your PATH variable.")

    else:
        raise NotImplementedError("Your OS is not supported. Or you can rewrite this detect_opencv() function to support it.")

    return cxDLL, cvDLL, hgDLL

_cxDLL, _cvDLL, _hgDLL = detect_opencv()

#
def cfunc(name, dll, result, *args):
    '''build and apply a ctypes prototype complete with parameter flags
    e.g.
cvMinMaxLoc = cfunc('cvMinMaxLoc', _cxDLL, None,
                    ('image', IplImage_p, 1),
                    ('min_val', c_double_p, 2),
                    ('max_val', c_double_p, 2),
                    ('min_loc', CvPoint_p, 2),
                    ('max_loc', CvPoint_p, 2),
                    ('mask', IplImage_p, 1, None))
means locate cvMinMaxLoc in dll _cxDLL, it returns nothing.
The first argument is an input image. The next 4 arguments are output, and the last argument is
input with an optional value. A typical call might look like:

min_val,max_val,min_loc,max_loc = cvMinMaxLoc(img)
    '''
    atypes = []
    aflags = []
    for arg in args:
        atypes.append(arg[1])
        aflags.append((arg[2], arg[0]) + arg[3:])
    return ctypes.CFUNCTYPE(result, *atypes)((name, dll), tuple(aflags))

#
class CvSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int),
                ("height", ctypes.c_int)]
                
CvSize_p = ctypes.POINTER(CvSize)
#CvSize_r = ByRefArg(CvSize)

def cvSize(x, y):
    return CvSize(ctypes.c_int(x), ctypes.c_int(y))


# Releases image header
_cvReleaseImageHeader = cfunc('cvReleaseImageHeader', _cxDLL, None,
    ('image', ByRefArg(IplImage_p), 1), # IplImage** image 
)


# Allocates, initializes, and returns structure IplImage
_cvCreateImageHeader = cfunc('cvCreateImageHeader', _cxDLL, IplImage_p,
    ('size', CvSize, 1), # CvSize size
    ('depth', ctypes.c_int, 1), # int depth
    ('channels', ctypes.c_int, 1), # int channels 
)

def cvCreateImageHeader(size, depth, channels):
    """IplImage cvCreateImageHeader(CvSize size, int depth, int channels)

    Allocates, initializes, and returns structure IplImage
    """
    z = pointee(_cvCreateImageHeader(size, depth, channels))
    z._owner = 1 # header only
    return z


# Releases array data
_cvReleaseData = cfunc('cvReleaseData', _cxDLL, None,
    ('arr', CvArr_r, 1), # CvArr* arr 
)

def cvReleaseData(arr):
    """void cvReleaseData(CvArr arr)

    Releases array data
    """
    _cvReleaseData(arr)
    if isinstance(arr, IplImage):
        arr._owner &= ~2 # arr does not own data anymore

# Assigns user data to the array header
_cvSetData = cfunc('cvSetData', _cxDLL, None,
    ('arr', CvArr_r, 1), # CvArr* arr
    ('data', ctypes.c_void_p, 1), # void* data
    ('step', ctypes.c_int, 1), # int step 
)

def cvSetData(arr, data, step):
    """void cvSetData(CvArr arr, void* data, int step)

    Assigns user data to the array header
    """
    if isinstance(arr, IplImage):
        if arr._owner & 2:
            cvReleaseData(arr) # release old data if arr owns it
        _cvSetData(arr, data, step)
    else:
        _cvSetData(arr, data, step)


############################################################

# from ctype_opencv/interfaces.py

_pil_image_bands_to_ipl_attrs = {
    ('L',): (IPL_DEPTH_8U, 1, 1, "raw", "L"),
    ('I',): (IPL_DEPTH_32S, 4, 1, "raw", "I"),
    ('F',): (IPL_DEPTH_32F, 4, 1, "raw", "F"),
    ('R', 'G', 'B'): (IPL_DEPTH_8U, 1, 3, "raw", "BGR"),
    ('R', 'G', 'B', 'A'): (IPL_DEPTH_8U, 1, 4, "raw", "BGRA"),
}

def cvCreateImageFromPilImage(pilimage):
    """Converts a PIL.Image into an IplImage
    
    Right now, ctypes-opencv can only convert PIL.Images of band ('L'), 
    ('I'), ('F'), ('R', 'G', 'B'), or ('R', 'G', 'B', 'A'). Whether the 
    data array is copied from PIL.Image to IplImage or shared between
    the two images depends on how PIL converts the PIL.Image's data into
    a string (i.e. via function PIL.Image.tostring()).
    """
    try:
        depth, elem_size, nchannels, decoder, mode = _pil_image_bands_to_ipl_attrs[pilimage.getbands()]
    except KeyError:
        raise TypeError("Don't know how to convert the image. Check its bands and/or its mode.")
    img = cvCreateImageHeader(cvSize(pilimage.size[0], pilimage.size[1]), depth, nchannels)
    step = pilimage.size[0] * nchannels * elem_size
    #data = pilimage.tostring(decoder, mode, step)
    data = pilimage.tobytes(decoder, mode, step)
    cvSetData(img, data, step)
    img._depends = (data,)
    return img




