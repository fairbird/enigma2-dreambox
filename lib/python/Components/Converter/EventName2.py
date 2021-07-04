#!/usr/bin/python
# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import eEPGCache
from time import localtime


class EventName2(Converter, object):
	NAME = 0
	SHORT_DESCRIPTION = 1
	EXTENDED_DESCRIPTION = 2
	FULL_DESCRIPTION = 3
	ID = 4
	NEXT_NAME = 5
	NEXT_DESCRIPTION = 6
	NEXT_NAMEWT = 7
	NEXT_NAME_NEXT = 8
	NEXT_NAME_NEXTWT = 9
	NEXT_EVENT_LIST = 10
	NEXT_EVENT_LISTWT = 11
	NEXT_EVENT_LIST2 = 12
	NEXT_EVENT_LISTWT2 = 13
	NEXT_TIME_DURATION = 14

	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgcache = eEPGCache.getInstance()
		if type == "Description" or type == "Short":
			self.type = self.SHORT_DESCRIPTION
		elif type == "ExtendedDescription":
			self.type = self.EXTENDED_DESCRIPTION
		elif type == "FullDescription" or type == "ShortOrExtendedDescription":
			self.type = self.FULL_DESCRIPTION
		elif type == "ID":
			self.type = self.ID
		elif type == "NextName":
			self.type = self.NEXT_NAME
		elif type == "NextNameNext":
			self.type = self.NEXT_NAME_NEXT
		elif type == "NextNameNextWithOutTime":
			self.type = self.NEXT_NAME_NEXTWT
		elif type == "NextNameWithOutTime":
			self.type = self.NEXT_NAMEWT
		elif type == "NextDescription" or type == "NextEvent":
			self.type = self.NEXT_DESCRIPTION
		elif type == "NextEventList":
			self.type = self.NEXT_EVENT_LIST
		elif type == "NextEventListWithOutTime":
			self.type = self.NEXT_EVENT_LISTWT
		elif type == "NextEventList2":
			self.type = self.NEXT_EVENT_LIST2
		elif type == "NextEventListWithOutTime2":
			self.type = self.NEXT_EVENT_LISTWT2
		elif type == "NextTimeDuration":
			self.type = self.NEXT_TIME_DURATION
		else:
			self.type = self.NAME

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""
		if self.type is self.NAME:
			return event.getEventName()
		elif self.type is self.SHORT_DESCRIPTION:
			return event.getShortDescription()
		elif self.type is self.EXTENDED_DESCRIPTION:
			text = event.getShortDescription()
			if text and not text[-1] is '\n' and not text[-1] is ' ':
				text += ' '
			return text + event.getExtendedDescription() or event.getEventName()
		elif self.type is self.FULL_DESCRIPTION:
			description = event.getShortDescription()
			extended = event.getExtendedDescription()
			if description and extended:
				description += '\n'
			return description + extended
		elif self.type is self.ID:
			return str(event.getEventId())
		elif self.type is self.NEXT_NAME or self.type is self.NEXT_TIME_DURATION or self.type is self.NEXT_DESCRIPTION or self.type is self.NEXT_NAMEWT:
			reference = self.source.service
			info = reference and self.source.info
			if info is not None:
				eventNext = self.epgcache.lookupEvent(['IBDCTSERNX', (reference.toString(), 1, -1)])
				if eventNext:
					if self.type is self.NEXT_NAME or self.type is self.NEXT_NAMEWT or self.type is self.NEXT_TIME_DURATION:
						t = localtime(eventNext[0][1])
						duration = _("%d min") % (int(0 if eventNext[0][2] is None else eventNext[0][2]) / 60)
						if len(eventNext[0]) > 4 and eventNext[0][4]:
							if self.type is self.NEXT_NAME:
								return "%02d:%02d  (%s)  %s" % (t[3], t[4], duration, eventNext[0][4])
							elif self.type is self.NEXT_TIME_DURATION:
								return "%02d:%02d  (%s)" % (t[3], t[4], duration)
							else:
								return "%s" % eventNext[0][4]
						else:
							return ''
					elif self.type is self.NEXT_DESCRIPTION:
						for i in (6, 5, 4):
							if len(eventNext[0]) > i and eventNext[0][i]:
								return "%s" % eventNext[0][i]
				else:
					return ''
			else:
				return ''
		elif self.type is self.NEXT_EVENT_LIST or self.type is self.NEXT_EVENT_LISTWT or\
			self.type is self.NEXT_EVENT_LIST2 or self.type is self.NEXT_EVENT_LISTWT2 or self.type is self.NEXT_NAME_NEXT or self.type is self.NEXT_NAME_NEXTWT:
			reference = self.source.service
			info = reference and self.source.info
			countitem = 10
			if info is not None:
				eventNext = self.epgcache.lookupEvent(["IBDCT", (reference.toString(), 0, -1, -1)])
				if self.type is self.NEXT_NAME_NEXT or self.type is self.NEXT_NAME_NEXTWT:
					countitem = 4
				if eventNext:
					listEpg = []
					i = 0
					for x in eventNext:
						if i > 0 and i < countitem:
							if x[4]:
								t = localtime(x[1])
								if self.type is self.NEXT_EVENT_LIST or self.type is self.NEXT_EVENT_LIST2 or self.type is self.NEXT_NAME_NEXT:
									duration = _("%d min") % (int(0 if eventNext[i][2] is None else eventNext[i][2]) / 60)
									listEpg.append("%02d:%02d (%s) %s" % (t[3], t[4], duration, x[4]))
								else:
									listEpg.append("%02d:%02d %s" % (t[3], t[4], x[4]))
						i += 1
					if self.type is self.NEXT_EVENT_LIST2 or self.type is self.NEXT_EVENT_LISTWT2 or self.type is self.NEXT_NAME_NEXT or\
						self.type is self.NEXT_NAME_NEXTWT:
						if len(listEpg) > 1:
							listEpg.pop(0)
						else:
							return ''
						return '\n'.join(listEpg)
					else:
						return '\n'.join(listEpg)
				else:
					return ''
			else:
				return ''
		else:
			return ''

	text = property(getText)
