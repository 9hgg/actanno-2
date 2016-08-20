#
# Makefile for libboxtracking 1.0
# Compiler: gcc/MinGW
#

# ---- Windows
#FINAL_TARGET = libboxtracking.dll
#OPENCV_DIR = C:/Data/Developpement/OpenCV-1.0
#INCLUDE_DIR = -I$(OPENCV_DIR)/cv/include -I$(OPENCV_DIR)/cxcore/include  -I$(OPENCV_DIR)/otherlibs/highgui
# LIB_DIR = -L$(OPENCV_DIR)/build_mingw/lib
# LIB_DIR = -L$(OPENCV_DIR)/lib
# LIBS = -lcv -lcxcore -lhighgui
# FINALOPTS = -shared

# ---- Linux (ubuntu)
 FINAL_TARGET = libboxtracking.so
 OPENCV_DIR = "error --- do not use under Linux."
 INCLUDE_DIR = $(shell pkg-config opencv --cflags-only-I)
 LIBS = $(shell pkg-config opencv --libs)
 FINALOPTS = -shared

# ---- Mac OS (Mac ports installation)
#FINAL_TARGET = libboxtracking.dylib
#OPENCV_DIR = "error --- do not use under Linux."
#INCLUDE_DIR = -I/opt/local/include -I /opt/local/include/opencv 
#LIB_DIR = -L /opt/local/lib/
#LIBS = -lopencv_core -lopencv_highgui 
#FINALOPTS = -dynamiclib


CC = g++
CPPFLAGS = -DNDEBUG -O2 -msse2 -fPIC # -ggdb
LD = g++
LDFLAGS = -DNEBUG -O2 -msse2 -fPIC # -ggdb
SRCS = libboxtracking.cpp arrayndfloat.cpp histogram.cpp
# OPENCV_DIR = C:/Data/Developpement/OpenCV-2.2.0
# INCLUDE_DIR = -I$(OPENCV_DIR)/include
# LIBS = -lopencv_core220.dll -lopencv_highgui220.dll

default: $(FINAL_TARGET)

$(FINAL_TARGET): $(SRCS:%.cpp=%.o)
	$(LD) $+ $(FINALOPTS) -o $@ $(LDFLAGS) $(LIB_DIR) $(LIBS)

%.o: %.cpp
	$(CC) -c $(CPPFLAGS) $(INCLUDE_DIR) $< -o $@

clean:
	rm -f *.o $(FINAL_TARGET)
