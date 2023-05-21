# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens import ChannelSelection
import Screens.InfoBar
from Components.config import config, ConfigClock
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.EpgList import EPGList, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR, EPG_TYPE_MULTI, EPG_TYPE_PARTIAL
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.UsageConfig import preferredTimerPath
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Components.Sources.Event import Event
from Screens.ChoiceBox import ChoiceBox
from Screens.TimerEdit import TimerSanityConflict, TimerEditList
from Screens.EventView import EventViewSimple
from Screens.TimeDateInput import TimeDateInput
from enigma import eServiceReference
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT, createRecordTimerEntry
from Screens.TimerEntry import TimerEntry
from ServiceReference import ServiceReference
from time import localtime, time, strftime
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Tools.BoundFunction import boundFunction
from Tools.FallbackTimer import FallbackTimerList
from Components.Button import Button
from Tools.Directories import isPluginInstalled
from Screens.MessageBox import MessageBox
from Components.Console import Console

mepg_config_initialized = False


class EPGSelection(Screen):
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2

	ZAP = 1

	def __init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None, parent=None):
		Screen.__init__(self, session)
		self.bouquetChangeCB = bouquetChangeCB
		self.serviceChangeCB = serviceChangeCB
		self.ask_time = -1 #now
		self["key_red"] = StaticText("")
		self.closeRecursive = False
		self.saved_title = None
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		self.Console = Console()
		if isinstance(service, str) and eventid is not None:
			self.type = EPG_TYPE_SIMILAR
			self.setTitle(_("Similar EPG"))
			self["key_yellow"] = StaticText(_("Partial"))
			self["key_blue"] = StaticText()
			self.currentService = service
			self.eventid = eventid
			self.zapFunc = None
		elif not service and isinstance(eventid, str):
			self.type = EPG_TYPE_PARTIAL
			self.title = _("Partial EPG")
			self["key_yellow"] = StaticText()
			self["key_blue"] = StaticText()
			self.currentService = service
			self.eventid = eventid
			self.zapFunc = None
		elif isinstance(service, eServiceReference) or isinstance(service, str):
			self.setTitle(_("Single EPG"))
			self.type = EPG_TYPE_SINGLE
			self["key_yellow"] = StaticText()
			self["key_blue"] = StaticText(_("Select Channel"))
			self.currentService = ServiceReference(service)
			self.zapFunc = zapFunc
			self.sort_type = 0
			self.setSortDescription()
		else:
			self.setTitle(_("Multi EPG"))
			self.skinName = "EPGSelectionMulti"
			self.type = EPG_TYPE_MULTI
			if self.bouquetChangeCB == StaticText:
				self["key_yellow"] = StaticText(pgettext("button label, 'previous screen'", "Prev"))
				self["key_blue"] = StaticText(pgettext("button label, 'next screen'", "Next"))
			else:
				self["key_yellow"] = Button(pgettext("button label, 'previous screen'", "Prev"))
				self["key_blue"] = Button(pgettext("button label, 'next screen'", "Next"))
			self["now_button"] = Pixmap()
			self["next_button"] = Pixmap()
			self["more_button"] = Pixmap()
			self["now_button_sel"] = Pixmap()
			self["next_button_sel"] = Pixmap()
			self["more_button_sel"] = Pixmap()
			self["now_text"] = Label()
			self["next_text"] = Label()
			self["more_text"] = Label()
			self["date"] = Label()
			self.services = service
			self.zapFunc = zapFunc
		self.parent = parent
		if self.bouquetChangeCB == StaticText:
			self["key_green"] = StaticText(_("Add timer"))
		else:
			self["key_green"] = Button(_("Add timer"))
		self.key_green_choice = self.ADD_TIMER
		self.key_red_choice = self.EMPTY
		self["list"] = EPGList(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)

		self["actions"] = ActionMap(["EPGSelectActions", "OkCancelActions"],
			{
				"cancel": self.closeScreen,
				"ok": self.eventSelected,
				"timerAdd": self.timerAdd,
				"yellow": self.yellowButtonPressed,
				"blue": self.blueButtonPressed,
				"info": self.infoKeyPressed,
				"menu": self.furtherOptions,
				"nextBouquet": self.nextBouquet, # just used in multi epg yet
				"prevBouquet": self.prevBouquet, # just used in multi epg yet
				"nextService": self.nextService, # just used in single epg yet
				"prevService": self.prevService, # just used in single epg yet
				"preview": self.eventPreview,
			})

		self['colouractions'] = HelpableActionMap(self, ["ColorActions"],
			{
				"red": (self.GoToTmbd, _("Search event in TMBD"))
			})

		self.isTMBD = isPluginInstalled("TMBD")
		if self.isTMBD:
			self["key_red"] = Button(_("Search TMBD"))
			self.select = True
		if not self.isTMBD:
			self["key_red"] = Button(_("TMBD Not Installed"))
			self.select = False
		try:
			from Plugins.Extensions.YTTrailer.plugin import baseEPGSelection__init__
			description = _("Search yt-trailer for event")
		except ImportError as ie:
			pass
		else:
			if baseEPGSelection__init__ is not None:
				self["trailerActions"] = ActionMap(["InfobarActions", "InfobarTeletextActions"],
				{
					"showTv": self.showTrailer,
					"showRadio": self.showTrailerList,
					"startTeletext": self.showConfig
				})
		self["actions"].csel = self
		if parent and hasattr(parent, "fallbackTimer"):
			self.fallbackTimer = parent.fallbackTimer
			self.onLayoutFinish.append(self.onCreate)
		else:
			self.fallbackTimer = FallbackTimerList(self, self.onCreate)

	def GoToTmbd(self):
		if isPluginInstalled("TMBD"):
			self.runTMBD()
		else:
			self.session.openWithCallback(self.doInstall, MessageBox, _('The TMBD plugin is not installed!\nDo you want to install it?'), MessageBox.TYPE_YESNO)

	def runTMBD(self):
		if isPluginInstalled("TMBD"):
			from Plugins.Extensions.TMBD.plugin import TMBD
			description = _("TMBD Details")
			description = _("TMBD details for event")
			description = _("Query details from the Internet Movie Database")
			cur = self["list"].getCurrent()
			if cur[0] is not None:
				name2 = cur[0].getEventName() or ''
				name3 = name2.split("(")[0].strip()
				eventname = name3.replace('"', '').replace('', '').replace('.', '')
				eventname = eventname.replace('', '')
				try:
					tmbdsearch = config.plugins.tmbd.profile.value
				except:
					tmbdsearch = None
				if tmbdsearch is not None:
					if config.plugins.tmbd.profile.value == "0":
						self.session.open(TMBD, eventname, False)
					else:
						try:
							from Plugins.Extensions.TMBD.plugin import KinoRu
							self.session.open(KinoRu, eventname, False)
						except:
							pass
				else:
					self.session.open(TMBD, eventname, False)

	def doInstall(self, val):
		if val:
			self.message = self.session.open(MessageBox, _("Please wait..."), MessageBox.TYPE_INFO, enable_input=False)
			self.message.setTitle(_('Installing TMBD'))
			self.Console.ePopen('opkg update && opkg install enigma2-plugin-extensions-tmbd', self.installComplete)
		else:
			self.close()

	def installComplete(self, str, retval, extra_args):
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("Seems internet connection down, Or TMBD Plugin not on feed."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
			self.message.close()
		else:
			self.message.close()
			self.close()

	def nextBouquet(self):
		if self.type == EPG_TYPE_SINGLE:
			self.session.openWithCallback(self.channelSelectionCallback, ChannelSelection.SimpleChannelSelection, _("Select channel"), True, True, self.currentService.ref, self.parent and self.parent.epg_bouquet)
		if self.bouquetChangeCB:
			self.bouquetChangeCB(1, self)

	def prevBouquet(self):
		if self.type == EPG_TYPE_SINGLE:
			self.session.openWithCallback(self.channelSelectionCallback, ChannelSelection.SimpleChannelSelection, _("Select channel"), True, True, self.currentService.ref, self.parent and self.parent.epg_bouquet)
		if self.bouquetChangeCB:
			self.bouquetChangeCB(-1, self)

	def nextService(self):
		if self.serviceChangeCB:
			self.serviceChangeCB(1, self)

	def prevService(self):
		if self.serviceChangeCB:
			self.serviceChangeCB(-1, self)

	def enterDateTime(self):
		if self.type == EPG_TYPE_MULTI:
			global mepg_config_initialized
			if not mepg_config_initialized:
				config.misc.prev_mepg_time = ConfigClock(default=time())
				mepg_config_initialized = True
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.misc.prev_mepg_time)

	def furtherOptions(self):
		menu = []
		text = _("Select action")
		event = self["list"].getCurrent()[0]
		if event:
			menu = [(p.name, boundFunction(self.runPlugin, p)) for p in plugins.getPlugins(where=PluginDescriptor.WHERE_EVENTINFO)
				if 'selectedevent' in p.fnc.__code__.co_varnames]
			if menu:
				text += ": %s" % event.getEventName()
		if self.type == EPG_TYPE_MULTI:
			menu.append((_("Goto specific date/time"), self.enterDateTime))
		menu.append((_("Timer Overview"), self.openTimerOverview))
		if len(menu) == 1:
			menu and menu[0][1]()
		elif len(menu) > 1:
			def boxAction(choice):
				if choice:
					choice[1]()
			self.session.openWithCallback(boxAction, ChoiceBox, title=text, list=menu, windowTitle=_("Further options"))

	def runPlugin(self, plugin):
		event = self["list"].getCurrent()
		plugin(session=self.session, selectedevent=event)

	def openTimerOverview(self):
		self.session.open(TimerEditList)

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				self.ask_time = ret[1]
				self["list"].fillMultiEPG(self.services, ret[1])

	def closeScreen(self):
		if self.zapFunc:
			self.zapFunc(None, zapback=True)
		self.close(self.closeRecursive)

	def infoKeyPressed(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None:
			if self.type != EPG_TYPE_SIMILAR:
				self.session.open(EventViewSimple, event, service, self.eventViewCallback, self.openSimilarList, parent=self.parent)
			else:
				self.session.open(EventViewSimple, event, service, self.eventViewCallback, parent=self.parent)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def setServices(self, services):
		self.services = services
		self.onCreate()

	def setService(self, service):
		self.currentService = service
		self.onCreate()

	#just used in multipeg
	def onCreate(self):
		li = self["list"]
		li.recalcEntrySize()
		if self.type == EPG_TYPE_MULTI:
			li.fillMultiEPG(self.services, self.ask_time)
			li.moveToService(Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.instance.servicelist.getCurrentSelection() or self.session.nav.getCurrentlyPlayingServiceOrGroup())
		elif self.type == EPG_TYPE_SINGLE:
			service = self.currentService
			self["Service"].newService(service.ref)
			if not self.saved_title:
				self.saved_title = self.instance.getTitle()
			self.setTitle(self.saved_title + ' - ' + service.getServiceName())
			li.fillSingleEPG(service)
		elif self.type == EPG_TYPE_PARTIAL:
			li.fill_partial_list(self.eventid)
		else:
			li.fillSimilarList(self.currentService, self.eventid)

	def eventViewCallback(self, setEvent, setService, val):
		l = self["list"]
		old = l.getCurrent()
		if val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		cur = l.getCurrent()
		if self.type == EPG_TYPE_MULTI and cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])

	def zapTo(self):
		if self.key_red_choice == self.ZAP and self.zapFunc:
			self.closeRecursive = True
			from Components.ServiceEventTracker import InfoBarCount
			if InfoBarCount > 1:
				self.eventPreview()
			else:
				self.zapSelectedService()
				self.close(self.closeRecursive)

	def zapSelectedService(self, prev=False):
		lst = self["list"]
		count = lst.getCurrentChangeCount()
		if count == 0:
			ref = lst.getCurrent()[1]
			if ref is not None:
				self.zapFunc(ref.ref, preview=prev)

	def eventPreview(self):
		if self.zapFunc:
			# if enabled, then closed whole EPG with EXIT:
			# self.closeRecursive = True
			self.zapSelectedService(True)

	def eventSelected(self):
		if self.skinName == "EPGSelectionMulti":
			cur = self["list"].getCurrent()
			event = cur[0]
			ref = cur[1] and cur[1].ref.toString()
			if ref and event:
				self.session.open(EPGSelection, ref)
		else:
			self.infoKeyPressed()

	def yellowButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(-1)
		elif self.type == EPG_TYPE_SINGLE:
			if self.sort_type == 0:
				self.sort_type = 1
			else:
				self.sort_type = 0
			self["list"].sortSingleEPG(self.sort_type)
			self.setSortDescription()
		elif self.type == EPG_TYPE_SIMILAR:
			cur = self["list"].getCurrent()
			cur_event = cur and cur[0]
			event = cur_event and cur_event.getEventName()
			if event:
				self.session.open(EPGSelection, None, None, event)

	def setSortDescription(self):
		if self.sort_type == 1:
			# TRANSLATORS: This must fit into the header button in the EPG-List
			self["key_yellow"].setText(_("Sort time"))
		else:
			# TRANSLATORS: This must fit into the header button in the EPG-List
			self["key_yellow"].setText(_("Sort A-Z"))

	def blueButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(1)
		if self.type == EPG_TYPE_SINGLE:
			self.session.openWithCallback(self.channelSelectionCallback, ChannelSelection.SimpleChannelSelection, _("Select channel"), True, True, self.currentService.ref, self.parent and self.parent.epg_bouquet)

	def channelSelectionCallback(self, *args):
		if args and len(args) == 2:
			serviceref, bouquetref = args[:2]
			if self.parent:
				self.parent.selectBouquet(bouquetref, self)
			self.setService(ServiceReference(serviceref))

	def removeTimer(self, timer):
		if timer.external:
			self.fallbackTimer.removeTimer(timer, self.onSelectionChanged)
		else:
			timer.afterEvent = AFTEREVENT.NONE
			self.session.nav.RecordTimer.removeEntry(timer)
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER

	def disableTimer(self, timer, state, repeat=False, record=False):
		if repeat:
			if record:
				title_text = _("A repeating event is currently recording. What would you like to do?")
				menu = [(_("Stop current event but not coming events"), "stoponlycurrent"), (_("Stop current event and disable coming events"), "stopall")]
				if not timer.disabled:
					menu.append((_("Don't stop current event but disable coming events"), "stoponlycoming"))
			else:
				title_text = _("Attention, this is repeated timer!\nWhat do you want to do?")
				menu = [(_("Disable current event but not coming events"), "nextonlystop"), (_("Disable timer"), "simplestop")]
			self.session.openWithCallback(boundFunction(self.runningEventCallback, timer, state), ChoiceBox, title=title_text, list=menu)
		elif timer.state == state:
			if timer.external:
				self.fallbackTimer.toggleTimer(timer, self.onSelectionChanged)
			else:
				timer.disable()
				self.session.nav.RecordTimer.timeChanged(timer)
				self["key_green"].setText(_("Add timer"))
				self.key_green_choice = self.ADD_TIMER

	def runningEventCallback(self, t, state, result):
		if result is not None and t.state == state:
			findNextRunningEvent = True
			findEventNext = False
			if result[1] == "nextonlystop":
				findEventNext = True
				t.disable()
				self.session.nav.RecordTimer.timeChanged(t)
				t.processRepeated(findNextEvent=True)
				t.enable()
			if result[1] in ("stoponlycurrent", "stopall"):
				findNextRunningEvent = False
				t.enable()
				t.processRepeated(findRunningEvent=False)
				self.session.nav.RecordTimer.doActivate(t)
			if result[1] in ("stoponlycoming", "stopall", "simplestop"):
				findNextRunningEvent = True
				t.disable()
			self.session.nav.RecordTimer.timeChanged(t)
			t.findRunningEvent = findNextRunningEvent
			t.findNextEvent = findEventNext
			if result[1] in ("stoponlycurrent", "stopall", "simplestop", "nextonlystop"):
				self["key_green"].setText(_("Add timer"))
				self.key_green_choice = self.ADD_TIMER

	def timerAdd(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		if event is None:
			return
		serviceref = cur[1]
		isRecordEvent = isRepeat = firstNextRepeatEvent = isRunning = False
		eventid = event.getEventId()
		begin = event.getBeginTime()
		end = begin + event.getDuration()
		refstr = ':'.join(serviceref.ref.toString().split(':')[:11])
		for timer in self.session.nav.RecordTimer.getAllTimersList():
			needed_ref = ':'.join(timer.service_ref.ref.toString().split(':')[:11]) == refstr
			if needed_ref and timer.eit == eventid and (begin < timer.begin <= end or timer.begin <= begin <= timer.end):
				isRecordEvent = True
				break
			elif needed_ref and timer.repeated and self.session.nav.RecordTimer.isInRepeatTimer(timer, event):
				isRecordEvent = True
				break
		if isRecordEvent:
			isRepeat = timer.repeated
			prev_state = timer.state
			isRunning = prev_state in (1, 2)
			title_text = isRepeat and _("Attention, this is repeated timer!\n") or ""
			firstNextRepeatEvent = isRepeat and (begin < timer.begin <= end or timer.begin <= begin <= timer.end) and not timer.justplay
			menu = [(_("Delete timer"), "delete"), (_("Edit timer"), "edit")]
			buttons = ["red", "green"]
			if not isRunning:
				if firstNextRepeatEvent and timer.isFindRunningEvent() and not timer.isFindNextEvent():
					menu.append((_("Options disable timer"), "disablerepeat"))
				else:
					menu.append((_("Disable timer"), "disable"))
				buttons.append("yellow")
			elif prev_state == 2 and firstNextRepeatEvent:
				menu.append((_("Options disable timer"), "disablerepeatrunning"))
				buttons.append("yellow")
			menu.append((_("Timer Overview"), "timereditlist"))

			def timerAction(choice):
				if choice is not None:
					if choice[1] == "delete":
						self.removeTimer(timer)
					elif choice[1] == "edit":
						self.session.openWithCallback(self.finishedEdit, TimerEntry, timer)
					elif choice[1] == "disable":
						self.disableTimer(timer, prev_state)
					elif choice[1] == "timereditlist":
						self.session.open(TimerEditList)
					elif choice[1] == "disablerepeatrunning":
						self.disableTimer(timer, prev_state, repeat=True, record=True)
					elif choice[1] == "disablerepeat":
						self.disableTimer(timer, prev_state, repeat=True)
			self.session.openWithCallback(timerAction, ChoiceBox, title=title_text + _("Select action for timer '%s'.") % timer.name, list=menu, keys=buttons)
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(event))
			newEntry.justplay = config.recording.timer_default_type.value == "zap"
			newEntry.always_zap = config.recording.timer_default_type.value == "zap+record"
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def finishedEdit(self, answer):
		if answer[0]:
			entry = answer[1]
			if entry.external_prev != entry.external:
				def removeEditTimer():
					entry.service_ref, entry.begin, entry.end, entry.external = entry.service_ref_prev, entry.begin_prev, entry.end_prev, entry.external_prev
					self.removeTimer(entry)

				def moveEditTimerError():
					entry.external = entry.external_prev
					self.onSelectionChanged()
				if entry.external:
					self.fallbackTimer.addTimer(entry, removeEditTimer, moveEditTimerError)
				else:
					newentry = createRecordTimerEntry(entry)
					entry.service_ref, entry.begin, entry.end = entry.service_ref_prev, entry.begin_prev, entry.end_prev
					self.fallbackTimer.removeTimer(entry, boundFunction(self.finishedAdd, (True, newentry)), moveEditTimerError)
			elif entry.external:
				self.fallbackTimer.editTimer(entry, self.onSelectionChanged)
			else:
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					for x in simulTimerList:
						if x.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(x)
					simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList is not None:
						self.session.openWithCallback(boundFunction(self.finishedEdit, service_ref, begin, end), TimerSanityConflict, simulTimerList)
						return
					else:
						self.session.nav.RecordTimer.timeChanged(entry)
				self.onSelectionChanged()

	def finishedAdd(self, answer):
		print("finished add")
		if answer[0]:
			entry = answer[1]
			if entry.external:
				self.fallbackTimer.addTimer(entry, self.onSelectionChanged)
			else:
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					for x in simulTimerList:
						if x.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(x)
					simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList is not None:
						if not entry.repeated and not config.recording.margin_before.value and not config.recording.margin_after.value and len(simulTimerList) > 1:
							change_time = False
							conflict_begin = simulTimerList[1].begin
							conflict_end = simulTimerList[1].end
							if conflict_begin == entry.end:
								entry.end -= 30
								change_time = True
							elif entry.begin == conflict_end:
								entry.begin += 30
								change_time = True
							elif entry.begin == conflict_begin and (entry.service_ref and entry.service_ref.ref and entry.service_ref.ref.flags & eServiceReference.isGroup):
								entry.begin += 30
								change_time = True
							if change_time:
								simulTimerList = self.session.nav.RecordTimer.record(entry)
						if simulTimerList is not None:
							self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
							return
				cur = self["list"].getCurrent()
				event = cur and cur[0]
				if event:
					begin = event.getBeginTime()
					end = begin + event.getDuration()
					if begin < entry.begin <= end or entry.begin <= begin <= entry.end:
						self["key_green"].setText(_("Change timer"))
						self.key_green_choice = self.REMOVE_TIMER
				else:
					self["key_green"].setText(_("Add timer"))
					self.key_green_choice = self.ADD_TIMER
					print("Timeredit aborted")

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()

	def applyButtonState(self, state):
		if state == 0:
			self["now_button"].hide()
			self["now_button_sel"].hide()
			self["next_button"].hide()
			self["next_button_sel"].hide()
			self["more_button"].hide()
			self["more_button_sel"].hide()
			self["now_text"].hide()
			self["next_text"].hide()
			self["more_text"].hide()
			self["key_red"].setText("")
		else:
			if state == 1:
				self["now_button_sel"].show()
				self["now_button"].hide()
			else:
				self["now_button"].show()
				self["now_button_sel"].hide()

			if state == 2:
				self["next_button_sel"].show()
				self["next_button"].hide()
			else:
				self["next_button"].show()
				self["next_button_sel"].hide()

			if state == 3:
				self["more_button_sel"].show()
				self["more_button"].hide()
			else:
				self["more_button"].show()
				self["more_button_sel"].hide()

	def onSelectionChanged(self):
		cur = self["list"].getCurrent()
		if cur is None:
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			return
		event = cur[0]
		self["Event"].newEvent(event)
		if self.type == EPG_TYPE_MULTI:
			count = self["list"].getCurrentChangeCount()
			if self.ask_time != -1:
				self.applyButtonState(0)
			elif count > 1:
				self.applyButtonState(3)
			elif count > 0:
				self.applyButtonState(2)
			else:
				self.applyButtonState(1)
			days = [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")]
			datestr = ""
			if event is not None:
				now = time()
				beg = event.getBeginTime()
				nowTime = localtime(now)
				begTime = localtime(beg)
				if nowTime[2] != begTime[2]:
					datestr = strftime(config.usage.date.dayshort.value, begTime)
				else:
					datestr = '%s' % _('Today')
			self["date"].setText(datestr)
			if cur[1] is None:
				self["Service"].newService(None)
			else:
				self["Service"].newService(cur[1].ref)
		if cur[1] is None or cur[1].getServiceName() == "":
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			return

		if event is None:
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			return

		serviceref = cur[1]
		eventid = event.getEventId()
		begin = event.getBeginTime()
		end = begin + event.getDuration()
		refstr = ':'.join(serviceref.ref.toString().split(':')[:11])
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.getAllTimersList():
			needed_ref = ':'.join(timer.service_ref.ref.toString().split(':')[:11]) == refstr
			if needed_ref and (timer.eit == eventid and (begin < timer.begin <= end or timer.begin <= begin <= timer.end) or timer.repeated and self.session.nav.RecordTimer.isInRepeatTimer(timer, event)):
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Change timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER
		if self.parent and eventid and hasattr(self.parent, "setEvent"):
			self.parent.setEvent(serviceref, eventid)
		self["list"].l.invalidate()
