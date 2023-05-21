# -*- coding: utf-8 -*-
from Components.GUIComponent import GUIComponent
from skin import parseFont

from Tools.FuzzyDate import FuzzyTime

from enigma import eListboxPythonMultiContent, eListbox, gFont, getBestPlayableServiceReference, eServiceReference, iRecordableServicePtr, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_TOP, RT_VALIGN_BOTTOM
from Tools.Alternatives import GetWithAlternative
from Tools.LoadPixmap import LoadPixmap
from Tools.TextBoundary import getTextBoundarySize
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN


class TimerList(GUIComponent):
#
#  | <Name of the Timer>     <Service>  |
#  | <state>  <orb.pos.>  <start, end>  |
#
	def buildTimerEntry(self, timer, processed):
		width = self.l.getItemSize().width()
		res = [None]
		serviceName = timer.service_ref.getServiceName()

		serviceNameWidth = getTextBoundarySize(self.instance, self.serviceNameFont, self.l.getItemSize(), serviceName).width()
		if 200 > width - serviceNameWidth - self.iconWidth - self.iconMargin:
			serviceNameWidth = width - 200 - self.iconWidth - self.iconMargin

		if timer.external:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, width - serviceNameWidth - self.iconMargin, 0, serviceNameWidth, self.rowSplit, 0, RT_HALIGN_RIGHT | RT_VALIGN_BOTTOM, serviceName, self.backupColor, self.backupColorSel, None, None, None, None))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, width - serviceNameWidth - self.iconMargin, 0, serviceNameWidth, self.rowSplit, 0, RT_HALIGN_RIGHT | RT_VALIGN_BOTTOM, serviceName))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.iconWidth + self.iconMargin, 0, width - serviceNameWidth - self.iconWidth - self.iconMargin*2, self.rowSplit, 2, RT_HALIGN_LEFT | RT_VALIGN_BOTTOM, timer.name))

		begin = FuzzyTime(timer.begin)
		if timer.repeated:
			days = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))
			repeatedtext = []
			flags = timer.repeated
			for x in (0, 1, 2, 3, 4, 5, 6):
				if flags & 1 == 1:
					repeatedtext.append(days[x])
				flags >>= 1
			repeatedtext = ", ".join(repeatedtext)
			if self.iconRepeat:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconMargin // 2, self.rowSplit + (self.itemHeight - self.rowSplit - self.iconHeight) // 2, self.iconWidth, self.iconHeight, self.iconRepeat))
		else:
			repeatedtext = begin[0] # date
			if "autotimer" in timer.flags:
				self.iconAutoTimer and res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconMargin // 2, self.rowSplit + (self.itemHeight - self.rowSplit - self.iconHeight) // 2, self.iconWidth, self.iconHeight, self.iconAutoTimer))
		if timer.justplay:
			if timer.pipzap:
				extra_text = _("(ZAP as PiP)")
			else:
				extra_text = _("(ZAP)")
			text = repeatedtext + ((" %s %s") % (begin[1], extra_text))
		else:
			text = repeatedtext + ((" %s ... %s (%d " + _("mins") + ")") % (begin[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) // 60))
		icon = None
		if not processed and (not timer.disabled or (timer.repeated and timer.isRunning() and not timer.justplay)):
			if timer.state == TimerEntry.StateWaiting:
				state = _("waiting")
				icon = self.iconWait
			elif timer.state == TimerEntry.StatePrepared:
				state = _("about to start")
				icon = self.iconPrepared
			elif timer.state == TimerEntry.StateRunning:
				if timer.justplay:
					state = _("zapped")
					icon = self.iconZapped
				else:
					state = _("recording...")
					icon = self.iconRecording
			elif timer.state == TimerEntry.StateEnded:
				state = _("done!")
				icon = self.iconDone
			else:
				state = _("<unknown>")
				icon = None
		elif timer.disabled:
			state = _("disabled")
			icon = self.iconDisabled
		else:
			state = _("done!")
			icon = self.iconDone

		icon and res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconMargin // 2, (self.rowSplit - self.iconHeight) // 2, self.iconWidth, self.iconHeight, icon))
		orbpos = self.getOrbitalPos(timer.service_ref, timer.state, hasattr(timer, "record_service") and timer.record_service or None)
		orbposWidth = getTextBoundarySize(self.instance, self.font, self.l.getItemSize(), orbpos).width()
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft, self.rowSplit, orbposWidth, self.itemHeight - self.rowSplit, 1, RT_HALIGN_LEFT | RT_VALIGN_TOP, orbpos))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.iconWidth + self.iconMargin, self.rowSplit, self.satPosLeft - self.iconWidth - self.iconMargin, self.itemHeight - self.rowSplit, 1, RT_HALIGN_LEFT | RT_VALIGN_TOP, state))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft + orbposWidth, self.rowSplit, width - self.satPosLeft - orbposWidth - self.iconMargin, self.itemHeight - self.rowSplit, 1, RT_HALIGN_RIGHT | RT_VALIGN_TOP, text))
		return res

	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildTimerEntry)
		self.serviceNameFont = gFont("Regular", 20)
		self.font = gFont("Regular", 18)
		self.eventNameFont = gFont("Regular", 18)
		self.l.setList(list)
		self.itemHeight = 50
		self.rowSplit = 25
		self.iconMargin = 4
		self.satPosLeft = 160
		self.backupColor = self.backupColorSel = 0x00CCAC68
		self.iconWait = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/timer_wait.png"))
		#currently intended that all icons have the same size
		self.iconWidth = self.iconWait.size().width()
		self.iconHeight = self.iconWait.size().height()
		self.iconRecording = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/timer_rec.png"))
		self.iconPrepared = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/timer_prep.png"))
		self.iconDone = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/timer_done.png"))
		self.iconRepeat = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/timer_rep.png"))
		self.iconZapped = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/timer_zap.png"))
		self.iconDisabled = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/timer_off.png"))
		self.iconAutoTimer = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/timer_autotimer.png"))

	def applySkin(self, desktop, parent):
		def itemHeight(value):
			self.itemHeight = int(value)

		def setServiceNameFont(value):
			self.serviceNameFont = parseFont(value, ((1, 1), (1, 1)))

		def setEventNameFont(value):
			self.eventNameFont = parseFont(value, ((1, 1), (1, 1)))

		def setFont(value):
			self.font = parseFont(value, ((1, 1), (1, 1)))

		def rowSplit(value):
			self.rowSplit = int(value)

		def iconMargin(value):
			self.iconMargin = int(value)

		def satPosLeft(value):
			self.satPosLeft = int(value)

		def backupColor(value):
			self.backupColor = int(value)

		def backupColorSel(value):
			self.backupColorSel = int(value)
		for (attrib, value) in list(self.skinAttributes):
			try:
				locals().get(attrib)(value)
				self.skinAttributes.remove((attrib, value))
			except:
				pass
		self.l.setItemHeight(self.itemHeight)
		self.l.setFont(0, self.serviceNameFont)
		self.l.setFont(1, self.font)
		self.l.setFont(2, self.eventNameFont)
		return GUIComponent.applySkin(self, desktop, parent)

	def getCurrent(self):
		cur = self.l.getCurrentSelection()
		return cur and cur[0]

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		self.instance = instance
		instance.setWrapAround(True)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	currentIndex = property(getCurrentIndex, moveToIndex)
	currentSelection = property(getCurrent)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def invalidate(self):
		self.l.invalidate()

	def entryRemoved(self, idx):
		self.l.entryRemoved(idx)

	def getOrbitalPos(self, ref, state, record_service=None):
		tuner_name = refstr = alternative = ""
		if hasattr(ref, "sref"):
			refstr = str(ref.sref)
		else:
			refstr = str(ref)
		if refstr and refstr.startswith("1:134:"):
			alternative = " (A)"
			if state in (1, 2) and not hasattr(ref, "sref"):
				current_ref = getBestPlayableServiceReference(ref.ref, eServiceReference())
				if not current_ref:
					return _("N/A") + alternative
				else:
					refstr = current_ref.toString()
			else:
				refstr = GetWithAlternative(refstr)
		if "%3a//" in refstr:
			return "%s" % _("Stream") + alternative
		if record_service and state in (1, 2) and not hasattr(ref, "sref"):
			if isinstance(record_service, iRecordableServicePtr):
				feinfo = hasattr(record_service, "frontendInfo") and record_service.frontendInfo()
				data = feinfo and hasattr(feinfo, "getFrontendData") and feinfo.getFrontendData()
				if data:
					number = data.get("tuner_number", None)
					if number != None and isinstance(number, int):
						tuner_name = "%s: " % chr(number + 65)
		op = int(refstr.split(":", 10)[6][:-4] or "0", 16)
		if op == 0xeeee:
			return tuner_name + ("%s" % "DVB-T") + alternative
		if op == 0xffff:
			return tuner_name + ("%s" % "DVB-C") + alternative
		direction = "E"
		if op > 1800:
			op = 3600 - op
			direction = "W"
		return tuner_name + ("%d.%d\xb0%s" % (op // 10, op % 10, direction)) + alternative
