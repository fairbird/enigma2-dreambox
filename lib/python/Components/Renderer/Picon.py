# -*- coding: utf-8 -*-
from os import listdir
from os.path import exists, getsize, isdir, join
from re import sub
from unicodedata import normalize
from enigma import ePixmap
from Components.config import config
from Components.Harddisk import harddiskmanager
from Components.Renderer.Renderer import Renderer
from ServiceReference import ServiceReference
from Tools.Alternatives import GetWithAlternative
from Tools.Directories import SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN, resolveFilename, sanitizeFilename


class PiconLocator:
	def __init__(self, piconDirectories=["picon"]):
		harddiskmanager.on_partition_list_change.append(self.onPartitionChange)
		self.piconDirectories = piconDirectories
		self.activePiconPath = None
		self.searchPaths = []
		for mp in ("/usr/share/enigma2/", "/"):
			self.onMountpointAdded(mp)
		for part in harddiskmanager.getMountedPartitions():
			mp = join(part.mountpoint, "usr/share/enigma2")
			self.onMountpointAdded(part.mountpoint)
			self.onMountpointAdded(mp)


	def onMountpointAdded(self, mountpoint):
		for piconDirectory in self.piconDirectories:
			try:
				path = join(mountpoint, piconDirectory) + "/"
				if isdir(path) and path not in self.searchPaths:
					for fn in listdir(path):
						if fn.endswith(".png") or fn.endswith(".svg"):
							print(f"[Picon] adding path: {path}")
							self.searchPaths.append(path)
							break
			except Exception as err:
				print(f"[Picon] Failed to investigate {mountpoint}:{str(err)}")

	def onMountpointRemoved(self, mountpoint):
		for piconDirectory in self.piconDirectories:
			path = join(mountpoint, piconDirectory) + "/"
			try:
				self.searchPaths.remove(path)
				print(f"[Picon] removed path: {path}")
			except Exception:
				pass

	def onPartitionChange(self, why, part):
		if why == "add":
			self.onMountpointAdded(part.mountpoint)
		elif why == "remove":
			self.onMountpointRemoved(part.mountpoint)

	def findPicon(self, serviceName):
		if self.activePiconPath is not None:
			for ext in (".png", ".svg"):
				pngname = f"{self.activePiconPath}{serviceName}{ext}"
				return pngname if exists(pngname) else ""
		else:
			for path in self.searchPaths:
				for ext in (".png", ".svg"):
					pngname = f"{path}{serviceName}{ext}"
					if exists(pngname):
						self.activePiconPath = path
						return pngname
		return ""

	def addSearchPath(self, value):
		if exists(value):
			if not value.endswith("/"):
				value += "/"
			if not value.startswith("/media/net") and not value.startswith("/media/autofs") and value not in self.searchPaths:
				self.searchPaths.append(value)

	def getPiconName(self, serviceName):
		#remove the path and name fields, and replace ":" by "_"
		fields = GetWithAlternative(serviceName).split(":", 10)[:10]
		if not fields or len(fields) < 10:
			return ""
		pngname = self.findPicon("_".join(fields))
		if not pngname and not fields[6].endswith("0000"):
			#remove "sub-network" from namespace
			fields[6] = fields[6][:-4] + "0000"
			pngname = self.findPicon("_".join(fields))
		if not pngname and fields[0] != "1":
			#fallback to 1 for IPTV streams
			fields[0] = "1"
			pngname = self.findPicon("_".join(fields))
		if not pngname and fields[2] != "2":
			#fallback to 1 for TV services with non-standard service types
			fields[2] = "1"
			pngname = self.findPicon("_".join(fields))
		if not pngname: # picon by channel name
			if (sname := ServiceReference(serviceName).getServiceName()) and "SID 0x" not in sname and (utf8_name := sanitizeFilename(sname).lower()) and utf8_name != "__":  # avoid lookups on zero length service names
				legacy_name = sub("[^a-z0-9]", "", utf8_name.replace("&", "and").replace("+", "plus").replace("*", "star"))  # legacy ascii service name picons
				pngname = self.findPicon(utf8_name) or legacy_name and self.findPicon(legacy_name) or self.findPicon(sub(r"(fhd|uhd|hd|sd|4k)$", "", utf8_name).strip()) or legacy_name and self.findPicon(sub(r"(fhd|uhd|hd|sd|4k)$", "", legacy_name).strip())
				if not pngname and len(legacy_name) > 6:
					series = sub(r"s[0-9]*e[0-9]*$", "", legacy_name)
					pngname = self.findPicon(series)
		if not pngname: # picon default
			tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png") # picon_default in current active skin
			tmp2 = self.findPicon("picon_default") # picon_default in picon folder
			if exists(tmp2):
				pngname = tmp2
			else:
				if exists(tmp):
					pngname = tmp
				else:
					pngname = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")
		return pngname


piconLocator = None


def initPiconPaths():
	global piconLocator
	piconLocator = PiconLocator()


initPiconPaths()


def getPiconName(serviceName):
	return piconLocator.getPiconName(serviceName)


class Picon(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.pngname = None
		self.defaultpngname = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				piconLocator.addSearchPath(value)
				attribs.remove((attrib, value))
		self.skinAttributes = attribs
		rc = Renderer.applySkin(self, desktop, parent)
		self.changed((self.CHANGED_DEFAULT,))
		return rc

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			if what[0] in (self.CHANGED_DEFAULT, self.CHANGED_ALL, self.CHANGED_SPECIFIC):
				pngname = piconLocator.getPiconName(self.source.text)
				if not exists(pngname): # no picon for service found
					pngname = self.defaultpngname
				if not config.usage.showpicon.value: # disabe picon on infobar
					pngname = self.defaultpngname
				if self.pngname != pngname:
					if pngname:
						self.instance.setScale(1)
						self.instance.setPixmapFromFile(pngname)
						self.instance.show()
					else:
						self.instance.hide()
					self.pngname = pngname
			elif what[0] == self.CHANGED_CLEAR:
				self.pngname = None
				self.instance.hide()
