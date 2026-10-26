#include <lib/gdi/gfbdc.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <lib/gdi/accel.h>

#ifdef DREAMNEXTGEN
#include <lib/gdi/dreamge2d.h>
#endif

#include <algorithm>
#include <cstring>

#if defined(DREAMBCM_ION_ACCEL)
#include <cstdlib>
#endif

#include <time.h>
#include <sys/time.h>

#ifdef HAVE_OSDANIMATION
#include <lib/base/cfile.h>
#endif

#if defined(CONFIG_ION) || defined(CONFIG_HISILICON_FB)
#include <lib/gdi/grc.h>

extern int bcm_accel_blit(
		int src_addr, int src_width, int src_height, int src_stride, int src_format,
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int src_x, int src_y, int width, int height,
		int dst_x, int dst_y, int dwidth, int dheight,
		int pal_addr, int flags);
#endif
#ifdef HAVE_HISILICON_ACCEL
extern void  dinobot_accel_register(void *p1,void *p2);
extern void  dinibot_accel_notify(void);
#endif

gFBDC::gFBDC()
{
	fb=new fbClass;
#ifndef CONFIG_ION
	if (!fb->Available())
		eFatal("[gFBDC] no framebuffer available");
#endif

	int xres;
	int yres;
	int bpp;
	fb->getMode(xres, yres, bpp);

	/* we can only use one of these three modes: */
	if (!((xres == 720 && yres == 576)
		|| (xres == 1280 && yres == 720)
		|| (xres == 1920 && yres == 1080)))
	{
		/* fallback to a decent default */
		xres = 720;
		yres = 576;
	}

	surface.clut.data = 0;
	setResolution(xres, yres); // default res

	reloadSettings();
}

gFBDC::~gFBDC()
{
#if defined(CONFIG_ION)
	if (m_logical_surface.data_phys && gAccel::getInstance())
		gAccel::getInstance()->accelFree(&m_logical_surface);
#endif
	delete fb;
	delete[] surface.clut.data;
}

void gFBDC::calcRamp()
{
#if 0
	float fgamma=gamma ? gamma : 1;
	fgamma/=10.0;
	fgamma=1/log(fgamma);
	for (int i=0; i<256; i++)
	{
		float raw=i/255.0; // IIH, float.
		float corr=pow(raw, fgamma) * 256.0;

		int d=corr * (float)(256-brightness) / 256 + brightness;
		if (d < 0)
			d=0;
		if (d > 255)
			d=255;
		ramp[i]=d;

		rampalpha[i]=i*alpha/256;
	}
#endif
	for (int i=0; i<256; i++)
	{
		int d;
		d=i;
		d=(d-128)*(gamma+64)/(128+64)+128;
		d+=brightness-128; // brightness correction
		if (d<0)
			d=0;
		if (d>255)
			d=255;
		ramp[i]=d;

		rampalpha[i]=i*alpha/256;
	}

	rampalpha[255]=255; // transparent BLEIBT bitte so.
}

void gFBDC::setPalette()
{
	if (!surface.clut.data)
		return;

	for (int i=0; i<256; ++i)
	{
		fb->CMAP()->red[i]=ramp[surface.clut.data[i].r]<<8;
		fb->CMAP()->green[i]=ramp[surface.clut.data[i].g]<<8;
		fb->CMAP()->blue[i]=ramp[surface.clut.data[i].b]<<8;
		fb->CMAP()->transp[i]=rampalpha[surface.clut.data[i].a]<<8;
	}
	fb->PutCMAP();
}

int gFBDC::getSurfaceOffset(const gUnmanagedSurface &s) const
{
	if (!s.data_phys)
		return 0;

	return (s.data_phys - fb->getPhysAddr()) / s.stride;
}

void gFBDC::rotateSurfaces()
{
	if (m_number_of_pages > 2 && surface_third.data_phys)
	{
		gUnmanagedSurface previously_displayed = surface_back;
		surface_back = surface;
		surface = surface_third;
		surface_third = previously_displayed;
	}
	else if (surface_back.data_phys)
	{
		std::swap(surface, surface_back);
	}
}

#if defined(DREAMBCM_ION_ACCEL)
static bool dreambcm_env_enabled(const char *name, bool default_value)
{
	const char *value = getenv(name);
	if (!value || !*value)
		return default_value;
	return atoi(value) != 0;
}
#endif

