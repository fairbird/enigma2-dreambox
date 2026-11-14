# -*- coding: utf-8 -*-
from enigma import getDesktop, eTimer
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.ScreenAnimations import eWindowAnimationManager
from Components.config import config, configfile, getConfigListEntry, ConfigSelection, ConfigSelectionNumber
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.HardwareInfo import HardwareInfo


def getDesktopSize():
	s = getDesktop(0).size()
	return (s.width(), s.height())


def isFullHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] == 1920


def isUHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] == 2560 or desktopSize[0] == 3840


class AnimationSetup(ConfigListScreen, Screen):
	skin_fhd = """
		<screen name="AnimationSetup" position="center,center" size="1360,970" title="OSD Animation Settings" resolution="1920,1080">
			<widget name="key_red" position="10,10" size="320,50" zPosition="1" font="Regular;26" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_green" position="343,10" size="320,50" zPosition="1" font="Regular;26" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_yellow" position="676,10" size="320,50" zPosition="1" font="Regular;26" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_blue" position="1009,10" size="320,50" zPosition="1" font="Regular;26" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" shadowColor="black" shadowOffset="-2,-2" />
			<eLabel position="10,72" size="1340,1" backgroundColor="grey" />
			<widget name="config" position="10,80" size="1340,770" font="Regular;30" valueFont="Regular;30" itemHeight="48" enableWrapAround="1" scrollbarMode="showOnDemand" />
			<eLabel position="10,860" size="1340,1" backgroundColor="grey" />
			<widget name="description" position="10,868" size="1340,90" font="Regular;26" halign="center" valign="center" />
		</screen>"""
	skin_uhd = """
		<screen name="AnimationSetup" position="center,center" size="2720,1940" title="OSD Animation Settings" resolution="3840,2160">
			<widget name="key_red" position="20,20" size="640,100" zPosition="1" font="Regular;52" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_green" position="686,20" size="640,100" zPosition="1" font="Regular;52" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_yellow" position="1352,20" size="640,100" zPosition="1" font="Regular;52" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_blue" position="2018,20" size="640,100" zPosition="1" font="Regular;52" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" shadowColor="black" shadowOffset="-2,-2" />
			<eLabel position="20,144" size="2680,2" backgroundColor="grey" />
			<widget name="config" position="20,160" size="2680,1540" font="Regular;60" valueFont="Regular;60" itemHeight="96" enableWrapAround="1" scrollbarMode="showOnDemand" />
			<eLabel position="20,1720" size="2680,2" backgroundColor="grey" />
			<widget name="description" position="20,1736" size="2680,180" font="Regular;52" halign="center" valign="center" />
		</screen>"""

	def __init__(self, session):
		self.skin = self.skin_uhd if isUHD() else self.skin_fhd
		Screen.__init__(self, session)
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))
		self["key_yellow"] = Label(_("Default"))
		self["key_blue"] = Label(_("Preview"))
		self["description"] = Label()
		self.styleConfig = ConfigSelection(default=config.osd.window_animation_default.value if config.osd.window_animation.value else eWindowAnimationManager.KEY_DISABLED, choices=list(eWindowAnimationManager.getAnimations().items()))
		ConfigListScreen.__init__(self, [], session=session, on_change=self.createSetup)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
			"cancel": self.keyCancel,
			"save": self.keySave,
			"yellow": self.keyDefault,
			"blue": self.keyPreview,
		}, -2)
		self["config"].onSelectionChanged.append(self.updateDescription)
		self.createSetup()

	def createSetup(self):
		note = " " + _("(Needs engine support; stored for later use.)")
		entries = [
			getConfigListEntry(_("Window animation"), self.styleConfig, _("Select the default OSD window animation.")),
			getConfigListEntry(_("Animation speed"), config.osd.animation_speed, _("Higher is faster. 15 is the standard speed.")),
			getConfigListEntry(_("Smooth list selection"), config.osd.animation_smooth_list, _("Move the list selection smoothly between entries.")),
			getConfigListEntry(_("Fade changed widget content"), config.osd.widget_animation, _("Cross-fade changing texts and pictures.")),
		]
		if self.hasDisplay():
			entries.append(getConfigListEntry(_("Fade changed display content"), config.osd.widget_animation_display, _("Cross-fade on the front display.")))
		entries += [
			getConfigListEntry(_("Widget fade duration (ms)"), config.osd.widget_animation_duration, _("Duration of the widget cross-fade in milliseconds.")),
			getConfigListEntry(_("Animation memory limit"), config.osd.animation_memory_limit, _("Shared limit for old and new widget content, including estimated texture storage.") + note),
			getConfigListEntry(_("Wizard step transitions"), config.osd.animation_wizard, _("Animate the change between wizard steps.") + note),
			getConfigListEntry(_("Picture player crossfade"), config.osd.animation_picture_crossfade, _("Cross-fade between pictures in the picture player.") + note),
			getConfigListEntry(_("Picture crossfade duration (ms)"), config.osd.animation_picture_crossfade_duration, _("Duration of the picture player cross-fade.") + note),
		]
		entries += [
			getConfigListEntry(_("TV InfoBar animation"), config.osd.animation_infobar, _("Animate the TV InfoBar independently of other windows. Slide moves it fully into the picture from below and out through the bottom edge when hidden.")),
			getConfigListEntry(_("Media InfoBar animation"), config.osd.animation_mediainfobar, _("Animate the media player InfoBar independently of other windows.")),
		]
		if config.osd.animation_infobar.value != "disabled" or config.osd.animation_mediainfobar.value != "disabled":
			entries.append(getConfigListEntry(_("InfoBar animation duration (ms)"), config.osd.animation_infobar_duration, _("Duration of the InfoBar animations.")))
		entries.append(getConfigListEntry(_("Adaptive animation profiles"), config.osd.animation_profiles, _("Use a separate animation for dialogs, popups and toasts.")))
		if config.osd.animation_profiles.value:
			entries += [
				getConfigListEntry(_("Dialog and message animation"), config.osd.animation_dialog, _("Message boxes and progress dialogs.")),
				getConfigListEntry(_("Popup and panel animation"), config.osd.animation_popup, _("Choice lists, context menus and small panels.")),
				getConfigListEntry(_("Toast notification animation"), config.osd.animation_toast, _("Short notifications.")),
				getConfigListEntry(_("Toast fade duration (ms)"), config.osd.animation_toast_duration, _("Duration of the toast animation.")),
			]
		self["config"].list = [(e[0], e[1]) for e in entries]
		self.descriptions = dict((id(e[1]), e[2]) for e in entries)
		self.applyLive()
		self.updateDescription()

	def keySelect(self):
		cur = self["config"].getCurrent()
		item = cur[1] if cur else None
		if isinstance(item, ConfigSelection) and not isinstance(item, ConfigSelectionNumber):
			def callback(answer):
				if answer:
					item.value = answer[1]
					self["config"].invalidateCurrent()
					self.createSetup()
			self.session.openWithCallback(callback, ChoiceBox, title=cur[0], list=list(zip(item.description, item.choices)), selection=item.getIndex(), keys=[], windowTitle=cur[0])
		else:
			ConfigListScreen.keySelect(self)

	def hasDisplay(self):
		return HardwareInfo().get_device_name() in ExtendedAnimationsSetup.DEVICES_TO_ANIMATE

	def applyLive(self):
		config.osd.window_animation.value = self.styleConfig.value != eWindowAnimationManager.KEY_DISABLED
		eWindowAnimationManager.setDefault(self.styleConfig.value)

	def updateDescription(self):
		cur = self["config"].getCurrent()
		self["description"].setText(getattr(self, "descriptions", {}).get(id(cur[1]), "") if cur else "")

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.updateDescription()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.updateDescription()

	def keySave(self):
		if self.styleConfig.value != eWindowAnimationManager.KEY_DISABLED:
			config.osd.window_animation_default.value = self.styleConfig.value
		config.osd.window_animation.value = self.styleConfig.value != eWindowAnimationManager.KEY_DISABLED
		for item in (config.osd.window_animation_default, config.osd.window_animation, config.osd.animation_speed, config.osd.animation_profiles, config.osd.animation_dialog, config.osd.animation_popup, config.osd.animation_toast, config.osd.animation_infobar, config.osd.animation_mediainfobar, config.osd.animation_infobar_duration, config.osd.animation_toast_duration, config.osd.animation_smooth_list, config.osd.animation_memory_limit, config.osd.animation_wizard, config.osd.animation_picture_crossfade, config.osd.animation_picture_crossfade_duration, config.osd.widget_animation, config.osd.widget_animation_display, config.osd.widget_animation_duration):
			item.save()
		configfile.save()
		eWindowAnimationManager.setDefault(config.osd.window_animation_default.value)
		eWindowAnimationManager.setWidgetDefault()
		self.close()

	def keyCancel(self):
		for item in (config.osd.window_animation, config.osd.animation_speed, config.osd.animation_profiles, config.osd.animation_dialog, config.osd.animation_popup, config.osd.animation_toast, config.osd.animation_infobar, config.osd.animation_mediainfobar, config.osd.animation_infobar_duration, config.osd.animation_toast_duration, config.osd.animation_smooth_list, config.osd.animation_memory_limit, config.osd.animation_wizard, config.osd.animation_picture_crossfade, config.osd.animation_picture_crossfade_duration, config.osd.widget_animation, config.osd.widget_animation_display, config.osd.widget_animation_duration):
			item.cancel()
		eWindowAnimationManager.setDefault(config.osd.window_animation_default.value)
		self.close()

	def keyDefault(self):
		for item in (config.osd.animation_speed, config.osd.animation_profiles, config.osd.animation_dialog, config.osd.animation_popup, config.osd.animation_toast, config.osd.animation_infobar, config.osd.animation_mediainfobar, config.osd.animation_infobar_duration, config.osd.animation_toast_duration, config.osd.animation_smooth_list, config.osd.animation_memory_limit, config.osd.animation_wizard, config.osd.animation_picture_crossfade, config.osd.animation_picture_crossfade_duration):
			item.value = item.default
		self.styleConfig.value = "simple_fade"
		self.createSetup()

	def keyPreview(self):
		cur = self["config"].getCurrent()
		item = cur[1] if cur else None
		if item in (config.osd.animation_toast,):
			self.session.open(PreviewToast)
		elif item in (config.osd.animation_popup,):
			self.session.openWithCallback(self.previewDone, ChoiceBox, title=_("Popup preview"), list=[(_("Option %d") % i, i) for i in range(1, 4)])
		elif item in (config.osd.animation_infobar, config.osd.animation_mediainfobar, config.osd.animation_infobar_duration):
			self.session.open(PreviewInfobar, "mediainfobar" if item is config.osd.animation_mediainfobar else "infobar")
		else:
			original = Screen.animationHook
			dialogRow = item is config.osd.animation_dialog

			def previewHook(screen):
				if screen is self:
					screen.instance.setAnimationId(-1)
				elif dialogRow:
					original(screen)
				else:
					screen.instance.setAnimationId(0)

			self.previewHook = original
			self.instance.setAnimationId(-1)
			Screen.animationHook = previewHook
			self.hide = lambda: None
			self.session.openWithCallback(self.previewDone, PreviewMessage)

	def previewDone(self, *args):
		self.__dict__.pop("hide", None)
		if getattr(self, "previewHook", None):
			Screen.animationHook = self.previewHook
			self.previewHook = None
			eWindowAnimationManager.applyScreen(self)


