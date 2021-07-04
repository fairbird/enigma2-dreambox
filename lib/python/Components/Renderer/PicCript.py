from os.path import isfile, join as pathjoin

from enigma import ePixmap, iServiceInformation

from Components.Pixmap import Pixmap
from Components.Renderer.Renderer import Renderer
from Tools.Directories import SCOPE_CURRENT_SKIN, fileReadLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]


class PicCript(Renderer):
	__module__ = __name__
	searchPaths = ("/usr/share/enigma2/", "/media/hdd/", "/media/usb/", "/media/ba/")
	condAccessIds = {
		"26": "BiSS",
		"01": "SEC",
		"06": "IRD",
		"17": "BET",
		"05": "VIA",
		"09": "NDS",
		"0B": "CONN",
		"0D": "CRW",
		"4A": "DRE",
		"0E": "PowerVU",
		"22": "Codicrypt",
		"07": "DigiCipher",
		"A1": "Rosscrypt",
		"56": "Verimatrix"
	}

	def __init__(self):
		Renderer.__init__(self)
		self.path = "cript"
		self.nameCache = {}
		self.pngName = ""
		self.picon_default = "picon_default.png"

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value,) in self.skinAttributes:
			if (attrib == "path"):
				self.path = value
			elif (attrib == "picon_default"):
				self.picon_default = value
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			pngName = ""
			if (what[0] != self.CHANGED_CLEAR) and isfile("/tmp/ecm.info"):
				sName = "NAG"
				service = self.source.service
				if service:
					info = service and service.info()
					if info:
						caids = info.getInfoObject(iServiceInformation.sCAIDs)
						if caids and len(caids) > 0:
							sName = self.matchCAId(caids)
				pngName = self.nameCache.get(sName, "")
				if (pngName == ""):
					pngName = self.findPicon(sName)
					if (pngName != ""):
						self.nameCache[sName] = pngName
			if (pngName == ""):
				pngName = self.nameCache.get("default", "")
				if (pngName == ""):
					pngName = self.findPicon("picon_default")
					if (pngName == ""):
						tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")
						if isfile(tmp):
							pngName = tmp
						self.nameCache["default"] = pngName
			if (self.pngName != pngName):
				self.pngName = pngName
				self.instance.setPixmapFromFile(self.pngName)

	def matchCAId(self, caids):
		lines = []
		for line in fileReadLines("/tmp/ecm.info", lines, source=MODULE_NAME):
			if line.startswith("caid: 0x"):
				for caid in caids:
					sName = self.condAccessIds.get(line[8:10])
					if sName is not None:
						return sName
		return "NAG"

	def findPicon(self, serviceName):
		for path in self.searchPaths:
			pngName = pathjoin(path, self.path, "%s.png" % serviceName)
			if isfile(pngName):
				return pngName
		return ""