void gFBDC::exec(const gOpcode *o)
{
	std::lock_guard<std::recursive_mutex> lock(m_graphics_mutex);
	if (m_graphics_suspended)
	{
		discardOpcode(o);
		return;
	}

	switch (o->opcode)
	{
	case gOpcode::setPalette:
	{
		gDC::exec(o);
		setPalette();
		break;
	}
	case gOpcode::flip:
	{
#if defined(CONFIG_ION) || defined(DREAMNEXTGEN)
		fb->setOffset(getSurfaceOffset(surface));

		if (surface_back.data_phys)
			rotateSurfaces();
#else
		if (surface_back.data_phys)
		{
			gUnmanagedSurface s(surface);
			surface = surface_back;
			surface_back = s;

			if (surface.data_phys > surface_back.data_phys)
				fb->setOffset(surface_back.y);
			else
				fb->setOffset(0);
		}
#endif
		break;
	}
	case gOpcode::waitVSync:
	{
		static timeval l;
		static int t;
		timeval now;

		if (t == 1000)
		{
			gettimeofday(&now, 0);

			int diff = (now.tv_sec - l.tv_sec) * 1000 + (now.tv_usec - l.tv_usec) / 1000;
			eDebug("[gFBDC] %d ms latency (%d fps)", diff, t * 1000 / (diff ? diff : 1));
			l = now;
			t = 0;
		}

		++t;

		fb->blit();
		fb->waitVSync();
		break;
	}
	case gOpcode::flush:
		fb->blit();
#if defined(CONFIG_ION)
		if (m_scaled_output && m_logical_surface.data_phys && surface.data_phys)
		{
			/* the skin is drawn at its own (larger) size, scale it down into the draw page */
			int ret = bcm_accel_blit(
				m_logical_surface.data_phys, m_logical_surface.x, m_logical_surface.y, m_logical_surface.stride, 0,
				surface.data_phys, surface.x, surface.y, surface.stride,
				0, 0, m_logical_surface.x, m_logical_surface.y,
				0, 0, surface.x, surface.y,
				0, 0);
			if (gAccel::getInstance())
				gAccel::getInstance()->sync();
			if (ret != 0)
				scaleLogicalToSurfaceCPU();
		}
		if (surface_back.data_phys)
		{
#if defined(DREAMBCM_ION_ACCEL)
			const bool pagecopy_enabled = dreambcm_env_enabled("DREAMBCM_PAGECOPY", true);
			const bool prepan_pagecopy = pagecopy_enabled && dreambcm_env_enabled("DREAMBCM_PREPAN_PAGECOPY", true) && (m_number_of_pages > 2) && surface_third.data_phys;

			if (prepan_pagecopy)
			{
				/*
				 * Triple-buffer Dreambox Broadcom path:
				 * copy the fully rendered draw page into the next draw page before
				 * switching the displayed framebuffer page.  The old OpenATV order
				 * panned first and copied afterwards; DreamOS traces show the Broadcom
				 * acceleration work before FBIOPAN_DISPLAY.
				 */
				bcm_accel_blit(
					surface.data_phys, surface.x, surface.y, surface.stride, 0,
					surface_third.data_phys, surface_third.x, surface_third.y, surface_third.stride,
					0, 0, surface.x, surface.y,
					0, 0, surface.x, surface.y,
					0, 0);
				if (gAccel::getInstance())
				{
					gAccel::getInstance()->dreamBCMPagecopyStat();
					gAccel::getInstance()->sync();
				}

				fb->waitVSync();
				fb->setOffset(getSurfaceOffset(surface));
				rotateSurfaces();
			}
			else
#endif
			{
				fb->waitVSync();
				fb->setOffset(getSurfaceOffset(surface));

				rotateSurfaces();

#if defined(DREAMBCM_ION_ACCEL)
				if (pagecopy_enabled)
				{
#endif
				bcm_accel_blit(
					surface_back.data_phys, surface_back.x, surface_back.y, surface_back.stride, 0,
					surface.data_phys, surface.x, surface.y, surface.stride,
					0, 0, surface.x, surface.y,
					0, 0, surface.x, surface.y,
					0, 0);
#if defined(DREAMBCM_ION_ACCEL)
					if (gAccel::getInstance())
					{
						gAccel::getInstance()->dreamBCMPagecopyStat();
						gAccel::getInstance()->sync();
					}
				}
#endif
			}
		}
#elif defined(DREAMNEXTGEN)
		if (surface_back.data_phys && surface.data)
		{
			fb->waitVSync();
			fb->setOffset(getSurfaceOffset(surface));

			rotateSurfaces();

			bool ge2d_copied = dreamGE2DCopySurface(&surface, &surface_back, surface.x, surface.y);
			if (!ge2d_copied)
			{
				const int virtual_height = surface.y * m_number_of_pages;
				const int src_y = getSurfaceOffset(surface_back);
				const int dst_y = getSurfaceOffset(surface);
				ge2d_copied = dreamGE2DCopyOSD(src_y, dst_y, surface.x, surface.y, virtual_height);
			}
			if (!ge2d_copied)
			{
				const int copy_bytes = surface.stride * surface.y;
				if (copy_bytes > 0)
					std::memcpy(surface.data, surface_back.data, copy_bytes);
			}
		}
#endif
#if defined(CONFIG_HISILICON_FB)
		if(islocked()==0)
		{
			bcm_accel_blit(
				surface.data_phys, surface.x, surface.y, surface.stride, 0,
				surface_back.data_phys, surface_back.x, surface_back.y, surface_back.stride,
				0, 0, surface.x, surface.y,
				0, 0, surface.x, surface.y,
				0, 0);
		}
#endif
#ifdef HAVE_HISILICON_ACCEL
		dinibot_accel_notify();
#endif
		break;
	case gOpcode::sendShow:
	{
#ifdef HAVE_OSDANIMATION
		CFile::writeIntHex("/proc/stb/fb/animation_mode", 0x01);
#endif
		delete o->parm.setShowHideInfo;
		break;
	}
	case gOpcode::sendHide:
	{
#ifdef HAVE_OSDANIMATION
		CFile::writeIntHex("/proc/stb/fb/animation_mode", 0x10);
#endif
		delete o->parm.setShowHideInfo;
		break;
	}
	default:
		gDC::exec(o);
		break;
	}
}

