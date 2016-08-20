// #include "stdafx.h"

#include "arrayndfloat.h"
#include "histogram.h"

// CHistogramBase

// CHistogramRGB
CHistogramRGB::CHistogramRGB()
{
	iNeighborhoodWidth = 0;
	fGaussianStdDeviation = 0.0f;

	SetNbColorLevels(5);
	SetGaussianStdDeviation(0.75f);
}

void CHistogramRGB::SetNbColorLevels(int nbColorLevels)
{
	if (nbColorLevels>0)
	{
		int iNeighbor;

		// Allocate 3D array of histogram bins
		iNbColorLevels = nbColorLevels;
		Init(iNbColorLevels, iNbColorLevels, iNbColorLevels);
		Fill(0.0f);

		// Allocate 3D array of histogram logs
		//arrayLogs.Init(iNbColorLevels, iNbColorLevels, iNbColorLevels);
		//arrayLogs.Fill(-100.0f);

		// Update status array
		arrayStatus.Init(iNbColorLevels, iNbColorLevels, iNbColorLevels);
		if (fGaussianStdDeviation==0.0f)
			arrayStatus.Fill(1);
		else {
			CArray3DIterator<unsigned char> itVoxel;
			int iHalfWidth;

			// Update neighborhood offsets
            for (iNeighbor=0; iNeighbor<vectNeighborhood.GetSize(); iNeighbor++)
                vectNeighborhoodOffsets[iNeighbor] = GetOffset(vectNeighborhood[iNeighbor]);

			arrayStatus.Fill(0);
			iHalfWidth = iNeighborhoodWidth/2;

			itVoxel = arrayStatus.GetIterator(CTriplet<int>(iHalfWidth,iHalfWidth,iHalfWidth),
				CTriplet<int>(iWidth-1-iHalfWidth, iHeight-1-iHalfWidth, iDepth-1-iHalfWidth));
			for (; !itVoxel.End(); itVoxel++)
				itVoxel.Element() = 1;
		}
	}
}

void CHistogramRGB::SetGaussianStdDeviation(float stdDeviation)
{
	if (stdDeviation<0.0f)
		return;

	fGaussianStdDeviation = stdDeviation;

	if (fGaussianStdDeviation==0.0f)
	{
		vectNeighborhood.Empty();
		vectNeighborhoodOffsets.Empty();
		vectNeighborhoodCoefs.Empty();

		// Update status array
		arrayStatus.Fill(1);
	}
	else {
		CTriplet<int> p;
		int iHalfWidth;
		CTriplet<float> fCoefs;
		float fSumCoefs, fSquaredStdDeviation;
		int i;

		iHalfWidth = max(1, (int)(3.0f * fGaussianStdDeviation));
		iNeighborhoodWidth = 2*iHalfWidth+1;

		vectNeighborhood.Init(iNeighborhoodWidth*iNeighborhoodWidth*iNeighborhoodWidth);
		vectNeighborhoodOffsets.Init(iNeighborhoodWidth*iNeighborhoodWidth*iNeighborhoodWidth);
		vectNeighborhoodCoefs.Init(iNeighborhoodWidth*iNeighborhoodWidth*iNeighborhoodWidth);

		i = 0;
		fSumCoefs = 0.0f;
		fSquaredStdDeviation = 2.0f*fGaussianStdDeviation*fGaussianStdDeviation;

		for (p.z=-iHalfWidth; p.z<=iHalfWidth; p.z++)
		{
			fCoefs.z = (float)(p.z*p.z);
			for (p.y=-iHalfWidth; p.y<=iHalfWidth; p.y++)
			{
				fCoefs.y = (float)(p.y*p.y);
				for (p.x=-iHalfWidth; p.x<=iHalfWidth; p.x++)
				{
					fCoefs.x = (float)(p.x*p.x);

					vectNeighborhood[i] = p;
					vectNeighborhoodOffsets[i] = GetOffset(p);
					vectNeighborhoodCoefs[i] = exp(-(fCoefs.x+fCoefs.y+fCoefs.z)/fSquaredStdDeviation);
					fSumCoefs += vectNeighborhoodCoefs[i];
					i++;
				}
			}
		}
		vectNeighborhoodCoefs/=fSumCoefs;

		// Update status array
		arrayStatus.Fill(0);
		if (iNeighborhoodWidth<iNbColorLevels)
		{
			CArray3DIterator<unsigned char> itVoxel;

			// iHalfWidth = iNeighborhoodWidth/2;
			itVoxel = arrayStatus.GetIterator(CTriplet<int>(iHalfWidth,iHalfWidth,iHalfWidth),
				CTriplet<int>(iWidth-1-iHalfWidth, iHeight-1-iHalfWidth, iDepth-1-iHalfWidth));
			for (; !itVoxel.End(); itVoxel++)
				itVoxel.Element() = 1;
		}
	}
}

