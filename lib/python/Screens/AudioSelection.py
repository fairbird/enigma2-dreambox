# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.Setup import getConfigMenuItem, Setup
from Screens.InputBox import PinInput
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigNothing, ConfigSelection, ConfigYesNo
from Components.Label import Label
from Components.Sources.List import List
from Components.Sources.Boolean import Boolean
from Components.SystemInfo import BoxInfo
from Components.VolumeControl import VolumeControl
from Components.UsageConfig import originalAudioTracks, visuallyImpairedCommentary
from Components.Converter.ServiceInfo import StdAudioDesc
from Tools.ISO639 import LanguageCodes
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap

from enigma import iPlayableService, eTimer, eSize, eDVBDB, eServiceReference, eServiceCenter, iServiceInformation

FOCUS_CONFIG, FOCUS_STREAMS = range(2)
[PAGE_AUDIO, PAGE_SUBTITLES] = ["audio", "subtitles"]

selectionpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/audioselectionmark.png"))

def isIPTV(service):
	path = service and service.getPath()
	return path and not path.startswith("/") and service.type in [0x1, 0x1001, 0x138A, 0x1389]
class AudioSelection(ConfigListScreen, Screen):
	def __init__(self, session, infobar=None, page=PAGE_AUDIO):
		Screen.__init__(self, session)

		self["streams"] = List([], enableWrapAround=True)
		self["key_red"] = Boolean(False)
		self["key_green"] = Boolean(False)
		self["key_yellow"] = Boolean(True)
		self["key_blue"] = Boolean(False)
		self.protectContextMenu = True
		self.Plugins = []
		ConfigListScreen.__init__(self, [])
		self.infobar = infobar or self.session.infobar
		if not hasattr(self.infobar, "selected_subtitle"):
			self.infobar.selected_subtitle = None

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evUpdatedInfo: self.__updatedInfo
			})
		self.cached_subtitle_checked = False
		self.__selected_subtitle = None

		self["actions"] = NumberActionMap(["AudioSelectionActions", "SetupActions", "DirectionActions", "MenuActions"],
		{
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"ok": self.keyOk,
			"cancel": self.cancel,
			"up": self.keyUp,
			"down": self.keyDown,
			"volumeUp": self.volumeUp,
			"volumeDown": self.volumeDown,
			"volumeMute": self.volumeMute,
			"menu": self.openAutoLanguageSetup,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
		}, -2)

		self.settings = ConfigSubsection()
		choicelist = [(PAGE_AUDIO, ""), (PAGE_SUBTITLES, "")]
		self.settings.menupage = ConfigSelection(choices=choicelist, default=page)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self["config"].instance.setSelectionEnable(False)
		self.focus = FOCUS_STREAMS
		self.settings.menupage.addNotifier(self.fillList)

	def saveAVDict(self):
		eDVBDB.getInstance().saveIptvServicelist()

	def fillList(self, arg=None):
		streams = []
		conflist = []
		selectedidx = 0
		is_downmix = False

		self["key_blue"].setBoolean(False)

		subtitlelist = self.getSubtitleList()

		if self.settings.menupage.getValue() == PAGE_AUDIO:
			self.setTitle(_("Select audio track"))
			service = self.session.nav.getCurrentService()
			self.audioTracks = audio = service and service.audioTracks()
			track_num = audio and audio.getNumberOfTracks() or 0
			if BoxInfo.getItem("CanDownmixAC3") and track_num > 0 and config.usage.setup_level.index >= 1:
				downmix_ac3_value = config.av.downmix_ac3.value
				if downmix_ac3_value in ("downmix", "passthrough"):
					choice_list = [
						("downmix", _("Downmix")),
						("passthrough", _("Passthrough"))
					]
					self.settings.downmix = ConfigSelection(choices=choice_list, default=downmix_ac3_value)
					self.settings.downmix.addNotifier(self.changeAC3Downmix, initial_call=False)
					extra_text = " - AC3"
					if BoxInfo.getItem("CanDownmixDTS"):
						extra_text += ",DTS"
					if BoxInfo.getItem("CanDownmixAAC"):
						extra_text += ",AAC"
					conflist.append((_("Multi channel downmix") + extra_text, self.settings.downmix))
					self["key_red"].setBoolean(True)
					is_downmix = True
			if not is_downmix:
				conflist.append(('',))
				self["key_red"].setBoolean(False)

			if track_num > 0:
				self.audioChannel = service.audioChannel()
				if self.audioChannel:
					choicelist = [("0", _("left")), ("1", _("stereo")), ("2", _("right"))]
					self.settings.channelmode = ConfigSelection(choices=choicelist, default=str(self.audioChannel.getCurrentChannel()))
					self.settings.channelmode.addNotifier(self.changeMode, initial_call=False)
					conflist.append((_("Channel"), self.settings.channelmode))
					self["key_green"].setBoolean(True)
				else:
					conflist.append(('',))
					self["key_green"].setBoolean(False)
				selectedAudio = self.audioTracks.getCurrentTrack()
				for x in range(track_num):
					number = str(x + 1)
					i = audio.getTrackInfo(x)
					languages = i.getLanguage().split('/')
					description = StdAudioDesc(i.getDescription())
					selected = ""
					language = ""

					if selectedAudio == x:
						selected = "X"
						selectedidx = x

					cnt = 0
					for lang in languages:
						if cnt:
							language += ' / '
						if lang == "":
							language += _("Not defined")
						elif lang in originalAudioTracks:
							language += "%s  (%s)" % (_("Original audio"), lang)
						elif lang in LanguageCodes:
							language += _(LanguageCodes[lang][0])
						elif lang in visuallyImpairedCommentary:
							language += "%s  (%s)" % (_("Visually impaired commentary"), lang)
						else:
							language += lang
						cnt += 1

					streams.append((x, "", number, description, language, selected, selectionpng if selected == "X" else None))

			else:
				streams = []
				conflist.append(('',))
				self["key_green"].setBoolean(False)

			if subtitlelist:
				self["key_yellow"].setBoolean(True)
				conflist.append((_("To subtitle selection"), self.settings.menupage))
			else:
				self["key_yellow"].setBoolean(False)
				conflist.append(('',))

			if BoxInfo.getItem("Has3DSurround"):
				choice_list = [("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))]
				self.settings.surround_3d = ConfigSelection(choices=choice_list, default=config.av.surround_3d.value)
				self.settings.surround_3d.addNotifier(self.change3DSurround, initial_call=False)
				conflist.append((_("3D Surround"), self.settings.surround_3d, None))

			if BoxInfo.getItem("Has3DSpeaker") and config.av.surround_3d.value != "none":
				choice_list = [("center", _("center")), ("wide", _("wide")), ("extrawide", _("extra wide"))]
				self.settings.surround_3d_speaker = ConfigSelection(choices=choice_list, default=config.av.surround_3d_speaker.value)
				self.settings.surround_3d_speaker.addNotifier(self.change3DSurroundSpeaker, initial_call=False)
				conflist.append((_("3D Surround Speaker Position"), self.settings.surround_3d_speaker, None))

			if BoxInfo.getItem("HasAutoVolume"):
				choice_list = [("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))]
				self.settings.autovolume = ConfigSelection(choices=choice_list, default=config.av.autovolume.value)
				self.settings.autovolume.addNotifier(self.changeAutoVolume, initial_call=False)
				conflist.append((_("Auto Volume Level"), self.settings.autovolume, None))

			from Components.PluginComponent import plugins
			from Plugins.Plugin import PluginDescriptor

			if hasattr(self.infobar, "runPlugin"):
				class PluginCaller:
					def __init__(self, fnc, *args):
						self.fnc = fnc
						self.args = args

					def __call__(self, *args, **kwargs):
						self.fnc(*self.args)

				self.Plugins = [(p.name, PluginCaller(self.infobar.runPlugin, p)) for p in plugins.getPlugins(where=PluginDescriptor.WHERE_AUDIOMENU)]

				if self.Plugins:
					self["key_blue"].setBoolean(True)
					if len(self.Plugins) > 1:
						conflist.append((_("Audio plugins"), ConfigNothing()))
						self.plugincallfunc = [(x[0], x[1]) for x in self.Plugins]
					else:
						conflist.append((self.Plugins[0][0], ConfigNothing()))
						self.plugincallfunc = self.Plugins[0][1]

		elif self.settings.menupage.getValue() == PAGE_SUBTITLES:

			self.setTitle(_("Subtitle selection"))
			conflist.append(('',))
			conflist.append(('',))
			self["key_red"].setBoolean(False)
			self["key_green"].setBoolean(False)

			idx = 0

			for x in subtitlelist:
				number = str(x[1])
				description = "?"
				language = ""
				selected = ""

				if config.subtitles.show.value and self.selectedSubtitle and x[:4] == self.selectedSubtitle[:4]:
					selected = "X"
					selectedidx = idx

				try:
					if x[4] != "und":
						if x[4] in LanguageCodes:
							language = _(LanguageCodes[x[4]][0])
						else:
							language = x[4]
				except:
					language = ""

				languagetype = ""
				if language and len(x) == 6 and x[5]:
					languagetype = x[5].split()
					if languagetype and len(languagetype) == 2:
						language = "%s (%s)" % (language, languagetype[1])

				if x[0] == 0:
					description = "DVB"
					number = "%x" % (x[1])

				elif x[0] == 1:
					description = "teletext"
					number = "%x%02x" % (x[3] and x[3] or 8, x[2])

				elif x[0] == 2:
					types = (_("unknown"), _("embedded"), _("SSA file"), _("ASS file"),
							_("SRT file"), _("VOB file"), _("PGS file"))
					try:
						description = types[x[2]]
					except:
						description = _("unknown") + ": %s" % x[2]
					number = str(int(number) + 1)

				streams.append((x, "", number, description, language, selected, selectionpng if selected == "X" else None))
				idx += 1

			conflist.append((_("To audio selection"), self.settings.menupage))

			if self.infobar.selected_subtitle and self.infobar.selected_subtitle != (0, 0, 0, 0) and ".DVDPlayer'>" not in repr(self.infobar):
				self["key_blue"].setBoolean(True)
				conflist.append((_("Subtitle Quickmenu"), ConfigNothing()))

		self["config"].list = conflist

		self["streams"].list = streams
		self["streams"].setIndex(selectedidx)

	def __updatedInfo(self):
		self.fillList()

	def getSubtitleList(self):
		service = self.session.nav.getCurrentService()
		subtitle = service and service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()
		self.selectedSubtitle = self.infobar.selected_subtitle
		if self.selectedSubtitle and self.selectedSubtitle[:4] == (0, 0, 0, 0):
			self.selectedSubtitle = None
		elif self.selectedSubtitle and not self.selectedSubtitle[:4] in (x[:4] for x in subtitlelist):
			subtitlelist.append(self.selectedSubtitle)
		return subtitlelist

	def change3DSurround(self, surround_3d):
		if surround_3d.value:
			config.av.surround_3d.value = surround_3d.value
		config.av.surround_3d.save()

	def change3DSurroundSpeaker(self, surround_3d_speaker):
		if surround_3d_speaker.value:
			config.av.surround_3d_speaker.value = surround_3d_speaker.value
		config.av.surround_3d_speaker.save()

	def changeAutoVolume(self, autovolume):
		if autovolume.value:
			config.av.autovolume.value = autovolume.value
		config.av.autovolume.save()

	def changeAC3Downmix(self, downmix):
		config.av.downmix_ac3.setValue(downmix.value)
		if BoxInfo.getItem("HasMultichannelPCM"):
			config.av.multichannel_pcm.setValue(False)
		config.av.downmix_ac3.save()
		if BoxInfo.getItem("HasMultichannelPCM"):
			config.av.multichannel_pcm.save()
		self.fillList()

	def changeBTAudio(self, btaudio):
		if btaudio.value:
			config.av.btaudio.value = btaudio.value
		config.av.btaudio.save()

	def changePCMMultichannel(self, multichan):
		if multichan.value:
			config.av.multichannel_pcm.setValue(multichan.value)
		else:
			config.av.multichannel_pcm.setValue(False)
		config.av.multichannel_pcm.save()
		self.fillList()

	def changeAACDownmix(self, downmix):
		config.av.downmix_aac.setValue(downmix.value)
		config.av.downmix_aac.save()

	def changeAACDownmixPlus(self, downmix):
		config.av.downmix_aacplus.setValue(downmix.value)
		config.av.downmix_aacplus.save()

	def setAC3plusTranscode(self, transcode):
		config.av.transcodeac3plus.setValue(transcode.value)
		config.av.transcodeac3plus.save()

	def setWMAPro(self, downmix):
		config.av.wmapro.setValue(downmix.value)
		config.av.wmapro.save()

	def setDTSHD(self, downmix):
		config.av.dtshd.setValue(downmix.value)
		config.av.dtshd.save()

	def setAACTranscode(self, transcode):
		config.av.transcodeaac.setValue(transcode)
		config.av.transcodeaac.save()

	def changeDTSDownmix(self, downmix):
		if downmix.value:
			config.av.downmix_dts.setValue(True)
		else:
			config.av.downmix_dts.setValue(False)
		config.av.downmix_dts.save()

	def changeMode(self, mode):
		if mode is not None and self.audioChannel:
			self.audioChannel.selectChannel(int(mode.getValue()))

	def changeAudio(self, audio):
		track = int(audio)
		if isinstance(track, int):
			service = self.session.nav.getCurrentService()
			ref = self.session.nav.getCurrentlyPlayingServiceReference()
			#ref = ref and eServiceReference(ref.toString())
			if service.audioTracks().getNumberOfTracks() > track:
				self.audioTracks.selectTrack(track)
				if isIPTV(ref):
					self.saveAVDict()

	def keyLeft(self):
		if self.focus == FOCUS_CONFIG:
			ConfigListScreen.keyLeft(self)
		elif self.focus == FOCUS_STREAMS:
			self["streams"].setIndex(0)

	def keyRight(self, config=False):
		if config or self.focus == FOCUS_CONFIG:
			if self["config"].getCurrentIndex() < 3:
				ConfigListScreen.keyRight(self)
			elif self["config"].getCurrentIndex() == 3:
				if self.settings.menupage.getValue() == PAGE_AUDIO and hasattr(self, "plugincallfunc"):
					if len(self.Plugins) > 1:
						def runPluginAction(choice):
							if choice:
								choice[1]()
						self.session.openWithCallback(runPluginAction, ChoiceBox, title=_("Audio plugins"), list=self.plugincallfunc)
					else:
						self.plugincallfunc()
				elif self.settings.menupage.getValue() == PAGE_SUBTITLES and self.infobar.selected_subtitle and self.infobar.selected_subtitle != (0, 0, 0, 0):
					self.session.open(QuickSubtitlesConfigMenu, self.infobar)
		if self.focus == FOCUS_STREAMS and self["streams"].count() and config is False:
			self["streams"].setIndex(self["streams"].count() - 1)

	def keyRed(self):
		if self["key_red"].getBoolean():
			self.colorkey(0)
		else:
			return 0

	def keyGreen(self):
		if self["key_green"].getBoolean():
			self.colorkey(1)
		else:
			return 0

	def keyYellow(self):
		if self["key_yellow"].getBoolean():
			self.colorkey(2)
		else:
			return 0

	def keyBlue(self):
		if self["key_blue"].getBoolean():
			self.colorkey(3)
		else:
			return 0

	def colorkey(self, idx):
		self["config"].setCurrentIndex(idx)
		self.keyRight(True)

	def keyUp(self):
		if self.focus == FOCUS_CONFIG:
			self["config"].instance.moveSelection(self["config"].instance.moveUp)
		elif self.focus == FOCUS_STREAMS:
			if self["streams"].getIndex() == 0:
				self["config"].instance.setSelectionEnable(True)
				self["streams"].style = "notselected"
				self["config"].setCurrentIndex(len(self["config"].getList()) - 1)
				self.focus = FOCUS_CONFIG
			else:
				self["streams"].selectPrevious()

	def keyDown(self):
		if self.focus == FOCUS_CONFIG:
			configList = self["config"].getList()
			count = len(configList)
			for x in configList:
				if x[0] == "":
					count -= 1
			if self["config"].getCurrentIndex() < count - 1:
				self["config"].instance.moveSelection(self["config"].instance.moveDown)
			else:
				self["config"].instance.setSelectionEnable(False)
				self["streams"].style = "default"
				self.focus = FOCUS_STREAMS
		elif self.focus == FOCUS_STREAMS:
			self["streams"].selectNext()

	def volumeUp(self):
		VolumeControl.instance and VolumeControl.instance.volUp()

	def volumeDown(self):
		VolumeControl.instance and VolumeControl.instance.volDown()

	def volumeMute(self):
		VolumeControl.instance and VolumeControl.instance.volMute()

	def keyNumberGlobal(self, number):
		if number <= len(self["streams"].list):
			self["streams"].setIndex(number - 1)
			self.keyOk()

	def keyOk(self):
		if self.focus == FOCUS_STREAMS and self["streams"].list:
			cur = self["streams"].getCurrent()
			if self.settings.menupage.getValue() == PAGE_AUDIO and cur[0] is not None:
				self.changeAudio(cur[0])
				self.__updatedInfo()
			ref = self.session.nav.getCurrentlyPlayingServiceReference()
			#ref = ref and eServiceReference(ref.toString())
			if self.settings.menupage.getValue() == PAGE_SUBTITLES and cur[0] is not None:
				if config.subtitles.show.value and self.infobar.selected_subtitle and self.infobar.selected_subtitle[:4] == cur[0][:4]:
					self.infobar.enableSubtitle(None)
					selectedidx = self["streams"].getIndex()
					self.__updatedInfo()
					self["streams"].setIndex(selectedidx)
				else:
					config.subtitles.show.value = True
					self.infobar.enableSubtitle(cur[0][:5])
					self.__updatedInfo()
				if isIPTV(ref):
					self.saveAVDict()
			self.close(0)
		elif self.focus == FOCUS_CONFIG:
			self.keyRight()

	def openAutoLanguageSetup(self):
		if self.protectContextMenu and config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.context_menus.value:
			self.session.openWithCallback(self.protectResult, PinInput, pinList=[x.value for x in config.ParentalControl.servicepin], triesEntry=config.ParentalControl.retries.servicepin, title=_("Please enter the correct PIN code"), windowTitle=_("Enter PIN code"))
		else:
			self.protectResult(True)

	def protectResult(self, answer):
		if answer:
			self.session.open(Setup, "autolanguagesetup")
			self.protectContextMenu = False
		elif answer is not None:
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code you entered is wrong."), MessageBox.TYPE_ERROR)

	def cancel(self):
		self.close(0)


class SubtitleSelection(AudioSelection):
	def __init__(self, session, infobar=None):
		AudioSelection.__init__(self, session, infobar, page=PAGE_SUBTITLES)
		self.skinName = ["AudioSelection"]


class QuickSubtitlesConfigMenu(ConfigListScreen, Screen):
	skin = """
	<screen position="50,50" size="480,305" title="Subtitle settings" backgroundColor="#7f000000" flags="wfNoBorder">
		<widget name="config" position="5,5" size="470,275" font="Regular;18" zPosition="1" transparent="1" selectionPixmap="buttons/sel.png" verticalAlignment="center" />
		<widget name="videofps" position="5,280" size="470,20" backgroundColor="secondBG" transparent="1" zPosition="1" font="Regular;16" verticalAlignment="center" horizontalAlignment="left" foregroundColor="blue"/>
	</screen>"""

	FLAG_CENTER_DVB_SUBS = 2048

	def __init__(self, session, infobar):
		Screen.__init__(self, session)
		self.skin = QuickSubtitlesConfigMenu.skin
		self.infobar = infobar or self.session.infobar
		self.wait = eTimer()
		self.wait.timeout.get().append(self.resyncSubtitles)
		self.resume = eTimer()
		self.resume.timeout.get().append(self.resyncSubtitlesResume)
		self.service = self.session.nav.getCurrentlyPlayingServiceReference()
		servicepath = self.service and self.service.getPath()
		if servicepath and servicepath.startswith("/") and self.service.toString().startswith("1:"):
			info = eServiceCenter.getInstance().info(self.service)
			self.service_string = info and info.getInfoString(self.service, iServiceInformation.sServiceref)
		else:
			self.service_string = self.service.toString()
		self.center_dvb_subs = ConfigYesNo(default=(eDVBDB.getInstance().getFlag(eServiceReference(self.service_string)) & self.FLAG_CENTER_DVB_SUBS) and True)
		self.center_dvb_subs.addNotifier(self.setCenterDvbSubs)
		self["videofps"] = Label("")

		sub = self.infobar.selected_subtitle
		if sub[0] == 0:  # dvb
			menu = [
				getConfigMenuItem("config.subtitles.dvb_subtitles_yellow"),
				getConfigMenuItem("config.subtitles.dvb_subtitles_backtrans"),
				getConfigMenuItem("config.subtitles.dvb_subtitles_original_position"),
				(_("Center DVB subtitles"), self.center_dvb_subs),
				getConfigMenuItem("config.subtitles.subtitle_position"),
				getConfigMenuItem("config.subtitles.subtitle_bad_timing_delay"),
				getConfigMenuItem("config.subtitles.subtitle_noPTSrecordingdelay"),
			]
		elif sub[0] == 1:  # teletext
			menu = [
				getConfigMenuItem("config.subtitles.ttx_subtitle_colors"),
				getConfigMenuItem("config.subtitles.ttx_subtitle_original_position"),
				getConfigMenuItem("config.subtitles.subtitle_fontsize"),
				getConfigMenuItem("config.subtitles.subtitle_rewrap"),
				getConfigMenuItem("config.subtitles.subtitle_borderwidth"),
				getConfigMenuItem("config.subtitles.subtitles_backtrans"),
				getConfigMenuItem("config.subtitles.subtitle_alignment"),
				getConfigMenuItem("config.subtitles.subtitle_bad_timing_delay"),
				getConfigMenuItem("config.subtitles.subtitle_noPTSrecordingdelay"),
			]
		else: 		# pango
			menu = [
				getConfigMenuItem("config.subtitles.pango_subtitles_delay"),
				getConfigMenuItem("config.subtitles.pango_subtitle_colors"),
				getConfigMenuItem("config.subtitles.pango_subtitle_fontswitch"),
				getConfigMenuItem("config.subtitles.colourise_dialogs"),
				getConfigMenuItem("config.subtitles.subtitle_fontsize"),
				getConfigMenuItem("config.subtitles.subtitle_position"),
				getConfigMenuItem("config.subtitles.subtitle_alignment"),
				getConfigMenuItem("config.subtitles.subtitle_rewrap"),
				getConfigMenuItem("config.subtitles.pango_subtitle_removehi"),
				getConfigMenuItem("config.subtitles.subtitle_borderwidth"),
				getConfigMenuItem("config.subtitles.subtitles_backtrans"),
				getConfigMenuItem("config.subtitles.pango_subtitles_fps"),
			]
			self["videofps"].setText(_("Video: %s fps") % (self.getFps().rstrip(".000")))

		ConfigListScreen.__init__(self, menu, self.session, on_change=self.changedEntry)

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"cancel": self.cancel,
			"ok": self.ok,
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)

	def setCenterDvbSubs(self, configElement):
		if configElement.value:
			eDVBDB.getInstance().addFlag(eServiceReference(self.service_string), self.FLAG_CENTER_DVB_SUBS)
			config.subtitles.dvb_subtitles_centered.value = True
		else:
			eDVBDB.getInstance().removeFlag(eServiceReference(self.service_string), self.FLAG_CENTER_DVB_SUBS)
			config.subtitles.dvb_subtitles_centered.value = False

	def layoutFinished(self):
		if not self["videofps"].text:
			self.instance.resize(eSize(self.instance.size().width(), self["config"].l.getItemSize().height() * len(self["config"].getList()) + 10))

	def changedEntry(self):
		if self["config"].getCurrent() in [getConfigMenuItem("config.subtitles.pango_subtitles_delay"), getConfigMenuItem("config.subtitles.pango_subtitles_fps")]:
			self.wait.start(500, True)

	def resyncSubtitles(self):
		self.infobar.setSeekState(self.infobar.SEEK_STATE_PAUSE)
		self.resume.start(100, True)

	def resyncSubtitlesResume(self):
		self.infobar.setSeekState(self.infobar.SEEK_STATE_PLAY)

	def getFps(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if not info:
			return ""
		fps = info.getInfo(iServiceInformation.sFrameRate)
		if fps > 0:
			return "%6.3f" % (fps / 1000.)
		return ""

	def cancel(self):
		self.center_dvb_subs.removeNotifier(self.setCenterDvbSubs)
		self.close()

	def ok(self):
		config.subtitles.save()
		self.close()
