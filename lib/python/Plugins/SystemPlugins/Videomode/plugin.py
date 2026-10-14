# -*- coding: utf-8 -*-
from enigma import eAVControl, iPlayableService, iServiceInformation
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.SystemInfo import BoxInfo
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigBoolean, ConfigNothing
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.ServiceEventTracker import ServiceEventTracker
from Tools.Directories import fileReadLine, fileWriteLine, isPluginInstalled
from Plugins.SystemPlugins.Videomode.VideoHardware import video_hw

config.misc.videowizardenabled = ConfigBoolean(default=True)


videoModeHDRController = None


class VideoModeHDRController(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.evStart,
			iPlayableService.evVideoGammaChanged: self.gammaChanged
		})

	def evStart(self):
		self.gammaChanged(reset=True)

	def gammaChanged(self, reset=False):
		if not BoxInfo.getItem("havehdmihdrtype") or not config.av.hdmihdrtype_switch.value or config.av.hdmihdrtype.value != "auto":
			return

		gamma = -1
		if not reset:
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			if info:
				gamma = info.getInfo(iServiceInformation.sGamma)

		hdrType = {2: "hdr10", 3: "hlg"}.get(gamma, "auto")
		if hdrType in config.av.hdmihdrtype.choices:
			self.writeVideoSetting("/proc/stb/video/hdmi_hdrtype", hdrType)
			if BoxInfo.getItem("havecolorimetry") and config.av.hdmicolorimetry.value == "auto":
				self.writeVideoSetting("/proc/stb/video/hdmi_colorimetry", "auto" if hdrType == "auto" else config.av.hdmicolorimetry_hdr.value)

	def writeVideoSetting(self, path, value):
		if fileReadLine(path, default="", source="VideoMode") != value:
			fileWriteLine(path, value, source="VideoMode")
			print("[VideoMode] Set '%s' to '%s'." % (path, value))


def videoModeSessionStart(session, **kwargs):
	global videoModeHDRController
	if videoModeHDRController is None and BoxInfo.getItem("havehdmihdrtype"):
		videoModeHDRController = VideoModeHDRController(session)


