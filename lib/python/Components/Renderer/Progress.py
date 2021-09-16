#!/usr/bin/python
# -*- coding: utf-8 -*-
from Components.VariableValue import VariableValue
from Components.Renderer.Renderer import Renderer

from enigma import eSlider


class Progress(VariableValue, Renderer):
	def __init__(self):
		Renderer.__init__(self)
		VariableValue.__init__(self)
		self.__start = 0
		self.__end = 100

	GUI_WIDGET = eSlider

	def changed(self, what):
		try:
			if what[0] == self.CHANGED_CLEAR:
				(self.range, self.value) = ((0, 1), 0)
				return

			range = (self.source and self.source.range) or 100
			value = (self.source and self.source.value) or 0
			if value is None:
				value = 0
			(self.range, self.value) = ((0, range), value)
		except:
			None

	def postWidgetCreate(self, instance):
		try:
			instance.setRange(self.__start, self.__end)
		except:
			None

	def setRange(self, range):
		try:
			(self.__start, self.__end) = range
			if self.instance is not None:
				self.instance.setRange(self.__start, self.__end)
		except:
			None

	def getRange(self):
		return (self.__start, self.__end)

	range = property(getRange, setRange)
