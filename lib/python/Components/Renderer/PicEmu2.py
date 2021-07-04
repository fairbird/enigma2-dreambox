#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from Components.Pixmap import Pixmap
from Components.Renderer.Renderer import Renderer
from enigma import iServiceInformation
from string import upper
from enigma import ePixmap
from Tools.Directories import fileExists, SCOPE_CURRENT_SKIN, resolveFilename
from Components.Element import cached
from Components.Converter.Poll import Poll
import os


class PicEmu2(Renderer, Poll):
	__module__ = __name__
	if os.path.exists("/usr/lib64"):
		searchPaths = ('/data/%s/', '/usr/share/enigma2/%s/', '/usr/lib64/enigma2/python/Plugins/Extensions/%s/', '/media/sde1/%s/', '/media/cf/%s/', '/media/sdd1/%s/', '/media/hdd/%s/', '/media/usb/%s/', '/media/ba/%s/', '/mnt/ba/%s/', '/media/sda/%s/', '/etc/%s/')
	else:
		searchPaths = ('/data/%s/', '/usr/share/enigma2/%s/', '/usr/lib/enigma2/python/Plugins/Extensions/%s/', '/media/sde1/%s/', '/media/cf/%s/', '/media/sdd1/%s/', '/media/hdd/%s/', '/media/usb/%s/', '/media/ba/%s/', '/mnt/ba/%s/', '/media/sda/%s/', '/etc/%s/')

	def __init__(self):
		Poll.__init__(self)
		Renderer.__init__(self)
		self.path = 'emu'
		self.nameCache = {}
		self.pngname = ''
		self.picon_default = "picon_default.png"

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value,) in self.skinAttributes:
			if (attrib == 'path'):
				self.path = value
			elif (attrib == 'picon_default'):
				self.picon_default = value
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not service:
			return None
		camd = ""
		serlist = None
		camdlist = None
		nameemu = []
		nameser = []
		if not info:
			return ""
		if fileExists("/etc/init.d/softcam") or fileExists("/etc/init.d/cardserver"):
			try:
				for line in open("/etc/init.d/softcam"):
					if "echo" in line:
						nameemu.append(line)
				camdlist = "%s" % nameemu[1].split('"')[1]
			except:
				pass
			try:
				for line in open("/etc/init.d/cardserver"):
					if "echo" in line:
						nameser.append(line)
				serlist = "%s" % nameser[1].split('"')[1]
			except:
				pass
			if serlist is not None and camdlist is not None:
				return ("%s %s" % (serlist, camdlist))
			elif camdlist is not None:
				return "%s" % camdlist
			elif serlist is not None:
				return "%s" % serlist
			return ""

		if serlist is not None:
			try:
				cardserver = ""
				for current in serlist.readlines():
					cardserver = current
				serlist.close()
			except:
				pass
		else:
			cardserver = " "

		if camdlist is not None:
			try:
				emu = ""
				for current in camdlist.readlines():
					emu = current
				camdlist.close()
			except:
				pass
		else:
			emu = " "

		return "%s %s" % (cardserver.split('\n')[0], emu.split('\n')[0])

	text = property(getText)

	def changed(self, what):
		self.poll_interval = 50
		self.poll_enabled = True
		if self.instance:
			pngname = ''
			if (what[0] != self.CHANGED_CLEAR):
				sname = ""
				service = self.source.service
				if service:
					info = (service and service.info())
					if info:
						caids = info.getInfoObject(iServiceInformation.sCAIDs)
						if fileExists("/tmp/ecm.info"):
							try:
								value = self.getText()
								value = value.lower()
								if value is None:
									print("[PicEmu2] No emu installed or FTA?")
									sname = "fta"
								else:
									if fileExists("/tmp/ecm.info"):
										try:
											content = open("/tmp/ecm.info", "r").read()
										except:
											content = ""
										contentInfo = content.split("\n")
										for line in contentInfo:
											if ("address" in line):
												sname = "cccam"
							except:
								print("")

						if caids:
							if (len(caids) > 0):
								for caid in caids:
									caid = self.int2hex(caid)
									if (len(caid) == 3):
										caid = ("0%s" % caid)
									caid = caid[:2]
									caid = caid.upper()
									if (caid != "") and (sname == ""):
										print("[PicEmu2] Unknown emu or FTA?")
										sname = "fta"

				pngname = self.nameCache.get(sname, '')
				if (pngname == ''):
					pngname = self.findPicon(sname)
					if (pngname != ''):
						self.nameCache[sname] = pngname

			if (pngname == ''):
				pngname = self.nameCache.get('fta', '')
				if (pngname == ''):
					pngname = self.findPicon('fta')
					if (pngname == ''):
						tmp = resolveFilename(SCOPE_CURRENT_SKIN, 'picon_default.png')
						if fileExists(tmp):
							pngname = tmp
						self.nameCache['default'] = pngname

			if (self.pngname != pngname):
				self.pngname = pngname
				self.instance.setPixmapFromFile(self.pngname)

	def int2hex(self, int):
		return ("%x" % int)

	def findPicon(self, serviceName):
		for path in self.searchPaths:
			pngname = (((path % self.path) + serviceName) + '.png')
			if fileExists(pngname):
				return pngname
		return ''
