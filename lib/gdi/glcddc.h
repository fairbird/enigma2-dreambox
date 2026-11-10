#ifndef __glcddc_h
#define __glcddc_h

#include "grc.h"
#include <lib/gdi/lcd.h>
#include <vector>
#include <chrono>
#include <stdint.h>

class gLCDDC: public gDC
{
	eLCD *lcd;
	static gLCDDC *instance;
	int update;
	void exec(const gOpcode *opcode);
	gUnmanagedSurface surface;
	struct LcdFade
	{
		int x, y, w, h;
		std::vector<uint8_t> oldpix, newpix;
	};
	std::vector<LcdFade> m_fades;
	bool m_fade_wait, m_fading;
	int m_fade_ms;
	std::chrono::steady_clock::time_point m_fade_t0, m_fade_last;
	void fadeBegin(const gOpcode *o);
	void fadeStart();
	void fadeBlend(int a);
	void fadeEnd();
public:
	gLCDDC();
	~gLCDDC();
	bool fadeActive() const { return m_fading; }
	void fadeTick();
	void setUpdate(int update);
	static int getInstance(ePtr<gLCDDC> &ptr) { if (!instance) return -1; ptr = instance; return 0; }
	int islocked() const { return lcd->islocked(); }
};

#endif
