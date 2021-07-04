#!/usr/bin/python
# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.Element import cached


class Textreplace(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type

	@cached
	def getText(self):
		if self.type is not None:
			if self.source is not None:
				if self.source.text is not None:
					return self.source.text.replace(self.type, "")
				else:
					return ""
			else:
				return ""
		else:
			return ""

	text = property(getText)