void gFBDC::setAlpha(int a)
{
	alpha=a;

	calcRamp();
	setPalette();
}

void gFBDC::setBrightness(int b)
{
	brightness=b;

	calcRamp();
	setPalette();
}

void gFBDC::setGamma(int g)
{
	gamma=g;

	calcRamp();
	setPalette();
}

void gFBDC::setResolution(int xres, int yres, int bpp)
{
	std::lock_guard<std::recursive_mutex> lock(m_graphics_mutex);
	if (m_pixmap && (m_requested_x == xres) && (m_requested_y == yres) && (surface.bpp == bpp)
	#if defined(CONFIG_HISILICON_FB)
		&& islocked()==0
	#endif
		)
		return;
#ifndef CONFIG_ION
	if (gAccel::getInstance())
		gAccel::getInstance()->releaseAccelMemorySpace();
#else
	gRC *grc = gRC::getInstance();
	if (grc)
		grc->lock();
#endif
	m_requested_x = xres;
	m_requested_y = yres;

	/* The OSD hardware tops out at 1920x1080.  Bigger skins (WQHD, 4K) are
	 * drawn into an off-screen logical surface and scaled down on flush. */
	const int logical_xres = xres;
	const int logical_yres = yres;
#ifdef HAVE_FBWQHD
	if (xres > 1920 || yres > 1080)
	{
		xres = 1920;
		yres = 1080;
	}
#endif

	fb->SetMode(xres, yres, bpp);

	unsigned char *base_addr = fb->lfb;
	unsigned long base_phys = fb->getPhysAddr();

	surface.x = xres;
	surface.y = yres;
	surface.bpp = bpp;
	surface.bypp = bpp / 8;
	surface.stride = fb->Stride();
	surface.data = base_addr;

	for (int y=0; y<yres; y++) // make whole screen transparent
		memset(fb->lfb+ y * xres * 4, 0x00, xres * 4);

	surface.data_phys = base_phys;

	m_number_of_pages = fb->getNumPages();

	int fb_page_size = surface.stride * surface.y;
	int fb_size = fb_page_size;

#if defined(CONFIG_ION) || defined(DREAMNEXTGEN)
	if (m_number_of_pages > 1)
	{
		surface_back = surface;
		fb_size += fb_page_size;
		// the hardware starts on the first page; draw to the next one first
		surface_back.data = base_addr;
		surface_back.data_phys = base_phys;

		surface.data = base_addr + fb_page_size;
		surface.data_phys = base_phys + fb_page_size;
	}
	else
	{
		surface_back.data = 0;
		surface_back.data_phys = 0;
	}

	if (m_number_of_pages > 2)
	{
		surface_third = surface;
		surface_third.data = base_addr + fb_page_size * 2;
		surface_third.data_phys = base_phys + fb_page_size * 2;
		fb_size += fb_page_size;
	}
	else
	{
		surface_third.data = 0;
		surface_third.data_phys = 0;
	}
#else
	if (m_number_of_pages > 1)
	{
		surface_back = surface;
		surface_back.data = base_addr + fb_page_size;
		surface_back.data_phys = base_phys + fb_page_size;
		fb_size = fb_page_size * 2;
	}
	else
	{
		surface_back.data = 0;
		surface_back.data_phys = 0;
	}

        surface_third.data = 0;
        surface_third.data_phys = 0;
#endif

	eDebug("[gFBDC] resolution: %d x %d x %d (stride: %d) pages: %d", surface.x, surface.y, surface.bpp, fb->Stride(), fb->getNumPages());

#ifndef CONFIG_ION
	/* accel is already set in fb.cpp */
	eDebug("[gFBDC] %dkB available for acceleration surfaces.", (fb->Available() - fb_size)/1024);
	if (gAccel::getInstance())
		gAccel::getInstance()->setAccelMemorySpace(fb->lfb + fb_size, surface.data_phys + fb_size, fb->Available() - fb_size);
#endif
#ifdef HAVE_HISILICON_ACCEL
	dinobot_accel_register(&surface,&surface_back);
#endif
	if (!surface.clut.data)
	{
		surface.clut.colors = 256;
		surface.clut.data = new gRGB[surface.clut.colors];
		memset(static_cast<void*>(surface.clut.data), 0, sizeof(*surface.clut.data)*surface.clut.colors);
	}

	surface_back.clut = surface.clut;
	surface_third.clut = surface.clut;

	m_scaled_output = false;
#if defined(CONFIG_ION)
	if (m_logical_surface.data_phys && gAccel::getInstance())
		gAccel::getInstance()->accelFree(&m_logical_surface);
	m_logical_surface.data = 0;
	m_logical_surface.data_phys = 0;
	if (logical_xres != xres || logical_yres != yres)
	{
		m_logical_surface.x = logical_xres;
		m_logical_surface.y = logical_yres;
		m_logical_surface.bpp = bpp;
		m_logical_surface.bypp = bpp / 8;
		m_logical_surface.stride = logical_xres * (bpp / 8);
		m_logical_surface.clut = surface.clut;
		if (bpp == 32 && gAccel::getInstance() && gAccel::getInstance()->accelAlloc(&m_logical_surface) == 0 && m_logical_surface.data_phys)
		{
			memset(m_logical_surface.data, 0, m_logical_surface.stride * m_logical_surface.y);
			m_scaled_output = true;
			eDebug("[gFBDC] scaled output: logical %dx%d -> physical %dx%d", logical_xres, logical_yres, xres, yres);
		}
		else
		{
			m_logical_surface.data = 0;
			m_logical_surface.data_phys = 0;
			eDebug("[gFBDC] can't allocate logical surface %dx%d, scaled output disabled", logical_xres, logical_yres);
		}
	}
#endif

#ifdef DREAMNEXTGEN
	dreamGE2DRegisterFramebuffer(fb->lfb, base_phys, surface.x, surface.y, surface.stride, m_number_of_pages);
#endif

#if defined(CONFIG_HISILICON_FB)
	if(islocked()==0)
	{
		gUnmanagedSurface s(surface);
		surface = surface_back;
		surface_back = s;
	}
#endif

	if (m_scaled_output)
		m_pixmap = new gPixmap(&m_logical_surface);
	else
		m_pixmap = new gPixmap(&surface);
		invalidateNativeSpinner();

#ifdef CONFIG_ION
	if (grc)
		grc->unlock();
#endif
}

