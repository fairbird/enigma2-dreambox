# -*- coding: utf-8 -*-
from Components.GUIComponent import GUIComponent

from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER

from Tools.Alternatives import CompareWithAlternatives
from Tools.LoadPixmap import LoadPixmap

from time import localtime, time, strftime
from Components.config import config
from ServiceReference import ServiceReference
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from skin import parseFont


EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1
EPG_TYPE_SIMILAR = 2
EPG_TYPE_PARTIAL = 3


class Rect:
	def __init__(self, x, y, width, height):
		self.x = x
		self.y = y
		self.w = width
		self.h = height

	# silly, but backward compatible
	def left(self):
		return self.x

	def top(self):
		return self.y

	def height(self):
		return self.h

	def width(self):
		return self.w


class EPGList(GUIComponent):
	def __init__(self, type=EPG_TYPE_SINGLE, selChangedCB=None, timer=None):
		self.days = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))
		self.timer = timer
		self.onSelChanged = []
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.type = type
		self.l = eListboxPythonMultiContent()
		self.eventItemFont = gFont("Regular", 22)
		self.eventTimeFont = gFont("Regular", 16)
		self.iconSize = 21
		self.iconDistance = 2
		self.colGap = 10
		self.skinColumns = False
		self.tw = 90
		self.dy = 0

		if type == EPG_TYPE_SINGLE:
			self.l.setBuildFunc(self.buildSingleEntry)
		elif type == EPG_TYPE_MULTI:
			self.l.setBuildFunc(self.buildMultiEntry)
		else:
			assert(type == EPG_TYPE_SIMILAR)
			self.l.setBuildFunc(self.buildSimilarEntry)
		self.epgcache = eEPGCache.getInstance()

		main_icons = (
			"epgclock",
			"zapclock",
			"zaprecclock",
			"repepgclock",
			"repzapclock",
			"repzaprecclock",
			"pipclock"
		)
		add_icons = (
			"_add",
			"_pre",
			"",
			"_prepost",
			"_post"
		)
		self.clocks = tuple(LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "icons/%s%s.png" % (m, a))) for m in main_icons for a in add_icons)

	def getEventFromId(self, service, eventid):
		event = None
		if self.epgcache is not None and eventid is not None:
			event = self.epgcache.lookupEventId(service.ref, eventid)
		return event

	def getCurrentChangeCount(self):
		if self.type == EPG_TYPE_MULTI and self.l.getCurrentSelection() is not None:
			return self.l.getCurrentSelection()[0]
		return 0

	def getCurrent(self):
		idx = 0
		if self.type == EPG_TYPE_MULTI:
			idx += 1
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return (None, None)
		eventid = tmp[idx + 1]
		service = ServiceReference(tmp[idx])
		event = self.getEventFromId(service, eventid)
		return (event, service)

	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def connectSelectionChanged(func):
		if not self.onSelChanged.count(func):
			self.onSelChanged.append(func)

	def disconnectSelectionChanged(func):
		self.onSelChanged.remove(func)

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()
#                               try:
#                                       x()
#                               except: # FIXME!!!
#                                       print("FIXME in EPGList.selectionChanged")
#                                       pass

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		try:
			self.iconSize = self.clocks[0].size().height()
		except:
			pass
		self.space = self.iconSize + self.iconDistance
		self.dy = int((height - self.iconSize) / 2.)

		if self.type == EPG_TYPE_SINGLE:
			if self.skinColumns:
				x = 0
				self.weekday_rect = Rect(0, 0, self.gap(self.col[0]), height)
				x += self.col[0]
				self.datetime_rect = Rect(x, 0, self.gap(self.col[1]), height)
				x += self.col[1]
				self.descr_rect = Rect(x, 0, width - x, height)
			else:
				self.weekday_rect = Rect(0, 0, width // 20 * 2 - 10, height)
				self.datetime_rect = Rect(width // 20 * 2, 0, width // 20 * 5 - 15, height)
				self.descr_rect = Rect(width // 20 * 7, 0, width // 20 * 13, height)
		elif self.type == EPG_TYPE_MULTI:
			if self.skinColumns:
				x = 0
				self.service_rect = Rect(x, 0, self.gap(self.col[0]), height)
				x += self.col[0]
				self.progress_rect = Rect(x, 8, self.gap(self.col[1]), height - 16)
				self.start_end_rect = Rect(x, 0, self.gap(self.col[1]), height)
				x += self.col[1]
				self.descr_rect = Rect(x, 0, width - x, height)
			else:
				xpos = 0
				w = width // 10 * 3
				self.service_rect = Rect(xpos, 0, w - 10, height)
				xpos += w
				w = width // 10 * 2
				self.start_end_rect = Rect(xpos, 0, w - 10, height)
				self.progress_rect = Rect(xpos, 4, w - 10, height - 8)
				xpos += w
				w = width // 10 * 5
				self.descr_rect = Rect(xpos, 0, width, height)
		else: # EPG_TYPE_SIMILAR
			if self.skinColumns:
				x = 0
				self.weekday_rect = Rect(0, 0, self.gap(self.col[0]), height)
				x += self.col[0]
				self.datetime_rect = Rect(x, 0, self.gap(self.col[1]), height)
				x += self.col[1]
				self.service_rect = Rect(x, 0, width - x, height)
			else:
				self.weekday_rect = Rect(0, 0, width // 20 * 2 - 10, height)
				self.datetime_rect = Rect(width // 20 * 2, 0, width // 20 * 5 - 15, height)
				self.service_rect = Rect(width // 20 * 7, 0, width // 20 * 13, height)

	def gap(self, width):
		return width - self.colGap

	def getClockTypesForEntry(self, service, eventId, beginTime, duration):
		if not beginTime:
			return None
		rec = self.timer.isInTimer(eventId, beginTime, duration, service)
		if rec is not None:
			return rec[1]
		else:
			return None

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		clock_types = self.getClockTypesForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect
		split = int(r2.w * 0.55)
		t = localtime(beginTime)
		et = localtime(beginTime + duration)
		res = [
			None, # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, strftime(config.usage.date.dayshort.value, t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value + " -", t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x + split, r2.y, r2.w - split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value, et))
		]
		if clock_types:
			for i in range(len(clock_types)):
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + i * self.space, r3.y + self.dy, self.iconSize, self.iconSize, self.clocks[clock_types[i]]))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x + (i + 1) * self.space, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName))
		return res

	def buildSimilarEntry(self, service, eventId, beginTime, service_name, duration):
		clock_types = self.getClockTypesForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.service_rect
		split = int(r2.w * 0.55)
		t = localtime(beginTime)
		et = localtime(beginTime + duration)
		res = [
			None,  # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, strftime(config.usage.date.dayshort.value, t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value + " -", t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x + split, r2.y, r2.w - split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value, et))
		]
		if clock_types:
			for i in range(len(clock_types)):
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + i * self.space, r3.y + self.dy, self.iconSize, self.iconSize, self.clocks[clock_types[i]]))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x + (i + 1) * self.space, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name))
		return res

	def buildMultiEntry(self, changecount, service, eventId, beginTime, duration, EventName, nowTime, service_name):
		clock_types = self.getClockTypesForEntry(service, eventId, beginTime, duration)
		r1 = self.service_rect
		r2 = self.progress_rect
		r3 = self.descr_rect
		r4 = self.start_end_rect
		res = [None] # no private data needed
		if clock_types:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w - self.space * len(clock_types), r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name))
			for i in range(len(clock_types)):
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r1.x + r1.w - self.space * (i + 1), r1.y + self.dy, self.iconSize, self.iconSize, self.clocks[clock_types[len(clock_types) - 1 - i]]))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name))
		if beginTime is not None:
			if nowTime < beginTime:
				begin = localtime(beginTime)
				end = localtime(beginTime + duration)
				split = int(r2.w * 0.55)
				res.extend((
					(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value + "- ", begin)),
					(eListboxPythonMultiContent.TYPE_TEXT, r2.x + split, r2.y, r2.w - split, r2.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value, end)),
					(eListboxPythonMultiContent.TYPE_TEXT, r3.x + self.tw, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName)
				))
			else:
				percent = (nowTime - beginTime) * 100 // duration
				prefix = "+"
				remaining = ((beginTime + duration) - int(time())) / 60
				if remaining <= 0:
					prefix = ""
				res.extend((
					(eListboxPythonMultiContent.TYPE_PROGRESS, r2.x, r2.y, self.tw, r2.h, percent),
					(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, self.gap(self.tw), r3.h, 1, RT_HALIGN_CENTER, _("%s%d min") % (prefix, remaining)),
					(eListboxPythonMultiContent.TYPE_TEXT, r3.x + self.tw, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName)
				))
		return res

	def queryEPG(self, list, buildFunc=None):
		if self.epgcache is not None:
			if buildFunc is not None:
				return self.epgcache.lookupEvent(list, buildFunc)
			else:
				return self.epgcache.lookupEvent(list)
		return []

	def fillMultiEPG(self, services, stime=-1):
		#t = int(time())
		test = [(service.ref.toString(), 0, stime) for service in services]
		test.insert(0, 'X0RIBDTCn')
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		#print(int(time() - t))
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		#t = int(time())
		test = [x[3] and (x[1], direction, x[3]) or (x[1], direction, 0) for x in self.list]
		test.insert(0, 'XRIBDTCn')
		tmp = self.queryEPG(test)
		cnt = 0
		for x in tmp:
			changecount = self.list[cnt][0] + direction
			if changecount >= 0:
				if x[2] is not None:
					self.list[cnt] = (changecount, x[0], x[1], x[2], x[3], x[4], x[5], x[6])
			cnt += 1
		self.l.setList(self.list)
		#print(int(time() - t))
		self.selectionChanged()

	def fillSingleEPG(self, service):
		t = int(time())
		epg_time = t - config.epg.histminutes.getValue() * 60
		test = ['RIBDT', (service.ref.toString(), 0, epg_time, -1)]
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		if t != epg_time:
			idx = 0
			for x in self.list:
				idx += 1
				if t < x[2] + x[3]:
					break
			self.instance.moveSelectionTo(idx - 1)
		self.selectionChanged()

	def sortSingleEPG(self, type):
		list = self.list
		if list:
			event_id = self.getSelectedEventId()
			if type == 1:
				list.sort(key=lambda x: (x[4] and x[4].lower(), x[2]))
			else:
				assert(type == 0)
				list.sort(key=lambda x: x[2])
			self.l.invalidate()
			self.moveToEventId(event_id)

	def getSelectedEventId(self):
		x = self.l.getCurrentSelection()
		return x and x[1]

	def moveToService(self, serviceref):
		if not serviceref:
			return
		index = 0
		refstr = serviceref.toString()
		for x in self.list:
			if CompareWithAlternatives(x[1], refstr):
				self.instance.moveSelectionTo(index)
				break
			index += 1

	def moveToEventId(self, eventId):
		if not eventId:
			return
		index = 0
		for x in self.list:
			if x[1] == eventId:
				self.instance.moveSelectionTo(index)
				break
			index += 1

	def fillSimilarList(self, refstr, event_id):
		# t = int(time())
		# search similar broadcastings
		if event_id:
			self.fill_list(self.epgcache.search(('RIBND', 1024, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, event_id)))
		# print(int(time() - t))

	def fill_partial_list(self, event):
		if event:
			self.fill_list(self.epgcache.search(('RIBND', 1024, eEPGCache.PARTIAL_TITLE_SEARCH, event, eEPGCache.NO_CASE_CHECK)))

	def fill_list(self, event_list):
		if event_list and len(event_list):
			event_list.sort(key=lambda x: x[2])
		self.l.setList(event_list)
		self.selectionChanged()

	def applySkin(self, desktop, parent):

		def warningWrongSkinParameter(string):
			print("[EpgList] wrong '%s' skin parameters" % string)

		def setEventItemFont(value):
			self.eventItemFont = parseFont(value, ((1, 1), (1, 1)))

		def setEventTimeFont(value):
			self.eventTimeFont = parseFont(value, ((1, 1), (1, 1)))

		def setIconDistance(value):
			self.iconDistance = int(value)

		def setIconShift(value):
			self.dy = int(value)

		def setTimeWidth(value):
			self.tw = int(value)

		def setColWidths(value):
			self.col = [int(x) for x in value.split(",")]
			if len(self.col) == 2:
				self.skinColumns = True
			else:
				warningWrongSkinParameter(attrib)

		def setColGap(value):
			self.colGap = int(value)

		for (attrib, value) in self.skinAttributes[:]:
			try:
				locals().get(attrib)(value)
			except (TypeError, ValueError, NameError) as er:
				print("[EPGList] error in set skin parameters", er)
			else:
				self.skinAttributes.remove((attrib, value))

		self.l.setFont(0, self.eventItemFont)
		self.l.setFont(1, self.eventTimeFont)
		return GUIComponent.applySkin(self, desktop, parent)
