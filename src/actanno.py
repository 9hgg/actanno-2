#!/usr/bin/env python

#####!/usr/bin/python
# -*- coding: utf-8 -*-

from Tkinter import Tk, Canvas, Frame, BOTH, Listbox, Toplevel, Message, Button, Entry, Scrollbar, Scale, IntVar
from Tkinter import N, S, W, E, NW, SW, NE, SE, CENTER, END, LEFT, RIGHT, X, Y, TOP, BOTTOM, HORIZONTAL
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageTk
import sys
import glob
import copy
import tkMessageBox
import os
import xml.etree.ElementTree as xml

import matplotlib.image as mpimg
import numpy as np

from minimal_ctypes_opencv import *
from config import cfg
from config import cfg_from_file

# ***************************************************************************
# Global constants
# ***************************************************************************

MAX_objectId = 100
CORNER_DIST_THR = 8
CENTER_DIST_THR = 10
CORNER_SIZE = 30
CENTER_SIZE = 30
JUMP_FRAMES = 25

TITLE = "Actanno V2.0"


# ***************************************************************************
# The data structure storing the annotations
# ***************************************************************************

# change the list below to define your own classes
classnames = ["null"]
# classnames = ["head","fullbody","right-hand","left-hand"]
# ***************************************************************************
# XML parsing helper functions
# ***************************************************************************

# Return the the given tag in the given tree, and ensure that this tag is
# present only a single time.
bindings="\
		--------------------------------------------------------\n \
		Navigation : \n \
			<Key-Left> : prevFrame \n \
			<Key-BackSpace> : prevFrame \n \
			<Key-Right> : nextFrame \n \
			<Next> : nextFrameFar \n \
			<Prior> : prevFrameFar \n \
		----------------------------\n \
		Save and quit : \n \
			q : quit \n \
			s : saveXML \n \
		--------------------------------------------------------\n \
		Propagation : \n \
			f : go to next frame + force propagation \n \
			p : go to next frame + force propagation of rectangle with focus \n \
			<Key-space> : go to next frame + propagation (no forcing)\n \
		--------------------------------------------------------\n \
		Deletion : \n \
			d : delete rectangle with focus \n \
			D : delete all rectangles \n \
		--------------------------------------------------------\n \
		Select objects : \n \
			1 : choseobjectId1 \n \
			2 : choseobjectId2 \n \
			3 : choseobjectId3 \n \
			4 : choseobjectId4 \n \
			5 : choseobjectId5 \n \
			6 : choseobjectId6 \n \
			7 : choseobjectId7 \n \
			8 : choseobjectId8 \n \
			9 : choseobjectId9 \n \
			0 : choseobjectId10 \n"



def getSingleTag(tree, tagname):
	rv = tree.findall(tagname)
	if len(rv) != 1:
		tkMessageBox.showinfo(TITLE, "tag " + tagname + " needs to occur a single time at this point!")
		sys.exit(1)
	return rv[0]

# Return an attribute value. Check for its existence

def getAtt(node, attname):
	rv = node.get(attname)
	if rv == None:
		tkMessageBox.showinfo(TITLE, "attribute " + attname + " not found in tag " + node.tag)
		sys.exit(1)
	return rv

# ***************************************************************************


class AARect:
	"""A rectangle (bounding box) and its running id"""

	def __init__(self, x1, y1, x2, y2, objectId):
		if x1 < x2:
			self.x1 = x1
			self.x2 = x2
		else:
			self.x1 = x2
			self.x2 = x1
		if y1 < y2:
			self.y1 = y1
			self.y2 = y2
		else:
			self.y1 = y2
			self.y2 = y1
		self.objectId = objectId

	def show(self):
		print "x1=", self.x1, "  y1=", self.y1, "  x2=", self.x2, "  y2=", self.y2, "  id=", self.objectId


# ***************************************************************************
# C type matching Python type
class c_AARect(ctypes.Structure):
   	_fields_ = [("x1", ctypes.c_int),("y1", ctypes.c_int),("x2", ctypes.c_int),("y2", ctypes.c_int),("objectId", ctypes.c_int)]

# ***************************************************************************
# convert AARect to c_AARect
def to_c_AARect(r):
	return c_AARect(x1=int(r.x1), y1=int(r.y1), x2=int(r.x2), y2=int(r.y2), objectId=int(r.objectId))

# ***************************************************************************
# convert c_AARect to AARect
def to_AARect(c_r):
	return AARect(c_r.x1, c_r.y1, c_r.x2, c_r.y2, c_r.objectId)


# ***************************************************************************
class SemMousePos:
	"""A semantic mouse position: in which rectangle (index) is the mouse
	   and which semantic position does it occupy.
	   sempose can be:
	   ul	upper left corner
	   ur	upper right corner
	   ll	lower left corner
	   lr	lower right corner
	   c	center
	   g	general position in the recangle
	   n	no rectangles"""

	def __init__(self, index, sempos):
		self.index = index
		self.sempos = sempos

# ***************************************************************************


class AAFrame:
	"""All rectangles of a frame"""

	def __init__(self):
		self.rects = []

	def getRects(self):
		return self.rects

	# Check the position of the mouse cursor with respect to corners of all
	# the rectangles, as well as the centers. If it is not near anything,
	# still check for the nearest center.
	# position x,y
	def getSemMousePos(self, x, y):

		# First check for the corners
		minval = 99999999
		argindex = -1
		for (i, r) in enumerate(self.rects):
			d = (r.x1 - x) * (r.x1 - x) + (r.y1 - y) * (r.y1 - y)
			if d < minval:
				minval = d
				argindex = i
				argsem = "ul"
			d = (r.x1 - x) * (r.x1 - x) + (r.y2 - y) * (r.y2 - y)
			if d < minval:
				minval = d
				argindex = i
				argsem = "ll"
			d = (r.x2 - x) * (r.x2 - x) + (r.y1 - y) * (r.y1 - y)
			if d < minval:
				minval = d
				argindex = i
				argsem = "ur"
			d = (r.x2 - x) * (r.x2 - x) + (r.y2 - y) * (r.y2 - y)
			if d < minval:
				minval = d
				argindex = i
				argsem = "lr"

		# We near enough to a corner, we are done
		if minval < CORNER_DIST_THR * CORNER_DIST_THR:
			return SemMousePos(argindex, argsem)

		# Now check for the nearest center
		minval = 99999999
		argindex = -1
		for (i, r) in enumerate(self.rects):
			cx = 0.5 * (r.x1 + r.x2)
			cy = 0.5 * (r.y1 + r.y2)
			d = (cx - x) * (cx - x) + (cy - y) * (cy - y)
			if d < minval:
				minval = d
				argindex = i

		if argindex < 0:
			return SemMousePos(-1, "n");

		if minval < CENTER_DIST_THR * CENTER_DIST_THR:
			return SemMousePos(argindex, "c")
		else:
			return SemMousePos(argindex, "g")

