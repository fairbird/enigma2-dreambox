# -*- coding: utf-8 -*-
from Components.Console import Console
from Components.About import about
from Components.PackageInfo import PackageInfoHandler
from Components.Language import language
from Components.Sources.List import List
from Components.Opkg import OpkgComponent
from Components.Network import iNetwork
from Tools.Directories import resolveFilename, SCOPE_METADIR
from Tools.HardwareInfo import HardwareInfo
from time import time


class SoftwareTools(PackageInfoHandler):
	lastDownloadDate = None
	NetworkConnectionAvailable = None
	list_updating = False
	available_updates = 0
	available_updatelist = []
	available_packetlist = []
	installed_packetlist = {}

	def __init__(self):
		aboutInfo = about.getImageVersionString()
		if aboutInfo.startswith("dev-"):
			self.ImageVersion = 'Experimental'
		else:
			self.ImageVersion = 'Stable'
		self.language = language.getLanguage()[:2] # getLanguage returns e.g. "fi_FI" for "language_country"
		PackageInfoHandler.__init__(self, self.statusCallback, neededTag='ALL_TAGS', neededFlag=self.ImageVersion)
		self.directory = resolveFilename(SCOPE_METADIR)
		self.list = List([])
		self.NotifierCallback = None
		self.Console = Console()
		self.UpdateConsole = Console()
		self.cmdList = []
		self.unwanted_extensions = ('-dbg', '-dev', '-doc', '-staticdev', '-src')
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)

	def statusCallback(self, status, progress):
		pass

	def startSoftwareTools(self, callback=None):
		if callback is not None:
			self.NotifierCallback = callback
		iNetwork.checkNetworkState(self.checkNetworkCB)

	def checkNetworkCB(self, data):
		if data is not None:
			if data <= 2:
				self.NetworkConnectionAvailable = True
				self.getUpdates()
			else:
				self.NetworkConnectionAvailable = False
				self.getUpdates()

	def getUpdates(self, callback=None):
		if self.lastDownloadDate is None:
				if self.NetworkConnectionAvailable == True:
					self.lastDownloadDate = time()
					if not self.list_updating and callback is None:
						self.list_updating = True
						self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
					elif not self.list_updating and callback is not None:
						self.list_updating = True
						self.NotifierCallback = callback
						self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
					elif self.list_updating and callback is not None:
						self.NotifierCallback = callback
				else:
					self.list_updating = False
					if callback is not None:
						callback(False)
					elif self.NotifierCallback is not None:
						self.NotifierCallback(False)
		else:
			if self.NetworkConnectionAvailable == True:
				self.lastDownloadDate = time()
				if not self.list_updating and callback is None:
					self.list_updating = True
					self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
				elif not self.list_updating and callback is not None:
					self.list_updating = True
					self.NotifierCallback = callback
					self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
				elif self.list_updating and callback is not None:
					self.NotifierCallback = callback
			else:
				if self.list_updating and callback is not None:
						self.NotifierCallback = callback
						self.startOpkgListAvailable()
				else:
					self.list_updating = False
					if callback is not None:
						callback(False)
					elif self.NotifierCallback is not None:
						self.NotifierCallback(False)

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_ERROR:
			self.list_updating = False
			if self.NotifierCallback is not None:
				self.NotifierCallback(False)
		elif event == OpkgComponent.EVENT_DONE:
			if self.list_updating:
				self.startOpkgListAvailable()
		pass

	def startOpkgListAvailable(self, callback=None):
		if callback is not None:
			self.list_updating = True
		if self.list_updating:
			if not self.UpdateConsole:
				self.UpdateConsole = Console()
			cmd = self.opkg.opkg + " list"
			self.UpdateConsole.ePopen(cmd, self.OpkgListAvailableCB, callback)

	def OpkgListAvailableCB(self, result, retval, extra_args=None):
		(callback) = extra_args
		if result:
			if self.list_updating:
				self.available_packetlist = []
				for x in result.splitlines():
					tokens = x.split(' - ')
					name = tokens[0].strip()
					if not any(name.endswith(x) for x in self.unwanted_extensions):
						l = len(tokens)
						version = l > 1 and tokens[1].strip() or ""
						descr = l > 2 and tokens[2].strip() or ""
						self.available_packetlist.append([name, version, descr])
				if callback is None:
					self.startInstallMetaPackage()
				else:
					if self.UpdateConsole:
						if not self.UpdateConsole.appContainers:
								callback(True)
		else:
			self.list_updating = False
			if self.UpdateConsole:
				if not self.UpdateConsole.appContainers:
					if callback is not None:
						callback(False)

	def startInstallMetaPackage(self, callback=None):
		if callback is not None:
			self.list_updating = True
		if self.list_updating:
			if self.NetworkConnectionAvailable == True:
				if not self.UpdateConsole:
					self.UpdateConsole = Console()
				cmd = self.opkg.opkg + " install enigma2-meta enigma2-plugins-meta enigma2-skins-meta"
				self.UpdateConsole.ePopen(cmd, self.InstallMetaPackageCB, callback)
			else:
				self.InstallMetaPackageCB(True)

	def InstallMetaPackageCB(self, result, retval=None, extra_args=None):
		(callback) = extra_args
		if result:
			self.fillPackagesIndexList()
			if callback is None:
				self.startOpkgListInstalled()
			else:
				if self.UpdateConsole:
					if not self.UpdateConsole.appContainers:
							callback(True)
		else:
			self.list_updating = False
			if self.UpdateConsole:
				if not self.UpdateConsole.appContainers:
					if callback is not None:
						callback(False)

	def startOpkgListInstalled(self, callback=None):
		if callback is not None:
			self.list_updating = True
		if self.list_updating:
			if not self.UpdateConsole:
				self.UpdateConsole = Console()
			cmd = self.opkg.opkg + " list_installed"
			self.UpdateConsole.ePopen(cmd, self.OpkgListInstalledCB, callback)

	def OpkgListInstalledCB(self, result, retval, extra_args=None):
		(callback) = extra_args
		if result:
			self.installed_packetlist = {}
			for x in result.splitlines():
				tokens = x.split(' - ')
				name = tokens[0].strip()
				if not any(name.endswith(x) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 1 and tokens[1].strip() or ""
					self.installed_packetlist[name] = version
			for package in self.packagesIndexlist[:]:
				if not self.verifyPrerequisites(package[0]["prerequisites"]):
					self.packagesIndexlist.remove(package)
			for package in self.packagesIndexlist[:]:
				attributes = package[0]["attributes"]
				if "packagetype" in attributes:
					if attributes["packagetype"] == "internal":
						self.packagesIndexlist.remove(package)
			if callback is None:
				self.countUpdates()
			else:
				if self.UpdateConsole:
					if not self.UpdateConsole.appContainers:
							callback(True)
		else:
			self.list_updating = False
			if self.UpdateConsole:
				if not self.UpdateConsole.appContainers:
					if callback is not None:
						callback(False)

	def countUpdates(self, callback=None):
		self.available_updates = 0
		self.available_updatelist = []
		for package in self.packagesIndexlist[:]:
			attributes = package[0]["attributes"]
			packagename = attributes["packagename"]
			for x in self.available_packetlist:
				if x[0] == packagename:
					if packagename in self.installed_packetlist:
						if self.installed_packetlist[packagename] != x[1]:
							self.available_updates += 1
							self.available_updatelist.append([packagename])

		self.list_updating = False
		if self.UpdateConsole:
			if not self.UpdateConsole.appContainers:
				if callback is not None:
					callback(True)
					callback = None
				elif self.NotifierCallback is not None:
					self.NotifierCallback(True)
					self.NotifierCallback = None

	def startOpkgUpdate(self, callback=None):
		if not self.Console:
			self.Console = Console()
		cmd = self.opkg.opkg + " update"
		self.Console.ePopen(cmd, self.OpkgUpdateCB, callback)

	def OpkgUpdateCB(self, result, retval, extra_args=None):
		(callback) = extra_args
		if result:
			if self.Console:
				if not self.Console.appContainers:
					if callback is not None:
						callback(True)
						callback = None

	def cleanupSoftwareTools(self):
		self.list_updating = False
		if self.NotifierCallback is not None:
			self.NotifierCallback = None
		self.opkg.stop()
		if self.Console is not None:
			self.Console.killAll()
		if self.UpdateConsole is not None:
			self.UpdateConsole.killAll()

	def verifyPrerequisites(self, prerequisites):
		if "hardware" in prerequisites:
			hardware_found = False
			for hardware in prerequisites["hardware"]:
				if hardware == HardwareInfo().device_name:
					hardware_found = True
			if not hardware_found:
				return False
		return True


iSoftwareTools = SoftwareTools()
