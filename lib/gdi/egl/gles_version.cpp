#include <lib/gdi/egl/gles_version.h>

namespace gles {
int version = 0; // initialised to 0; set by gEGLDC::initEGL()
std::string eglVersionString; // set by gEGLDC::tryInitEGL()
std::string glesVersionString; // set by gEGLDC::tryInitEGL()
}
