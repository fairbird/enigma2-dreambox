# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens import ChannelSelection
from ServiceReference import ServiceReference
from Components.config import config, ConfigSelection, ConfigText, ConfigSubList, ConfigDateTime, ConfigClock, ConfigYesNo
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Components.Button import Button
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.NimManager import nimmanager
from Components.SystemInfo import SystemInfo
from Components.UsageConfig import defaultMoviePath
from Screens.MovieSelection import getPreferredTagEditor
from Screens.LocationBox import MovieLocationBox
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.FallbackTimer import FallbackTimerDirs
from RecordTimer import AFTEREVENT
from enigma import eEPGCache, iRecordableServicePtr
from time import localtime, mktime, time, strftime
from datetime import datetime


class TimerEntry(ConfigListScreen, Screen):
	EMPTY = 0

	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer

		self.timer.service_ref_prev = self.timer.service_ref
		self.timer.begin_prev = self.timer.begin
		self.timer.end_prev = self.timer.end
		self.timer.external_prev = self.timer.external
		self.timer.dirname_prev = self.timer.dirname

		self.entryDate = None
		self.entryService = None
		self.key_red_choice = self.EMPTY

		if self.key_red_choice != Pixmap:
			self["key_red"] = StaticText(_("Cancel"))
			self["key_green"] = StaticText(_("Save"))
			self["key_yellow"] = StaticText(_("Timer type"))
			self["key_blue"] = StaticText("")
		if self.key_red_choice != StaticText:
			self["oktext"] = Label(_("OK"))
			self["canceltext"] = Label(_("Cancel"))
			self["ok"] = Pixmap()
			self["cancel"] = Pixmap()

		self["actions"] = NumberActionMap(["SetupActions", "GlobalActions", "PiPSetupActions", "ColorActions"],
		{
			"ok": self.keySelect,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"volumeUp": self.incrementStart,
			"volumeDown": self.decrementStart,
			"size+": self.incrementEnd,
			"size-": self.decrementEnd,
			"red": self.keyCancel,
			"green": self.keyGo,
			"yellow": self.changeTimerType,
			"blue": self.changeZapWakeupType
		}, -2)

		self.list = []

		ConfigListScreen.__init__(self, self.list, session=session)
		self.setTitle(_("Timer entry"))
		FallbackTimerDirs(self, self.createConfig)

	def createConfig(self, currlocation=None, locations=[]):
		justplay = self.timer.justplay
		always_zap = self.timer.always_zap
		zap_wakeup = self.timer.zap_wakeup
		pipzap = self.timer.pipzap
		rename_repeat = self.timer.rename_repeat
		conflict_detection = self.timer.conflict_detection

		afterevent = {
			AFTEREVENT.NONE: "nothing",
			AFTEREVENT.DEEPSTANDBY: "deepstandby",
			AFTEREVENT.STANDBY: "standby",
			AFTEREVENT.AUTO: "auto"
			}[self.timer.afterEvent]

		if self.timer.record_ecm and self.timer.descramble:
			recordingtype = "descrambled+ecm"
		elif self.timer.record_ecm:
			recordingtype = "scrambled+ecm"
		elif self.timer.descramble:
			recordingtype = "normal"

		weekday_table = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

		day = list([int(x) for x in reversed('{0:07b}'.format(self.timer.repeated))])
		weekday = 0
		if self.timer.repeated: # repeated
			type = "repeated"
			if (self.timer.repeated == 31): # Mon-Fri
				repeated = "weekdays"
			elif (self.timer.repeated == 127): # daily
				repeated = "daily"
			else:
				repeated = "user"
				if day.count(1) == 1:
					repeated = "weekly"
					weekday = day.index(1)
		else: # once
			type = "once"
			repeated = None
			weekday = int(strftime("%u", localtime(self.timer.begin))) - 1
			day[weekday] = 1
		self.timerentry_fallback = ConfigYesNo(default=self.timer.external_prev or config.usage.remote_fallback_external_timer.value and config.usage.remote_fallback.value and not nimmanager.somethingConnected())
		self.timerentry_justplay = ConfigSelection(choices=[
			("zap", _("zap")), ("record", _("record")), ("zap+record", _("zap and record"))],
			default={0: "record", 1: "zap", 2: "zap+record"}[justplay + 2 * always_zap])
		if SystemInfo["DeepstandbySupport"]:
			shutdownString = _("go to deep standby")
			choicelist = [("always", _("always")), ("from_standby", _("only from standby")), ("from_deep_standby", _("only from deep standby")), ("never", _("never"))]
		else:
			shutdownString = _("shut down")
			choicelist = [("always", _("always")), ("never", _("never"))]
		self.timerentry_zapwakeup = ConfigSelection(choices=choicelist, default=zap_wakeup)
		self.timerentry_afterevent = ConfigSelection(choices=[("nothing", _("do nothing")), ("standby", _("go to standby")), ("deepstandby", shutdownString), ("auto", _("auto"))], default=afterevent)
		self.timerentry_recordingtype = ConfigSelection(choices=[("normal", _("normal")), ("descrambled+ecm", _("descramble and record ecm")), ("scrambled+ecm", _("don't descramble, record ecm"))], default=recordingtype)
		self.timerentry_type = ConfigSelection(choices=[("once", _("once")), ("repeated", _("repeated"))], default=type)
		self.timerentry_name = ConfigText(default=self.timer.name, visible_width=50, fixed_size=False)
		self.timerentry_description = ConfigText(default=self.timer.description, visible_width=50, fixed_size=False)
		self.timerentry_tags = self.timer.tags[:]
		self.timerentry_tagsset = ConfigSelection(choices=[not self.timerentry_tags and _("None") or " ".join(self.timerentry_tags)])

		self.timerentry_repeated = ConfigSelection(default=repeated, choices=[("weekly", _("weekly")), ("daily", _("daily")), ("weekdays", _("Mon-Fri")), ("user", _("user defined"))])
		self.timerentry_renamerepeat = ConfigYesNo(default=rename_repeat)
		self.timerentry_pipzap = ConfigYesNo(default=pipzap)
		self.timerentry_conflictdetection = ConfigYesNo(default=conflict_detection)

		self.timerentry_date = ConfigDateTime(default = self.timer.begin, formatstring = config.usage.date.full.value, increment = 86400)
		self.timerentry_starttime = ConfigClock(default=self.timer.begin)
		self.timerentry_endtime = ConfigClock(default=self.timer.end)
		self.timerentry_showendtime = ConfigSelection(default=((self.timer.end - self.timer.begin) > 4), choices=[(True, _("yes")), (False, _("no"))])

		default = not self.timer.external_prev and self.timer.dirname or defaultMoviePath()
		tmp = config.movielist.videodirs.value
		if default not in tmp:
			tmp.append(default)
		self.timerentry_dirname = ConfigSelection(default=default, choices=tmp)

		default = self.timer.external_prev and self.timer.dirname or currlocation
		if default not in locations:
			locations.append(default)
		self.timerentry_fallbackdirname = ConfigSelection(default=default, choices=locations)

		self.timerentry_repeatedbegindate = ConfigDateTime(default = self.timer.repeatedbegindate, formatstring = config.usage.date.full.value, increment = 86400)

		self.timerentry_weekday = ConfigSelection(default=weekday_table[weekday], choices=[("mon", _("Monday")), ("tue", _("Tuesday")), ("wed", _("Wednesday")), ("thu", _("Thursday")), ("fri", _("Friday")), ("sat", _("Saturday")), ("sun", _("Sunday"))])

		self.timerentry_day = ConfigSubList()
		for x in (0, 1, 2, 3, 4, 5, 6):
			self.timerentry_day.append(ConfigYesNo(default=day[x]))

		# FIXME some service-chooser needed here
		servicename = "N/A"
		try: # no current service available?
			servicename = str(self.timer.service_ref.getServiceName())
		except:
			pass
		self.timerentry_service_ref = self.timer.service_ref
		self.timerentry_service = ConfigSelection([servicename])
		self.createSetup("config")

	def createSetup(self, widget):
		self.list = []
		self.entryFallbackTimer = (_("Fallback Timer"), self.timerentry_fallback)
		if config.usage.remote_fallback_external_timer.value and config.usage.remote_fallback.value and not hasattr(self, "timerentry_remote"):
			self.list.append(self.entryFallbackTimer)
		self.entryName = (_("Name"), self.timerentry_name)
		self.list.append(self.entryName)
		self.entryDescription = (_("Description"), self.timerentry_description)
		self.list.append(self.entryDescription)
		self.timerJustplayEntry = (_("Timer type"), self.timerentry_justplay)
		if config.usage.setup_level.index >= 1:
			self.list.append(self.timerJustplayEntry)
		self.timerTypeEntry = (_("Repeat type"), self.timerentry_type)
		self.list.append(self.timerTypeEntry)

		if self.timerentry_type.value == "once":
			self.frequencyEntry = None
		else: # repeated
			self.frequencyEntry = (_("Repeats"), self.timerentry_repeated)
			self.list.append(self.frequencyEntry)
			self.repeatedbegindateEntry = (_("Starting on"), self.timerentry_repeatedbegindate)
			self.list.append(self.repeatedbegindateEntry)
			if self.timerentry_repeated.value == "daily":
				pass
			if self.timerentry_repeated.value == "weekdays":
				pass
			if self.timerentry_repeated.value == "weekly":
				self.list.append((_("Weekday"), self.timerentry_weekday))

			if self.timerentry_repeated.value == "user":
				self.list.append((_("Monday"), self.timerentry_day[0]))
				self.list.append((_("Tuesday"), self.timerentry_day[1]))
				self.list.append((_("Wednesday"), self.timerentry_day[2]))
				self.list.append((_("Thursday"), self.timerentry_day[3]))
				self.list.append((_("Friday"), self.timerentry_day[4]))
				self.list.append((_("Saturday"), self.timerentry_day[5]))
				self.list.append((_("Sunday"), self.timerentry_day[6]))
			if self.timerentry_justplay.value != "zap":
				self.list.append((_("Rename name and description for new events"), self.timerentry_renamerepeat))

		self.entryDate = (_("Date"), self.timerentry_date)
		if self.timerentry_type.value == "once":
			self.list.append(self.entryDate)

		self.entryStartTime = (_("Start time"), self.timerentry_starttime)
		self.list.append(self.entryStartTime)

		self.entryShowEndTime = (_("Set end time"), self.timerentry_showendtime)
		self.entryZapWakeup = (_("Wakeup receiver for start timer"), self.timerentry_zapwakeup)
		if self.timerentry_justplay.value == "zap":
			self.list.append(self.entryZapWakeup)
			if SystemInfo["PIPAvailable"]:
				self.list.append((_("Use as PiP if possible"), self.timerentry_pipzap))
			self.list.append(self.entryShowEndTime)
			self["key_blue"].setText(_("Wakeup type"))
		else:
			self["key_blue"].setText("")
		self.entryEndTime = (_("End time"), self.timerentry_endtime)
		if self.timerentry_justplay.value != "zap" or self.timerentry_showendtime.value:
			self.list.append(self.entryEndTime)

		self.channelEntry = (_("Channel"), self.timerentry_service)
		self.list.append(self.channelEntry)

		self.dirname = (_("Location"), self.timerentry_fallbackdirname) if self.timerentry_fallback.value and self.timerentry_fallbackdirname.value else (_("Location"), self.timerentry_dirname)
		if config.usage.setup_level.index >= 2 and ((self.timerentry_fallback.value and self.timerentry_fallbackdirname.value) or (self.timerentry_justplay.value != "zap" and self.timerentry_dirname.value)): # expert+
			self.list.append(self.dirname)

		self.conflictDetectionEntry = (_("Enable timer conflict detection"), self.timerentry_conflictdetection)
		if not self.timerentry_fallback.value:
			self.list.append(self.conflictDetectionEntry)

		self.tagsSet = (_("Tags"), self.timerentry_tagsset)
		if self.timerentry_justplay.value != "zap" and not self.timerentry_fallback.value:
			if getPreferredTagEditor():
				self.list.append(self.tagsSet)
			self.list.append((_("After event"), self.timerentry_afterevent))
			self.list.append((_("Recording type"), self.timerentry_recordingtype))

		self[widget].list = self.list

	def newConfig(self):
		print("[TimerEdit] newConfig", self["config"].getCurrent())
		if self["config"].getCurrent() in (self.timerTypeEntry, self.timerJustplayEntry, self.frequencyEntry, self.entryShowEndTime, self.entryFallbackTimer):
			self.createSetup("config")

	def keyLeft(self):
		cur = self["config"].getCurrent()
		if cur in (self.channelEntry, self.tagsSet):
			self.keySelect()
		elif cur in (self.entryName, self.entryDescription):
			self.renameEntry()
		else:
			ConfigListScreen.keyLeft(self)
			self.newConfig()

	def keyRight(self):
		cur = self["config"].getCurrent()
		if cur in (self.channelEntry, self.tagsSet):
			self.keySelect()
		elif cur in (self.entryName, self.entryDescription):
			self.renameEntry()
		else:
			ConfigListScreen.keyRight(self)
			self.newConfig()

	def renameEntry(self):
		cur = self["config"].getCurrent()
		if cur == self.entryName:
			title_text = _("Please enter new name:")
			old_text = self.timerentry_name.value
		else:
			title_text = _("Please enter new description:")
			old_text = self.timerentry_description.value
		self.session.openWithCallback(self.renameEntryCallback, VirtualKeyBoard, title=title_text, text=old_text)

	def renameEntryCallback(self, answer):
		if answer:
			cur = self["config"].getCurrent()
			if cur == self.entryName:
				self.timerentry_name.value = answer
				self["config"].invalidate(self.entryName)
			else:
				self.timerentry_description.value = answer
				self["config"].invalidate(self.entryDescription)

	def handleKeyFileCallback(self, answer):
		if self["config"].getCurrent() in (self.channelEntry, self.tagsSet):
			self.keySelect()
		else:
			ConfigListScreen.handleKeyFileCallback(self, answer)
			self.newConfig()

	def openMovieLocationBox(self, answer=""):
		self.session.openWithCallback(
			self.pathSelected,
			MovieLocationBox,
			_("Select target folder"),
			self.timerentry_dirname.value,
			filename=answer,
			minFree=100 # We require at least 100MB free space
			)

	def keySelect(self):
		cur = self["config"].getCurrent()
		if cur == self.channelEntry:
			self.session.openWithCallback(
				self.finishedChannelSelection,
				ChannelSelection.SimpleChannelSelection,
				_("Select channel to record from"),
				currentBouquet=True
			)
		elif cur == self.dirname:
			menu = [(_("Open select location"), "empty")]
			if self.timerentry_type.value == "repeated" and self.timerentry_name.value:
				menu.append((_("Open select location as timer name"), "timername"))
			if len(menu) == 1:
				self.openMovieLocationBox()
			elif len(menu) == 2:
				text = _("Select action")

				def selectAction(choice):
					if choice:
						if choice[1] == "timername":
							self.openMovieLocationBox(self.timerentry_name.value)
						elif choice[1] == "empty":
							self.openMovieLocationBox()
				self.session.openWithCallback(selectAction, ChoiceBox, title=text, list=menu)

		elif getPreferredTagEditor() and cur == self.tagsSet:
			self.session.openWithCallback(
				self.tagEditFinished,
				getPreferredTagEditor(),
				self.timerentry_tags
			)
		else:
			self.keyGo()

	def finishedChannelSelection(self, *args):
		if args:
			self.timerentry_service_ref = ServiceReference(args[0])
			self.timerentry_service.setCurrentText(self.timerentry_service_ref.getServiceName())
			self["config"].invalidate(self.channelEntry)

	def getTimestamp(self, date, mytime):
		d = localtime(date)
		dt = datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(mktime(dt.timetuple()))

	def getBeginEnd(self):
		date = self.timerentry_date.value
		endtime = self.timerentry_endtime.value
		starttime = self.timerentry_starttime.value

		begin = self.getTimestamp(date, starttime)
		end = self.getTimestamp(date, endtime)

		# if the endtime is less than the starttime, add 1 day.
		if end < begin:
			end += 86400
		return begin, end

	def selectChannelSelector(self, *args):
		self.session.openWithCallback(
				self.finishedChannelSelectionCorrection,
				ChannelSelection.SimpleChannelSelection,
				_("Select channel to record from")
			)

	def finishedChannelSelectionCorrection(self, *args):
		if args:
			self.finishedChannelSelection(*args)
			self.keyGo()

	def RemoteSubserviceSelected(self, service):
		if service:
			# ouch, this hurts a little
			service_ref = timerentry_service_ref
			self.timerentry_service_ref = ServiceReference(service[1])
			eit = self.timer.eit
			self.timer.eit = None
			self.keyGo()
			self.timerentry_service_ref = service_ref
			self.timer.eit = eit

	def keyGo(self, result=None):
		if not self.timerentry_service_ref.isRecordable():
			self.session.openWithCallback(self.selectChannelSelector, MessageBox, _("You didn't select a channel to record from."), MessageBox.TYPE_ERROR)
		else:
			self.timer.external = self.timerentry_fallback.value
			self.timer.name = self.timerentry_name.value
			self.timer.description = self.timerentry_description.value
			self.timer.justplay = self.timerentry_justplay.value == "zap"
			self.timer.always_zap = self.timerentry_justplay.value == "zap+record"
			self.timer.zap_wakeup = self.timerentry_zapwakeup.value
			self.timer.pipzap = self.timerentry_pipzap.value
			self.timer.rename_repeat = self.timerentry_renamerepeat.value
			self.timer.conflict_detection = self.timerentry_conflictdetection.value
			if self.timerentry_justplay.value == "zap":
				if not self.timerentry_showendtime.value:
					self.timerentry_endtime.value = self.timerentry_starttime.value
					self.timerentry_afterevent.value = "nothing"
			self.timer.resetRepeated()
			self.timer.afterEvent = {
				"nothing": AFTEREVENT.NONE,
				"deepstandby": AFTEREVENT.DEEPSTANDBY,
				"standby": AFTEREVENT.STANDBY,
				"auto": AFTEREVENT.AUTO
				}[self.timerentry_afterevent.value]
			self.timer.descramble = {
				"normal": True,
				"descrambled+ecm": True,
				"scrambled+ecm": False,
				}[self.timerentry_recordingtype.value]
			self.timer.record_ecm = {
				"normal": False,
				"descrambled+ecm": True,
				"scrambled+ecm": True,
				}[self.timerentry_recordingtype.value]
			self.timer.service_ref = self.timerentry_service_ref
			self.timer.tags = self.timerentry_tags

			# reset state when edit timer type
			if not self.timer.external and self.timer.justplay != "zap" and self.timer.isRunning():
				if self.timer in self.session.nav.RecordTimer.timer_list and (not self.timer.record_service or not isinstance(self.timer.record_service, iRecordableServicePtr)):
					self.timer.resetState()

			if self.timerentry_fallback.value:
				self.timer.dirname = self.timerentry_fallbackdirname.value
			else:
				if self.timer.dirname or self.timerentry_dirname.value != defaultMoviePath():
					self.timer.dirname = self.timerentry_dirname.value
					config.movielist.last_timer_videodir.value = self.timer.dirname
					config.movielist.last_timer_videodir.save()

			if self.timerentry_type.value == "once":
				self.timer.begin, self.timer.end = self.getBeginEnd()
			if self.timerentry_type.value == "repeated":
				if self.timerentry_repeated.value == "daily":
					for x in (0, 1, 2, 3, 4, 5, 6):
						self.timer.setRepeated(x)

				if self.timerentry_repeated.value == "weekly":
					self.timer.setRepeated(self.timerentry_weekday.index)

				if self.timerentry_repeated.value == "weekdays":
					for x in (0, 1, 2, 3, 4):
						self.timer.setRepeated(x)

				if self.timerentry_repeated.value == "user":
					for x in (0, 1, 2, 3, 4, 5, 6):
						if self.timerentry_day[x].value:
							self.timer.setRepeated(x)

				self.timer.repeatedbegindate = self.getTimestamp(self.timerentry_repeatedbegindate.value, self.timerentry_starttime.value)
				if self.timer.repeated:
					self.timer.begin = self.getTimestamp(self.timerentry_repeatedbegindate.value, self.timerentry_starttime.value)
					self.timer.end = self.getTimestamp(self.timerentry_repeatedbegindate.value, self.timerentry_endtime.value)
				else:
					self.timer.begin = self.getTimestamp(time(), self.timerentry_starttime.value)
					self.timer.end = self.getTimestamp(time(), self.timerentry_endtime.value)

				# when a timer end is set before the start, add 1 day
				if self.timer.end < self.timer.begin:
					self.timer.end += 86400

			if self.timer.eit is not None:
				event = eEPGCache.getInstance().lookupEventId(self.timer.service_ref.ref, self.timer.eit)
				if event:
					n = event.getNumOfLinkageServices()
					if n > 1:
						tlist = []
						ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
						parent = self.timer.service_ref.ref
						selection = 0
						for x in range(n):
							i = event.getLinkageService(parent, x)
							if i.toString() == ref.toString():
								selection = x
							tlist.append((i.getName(), i))
						self.session.openWithCallback(self.subserviceSelected, ChoiceBox, title=_("Please select a subservice to record..."), list=tlist, selection=selection)
						return
					elif n > 0:
						parent = self.timer.service_ref.ref
						self.timer.service_ref = ServiceReference(event.getLinkageService(parent, 0))
			self.saveTimer()
			self.close((True, self.timer))

	def changeTimerType(self):
		self.timerentry_justplay.selectNext()
		self.timerJustplayEntry = (_("Timer type"), self.timerentry_justplay)
		self["config"].invalidate(self.timerJustplayEntry)
		self.createSetup("config")

	def changeZapWakeupType(self):
		if self.timerentry_justplay.value == "zap":
			self.timerentry_zapwakeup.selectNext()
			self["config"].invalidate(self.entryZapWakeup)

	def incrementStart(self):
		self.timerentry_starttime.increment()
		self["config"].invalidate(self.entryStartTime)
		if self.timerentry_type.value == "once" and self.timerentry_starttime.value == [0, 0]:
			self.timerentry_date.value += 86400
			self["config"].invalidate(self.entryDate)

	def decrementStart(self):
		self.timerentry_starttime.decrement()
		self["config"].invalidate(self.entryStartTime)
		if self.timerentry_type.value == "once" and self.timerentry_starttime.value == [23, 59]:
			self.timerentry_date.value -= 86400
			self["config"].invalidate(self.entryDate)

	def incrementEnd(self):
		if self.entryEndTime is not None:
			self.timerentry_endtime.increment()
			self["config"].invalidate(self.entryEndTime)

	def decrementEnd(self):
		if self.entryEndTime is not None:
			self.timerentry_endtime.decrement()
			self["config"].invalidate(self.entryEndTime)

	def subserviceSelected(self, service):
		if not service is None:
			self.timer.service_ref = ServiceReference(service[1])
		self.saveTimer()
		self.close((True, self.timer))

	def saveTimer(self):
		self.session.nav.RecordTimer.saveTimer()

	def keyCancel(self):
		self.close((False,))

	def pathSelected(self, res):
		if res is not None:
			if config.movielist.videodirs.value != self.timerentry_dirname.choices:
				self.timerentry_dirname.setChoices(config.movielist.videodirs.value, default=res)
			self.timerentry_dirname.value = res

	def tagEditFinished(self, ret):
		if ret is not None:
			self.timerentry_tags = ret
			self.timerentry_tagsset.setChoices([not ret and _("None") or " ".join(ret)])
			self["config"].invalidate(self.tagsSet)