class VideoSetup(ConfigListScreen, Screen):

	def __init__(self, session, hw):
		Screen.__init__(self, session)
		# for the skin: first try VideoSetup, then Setup, this allows individual skinning
		self.skinName = ["VideoSetup", "Setup"]
		self.setTitle(_("Video Settings"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self["footnote"] = Label("")
		self.hw = hw
		self.onChangedEntry = []

		# handle hotplug by re-creating setup
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session)

		from Components.ActionMap import ActionMap
		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"menu": self.closeRecursive,
				"left": self.keyLeft,
				"right": self.keyRight
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["description"] = Label("")
		self["footnote"] = Label("")
		self["footnote"].hide()
		self["config"].onSelectionChanged.append(self.selectionChanged)

		self.createSetup()
		self.selectionChanged()
		self.grabLastGoodMode()

	def startHotplug(self):
		self.hw.on_hotplug.append(self.createSetup)

	def stopHotplug(self):
		self.hw.on_hotplug.remove(self.createSetup)

	def selectionChanged(self):
		current = self["config"].getCurrent()
		description = current[2] if current and len(current) > 2 else ""
		self["description"].setText(description)
		self["footnote"].setText(description)

	def createSetup(self):
		level = config.usage.setup_level.index

		self.list = []
		self.list.append((_("Video output"), config.av.videoport, _("Configures which video output connector will be used.")))

		# if we have modes for this port:
		if config.av.videoport.value in config.av.videomode:
			# add mode- and rate-selection:
			self.list.append((pgettext("Video output mode", "Mode"), config.av.videomode[config.av.videoport.value], _("Configure the video output mode (or resolution).")))
			if config.av.videomode[config.av.videoport.value].value == 'PC':
				self.list.append((_("Resolution"), config.av.videorate[config.av.videomode[config.av.videoport.value].value], _("Configure the screen resolution in PC output mode.")))
			else:
				self.list.append((_("Refresh rate"), config.av.videorate[config.av.videomode[config.av.videoport.value].value], _("Configure the refresh rate of the screen.")))

		self.list.append((_("Aspect ratio"), config.av.aspect, _("Configure the aspect ratio of the screen.")))
		self.list.append((_("Display 4:3 content as"), config.av.policy_43, _("When the content has an aspect ratio of 4:3, choose whether to scale/stretch the picture.")))
		try:
			if hasattr(config.av, 'policy_169'):
				self.list.append((_("Display 16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture.")))
		except:
			pass

		self.list.append((_("Force frame"), config.av.force, _("Allow forcing the frames per second.")))

		if config.av.videoport.value == "HDMI":
			if not eAVControl.getInstance().hasVideoAxis():
				self.list.append((_("Aspect switch"), config.av.aspectswitch.enabled, _("This option allows you to set offset values for different Letterbox resolutions.")))
				if config.av.aspectswitch.enabled.value:
					for aspect in range(5):
						self.list.append((f" -> {video_hw.ASPECT_SWITCH_MSG[aspect]}", config.av.aspectswitch.offsets[str(aspect)]))

			self.list.append((_("Allow unsupported modes"), config.av.edid_override, _("When selected this allows video modes to be selected even if they are not reported as supported.")))

		if config.av.videoport.value == "Scart":
			self.list.append((_("Scart Color format"), config.av.colorformat, _("Configure which color format should be used on the SCART output.")))
			if level >= 1:
				self.list.append((_("WSS on 4:3"), config.av.wss, _("When enabled, content with an aspect ratio of 4:3 will be stretched to fit the screen.")))
				if BoxInfo.getItem("ScartSwitch"):
					self.list.append((_("Auto scart switching"), config.av.vcrswitch, _("When enabled, your receiver will detect activity on the VCR SCART input.")))

		if not isinstance(config.av.scaler_sharpness, ConfigNothing) and not isPluginInstalled("VideoEnhancement"):
			self.list.append((_("Scaler sharpness"), config.av.scaler_sharpness, _("Configure the sharpness of the video scaling.")))

		if BoxInfo.getItem("HasBypassEdidChecking"):
			self.list.append((_("Bypass HDMI EDID checking"), config.av.bypass_edid_checking, _("Configure if the HDMI EDID checking should be bypassed as this might solve issue with some TVs.")))
		if BoxInfo.getItem("havecolorspace"):
			self.list.append((_("HDMI Colorspace"), config.av.hdmicolorspace, _("This option allows you to configure the Colorspace from Auto to RGB")))
		if BoxInfo.getItem("havehdmicolordepth"):
			self.list.append((_("HDMI Colordepth"), config.av.hdmicolordepth, _("This option allows you to configure the Colordepth for UHD")))
		if BoxInfo.getItem("havecolorimetry"):
			self.list.append((_("HDMI Colorimetry"), config.av.hdmicolorimetry, _("This option allows you to configure the Colorimetry for HDR.")))
		if BoxInfo.getItem("havehdmihdrtype"):
			self.list.append((_("HDMI HDR Type"), config.av.hdmihdrtype, _("This option allows you to configure the HDR type.")))
			if config.av.hdmihdrtype.value == "auto":
				self.list.append((_("Switch HDR type by content"), config.av.hdmihdrtype_switch, _("Switch between SDR, HDR10 and HLG according to the current video content.")))
				if config.av.hdmihdrtype_switch.value and BoxInfo.getItem("havecolorimetry") and config.av.hdmicolorimetry.value == "auto":
					self.list.append((_("Colorimetry for HDR content"), config.av.hdmicolorimetry_hdr, _("Select the HDMI colorimetry used while HDR content is shown.")))
		if BoxInfo.getItem("havehdmihdrosd"):
			self.list.append((_("HDR OSD adjustment"), config.av.hdmihdrosd, _("This option adjusts SDR graphics and OSD colors while the HDMI output is in HDR mode.")))
		if BoxInfo.getItem("HasHDMIpreemphasis"):
			self.list.append((_("Use HDMI pre-emphasis"), config.av.hdmipreemphasis, _("This option can be useful for long HDMI cables.")))
		if BoxInfo.getItem("HDRSupport"):
			self.list.append((_("HLG support"), config.av.hlg_support, _("This option allows you to force the HLG modes for UHD")))
			self.list.append((_("HDR10 support"), config.av.hdr10_support, _("This option allows you to force the HDR10 modes for UHD")))
			self.list.append((_("Allow 12bit"), config.av.allow_12bit, _("This option allows you to enable or disable the 12 bit color mode")))
			self.list.append((_("Allow 10bit"), config.av.allow_10bit, _("This option allows you to enable or disable the 10 bit color mode")))
		if BoxInfo.getItem("haveamlhdrsupport"):
			self.list.append((_("Amlogic HLG Support"), config.av.amlhlg_support, _("This option allows you to force the HLG modes for UHD")))
			self.list.append((_("Amlogic HDR10 Support"), config.av.amlhdr10_support, _("This option allows you to force the HDR10 modes for UHD")))
		if BoxInfo.getItem("havesyncmode"):
			self.list.append((_("Video sync mode"), config.av.sync_mode, _("This option allows you to use video sync mode.")))

		if level >= 1 and BoxInfo.getItem("havedeinterlace"):
			self.list.append((_("Deinterlacer mode"), config.av.deinterlace, _("Select the de-interlacing mode of the video decoder.")))
		if config.av.videoport.value != "Scart":
			self.list.append((_("Show 'Manual resolution' in extensions menu"), config.av.manual_resolution_extmenu, _("Add an entry to the extensions menu to change the video mode for the current video.")))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def confirm(self, confirmed):
		if not confirmed:
			config.av.videoport.value = self.last_good[0]
			config.av.videomode[self.last_good[0]].value = self.last_good[1]
			config.av.videorate[self.last_good[1]].value = self.last_good[2]
			self.hw.setMode(*self.last_good)
		else:
			self.keySave()

	def grabLastGoodMode(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		self.last_good = (port, mode, rate)

	def apply(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		if (port, mode, rate) != self.last_good:
			self.hw.setMode(port, mode, rate)
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.confirm, MessageBox, _("Is this video mode ok?"), MessageBox.TYPE_YESNO, timeout=20, default=False)
		else:
			self.keySave()


def manualResolution(session):
	from Screens.ChoiceBox import ChoiceBox
	from Screens.MessageBox import MessageBox

	avControl = eAVControl.getInstance()
	oldMode = avControl.getVideoMode("")
	if not oldMode:
		return

	modes = [(x, x) for x in video_hw.readAvailableModes() if x not in ("auto", "pal", "ntsc") and not x.startswith("3d")]
	if not modes:
		return

	pol = "p" if avControl.getProgressive() else "i"
	rate = (avControl.getFrameRate(0) + 500) // 1000 * (2 if pol == "i" else 1)
	text = _("Video content: %ix%i%s %iHz") % (avControl.getResolutionX(0), avControl.getResolutionY(0), pol, rate)
	selection = next((index for index, x in enumerate(modes) if x[1] == oldMode), 0)

	def manualResolutionCallback(choice):
		if choice and choice[1] != oldMode:
			video_hw.setVideoModeDirect(choice[1])
			session.openWithCallback(confirmCallback, MessageBox, _("Is this video mode ok?"), MessageBox.TYPE_YESNO, timeout=10, default=False)

	def confirmCallback(answer):
		if not answer:
			video_hw.setVideoModeDirect(oldMode)

	session.openWithCallback(manualResolutionCallback, ChoiceBox, title=text, list=modes, selection=selection, windowTitle=_("Manual resolution"))


class VideomodeHotplug:
	def __init__(self, hw):
		self.hw = hw

	def start(self):
		self.hw.on_hotplug.append(self.hotplug)

	def stop(self):
		self.hw.on_hotplug.remove(self.hotplug)

	def hotplug(self, what):
		print("[Videomode] hotplug detected on port '%s'" % (what))
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value

		if not self.hw.isModeAvailable(port, mode, rate):
			print("[Videomode] mode %s/%s/%s went away!" % (port, mode, rate))
			modelist = self.hw.getModeList(port)
			if not len(modelist):
				print("[Videomode] sorry, no other mode is available (unplug?). Doing nothing.")
				return
			mode = modelist[0][0]
			rate = modelist[0][1]
			print("[Videomode] setting %s/%s/%s" % (port, mode, rate))
			self.hw.setMode(port, mode, rate)


hotplug = None


def startHotplug():
	global hotplug, video_hw
	hotplug = VideomodeHotplug(video_hw)
	hotplug.start()


def stopHotplug():
	global hotplug
	hotplug.stop()


def autostart(reason, session=None, **kwargs):
	if session is not None:
		global my_global_session
		my_global_session = session
		return

	if reason == 0:
		startHotplug()
	elif reason == 1:
		stopHotplug()


def videoSetupMain(session, **kwargs):
	session.open(VideoSetup, video_hw)


def startSetup(menuid):
	if menuid != "video":
		return []

	return [(_("Video Setup"), videoSetupMain, "av_setup", 40)]


def VideoWizard(*args, **kwargs):
	from Plugins.SystemPlugins.Videomode.VideoWizard import VideoWizard
	return VideoWizard(*args, **kwargs)


def Plugins(**kwargs):
	list = [
#		PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=videoModeSessionStart),
		PluginDescriptor(name=_("Video setup"), description=_("Advanced video setup"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=startSetup)
	]
	if config.misc.videowizardenabled.value:
		list.append(PluginDescriptor(name=_("Video wizard"), where=PluginDescriptor.WHERE_WIZARD, needsRestart=False, fnc=(20, VideoWizard)))
	return list
