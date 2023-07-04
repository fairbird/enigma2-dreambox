# -*- coding: utf-8 -*-
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import config
from Components.ConfigList import ConfigListScreen
from Components.NetworkTime import ntpSyncPoller
from Components.Sources.StaticText import StaticText
from Screens.Setup import Setup
from Tools.Geolocation import geolocation
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.HelpMenu import Rc
from Tools.Directories import fileContains
from enigma import getDesktop

def getDesktopSize():
	s = getDesktop(0).size()
	return (s.width(), s.height())

def isHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] == 1280


class Time(Setup):
	def __init__(self, session):
		Setup.__init__(self, session=session, setup="Time")
		self["key_yellow"] = StaticText("")
		self["geolocationActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.useGeolocation, _("Use geolocation to set the current time zone location")),
			"green": (self.keySave, _("Save and update Network Time")),
		}, prio=0, description=_("Time Setup Actions"))
		self.NTPserver = config.misc.NTPserver.value
		self.SyncTimeUsing = config.misc.SyncTimeUsing.value
		self.useNTPminutes = config.misc.useNTPminutes.value
		self.selectionChanged()

	def updateNetworkTime(self):
		if not self.NTPserver == config.misc.NTPserver.value or not self.SyncTimeUsing == config.misc.SyncTimeUsing.value or not self.useNTPminutes == config.misc.useNTPminutes.value:
			ntpSyncPoller.timeCheck()

	def selectionChanged(self):
		if Setup.getCurrentItem(self) in (config.timezone.area, config.timezone.val):
			self["key_yellow"].setText(_("Use Geolocation"))
			self["geolocationActions"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["geolocationActions"].setEnabled(False)
		Setup.selectionChanged(self)

	def useGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="status,message,timezone,proxy")
		if geolocationData.get("proxy", True):
			self.session.open(MessageBox, 'Geolocation is not available.', MessageBox.TYPE_INFO, timeout=3)
			return
		tz = geolocationData.get("timezone", None)
		if tz is None:
			self.session.open(MessageBox, 'Geolocation does not contain time zone information.', MessageBox.TYPE_INFO, timeout=3)
		else:
			areaItem = None
			valItem = None
			for item in self["config"].list:
				if item[1] is config.timezone.area:
					areaItem = item
				if item[1] is config.timezone.val:
					valItem = item
			area, zone = tz.split("/", 1)
			config.timezone.area.value = area
			if areaItem is not None:
				areaItem[1].changed()
			self["config"].invalidate(areaItem)
			config.timezone.val.value = zone
			if valItem is not None:
				valItem[1].changed()
			self["config"].invalidate(valItem)
			self.session.open(MessageBox, 'Geolocation has been used to set the time zone.', MessageBox.TYPE_INFO, timeout=3)

	def yellow(self):  # Invoked from the Wizard.
		self.useGeolocation()

	def keySave(self):
		Setup.keySave(self)
		self.updateNetworkTime()


