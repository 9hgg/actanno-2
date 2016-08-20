/* 
  C++ library example.
  Used to test C++ function call from python, watch test_libtracking++.py.
  
  To build library :
  g++ -fPIC -shared -o libtracking++.so -I /usr/include/opencv -l highgui libtracking.cpp
*/

#include <stdio.h>
#include <iostream>

// Paths to OpenCV header should be changed for versions earlier than 2.2
// #include <opencv2/core/core.hpp>
// #include <opencv2/highgui/highgui.hpp>

#include <cv.h>
#include <cxcore.h>
#include <highgui.h>

#include "histogram.h"
#include "couple.h"

using namespace std;

struct c_AARect
{
	int x1;
	int y1;
	int x2;
	int y2;
	int runid;
};

typedef struct
{
	// Top-left corner
	CCouple<int> ptStart;

	// Bottom-right corner
	CCouple<int> ptEnd;
} RectangleBox;

// C++ library interface

class Tracking
{
public:
	int track_block_matching( const IplImage *im1, const IplImage *im2, const struct c_AARect *inrect, struct c_AARect *outrect);
	int track_histogram_matching( const IplImage *im1, const IplImage *im2, const struct c_AARect *inrect, struct c_AARect *outrect);
	
protected:
	float GetRegionMismatch_PixelL2(const IplImage &img1, const IplImage &img2, const RectangleBox &box1, const RectangleBox &box2);
	float GetRegionMismatch_HistogramL1(const IplImage &img1, const IplImage &img2, const RectangleBox &box1, const RectangleBox &box2);
	
	void infoCvImg(const IplImage *img);
	void displayCvImg(const IplImage *img);
};


// library C interface, callable by python ctypes

Tracking *tracker = NULL;

extern "C" int init_lib(void)
{
	tracker = new Tracking;	
}

extern "C" int track_block_matching( const IplImage *im1, const IplImage *im2, 
	const struct c_AARect *inrect, struct c_AARect *outrect)
{
	if( tracker == NULL )
		return -1;
	
	return tracker->track_block_matching( im1, im2, inrect, outrect);	
}

extern "C" int track_histogram_matching( const IplImage *im1, const IplImage *im2, 
	const struct c_AARect *inrect, struct c_AARect *outrect)
{
	if( tracker == NULL )
		return -1;
	
	return tracker->track_histogram_matching( im1, im2, inrect, outrect);	
}

extern "C" int close_lib(void)
{
	delete tracker;
	tracker = NULL;
	return 0;
}

// C++ library implementation

