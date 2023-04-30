installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = SoftwareManager PositionerSetup Satfinder \
	SatelliteEquipmentControl Videomode VideoTune Hotplug \
	DefaultServicesScanner DiseqcTester CommonInterfaceAssignment \
	CableScan FastScan OSDPositionSetup OSD3DSetup HdmiCEC VideoClippingSetup \
	WirelessLan NetworkWizard FastChannelChange

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMNEXTGEN
SUBDIRS += AmlFRQ VideoEnhancementAML
else
SUBDIRS += VideoEnhancement
endif

install_PYTHON =	\
	__init__.py
