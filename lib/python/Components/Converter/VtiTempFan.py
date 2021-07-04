#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll


class VtiTempFan(Poll, Converter, object):
	TEMPINFO = 1
	FANINFO = 2
	ALL = 5

	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)
		self.type = type
		self.poll_interval = 30000
		self.poll_enabled = True
		if type == 'TempInfo':
			self.type = self.TEMPINFO
		elif type == 'FanInfo':
			self.type = self.FANINFO
		else:
			self.type = self.ALL

	@cached
	def getText(self):
		textvalue = ''
		if self.type == self.TEMPINFO:
			textvalue = self.tempfile()
		elif self.type == self.FANINFO:
			textvalue = self.fanfile()
		return textvalue

	text = property(getText)

	def tempfile(self):
		temp = ''
		unit = ''
		try:
			print("[VtiTempFan] Read /proc/stb/sensors/temp0/value")
			temp = open("/proc/stb/sensors/temp0/value", "rb").readline().strip()
			print("[VtiTempFan] Read /proc/stb/sensors/temp0/unit")
			unit = open("/proc/stb/sensors/temp0/unit", "rb").readline().strip()
			tempinfo = 'TEMP: ' + str(temp) + ' \xc2\xb0' + str(unit)
			return tempinfo
		except:
			print("[VtiTempFan] Read /proc/stb/sensors/temp0/value failed.")
			print("[VtiTempFan] Read /proc/stb/sensors/temp0/unit failed.")

	def fanfile(self):
		fan = ''
		try:
			print("[VtiTempFan] Read /proc/stb/fp/fan_speed")
			fan = open("/proc/stb/fp/fan_speed", "rb").readline().strip()
			faninfo = 'FAN: ' + str(fan)
			return faninfo
		except:
			print("[VtiTempFan] Read /proc/stb/fp/fan_speed failed.")

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)
