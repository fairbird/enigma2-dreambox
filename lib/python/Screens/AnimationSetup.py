# -*- coding: utf-8 -*-
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ScreenAnimations import eWindowAnimationManager
from Components.config import config, configfile, getConfigListEntry
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen


class AnimationSetup(Screen):
	skin = """
		<screen name="AnimationSetup" position="center,120" size="820,520" title="Animation Setup" resolution="1280,720">
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="410,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="610,5" size="200,40" alphatest="on" />
			<widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_yellow" position="410,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_blue" position="610,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<eLabel position="10,50" size="800,1" backgroundColor="grey" />
			<widget name="list" position="10,60" size="800,390" font="Regular;22" itemHeight="30" enableWrapAround="1" scrollbarMode="showOnDemand" />
			<eLabel position="10,480" size="800,1" backgroundColor="grey" />
			<widget name="selected_info" position="10,488" size="800,25" font="Regular;22" halign="center" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["list"] = MenuList([], enableWrapAround=True)
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))
		self["key_yellow"] = Label(_("Extended"))
		self["key_blue"] = Label(_("Preview"))
		self["selected_info"] = Label(_("* current animation"))
		self["SetupActions"] = ActionMap(["SetupActions", "ColorActions"], {
			"save": self.keySave,
			"cancel": self.close,
			"ok": self.keySave,
			"yellow": self.keyExtended,
			"blue": self.keyPreview,
		}, -3)
		self.reload()

	def reload(self):
		items = []
		selected = 0
		for index, (key, name) in enumerate(eWindowAnimationManager.getAnimations().items()):
			if key == config.osd.window_animation_default.value:
				name = "* %s" % name
				selected = index
			items.append((name, key))
		self["list"].setList(items)
		self["list"].moveToIndex(selected)

	def getCurrent(self):
		return self["list"].getCurrent()

	def keySave(self):
		current = self.getCurrent()
		if current:
			config.osd.window_animation_default.value = current[1]
			config.osd.window_animation_default.save()
			configfile.save()
			eWindowAnimationManager.setDefault(current[1])
		self.close()

	def keyPreview(self):
		current = self.getCurrent()
		if current:
			eWindowAnimationManager.setDefault(current[1])
			self.session.openWithCallback(self.previewDone, MessageBox, current[0], MessageBox.TYPE_INFO, timeout=3)

	def previewDone(self, *args):
		eWindowAnimationManager.setDefault(config.osd.window_animation_default.value)

	def keyExtended(self):
		self.session.open(ExtendedAnimationsSetup)


class ExtendedAnimationsSetup(ConfigListScreen, Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.skinName = ["ExtendedAnimationsSetup", "Setup"]
		self.setTitle(_("Extend Animations Configuration"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["footnote"] = Label()
		self["footnote"].hide()
		self["description"] = Label()
		ConfigListScreen.__init__(self, [], session=session, on_change=self.createSetup, fullUI=True)
		self.createSetup()

	def createSetup(self):
		entries = [
			(_("OSD"),),
			getConfigListEntry(_("OSD cross-fading for text and pictures"), config.osd.widget_animation),
		]
		if config.osd.widget_animation.value:
			entries.extend([
				(_("General Settings"),),
				getConfigListEntry(_("Cross-fading duration"), config.osd.widget_animation_duration),
			])
		if len(entries) != len(self["config"].list or []):
			self["config"].list = entries

	def saveAll(self):
		quitData = ConfigListScreen.saveAll(self)
		eWindowAnimationManager.setWidgetDefault()
		return quitData
