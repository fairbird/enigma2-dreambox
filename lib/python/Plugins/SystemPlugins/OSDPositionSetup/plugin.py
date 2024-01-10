# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.config import config, ConfigSelectionNumber, ConfigSubsection, ConfigInteger
from Components.SystemInfo import BoxInfo

config.plugins.OSDPositionSetup = ConfigSubsection()
if BoxInfo.getItem("AmlogicFamily"):
	from Plugins.SystemPlugins.Videomode.VideoHardware import video_hw
	limits = [int(x) for x in video_hw.getWindowsAxis().split()]
	config.plugins.OSDPositionSetup.dst_left = ConfigSelectionNumber(default=limits[0], stepwidth=1, min=limits[0] - 255, max=limits[0] + 255, wraparound=False)
	config.plugins.OSDPositionSetup.dst_width = ConfigSelectionNumber(default=limits[2], stepwidth=1, min=limits[2] - 255, max=limits[2] + 255, wraparound=False)
	config.plugins.OSDPositionSetup.dst_top = ConfigSelectionNumber(default=limits[1], stepwidth=1, min=limits[1] - 255, max=limits[1] + 255, wraparound=False)
	config.plugins.OSDPositionSetup.dst_height = ConfigSelectionNumber(default=limits[3], stepwidth=1, min=limits[3] - 255, max=limits[3] + 255, wraparound=False)
else:
	config.plugins.OSDPositionSetup.dst_left = ConfigSelectionNumber(default=0, stepwidth=1, min=0, max=720, wraparound=False)
	config.plugins.OSDPositionSetup.dst_width = ConfigSelectionNumber(default=720, stepwidth=1, min=0, max=720, wraparound=False)
	config.plugins.OSDPositionSetup.dst_top = ConfigSelectionNumber(default=0, stepwidth=1, min=0, max=576, wraparound=False)
	config.plugins.OSDPositionSetup.dst_height = ConfigSelectionNumber(default=576, stepwidth=1, min=0, max=576, wraparound=False)


def setPosition(dst_left, dst_width, dst_top, dst_height):
	if dst_left + dst_width > 720:
		dst_width = 720 - dst_left
	if dst_top + dst_height > 576:
		dst_height = 576 - dst_top
	try:
		print("[OSDPositionSetup] Write to /proc/stb/fb/dst_left")
		open("/proc/stb/fb/dst_left", "w").write('%08x' % dst_left)
		print("[OSDPositionSetup] Write to /proc/stb/fb/dst_width")
		open("/proc/stb/fb/dst_width", "w").write('%08x' % dst_width)
		print("[OSDPositionSetup] Write to /proc/stb/fb/dst_top")
		open("/proc/stb/fb/dst_top", "w").write('%08x' % dst_top)
		print("[OSDPositionSetup] Write to /proc/stb/fb/dst_height")
		open("/proc/stb/fb/dst_height", "w").write('%08x' % dst_height)
	except:
		return


def setConfiguredPosition():
	if BoxInfo.getItem("AmlogicFamily"):
		try:
			print("[OSDPositionSetup] Write to /sys/class/graphics/fb0/window_axis")
			open("/sys/class/graphics/fb0/window_axis", "w").write('%s %s %s %s' % (config.plugins.OSDPositionSetup.dst_left.value, config.plugins.OSDPositionSetup.dst_top.value, config.plugins.OSDPositionSetup.dst_width.value, config.plugins.OSDPositionSetup.dst_height.value))
			print("[OSDPositionSetup] Write to /sys/class/graphics/fb0/free_scale")
			open("/sys/class/graphics/fb0/free_scale", "w").write("0x10001")
		except:
			print("[OSDPositionSetup] Write window_axis or free_scale failed!")
	else:
		setPosition(int(config.plugins.OSDPositionSetup.dst_left.value), int(config.plugins.OSDPositionSetup.dst_width.value), int(config.plugins.OSDPositionSetup.dst_top.value), int(config.plugins.OSDPositionSetup.dst_height.value))

def main(session, **kwargs):
	from Plugins.SystemPlugins.OSDPositionSetup.overscanwizard import OverscanWizard
	session.open(OverscanWizard, timeOut=False)


def startSetup(menuid):
	return menuid == "video" and [(_("Overscan wizard"), main, "sd_position_setup", 0)] or []


def startup(reason, **kwargs):
	setConfiguredPosition()


def Plugins(**kwargs):
	from Plugins.Plugin import PluginDescriptor
	return [PluginDescriptor(name=_("Overscan wizard"), description="", where=PluginDescriptor.WHERE_SESSIONSTART, fnc=startup),
		PluginDescriptor(name=_("Overscan wizard"), description=_("Wizard to arrange the overscan"), where=PluginDescriptor.WHERE_MENU, fnc=startSetup)]
