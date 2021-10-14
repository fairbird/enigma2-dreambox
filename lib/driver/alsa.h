#ifndef __LIB_DRIVER_ALSA_H_
#define __LIB_DRIVER_ALSA_H_

#include <lib/base/ebase.h>

#ifndef SWIG
#define PCM_FRAMES 64
#define PCM_CHUNK_SIZE (8 * 1024)
#endif

class eAlsaOutput
{
	E_DECLARE_PRIVATE(eAlsaOutput);
	E_DISABLE_COPY(eAlsaOutput);
	static eAlsaOutput *instance[3];

	eAlsaOutput(int type);
	~eAlsaOutput();

public:
	enum { HDMI, SPDIF, BTPCM };

	static eAlsaOutput *getInstance(int type = HDMI);

	bool running() const;
	int close();
	int stop();
#ifndef SWIG
	int pause(int state);
	int start(unsigned int rate, unsigned int channels, unsigned int bits, const sigc::slot<int64_t> &get_stc, const sigc::slot<void> &buffer_consumed);
	int pushData(uint8_t *data, int size, int64_t pts);
	uint64_t fifoFillClockTicks() const;
	int fifoFill() const;
	int fifoSize() const;
	void flushFifo();
	int64_t getPTS();
	unsigned int sample_rate();
        unsigned int channels();
        unsigned int hw_channels();
        unsigned int bits();
#endif
};

#endif // __LIB_DRIVER_ALSA_H_
