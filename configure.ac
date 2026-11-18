AC_INIT([enigma2],[4],[https://github.com/fairbird/enigma2-dreambox])
AM_INIT_AUTOMAKE([dist-bzip2 no-define tar-pax -Wno-portability])
AC_CONFIG_HEADERS([enigma2_config.h])

# Silent rules are available since 1.11, but older versions
# are still in use. So don't use them unconditionally.
m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

AC_USE_SYSTEM_EXTENSIONS
AC_SYS_LARGEFILE

AC_PROG_CC
AC_PROG_CXX
PKG_PROG_PKG_CONFIG
m4_ifdef([LT_INIT], [LT_INIT], [AC_PROG_LIBTOOL])
AC_CONFIG_MACRO_DIR([m4])
AC_OPENMP()

AC_PATH_PROG(MSGFMT, msgfmt, AC_MSG_ERROR(Could not find msgfmt))

AM_PATH_PYTHON
AX_PYTHON_DEVEL
AX_PKG_SWIG
AX_SWIG_ENABLE_CXX
AX_SWIG_PYTHON
AX_PTHREAD

TUXBOX_APPS_DVB

AM_CONDITIONAL(HAVE_GIT_DIR, test -d "$srcdir/.git")
AM_CONDITIONAL(HAVE_FAKE_GIT_DIR, test -f "$srcdir/.git/last_commit_info")

dnl versions of gstreamer and plugins-base
AC_ARG_WITH(gstversion,
	AS_HELP_STRING([--with-gstversion],[use gstreamer version (major.minor)]),
	[GST_MAJORMINOR=$withval],[GST_MAJORMINOR=0.10])

PKG_CHECK_MODULES(TUXTXT, tuxbox-tuxtxt)
PKG_CHECK_MODULES(GSTREAMER, gstreamer-$GST_MAJORMINOR gstreamer-pbutils-$GST_MAJORMINOR  gstreamer-video-$GST_MAJORMINOR)
PKG_CHECK_MODULES(BASE, [freetype2 fribidi >= 1.0.0 harfbuzz >= 0.9.38 glib-2.0 gstreamer-$GST_MAJORMINOR gstreamer-pbutils-$GST_MAJORMINOR  gstreamer-video-$GST_MAJORMINOR gio-2.0 libdvbsi++ libpng libxml-2.0 sigc++-3.0 libssl libcrypto libcurl])
AC_MSG_CHECKING([for HarfBuzz FreeType integration])
saved_CPPFLAGS=$CPPFLAGS
saved_LIBS=$LIBS
CPPFLAGS="$CPPFLAGS $BASE_CFLAGS"
LIBS="$BASE_LIBS $LIBS"
AC_LINK_IFELSE([AC_LANG_PROGRAM([[#include <hb-ft.h>]],
	[[hb_face_destroy(hb_ft_face_create_referenced((FT_Face)0));]])],
	[AC_MSG_RESULT([yes])], [AC_MSG_ERROR([HarfBuzz must be built with FreeType support])])
CPPFLAGS=$saved_CPPFLAGS
LIBS=$saved_LIBS
PKG_CHECK_MODULES(LIBDDVD, libdreamdvd, HAVE_LIBDDVD="yes", HAVE_LIBDDVD="no")
AM_CONDITIONAL(HAVE_LIBDDVD, test "$HAVE_LIBDDVD" = "yes")
PKG_CHECK_MODULES(AVAHI, avahi-client)

AC_CHECK_LIB([atomic], [__atomic_exchange_8], [LIBATOMIC_LIBS="-latomic"], [LIBATOMIC_LIBS=""])
AC_SUBST(LIBATOMIC_LIBS)
AC_CHECK_LIB([bluray], [bd_open])
AC_CHECK_LIB([udfread], [udfread_init])
AC_CHECK_LIB([dl], [dlopen], [LIBDL_LIBS="-ldl"], [AC_MSG_ERROR([Could not find libdl])])
AC_SUBST(LIBDL_LIBS)
AC_CHECK_LIB([jpeg], [jpeg_set_defaults], [LIBJPEG_LIBS="-ljpeg"], [AC_MSG_ERROR([Could not find libjpeg])])
AC_SUBST(LIBJPEG_LIBS)
AC_CHECK_LIB([ungif], [DGifOpen], [LIBGIF_LIBS="-lungif"], [AC_CHECK_LIB([gif], [DGifOpen], [LIBGIF_LIBS="-lgif"], [AC_MSG_ERROR([Could not find libgif or libungif])])])
AC_SUBST(LIBGIF_LIBS)
AC_CHECK_LIB([webp], [WebPDecodeRGB],[LIBWEBP_LIBS="-lwebp"], [AC_MSG_ERROR([Could not find libwebp])])
AC_SUBST(LIBWEBP_LIBS)

PKG_CHECK_MODULES([SWSCALE], [libswscale], [
    AC_DEFINE([HAVE_SWSCALE], [1], [Define if libswscale is available])
], [
    AC_MSG_WARN([Could not find libswscale, scaling support will be disabled.])
])

AC_ARG_WITH(crashlogemail,
	[  --with-crashlogemail=crash log email address],
	[CRASHLOGEMAIL="$withval"],[CRASHLOGEMAIL="https://github.com/fairbird/enigma2-dreambox"])
AC_SUBST(CRASHLOGEMAIL)
AC_DEFINE_UNQUOTED(CRASH_EMAILADDR,"$CRASHLOGEMAIL",[crash log email address])

AC_ARG_WITH(boxtype,
	[  --with-boxtype=NAME box type [[none,dm800...]]],
	[BOXTYPE="$withval"],[BOXTYPE="dm800"])
AC_SUBST(BOXTYPE)
AC_DEFINE_UNQUOTED(BOXTYPE,"$BOXTYPE",[box type])

AC_ARG_WITH(colorlcd,
	AC_HELP_STRING([--with-colorlcd], [use 96x64 16bpp color display, yes or no]),
	[[withcolorlcd=$withval]],
	[[withcolorlcd=no]]
)
if test x"$withcolorlcd" != xno ; then
	AC_DEFINE(HAVE_COLORLCD, 1,[Define when using a 96x64 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD, test x"$withcolorlcd" != xno)

AC_ARG_WITH(colorlcd128,
	AC_HELP_STRING([--with-colorlcd128], [use 128x64 16bpp color display, yes or no]),
	[[withcolorlcd128=$withval]],
	[[withcolorlcd128=no]]
)
if test x"$withcolorlcd128" != xno ; then
	AC_DEFINE(HAVE_COLORLCD128, 1,[Define when using a 128x64 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD128, test x"$withcolorlcd" != xno)

AC_ARG_WITH(colorlcd220,
	AC_HELP_STRING([--with-colorlcd220], [use 220x176 16bpp color display, yes or no]),
	[[withcolorlcd220=$withval]],
	[[withcolorlcd220=no]]
)
if test x"$withcolorlcd220" != xno ; then
	AC_DEFINE(HAVE_COLORLCD220, 1,[Define when using a 220x176 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD220, test x"$withcolorlcd220" != xno)

AC_ARG_WITH(colorlcd240,
	AC_HELP_STRING([--with-colorlcd240], [use 240x80 16bpp color display, yes or no]),
	[[withcolorlcd240=$withval]],
	[[withcolorlcd240=no]]
)
if test x"$withcolorlcd240" != xno ; then
	AC_DEFINE(HAVE_COLORLCD240, 1,[Define when using a 240x80 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD240, test x"$withcolorlcd240" != xno)

AC_ARG_WITH(colorlcd390,
	AC_HELP_STRING([--with-colorlcd390], [use 390x240 16bpp color display, yes or no]),
	[[withcolorlcd390=$withval]],
	[[withcolorlcd390=no]]
)
if test x"$withcolorlcd390" != xno ; then
	AC_DEFINE(HAVE_COLORLCD390, 1,[Define when using a 390x240 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD390, test x"$withcolorlcd390" != xno)

AC_ARG_WITH(colorlcd400,
	AC_HELP_STRING([--with-colorlcd400], [use 400x176 16bpp color display, yes or no]),
	[[withcolorlcd400=$withval]],
	[[withcolorlcd400=no]]
)
if test x"$withcolorlcd400" != xno ; then
	AC_DEFINE(HAVE_COLORLCD400, 1,[Define when using a 400x176 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD400, test x"$withcolorlcd400" != xno)

AC_ARG_WITH(colorlcd480,
	AC_HELP_STRING([--with-colorlcd480], [use 480x320 16bpp color display, yes or no]),
	[[withcolorlcd480=$withval]],
	[[withcolorlcd480=no]]
)
if test x"$withcolorlcd480" != xno ; then
	AC_DEFINE(HAVE_COLORLCD480, 1,[Define when using a 480x320 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD480, test x"$withcolorlcd480" != xno)

AC_ARG_WITH(colorlcd720,
	AC_HELP_STRING([--with-colorlcd720], [use 720x576 16bpp color display, yes or no]),
	[[withcolorlcd720=$withval]],
	[[withcolorlcd720=no]]
)
if test x"$withcolorlcd720" != xno ; then
	AC_DEFINE(HAVE_COLORLCD720, 1,[Define when using a 720x576 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD720, test x"$withcolorlcd720" != xno)

AC_ARG_WITH(colorlcd800,
	AC_HELP_STRING([--with-colorlcd800], [use 800x480 16bpp color display, yes or no]),
	[[withcolorlcd800=$withval]],
	[[withcolorlcd800=no]]
)
if test x"$withcolorlcd800" != xno ; then
	AC_DEFINE(HAVE_COLORLCD800, 1,[Define when using a 800x480 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD800, test x"$withcolorlcd800" != xno)

AM_CONDITIONAL(DREAMBOX, test `echo "$BOXTYPE" | cut -b 1-2` == "dm" -o `echo "$BOXTYPE" | cut -b 1-5` == "dream")
AM_CONDITIONAL(HAVE_TEMPFANCONTROL, test "$BOXTYPE" == dm8000 -o "$BOXTYPE" == dm800se -o "$BOXTYPE" == dm500hd)
AM_CONDITIONAL(DM7252S, test "$BOXTYPE" == dm7252s)
AM_CONDITIONAL(DM8000, test "$BOXTYPE" == dm8000)
AM_CONDITIONAL(DM7435, test "$BOXTYPE" == dm7435)
AM_CONDITIONAL(DM520, test "$BOXTYPE" == dm520)
AM_CONDITIONAL(DM7020HD, test "$BOXTYPE" == dm7020hd)
AM_CONDITIONAL(DM800, test "$BOXTYPE" == dm800)
AM_CONDITIONAL(DM7405NAND, test "$BOXTYPE" == dm7405nand)
AM_CONDITIONAL(DM7405UBI, test "$BOXTYPE" == dm7405ubi)
AM_CONDITIONAL(HAVE_COLORLCD3, test "$MACHINEBUILD" == dm7080)
AM_CONDITIONAL(HAVE_COLORLCD240, test "$MACHINEBUILD" == dreamtwo)
AM_CONDITIONAL(HAVE_COLORLCD2, test "$MACHINEBUILD" == dm800se -o "$MACHINEBUILD" == dm800sev2 -o "$MACHINEBUILD" == dm820)
AM_CONDITIONAL(HAVE_COLORLCD1, test "$BOXTYPE" == dm8000 -o "$BOXTYPE" == dm800 -o "$BOXTYPE" == dm7020hd -o "$MACHINEBUILD" == dm7020hdv2)
AM_CONDITIONAL(HAVE_GRAUTEC8000, test "$BOXTYPE" == dm8000)
AM_CONDITIONAL(HAVE_GRAUTEC70X0, test "$BOXTYPE" == dm7020hd -o "$MACHINEBUILD" == dm7020hdv2 -o "$MACHINEBUILD" == dm7080)
AM_CONDITIONAL(LCD_FRAMEBUFFER_MODE, test "$BOXTYPE" == et8500 -o "$BOXTYPE" == et8500s -o "$BOXTYPE" == 8100s)

AS_IF([test "$MACHINEBUILD" == "dreamone"],[AC_DEFINE(HWDREAMONE, 1,[dreamone])])
AS_IF([test "$MACHINEBUILD" == "dreamtwo"],[AC_DEFINE(HWDREAMTWO, 1,[dreamtwo])])
AS_IF([test "$BOXTYPE" == "dm8000"],[AC_DEFINE(HWDM8000, 1,[dm8000])])
AS_IF([test "$BOXTYPE" == "dm7020hd" -o "$MACHINEBUILD" == "dm7020hdv2"],[AC_DEFINE(HWDM7020HD, 1,[dm7020hd])])
AS_IF([test "$BOXTYPE" == "dm7435"],[AC_DEFINE(HWDM7435, 1,[dm7435])])
AS_IF([test "$MACHINEBUILD" == "dm7080"],[AC_DEFINE(HWDM7080, 1,[dm7080])])
AS_IF([test "$MACHINEBUILD" == "dm820"],[AC_DEFINE(HWDM820, 1,[dm820])])
AS_IF([test "$BOXTYPE" == "dm520" -o "$BOXTYPE" == "dm525"],[AC_DEFINE(HWDM520, 1,[dm520])])
AS_IF([test "$BOXTYPE" == "dm7252s"],[AC_DEFINE(HWDM7252S, 1,[dm7252s])])
AS_IF([test "$MACHINEBUILD" == "dm900"],[AC_DEFINE(HWDM900, 1,[dm900])])
AS_IF([test "$MACHINEBUILD" == "dm920"],[AC_DEFINE(HWDM920, 1,[dm920])])
AS_IF([test "$MACHINEBUILD" == "dm800se"],[AC_DEFINE(HWDM800SE, 1,[dm800se])])
AS_IF([test "$MACHINEBUILD" == "dm500hd"],[AC_DEFINE(HWDM500HD, 1,[dm500hd])])
AS_IF([test "$MACHINEBUILD" == "dm800sev2"],[AC_DEFINE(HWDM800SEV2, 1,[dm800sev2])])
AS_IF([test "$MACHINEBUILD" == "dm500hdv2"],[AC_DEFINE(HWDM500HDV2, 1,[dm500hdv2])])

if test `echo "$BOXTYPE" | cut -b 1-2` == "dm" -o `echo "$BOXTYPE" | cut -b 1-5` == "dream"; then
	AC_DEFINE(DREAMBOX, 1, [Dreambox hardware])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "dreamone" -o "$BOXTYPE" == "dreamtwo"; then
	AC_DEFINE(DMAMLOGIC, 1, [Dreambox Amlogic hardware])
fi

if test "$BOXTYPE" == "dm7435" -o "$MACHINEBUILD" == "dm800se" -o "$MACHINEBUILD" == "dm800sev2" -o "$BOXTYPE" == "dm7020hd" -o "$MACHINEBUILD" == "dm7020hdv2" -o "$BOXTYPE" == "dms922x" -o "$BOXTYPE" == "dm7252s"; then
	AC_DEFINE(DREAMBOX_DUAL_TUNER, 1,[define BOXTYPE DM7080])
fi

if test "$MACHINEBUILD" == "dreamtwo"; then
	AC_DEFINE(LCD_COLOR_BYTESWAP_16, 1, [LCD 16-bit Byte-Swap])
fi

if test "$BOXTYPE" == "dm7435" -o "$BOXTYPE" == "dm7252s" -o "$BOXTYPE" == "dm520"; then
	AC_DEFINE(CONFIG_ION, 1,[define BOX use ION Allocator])
	AC_DEFINE(DREAMBCM_ION_ACCEL, 1,[define Dreambox Broadcom ION framebuffer acceleration])
fi

if test "$BOXTYPE" == "dm7435" -o "$BOXTYPE" == "dm7252s"; then
	AC_DEFINE(HAVE_HDMIIN_DM, 1,[has hdmi in dm])
fi

if test "$BOXTYPE" == "dm7252s"; then
	AC_DEFINE(LCD_DM900_Y_OFFSET, 4,[define LCD Y offset for dm900 and dm920])
	AC_DEFINE(HAVE_DM_FBC, 1,[define for dm900 and dm920])
	AC_DEFINE(ENABLE_TIMESHIFT_HW_LATENCY_FIX, 1,[define for dm900 and dm920])
fi

if test "$BOXTYPE" == "gb7252" -o "$BOXTYPE" == "dm7252s"; then
	AC_DEFINE(LCD_FORCE_RGB, 1,[define 16 Bit LCD force rgb])
fi
AC_ARG_WITH(nolcd,
	AC_HELP_STRING([--with-nolcd], [disable ascii based lcd, yes or no]),
	[[withnolcd=$withval]],
	[[withnolcd=no]]
)
if test x"$withnolcd" != xno ; then
	AC_DEFINE(NO_LCD, 1,[Define when disable an ascii based lcd device])
fi
AM_CONDITIONAL(NO_LCD, test x"$withnolcd" != xno)

AC_ARG_WITH(textlcd,
	AC_HELP_STRING([--with-textlcd], [use ascii based lcd, yes or no]),
	[[withtextlcd=$withval]],
	[[withtextlcd=no]]
)
if test x"$withtextlcd" != xno ; then
	AC_DEFINE(HAVE_TEXTLCD, 1,[Define when using an ascii based lcd device])
fi
AM_CONDITIONAL(HAVE_TEXTLCD, test x"$withtextlcd" != xno)

AC_ARG_WITH(egl,
	AC_HELP_STRING([--with-egl], [passed by the e2egl machine feature: render skins larger than 1920x1080 (WQHD/4K) in gFBDC and scale them down, yes or no]),
	[[withegl=$withval]],
	[[withegl=no]]
)
if test x"$withegl" != xno ; then
	AC_DEFINE(HAVE_FBWQHD, 1,[Define to enable scaled WQHD/4K skins in gFBDC])
fi

AC_ARG_WITH(7segment,
	AC_HELP_STRING([--with-7segment], [use 7 segment lcd, yes or no]),
	[[TEXTSKIN="7segment"]],
	[[TEXTSKIN="default"]]
)
AC_SUBST(TEXTSKIN)
if test x"$with7segment" != xno ; then
	AC_DEFINE(HAVE_7SEGMENT, 1,[Define when using an ascii based lcd device])
fi
AM_CONDITIONAL(HAVE_7SEGMENT, test x"$with7segment" != xno)

if test `echo "$BOXTYPE" | cut -b 1-7` == "mbmicro"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_NO_FILL_ACCELERATION, 1,[define when the framebuffer acceleration does not have fill support])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test `echo "$BOXTYPE" | cut -b 1-2` == "vu"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_NO_FILL_ACCELERATION, 1,[define when the framebuffer acceleration does not have fill support])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
fi

if test "$BOXTYPE" == "vuultimo4k" -o "$BOXTYPE" == "vuduo4kse"; then
	AC_DEFINE(PASSTHROUGH_FIX, 1 ,[define when passthrough is not entirely supported by drivers (usually Vu+)])
fi

# VFD Symbols Poll Time
if test "$MACHINEBUILD" == "dm7020hd" -o "$MACHINEBUILD" == "dm7020hdv2"; then
	AC_DEFINE(VFDSymbolsPoll, 1,[define VFD Symbols Poll])
else
	AC_DEFINE(VFDSymbolsPoll, 0,[define VFD Symbols Poll])
fi

AC_ARG_WITH(libsdl,
	AS_HELP_STRING([--with-libsdl],[use libsdl, yes or no]),
	[with_libsdl=$withval],[with_libsdl=no])
if test "$with_libsdl" = "yes"; then
	PKG_CHECK_MODULES(LIBSDL, sdl)
fi
AM_CONDITIONAL(HAVE_LIBSDL, test "$with_libsdl" = "yes")

AC_ARG_WITH(libxine,
	AS_HELP_STRING([--with-libxine],[use libxine, yes or no]),
	[with_libxine=$withval],[with_libxine=no])
if test "$with_libxine" = "yes"; then
	PKG_CHECK_MODULES(LIBXINE, libxine)
	AC_DEFINE([WITH_XINE],[1],[Define to 1 if you have libxine])
fi
AM_CONDITIONAL(HAVE_LIBXINE, test "$with_libxine" = "yes")

AC_ARG_WITH(gles,
	AS_HELP_STRING([--with-gles],[enable OpenGL ES 2.0 hardware acceleration, yes or no]),
	[with_gles=$withval],[with_gles=no])
if test "$with_gles" = "yes"; then
	PKG_CHECK_MODULES(GLES, egl glesv2)
	AC_DEFINE([HAVE_GLES],[1],[Define to 1 if you have GLES support])
	BASE_LIBS="$BASE_LIBS $GLES_LIBS"
fi
AM_CONDITIONAL(HAVE_GLES, test "$with_gles" = "yes")

AC_ARG_WITH(debug,
	AS_HELP_STRING([--without-debug],[disable debugging code]),
	[with_debug="$withval"],[with_debug="yes"])
if test "$with_debug" = "yes"; then
	AC_DEFINE([DEBUG],[1],[Define to 1 to enable debugging code])
fi

AC_ARG_WITH(memcheck,
	AS_HELP_STRING([--with-memcheck],[enable memory leak checks]),
	[with_memcheck="$withval"],[with_memcheck="no"])
if test "$with_memcheck" = "yes"; then
	AC_DEFINE([MEMLEAK_CHECK],[1],[Define to 1 to enable memory leak checks])
fi

AC_ARG_WITH(po,
	AS_HELP_STRING([--with-po],[enable updating of po files]),
	[with_po="$withval"],[with_po="no"])
if test "$with_po" = "yes"; then
	AC_PATH_PROG(MSGINIT, msginit)
	AC_PATH_PROG(MSGMERGE, msgmerge)
	AC_PATH_PROG(MSGUNIQ, msguniq)
	AC_PATH_PROG(MSGATTRIB, msgattrib)
	AC_PATH_PROG(XGETTEXT, xgettext)
	if test -z "$MSGINIT" -o -z "$MSGMERGE" -o -z "$MSGUNIQ" -o -z "$MSGATTRIB" -o -z "$XGETTEXT"; then
		AC_MSG_ERROR([Could not find required gettext tools])
	fi
fi
AM_CONDITIONAL(UPDATE_PO, test "$with_po" = "yes")

AC_ARG_WITH(alsa,
	AC_HELP_STRING([--with-alsa], [Enable ALSA support]),
	[[with_alse=$withval]],
	[[with_alse=no]]
)
if test x"$with_alsa" == xyes ; then
	AC_DEFINE(HAVE_ALSA, 1,[Enables ALSA support])
	PKG_CHECK_MODULES(ALSA, alsa)
fi

AC_ARG_WITH(alsacard,
	AC_HELP_STRING([--with-alsacard=card], [use 'card' for alsa card device, e.g. hw:0]),
	[[with_alsacard=$withval]],
	[[with_alsacard=no]]
)
if test x"$with_alsacard" != xno ; then
	AC_DEFINE_UNQUOTED(ALSA_CARD, "$withval",[Defines which alsa card to use])
fi

AC_ARG_WITH(alsamixer,
	AC_HELP_STRING([--with-alsamixer=mixername], [use alsa 'mixername' for volume control, e.g. Master]),
	[[with_alsamixer=$withval]],
	[[with_alsamixer=no]]
)
if test x"$with_alsamixer" != xno ; then
	AC_DEFINE_UNQUOTED(ALSA_VOLUME_MIXER, "$withval",[Defines which alsa mixer to use for volume control])
fi

AC_ARG_WITH(fbdev,
	AC_HELP_STRING([--with-fbdev=devicename], [use devicename for framebuffer device, e.g. /dev/fb0 ]),
	[[with_fbdev=$withval]],
	[[with_fbdev=no]]
)
if test x"$with_fbdev" != xno ; then
	AC_DEFINE_UNQUOTED(FB_DEV, "$withval", [Defines which device to use for main framebuffer (e.g. /dev/fb0)])
fi

AC_ARG_WITH(lcddev,
	AC_HELP_STRING([--with-lcddev=devicename], [use devicename for lcd framebuffer device, e.g. /dev/fb1 ]),
	[[with_lcddev=$withval]],
	[[with_lcddev=no]]
)
if test x"$with_lcddev" != xno ; then
	AC_DEFINE_UNQUOTED(LCD_DEV, "$withval", [Defines which device to use for lcd (e.g. /dev/fb1)])
fi

AC_ARG_WITH(amlogic,
	AS_HELP_STRING([--with-amlogic], [use amlogic MPEG decoder]),
	[[with_amlogic=$withval]],
	[[with_amlogic=no]]
)

FFMPEG_CFLAGS=" "

AC_ARG_WITH([egl],
  AS_HELP_STRING([--with-egl], [enable EGL/GLES2/GLES3 backend]),
  [],
  [with_egl=no])

have_egl=no
have_gles2=no
have_gles3=no
have_nxpl=no
have_vupl=no
have_v3dplatform=no
use_vuplus_egl=no
use_vuplus_mips_egl=no
use_nxpl_egl=no
use_v3dplatform_egl=no
use_hisilicon_egl=no
use_dreambcm_egl=no
NXPL_CFLAGS=""
NXPL_LIBS=""
VUPL_CFLAGS=""
VUPL_LIBS=""
V3DPLATFORM_CFLAGS=""
V3DPLATFORM_LIBS=""

is_vuplus_egl_box=no
case "$BOXTYPE" in
  vu7376duo|vu7376|vuuno4k|vuuno4kse|vuzero4k)
    is_vuplus_egl_box=yes
    ;;
esac

is_vuplus_mips_egl_box=no
case "$BOXTYPE" in
  vuduo2|vusolo2|vusolose)
    is_vuplus_mips_egl_box=yes
    ;;
esac

is_nxpl_egl_box=no
case "$BOXTYPE" in
  et10000|et1x000|triplex|hd2400|8100s|gb7252|gb72604|dags72604|hd51|vs1500|h7|h17|sf4008)
    is_nxpl_egl_box=yes
    ;;
esac
# Only formuler1 of fm7356, not formuler1tc.
if test "$MACHINEBUILD" == "formuler1"; then
  is_nxpl_egl_box=yes
fi

is_v3dplatform_egl_box=no
case "$BOXTYPE" in
  ed72604|xc7346)
    is_v3dplatform_egl_box=yes
    ;;
esac

is_dreambcm_egl_box=no
case "$BOXTYPE" in
  dm520|dm525|dm7435|dm7252s|dm900|dm920|dm7080|dm820)
    is_dreambcm_egl_box=yes
    ;;
esac

is_hisilicon_egl_box=no
case "$BOXTYPE" in
  u5|u5pvr|u51|u52|u54|u55|u56|u57|u571|u41|u42|u43|u45|u53|u532|u533|ocmv200|sx988|ip8|ustym4kpro|ustym4kottpremium|ustym4ks2ottx|gbmv200|beyonwizv2|viper4k|dagsmv200|og2ott4k|og2s4k|sfx6008|sx88v2|abmv200|multibox|multiboxpro|multiboxse|h8se|h9|h9combo|h9combose|h9se|h10|h11|i55plus|i55se|hd60|hd61|hd66se)
    is_hisilicon_egl_box=yes
    ;;
esac

AS_IF([test "x$with_egl" != "xno"], [
  PKG_CHECK_MODULES([EGL], [egl], [have_egl=yes], [
    EGL_CFLAGS=""
    EGL_LIBS="-lEGL"
    have_egl=yes
  ])
  PKG_CHECK_MODULES([GLES2], [glesv2], [have_gles2=yes], [
    GLES2_CFLAGS=""
    GLES2_LIBS="-lGLESv2"
    have_gles2=yes
  ])
  AS_IF([test "x$is_vuplus_egl_box" = "xyes" -o "x$is_nxpl_egl_box" = "xyes"], [
    PKG_CHECK_MODULES([NXPL], [nxpl], [have_nxpl=yes], [have_nxpl=no])
  ])
  AS_IF([test "x$is_vuplus_mips_egl_box" = "xyes"], [
    PKG_CHECK_MODULES([VUPL], [libvupl nxpl], [have_vupl=yes], [
      AC_CHECK_HEADERS([eglvuplus.h], [have_vupl_header=yes], [have_vupl_header=no])
      saved_LIBS="$LIBS"
      LIBS="$LIBS -lnxpl -ldvb_client -ldvb_base"
      AC_CHECK_LIB([vupl], [VUGLES_InitPlatformAndDefaultDisplay], [have_vupl_lib=yes], [have_vupl_lib=no])
      LIBS="$saved_LIBS"
      AS_IF([test "x$have_vupl_header" = "xyes" -a "x$have_vupl_lib" = "xyes"], [
        VUPL_CFLAGS=""
        VUPL_LIBS="-lvupl -lnxpl -ldvb_client -ldvb_base"
        have_vupl=yes
      ], [
        have_vupl=no
      ])
    ])
  ])
  AS_IF([test "x$is_v3dplatform_egl_box" = "xyes"], [
    PKG_CHECK_MODULES([V3DPLATFORM], [v3dplatform], [have_v3dplatform=yes], [have_v3dplatform=no])
  ])
])

AS_IF([test "x$have_gles2" = "xyes"], [
  saved_CPPFLAGS="$CPPFLAGS"
  saved_LIBS="$LIBS"
  CPPFLAGS="$CPPFLAGS $EGL_CFLAGS $GLES2_CFLAGS"
  LIBS="$LIBS $GLES2_LIBS $EGL_LIBS $NXPL_LIBS $VUPL_LIBS $V3DPLATFORM_LIBS"
  AC_CHECK_HEADERS([GLES3/gl3.h], [have_gles3_header=yes], [have_gles3_header=no])
  # Some SDKs ship GLES3/gl3.h but a GLESv2-only library, verify the GLES3 entry points link.
  AS_IF([test "x$have_gles3_header" = "xyes"], [
    AC_MSG_CHECKING([whether libGLESv2 provides GLES3 entry points])
    AC_LINK_IFELSE([AC_LANG_PROGRAM(
      [[#include <GLES3/gl3.h>]],
      [[GLuint vao; glGenVertexArrays(1, &vao); glBindVertexArray(vao);]])],
      [have_gles3=yes], [have_gles3=no])
    AC_MSG_RESULT([$have_gles3])
  ], [have_gles3=no])
  AC_CHECK_HEADERS([EGL/fbdev_window.h])
  AC_CHECK_TYPES([fbdev_window],
    [AC_DEFINE([HAVE_FBDEV_WINDOW_TYPE], [1], [Define if EGL exposes the fbdev_window type])],
    [],
    [[#include <EGL/egl.h>]])
  CPPFLAGS="$saved_CPPFLAGS"
  LIBS="$saved_LIBS"
])

AS_IF([test "x$with_egl" = "xyes"], [
  AS_IF([test "x$have_egl" != "xyes" -o "x$have_gles2" != "xyes"], [
    AC_MSG_ERROR([--with-egl was given, but egl and/or glesv2 were not found])
  ])
  AS_IF([test "x$is_vuplus_egl_box" = "xyes" -a "x$have_nxpl" != "xyes"], [
    AC_MSG_ERROR([--with-egl on Vu+ requires nxpl])
  ])
  AS_IF([test "x$is_vuplus_mips_egl_box" = "xyes" -a "x$have_vupl" != "xyes"], [
    AC_MSG_ERROR([--with-egl on Vu+ MIPS requires libvupl])
  ])
  AS_IF([test "x$is_nxpl_egl_box" = "xyes" -a "x$have_nxpl" != "xyes"], [
    AC_MSG_ERROR([--with-egl on Broadcom/NXPL requires nxpl])
  ])
  AS_IF([test "x$is_v3dplatform_egl_box" = "xyes" -a "x$have_v3dplatform" != "xyes"], [
    AC_MSG_ERROR([--with-egl on Broadcom/V3D platform requires v3dplatform])
  ])
  AS_IF([test "x$is_hisilicon_egl_box" = "xyes"], [
    AC_DEFINE([HAVE_HISILICON_EGL], [1], [Define if HiSilicon Mali native EGL support is available])
    use_hisilicon_egl=yes
  ])
  AS_IF([test "x$is_dreambcm_egl_box" = "xyes"], [
    AC_DEFINE([HAVE_DREAMBCM_EGL], [1], [Define if Dreambox Broadcom native EGL support is available])
    EGL_CFLAGS="$EGL_CFLAGS -DBROADCOM_PLATFORM"
    GLES2_CFLAGS="$GLES2_CFLAGS -DBROADCOM_PLATFORM"
    use_dreambcm_egl=yes
  ])
])

use_egl=no
AS_IF([test "x$have_egl" = "xyes" -a "x$have_gles2" = "xyes"], [
  AC_DEFINE([HAVE_EGL], [1], [Define if EGL/GLES2 support is available])
  use_egl=yes
  AS_IF([test "x$is_vuplus_egl_box" = "xyes" -a "x$have_nxpl" = "xyes"], [
    AC_DEFINE([HAVE_VUPLUS_EGL], [1], [Define if Vu+ NXPL native EGL support is available])
    use_vuplus_egl=yes
  ])
  AS_IF([test "x$is_vuplus_mips_egl_box" = "xyes" -a "x$have_vupl" = "xyes"], [
    AC_DEFINE([HAVE_VUPLUS_MIPSEL_EGL], [1], [Define if legacy Vu+ MIPS libvupl native EGL support is available])
    use_vuplus_mips_egl=yes
  ])
  AS_IF([test "x$is_nxpl_egl_box" = "xyes" -a "x$have_nxpl" = "xyes"], [
    AC_DEFINE([HAVE_NXPL_EGL], [1], [Define if Broadcom NXPL native EGL support is available])
    use_nxpl_egl=yes
  ])
  AS_IF([test "x$is_v3dplatform_egl_box" = "xyes" -a "x$have_v3dplatform" = "xyes"], [
    AC_DEFINE([HAVE_V3DPLATFORM_EGL], [1], [Define if Broadcom V3D platform native EGL support is available])
    use_v3dplatform_egl=yes
  ])
])

AS_IF([test "x$have_egl" = "xyes" -a "x$have_gles3" = "xyes"], [
  AC_DEFINE([HAVE_GLES3], [1], [Define if GLES3 support is available])
])

AM_CONDITIONAL([HAVE_EGL], [test "x$use_egl" = "xyes"])
AM_CONDITIONAL([HAVE_VUPLUS_EGL], [test "x$use_vuplus_egl" = "xyes"])
AM_CONDITIONAL([HAVE_VUPLUS_MIPSEL_EGL], [test "x$use_vuplus_mips_egl" = "xyes"])
AM_CONDITIONAL([HAVE_NXPL_EGL], [test "x$use_nxpl_egl" = "xyes"])
AM_CONDITIONAL([HAVE_V3DPLATFORM_EGL], [test "x$use_v3dplatform_egl" = "xyes"])
AM_CONDITIONAL([HAVE_HISILICON_EGL], [test "x$use_hisilicon_egl" = "xyes"])
AM_CONDITIONAL([HAVE_DREAMBCM_EGL], [test "x$use_dreambcm_egl" = "xyes"])

AC_ARG_ENABLE([gles-testlab],
  AS_HELP_STRING([--enable-gles-testlab], [build the optional GLES visual/performance test plugin (default: no)]),
  [enable_gles_testlab="$enableval"], [enable_gles_testlab=no])
AS_CASE([$enable_gles_testlab], [yes|no], [], [AC_MSG_ERROR([--enable-gles-testlab accepts yes or no])])
AS_IF([test "x$enable_gles_testlab" = "xyes"], [
  AS_IF([test "x$use_egl" != "xyes"], [AC_MSG_ERROR([--enable-gles-testlab requires --with-egl])])
  AC_DEFINE([ENABLE_GLES_TESTLAB], [1], [Build the optional GLES renderer test lab])
  AX_SWIG_PYTHON_OPT="$AX_SWIG_PYTHON_OPT -DENABLE_GLES_TESTLAB"
])
AM_CONDITIONAL([ENABLE_GLES_TESTLAB], [test "x$enable_gles_testlab" = "xyes"])

AC_SUBST([EGL_CFLAGS])
AC_SUBST([EGL_LIBS])
AC_SUBST([GLES2_CFLAGS])
AC_SUBST([GLES2_LIBS])
AC_SUBST([NXPL_CFLAGS])
AC_SUBST([NXPL_LIBS])
AC_SUBST([VUPL_CFLAGS])
AC_SUBST([VUPL_LIBS])
AC_SUBST([V3DPLATFORM_CFLAGS])
AC_SUBST([V3DPLATFORM_LIBS])

AM_CONDITIONAL(DREAMNEXTGEN, test "$BOXTYPE" == dms922x)
if test "$BOXTYPE" == "dms922x"; then
	ALSA_CFLAGS="-lasound"
	FFMPEG_CFLAGS=" -lavdevice -lavformat -lavcodec -lswresample -lswscale -lavutil -lm "
	AC_DEFINE(DREAMNEXTGEN, 1, [Dreambox NexT Generation Hardware])
fi

AC_ARG_WITH(fcc,
	AS_HELP_STRING([--with-fcc], [add FCC system plugin]),
	[[with_fcc=$withval]],
	[[with_fcc=no]]
)
AM_CONDITIONAL(HAVE_FCC, test x"$with_fcc" = xyes)
if test x"$with_fcc" = xyes ; then
	AC_DEFINE(HAVE_FCC, 1,[add FCC system plugin])
fi

AC_ARG_WITH(alphablendingacceleration,
	AC_HELP_STRING([--with-alphablendingacceleration=never/always/auto], [alphablending acceleration strategy: never accelerate / always accelerate / automatically decide when to accelerate (default)]),
	[[with_alphablendingacceleration=$withval]],
	[[with_alphablendingacceleration=auto]]
)

if test x"$with_alphablendingacceleration" = xnever ; then
	AC_DEFINE_UNQUOTED(FORCE_NO_BLENDING_ACCELERATION, 1, [Do not attempt to accelerate alphablending blits])
elif test x"$with_alphablendingacceleration" = xalways ; then
	AC_DEFINE_UNQUOTED(FORCE_ALPHABLENDING_ACCELERATION, 1, [Accelerate alphablending blits])
fi

AC_ARG_WITH(accelerationthreshold,
	AC_HELP_STRING([--with-accelerationthreshold=n], [use acceleration threshold of n bytes]),
	[[with_accelerationthreshold=$withval]],
	[[with_accelerationthreshold=48000]]
)

AC_DEFINE_UNQUOTED(GFX_SURFACE_ACCELERATION_THRESHOLD, $with_accelerationthreshold,[Configure threshold for accelerated surfaces (in bytes)])

AC_ARG_WITH(fillaccelerationthreshold,
	AC_HELP_STRING([--with-fillaccelerationthreshold=n], [use fill acceleration threshold of n bytes]),
	[[with_fillaccelerationthreshold=$withval]],
	[[with_fillaccelerationthreshold=80000]]
)

AC_DEFINE_UNQUOTED(GFX_SURFACE_FILL_ACCELERATION_THRESHOLD, $with_fillaccelerationthreshold,[Configure threshold for accelerated fill operations (in bytes)])

AC_ARG_WITH(blitaccelerationthreshold,
	AC_HELP_STRING([--with-blitaccelerationthreshold=n], [use blit acceleration threshold of n bytes]),
	[[with_blitaccelerationthreshold=$withval]],
	[[with_blitaccelerationthreshold=0]]
)

AC_DEFINE_UNQUOTED(GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD, $with_blitaccelerationthreshold,[Configure threshold for accelerated blit operations (in bytes)])

if test "$BOXTYPE" == "dm7080" -o "$BOXTYPE" == "dm820" -o "$BOXTYPE" == "dm900" -o "$BOXTYPE" == "dm920" -o "$BOXTYPE" == "dm520"; then
	default_accelerationaccumulation=yes
else
	default_accelerationaccumulation=no
fi

AC_ARG_WITH(accelerationaccumulation,
	AC_HELP_STRING([--with-accelerationaccumulation], [accumulate blit/fill acceleration operations]),
	[[with_accelerationaccumulation=$withval]],
	[[with_accelerationaccumulation=$default_accelerationaccumulation]]
)

if test x"$with_accelerationaccumulation" = xyes ; then
	AC_DEFINE(SUPPORT_ACCUMULATED_ACCELERATION_OPERATIONS, 1,[Accumulate blit/fill acceleration operations])
fi

AC_ARG_WITH(olde2api,
	AS_HELP_STRING([--with-olde2api],[use olde2api, yes or no]),
	[with_olde2api=$withval],[with_olde2api=no])
if test x"$with_olde2api" != xno ; then
	AC_DEFINE(HAVE_OLDE2_API, 1,[define add old api of enigma2])
fi

AC_CHECK_HEADERS([sys/klog.h])
AC_CHECK_FUNCS([klogctl])

AC_CHECK_HEADERS([shadow.h])
AC_CHECK_LIB([crypt], [crypt], [BASE_LIBS+=" -lcrypt"], [AC_MSG_ERROR([Could not find crypt])])
AC_CHECK_LIB([rt], [clock_gettime], [BASE_LIBS+=" -lrt"], [AC_MSG_ERROR([Could not find rt])])

ENIGMA2_CFLAGS="-frtti -rdynamic -funwind-tables"
AC_SUBST(ENIGMA2_CFLAGS)

AX_CXX_COMPILE_STDCXX([20], [ext], [mandatory])

AX_CHECK_COMPILE_FLAG([-Wattribute-alias], [CXXFLAGS="$CXXFLAGS -Wattribute-alias"])
AX_CHECK_COMPILE_FLAG([-Wattribute-alias=1], [CXXFLAGS="$CXXFLAGS -Wattribute-alias=1"])

CPPFLAGS="$CPPFLAGS $PYTHON_CPPFLAGS"
CFLAGS="$CFLAGS -Wall"
CXXFLAGS="$CXXFLAGS -Wall -Wno-psabi \
	-Wformat=2 -Wformat-overflow=2 -Wformat-nonliteral -Wformat-security \
	-Wimplicit-fallthrough=5 -Wdangling-else -Wno-error=stringop-truncation -Wno-error=maybe-uninitialized -Wno-error=array-bounds= \
	$BASE_CFLAGS $ENIGMA2_CFLAGS $PTHREAD_CFLAGS $OPENMP_CFLAGS $GLES_CFLAGS $EGL_CFLAGS $GLES2_CFLAGS $NXPL_CFLAGS $VUPL_CFLAGS $V3DPLATFORM_CFLAGS $ALSA_CFLAGS $AMCODEC_CFLAGS $FFMPEG_CFLAGS $AMADEC_CFLAGS $DVBCSA_CFLAGS"

AX_SWIG_PYTHON_OPT="$AX_SWIG_PYTHON_OPT -DSWIG_PYTHON_LEGACY_BOOL"

ARFLAGS="cr"
AC_SUBST(ARFLAGS)
AR_FLAGS="cr"
AC_SUBST(AR_FLAGS)

AC_CONFIG_FILES([
Makefile
data/Makefile
data/fonts/Makefile
data/countries/Makefile
data/display/Makefile
data/display/display/Makefile
data/display/display96/Makefile
data/display/display128/Makefile
data/display/display128dm/Makefile
data/display/display220/Makefile
data/display/display240/Makefile
data/display/display390/Makefile
data/display/display400/Makefile
data/display/display480/Makefile
data/display/display720/Makefile
data/display/display800/Makefile
data/display/displaytext/Makefile
data/display/grautec70x0/Makefile
data/display/grautec70x0/fonts/Makefile
data/display/grautec8000/Makefile
data/display/grautec8000/fonts/Makefile
data/extensions/Makefile
data/keymaps/Makefile
data/hw_info/Makefile
data/icons/Makefile
data/rc_models/Makefile
data/skin_default/Makefile
data/skin_default/buttons/Makefile
data/skin_default/epg/Makefile
data/skin_default/icons/Makefile
data/skin_default/infobar/Makefile
data/skin_default/LCDIcons/Makefile
data/skin_default/menu/Makefile
data/skin_default/piconbg/Makefile
data/skin_default/screens/Makefile
data/skin_default/skin_default/Makefile
data/skin_default/spinner/Makefile
data/VirtualKeyBoard_Icons/Makefile
data/VirtualKeyBoard_Icons/buttonsHD/Makefile
data/VirtualKeyBoard_Icons/buttonsFHD/Makefile
include/Makefile
lib/Makefile
lib/base/eenv.cpp
lib/python/Makefile
lib/python/Components/Makefile
lib/python/Components/Addons/Makefile
lib/python/Components/Converter/Makefile
lib/python/Components/Renderer/Makefile
lib/python/Components/Sources/Makefile
lib/python/Screens/Makefile
lib/python/Plugins/Makefile
lib/python/Plugins/SystemPlugins/CableScan/Makefile
lib/python/Plugins/SystemPlugins/FastScan/Makefile
lib/python/Plugins/SystemPlugins/OSDPositionSetup/Makefile
lib/python/Plugins/SystemPlugins/OSD3DSetup/Makefile
lib/python/Plugins/SystemPlugins/VideoClippingSetup/Makefile
lib/python/Plugins/Extensions/CutListEditor/Makefile
lib/python/Plugins/Extensions/CutListEditor/meta/Makefile
lib/python/Plugins/Extensions/DVDBurn/Makefile
lib/python/Plugins/Extensions/DVDBurn/meta/Makefile
lib/python/Plugins/Extensions/DVDPlayer/Makefile
lib/python/Plugins/Extensions/DVDPlayer/meta/Makefile
lib/python/Plugins/Extensions/FileCommander/Makefile
lib/python/Plugins/Extensions/GraphMultiEPG/Makefile
lib/python/Plugins/Extensions/GraphMultiEPG/meta/Makefile
lib/python/Plugins/Extensions/Makefile
lib/python/Plugins/Extensions/MediaPlayer/Makefile
lib/python/Plugins/Extensions/MediaScanner/Makefile
lib/python/Plugins/Extensions/MediaScanner/meta/Makefile
lib/python/Plugins/Extensions/PicturePlayer/Makefile
lib/python/Plugins/Extensions/GlesTestLab/Makefile
lib/python/Plugins/Extensions/SocketMMI/Makefile
lib/python/Plugins/Extensions/SocketMMI/meta/Makefile
lib/python/Plugins/Extensions/SocketMMI/src/Makefile
lib/python/Plugins/Extensions/QuadPip/Makefile
lib/python/Plugins/Extensions/StreamlinkWrapper/Makefile
lib/python/Plugins/Extensions/YTDLWrapper/Makefile
lib/python/Plugins/Extensions/YTDLPWrapper/Makefile
lib/python/Plugins/PLi/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/meta/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/meta/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/meta/Makefile
lib/python/Plugins/SystemPlugins/FastChannelChange/Makefile
lib/python/Plugins/SystemPlugins/FSBLUpdater/Makefile
lib/python/Plugins/SystemPlugins/Hotplug/Makefile
lib/python/Plugins/SystemPlugins/Makefile
lib/python/Plugins/SystemPlugins/AmlFRQ/Makefile
lib/python/Plugins/SystemPlugins/TempFanControl/Makefile
lib/python/Plugins/SystemPlugins/TempFanControl/meta/Makefile
lib/python/Plugins/SystemPlugins/LCNScanner/Makefile
lib/python/Plugins/SystemPlugins/PositionerSetup/Makefile
lib/python/Plugins/SystemPlugins/SatelliteEquipmentControl/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/meta/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/meta/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancement/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancementAML/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/meta/Makefile
lib/python/Tools/Makefile
po/Makefile
main/Makefile
tools/Makefile
tools/enigma2.sh
hotplug/Makefile
enigma2.pc
])
AC_OUTPUT