# ***************************************************************************


class AAControler:

	def __init__(self):
		# An array holding an AAFrame object for each frame of the video
		self.frames = []
		# An array holding the classnr for each object nr. ("objectId")
		self.ClassAssignations = []
		# The nr. of the currently visible frame
		self.curFrameNr = 0
		self.switchActivated = False
		#self.videoname = ""

		if len(sys.argv) < 1:
			self.usage()

		# dataset name
		self.datasetName = cfg.DATASET_NAME
		self.videoname = cfg.FOLDER_NAME
		print "self.videoname=",self.videoname
		# owner name
		self.owner = cfg.OWNER
		# folder name
		self.folderName = cfg.FOLDER_NAME
		# voc path
		self.vocPath =cfg.MAIN_DIR+cfg.VOC_DIR
		# rgb
		prefix=cfg.MAIN_DIR+cfg.RGB_PREFIX
		self.filenames=sorted(glob.glob(prefix+"*"))
		if len(self.filenames)<1:
			print >> sys.stderr, "Did not find any rgb frames! Is the prefix correct?"
			self.usage()
		for i in range(len(self.filenames)):
			self.frames.append(AAFrame())

		# if depth
		if not cfg.D_PREFIX=="default":
			print("USING RGB AND DEPTH")
			self.depth_available = True
			prefix_depth = cfg.MAIN_DIR+cfg.D_PREFIX
			self.filenames_depth=sorted(glob.glob(prefix_depth+"*"))
			if len(self.filenames_depth)<1:
				print >> sys.stderr, "Did not find any depths frames! Is the prefix correct?"
				self.usage()

			self.array_rgb2depth_ts = np.zeros(len(self.filenames),dtype=np.int)
			for id_img_rgb,filename_rgb in enumerate(self.filenames):
				ts_rgb = int(filename_rgb.split("-")[-1].split(".")[0])
				id_img_depth_closest = 0
				ts_depth_closest = 0
				for id_img_depth,filename_depth in enumerate(self.filenames_depth):
					ts_depth = int(filename_depth.split("-")[-1].split(".")[0])
					if abs(ts_rgb-ts_depth)<=abs(ts_rgb-ts_depth_closest):
						ts_depth_closest = ts_depth
						id_img_depth_closest = id_img_depth
				self.array_rgb2depth_ts[id_img_rgb]=id_img_depth_closest
			# print self.array_rgb2depth_ts
		else:
			print("USING RGB ONLY")
			self.depth_available = False
			prefix_depth = ""

		self.outputfilename=cfg.MAIN_DIR+cfg.XML_PREFIX
		# If the given XML file exists, parse it

		if not os.path.isdir(os.path.dirname(self.outputfilename)):
			os.makedirs(os.path.dirname(self.outputfilename))

		if os.path.isfile(self.outputfilename):
			if os.stat(self.outputfilename).st_size>0:
				self.parseXML()
		else:
			# If it does NOT exist, let's try to create one
			try:
				fd=open(self.outputfilename,'w')

			# Unsuccessful -> the given directory does not exist
			except:
				s="Could not save to the specified XML file. Please check the location. Does the directory exist?"
				tkMessageBox.showinfo(TITLE,s)
				sys.exit(1)
			tkMessageBox.showinfo(TITLE, "XML File "+self.outputfilename+" does not exist. Creating a new one.")

	def usage(self):
		print >> sys.stderr, "usage:"
		print >> sys.stderr, sys.argv[0]," <output-xml-filename> <framefileprefix RGB> <framefileprefix depth>"
		sys.exit(1);

	# Check the current annotation for validity
	def checkValidity(self):
		msg=''

		# Check for non contiguous activities.
		# Keep a dictionary which holds for each activity the framenr of the
		# last frame
		acts = {}
		#for (frnr,fr) in enumerate(self.frames):
		#	for r in fr.rects:
		#		if r.objectId in acts:
		#			if frnr-acts[r.objectId] > 1:
		#				msg = msg+"Activity nr. "+str(r.objectId)+" has a hole after frame nr. "+str(acts[r.objectId])+".\n"
		#		acts[r.objectId] = frnr;

		# Check for several occurrences of a objectId in the same frame.
		for (frnr,fr) in enumerate(self.frames):
			msg=msg+self.checkValidityFrame(frnr)

		# Check for unassigned ClassAssignations (no known object class)
		msg2=''
		for (i,x) in enumerate(self.ClassAssignations):
			if x<0:
				msg2=msg2+str(i+1)+","
		if msg2<>'':
			msg2="The following activities do not have assigned classes: "+msg2+"\n"
		msg=msg+msg2

		return msg

	# Check a single frame for validity (multiple identical ClassAssignations)
	def checkValidityFrame(self, framenr):
		msg=''
		ids=set()
		for r in self.frames[framenr].rects:
			if r.objectId in ids:
				msg = msg+'Activity nr. '+str(r.objectId)+' occurs multiple times in frame nr. '+str(framenr+1)+'.\n'
			else:
				ids.add(r.objectId)
		return msg

	# Open the image corresponding to the current frame number,
	# set the property self.curImage, and return it
	def curFrame(self):
		if self.switchActivated and self.depth_available:
			# find the depth image whose timestamp is the closer from the rgb image
			# print "using depth images"
			name,ext=os.path.splitext(self.filenames_depth[self.array_rgb2depth_ts[self.curFrameNr]])
			path = self.filenames_depth[self.array_rgb2depth_ts[self.curFrameNr]]
		else:
			# print "using rgb images"
			name,ext=os.path.splitext(self.filenames[self.curFrameNr])
			path = self.filenames[self.curFrameNr]
		# print name
		if ext == ".png":
			# png = Image.open(self.filenames[self.curFrameNr])#.convert('L')
			img_matplotlib=mpimg.imread(path)
			value_max = np.amax(img_matplotlib)
			scale = 254. / value_max
			png = Image.fromarray(np.uint8((img_matplotlib)*scale))
			# print(40*"-")
			# print "format :",png.format
			# print "size :", png.size
			# print "mode :", png.mode
			# png.load()
			data = list(png.getdata())
			# print "max(data)", max(data),"min(data)", min(data)
			self.curImage = png.convert('RGB')
		elif ext == ".jpg":
				self.curImage = Image.open(self.filenames[self.curFrameNr])
		else:
			print "def curFrame(self): Extension not supported but trying anyway. [",ext,"]"
			self.curImage = Image.open(self.filenames[self.curFrameNr])
		   	# print "frame nr. ",self.curFrameNr, "=",self.filenames[self.curFrameNr]
		return self.curImage

	# Remove all rectangles of the current frame
	def deleteAllRects(self):
		self.frames[self.curFrameNr].rects = []

	# Remove the rectangle with the given index from the list
	# of rectangles of the currently selected frame
	def deleteRect(self, index):
		del self.frames[self.curFrameNr].rects[index];

	def nextFrame(self,doPropagate,force):
		if self.curFrameNr<len(self.filenames)-1:
			self.curFrameNr+=1
		# if the next frame does NOT contain any rectangles,
		# propagate the previous ones
		if doPropagate:
			x=len(self.frames[self.curFrameNr].rects)

			print "we have",x,"frames"
			if x>0 and not force :
				print "No propagation, target frame is not empty"
			else:
				self.frames[self.curFrameNr].rects = []
				y = len(self.frames[self.curFrameNr-1].rects)
				if y>0:
					# Tracking code goes here .....
					print "Propagating ",y,"rectangle(s) to next frame"

					if trackingLib == None:
						# simple copy
						print "simple copy"
						self.curFrame()
						self.frames[self.curFrameNr].rects = copy.deepcopy(self.frames[self.curFrameNr-1].rects)
					else:
						# JM tracking
						print "use JM tracking"
						self.oldFrame = self.curImage
						self.curFrame()

						for inrect in self.frames[self.curFrameNr-1].rects:
							# convert PIL image to OpenCV image
							cvOldImg = cvCreateImageFromPilImage(self.oldFrame)
							cvCurImg = cvCreateImageFromPilImage(self.curImage)
							# No need to invoke cvRelease...()

							# convert Python types to C types
							c_inrect = to_c_AARect(inrect)
							c_outrect = c_AARect()

							# call C++ tracking lib
							trackingLib.track_block_matching( ctypes.byref(cvOldImg), ctypes.byref(cvCurImg), ctypes.byref(c_inrect), ctypes.byref(c_outrect))

							# convert C types to Python types
							outrect = to_AARect(c_outrect)
							self.frames[self.curFrameNr].rects.append(outrect)

				else:
					print "No frames to propagate"

		else:
			self.curFrame()
		self.exportXMLFilename("save.xml")
		return self.curImage

	def nextFramePropCurrentRect(self,rect_index):
		propagateId = self.frames[self.curFrameNr].rects[rect_index].objectId
		print "Rect[",rect_index,"].objectId == ",  propagateId

		if self.curFrameNr<len(self.filenames)-1:
			self.curFrameNr+=1
			print "Propagating rectangle",propagateId," to new frame"
			x = len(self.frames[self.curFrameNr].rects)
			y = len(self.frames[self.curFrameNr-1].rects)
			print "we have ",x," objects"
			print "we had  ",y," objects"

			# self.frames[self.curFrameNr].rects = []

			# get old rect to propagate
			rectToPropagate = self.frames[self.curFrameNr-1].rects[rect_index]

			# get his new position by tracking
			if trackingLib == None:
				# simple copy
				print "simple copy"
				self.curFrame()
				rectPropagated = copy.deepcopy(rectToPropagate)
			else:
				# JM tracking
				print "use JM tracking"
				self.oldFrame = self.curImage
				self.curFrame()


				# convert PIL image to OpenCV image
				cvOldImg = cvCreateImageFromPilImage(self.oldFrame)
				cvCurImg = cvCreateImageFromPilImage(self.curImage)
				# No need to invoke cvRelease...()

				# convert Python types to C types
				c_inrect = to_c_AARect(rectToPropagate)
				c_outrect = c_AARect()

				# call C++ tracking lib
				trackingLib.track_block_matching( ctypes.byref(cvOldImg), ctypes.byref(cvCurImg), ctypes.byref(c_inrect), ctypes.byref(c_outrect))

				# convert C types to Python types
				rectPropagated = to_AARect(c_outrect)
				# self.frames[self.curFrameNr].rects.append(outrect)

			rectPropagated.objectId = propagateId

			# update it or add it
			rectAlreadyExists = False
			for i,currentrect in enumerate(self.frames[self.curFrameNr].rects):
				if currentrect.objectId == propagateId:
					print "Rectangle found. Updating."
					self.frames[self.curFrameNr].rects[i] = copy.deepcopy(rectPropagated)
					rectAlreadyExists = True
					break

			if not rectAlreadyExists:
				self.frames[self.curFrameNr].rects.append(rectPropagated)

		# self.curFrame()
		self.exportXMLFilename("save.xml")
		return self.curImage

	def changeFrame(self, id_frame):
		self.curFrameNr=int(id_frame)-1
		self.exportXMLFilename("save.xml")
		return self.curFrame()

	def nextFrameFar(self):
		if self.curFrameNr<len(self.filenames)-JUMP_FRAMES:
			self.curFrameNr+=JUMP_FRAMES
		else:
			self.curFrameNr=len(self.filenames)-1
		self.exportXMLFilename("save.xml")
		return self.curFrame()

	def prevFrame(self):
		if self.curFrameNr>0:
			self.curFrameNr-=1
		self.exportXMLFilename("save.xml")
		return self.curFrame()

	def prevFrameFar(self):
		if self.curFrameNr>=JUMP_FRAMES:
			self.curFrameNr-=JUMP_FRAMES
		else:
			self.curFrameNr=0
		self.exportXMLFilename("save.xml")
		return self.curFrame()

	def getRects(self):
		return self.frames[self.curFrameNr].getRects()

	def addRect(self,x1,y1,x2,y2,objectId,fnr=-1):
		if fnr==-1:
			fnr=self.curFrameNr
		if fnr>=len(self.frames):
			raise Exception()
		self.frames[fnr].getRects().append(AARect(x1,y1,x2,y2,objectId))

	def delRect(self,index):
		del self.frames[self.curFrameNr].getRects()[index]

	def getSemMousePos(self,x,y):
		return self.frames[self.curFrameNr].getSemMousePos(x,y)

	# Update the running id for a rectangle index
	def updateobjectId(self,indexRect,newId):
		self.frames[self.curFrameNr].rects[indexRect].objectId=newId
		self.useobjectId(newId)

	# Tell the system the given objectId is used. If the array holding the classes
	# for the different ids is not large enough, grow it and insert -1 as class
	def useobjectId(self,newId):
		neededcap=newId-len(self.ClassAssignations)
		if neededcap>0:
			for i in range(neededcap):
				self.ClassAssignations.append(-1)
		print "new run id array",self.ClassAssignations

	def exportXML(self):
		self.exportXMLFilename(self.outputfilename)

	def exportXMLFilename(self,filename):
		# Get maximum running id
		maxid=-1
		for (i,f) in enumerate(self.frames):
			for (j,r) in enumerate(f.getRects()):
				if r.objectId > maxid:
					maxid=r.objectId

		try:
			fd=open(filename,'w')
		except:
			tkMessageBox.showinfo(TITLE, "Could not save to the specified XML file. Please check the location. Does the directory exist?")
		print >> fd, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
		print >> fd, "<tagset>"
		print >> fd, "  <video>"
		print >> fd, "	<videoName>"+self.videoname+"</videoName>"

		# self.filenames[self.curFrameNr]
		# Travers all different running id's
		for curObjectId in range(maxid):
			foundRects=False
			for (i,f) in enumerate(self.frames):
				for (j,r) in enumerate(f.getRects()):
					if r.objectId==curObjectId+1:
						if not foundRects:
							foundRects=True
							fd.write ("	<object nr=\""+str(curObjectId+1)+"\" class=\""+str(self.ClassAssignations[curObjectId])+"\">\n")
						s="	  <bbox x=\""+str(int(r.x1))+"\" y=\""+str(int(r.y1))
						s=s+"\" width=\""+str(int(r.x2-r.x1+1))+"\" height=\""+str(int(r.y2-r.y1+1))
						s=s+"\" framenr=\""+str(i+1)
						s=s+"\" framefile=\""+self.filenames[i]+"\"/>\n"
						fd.write(s)
			if foundRects:
				print >> fd, "	</object>"
		print >> fd, "  </video>"
		print >> fd, "</tagset>"
		fd.close()

	def exportXML2voc(self):
		for (i,f) in enumerate(self.frames):
			head, tail = os.path.split(self.filenames[i])
			filename = self.vocPath+tail[:-3]+"xml"
			try:
				fd=open(filename,'w')
			except:
				tkMessageBox.showinfo(TITLE, "Could not save to the specified XML file. Please check the location. Does the directory exist?")

			print >> fd, "<annotation>"
			print >> fd, "	<folder>"+self.folderName+"</folder>"
			print >> fd, "	<filename>"+tail+"</filename>"
			print >> fd, "	<source>"
			print >> fd, "		<database>The "+self.datasetName+" database</database>"
			print >> fd, "	</source>"
			print >> fd, "	<owner>"+self.owner+"</owner>"
			print >> fd, "	<size>"
			print >> fd, "		<width>640</width>"
			print >> fd, "		<height>480</height>"
			print >> fd, "		<depth>1</depth>"
			print >> fd, "	</size>"
			print >> fd, "	<segmented>0</segmented>"


			for (j,r) in enumerate(f.getRects()):
				print >> fd, "	<object>"
				print >> fd, "		<name>"+classnames[self.ClassAssignations[r.objectId-1]]+"</name>"
				print >> fd, "		<pose>unknown</pose>"
				print >> fd, "		<truncated>-1</truncated>"
				print >> fd, "		<difficult>0</difficult>"
				print >> fd, "		<bndbox>"
				print >> fd, "			<xmin>"+str(int(r.x1))+"</xmin>"
				print >> fd, "			<ymin>"+str(int(r.y1))+"</ymin>"
				print >> fd, "			<xmax>"+str(int(r.x2))+"</xmax>"
				print >> fd, "			<ymax>"+str(int(r.y2))+"</ymax>"
				print >> fd, "		</bndbox>"
				print >> fd, "	</object>"

			print >> fd, "</annotation>"
			fd.close()

	def parseXML(self):
		tree = xml.parse(self.outputfilename)
		rootElement = tree.getroot()

		# Get the single video tag
		vids=tree.findall("video")
		if len(vids)<1:
			tkMessageBox.showinfo(TITLE, "No <video> tag found in the input XML file!")
			sys.exit(1)
		if len(vids)>1:
			tkMessageBox.showinfo(TITLE, "Currently only a single <video> tag is supported per XML file!")
			sys.exit(1)
		vid=vids[0]

		# Get the video name
		#x=getSingleTag(vid,"videoName")
		#if (x.text is None) or (len(x.text)==0) or (x.text=="NO-NAME"):
		#	tkMessageBox.showinfo(TITLE, "The video name in the given XML file is empty. Please provide the correct name before saving the file.")
		#	self.videoname="NO-NAME"
		#else:
		#	self.videoname=x.text

		# Get all the objects
		objectnodes=vid.findall("object")
		if len(objectnodes)<1:
			tkMessageBox.showinfo(TITLE, "The given XML file does not contain any objects.")
		for a in objectnodes:
			# Add the classnr to the objectId array. Grow if necessary
			anr=int(getAtt(a,"nr"))
			aclass=int(getAtt(a,"class"))
			# print "-----",anr,aclass
			# print len(self.ClassAssignations)
			if len(self.ClassAssignations)<anr:
				# print "Growing objectId:"
				self.ClassAssignations += [None]*(anr-len(self.ClassAssignations))
			self.ClassAssignations[anr-1]=aclass
			# print "size of objectId array:", len(self.ClassAssignations), "array:", self.ClassAssignations

			# Get all the bounding boxes for this object
			bbs=a.findall("bbox")
			if len(bbs)<1:
				tkMessageBox.showinfo(TITLE, "No <bbox> tags found for an object in the input XML file!")
				sys.exit(1)
			for bb in bbs:

				# Add the bounding box to the frames() list
				bfnr=int(getAtt(bb,"framenr"))
				bx=int(getAtt(bb,"x"))
				by=int(getAtt(bb,"y"))
				bw=int(getAtt(bb,"width"))
				bh=int(getAtt(bb,"height"))
				try:
					self.addRect(bx,by,bx+bw-1,by+bh-1,anr,bfnr-1)
				except:
					print "*** ERROR ***"
					print "The XML file contains rectangles in frame numbers which are outside of the video"
					print "(frame number too large). Please check whether the XML file really fits to these"
					print "frames."
					sys.exit(1)

