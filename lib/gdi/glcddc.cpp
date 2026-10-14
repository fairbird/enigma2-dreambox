#include <lib/gdi/glcddc.h>
#include <lib/gdi/lcd.h>
#include <lib/gdi/fblcd.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <string.h>

gLCDDC *gLCDDC::instance;

gLCDDC::gLCDDC()
{
#ifndef NO_LCD
	lcd = new eFbLCD();
	if (!lcd->detected())
	{
		delete lcd;
		lcd = new eDBoxLCD();
	}
#else
		lcd = new eDBoxLCD();
#endif
	instance = this;

	update = 1;
	m_fade_wait = false;
	m_fading = false;
	m_fade_ms = 400;

	surface.x = lcd->size().width();
	surface.y = lcd->size().height();
	surface.stride = lcd->stride();
	surface.bypp = surface.stride / surface.x;
	surface.bpp = surface.bypp*8;
	surface.data = lcd->buffer();
	surface.data_phys = 0;
	if (lcd->getLcdType() == 4)
	{
		surface.clut.colors = 256;
		surface.clut.data = new gRGB[surface.clut.colors];
		memset(static_cast<void*>(surface.clut.data), 0, sizeof(*surface.clut.data)*surface.clut.colors);
	}
	else
	{
		surface.clut.colors = 0;
		surface.clut.data = 0;
	}
	eDebug("[gLCDDC] resolution: %dx%dx%d stride=%d", surface.x, surface.y, surface.bpp, surface.stride);

	m_pixmap = new gPixmap(&surface);
}

gLCDDC::~gLCDDC()
{
	delete lcd;
	if (surface.clut.data)
		delete[] surface.clut.data;
	instance = 0;
}

void gLCDDC::fadeBegin(const gOpcode *o)
{
	const gOpcode::para::psetShowHideInfo *info = o->parm.setShowHideInfo;
	if (m_fading)
		fadeEnd();
	if (!surface.data || (surface.bypp != 2 && surface.bypp != 4) || surface.clut.colors || m_fades.size() >= 4)
		return;
	int x = info->point.x(), y = info->point.y();
	int w = info->size.width(), h = info->size.height();
	if (x < 0) { w += x; x = 0; }
	if (y < 0) { h += y; y = 0; }
	if (x + w > surface.x) w = surface.x - x;
	if (y + h > surface.y) h = surface.y - y;
	if (w <= 0 || h <= 0)
		return;
	LcdFade f;
	f.x = x; f.y = y; f.w = w; f.h = h;
	f.oldpix.resize(w * h * surface.bypp);
	for (int r = 0; r < h; ++r)
		memcpy(&f.oldpix[r * w * surface.bypp], (uint8_t*)surface.data + (y + r) * surface.stride + x * surface.bypp, w * surface.bypp);
	m_fades.push_back(f);
	m_fade_ms = info->anim_id;
	if (m_fade_ms < 50) m_fade_ms = 50;
	if (m_fade_ms > 1000) m_fade_ms = 1000;
	m_fade_wait = true;
}

void gLCDDC::fadeStart()
{
	for (size_t i = 0; i < m_fades.size(); ++i)
	{
		LcdFade &f = m_fades[i];
		f.newpix.resize(f.w * f.h * surface.bypp);
		for (int r = 0; r < f.h; ++r)
			memcpy(&f.newpix[r * f.w * surface.bypp], (uint8_t*)surface.data + (f.y + r) * surface.stride + f.x * surface.bypp, f.w * surface.bypp);
	}
	m_fade_wait = false;
	m_fading = true;
	m_fade_t0 = m_fade_last = std::chrono::steady_clock::now();
	fadeBlend(0);
}

void gLCDDC::fadeBlend(int a)
{
	const int b = 256 - a;
	for (size_t i = 0; i < m_fades.size(); ++i)
	{
		LcdFade &f = m_fades[i];
		for (int r = 0; r < f.h; ++r)
		{
			uint8_t *dst = (uint8_t*)surface.data + (f.y + r) * surface.stride + f.x * surface.bypp;
			const uint8_t *po = &f.oldpix[r * f.w * surface.bypp];
			const uint8_t *pn = &f.newpix[r * f.w * surface.bypp];
			if (surface.bypp == 2)
			{
				for (int c = 0; c < f.w; ++c)
				{
					const uint16_t o = ((const uint16_t*)po)[c], n = ((const uint16_t*)pn)[c];
					const uint16_t hi = (((n >> 11) * a + (o >> 11) * b) >> 8) & 31;
					const uint16_t mid = ((((n >> 5) & 63) * a + ((o >> 5) & 63) * b) >> 8) & 63;
					const uint16_t lo = (((n & 31) * a + (o & 31) * b) >> 8) & 31;
					((uint16_t*)dst)[c] = (hi << 11) | (mid << 5) | lo;
				}
			}
			else
			{
				for (int c = 0; c < f.w * 4; ++c)
					dst[c] = (pn[c] * a + po[c] * b) >> 8;
			}
		}
	}
}

void gLCDDC::fadeEnd()
{
	if (m_fading)
		fadeBlend(256);
	m_fading = false;
	m_fade_wait = false;
	m_fades.clear();
}

void gLCDDC::fadeTick()
{
	if (!m_fading)
		return;
	const std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
	if (std::chrono::duration_cast<std::chrono::milliseconds>(now - m_fade_last).count() < 30)
		return;
	m_fade_last = now;
	const int ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - m_fade_t0).count();
	if (ms >= m_fade_ms)
		fadeEnd();
	else
		fadeBlend(ms * 256 / m_fade_ms);
	lcd->update();
}

void gLCDDC::exec(const gOpcode *o)
{
	if (o->opcode == gOpcode::beginFade)
	{
		fadeBegin(o);
		delete o->parm.setShowHideInfo;
		return;
	}
	if (m_fading && o->opcode != gOpcode::flush)
		fadeEnd();
	switch (o->opcode)
	{
	case gOpcode::setPalette:
	{
		gDC::exec(o);
		lcd->setPalette(surface);
		break;
	}
#ifdef HAVE_TEXTLCD
	case gOpcode::renderText:
		if (o->parm.renderText->text)
		{
			lcd->renderText(gDC::m_current_offset, o->parm.renderText->text);
			free(o->parm.renderText->text);
		}
		delete o->parm.renderText;
		break;
#endif
	case gOpcode::flush:
		if (m_fade_wait)
			fadeStart();
		lcd->update();
		[[fallthrough]];
	default:
		gDC::exec(o);
		break;
	}
}

void gLCDDC::setUpdate(int u)
{
	update = u;
}

eAutoInitPtr<gLCDDC> init_gLCDDC(eAutoInitNumbers::graphic-1, "gLCD");