class TimeWizard(ConfigListScreen, Screen, Rc):
	if isHD():
		skin = """
		<screen name="TimeWizard" position="0,0" size="1280,720" resolution="1280,720">
			<widget name="text" position="30,10" size="1000,47" font="Regular;20" transparent="1" verticalAlignment="center" />
			<widget name="config" position="212,95" size="944,430" enableWrapAround="1" entryFont="Regular;25" valueFont="Regular;25" itemHeight="35" scrollbarMode="showOnDemand" />
			<eLabel position="234,710" zPosition="2" size="234,2" foregroundColor="#00ff2525" backgroundColor="#00ff2525"/>
			<eLabel position="519,710" zPosition="2" size="234,2" foregroundColor="#00bab329" backgroundColor="#00bab329"/>
			<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="234,670" size="234,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="519,670" size="234,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
			<widget name="rc" conditional="rc" alphaTest="blend" position="24,95" size="163,524" />
			<widget name="wizard" conditional="wizard" pixmap="picon_default.png" position="1044,582" size="220,132" alphaTest="blend"/>
			<widget name="indicatorU0" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU1" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU2" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU3" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU4" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU5" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU6" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU7" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU8" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU9" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU10" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU11" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU12" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU13" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU14" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU15" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL0" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL1" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL2" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL3" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL4" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL5" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL6" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL7" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL8" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL9" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL10" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL11" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL12" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL13" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL14" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL15" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		</screen>"""
	else:
		skin = """
		<screen name="TimeWizard" position="center,center" size="1746,994" resolution="1920,1080" flags="wfNoBorder">
			<widget name="text" position="10,10" size="1619,40" font="Regular;35" transparent="1" verticalAlignment="center" />
			<widget name="config" position="253,221" size="1446,512" font="Regular;30" valueFont="Regular;30" itemHeight="40" />
			<eLabel position="113,977" zPosition="2" size="250,4" foregroundColor="#00ff2525" backgroundColor="#00ff2525"/>
			<eLabel position="385,977" zPosition="2" size="250,4" foregroundColor="#00bab329" backgroundColor="#00bab329"/>
			<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="113,935" size="250,45" backgroundColor="key_red" conditional="key_red" font="Regular;30" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="385,937" size="250,45" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;35" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
			<widget name="rc" conditional="rc" alphaTest="blend" position="10,165" size="214,675" />
			<widget name="wizard" conditional="wizard" pixmap="picon_default.png" position="1515,857" size="220,132" alphaTest="blend" />
			<widget name="indicatorU0" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU1" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU2" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU3" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU4" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU5" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU6" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU7" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU8" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU9" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU10" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU11" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU12" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU13" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU14" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorU15" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL0" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL1" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL2" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL3" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL4" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL5" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL6" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL7" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL8" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL9" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL10" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL11" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL12" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL13" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL14" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
			<widget name="indicatorL15" pixmap="skin_default/yellow_circle23x23.png" position="0,0" size="23,23" alphaTest="blend" offset="11,11" zPosition="11" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Rc.__init__(self)
		self.skinName = ["TimeWizard"]
		self.setTitle(_("Time Wizard"))
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self["text"] = Label()
		self["text"].setText(_("Press YELLOW button to set your schedule."))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_yellow"] = StaticText(_("Set local time"))
		self["wizard"] = Pixmap()
		self["lab1"] = StaticText(_("Openpli"))
		self["lab2"] = StaticText(_("Report problems to:"))
		self["lab3"] = StaticText(_("https://github.com/fairbird"))
		self["actions"] = ActionMap(["WizardActions", "ColorActions"], {
			"yellow": self.yellow,
			"ok": self.red,
			"red": self.red,
			"back": self.red
		}, -2)
		self.onLayoutFinish.append(self.selectKeys)
		self.updateTimeList()

	def selectKeys(self):
		self.clearSelectedKeys()
		self.selectKey("UP")
		self.selectKey("DOWN")
		self.selectKey("LEFT")
		self.selectKey("RIGHT")
		self.selectKey("RED")
		self.selectKey("YELLOW")

	def updateTimeList(self):
		self.list = []
		self.list.append((_("Time zone area"), config.timezone.area))
		self.list.append((_("Time zone"), config.timezone.val))
		self.list.append((_("Time synchronization method"), config.misc.SyncTimeUsing))
		self.list.append((_("pool.ntp.org"), config.misc.NTPserver))
		self.list.append((_("Sync NTP every (minutes)"), config.misc.useNTPminutes))
		if config.usage.date.enabled.value:
			self.list.append((_("Date style"), config.usage.date.dayfull))
			config.usage.date.dayfull.save()
		if config.usage.time.enabled.value:
			self.list.append((_("Time style"), config.usage.time.long))
			config.usage.time.long.save()
		config.misc.NTPserver.save()
		config.misc.useNTPminutes.save()
		config.misc.SyncTimeUsing.save()
		config.timezone.val.save()
		config.timezone.area.save()
		self["config"].list = self.list
		self["config"].setList(self.list)

	def useGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="status,message,timezone,proxy")
		if geolocationData.get("proxy", True):
			self["text"].setText(_("Geolocation is not available."))
			return
		tz = geolocationData.get("timezone", None)
		if not tz:
			self["text"].setText(_("Geolocation does not contain time zone information."))
		else:
			areaItem = None
			valItem = None
			for item in self["config"].list:
				if item[1] is config.timezone.area:
					areaItem = item
				if item[1] is config.timezone.val:
					valItem = item
			area, zone = tz.split("/", 1)
			config.timezone.area.value = area
			if areaItem:
				areaItem[1].changed()
			self["config"].invalidate(areaItem)
			config.timezone.val.value = zone
			if valItem:
				valItem[1].changed()
			self["config"].invalidate(valItem)
			self.updateTimeList()
			self["text"].setText(_("Your local time has been set successfully. Settings has been saved.\n\nPress \"OK\" to continue wizard."))

	def red(self):
		self.close()

	def yellow(self):
		self.useGeolocation()