// Compute the mismatch between two rectangular regions of same sizes using pixel-wise differences
// i.e the sum of pixel-wise squared euclidean distances in RGB space
// Images are assumed to be RGB or RGBA (3 or 4 channels) but do not need to have the same size
// Boxes should have the same size
float Tracking::GetRegionMismatch_PixelL2(const IplImage &img1, const IplImage &img2, const RectangleBox &box1, const RectangleBox &box2)
{
	CTriplet<int> iPixel1, iPixel2;
	CCouple<int> p;
	float fMismatch;
	unsigned char *pImgBuffer1, *pImgBuffer2;
	int iOffsetEndRow1, iOffsetEndRow2;

	// Check corners of boxes are okay
	if (box1.ptStart.x>box1.ptEnd.x || box1.ptStart.y>box1.ptEnd.y
		|| box2.ptStart.x>box1.ptEnd.x || box2.ptStart.y>box1.ptEnd.y)
	{
		cout<<"ERROR: corners of boxes are inverted"<<endl;
		return -1.0f;
	}

	// Check sizes of boxes are equal
	if (box1.ptEnd-box1.ptStart != box2.ptEnd-box2.ptStart)
	{
		cout<<"ERROR: boxes should have the size"<<endl;
		return -1.0f;
	}

	iOffsetEndRow1 = img1.widthStep - (box1.ptEnd.x-box1.ptStart.x+1)*img1.nChannels;
	iOffsetEndRow2 = img2.widthStep - (box2.ptEnd.x-box2.ptStart.x+1)*img2.nChannels;
	pImgBuffer1 = ((unsigned char *)img1.imageData) + box1.ptStart.y*img1.widthStep + box1.ptStart.x*img1.nChannels;
	pImgBuffer2 = ((unsigned char *)img2.imageData) + box2.ptStart.y*img2.widthStep + box2.ptStart.x*img2.nChannels;
	fMismatch = 0.0f;

	for (p.y=box1.ptStart.y; p.y<=box1.ptEnd.y; p.y++)
	{
		for (p.x=box1.ptStart.x; p.x<=box1.ptEnd.x; p.x++)
		{
			iPixel1.x = (int)pImgBuffer1[2];
			iPixel1.y = (int)pImgBuffer1[1];
			iPixel1.z = (int)pImgBuffer1[0];

			iPixel2.x = (int)pImgBuffer2[2];
			iPixel2.y = (int)pImgBuffer2[1];
			iPixel2.z = (int)pImgBuffer2[0];
			
			// Diffence is first casted to real values, then normalized and finally the squared norm is taken
			fMismatch += ((CTriplet<float>)(iPixel1-iPixel2)/255.0f).L2Norm2();

			pImgBuffer1 += img1.nChannels;
			pImgBuffer2 += img2.nChannels;
		}
		pImgBuffer1 += iOffsetEndRow1;
		pImgBuffer2 += iOffsetEndRow2;
	}

	return fMismatch;
}

// Compute the mismatch between two rectangular regions of same sizes using RGB histograms
// The histogram distance is simply the sum of bin-wise absolute differences
// Images are assumed to be RGB or RGBA (3 or 4 channels) but do not need to have the same size
// Boxes should have the same size
float Tracking::GetRegionMismatch_HistogramL1(const IplImage &img1, const IplImage &img2, const RectangleBox &box1, const RectangleBox &box2)
{
	CTriplet<int> iPixel1, iPixel2;
	CCouple<int> p;
	CHistogramRGB histo1, histo2;
	float fMismatch;
	unsigned char *pImgBuffer1, *pImgBuffer2;
	float *pHistoBuffer1, *pHistoBuffer2;
	int iOffsetEndRow1, iOffsetEndRow2;
	int iColor, iHistoSize;
	int iNbRGBLevels = 64;

	// Check corners of boxes are okay
	if (box1.ptStart.x>box1.ptEnd.x || box1.ptStart.y>box1.ptEnd.y
		|| box2.ptStart.x>box1.ptEnd.x || box2.ptStart.y>box1.ptEnd.y)
	{
		cout<<"ERROR: corners of boxes are inverted"<<endl;
		return -1.0f;
	}

	// Check sizes of boxes are equal
	if (box1.ptEnd-box1.ptStart != box2.ptEnd-box2.ptStart)
	{
		cout<<"ERROR: boxes should have the size"<<endl;
		return -1.0f;
	}

	histo1.SetNbColorLevels(iNbRGBLevels);
	histo2.SetNbColorLevels(iNbRGBLevels);

	iOffsetEndRow1 = img1.widthStep - (box1.ptEnd.x-box1.ptStart.x+1)*img1.nChannels;
	iOffsetEndRow2 = img2.widthStep - (box2.ptEnd.x-box2.ptStart.x+1)*img2.nChannels;
	pImgBuffer1 = ((unsigned char *)img1.imageData) + box1.ptStart.y*img1.widthStep + box1.ptStart.x*img1.nChannels;
	pImgBuffer2 = ((unsigned char *)img2.imageData) + box2.ptStart.y*img2.widthStep + box2.ptStart.x*img2.nChannels;
	
	// Fill histograms
	for (p.y=box1.ptStart.y; p.y<=box1.ptEnd.y; p.y++)
	{
		for (p.x=box1.ptStart.x; p.x<=box1.ptEnd.x; p.x++)
		{
			iPixel1.x = (int)pImgBuffer1[2];
			iPixel1.y = (int)pImgBuffer1[1];
			iPixel1.z = (int)pImgBuffer1[0];

			iPixel2.x = (int)pImgBuffer2[2];
			iPixel2.y = (int)pImgBuffer2[1];
			iPixel2.z = (int)pImgBuffer2[0];
			
			histo1.AddIntPixel(iPixel1);
			histo2.AddIntPixel(iPixel2);

			pImgBuffer1 += img1.nChannels;
			pImgBuffer2 += img2.nChannels;
		}
		pImgBuffer1 += iOffsetEndRow1;
		pImgBuffer2 += iOffsetEndRow2;
	}

	// Compute the bin-wise sum of absolute differences
	pHistoBuffer1 = histo1.GetBuffer();
	pHistoBuffer2 = histo2.GetBuffer();
	iHistoSize = iNbRGBLevels*iNbRGBLevels*iNbRGBLevels;
	fMismatch = 0.0f;

	for (iColor=0; iColor<iHistoSize; iColor++)
	{
		fMismatch += fabs(*pHistoBuffer1 - *pHistoBuffer2);
		pHistoBuffer1++;
		pHistoBuffer2++;
	}
	
	return fMismatch;
}

