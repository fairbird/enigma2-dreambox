#!/usr/bin/python
# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.Element import cached


class TextToUpper(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type

	@cached
	def getText(self):
		return self.source.text.upper()

	text = property(getText)
