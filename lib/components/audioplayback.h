#ifndef __LIB_COMPONENTS_AUDIOPLAYBACK_H
#define __LIB_COMPONENTS_AUDIOPLAYBACK_H

#include <lib/base/ebase.h>

class eConnection;

class eAudioPlayback: public iObject
{
	DECLARE_REF(eAudioPlayback);
	E_DECLARE_PRIVATE(eAudioPlayback);
	E_DISABLE_COPY(eAudioPlayback);

public:
	eAudioPlayback(const sigc::slot<int64_t> &get_stc, const sigc::slot<void> &audioConsumed);
	~eAudioPlayback();

	int init(int type, int samplerate = -1, int channels = -1, int misc = -1, int bitrate = -1, int block_align = -1, int codec_data_size = 0, const uint8_t *codec_data = NULL, std::string raw_format = "", int mpegversion = 4);
	void processAudio(const uint8_t *data, int bytes, int64_t pts, bool framed=true); // should be called from worker thread

	bool decoderStarted();

	void flush();
	void resetDecoder();
	void stopAudio();
	void stopDecoder();
	bool checkDecoderAbort();

	void stop(bool final = false); // should be called from worker thread
	void pause(); // should be called from worker thread
	void unpause(); // should be called from worker thread

	bool bufferFull(); // should be called from worker thread
	uint64_t bufferFillClockTicks() const;

	int64_t getPTS();

	RESULT connectPCMEvent(const sigc::slot<void, uint8_t*, int, int64_t>  &pcm_callback, ePtr<eConnection> &connection, int type = 0 /* 0 = eAlsaOutput::HDMI, 1 = eAlsaOutput::SPDIF */);
};

#endif //__LIB_COMPONENTS_AUDIOPLAYBACK_H