# ***************************************************************************
# GUI
# The state variable self.state can take one of the following values:
# ul 	we are currently moving the upper left corner
# ur 	we are currently moving the upper right corner
# ll 	we are currently moving the lower left corner
# lr 	we are currently moving the lower right corner
# c 	we are currently moving the window
# d	we are currently drawing a new rectangle
# i	we are currently choosing the running id
# "" 	(empty) no current object
# ***************************************************************************

class Example(Frame):

	def __init__(self, parent, aCurPath):
		Frame.__init__(self, parent)
		self.parent = parent
		self.curPath = aCurPath
		self.ct = AAControler();
		fontPath = os.path.dirname(os.path.realpath(__file__))
		self.imgFont = ImageFont.truetype(fontPath + "/FreeSans.ttf", 30)
		self.initUI()
		self.eventcounter = 0

	# Interface startup: create all widgets and create key and mouse event
	# bindings
	def initUI(self):
		self.parent.title(TITLE+" (frame nr.1 of "+str(len(self.ct.filenames))+")")
		self.pack(fill=BOTH, expand=1)
		self.img = self.ct.curFrame()
		self.curFrame = ImageTk.PhotoImage(self.img)

		self.imgTrash = ImageTk.PhotoImage(Image.open(self.curPath+"/trashcan.png"))
		self.imgMove = ImageTk.PhotoImage(Image.open(self.curPath+"/move.png"))
		# create canvas
		self.canvas = Canvas(self.parent, width=self.img.size[0], height=self.img.size[1])

		# create scale bar
		self.scalevar = IntVar()
		self.xscale = Scale(self.parent,variable = self.scalevar,from_=1, to=len(self.ct.filenames), orient=HORIZONTAL, command=self.changeFrame)


		self.canvas.create_image(0, 0, anchor=NW, image=self.curFrame)



		self.objectIdbox = Listbox(self.parent)
		self.switchbutton = Button(self.parent, text="RGB <-> Depth")
		self.savebutton = Button(self.parent, text="SAVE")
		self.export2voc = Button(self.parent, text="EXPORT2VOC")
		self.quitbutton = Button(self.parent, text="QUIT")
		self.fnEntry = Entry(self.parent)#, state='readonly')
		self.grid(sticky=W+E+N+S)

		# position
		self.canvas.grid(row=0,column=0,rowspan=6)
		self.objectIdbox.grid(row=0,column=1,sticky=N+S)
		self.fnEntry.grid(row=1,column=1)
		self.switchbutton.grid(row=2,column=1)
		self.savebutton.grid(row=3,column=1)
		self.export2voc.grid(row=4,column=1)
		self.quitbutton.grid(row=5,column=1)
		self.xscale.grid(row=6,sticky=W+E)

		# bindings
		self.canvas.bind ("<Key-Left>", self.prevFrame)
		self.canvas.bind ("<Key-BackSpace>", self.prevFrame)
		self.canvas.bind ("<Key-Right>", self.nextFrame)
		self.canvas.bind ("<Next>", self.nextFrameFar)
		self.canvas.bind ("<Prior>", self.prevFrameFar)   # the space key
		self.canvas.bind ("<Motion>", self.mouseMove)
		self.canvas.bind ("<Button-1>", self.leftMouseDown)
		self.canvas.bind ("<ButtonRelease-1>", self.leftMouseUp)
		self.canvas.bind ("<Button-3>", self.rightMouseDown)
		self.canvas.bind ("<ButtonRelease-3>", self.rightMouseUp)
		self.canvas.bind ("q", self.quit)
		self.canvas.bind ("s", self.saveXML)
		self.canvas.bind ("f", self.nextFrameWPropForced)
		self.canvas.bind ("p", self.nextFrameWPropForcedSelectedRect)
		self.canvas.bind ("d", self.deleteCurRect)
		self.canvas.bind ("D", self.deleteAllRects)
		self.canvas.bind ("1", self.choseobjectId1)
		self.canvas.bind ("2", self.choseobjectId2)
		self.canvas.bind ("3", self.choseobjectId3)
		self.canvas.bind ("4", self.choseobjectId4)
		self.canvas.bind ("5", self.choseobjectId5)
		self.canvas.bind ("6", self.choseobjectId6)
		self.canvas.bind ("7", self.choseobjectId7)
		self.canvas.bind ("8", self.choseobjectId8)
		self.canvas.bind ("9", self.choseobjectId9)
		self.canvas.bind ("0", self.choseobjectId10)
		self.objectIdbox.bind ("<Key-space>", self.nextFrameWProp)   # the space key
		self.canvas.bind ("<Key-space>", self.nextFrameWProp)   # the space key
		self.objectIdbox.bind ("<<ListboxSelect>>", self.objectIdboxClick)
		self.switchbutton.bind("<Button-1>", self.activateSwitch)
		self.savebutton.bind("<Button-1>", self.saveXML)
		self.export2voc.bind("<Button-1>", self.saveXML2voc)
		self.quitbutton.bind("<Button-1>", self.quit)



		# Variable inits
		self.state=""
		self.mousex = 1
		self.mousey = 1
		self.objectIdProposed4NewRect=1
		self.displayAnno()
		self.displayClassAssignations()
		self.fnEntry.delete(0, END)
		self.fnEntry.insert(0, self.ct.videoname)
		self.isModified=False
		self.canvas.focus_force()

	def checkValidity(self):
		msg=self.ct.checkValidity()
		if len(self.fnEntry.get())<1:
			msg=msg+"The video name is empty.\n"
		if len(msg)>0:
			tkMessageBox.showinfo(TITLE, "There are errors in the annotation:\n\n"+msg+"\nThe file has been saved. Please address the problem(s) and save again.")

	def quit(self,event):
		print "quit method"
		self.ct.videoname=self.fnEntry.get()

		ok=True

		if self.isModified:
			if tkMessageBox.askyesno( title='Unsaved changes', message='The annotation has been modified. Do you really want to quit?'):
				tkMessageBox.showinfo ("First help","A backup of the latest changes can be found in save.xml, just in case.")
			else:
				ok=False

		if ok:

			# close tracking library
			if trackingLib != None:
				trackingLib.close_lib()
			self.parent.destroy()


	def updateAfterJump(self):
		self.curFrame = ImageTk.PhotoImage(self.img)
		self.displayAnno()
		self.parent.title(TITLE+" (frame nr."+str(self.ct.curFrameNr+1)+" of "+str(len(self.ct.filenames))+")")
		self.canvas.update()
	def changeFrame(self,id_frame):
		self.img = self.ct.changeFrame(id_frame)
		self.updateAfterJump()

	def prevFrame(self,event):
		self.img = self.ct.prevFrame()
		self.updateAfterJump()

	def prevFrameFar(self,event):
		self.img = self.ct.prevFrameFar()
		self.updateAfterJump()

	def nextFrame(self,event):
		self.img = self.ct.nextFrame(False, False)
		self.updateAfterJump()

	def nextFrameFar(self,event):
		self.img = self.ct.nextFrameFar()
		self.updateAfterJump()

	def nextFrameWProp(self,event):
		self.img = self.ct.nextFrame(True, False)
		self.updateAfterJump()
		self.isModified=True

	def nextFrameWPropForced(self,event):
		self.img = self.ct.nextFrame(True, True)
		self.updateAfterJump()
		self.isModified=True

	def nextFrameWPropForcedSelectedRect(self,event):
		sempos = self.ct.getSemMousePos(self.mousex,self.mousey)
		if sempos.index > -1:
			self.img = self.ct.nextFramePropCurrentRect(sempos.index)
		self.updateAfterJump()
		self.isModified=True

	def mouseMove(self,event):
		# self.debugEvent('mouseMove')

		self.displayAnno()
		self.mousex = event.x
		self.mousey = event.y

	 	maxx = self.img.size[0]
		maxy = self.img.size[1]

		# print "mouse x,y = ",self.mousex,",",self.mousey

		# Put the focus on the canvas, else the other widgets
		# keep all keyboard events once they were selected.
		self.canvas.focus_force()



		if self.state=="d":
			# We currently draw a rectangle
			self.curx2=min(maxx,max(1,event.x))
			self.cury2=min(maxy,max(1,event.y))
			self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2,
				outline="blue", width=2)
		elif self.state=="i":
			# We currently choose a running id
			self.propobjectId = self.curObjectId+(event.y-self.oldY)/20
			if self.propobjectId<0:
				self.propobjectId=0
			if self.propobjectId>MAX_objectId:
				self.propobjectId=MAX_objectId
			self.canvas.create_rectangle(self.curx1,self.cury1,self.curx1+30,
			self.cury1+30, outline="white", fill="white")
			self.canvas.create_text(self.curx1+15,self.cury1+15, text=str(self.propobjectId),
			fill="blue", font=("Helvectica", "20"))
		elif self.state=="ul":
			# We currently move the upper left corner
			self.curx1=min(maxx,max(1,event.x))
			self.cury1=min(maxy,max(1,event.y))
			self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2,
			outline="blue", width=2)
			# ELtodo self.drawAnchorPoint(self.curx1, self.cury1)
		elif self.state=="ur":
			# We currently move the upper right corner
			self.curx2=min(maxx,max(1,event.x))
			self.cury1=min(maxy,max(1,event.y))
			self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2,
			outline="blue", width=2)
			# ELtodo self.drawAnchorPoint(self.curx2, self.cury1)
		# We currently move the lower left corner
		elif self.state=="ll":
			self.curx1=min(maxx,max(1,event.x))
			self.cury2=min(maxy,max(1,event.y))
			self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2,
			outline="blue", width=2)
			# ELtodo self.drawAnchorPoint(self.curx1, self.cury2)
		elif self.state=="lr":
			# We currently move the lower right corner
			self.curx2=min(maxx,max(1,event.x))
			self.cury2=min(maxy,max(1,event.y))
			self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2,
			outline="blue", width=2)
			# ELtodo self.drawAnchorPoint(self.curx2, self.cury2)
		elif self.state=="c":
			# We currently move the whole rectangle
			self.curx1=min(maxx-10,max(1,event.x-int(0.5*self.curwidth)))
			self.cury1=min(maxy-10,max(1,event.y-int(0.5*self.curheigth)))
			self.curx2=min(maxx,max(self.curx1+10,max(1,event.x+int(0.5*self.curwidth))))
			self.cury2=min(maxy,max(self.cury1+10,max(1,event.y+int(0.5*self.curheigth))))

			self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2,
			outline="blue", width=2)
			# ELtodo self.drawAnchorPoint(event.x, event.y)
			# Drag outside of the canvas -> delete
			# if (event.x<0) or (event.x>self.img.size[0]) or (event.y<0) or (event.y>self.img.size[1]):
			#	self.canvas.create_image(self.curx1, self.cury1, anchor=NW, image=self.imgTrash)
			#	self.canvas.create_image(self.curx1, self.cury2-40, anchor=NW, image=self.imgTrash)
			#	self.canvas.create_image(self.curx2-40, self.cury1, anchor=NW, image=self.imgTrash)
			#	self.canvas.create_image(self.curx2-40, self.cury2-40, anchor=NW, image=self.imgTrash)
	def saveXML(self,event):
		self.ct.videoname=self.fnEntry.get()
		self.ct.exportXML()
		self.checkValidity()
		self.isModified=False

	def saveXML2voc(self,event):

		self.ct.videoname=self.fnEntry.get()
		self.ct.exportXML()
		self.checkValidity()
		self.isModified=False

		self.ct.exportXML2voc()

	def activateSwitch(self,event):
		self.ct.switchActivated = not self.ct.switchActivated
		# print self.ct.switchActivated
		self.img = self.ct.curFrame()
		self.updateAfterJump()

	# Remove all rectangles of the current frame
	def deleteAllRects(self,event):
		self.ct.deleteAllRects()
		self.displayAnno()
		self.canvas.update()
		self.isModified=True

	# Remove the currently selected rectangle of the current frame
	def deleteCurRect(self,event):
		sempos = self.ct.getSemMousePos(self.mousex,self.mousey)
		if sempos.index > -1:
			self.ct.deleteRect(sempos.index)
			self.displayAnno()
			self.canvas.update()
		self.isModified=True

	def leftMouseDown(self,event):
		# self.debugEvent('leftMouseDown')

		# On a Mac the right click does not work, at least not expected
		# workaround: if the CTRL key is held with a left click, we consider
		# it a right click
		if (event.state & 0x0004) > 0:
			self.rightMouseDown(event)
			return

		# Which rectangle is the nearest one to the mouse cursor, and what is
		# its relative position (corners, center, general position)?
		sempos = self.ct.getSemMousePos(self.mousex,self.mousey)

		# We change an existing rectangle. Remove the old one from the
		# controler
		if sempos.sempos in ("ul","ur","ll","lr","c"):
			self.state=sempos.sempos
			r=self.ct.getRects()[sempos.index]
			self.curx1=r.x1
			self.cury1=r.y1
			self.curx2=r.x2
			self.cury2=r.y2
			self.curwidth=abs(r.x2-r.x1)
			self.curheigth=abs(r.y2-r.y1)
			self.curObjectId=r.objectId
			self.ct.delRect(sempos.index)

		# We start drawing a new rectangle
		else:
			self.state="d"
			self.curObjectId=self.objectIdProposed4NewRect
			self.curx1=event.x
			self.cury1=event.y
			self.curx2=-1
			self.cury2=-1

		self.curSempos = SemMousePos(-1,"g")

	def leftMouseUp(self,event):
		# self.debugEvent('leftMouseUp')

		# On a Mac the right click does not work, at least not expected
		# workaround: if the CTRL key is held with a left click, we consider
		# it a right click
		if (event.state & 0x0004) > 0:
			self.rightMouseUp(event)
			return

		if self.state in ("ul","ur","ll","lr","c","d"):
			# Are we inside the window?
			if True: #not ((event.x<0) or (event.x>self.img.size[0]) or (event.y<0) or (event.y>self.img.size[1])):

				# If we create a new rectangle, we check whether we moved
				# since the first click (Non trivial rectangle)?
				if (self.state!="d") or (abs(event.x-self.curx1)>5) or (abs(event.y-self.cury1)>5):

					self.ct.addRect(self.curx1,self.cury1,self.curx2,self.cury2,self.curObjectId);
					self.isModified=True
					# We just drew a new rectangle
					if self.state=="d":
						self.ct.useobjectId(self.curObjectId)
						self.displayClassAssignations()
						self.objectIdProposed4NewRect = self.objectIdProposed4NewRect+1
			self.curx2=event.x
			self.cury2=event.y
		self.state=""
		self.displayAnno()

	def rightMouseDown(self,event):
		print "right mouse down"
		sempos=self.ct.getSemMousePos(event.x,event.y)
		self.curSempos = sempos
		self.oldY=event.y
		print "sempos.index",sempos.index
		if sempos.index>=0:
			self.state="i"
			r=self.ct.getRects()[sempos.index]
			self.curObjectId=r.objectId
			self.curx1=r.x1
			self.cury1=r.y1

	def rightMouseUp(self,event):
		if self.state=="i":
			self.ct.updateobjectId(self.curSempos.index,self.propobjectId)
			self.displayClassAssignations()
			self.isModified=True
		self.state=""

	def choseobjectId(self,event,id):
		sempos=self.ct.getSemMousePos(self.mousex,self.mousey)
		print "choseobjectId(self,event,id):",sempos.index, "pos: ",self.mousex,",",self.mousey
		if sempos.index>-1:
			self.ct.updateobjectId(sempos.index,id)
			self.displayAnno()
			self.displayClassAssignations()
			self.isModified=True



	# draw an anchor point at (x, y) coordinates
	def drawAnchorPoint(self, draw, x, y, size=5, color="cyan"):
		x1 = x-size
		y1 = y-size
		x2 = x+size
		y2 = y+size
		draw.ellipse([x1, y1, x2, y2], outline=color)
		draw.ellipse([x1+1, y1+1, x2-1, y2-1], outline=color)
		draw.ellipse([x1+2, y1+2, x2-2, y2-2], outline=color)


	# Draw the image and the current annotation
	def displayAnno(self):
		if self.state in ("ul","ur","ll","lr","c","d","i"):
			# We are currently in an operation, so do not search
			# the nearest rectangle. It is the one blocked at the
			# beginning of the operation
			sempos = self.curSempos
		else:
			# Search for the nearest rectangle:
			# which rectangle is the nearest one to the mouse cursor,
			# and what is its relative position (corners, center,
			# general position)?
			sempos = self.ct.getSemMousePos(self.mousex,self.mousey)

		# Init drawing
		drawFrame = self.img.copy()
		draw = ImageDraw.Draw(drawFrame)

		# Draw all rectangles
		for (i,r) in enumerate(self.ct.getRects()):
			if i == sempos.index:
				curcol = "blue"
			else:
				curcol = "red"
			draw.rectangle([r.x1, r.y1, r.x2, r.y2], outline=curcol)
			draw.rectangle([r.x1+1, r.y1+1, r.x2-1, r.y2-1], outline=curcol)
			draw.text([r.x1+3, r.y1+2], str(r.objectId), font=self.imgFont, fill=curcol)


			# Draw the icons
			if i == sempos.index:
				if sempos.sempos == "ul":
					self.drawAnchorPoint(draw, r.x1, r.y1)
				if sempos.sempos == "ur":
					self.drawAnchorPoint(draw, r.x2, r.y1)
				if sempos.sempos == "ll":
					self.drawAnchorPoint(draw, r.x1, r.y2)
				if sempos.sempos == "lr":
					self.drawAnchorPoint(draw, r.x2, r.y2)
				if sempos.sempos == "c":
					cx=0.5*(r.x1+r.x2)
					cy=0.5*(r.y1+r.y2)
					self.drawAnchorPoint(draw, cx, cy)

		del draw
		self.drawPhoto = ImageTk.PhotoImage(drawFrame)
		self.canvas.create_image(0, 0, anchor=NW, image=self.drawPhoto)

	def displayClassAssignations(self):
		self.objectIdbox.delete(0, END)
		x=self.ct.ClassAssignations
		for i in range(len(x)):
			if x[i]<0:
				self.objectIdbox.insert(END, str(i+1)+" has no assigned class ")
			else:
				self.objectIdbox.insert(END, str(i+1)+" has class "+str(x[i])+" ["+classnames[x[i]]+"]")


	# a listbox item has been clicked: choose the object class for
	# a given object
	def objectIdboxClick(self,event):
		self.clickedobjectId = self.objectIdbox.curselection()
		top = self.classDlg = Toplevel()
		lengthOfDialogBox=25*len(classnames)
		top.geometry("400x"+str(lengthOfDialogBox)+"+"+str(self.winfo_rootx())+"+"+str(self.winfo_rooty()))
		top.title("Enter class label for chosen object")
		classId = 0
		for classname in classnames:
			buttonText = str(classId) + " " + classname
			button = Button(top, text=buttonText, command= lambda i=classId: self.choseClassNr(i))
			button.pack(fill=X)
			classId += 1

	def choseClassNr(self,classNr):
		objectId=int(self.clickedobjectId[0])
		self.ct.ClassAssignations[objectId]=classNr
		self.classDlg.destroy()
		self.displayClassAssignations()
		# Put the focus on the canvas, else the listbox gets all events
		self.canvas.focus_force()
		self.isModified=True

	def choseobjectId1(self,event):
		self.choseobjectId(event,1)
	def choseobjectId2(self,event):
		self.choseobjectId(event,2)
	def choseobjectId3(self,event):
		self.choseobjectId(event,3)
	def choseobjectId4(self,event):
		self.choseobjectId(event,4)
	def choseobjectId5(self,event):
		self.choseobjectId(event,5)
	def choseobjectId6(self,event):
		self.choseobjectId(event,6)
	def choseobjectId7(self,event):
		self.choseobjectId(event,7)
	def choseobjectId8(self,event):
		self.choseobjectId(event,8)
	def choseobjectId9(self,event):
		self.choseobjectId(event,9)
	def choseobjectId10(self,event):
		self.choseobjectId(event,10)


	def debugEvent(self, title):
		self.eventcounter += 1
		print 'event #' + str(self.eventcounter), title


