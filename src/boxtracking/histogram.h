#ifndef _HISTOGRAM_H
#define _HISTOGRAM_H

#include "arrayndfloat.h"
#include <list>

class CHistogramBase
{
  // Definitions
  public:
	typedef enum {
		HISTOGRAMCOLORSPACE_BASE, HISTOGRAMCOLORSPACE_RGB, HISTOGRAMCOLORSPACE_UV, HISTOGRAMCOLORSPACE_HSVPEREZ
	} typeHistogramColorSpace;

  // Structures
  public:
	typedef struct {
		float fSumTerms;
	} CDensityDistanceParams;

  // Attributes
  public:
	int iNbColorLevels;
	float fGaussianStdDeviation;
	int iNeighborhoodWidth;

  // Methods
  public:
	virtual typeHistogramColorSpace GetColorSpace() {return HISTOGRAMCOLORSPACE_BASE;}

	CHistogramBase() {iNbColorLevels=0; fGaussianStdDeviation=0.0f; iNeighborhoodWidth=0;}
	virtual ~CHistogramBase() {}

	virtual inline int GetNbColorLevels() {return iNbColorLevels;}
	virtual void SetNbColorLevels(int nbColorLevels) {iNbColorLevels = nbColorLevels;}

	virtual inline float GetGaussianStdDeviation() {return fGaussianStdDeviation;}
	virtual void SetGaussianStdDeviation(float stdDeviation) {fGaussianStdDeviation = stdDeviation;}

	virtual void Empty()=0;
	virtual void Destroy() {iNbColorLevels = 0;}
	virtual void operator =(CHistogramBase &) {};

	// Add and subtract pixels
	virtual void AddIntPixel(const CTriplet<int> &, float fWeight=1.0f)=0;
	virtual void SubtractIntPixel(const CTriplet<int> &, float fWeight=1.0f)=0;
	
	// Overloaded operators
	virtual void operator +=(CHistogramBase &) {}
	virtual void operator -=(CHistogramBase &) {}
	virtual void operator *=(float) {}
	virtual void operator /=(float) {}

	virtual float GetValue(const CTriplet<int> &)=0;

	inline static float ElementaryTermKullbackLeibler(float fHistoValue1, float fHistoValue2, float fArea1, float fArea2, float fLogArea1, float fLogArea2)
	{
		float fTerm, fProba1, fProba2, fLogProba1, fLogProba2;

		if (fHistoValue1<=0.0f)
		{
			fProba1 = 0.0f;
			fLogProba1 = -10.0f;
		}
		else {
			fProba1 = fHistoValue1/fArea1;
			fLogProba1 = log(fHistoValue1) - fLogArea1;
		}

		if (fHistoValue2<=0.0f)
		{
			fProba2 = 0.0f;
			fLogProba2 = -10.0f;
		}
		else {
			fProba2 = fHistoValue2/fArea2;
			fLogProba2 = fHistoValue1 - fLogArea2;
		}

		// Symmetric KL
		fTerm = (fProba1-fProba2)*(fLogProba1-fLogProba2);

		// Proba 2 with respect to proba 1
		// fTerm = fProba1*(fLogProba1-fLogProba2);

		// Proba 1 with respect to proba 2
		// fTerm = fProba2*(fLogProba2-fLogProba1);
		return fTerm;
	}

	inline static float ElementaryTermTimeVariation(float fHistoValue1, float fHistoValue2)
	{
		// return fabs(fHistoValue1 - fHistoValue2)/min(max(1.0f, fHistoValue2), 3.0f);
		return fabs(fHistoValue1 - fHistoValue2)/sqrt(max(1.0f, fHistoValue2));
		//if (fHistoValue2<=1.0f)
		//	return fabs(fHistoValue1 - fHistoValue2);
		//else
		//	return fabs(fHistoValue1 - fHistoValue2)/max(1.0f, log(fHistoValue2));
	}

	#ifdef __glut_h__
	virtual void DrawOpenGL();
	#endif
};

class CHistogramRGB : public CHistogramBase, public CArray3D<float>
{
  // Attributes
  public:
	CArray1D<CTriplet<int> > vectNeighborhood;
	CArray1D<int> vectNeighborhoodOffsets;
	CArray1D<float> vectNeighborhoodCoefs;

	// CArray3D<float> arrayLogs; // Store logarithms of histogram values
	CArray3D<unsigned char> arrayStatus; // Border flag -> faster test if color is in safety area

  // Methods
  public:
	virtual typeHistogramColorSpace GetColorSpace() {return HISTOGRAMCOLORSPACE_RGB;}

	CHistogramRGB();
	virtual ~CHistogramRGB() {}

	virtual inline int GetNbColorLevels() {return iNbColorLevels;}
	virtual void SetNbColorLevels(int);

	virtual inline float GetGaussianStdDeviation() {return fGaussianStdDeviation;}
	virtual void SetGaussianStdDeviation(float);

	virtual void Empty() {Fill(0.0f);}
	virtual void Destroy() {iNbColorLevels = 0; CArray3D<float>::Empty(); arrayStatus.Empty();}
	virtual void operator =(CHistogramBase &);

	// Add and subtract pixels
	virtual void AddIntPixel(const CTriplet<int> &, float fWeight=1.0f);
	virtual void SubtractIntPixel(const CTriplet<int> &, float fWeight=1.0f);
	
	// Overloaded operators
	virtual void operator +=(CHistogramBase &);
	virtual void operator -=(CHistogramBase &);
	virtual void operator *=(float);
	virtual void operator /=(float);

	virtual float GetValue(const CTriplet<int> &);
	
	#ifdef __glut_h__
	virtual void DrawOpenGL();
	#endif
};

#endif
