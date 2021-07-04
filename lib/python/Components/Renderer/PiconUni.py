#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from Components.Renderer.Renderer import Renderer
from enigma import ePixmap
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename, SCOPE_PLUGINS
import os

searchPaths = []


def initPiconPaths():
	global searchPaths
	if os.path.isfile('/proc/mounts'):
#		print("[PiconUni] Read /proc/mounts")
		for line in open('/proc/mounts'):
			if '/dev/sd' in line or '/dev/disk/by-uuid/' in line or '/dev/mmc' in line:
				piconPath = line.split()[1].replace('\\040', ' ') + '/%s/'
				searchPaths.append(piconPath)
	searchPaths.append('/usr/share/enigma2/%s/')
	searchPaths.append(resolveFilename(SCOPE_PLUGINS, '%s/'))


class PiconUni(Renderer):
	__module__ = __name__

	def __init__(self):
		Renderer.__init__(self)
		self.path = 'piconUni'
		self.scale = '0'
		self.nameCache = {}
		self.pngname = ''

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value,) in self.skinAttributes:
			if attrib == 'path':
				self.path = value
			elif attrib == 'noscale':
				self.scale = value
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			pngname = ''
			if not what[0] is self.CHANGED_CLEAR:
				sname = self.source.text
				sname = sname.upper().replace('.', '').replace('\xc2\xb0', '')
				print(sname)
				#if sname.startswith('4097'):
				if not sname.startswith('1'):
					sname = sname.replace('4097', '1', 1).replace('5001', '1', 1).replace('5002', '1', 1)
				if ':' in sname:
					sname = '_'.join(sname.split(':')[:10])
				pngname = self.nameCache.get(sname, '')
				if pngname is '':
					pngname = self.findPicon(sname)
					if not pngname is '':
						self.nameCache[sname] = pngname
			if pngname is '':
				pngname = self.nameCache.get('default', '')
				if pngname is '':
					pngname = self.findPicon('picon_default')
					if pngname is '':
						tmp = resolveFilename(SCOPE_CURRENT_SKIN, 'picon_default.png')
						if os.path.isfile(tmp):
							pngname = tmp
					self.nameCache['default'] = pngname
			if not self.pngname is pngname:
				if self.scale is '0':
					if pngname:
						self.instance.setScale(1)
						self.instance.setPixmapFromFile(pngname)
						self.instance.show()
					else:
						self.instance.hide()
				else:
					if pngname:
						self.instance.setPixmapFromFile(pngname)
				self.pngname = pngname

	def findPicon(self, serviceName):
		global searchPaths
		pathtmp = self.path.split(',')
		for path in searchPaths:
			for dirName in pathtmp:
				pngname = (path % dirName) + serviceName + '.png'
				if os.path.isfile(pngname):
					return pngname
		return ''


initPiconPaths()