class PreviewMessage(Screen):
	skin = """
		<screen name="PreviewMessage" position="center,center" size="900,340" zPosition="1000" flags="wfNoBorder" transparent="1" resolution="1920,1080">
			<eLabel position="0,0" size="900,340" zPosition="-1" backgroundColor="#0D1B26" cornerRadius="28" borderWidth="3" borderColor="#5E90A0" />
			<widget name="text" position="40,40" size="820,100" zPosition="1" font="Regular;48" halign="center" valign="center" foregroundColor="#FFFFFF" transparent="1" />			<widget name="text" position="40,40" size="820,100" font="Regular;48" halign="center" valign="center" foregroundColor="#FFFFFF" transparent="1" />
			<eLabel position="120,160" size="660,2" backgroundColor="#5E90A0" />
			<widget name="hint" position="40,180" size="820,120" zPosition="1" font="Regular;32" halign="center" valign="center" foregroundColor="#9FB6C3" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["text"] = Label(_("Animation preview"))
		self["hint"] = Label()
		self.left = 3
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.close, "cancel": self.close}, -1)
		self.timer = eTimer()
		self.timer.callback.append(self.tick)
		self.tick()
		self.timer.start(1000)

	def tick(self):
		if self.left <= 0:
			self.timer.stop()
			self.close()
			return
		self["hint"].setText(_("Closing in %d s") % self.left)
		self.left -= 1


class PreviewToast(Screen):
	skin = """
		<screen name="PreviewToast" position="center,40" size="520,70" flags="wfNoBorder" backgroundColor="#CC101010" resolution="1280,720">
			<widget name="text" position="10,5" size="500,60" font="Regular;24" halign="center" valign="center" transparent="1" />
		</screen>"""
	animationProfile = "toast"

	def __init__(self, session):
		Screen.__init__(self, session)
		self["text"] = Label(_("Toast preview"))
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.close, "cancel": self.close}, -1)
		from enigma import eTimer
		self.timer = eTimer()
		self.timer.callback.append(self.close)
		self.timer.start(2000, True)


class PreviewInfobar(Screen):
	skin = """
		<screen name="PreviewInfobar" position="0,520" size="1280,200" flags="wfNoBorder" backgroundColor="#CC101010" resolution="1280,720">
			<widget name="text" position="20,60" size="1240,80" font="Regular;28" halign="center" valign="center" transparent="1" />
		</screen>"""

	def __init__(self, session, profile="infobar"):
		Screen.__init__(self, session)
		self.animationProfile = profile
		self["text"] = Label(_("Infobar preview"))
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.close, "cancel": self.close}, -1)
		from enigma import eTimer
		self.timer = eTimer()
		self.timer.callback.append(self.close)
		self.timer.start(2500, True)


class ExtendedAnimationsSetup(ConfigListScreen, Screen):
	DEVICES_TO_ANIMATE = ["dm900", "dm920"]

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["ExtendedAnimationsSetup", "Setup"]
		self.setTitle(_("Extend Animations Configuration"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["footnote"] = Label()
		self["footnote"].hide()
		self["description"] = Label()
		self.hasDisplay = HardwareInfo().get_device_name() in self.DEVICES_TO_ANIMATE
		ConfigListScreen.__init__(self, [], session=session, on_change=self.createSetup)
		self["actions"] = ActionMap(["SetupActions"], {"cancel": self.keyCancel, "save": self.keySave}, -2)
		self.createSetup()

	def createSetup(self):
		entries = [
			(_("OSD"),),
			getConfigListEntry(_("OSD cross-fading for text and pictures"), config.osd.widget_animation),
		]
		if self.hasDisplay:
			entries.extend([
				(_("Display"),),
				getConfigListEntry(_("Display cross-fading for text and pictures"), config.osd.widget_animation_display),
			])
		if config.osd.widget_animation.value == "on" or (self.hasDisplay and config.osd.widget_animation_display.value == "on"):
			entries.extend([
				(_("General Settings"),),
				getConfigListEntry(_("Cross-fading duration"), config.osd.widget_animation_duration),
			])
		self["config"].list = entries

	def saveAll(self):
		quitData = ConfigListScreen.saveAll(self)
		eWindowAnimationManager.setWidgetDefault()
		return quitData
