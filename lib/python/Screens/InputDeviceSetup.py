# -*- coding: utf-8 -*-
from enigma import getDesktop
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Components.InputDevice import iInputDevices, iRcTypeControl
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.config import config, ConfigYesNo, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, HelpableActionMap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

FHD = False
if getDesktop(0).size().width() >= 1920:
	FHD = True


class InputDeviceSelection(HelpableScreen, Screen):

	if FHD:
		skin = """
		<screen name="InputDeviceSelection" position="center,center" size="560,400">
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphaTest="on"/>
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphaTest="on"/>
			<ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphaTest="on"/>
			<ePixmap pixmap="buttons/blue.png" position="420,0" size="140,40" alphaTest="on"/>
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#9f1313" transparent="1"/>
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#1f771f" transparent="1"/>
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#a08500" transparent="1"/>
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#18188b" transparent="1"/>
			<widget source="list" render="Listbox" position="5,50" size="550,280" zPosition="10" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
				<!--  device, description, devicepng, divpng  -->
								{"template": [
										MultiContentEntryPixmapAlphaBlend(pos = (2, 8), size = (54, 54), png = 2), # index 3 is the interface pixmap
										MultiContentEntryText(pos = (65, 6), size = (450, 54), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER|RT_WRAP, text = 1), # index 1 is the interfacename
									],
								"fonts": [gFont("Regular", 28),gFont("Regular", 20)],
								"itemHeight": 70
								}
				</convert>
			</widget>
			<ePixmap pixmap="div-h.png" position="0,340" zPosition="1" size="560,2"/>
			<widget source="introduction" render="Label" position="0,350" size="560,50" zPosition="10" font="Regular;21" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#25062748" transparent="1"/>
		</screen>"""
	else:
		skin = """
		<screen name="InputDeviceSelection" position="center,center" size="902,740">
			<ePixmap pixmap="buttons/red.png" position="85,0" size="140,40" alphaTest="on"/>
			<ePixmap pixmap="buttons/green.png" position="275,0" size="140,40" alphaTest="on"/>
			<ePixmap pixmap="buttons/yellow.png" position="465,0" size="140,40" alphaTest="on"/>
			<ePixmap pixmap="buttons/blue.png" position="665,0" size="140,40" alphaTest="on"/>
			<widget source="key_red" render="Label" position="85,0" zPosition="1" size="140,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#9f1313" transparent="1"/>
			<widget source="key_green" render="Label" position="275,0" zPosition="1" size="140,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#1f771f" transparent="1"/>
			<widget source="key_yellow" render="Label" position="465,0" zPosition="1" size="140,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#a08500" transparent="1"/>
			<widget source="key_blue" render="Label" position="665,0" zPosition="1" size="140,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#18188b" transparent="1"/>
			<widget source="list" render="Listbox" position="5,50" size="891,618" zPosition="10" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
				<!--  device, description, devicepng, divpng  -->
								{"template": [
										MultiContentEntryPixmapAlphaBlend(pos = (2, 14), size = (54, 54), png = 2), # index 3 is the interface pixmap
										MultiContentEntryText(pos = (65, 2), size = (450, 80), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER|RT_WRAP, text = 1), # index 1 is the interfacename
									],
								"fonts": [gFont("Regular", 30),gFont("Regular", 25)],
								"itemHeight": 80
								}
				</convert>
			</widget>
			<ePixmap pixmap="div-h.png" position="0,675" zPosition="1" size="900,2"/>
			<widget source="introduction" render="Label" position="0,680" size="900,60" zPosition="10" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#25062748" transparent="1"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Select input device"))
		HelpableScreen.__init__(self)

		self.edittext = _("Press OK to edit the settings.")

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["introduction"] = StaticText(self.edittext)

		self.devices = [(iInputDevices.getDeviceName(x), x) for x in iInputDevices.getDeviceList()]
		print("[InputDeviceSelection] found devices :->", len(self.devices), self.devices)

		self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions"],
			{
			"cancel": (self.close, _("Exit input device selection.")),
			"ok": (self.okbuttonClick, _("Select input device.")),
			}, -2)

		self["ColorActions"] = HelpableActionMap(self, ["ColorActions"],
			{
			"red": (self.close, _("Exit input device selection.")),
			"green": (self.okbuttonClick, _("Select input device.")),
			}, -2)

		self.currentIndex = 0
		self.list = []
		self["list"] = List(self.list)
		self.updateList()
		self.onClose.append(self.cleanup)

	def cleanup(self):
		self.currentIndex = 0

	def buildInterfaceList(self, device, description, type, isinputdevice=True):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "div-h.png"))
		activepng = None
		devicepng = None
		enabled = iInputDevices.getDeviceAttribute(device, 'enabled')

		if type == 'remote':
			if config.misc.rcused.value == 0:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcnew-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcnew.png"))
			else:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcold-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcold.png"))
		elif type == 'keyboard':
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_keyboard-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_keyboard.png"))
		elif type == 'mouse':
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_mouse-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_mouse.png"))
		elif isinputdevice:
			devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcnew.png"))
		return ((device, description, devicepng, divpng))

	def updateList(self):
		self.list = []

		if iRcTypeControl.multipleRcSupported():
			self.list.append(self.buildInterfaceList('rctype', _('Configure remote control type'), None, False))

		for x in self.devices:
			dev_type = iInputDevices.getDeviceAttribute(x[1], 'type')
			self.list.append(self.buildInterfaceList(x[1], _(x[0]), dev_type))

		self["list"].setList(self.list)
		self["list"].setIndex(self.currentIndex)

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		self.currentIndex = self["list"].getIndex()
		if selection is not None:
			if selection[0] == 'rctype':
				self.session.open(RemoteControlType)
			else:
				self.session.openWithCallback(self.DeviceSetupClosed, InputDeviceSetup, selection[0])

	def DeviceSetupClosed(self, *ret):
		self.updateList()


class InputDeviceSetup(ConfigListScreen, Screen):

	if FHD:
		skin = """
			<screen name="InputDeviceSetup" position="center,center" size="560,440">
				<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphaTest="on" />
				<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphaTest="on" />
				<ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphaTest="on" />
				<ePixmap pixmap="buttons/blue.png" position="420,0" size="140,40" alphaTest="on" />
				<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#9f1313" transparent="1" />
				<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#a08500" transparent="1" />
				<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#18188b" transparent="1" />
				<widget name="config" position="5,50" size="550,350" scrollbarMode="showOnDemand" />
				<ePixmap pixmap="div-h.png" position="0,400" zPosition="1" size="560,2" />
				<widget source="introduction" render="Label" position="5,410" size="550,30" zPosition="10" font="Regular;21" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#25062748" transparent="1" />
			</screen>"""
	else:
		skin = """
			<screen name="InputDeviceSelection" position="center,center" size="902,740">
				<ePixmap pixmap="buttons/red.png" position="85,0" size="140,40" alphaTest="on"/>
				<ePixmap pixmap="buttons/green.png" position="275,0" size="140,40" alphaTest="on"/>
				<ePixmap pixmap="buttons/yellow.png" position="465,0" size="140,40" alphaTest="on"/>
				<ePixmap pixmap="buttons/blue.png" position="665,0" size="140,40" alphaTest="on"/>
				<widget source="key_red" render="Label" position="85,0" zPosition="1" size="140,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#9f1313" transparent="1"/>
				<widget source="key_green" render="Label" position="275,0" zPosition="1" size="140,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#1f771f" transparent="1"/>
				<widget source="key_yellow" render="Label" position="465,0" zPosition="1" size="140,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#a08500" transparent="1"/>
				<widget source="key_blue" render="Label" position="665,0" zPosition="1" size="140,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#18188b" transparent="1"/>
				<widget name="config" font="Regular;28" itemHeight="40" position="5,50" size="891,618" scrollbarMode="showOnDemand" />
				<ePixmap pixmap="div-h.png" position="0,675" zPosition="1" size="900,2"/>
				<widget source="introduction" render="Label" position="0,680" size="900,60" zPosition="10" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#25062748" transparent="1"/>
 		</screen>"""

	def __init__(self, session, device):
		Screen.__init__(self, session)
		self.setTitle(_("Input device setup"))
		self.inputDevice = device
		iInputDevices.currentDevice = self.inputDevice
		self.onChangedEntry = []
		self.isStepSlider = None
		self.enableEntry = None
		self.repeatEntry = None
		self.delayEntry = None
		self.nameEntry = None
		self.enableConfigEntry = None

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"menu": self.closeRecursive,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["introduction"] = StaticText()

		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def layoutFinished(self):
		listWidth = self["config"].l.getItemSize().width()
		# use 20% of list width for sliders
		self["config"].l.setSeperation(int(listWidth * .8))

	def cleanup(self):
		iInputDevices.currentDevice = ""

	def createSetup(self):
		self.list = []
		label = _("Change repeat and delay settings?")
		cmd = "self.enableEntry = (label, config.inputDevices." + self.inputDevice + ".enabled)"
		exec(cmd)
		label = _("Interval between keys when repeating:")
		cmd = "self.repeatEntry = (label, config.inputDevices." + self.inputDevice + ".repeat)"
		exec(cmd)
		label = _("Delay before key repeat starts:")
		cmd = "self.delayEntry = (label, config.inputDevices." + self.inputDevice + ".delay)"
		exec(cmd)
		label = _("Device name:")
		cmd = "self.nameEntry = (label, config.inputDevices." + self.inputDevice + ".name)"
		exec(cmd)
		if self.enableEntry:
			if isinstance(self.enableEntry[1], ConfigYesNo):
				self.enableConfigEntry = self.enableEntry[1]

		self.list.append(self.enableEntry)
		if self.enableConfigEntry:
			if self.enableConfigEntry.value:
				self.list.append(self.repeatEntry)
				self.list.append(self.delayEntry)
			else:
				self.repeatEntry[1].setValue(self.repeatEntry[1].default)
				self["config"].invalidate(self.repeatEntry)
				self.delayEntry[1].setValue(self.delayEntry[1].default)
				self["config"].invalidate(self.delayEntry)
				self.nameEntry[1].setValue(self.nameEntry[1].default)
				self["config"].invalidate(self.nameEntry)

		self["config"].list = self.list
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		if self["config"].getCurrent() == self.enableEntry:
			self["introduction"].setText(_("Current device: ") + str(iInputDevices.getDeviceAttribute(self.inputDevice, 'name')))
		else:
			self["introduction"].setText(_("Current value: ") + self.getCurrentValue() + _(" ms"))

	def newConfig(self):
		current = self["config"].getCurrent()
		if current:
			if current == self.enableEntry:
				self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def confirm(self, confirmed):
		if not confirmed:
			print("not confirmed")
			return
		else:
			self.nameEntry[1].setValue(iInputDevices.getDeviceAttribute(self.inputDevice, 'name'))
			cmd = "config.inputDevices." + self.inputDevice + ".name.save()"
			exec(cmd)
			self.keySave()

	def apply(self):
		self.session.openWithCallback(self.confirm, MessageBox, _("Use these input device settings?"), MessageBox.TYPE_YESNO, timeout=20, default=True)

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), MessageBox.TYPE_YESNO, timeout=20, default=True)
		else:
			self.close()

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()


class RemoteControlType(ConfigListScreen, Screen):
	rcList = [
			("0", _("Default")),
			("4", _("DMM normal")),
			("5", _("et9000/et9100")),
			("6", _("DMM advanced")),
			("7", _("et5000/et6000")),
			("8", _("VU+")),
			("9", _("et8000/et10000")),
			("11", _("et9200/et9500/et6500")),
			("13", _("et4000")),
			("14", _("xp1000")),
			("16", _("HDx1/HD1xxx/HD5x0C/VS1x00/et7x00/et8500/et7000mini")),
			("18", _("F1/F3/F4/F4-TURBO")),
			("19", _("HD2400")),
			("20", _("Zgemma Star S/2S/H1/H2")),
			("21", _("Zgemma H.S/H.2S/H.2H/H5/H7(old model)")),
			("24", _("Axas E4HD Ultra")),
			("25", _("Zgemma H9(old model)/I55Plus/H8")),
			("27", _("HD60/HD66SE/Multibox/Multibox SE")),
			("28", _("I55SE/H7(new model)/H9(new model)/H9COMBO/H9TWIN/H9SE/H9COMBOSE/H10/H11")),
			("30", _("PULSe 4K(mini)"))
		]

	defaultRcList = [
			("et4000", 13),
			("et5000", 7),
			("et6000", 7),
			("et6500", 11),
			("et8000", 9),
			("et9000", 5),
			("et9100", 5),
			("et9200", 11),
			("et9500", 11),
			("et10000", 9),
			("formuler1", 18),
			("formuler3", 18),
			("formuler4", 18),
			("formuler4turbo", 18),
			("xp1000", 14),
			("vs1000", 16),
			("vs1500", 16),
			("hd500c", 16),
			("hd530c", 16),
			("hd11", 16),
			("hd51", 16),
			("hd1200", 16),
			("hd1265", 16),
			("hd1100", 16),
			("hd2400", 19),
			("hd60", 27),
			("hd66se", 27),
			("multibox", 27),
			("multiboxse", 27),
			("et7000mini", 16),
			("et7000", 16),
			("et7500", 16),
			("et8500", 16),
			("sh1", 20),
			("h3", 21),
			("h5", 21),
			("e4hd", 24),
			("h8", 25),
			("h9se", 28),
			("h9combo", 28),
			("h9combose", 28),
			("i55se", 28),
			("h7", 28), # new model /old 21
			("h9", 28), # new model /old 25
			("h9twin", 28),
			("h9twinse", 28),
			("h10", 28),
			("h11", 28),
			("pulse4k", 30),
			("pulse4kmini", 30)
		]

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["RemoteControlType", "Setup"]
		self.setTitle(_("Remote control type setup"))

		self["actions"] = ActionMap(["SetupActions"],
		{
			"cancel": self.keyCancel,
			"save": self.keySave,
		}, -1)

		self["key_green"] = StaticText(_("Save"))
		self["key_red"] = StaticText(_("Cancel"))

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session)

		rctype = config.plugins.remotecontroltype.rctype.value
		self.rctype = ConfigSelection(choices=self.rcList, default=str(rctype))
		self.list.append((_("Remote control type"), self.rctype))
		self["config"].list = self.list

		self.defaultRcType = 0
		self.getDefaultRcType()

	def getDefaultRcType(self):
		data = iRcTypeControl.getBoxType()
		for x in self.defaultRcList:
			if x[0] in data:
				self.defaultRcType = x[1]
				break
		if self.defaultRcType == 0:
			self.defaultRcType = iRcTypeControl.readRcType()

	def setDefaultRcType(self):
		iRcTypeControl.writeRcType(self.defaultRcType)

	def keySave(self):
		if config.plugins.remotecontroltype.rctype.value == int(self.rctype.value):
			self.close()
		else:
			self.setNewSetting()
			self.session.openWithCallback(self.keySaveCallback, MessageBox, _("Is this setting ok?"), MessageBox.TYPE_YESNO, timeout=20, default=True, timeout_default=False)

	def keySaveCallback(self, answer):
		if not answer:
			self.restoreOldSetting()
		else:
			config.plugins.remotecontroltype.rctype.value = int(self.rctype.value)
			config.plugins.remotecontroltype.save()
			self.close()

	def restoreOldSetting(self):
		if config.plugins.remotecontroltype.rctype.value == 0:
			self.setDefaultRcType()
		else:
			iRcTypeControl.writeRcType(config.plugins.remotecontroltype.rctype.value)

	def setNewSetting(self):
		if int(self.rctype.value) == 0:
			self.setDefaultRcType()
		else:
			iRcTypeControl.writeRcType(int(self.rctype.value))

	def keyCancel(self):
		self.restoreOldSetting()
		self.close()
