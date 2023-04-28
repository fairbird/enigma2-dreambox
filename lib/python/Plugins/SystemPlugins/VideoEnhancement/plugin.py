from Plugins.Plugin import PluginDescriptor
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigNothing
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from .import VideoEnhancement
import os
import skin


class VideoEnhancementSetup(ConfigListScreen, Screen):

	skin = """
		<screen name="VideoEnhancementSetup" position="center,center" size="560,440" title="VideoEnhancementSetup">
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="config" position="5,50" size="550,350" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="div-h.png" position="0,400" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="5,410" size="550,42" zPosition="10" font="Regular;20" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.onChangedEntry = []
		self.skinName = ["VideoEnhancementSetup"]
		self.setTitle(_("Video enhancement setup"))
		self["introduction"] = StaticText()

		self.list = []
		self.xtdlist = []
		self.seperation = skin.parameters.get("ConfigListSeperator", 300)
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)
		self.createSetup()

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"yellow": self.keyYellow,
				"blue": self.keyBlue,
				"menu": self.closeRecursive,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Last config"))
		self["key_blue"] = StaticText(_("Default"))

		if self.SelectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.SelectionChanged)
		self.rememberOldSettings()
		self.changedEntry()

	def rememberOldSettings(self):
		self.oldContrast = config.pep.contrast.value
		self.oldSaturation = config.pep.saturation.value
		self.oldHue = config.pep.hue.value
		self.oldBrightness = config.pep.brightness.value
		self.oldBlock_noise = config.pep.block_noise_reduction.value
		self.oldMosquito_noise = config.pep.mosquito_noise_reduction.value
		self.oldDigital_contour = config.pep.digital_contour_removal.value
		self.oldScaler_sharpness = config.av.scaler_sharpness.value
		self.oldScaler_vertical_dejagging = config.pep.scaler_vertical_dejagging.value
		self.oldSmooth = config.pep.smooth.value
		self.oldSplit = config.pep.split.value
		self.oldSharpness = config.pep.sharpness.value
		self.oldAuto_flesh = config.pep.auto_flesh.value
		self.oldGreen_boost = config.pep.green_boost.value
		self.oldBlue_boost = config.pep.blue_boost.value
		self.oldDynamic_contrast = config.pep.dynamic_contrast.value

	def addToConfigList(self, description, configEntry, hinttext, add_to_xtdlist=False):
		if isinstance(configEntry, ConfigNothing):
			return None
		entry = (description, configEntry, hinttext)
		self.list.append(entry)
		if add_to_xtdlist:
			self.xtdlist.append(entry)
		return entry

	def createSetup(self):
		self.list = []
		self.xtdlist = []
		addToConfigList = self.addToConfigList
		self.splitEntry = addToConfigList(_("Split preview mode"), config.pep.split, _("This option allows you to view the old and new settings side by side."), True)
		add_to_xtdlist = self.splitEntry is not None
		self.auto_fleshEntry = addToConfigList(_("Auto flesh"), config.pep.auto_flesh, _("This option sets the picture flesh tones."), add_to_xtdlist)
		self.block_noise_reductionEntry = addToConfigList(_("Block noise reduction"), config.pep.block_noise_reduction, _("This option allows to reduce the block-noise in the picture. Obviously this is at the cost of the picture's sharpness."), add_to_xtdlist)
		self.brightnessEntry = addToConfigList(_("Brightness"), config.pep.brightness, _("This option sets the picture brightness."))
		self.blue_boostEntry = addToConfigList(_("Boost blue"), config.pep.blue_boost, _("This option allows you to boost the blue tones in the picture."), add_to_xtdlist)
		self.green_boostEntry = addToConfigList(_("Boost green"), config.pep.green_boost, _("This option allows you to boost the green tones in the picture."), add_to_xtdlist)
		self.contrastEntry = addToConfigList(_("Contrast"), config.pep.contrast, _("This option sets the picture contrast."))
		self.digital_contour_removalEntry = addToConfigList(_("Digital contour removal"), config.pep.digital_contour_removal, _("This option sets the surpression of false digital contours, that are the result of a limited number of discrete values."), add_to_xtdlist)
		self.dynamic_contrastEntry = addToConfigList(_("Dynamic contrast"), config.pep.dynamic_contrast, _("This option allows to set the level of dynamic contrast of the picture."), add_to_xtdlist)
		self.hueEntry = addToConfigList(_("Hue"), config.pep.hue, _("This option sets the picture hue."))
		self.mosquito_noise_reductionEntry = addToConfigList(_("Mosquito noise reduction"), config.pep.mosquito_noise_reduction, _("This option set the level of surpression of mosquito noise (Mosquito Noise is random aliasing as a result of strong compression). Obviously this goes at the cost of picture details."), add_to_xtdlist)
		self.scaler_sharpnessEntry = addToConfigList(_("Scaler sharpness"), config.av.scaler_sharpness, _("This option sets the scaler sharpness, used when stretching picture from 4:3 to 16:9."))
		self.scaler_vertical_dejaggingEntry = addToConfigList(_("Scaler vertical dejagging"), config.pep.scaler_vertical_dejagging, _("This option allows you enable the vertical scaler dejagging."))
		self.smoothEntry = addToConfigList(_("Smooth"), config.pep.smooth, _("This option allows you enable smoothing filter to control the dithering process."))
		self.sharpnessEntry = addToConfigList(_("Sharpness"), config.pep.sharpness, _("This option sets up the picture sharpness, used when the picture is being upscaled."), add_to_xtdlist)
		self.saturationEntry = addToConfigList(_("Saturation"), config.pep.saturation, _("This option sets the picture saturation."))
		self["config"].list = self.list
		self["config"].l.setSeperation(self.seperation)
		self["config"].l.setList(self.list)

	def SelectionChanged(self):
		self["introduction"].setText(self["config"].getCurrent() and len(self["config"].getCurrent()[2]) > 2 and self["config"].getCurrent()[2] or "")

	def PreviewClosed(self):
		self["config"].invalidate(self["config"].getCurrent())
		self.createSetup()

	def keyLeft(self):
		current = self["config"].getCurrent()
		if current in (self.splitEntry, self.scaler_vertical_dejaggingEntry, self.smoothEntry):
			ConfigListScreen.keyLeft(self)
		else:
			if current in self.xtdlist:
				self.previewlist = [current, self.splitEntry]
				oldsplitmode = config.pep.split.value
			else:
				self.previewlist = [current]
				oldsplitmode = None
			maxvalue = current[1].max
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry=self.previewlist, oldSplitMode=oldsplitmode, maxValue=maxvalue)

	def keyRight(self):
		current = self["config"].getCurrent()
		if current in (self.splitEntry, self.scaler_vertical_dejaggingEntry, self.smoothEntry):
			ConfigListScreen.keyRight(self)
		else:
			if current in self.xtdlist:
				self.previewlist = [current, self.splitEntry]
				oldsplitmode = config.pep.split.value
			else:
				self.previewlist = [current]
				oldsplitmode = None
			maxvalue = current[1].max
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry=self.previewlist, oldSplitMode=oldsplitmode, maxValue=maxvalue)

	def confirm(self, confirmed):
		if confirmed:
			if self.splitEntry is not None:
				config.pep.split.setValue('off')
			self.keySave()

	def apply(self):
		self.session.openWithCallback(self.confirm, MessageBox, _("Use this video enhancement settings?"), MessageBox.TYPE_YESNO, timeout=20, default=True)

	def cancelConfirm(self, result):
		if not result:
			return
		self.keyYellowConfirm(True)
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default=False)
		else:
			self.close()

	def keyYellowConfirm(self, confirmed):
		if confirmed:
			if self.contrastEntry is not None:
				config.pep.contrast.setValue(self.oldContrast)
			if self.saturationEntry is not None:
				config.pep.saturation.setValue(self.oldSaturation)
			if self.hueEntry is not None:
				config.pep.hue.setValue(self.oldHue)
			if self.brightnessEntry is not None:
				config.pep.brightness.setValue(self.oldBrightness)
			if self.block_noise_reductionEntry is not None:
				config.pep.block_noise_reduction.setValue(self.oldBlock_noise)
			if self.mosquito_noise_reductionEntry is not None:
				config.pep.mosquito_noise_reduction.setValue(self.oldMosquito_noise)
			if self.digital_contour_removalEntry is not None:
				config.pep.digital_contour_removal.setValue(self.oldDigital_contour)
			if self.scaler_sharpnessEntry is not None:
				config.av.scaler_sharpness.setValue(self.oldScaler_sharpness)
			if self.scaler_vertical_dejaggingEntry is not None:
				config.pep.scaler_vertical_dejagging.setValue(self.oldScaler_vertical_dejagging)
			if self.smoothEntry is not None:
				config.pep.smooth.setValue(self.oldSmooth)
			if self.splitEntry is not None:
				config.pep.split.setValue('off')
			if self.sharpnessEntry is not None:
				config.pep.sharpness.setValue(self.oldSharpness)
			if self.auto_fleshEntry is not None:
				config.pep.auto_flesh.setValue(self.oldAuto_flesh)
			if self.green_boostEntry is not None:
				config.pep.green_boost.setValue(self.oldGreen_boost)
			if self.blue_boostEntry is not None:
				config.pep.blue_boost.setValue(self.oldBlue_boost)
			if self.dynamic_contrastEntry is not None:
				config.pep.dynamic_contrast.setValue(self.oldDynamic_contrast)
			self.keySave()

	def keyYellow(self):
		self.session.openWithCallback(self.keyYellowConfirm, MessageBox, _("Reset video enhancement settings to your last configuration?"), MessageBox.TYPE_YESNO, timeout=20, default=False)

	def keyBlueConfirm(self, confirmed):
		if not confirmed:
			if self.contrastEntry is not None:
				config.pep.contrast.setValue(128)
			if self.saturationEntry is not None:
				config.pep.saturation.setValue(128)
			if self.hueEntry is not None:
				config.pep.hue.setValue(128)
			if self.brightnessEntry is not None:
				config.pep.brightness.setValue(128)
			if self.block_noise_reductionEntry is not None:
				config.pep.block_noise_reduction.setValue(0)
			if self.mosquito_noise_reductionEntry is not None:
				config.pep.mosquito_noise_reduction.setValue(0)
			if self.digital_contour_removalEntry is not None:
				config.pep.digital_contour_removal.setValue(0)
			if self.scaler_sharpnessEntry is not None:
				config.av.scaler_sharpness.setValue(13)
			if self.scaler_vertical_dejaggingEntry is not None:
				config.pep.scaler_vertical_dejagging.setValue(False)
			if self.smoothEntry is not None:
				config.pep.smooth.setValue(False)
			if self.splitEntry is not None:
				config.pep.split.setValue('off')
			if self.sharpnessEntry is not None:
				config.pep.sharpness.setValue(0)
			if self.auto_fleshEntry is not None:
				config.pep.auto_flesh.setValue(0)
			if self.green_boostEntry is not None:
				config.pep.green_boost.setValue(0)
			if self.blue_boostEntry is not None:
				config.pep.blue_boost.setValue(0)
			if self.dynamic_contrastEntry is not None:
				config.pep.dynamic_contrast.setValue(0)
			self.keySave()

	def keyBlue(self):
		self.session.openWithCallback(self.keyBlueConfirm, MessageBox, _("Reset video enhancement settings to system defaults?"), MessageBox.TYPE_YESNO, timeout=20, default=False)


class VideoEnhancementPreview(ConfigListScreen, Screen):
	skin = """
		<screen name="VideoEnhancementPreview" position="center,e-170" size="560,170" title="VideoEnhancementPreview">
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="5,50" size="550,80" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="div-h.png" position="0,130" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="0,140" size="550,25" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, configEntry=None, oldSplitMode=None, maxValue=None):
		Screen.__init__(self, session)

		self.onChangedEntry = []
		self.setTitle(_("Video enhancement preview"))
		self.oldSplitMode = oldSplitMode
		self.maxValue = maxValue
		self.configStepsEntry = None
		self.isStepSlider = None
		self.seperation = skin.parameters.get("ConfigListSeperator", 300)

		self.list = []
		self.configEntry = configEntry
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["introduction"] = StaticText()

		self.createSetup()

	def createSetup(self):
		self.list = []
		if self.maxValue == 255:
			self.configStepsEntry = (_("Change step size"), config.pep.configsteps)

		if self.configEntry is not None:
			self.list = self.configEntry
		if self.maxValue == 255:
			self.list.append(self.configStepsEntry)

		self["config"].list = self.list
		self["config"].l.setSeperation(self.seperation)
		self["config"].l.setList(self.list)
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["introduction"].setText(_("Current value: ") + self.getCurrentValue())
		try:
			max_avail = self["config"].getCurrent()[1].max
			if max_avail == 255:
				self.isStepSlider = True
			else:
				self.isStepSlider = False
		except AttributeError:
			print("[VideoEnhancement] no max value")

	def keyLeft(self):
		if self.isStepSlider:
			self["config"].getCurrent()[1].increment = config.pep.configsteps.value
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		if self.isStepSlider:
			self["config"].getCurrent()[1].increment = config.pep.configsteps.value
		ConfigListScreen.keyRight(self)

	def keySave(self):
		if self.oldSplitMode is not None:
			currentSplitMode = config.pep.split.value
			if self.oldSplitMode == 'off' and currentSplitMode != 'off':
				config.pep.split.setValue('off')
			else:
				pass
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		if self.oldSplitMode is not None:
			currentSplitMode = config.pep.split.value
			if self.oldSplitMode == 'off' and currentSplitMode != 'off':
				config.pep.split.setValue('off')
			else:
				pass
		self.close()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

def videoEnhancementSetupMain(session, **kwargs):
	session.open(VideoEnhancementSetup)


def startSetup(menuid):
	if menuid == "video" and config.usage.setup_level.index == 2:
		return [(_("Video enhancement settings"), videoEnhancementSetupMain, "videoenhancement_setup", 41)]
	return []


def Plugins(**kwargs):
	list = []
	if config.usage.setup_level.index >= 2 and os.path.exists("/proc/stb/vmpeg/0/pep_apply"):
		return PluginDescriptor(name=_("Video enhancement setup"), description=_("Advanced video enhancement setup"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=startSetup)
	return []
