#include <fcntl.h>
#include <linux/fb.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/amlogic/amlogic_window_provider.h>

// Nothing else sets up /dev/fb0 when EGL is used (fbClass::SetMode() is not run): set the mode and
// clear every page, otherwise memory left over from the boot is shown before the first frame is presented
static void prepareFramebuffer(int width, int height) {
	int fd = open("/dev/fb0", O_RDWR | O_CLOEXEC);
	if (fd < 0) {
		eDebug("[AmlogicWindowProvider] /dev/fb0 not available: %m");
		return;
	}
	fb_var_screeninfo var;
	if (ioctl(fd, FBIOGET_VSCREENINFO, &var) < 0) {
		eDebug("[AmlogicWindowProvider] FBIOGET_VSCREENINFO: %m");
		close(fd);
		return;
	}
	var.xres = width;
	var.xres_virtual = width;
	var.yres = height;
	var.xoffset = 0;
	var.yoffset = 0;
	var.bits_per_pixel = 32;
	var.activate = FB_ACTIVATE_ALL;
	var.transp.offset = 24;
	var.transp.length = 8;
	var.red.offset = 16;
	var.red.length = 8;
	var.green.offset = 8;
	var.green.length = 8;
	var.blue.offset = 0;
	var.blue.length = 8;
	for (int pages = 3; pages >= 1; --pages) {
		var.yres_virtual = height * pages;
		if (ioctl(fd, FBIOPUT_VSCREENINFO, &var) == 0)
			break;
	}
	ioctl(fd, FBIOGET_VSCREENINFO, &var);
	fb_fix_screeninfo fix;
	if (ioctl(fd, FBIOGET_FSCREENINFO, &fix) == 0) {
		size_t size = (size_t)fix.line_length * var.yres_virtual;
		if (size > fix.smem_len)
			size = fix.smem_len;
		void *mem = mmap(nullptr, size, PROT_WRITE | PROT_READ, MAP_SHARED, fd, 0);
		if (mem != MAP_FAILED) {
			memset(mem, 0, size);
			munmap(mem, size);
		}
	}
	var.xoffset = 0;
	var.yoffset = 0;
	ioctl(fd, FBIOPAN_DISPLAY, &var);
	eDebug("[AmlogicWindowProvider] fb0 %ux%u, %u pages, cleared", var.xres, var.yres, var.yres_virtual / (var.yres ? var.yres : 1));
	close(fd);
}

AmlogicWindowProvider::AmlogicWindowProvider(int width, int height) {
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
}

AmlogicWindowProvider::~AmlogicWindowProvider() {
	// nothing to tear down: fbdev_window is stack-allocated
}

bool AmlogicWindowProvider::init(int width, int height) {
	// The Amlogic/Mali-fbdev backend needs no display connection or
	// surface object — the kernel driver opens the fbdev node by itself.
	// We simply record the requested dimensions and return success.
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
	prepareFramebuffer(width, height);
	eDebug("[AmlogicWindowProvider] init %dx%d", width, height);
	return true;
}

EGLNativeDisplayType AmlogicWindowProvider::getNativeDisplay() {
	// Mali fbdev EGL resolves the display internally from the fbdev node.
	// EGL_DEFAULT_DISPLAY is the correct value here.
	return EGL_DEFAULT_DISPLAY;
}

EGLNativeWindowType AmlogicWindowProvider::getNativeWindow() {
	// Mali fbdev EGL expects a pointer to the fbdev_window struct.
	return reinterpret_cast<EGLNativeWindowType>(&m_native_window);
}

void AmlogicWindowProvider::cleanup() {
	// Nothing to release: no display connection, no allocated surface.
}
