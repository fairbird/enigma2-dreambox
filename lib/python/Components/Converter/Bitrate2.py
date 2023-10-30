#
#  Converter Bitrate2
#
#  This plugin is licensed under the Creative Commons 
#  Attribution-NonCommercial-ShareAlike 3.0 Unported 
#  License. To view a copy of this license, visit
#  http://creativecommons.org/licenses/by-nc-sa/3.0/ or send a letter to Creative
#  Commons, 559 Nathan Abbott Way, Stanford, California 94305, USA.
#
#  Alternatively, this plugin may be distributed and executed on hardware which
#  is licensed by Dream Multimedia GmbH.

#  This plugin is NOT free software. It is open source, you are allowed to
#  modify it (if you keep the license), but it may not be commercially 
#  distributed other than under the conditions noted above.
#
#  mod by 2boom 2013-22 08.12.2015
#  Update by RAED
#
#	<widget source="session.CurrentService" render="Label" position="1712,920" size="250,32" font="Regular; 24" zPosition="3" halign="left" transparent="1" >
#		<convert type="iFlatBitrate">Video: %V Kbit/s</convert>
#	</widget>
#	<widget source="session.CurrentService" render="Label" position="1712,957" size="250,32" font="Regular; 24" zPosition="3" halign="left" transparent="1" >
#		<convert type="iFlatBitrate">Audio :%A Kbit/s</convert>
#	</widget>

from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import iServiceInformation, iPlayableService, eTimer, eServiceReference
from Tools.Directories import fileExists
from Components.Console import Console
import os

if fileExists('/usr/lib/bitratecalc.so'):
	if not os.path.islink('/usr/lib/enigma2/python/Components/Converter/bitratecalc.so') or not fileExists('/usr/lib/enigma2/python/Components/Converter/bitratecalc.so'):
		Console().ePopen('ln -s /usr/lib/bitratecalc.so /usr/lib/enigma2/python/Components/Converter/bitratecalc.so')
	from Components.Converter.bitratecalc import eBitrateCalculator
	binaryfound = True
else:
	binaryfound = False

class Bitrate2(Converter, object):
	VBIT = 0
	ABIT = 1
	FORMAT = 2

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "VideoBitrate":
			self.type = self.VBIT
		elif type == "AudioBitrate":
			self.type = self.ABIT
		else:
			# format:
			#   %V - video bitrate value
			#   %A - audio bitrate value
			self.type = self.FORMAT
			self.sfmt = type[:]
			if self.sfmt == '':
				self.sfmt = "V:%V Kb/s A:%A Kb/s"
		self.clearData()
		self.initTimer = eTimer()
		self.initTimer.callback.append(self.initBitrateCalc)

	def clearData(self):
		self.videoBitrate = None
		self.audioBitrate = None
		self.video = self.audio = 0

	def initBitrateCalc(self):
		service = self.source.service
		vpid = apid = dvbnamespace = tsid = onid = -1
		if service and binaryfound:
			serviceInfo = service.info()
			vpid = serviceInfo.getInfo(iServiceInformation.sVideoPID)
			apid = serviceInfo.getInfo(iServiceInformation.sAudioPID)
			tsid = serviceInfo.getInfo(iServiceInformation.sTSID)
			onid = serviceInfo.getInfo(iServiceInformation.sONID)
			dvbnamespace = serviceInfo.getInfo(iServiceInformation.sNamespace)
		if vpid > 0 and (self.type == self.VPID or self.type == self.FORMAT and '%V' in self.sfmt):
			# pid, dvbnamespace, tsid, onid, refresh intervall, buffer size
			self.videoBitrate = eBitrateCalculator(vpid, dvbnamespace, tsid, onid, 1000, 1048576)
			self.videoBitrate.callback.append(self.getVideoBitrateData)
		if apid > 0 and (self.type == self.APID or self.type == self.FORMAT and '%A' in self.sfmt):
			self.audioBitrate = eBitrateCalculator(apid, dvbnamespace, tsid, onid, 1000, 65536)
			self.audioBitrate.callback.append(self.getAudioBitrateData)

	@cached
	def getText(self):
		if not binaryfound:
			return 'N/A'
		elif self.type == self.VBIT:
			ret = '%d' % self.video
		elif self.type == self.ABIT:
			ret = '%d' % self.audio
		else:
			ret = ''
			tmp = self.sfmt[:]
			while True:
				pos = tmp.find('%')
				if pos == -1:
					ret += tmp
					break
				ret += tmp[:pos]
				pos += 1
				l = len(tmp)
				f = pos < l and tmp[pos] or '%'
				if f == 'V':
					ret += '%d' % self.video
				elif f == 'A':
					ret += '%d' % self.audio
				else:
					ret += f
				if pos + 1 >= l:
					break
				tmp = tmp[pos + 1:]

		return ret

	text = property(getText)

	def getVideoBitrateData(self, value, status):
		if status:
			self.video = value
		else:
			self.videoBitrate = None
			self.video = 0
		Converter.changed(self, (self.CHANGED_POLL,))

	def getAudioBitrateData(self, value, status):
		if status:
			self.audio = value
		else:
			self.audioBitrate = None
		Converter.changed(self, (self.CHANGED_POLL,))

	def changed(self, what):
		if what[0] == self.CHANGED_SPECIFIC:
			if what[1] == iPlayableService.evStart:
				self.initTimer.start(200, True)
			elif what[1] == iPlayableService.evEnd:
				self.clearData()
				Converter.changed(self, what)
