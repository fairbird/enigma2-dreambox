# -*- coding: utf-8 -*-
from Components.Element import Element


class Converter(Element):
	def __init__(self, arguments):
		Element.__init__(self)
		self.converter_arguments = arguments
		self.separator = ""

	def __repr__(self):
		return str(type(self)) + "(" + self.converter_arguments + ")"

	def handleCommand(self, cmd):
		self.source.handleCommand(cmd)

	def appendToStringWithSeparator(self, str, part):
		if str == "":
			str = part
		else:
			str = str + self.separator + part
		return str

	def appendToStringWithSeparator(self, str, part):
		if str == "":
			str = part
		else:
			str = str + "  " + self.separator + "  " + part
		return str
