#ifndef __LIB_COMPONENTS_DECODER_H
#define __LIB_COMPONENTS_DECODER_H

#include <lib/base/ebase.h>


class eAudioDecoder
{
	E_DECLARE_PRIVATE(eAudioDecoder);
	E_DISABLE_COPY(eAudioDecoder);

public:
	eAudioDecoder();
	~eAudioDecoder();
	bool started() const;

	int start(int type, int sample_rate=-1, int channels=-1, int misc=-1, int bit_rate=-1, int block_align=-1, int codec_data_size=0, const uint8_t *codec_data=NULL, std::string raw_format="");
	void stop();
	void reset();
	void decode(const uint8_t *data, int bytes, int64_t pts, sigc::slot<void, uint8_t*, int, int64_t> hdmi_callback, sigc::slot<bool> abort, bool need_more_data_callback = false, sigc::slot<void, uint8_t*, int, int64_t> spdif_callback=sigc::slot<void, uint8_t*, int, int64_t>(), sigc::slot<void, uint8_t*, int, int64_t> pcm_callback=sigc::slot<void, uint8_t*, int, int64_t>());
	unsigned int channels() const;
	unsigned int sample_rate() const;
	unsigned int bits() const;
};

#endif //__LIB_COMPONENTS_DECODER_H