void gFBDC::scaleLogicalToSurfaceCPU()
{
	/* fallback when the hardware scaler refused the blit: nearest neighbour */
	if (!m_logical_surface.data || !surface.data || m_logical_surface.bypp != 4 || surface.bypp != 4)
		return;
	for (int y = 0; y < surface.y; y++)
	{
		const unsigned int *src = (const unsigned int *)((unsigned char *)m_logical_surface.data + (long)(y * m_logical_surface.y / surface.y) * m_logical_surface.stride);
		unsigned int *dst = (unsigned int *)((unsigned char *)surface.data + (long)y * surface.stride);
		for (int x = 0; x < surface.x; x++)
			dst[x] = src[x * m_logical_surface.x / surface.x];
	}
}

bool gFBDC::suspendGraphics()
{
	std::lock_guard<std::recursive_mutex> lock(m_graphics_mutex);

	if (m_graphics_suspended)
		return true;
	if (!fb || !fb->Available())
		return false;
	if (!fb->islocked())
		eDebug("[gFBDC] suspending graphics without fbClass lock; callers should lock painting first");

	/*
	 * fbClass::lock() prevents new gPainter commands.  The suspended flag also
	 * makes exec() dispose commands which were already queued without touching
	 * the framebuffer while an external graphics client owns the display.
	 */
	m_graphics_suspended = true;
	eDebug("[gFBDC] framebuffer graphics suspended");
	return true;
}

