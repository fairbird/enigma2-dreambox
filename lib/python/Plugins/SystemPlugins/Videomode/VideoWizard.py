# -*- coding: utf-8 -*-
from Plugins.SystemPlugins.Videomode.VideoHardware import video_hw
from Components.config import config, configfile
from Components.SystemInfo import BoxInfo
from Screens.HelpMenu import Rc
from Screens.Wizard import WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Tools.Directories import SCOPE_PLUGINS, resolveFilename
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap


MODELBox = BoxInfo.getItem("model")
has_dvi = BoxInfo.getItem("DreamBoxDVI")
has_scart = BoxInfo.getItem("SCART")


class VideoWizard(WizardLanguage, Rc):
	def __init__(self, session):
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/videowizard.xml")
		WizardLanguage.__init__(self, session, showSteps=False, showStepSlider=False)
		Rc.__init__(self)
		self.setTitle(_("Video Wizard"))
		self.avSwitch = video_hw
		self.portCount = 0
		self.port = None
		self.mode = None
		self.rate = None
		self["portpic"] = Pixmap()
		self["lab1"] = StaticText(_("OpenVision"))
		self["lab2"] = StaticText(_("Lets define enigma2 once more"))
		self["lab3"] = StaticText(_("Report problems to:"))
		self["lab4"] = StaticText(_("https://openvision.tech"))
		self["lab5"] = StaticText(_("Sources are available at:"))
		self["lab6"] = StaticText(_("https://github.com/OpenVisionE2"))

	def listPorts(self):  # Called by videowizard.xml
		ports = []
		for port in self.avSwitch.getPortList():
			if self.avSwitch.isPortUsed(port):
				descr = port
				if descr == "HDMI" and has_dvi:
					descr = "DVI"
				if descr == 'HDMI-PC' and has_dvi:
					descr = 'DVI-PC'
				if descr == "Scart" and BoxInfo.getItem("rca") and not has_scart:
					descr = "RCA"
				if descr == "Scart" and BoxInfo.getItem("avjack") and not has_scart:
					descr = "Jack"
				if port != "HDMI-PC":
					ports.append((descr, port))
		ports.sort(key=lambda x: x[0])
		# print("[VideoWizard] listPorts DEBUG: Ports=%s." % ports)
		return ports

	def listModes(self):  # Called by videowizard.xml
		def sortKey(name):
			return sortKeys.get(name[0], 6)

		modes = [(mode[0], mode[0]) for mode in self.avSwitch.getModeList(self.port)]

		sortKeys = {
			"720p": 1,
			"1080i": 2,
			"1080p": 3,
			"2160p": 4,
			"2160p30": 5,
			"smpte": 20
		}

		modes.sort(key=sortKey)
		# print("[VideoWizard] listModes DEBUG: port='%s', modes=%s." % (self.port, modes))
		return modes

	def listRates(self, mode=None):  # Called by videowizard.xml
		def sortKey(name):
			return {
				"50Hz": 1,
				"60Hz": 2
			}.get(name[0], 3)

		if mode is None:
			mode = self.mode
		rates = []
		for modes in self.avSwitch.getModeList(self.port):
			if modes[0] == mode:
				for rate in modes[1]:
					if rate == "auto" and not BoxInfo.getItem("Has24hz"):
						continue
					if self.port == "HDMI-PC":
						# print("[VideoWizard] listModes DEBUG: rate='%s'." % rate)
						if rate == "640x480":
							rates.insert(0, (rate, rate))
							continue
					rates.append((rate, rate))
		rates.sort(key=sortKey)
		# print("[VideoWizard] listRates DEBUG: port='%s', mode='%s', rates=%s." % (self.port, mode, rates))
		return rates

	def portSelectionMade(self, index):  # Called by videowizard.xml
		# print("[VideoWizard] inputSelectionMade DEBUG: index='%s'." % index)
		self.port = index
		self.portSelect(index)

	def portSelectionMoved(self):  # Called by videowizard.xml
		# print("[VideoWizard] inputSelectionMoved DEBUG: self.selection='%s'." % self.selection)
		if self["portpic"].instance is not None:
			picname = self.selection
			if picname == 'HDMI-PC':
				picname = "HDMI"
			if picname == 'HDMI' and has_dvi:
				picname = "DVI"
			if picname == 'HDMI-PC' and has_dvi:
				picname = "DVI"
			self["portpic"].instance.setPixmapFromFile(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/" + picname + ".png"))
		self.portSelect(self.selection)

	def portSelect(self, port):
		modeList = self.avSwitch.getModeList(self.selection)
		# print("[VideoWizard] inputSelect DEBUG: port='%s', modeList=%s." % (port, modeList))
		self.port = port
		if modeList:
			ratesList = self.listRates(modeList[0][0])
			self.avSwitch.setMode(port=port, mode=modeList[0][0], rate=ratesList[0][0])

	def modeSelectionMade(self, index):  # Called by videowizard.xml
		# print("[VideoWizard] modeSelectionMade DEBUG: index='%s'." % index)
		self.mode = index
		self.modeSelect(index)

	def modeSelectionMoved(self):  # Called by videowizard.xml
		# print("[VideoWizard] modeSelectionMoved DEBUG: self.selection='%s'." % self.selection)
		self.modeSelect(self.selection)

	def modeSelect(self, mode):
		rates = self.listRates(mode)
		# print("[VideoWizard] modeSelect DEBUG: rates=%s." % rates)
		if self.port == "HDMI" and mode in ("720p", "1080i", "1080p") and MODELBox not in ("dreamone", "dreamtwo"):
			self.rate = "multi"
			self.avSwitch.setMode(port=self.port, mode=mode, rate="multi")
		else:
			self.avSwitch.setMode(port=self.port, mode=mode, rate=rates[0][0])

	def rateSelectionMade(self, index):  # Called by videowizard.xml
		# print("[VideoWizard] rateSelectionMade DEBUG: index='%s'." % index)
		self.rate = index
		self.rateSelect(index)

	def rateSelectionMoved(self):  # Called by videowizard.xml
		# print("[VideoWizard] rateSelectionMade DEBUG: self.selection='%s'." % self.selection)
		self.rateSelect(self.selection)

	def rateSelect(self, rate):
		self.avSwitch.setMode(port=self.port, mode=self.mode, rate=rate)

	def keyNumberGlobal(self, number):
		if number in (1, 2, 3):
			if number == 1:
				self.avSwitch.saveMode("HDMI", "720p", "multi")
			elif number == 2:
				self.avSwitch.saveMode("HDMI", "1080i", "multi")
			elif number == 3:
				self.avSwitch.saveMode("Scart", "Multi", "multi")
			self.avSwitch.setConfiguredMode()
			self.close()
		WizardLanguage.keyNumberGlobal(self, number)

	def saveWizardChanges(self):  # Called by videowizard.xml
		self.avSwitch.saveMode(self.port, self.mode, self.rate)
		config.misc.videowizardenabled.value = False
		config.misc.videowizardenabled.save()
		configfile.save()

	def createSummary(self):
		return WizardSummary
