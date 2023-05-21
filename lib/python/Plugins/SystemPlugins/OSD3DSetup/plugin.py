# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.ChannelSelection import FLAG_IS_DEDICATED_3D
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import SystemInfo
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigSlider
from enigma import iPlayableService, iServiceInformation, eServiceCenter, eServiceReference, eDVBDB

modelist = {"off": _("Off"), "auto": _("Auto"), "sidebyside": _("Side by side"), "topandbottom": _("Top and bottom")}

config.plugins.OSD3DSetup = ConfigSubsection()
config.plugins.OSD3DSetup.mode = ConfigSelection(choices=modelist, default="auto")
config.plugins.OSD3DSetup.znorm = ConfigInteger(default=0)


class OSD3DSetupScreen(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.setTitle(_("OSD 3D setup"))

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"menu": self.closeRecursive,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session)

		mode = config.plugins.OSD3DSetup.mode.value
		znorm = config.plugins.OSD3DSetup.znorm.value

		self.mode = ConfigSelection(choices=modelist, default=mode)
		self.znorm = ConfigSlider(default=znorm + 50, increment=1, limits=(0, 100))
		self.list.append((_("3d mode"), self.mode))
		self.list.append((_("Depth"), self.znorm))
		self["config"].list = self.list

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewSettings()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewSettings()

	def setPreviewSettings(self):
		applySettings(self.mode.value, int(self.znorm.value) - 50)

	def keyGo(self):
		config.plugins.OSD3DSetup.mode.value = self.mode.value
		config.plugins.OSD3DSetup.znorm.value = int(self.znorm.value) - 50
		config.plugins.OSD3DSetup.save()
		self.close()

	def keyCancel(self):
		applySettings()
		self.close()


previous = None
isDedicated3D = False


def applySettings(mode=config.plugins.OSD3DSetup.mode.value, znorm=int(config.plugins.OSD3DSetup.znorm.value)):
	global previous, isDedicated3D
	mode = isDedicated3D and mode == "auto" and "sidebyside" or mode
	mode == "3dmode" in SystemInfo["3DMode"] and mode or mode == 'sidebyside' and 'sbs' or mode == 'topandbottom' and 'tab' or 'off'
	if previous != (mode, znorm):
		try:
			open(SystemInfo["3DMode"], "w").write(mode)
			open(SystemInfo["3DZNorm"], "w").write('%d' % znorm)
			previous = (mode, znorm)
		except:
			return


class auto3D(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStart: self.__evStart
			})

	def checkIfDedicated3D(self):
			service = self.session.nav.getCurrentlyPlayingServiceReference()
			servicepath = service and service.getPath()
			if servicepath and servicepath.startswith("/"):
				if service.toString().startswith("1:"):
					info = eServiceCenter.getInstance().info(service)
					service = info and info.getInfoString(service, iServiceInformation.sServiceref)
					return service and eDVBDB.getInstance().getFlag(eServiceReference(service)) & FLAG_IS_DEDICATED_3D == FLAG_IS_DEDICATED_3D and "sidebyside"
				else:
					return ".3d." in servicepath.lower() and "sidebyside" or ".tab." in servicepath.lower() and "topandbottom"
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			return info and info.getInfo(iServiceInformation.sIsDedicated3D) == 1 and "sidebyside"

	def __evStart(self):
		if config.plugins.OSD3DSetup.mode.value == "auto":
			global isDedicated3D
			isDedicated3D = self.checkIfDedicated3D()
			if isDedicated3D:
				applySettings(isDedicated3D)
			else:
				applySettings()


def main(session, **kwargs):
	session.open(OSD3DSetupScreen)


def startSetup(menuid):
	# show only in the menu when set at expert level
	if menuid == "video" and config.usage.setup_level.index == 2:
		return [(_("OSD 3D setup"), main, "auto_3d_setup", 0)]
	return []


def autostart(reason, **kwargs):
	"session" in kwargs and kwargs["session"].open(auto3D)


def Plugins(**kwargs):
	if SystemInfo["3DMode"]:
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart),
			PluginDescriptor(name=_("OSD 3D setup"), description=_("Adjust 3D settings"), where=PluginDescriptor.WHERE_MENU, fnc=startSetup)]
	return []