int Tracking::track_block_matching( const IplImage *im1, const IplImage *im2, const struct c_AARect *inrect, struct c_AARect *outrect)
{
	// displayCvImg(im1);
	// displayCvImg(im2);
	
	CCouple<int> ptOffsetSum, ptOffset, ptOffsetMin;
	CArray1D<CCouple<int> > vectNeighborhood;
	float fEnergy, fEnergyMin;
	int iNumBox, iNeighbor, iNeighborMin;
	RectangleBox boxInput, boxToTest, boxOutput;
	bool bEvolve;
	
	vectNeighborhood.Init(4);
	vectNeighborhood[0].Set(-1,0);
	vectNeighborhood[1].Set(1,0);
	vectNeighborhood[2].Set(0,-1);
	vectNeighborhood[3].Set(0,1);
	
	boxInput.ptStart.x = max(inrect->x1, 0);
	boxInput.ptStart.y = max(inrect->y1, 0);
	boxInput.ptEnd.x = min(inrect->x2, im1->width-1);
	boxInput.ptEnd.y = min(inrect->y2, im1->height-1);
	
	ptOffsetSum.Set(0,0);
	boxToTest = boxInput;
	fEnergyMin = GetRegionMismatch_PixelL2(*im1, *im2, boxInput, boxToTest);
	bEvolve = true;

	// Translate region until energy is minimal
	int iIter=0, iIterMax = 20;
	while (bEvolve==true && iIter<iIterMax)
	{
		iNeighborMin = -1;
		for (iNeighbor=0; iNeighbor<4; iNeighbor++)
		{
			boxToTest = boxInput;
			boxToTest.ptStart += ptOffsetSum+vectNeighborhood[iNeighbor];
			boxToTest.ptEnd += ptOffsetSum+vectNeighborhood[iNeighbor];
			
			if (boxToTest.ptStart.x>=0 && boxToTest.ptStart.y>=0 && boxToTest.ptEnd.x<im2->width && boxToTest.ptEnd.y<im2->height)
			{
				fEnergy = GetRegionMismatch_PixelL2(*im1, *im2, boxInput, boxToTest);
				
				if (fEnergy<fEnergyMin)
				{
					fEnergyMin = fEnergy;
					iNeighborMin = iNeighbor;
				}
			}
		}
	
		if (iNeighborMin != -1)
			ptOffsetSum += vectNeighborhood[iNeighborMin];
		else
			bEvolve = false;
		iIter++;
	}
	
	boxOutput = boxInput;
	boxOutput.ptStart += ptOffsetSum;
	boxOutput.ptEnd += ptOffsetSum;
	
	cout<<"Box "<<inrect->runid<<" translated of ("<<ptOffsetSum.x<<","<<ptOffsetSum.y<<")"<<endl;
	
	outrect->x1 = boxOutput.ptStart.x;
	outrect->y1 = boxOutput.ptStart.y;
	outrect->x2 = boxOutput.ptEnd.x;
	outrect->y2 = boxOutput.ptEnd.y;
	
	outrect->runid = inrect->runid;
	
	return 0;
}

