#!/usr/bin/python
# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.Element import cached
from Screens.InfoBar import InfoBar
from enigma import eServiceReference


class RefString(Converter, object):
	CURRENT = 0
	EVENT = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		self.CHANSEL = None
		self.type = {
				"CurrentRef": self.CURRENT,
				"ServicelistRef": self.EVENT
			}[type]

	@cached
	def getText(self):
		if (self.type == self.EVENT):
			service = self.source.service
			marker = (service.flags & eServiceReference.isMarker == eServiceReference.isMarker)
			bouquet = (service.flags & eServiceReference.flagDirectory == eServiceReference.flagDirectory)
			if marker:
				return "marker"
			elif bouquet:
				return "bouquet"
			else:
				return str(self.source.service.toString())
		elif (self.type == self.CURRENT):
			if self.CHANSEL == None:
				self.CHANSEL = InfoBar.instance.servicelist
			vSrv = self.CHANSEL.servicelist.getCurrent()
			return str(vSrv.toString())
		else:
			return "na"

	text = property(getText)