bool gFBDC::resumeGraphics()
{
	std::lock_guard<std::recursive_mutex> lock(m_graphics_mutex);

	if (!m_graphics_suspended)
		return true;
	if (!fb || !fb->Available())
		return false;
	if (fb->islocked())
	{
		eDebug("[gFBDC] graphics resume deferred while fbClass is still locked");
		return false;
	}

	/*
	 * fbClass::unlock() calls SetMode().  On ION targets this unmaps and maps
	 * the framebuffer again, so the unmanaged surfaces and m_pixmap must be
	 * rebound before drawing is allowed to continue.
	 */
	const int xres = m_requested_x ? m_requested_x : surface.x;
	const int yres = m_requested_y ? m_requested_y : surface.y;
	const int bpp = surface.bpp;
	m_pixmap = 0;
	m_graphics_suspended = false;
	setResolution(xres, yres, bpp);

	eDebug("[gFBDC] framebuffer graphics resumed at %dx%dx%d", xres, yres, bpp);
	return true;
}

bool gFBDC::isGraphicsSuspended() const
{
	std::lock_guard<std::recursive_mutex> lock(m_graphics_mutex);
	return m_graphics_suspended;
}

void gFBDC::saveSettings()
{
}

void gFBDC::reloadSettings()
{
	alpha=255;
	gamma=128;
	brightness=128;

	calcRamp();
	setPalette();
}

eAutoInitPtr<gFBDC> init_gFBDC(eAutoInitNumbers::graphic-1, "GFBDC");

#ifdef HAVE_OSDANIMATION
void setAnimation_current(int a) {
	switch (a) {
		case 1:
			CFile::writeStr("/proc/stb/fb/animation_current", "simplefade");
			break;
		case 2:
			CFile::writeStr("/proc/stb/fb/animation_current", "simplezoom");
			break;
		case 3:
			CFile::writeStr("/proc/stb/fb/animation_current", "growdrop");
			break;
		case 4:
			CFile::writeStr("/proc/stb/fb/animation_current", "growfromleft");
			break;
		case 5:
			CFile::writeStr("/proc/stb/fb/animation_current", "extrudefromleft");
			break;
		case 6:
			CFile::writeStr("/proc/stb/fb/animation_current", "popup");
			break;
		case 7:
			CFile::writeStr("/proc/stb/fb/animation_current", "slidedrop");
			break;
		case 8:
			CFile::writeStr("/proc/stb/fb/animation_current", "slidefromleft");
			break;
		case 9:
			CFile::writeStr("/proc/stb/fb/animation_current", "slidelefttoright");
			break;
		case 10:
			CFile::writeStr("/proc/stb/fb/animation_current", "sliderighttoleft");
			break;
		case 11:
			CFile::writeStr("/proc/stb/fb/animation_current", "slidetoptobottom");
			break;
		case 12:
			CFile::writeStr("/proc/stb/fb/animation_current", "zoomfromleft");
			break;
		case 13:
			CFile::writeStr("/proc/stb/fb/animation_current", "zoomfromright");
			break;
		case 14:
			CFile::writeStr("/proc/stb/fb/animation_current", "stripes");
			break;
		default:
			CFile::writeStr("/proc/stb/fb/animation_current", "disable");
			break;
	}
}

void setAnimation_speed(int speed) {
	CFile::writeInt("/proc/stb/fb/animation_speed", speed);
}

void setAnimation_current_listbox(int a) {}
#endif