class TimerLog(Screen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer
		self.log_entries = self.timer.log_entries[:]

		self.fillLogList()

		self["loglist"] = MenuList(self.list)
		self["logentry"] = Label()

		self["key_red"] = StaticText(_("Delete entry"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(_("Clear log"))

		self.onShown.append(self.updateText)

		self["actions"] = NumberActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
		{
			"ok": self.keyClose,
			"cancel": self.keyClose,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"red": self.deleteEntry,
			"blue": self.clearLog
		}, -1)
		self.setTitle(_("Timer log"))

	def deleteEntry(self):
		cur = self["loglist"].getCurrent()
		if cur is None:
			return
		self.log_entries.remove(cur[1])
		self.fillLogList()
		self["loglist"].l.setList(self.list)
		self.updateText()

	def fillLogList(self):
		self.list = [(str(strftime(config.usage.date.daylong.value + " " + config.usage.time.short.value, localtime(x[0])) + " - " + x[2]), x) for x in self.log_entries]

	def clearLog(self):
		self.log_entries = []
		self.fillLogList()
		self["loglist"].l.setList(self.list)
		self.updateText()

	def keyClose(self):
		if self.timer.log_entries != self.log_entries:
			self.timer.log_entries = self.log_entries
			self.close((True, self.timer))
		else:
			self.close((False,))

	def up(self):
		self["loglist"].instance.moveSelection(self["loglist"].instance.moveUp)
		self.updateText()

	def down(self):
		self["loglist"].instance.moveSelection(self["loglist"].instance.moveDown)
		self.updateText()

	def left(self):
		self["loglist"].instance.moveSelection(self["loglist"].instance.pageUp)
		self.updateText()

	def right(self):
		self["loglist"].instance.moveSelection(self["loglist"].instance.pageDown)
		self.updateText()

	def updateText(self):
		if self.list:
			self["logentry"].setText(str(self["loglist"].getCurrent()[1][2]))
		else:
			self["logentry"].setText("")
