#ifndef __gfbdc_h
#define __gfbdc_h

#include "fb.h"
#include "gpixmap.h"
#include "gmaindc.h"

#ifndef SWIG
#include <mutex>

class gFBDC: public gMainDC
{
	fbClass *fb;
	int brightness, gamma, alpha;
	gUnmanagedSurface surface;
	gUnmanagedSurface surface_back;
	gUnmanagedSurface surface_third;
	gUnmanagedSurface m_logical_surface; // off-screen skin canvas when the skin is larger than the OSD hardware (WQHD)
	bool m_scaled_output = false;
	int m_requested_x = 0, m_requested_y = 0;
	int m_number_of_pages = 1;
	bool m_graphics_suspended = false;
	mutable std::recursive_mutex m_graphics_mutex;
	unsigned char ramp[256], rampalpha[256]; // RGB ramp 0..255
	void exec(const gOpcode *opcode);
	void calcRamp();
	void setPalette();
	void rotateSurfaces();
	void scaleLogicalToSurfaceCPU();
	void scaleLogicalToSurfaceNextGen();
	void freeLogicalSurface();
	bool m_logical_cpu = false; // the logical surface is a plain CPU buffer
	int getSurfaceOffset(const gUnmanagedSurface &s) const;
public:
	void setResolution(int xres, int yres, int bpp = 32);
	bool suspendGraphics() override;
	bool resumeGraphics() override;
	bool isGraphicsSuspended() const override;
	void reloadSettings();
	void setAlpha(int alpha);
	void setBrightness(int brightness);
	void setGamma(int gamma);

	int getAlpha() const { return alpha; }
	int getBrightness() const { return brightness; }
	int getGamma() const { return gamma; }

	int haveDoubleBuffering() const { return surface_back.data_phys != 0; }

	void saveSettings();

	gFBDC();
	virtual ~gFBDC();
	int islocked() const { return fb->islocked(); }
};
#endif
#ifdef HAVE_OSDANIMATION
void setAnimation_current(int a);
void setAnimation_speed(int speed);
void setAnimation_current_listbox(int a);
#endif
#endif
