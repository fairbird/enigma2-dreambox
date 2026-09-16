installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = SoftwareManager PositionerSetup Satfinder \
	SatelliteEquipmentControl Videomode VideoTune Hotplug \
	DefaultServicesScanner DiseqcTester CommonInterfaceAssignment \
	CableScan FastScan OSDPositionSetup OSD3DSetup VideoClippingSetup \
	FastChannelChange LCNScanner

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMNEXTGEN
SUBDIRS += AmlFRQ VideoEnhancementAML
else
SUBDIRS += VideoEnhancement
endif

if DM900
SUBDIRS += FSBLUpdater
endif

if DM920
SUBDIRS += FSBLUpdater
endif


if HAVE_LIBVUGLES2
SUBDIRS += AnimationSetup
endif

if HAVE_OSDANIMATION
SUBDIRS += AnimationSetup
endif

install_PYTHON =	\
	__init__.py