void CHistogramRGB::operator =(CHistogramBase &histo)
{
	CHistogramRGB *pHistoRGB = (CHistogramRGB *)(&histo);

	CArray3D<float>::operator =(*pHistoRGB);

	iNbColorLevels = pHistoRGB->iNbColorLevels;
	fGaussianStdDeviation = pHistoRGB->fGaussianStdDeviation;
	iNeighborhoodWidth = pHistoRGB->iNeighborhoodWidth;
	vectNeighborhood = pHistoRGB->vectNeighborhood;
	vectNeighborhoodOffsets = pHistoRGB->vectNeighborhoodOffsets;
	vectNeighborhoodCoefs = pHistoRGB->vectNeighborhoodCoefs;
	arrayStatus = pHistoRGB->arrayStatus;
}

void CHistogramRGB::AddIntPixel(const CTriplet<int> &iPixel, float fWeight)
{
	CTriplet<int> iPixelCoord;
	float *pCentre;
	int iOffset;

	iPixelCoord = iPixel/(256/iNbColorLevels);
	
	// Pointer to central color in histogram array
	iOffset = GetOffset(iPixelCoord);
	pCentre = pElements + iOffset;

	if (fGaussianStdDeviation==0.0f)
		*pCentre += fWeight;
	else {
		int iNeighbor;

		if (arrayStatus.GetBuffer()[iOffset]==1)
		{
			for (iNeighbor=0; iNeighbor<vectNeighborhood.GetSize(); iNeighbor++)
				pCentre[vectNeighborhoodOffsets[iNeighbor]] += vectNeighborhoodCoefs[iNeighbor]*fWeight;
		}
		else {
			CTriplet<int> ptNeighborMin(-iPixelCoord), ptNeighborMax(CTriplet<int>(iNbColorLevels-1)-iPixelCoord);
			for (iNeighbor=0; iNeighbor<vectNeighborhood.GetSize(); iNeighbor++)
			{
				if (vectNeighborhood[iNeighbor].IsInRange(ptNeighborMin, ptNeighborMax))
					pCentre[vectNeighborhoodOffsets[iNeighbor]] += vectNeighborhoodCoefs[iNeighbor]*fWeight;
			}
		}
	}
}

void CHistogramRGB::SubtractIntPixel(const CTriplet<int> &iPixel, float fWeight)
{
	CTriplet<int> iPixelCoord;
	float *pCentre;
	int iOffset;

	iPixelCoord = iPixel/(256/iNbColorLevels);
	
	// Pointer to central color in histogram array
	iOffset = GetOffset(iPixelCoord);
	pCentre = pElements + iOffset;

	if (fGaussianStdDeviation==0.0f)
		*pCentre -= fWeight;
	else {
		int iNeighbor;

		if (arrayStatus.GetBuffer()[iOffset]==1)
		{
			for (iNeighbor=0; iNeighbor<vectNeighborhood.GetSize(); iNeighbor++)
				pCentre[vectNeighborhoodOffsets[iNeighbor]] -= vectNeighborhoodCoefs[iNeighbor]*fWeight;
		}
		else {
			CTriplet<int> ptNeighborMin(-iPixelCoord), ptNeighborMax(CTriplet<int>(iNbColorLevels-1)-iPixelCoord);
			for (iNeighbor=0; iNeighbor<vectNeighborhood.GetSize(); iNeighbor++)
			{
				if (vectNeighborhood[iNeighbor].IsInRange(ptNeighborMin, ptNeighborMax))
					pCentre[vectNeighborhoodOffsets[iNeighbor]] -= vectNeighborhoodCoefs[iNeighbor]*fWeight;
			}
		}
	}
}

