# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSlider, ConfigYesNo
from Components.Label import Label
from Plugins.SystemPlugins.OSDPositionSetup.plugin import setPosition, setConfiguredPosition
from enigma import quitMainloop, eTimer, getDesktop
import os


class OverscanWizard(Screen, ConfigListScreen):
	def __init__(self, session, timeOut=True):
		if getDesktop(0).size().height() == 1080:
			self.skin = """<screen position="fill" flags="wfNoBorder">
				<ePixmap pixmap="overscan1920x1080.png" position="0,0" size="1920,1080" zPosition="3" alphaTest="on"/>
				<eLabel position="338,190" size="1244,698" zPosition="3"/>
				<widget name="title" position="353,202" size="1224,50" font="Regular;40" foregroundColor="blue" zPosition="4"/>
				<widget name="introduction" position="343,252" size="1234,623" horizontalAlignment="center" verticalAlignment="center" font="Regular;30" zPosition="4"/>
				<widget name="config" position="343,662" size="1234,226" font="Regular;30" itemHeight="40" zPosition="4"/>
			</screen>"""
		else:
			self.skin = """<screen position="fill"  flags="wfNoBorder">
				<ePixmap pixmap="overscan1280x720.png" position="0,0" size="1280,720" zPosition="3" alphaTest="on"/>
				<eLabel position="235,131" size="810,457" zPosition="3"/>
				<widget name="title" position="240,135" size="800,40" font="Regular;30" foregroundColor="blue" zPosition="4"/>
				<widget name="introduction" position="240,175" size="800,623" horizontalAlignment="center" verticalAlignment="center" font="Regular;18" zPosition="4"/>
				<widget name="config" position="240,590" size="800,120" font="Regular;20" itemHeight="30" zPosition="4"/>
			</screen>"""

		Screen.__init__(self, session)
		self.setTitle(_("Overscan wizard"))
		self["introduction"] = Label()

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"ok": self.keyGo,
		}, -2)

		self.step = 1
		self.list = []
		ConfigListScreen.__init__(self, self.list, session)
		self.setScreen()

		self.Timer = eTimer()
		if timeOut:
			self.countdown = 10
			self.Timer.callback.append(self.TimerTimeout)
			self.Timer.start(1000)

		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		from enigma import eSize, ePoint
		if getDesktop(0).size().height() == 1080:
			lenlist = len(self.list) * 40
			self["config"].instance.move(ePoint(343, 873 - lenlist))
			self["config"].instance.resize(eSize(1234, lenlist))
			self["introduction"].instance.resize(eSize(1234, 623 - lenlist))
		else:
			lenlist = len(self.list) * 30
			self["config"].instance.move(ePoint(240, 580 - lenlist))
			self["config"].instance.resize(eSize(800, lenlist))
			self["introduction"].instance.resize(eSize(800, 405 - lenlist))

	def setScreen(self):
		self.list = []
		if self.step == 1:
			self["introduction"].setText(_("The overscan wizard helps you to setup your TV in the correct way.\n\n"
				"For the majority of TV's, the factory default is to have overscan enabled. "
				"This means you are always watching a \"zoomed in\" picture instead of real HD, and parts of the user inferface (skin) may be invisible.\n\n"
				"The yellow area means a 5% border area of a full HD picture will be invisible.\n"
				"The green area means a 10% border area of a full HD picture will be invisible.\n\n"
				"In other words, if the yellow box touches all four sides of your screen, you have at least 5% overscan on all sides.\n\n"
				"If you see the tips of all eight arrowheads, then your TV has overscan disabled.\n\n"
				"Test Pattern by TigerDave - www.tigerdave.com/ht_menu.htm"))
			self.yes_no = ConfigYesNo(default=True, graphic=False)
			self.list.append((_("Did you see all eight arrow heads?"), self.yes_no))
			self.save_new_position = False
			setPosition(0, 720, 0, 576)
		elif self.step == 2:
			self.Timer.stop()
			self.setTitle(_("Overscan wizard"))
			self["introduction"].setText(_("It seems you did not see all the eight arrow heads. This means your TV "
				"has overscan enabled, and is not configured properly.\n\n"
				"Please refer to your TV's manual to find how you can disable overscan on your TV. Look for terms like 'Just fit', 'Full width', etc. "
				"If you can't find it, ask other users at http://forums.openpli.org.\n\n"))
			self.list.append((_("Did you see all eight arrow heads?"), self.yes_no))
			self.yes_no.value = True
			self.save_new_position = False
			setPosition(0, 720, 0, 576)
		elif self.step == 3:
			self["introduction"].setText(_("You did not see all eight arrow heads. This means your TV has overscan enabled "
				"and presents you with a zoomed-in picture, causing you to loose part of a full HD screen. In addition to this "
				"you may also miss parts of the user interface, for example volume bars and more.\n\n"
				"You can now try to resize and change the position of the user interface until you see the eight arrow heads.\n\n"
				"When done press OK.\n\n"))
			self.dst_left = ConfigSlider(default=config.plugins.OSDPositionSetup.dst_left.value, increment=1, limits=(0, 720))
			self.dst_right = ConfigSlider(default=config.plugins.OSDPositionSetup.dst_left.value + config.plugins.OSDPositionSetup.dst_width.value, increment=1, limits=(0, 720))
			self.dst_top = ConfigSlider(default=config.plugins.OSDPositionSetup.dst_top.value, increment=1, limits=(0, 576))
			self.dst_bottom = ConfigSlider(default=config.plugins.OSDPositionSetup.dst_top.value + config.plugins.OSDPositionSetup.dst_height.value, increment=1, limits=(0, 576))
			self.list.append((_("left"), self.dst_left))
			self.list.append((_("right"), self.dst_right))
			self.list.append((_("top"), self.dst_top))
			self.list.append((_("bottom"), self.dst_bottom))
			setConfiguredPosition()
		elif self.step == 4:
			self["introduction"].setText(_("You did not see all eight arrow heads. This means your TV has overscan enabled "
				"and presents you with a zoomed-in picture, causing you to loose part of a full HD screen. In addition this "
				"you may also miss parts of the user interface, for example volume bars and more.\n\n"
				"Unfortunately, your model of receiver is not capable to adjust the dimensions of the user interface. "
				"If not everything is visible, you should change the installed skin to one that supports the overscan area of your TV.\n\n"
				"When you select a different skin, the user interface of your receiver will restart.\n\n"
				"Note: you can always start the Overscan wizard later, via\n\nmenu->installation->system->Overscan wizard"))
			self.yes_no.value = False
			self.list.append((_("Do you want to select a different skin?"), self.yes_no))
		elif self.step == 5:
			self.Timer.stop()
			self.setTitle(_("Overscan wizard"))
			self["introduction"].setText(_("The overscan wizard has been completed.\n\n"
				"Note: you can always start the Overscan wizard later, via\n\nMenu->Installation->System->Audio/Video->Overscan wizard"))
			self.yes_no.value = True
			self.list.append((_("Do you want to quit the overscan wizard?"), self.yes_no))
		elif self.step == 6:
			config.skin.primary_skin.value = "PLi-HD/skin.xml"
			config.save()
			self["introduction"].setText(_("The user interface of the receiver will now restart to select the selected skin"))
			quitMainloop(3)
		self["config"].list = self.list
		if self["config"].instance:
			self.__layoutFinished()

	def TimerTimeout(self):
		self.countdown -= 1
		self.setTitle(_("Overscan wizard") + " (%s)" % self.countdown)
		if not(self.countdown):
			self.keyCancel()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		if self.step == 3:
			self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		if self.step == 3:
			self.setPreviewPosition()

	def keyGo(self):
		if self.step == 1:
			self.step = self.yes_no.value and 5 or 2
		elif self.step == 2:
			self.step = self.yes_no.value and 5 or os.path.exists("/proc/stb/fb/dst_left") and 3 or 4
		elif self.step == 3:
			self.save_new_position = True
			self.step = 5
		elif self.step == 4:
			self.step = self.yes_no.value and 6 or 5
		elif self.step == 5:
			if self.yes_no.value:
				if self.save_new_position:
					config.plugins.OSDPositionSetup.dst_left.value = self.dst_left.value
					config.plugins.OSDPositionSetup.dst_width.value = self.dst_right.value - self.dst_left.value
					config.plugins.OSDPositionSetup.dst_top.value = self.dst_top.value
					config.plugins.OSDPositionSetup.dst_height.value = self.dst_bottom.value - self.dst_top.value
				else:
					config.plugins.OSDPositionSetup.dst_left.value = 0
					config.plugins.OSDPositionSetup.dst_width.value = 720
					config.plugins.OSDPositionSetup.dst_top.value = 0
					config.plugins.OSDPositionSetup.dst_height.value = 576
				config.misc.do_overscanwizard.value = False
				config.misc.do_overscanwizard.save()
				config.plugins.OSDPositionSetup.save()
				setConfiguredPosition()
				self.close()
			else:
				self.step = 1
		self.setScreen()

	def setPreviewPosition(self):
		if self.dst_left.value > self.dst_right.value:
			self.dst_left.value = self.dst_right.value
		if self.dst_top.value > self.dst_bottom.value:
			self.dst_top.value = self.dst_bottom.value
		self["config"].list = self.list
		setPosition(int(self.dst_left.value), int(self.dst_right.value) - int(self.dst_left.value), int(self.dst_top.value), int(self.dst_bottom.value) - int(self.dst_top.value))

	def keyCancel(self):
		self.step = self.step in (2, 5) and 1 or self.step in (3, 4) and 2
		if self.step:
			self.setScreen()
		else:
			setConfiguredPosition()
			self.close()
