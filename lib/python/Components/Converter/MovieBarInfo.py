#!/usr/bin/python
# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import iServiceInformation
from ServiceReference import ServiceReference
from os import path


class MovieBarInfo(Converter, object):
	MOVIE_REFERENCE = 0
	MOVIE_DESC = 1

	def __init__(self, type):
		if type == "Reference":
			self.type = self.MOVIE_REFERENCE
		elif type == "Description":
			self.type = self.MOVIE_DESC
		Converter.__init__(self, type)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if info and service:
			if self.type == self.MOVIE_REFERENCE:
				movie_meta = ServiceReference(info.getInfoString(iServiceInformation.sServiceref))
				movie_meta = path.realpath(movie_meta.getPath()) + ".meta"
				try:
					f = open(movie_meta, "rb")
					rec_ref = f.readlines()
					f.close()
				except IOError:
					return ""
				if len(rec_ref):
					return rec_ref[0].rstrip('\n')
			elif self.type == self.MOVIE_DESC:
				movie_meta = ServiceReference(info.getInfoString(iServiceInformation.sServiceref))
				movie_meta = path.realpath(movie_meta.getPath()) + ".meta"
				try:
					f = open(movie_meta, "rb")
					rec_ref = f.readlines()
					f.close()
				except IOError:
					return ""
				if len(rec_ref):
					return rec_ref[2].rstrip('\n')

	text = property(getText)
