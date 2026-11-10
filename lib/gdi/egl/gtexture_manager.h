#pragma once

#ifdef HAVE_GLES3
#include <GLES3/gl3.h>
#else
#include <GLES2/gl2.h>
#endif
#include <GLES2/gl2ext.h>

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <lib/gdi/gpixmap.h>
#include <mutex>
#include <unordered_map>
#include <vector>

class gTextureManager {
private:
	// thread safe garbage collection for destroyed pixmaps
	std::vector<GLuint> m_pending_deletions;
	std::mutex m_deletion_mutex;
	EGLDisplay m_egl_display;
	std::unordered_map<GLuint, EGLImageKHR> m_texture_to_image_map;

	// Diagnostic only (see gTextureManager::createTextureFromPixmap()/
	// processDeletions()): tracks how many GL textures this manager
	// currently believes are live, so a genuine unbounded leak (count keeps
	// climbing) can be told apart from a legitimate-but-too-high working set
	// (count plateaus, then the next alloc past that plateau fails). Both
	// the increment (getTexture(), on the render/GL thread) and the
	// decrement (processDeletions(), same thread) only ever run on the
	// single EGL context thread, so this doesn't need its own lock.
	long m_live_texture_count = 0;
	// Approximate GPU storage tracked for each texture, used only when a
	// GL_OUT_OF_MEMORY needs to trigger controlled LRU eviction.
	std::unordered_map<GLuint, size_t> m_texture_bytes;
	// texture name -> owning surface. This prevents a recycled GL name from
	// being released by a different surface after an LRU eviction.
	std::unordered_map<GLuint, gUnmanagedSurface*> m_texture_owner;
	unsigned int m_frame = 0;
	bool m_last_upload_oom = false;
	size_t evictLRU(size_t bytes_wanted);
	size_t m_live_texture_bytes = 0;

	// unified method to generate and upload the texture based on bpp
	GLuint createTextureFromPixmap(gPixmap* pixmap);
	GLuint createTextureFromDmabuf(gPixmap* pixmap);

public:
	gTextureManager();
	~gTextureManager();

	void setDisplay(EGLDisplay display) { m_egl_display = display; }

	// returns the gl texture id, creating it on the fly if not cached
	GLuint getTexture(gPixmap* pixmap);

	// called by enigma2 main thread when a pixmap dies
	void queueForDeletion(GLuint texture_id);

	// called by our egl context thread at the start of exec() to free vram
	void processDeletions();
	// Called once after presenting a frame; defines the frame boundary for LRU.
	void nextFrame() { ++m_frame; }
	void releaseSurfaceTexture(GLuint texture_id, const void* surface);
};
