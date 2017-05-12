![http://jorisguerry.fr/?page_id=142](http://jorisguerry.fr/wp-content/uploads/2017/05/acctano-v2_1-1024x576.png)
![http://jorisguerry.fr/?page_id=142](http://jorisguerry.fr/wp-content/uploads/2017/05/acctano-v2_0-768x432.png)

*****************************************************************************
ACTANNO : Object annotation tool

LIRIS Authors: Christian Wolf, Eric Lombardi, Julien Mille

ONERA Contributor : Joris Guerry (joris.guerry@onera.fr)


Changelog:

09.09.16 jg:
	     - add gray image PNG compatibility
	     - add keyboard shortcut : q -> quit
	     - add keyboard shortcut : s -> save
	     - add keyboard shortcut : p -> force propagate only the bounding box hovered (with the focus). Allows to make a new bounding box from the beginning and propagate it without impacting the others.
	     - add scroll bar at bottom to visualise the movie
	     - change the export format : add the file name in XML (for external use)
	     - add RGBD features :
		- files must be at format numFrame_timestamp.ext
		- ./actanno.py <xml file> <rgb prefix> [optional: <depth prefix>]
		- add switch button to show the depth image closest to the current rgb image
		-
	     - rectangle can go at the edge of the window without disappear
	     - change tostring -> tobytes in src/minimal_ctypes_opencv.py (due update of opencv)
##################################################################################################################
10.09.14 el: - Fix performance issue (slow-down when first rectangles are drawn).
03.09.14 el: - Replace 'moving arrows' image by a circle around anchor points, to provide better
               visibility in small boxes ; change anchor points activation distance to allow
               smaller boxes.
03.09.14 el: - Changing the classes is made easier: it only requires to modify the 'classnames'
               variable ; the class menu is now dynamically built from the content of the
               'classnames' variable, and does'nt need anymore to be changed by hand.
14.12.11 cw: - Bugfix in actreader version : remove imgTrash and imgMove and
               references to it
01.12.11 cw: - Added comments allowing to extract a read only version of the tool
06.10.11 cw: - Change the description of some objects
             - Check if save went ok
             - Jump only 25 frames
             - The program does not stop when no objects are in an existing XML file
             - A loaded file is not automatically considered as modified
05.10.11 cw: - Check whether the XML frame numbers are larger than the
               number of frames in the input
             - Remove most of the debugging output
03.10.11 cw: - Added "D" (DELETE ALL) command
             - Runid's can be entered with the keyboard
             - Typing in a videoname will do keyboard short cuts (d,f etc.)
             - Check for validity when saving a file
             - Jump far with page keys
             - Check for unsaved changes before quitting
             - Add video length in the title
01.19.11 cw: - Added "d" (DELETE) command
             - Simulate right click with CTRL + left Click
             - Bugfixes:
             -- All 4 corners can be used to resize a rectangle now
29.09.11 el: Integration du module tracking de Julien Mille
07.09.11 cw: Bugfixes:
             -no crash if XML does not exist
             -correct update of class list;
             -fixed: incomplete XML export
             -fixed: Propagating with space after listbox usage will pop up the listbox again
             -Short click on the image will create a rectangle with weird coordinates
30.08.11 cw: Add XML parser
02.07.11 cw: begin development

*****************************************************************************