int Tracking::track_histogram_matching( const IplImage *im1, const IplImage *im2, const struct c_AARect *inrect, struct c_AARect *outrect)
{
	// displayCvImg(im1);
	// displayCvImg(im2);
	
	CCouple<int> ptOffsetSum, ptOffset, ptOffsetMin;
	CArray1D<CCouple<int> > vectNeighborhood;
	float fEnergy, fEnergyMin;
	int iNumBox, iNeighbor, iNeighborMin;
	RectangleBox boxInput, boxToTest, boxOutput;
	bool bEvolve;
	
	vectNeighborhood.Init(4);
	vectNeighborhood[0].Set(-1,0);
	vectNeighborhood[1].Set(1,0);
	vectNeighborhood[2].Set(0,-1);
	vectNeighborhood[3].Set(0,1);
	
	boxInput.ptStart.x = max(inrect->x1, 0);
	boxInput.ptStart.y = max(inrect->y1, 0);
	boxInput.ptEnd.x = min(inrect->x2, im1->width-1);
	boxInput.ptEnd.y = min(inrect->y2, im1->height-1);
	
	ptOffsetSum.Set(0,0);
	boxToTest = boxInput;
	fEnergyMin = GetRegionMismatch_HistogramL1(*im1, *im2, boxInput, boxToTest);
	bEvolve = true;

	// Translate region until energy is minimal
	int iIter=0, iIterMax = 20;
	while (bEvolve==true && iIter<iIterMax)
	{
		iNeighborMin = -1;
		for (iNeighbor=0; iNeighbor<4; iNeighbor++)
		{
			boxToTest = boxInput;
			boxToTest.ptStart += ptOffsetSum+vectNeighborhood[iNeighbor];
			boxToTest.ptEnd += ptOffsetSum+vectNeighborhood[iNeighbor];
			
			if (boxToTest.ptStart.x>=0 && boxToTest.ptStart.y>=0 && boxToTest.ptEnd.x<im2->width && boxToTest.ptEnd.y<im2->height)
			{
				fEnergy = GetRegionMismatch_HistogramL1(*im1, *im2, boxInput, boxToTest);
				
				if (fEnergy<fEnergyMin)
				{
					fEnergyMin = fEnergy;
					iNeighborMin = iNeighbor;
				}
			}
		}
	
		if (iNeighborMin != -1)
			ptOffsetSum += vectNeighborhood[iNeighborMin];
		else
			bEvolve = false;
		iIter++;
	}
	
	boxOutput = boxInput;
	boxOutput.ptStart += ptOffsetSum;
	boxOutput.ptEnd += ptOffsetSum;
	
	cout<<"Box "<<inrect->runid<<" translated of ("<<ptOffsetSum.x<<","<<ptOffsetSum.y<<")"<<endl;
	
	outrect->x1 = boxOutput.ptStart.x;
	outrect->y1 = boxOutput.ptStart.y;
	outrect->x2 = boxOutput.ptEnd.x;
	outrect->y2 = boxOutput.ptEnd.y;
	
	outrect->runid = inrect->runid;
	
	return 0;
}

void Tracking::infoCvImg(const IplImage *img)
{
	printf( "width = %d\n", img->width);
	printf( "height = %d\n", img->height);
	printf( "nChannels = %d\n", img->nChannels);
	printf( "depth = %d\n", img->depth);
	printf( "imageSize = %d\n", img->imageSize);
}

void Tracking::displayCvImg(const IplImage *img)
{
	const char *name = "displayed_by_C_code";
	cvNamedWindow( name, CV_WINDOW_AUTOSIZE);
	cvShowImage( name, img );
	cvWaitKey(0);
    cvDestroyWindow(name);
}


