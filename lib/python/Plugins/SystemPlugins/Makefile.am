installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = SoftwareManager PositionerSetup Satfinder \
	SatelliteEquipmentControl Videomode VideoTune Hotplug \
	DefaultServicesScanner DiseqcTester CommonInterfaceAssignment \
	CableScan FastScan OSDPositionSetup OSD3DSetup HdmiCEC VideoClippingSetup \
	WirelessLan NetworkWizard FastChannelChange LCNScanner

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

install_PYTHON =	\
	__init__.py