def onexit():
	print "qqqq"
	ex.quit(None)


trackingLib = None


def main():
	curPath=sys.path[0]

	global classnames
	global trackingLib
	#print "Script installed at: ",curPath

	folder_path = sys.argv[1]
	cfg_file=folder_path+'config.yml'
	print "Loading config from", cfg_file
	cfg_from_file(cfg_file)
	cfg.MAIN_DIR=folder_path

	from os.path import normpath, basename
	cfg.FOLDER_NAME = basename(normpath(folder_path))
	cfg.MAIN_DIR=folder_path
	print "Configuration :"
	print cfg
	classnames = cfg.CLASSES


	# load C++ JM tracking library
	if os.name == 'posix':
		# ---- Mac Os
		if platform.system() == 'Darwin':
			trackingLib = ctypes.CDLL(curPath+"/boxtracking/libboxtracking.dylib")

		# ---- Linux
		else:
			trackingLib = ctypes.CDLL(curPath+"/boxtracking/libboxtracking.so")
	# ---- Windows
	elif os.name == 'nt':
		trackingLib = ctypes.CDLL(curPath+"/boxtracking/libboxtracking.dll")


	if trackingLib != None:
		print "JM tracking library loaded."
		trackingLib.init_lib()
	else:
		print "Failed to load JM tracking library."
	print trackingLib


	root = Tk()
	root.protocol("WM_DELETE_WINDOW", onexit)
	global ex
	ex = Example(root, curPath)
	root.mainloop()

if __name__ == '__main__':
	main()