float CHistogramRGB::GetValue(const CTriplet<int> &iPixel)
{
	CTriplet<int> iPixelCoord;
	float fValue;

	iPixelCoord = iPixel/(256/iNbColorLevels);
	fValue = Element(iPixelCoord);

	return fValue;
}

void CHistogramRGB::operator +=(CHistogramBase &histo)
{
	CHistogramRGB *pHistoRGB = (CHistogramRGB *)(&histo);
	CArray3D<float>::operator +=(*pHistoRGB);
}

void CHistogramRGB::operator -=(CHistogramBase &histo)
{
	CHistogramRGB *pHistoRGB = (CHistogramRGB *)(&histo);
	CArray3D<float>::operator -=(*pHistoRGB);
}

void CHistogramRGB::operator *=(float fCoef)
{
	CArray3D<float>::operator *=(fCoef);
}

void CHistogramRGB::operator /=(float fCoef)
{
	CArray3D<float>::operator /=(fCoef);
}

#ifdef __glut_h__
void CHistogramRGB::DrawOpenGL()
{
	CImage2DFloatRGBPixel fPixelRGB;
	CTriplet<int> p;
	float *pFloat;
	float fCoef;
	CPoint3D pgl;
	float rayon_cube = 20.0f/CPoint3D::maxdim;

	static float Spec[4] = {0.5f, 1.0f, 1.0f, 1.0f};
	static float Dif[4] = {0.0f, 0.5f, 1.0f, 1.0f};
	static float Amb[4] = {0.0f, 0.0f, 0.0f, 1.0f};

	fCoef = 255.0f/(float)(iNbColorLevels-1);

	pFloat = pElements;

	for (p.z=0; p.z<iDepth; p.z++)
		for (p.y=0; p.y<iHeight; p.y++)
			for (p.x=0; p.x<iWidth; p.x++)
			{
				if (*pFloat!=0.0f)
				{
					fPixelRGB.fRed   = (float)p.x*fCoef;
					fPixelRGB.fGreen = (float)p.y*fCoef;
					fPixelRGB.fBlue  = (float)p.z*fCoef;

					pgl.x = fPixelRGB.fRed * 2.0f/255.0f - 1.0f;
					pgl.y = fPixelRGB.fGreen * 2.0f/255.0f - 1.0f;
					pgl.z = fPixelRGB.fBlue * 2.0f/255.0f - 1.0f;

					Amb[0] = 0.5f * fPixelRGB.fRed/255.0f;
					Amb[1] = 0.5f * fPixelRGB.fGreen/255.0f;
					Amb[2] = 0.5f * fPixelRGB.fBlue/255.0f;
					Amb[3] = 1.0f;

					Dif[0] = fPixelRGB.fRed/255.0f;
					Dif[1] = fPixelRGB.fGreen/255.0f;
					Dif[2] = fPixelRGB.fBlue/255.0f;
					Dif[3] = 1.0f;

					//Spec[0] = 0.5f; Spec[1] = 0.5f; Spec[2] = 0.5f; Spec[3] = 1.0f;
					memcpy(Spec, Dif, sizeof(float)*4);
					// pgl.setImage2GL();

					glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, Amb);
					glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, Dif);
					glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, Spec);

					glTranslatef(pgl.x, pgl.y, pgl.z);
					glutSolidCube(rayon_cube*0.5f);
					glTranslatef(-pgl.x, -pgl.y, -pgl.z);
				}
				pFloat++;
			}

	glDisable(GL_LIGHTING);
	glColor3f(0.0f, 0.0f, 1.0f);
	glutWireCube(2.0f);
	glEnable(GL_LIGHTING);
}
#endif
