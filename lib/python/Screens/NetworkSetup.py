# -*- coding: utf-8 -*-
import os, re, random, netifaces
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.MessageBox import MessageBox
from Components.Network import iNetwork
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.Label import Label, MultiColorLabel
from Components.Pixmap import Pixmap, MultiPixmap
from Components.MenuList import MenuList
from Components.Console import Console
from Components.config import config, ConfigYesNo, ConfigIP, NoSave, ConfigText, ConfigPassword, ConfigSelection, ConfigSubsection
from Components.ConfigList import ConfigListScreen
from Components.PluginComponent import plugins
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Tools.Directories import resolveFilename, fileReadLines, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN, fileContains
from Tools.LoadPixmap import LoadPixmap
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, getDesktop, eConsoleAppContainer

MODULE_NAME = __name__.split(".")[-1]

macaddress = str(dict(netifaces.ifaddresses("eth0")[netifaces.AF_LINK][0])["addr"].upper())
config.macaddress = ConfigSubsection()
config.macaddress.interfaces = ConfigSelection(default="1", choices=[("1", "eth0")])
config.macaddress.mac = ConfigText(default="", fixed_size=False)
config.macaddress.change = ConfigText(default="%s" % macaddress)
configmac = config.macaddress


class NetworkAdapterSelection(Screen):

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Select a network adapter"))
		self.wlan_errortext = _("No working wireless network adapter found.\nPlease verify that you have attached a compatible WLAN device and your network is configured correctly.")
		self.lan_errortext = _("No working local network adapter found.\nPlease verify that you have attached a network cable and your network is configured correctly.")
		self.oktext = _("Press OK on your remote control to continue.")
		self.edittext = _("Press OK to edit the settings.")
		self.defaulttext = _("Press yellow to set this interface as default interface.")
		self.restartLanRef = None

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["key_menu"] = StaticText(_("MENU"))
		self["introduction"] = StaticText(self.edittext)

		self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions"],
				{
				"cancel": (self.close, _("Exit network interface list")),
				"ok": (self.okbuttonClick, _("Select interface")),
				})

		self["ColorActions"] = HelpableActionMap(self, ["ColorActions"],
				{
				"red": (self.close, _("Exit network interface list")),
				"green": (self.okbuttonClick, _("Select interface")),
				"blue": (self.openNetworkWizard, _("Use the network wizard to configure selected network adapter")),
				})

		self["DefaultInterfaceAction"] = HelpableActionMap(self, ["ColorActions"],
				{
				"yellow": (self.setDefaultInterface, [_("Set interface as default Interface"), _("* Only available if more than one interface is active.")]),
				})

		self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]

		if not self.adapters:
				self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getConfiguredAdapters()]

		if len(self.adapters) == 0:
				self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getInstalledAdapters()]

		self.list = []
		self["list"] = List(self.list)
		self.updateList()

		if len(self.adapters) == 1:
				self.onFirstExecBegin.append(self.okbuttonClick)
		self.onClose.append(self.cleanup)

	def buildInterfaceList(self, iface, name, default, active):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "div-h.png"))
		defaultpng = None
		activepng = None
		description = None
		interfacepng = None

		if not iNetwork.isWirelessInterface(iface):
				icon = {True: "icons/network_wired-active.png", False: "icons/network_wired-inactive.png", None: "icons/network_wired.png"}[active]
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, icon))
		elif iNetwork.isWirelessInterface(iface):
				icon = {True: "icons/network_wireless-active.png", False: "icons/network_wireless-inactive.png", None: "icons/network_wireless.png"}[active]
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, icon))

		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
				icon = "buttons/button_blue.png" if default else "buttons/button_blue_off.png"
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, icon))
		icon = "icons/lock_on.png" if active else "icons/lock_error.png"
		activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, icon))

		description = iNetwork.getFriendlyAdapterDescription(iface)

		return ((iface, name, description, interfacepng, defaultpng, activepng, divpng))

	def updateList(self):
		self.list = []
		default_gw = None
		iNetwork.getInterfaces()
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
				self["key_yellow"].setText(_("Default"))
				self["introduction"].setText(self.defaulttext)
				self["DefaultInterfaceAction"].setEnabled(True)
		else:
				self["key_yellow"].setText("")
				self["introduction"].setText(self.edittext)
				self["DefaultInterfaceAction"].setEnabled(False)

		if num_configured_if < 2 and os.path.exists("/etc/default_gw"):
				os.unlink("/etc/default_gw")

		if os.path.exists("/etc/default_gw"):
				fp = open('/etc/default_gw')
				result = fp.read()
				fp.close()
				default_gw = result

		for x in self.adapters:
				if x[1] == default_gw:
						default_int = True
				else:
						default_int = False
				if iNetwork.getAdapterAttribute(x[1], 'up'):
						active_int = True
				else:
						active_int = False
				self.list.append(self.buildInterfaceList(x[1], _(x[0]), default_int, active_int))

		if os.path.exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
				self["key_blue"].setText(_("Network wizard"))
		self["list"].setList(self.list)

	def setDefaultInterface(self):
		selection = self["list"].getCurrent()
		num_if = len(self.list)
		old_default_gw = None
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if os.path.exists("/etc/default_gw"):
				fp = open('/etc/default_gw')
				old_default_gw = fp.read()
				fp.close()
		if num_configured_if > 1 and (not old_default_gw or old_default_gw != selection[0]):
				fp = open('/etc/default_gw', 'w+')
				fp.write(selection[0])
				fp.close()
				self.restartLan()
		elif old_default_gw and num_configured_if < 2:
				os.unlink("/etc/default_gw")
				self.restartLan()

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		if selection is not None:
				self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, selection[0])

	def AdapterSetupClosed(self, *ret):
		if len(self.adapters) == 1:
				self.close()
		else:
				self.updateList()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopRestartConsole()
		iNetwork.stopGetInterfacesConsole()

	def restartLan(self):
		iNetwork.restartNetwork(self.restartLanDataAvail)
		self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while we configure your network..."), type=MessageBox.TYPE_INFO, enable_input=False)

	def restartLanDataAvail(self, data):
		if data:
				iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data:
				self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data:
				self.updateList()
				self.session.open(MessageBox, _("Finished configuring your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)

	def openNetworkWizard(self):
		if os.path.exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
				try:
						from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
				except ImportError:
						self.session.open(MessageBox, _("The network wizard extension is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)
				else:
						selection = self["list"].getCurrent()
						if selection is not None:
								self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, selection[0])

class NameserverSetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Configure nameservers"))
		self.backupNameserverList = iNetwork.getNameserverList()[:]
		print("[NetworkSetup] backup-list:", self.backupNameserverList)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions"],
				{
				"cancel": (self.keyCancel, _("Exit nameserver configuration")),
				})

		self["ColorActions"] = HelpableActionMap(self, ["ColorActions"],
				{
				"green": (self.save, _("Activate current configuration")),
				"left": (self.keyLeft, _("Change to another server")),
				"right": (self.keyRight, _("Change to another server")),
				})

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()
		strdns = str(self.backupNameserverList)
		dhcp_router = str([list(x[1]) for x in self.getNetworkRoutes()]).replace("[[", "[").replace("]]", "]").replace(",", ".").replace("].", "]")
		dns = strdns.replace("[[", "[").replace("]]", "]").replace(",", ".").replace("].", "]")
		if config.usage.dns.value not in ("google", "quad9security", "quad9nosecurity", "cloudflare", "opendns", "opendns-2", "nordvpn"):
			if dhcp_router != dns:
					config.usage.dns.default = "staticip"
					config.usage.dns.value = config.usage.dns.default
					servername = _("Static IP Router")
			else:
					config.usage.dns.default = "dhcp-router"
					config.usage.dns.value = config.usage.dns.default
					servername = _("DHCP Router")
		else:
			if "8. 8." in dns:
					servername = _("Google DNS")
			elif "9. 9. 9. 9" in dns:
					servername = _("Quad9 Security")
			elif "9. 9. 9. 10" in dns:
					servername = _("Quad9 No Security")
			elif "222. 222" in dns:
					servername = _("OpenDNS")
			elif "220. 222" in dns:
					servername = _("OpenDNS-2")
			elif "103. 86" in dns:
					servername = _("NordVPN")
			else:
					servername = _("Cloudflare")
		introduction = _("Press LEFT or RIGHT to choose another server. Then press Green Button to save it.")
		if "0. 0. 0. 0" in dns:
				introduction = _("WARNING: The DNS were not saved in your settings.\n\nActive server: %s\nDNS Active: %s\n\nIt is necessary to choose a server and save with GREEN button!.") % (servername, dns)
				self["introduction"] = StaticText(introduction)
		elif config.usage.dns.value == "staticip":
				self["introduction"] = StaticText(_("%s\n\nYou can use the DNS provided by other servers in Static IP Router.") % introduction)
		elif config.usage.dns.value == "dhcp-router":
				self["introduction"] = StaticText(_("%s\n\nIf the DNS of other servers are still kept in the DHCP Router, to get the DNS from your Router, reboot receiver.") % introduction)
		else:
				self["introduction"] = StaticText(introduction)

	def createSetup(self):
		self.nameservers = iNetwork.getNameserverList()
		if config.usage.dns.value == 'google':
				self.nameserverEntries = [NoSave(ConfigIP(default=[8, 8, 8, 8])), NoSave(ConfigIP(default=[8, 8, 4, 4]))]
		elif config.usage.dns.value == 'quad9security':
				self.nameserverEntries = [NoSave(ConfigIP(default=[9, 9, 9, 9])), NoSave(ConfigIP(default=[149, 112, 112, 112]))]
		elif config.usage.dns.value == 'quad9nosecurity':
				self.nameserverEntries = [NoSave(ConfigIP(default=[9, 9, 9, 10])), NoSave(ConfigIP(default=[149, 112, 112, 10]))]
		elif config.usage.dns.value == 'opendns':
				self.nameserverEntries = [NoSave(ConfigIP(default=[208, 67, 222, 222])), NoSave(ConfigIP(default=[208, 67, 220, 220]))]
		elif config.usage.dns.value == 'opendns-2':
				self.nameserverEntries = [NoSave(ConfigIP(default=[208, 67, 220, 222])), NoSave(ConfigIP(default=[208, 67, 222, 220]))]
		elif config.usage.dns.value == 'cloudflare':
				self.nameserverEntries = [NoSave(ConfigIP(default=[1, 1, 1, 1])), NoSave(ConfigIP(default=[1, 0, 0, 1]))]
		elif config.usage.dns.value == 'nordvpn':
				self.nameserverEntries = [NoSave(ConfigIP(default=[103, 86, 96, 100])), NoSave(ConfigIP(default=[103, 86, 99, 100]))]
		elif config.usage.dns.value == 'dhcp-router':
				self.nameserverEntries = [NoSave(ConfigIP(default=nameRoutes)) for nameRoutes in [list(x[1]) for x in self.getNetworkRoutes()]]
		else:
				self.nameserverEntries = [NoSave(ConfigIP(default=nameserver)) for nameserver in self.nameservers]
		self.list = []
		self["config"].list = self.list
		self.ListDNSServers = (_("DNS server name"), config.usage.dns)
		self.list.append(self.ListDNSServers)
		i = 1
		for x in self.nameserverEntries:
				self.list.append((_("DNS %d") % (i), x))
				i += 1

	def newConfig(self):
		if self["config"].getCurrent() == self.ListDNSServers:
				self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def save(self):
		self.RefreshNameServerUsed()
		iNetwork.clearNameservers()
		for nameserver in self.nameserverEntries:
				iNetwork.addNameserver(nameserver.value)
		iNetwork.writeNameserverConfig()
		Setup.keySave(self)

	def keyCancel(self):
		current = self["config"].getCurrent()[1]
		index = self["config"].getCurrentIndex()
		dnsList = self["config"].getList()
		self.dns = len(dnsList)
		if current:
				Setup.keySave(self) if self.dns <= index < self.dns + current else Setup.keyCancel(self)

	def RefreshNameServerUsed(self):
		print("[NetworkSetup] currentIndex:", self["config"].getCurrentIndex())
		index = self["config"].getCurrentIndex()
		if index < len(self.nameservers):
				self.createSetup()

	def getNetworkRoutes(self):
		# # cat /proc/net/route
		# Iface   Destination     Gateway         Flags   RefCnt  Use     Metric  Mask            MTU     Window  IRTT
		# eth0    00000000        FE08A8C0        0003    0       0       0       00000000        0       0       0
		# eth0    0008A8C0        00000000        0001    0       0       0       00FFFFFF        0       0       0
		gateways = []
		lines = []
		lines = fileReadLines("/proc/net/route", lines, source=MODULE_NAME)
		headings = lines.pop(0)
		for line in lines:
				data = line.split()
				if data[1] == "00000000" and int(data[3]) & 0x03 and data[7] == "00000000":  # If int(flags) & 0x03 is True this is a gateway (0x02) and it is up (0x01).
						gateways.append((data[0], tuple(reversed([int(data[2][x:x + 2], 16) for x in range(0, len(data[2]), 2)]))))
		return gateways


class NetworkMacSetup(Screen, ConfigListScreen):

	if getDesktop(0).size().width() == 1920:
		skin = """
		<screen name="NetworkMacSetup" position="center,center" size="912,568" title="MAC address setup" >
				<eLabel position="20,547" size="200,4" foregroundColor="#00ff2525" backgroundColor="#00ff2525" zPosition="1"/>
				<eLabel position="238,547" size="200,4" foregroundColor="#00389416" backgroundColor="#00389416" zPosition="1"/>
				<eLabel position="456,547" size="200,4" foregroundColor="#00bab329" backgroundColor="#00bab329" zPosition="1"/>
				<eLabel position="675,547" size="200,4" foregroundColor="#00ff2525" backgroundColor="#000080ff" zPosition="1"/>
				<widget source="key_red" render="Label" position="20,506" zPosition="1" size="200,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
				<widget source="key_green" render="Label" position="238,506" zPosition="1" size="200,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
				<widget source="key_yellow" render="Label" position="456,506" zPosition="1" size="200,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
				<widget source="key_blue" render="Label" position="660,506" zPosition="1" size="230,40" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
				<widget name="config" itemHeight="45" font="Regular;33" position="10,50" size="890,308" scrollbarMode="showOnDemand" />
				<!--widget source="introduction" render="Label" position="48,390" size="803,67" zPosition="10" font="Regular;30" horizontalAlignment="center" verticalAlignment="center" transparent="1" foregroundColor="#00ff2525" /-->
		</screen>"""
	else:
		skin = """
		<screen name="NetworkMacSetup" position="center,center" size="720,400" title="MAC address setup" >
				<eLabel position="25,385" size="150,2" foregroundColor="#00ff2525" backgroundColor="#00ff2525" zPosition="1"/>
				<eLabel position="200,385" size="150,2" foregroundColor="#00389416" backgroundColor="#00389416" zPosition="1"/>
				<eLabel position="374,385" size="150,4" foregroundColor="#00bab329" backgroundColor="#00bab329" zPosition="1"/>
				<eLabel position="545,385" size="150,4" foregroundColor="#00ff2525" backgroundColor="#000080ff" zPosition="1"/>
				<widget source="key_red" render="Label" position="25,345" zPosition="1" size="150,40" font="Regular;22" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
				<widget source="key_green" render="Label" position="200,345" zPosition="1" size="150,40" font="Regular;22" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
				<widget source="key_yellow" render="Label" position="374,345" zPosition="1" size="150,40" font="Regular;22" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
				<widget source="key_blue" render="Label" position="535,345" zPosition="1" size="170,40" font="Regular;22" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
				<widget name="config" position="10,50" size="700,235" scrollbarMode="showOnDemand" />
				<!--widget source="introduction" render="Label" position="80,200" size="560,50" zPosition="10" font="Regular;21" horizontalAlignment="center" verticalAlignment="center" transparent="1" foregroundColor="#00ff2525"/-->
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		Screen.setTitle(self, _('MAC Address Settings'))
		self['key_red'] = StaticText(_('Cancel'))
		self['key_green'] = StaticText(_('Change Now !'))
		self['key_yellow'] = StaticText(_('Random'))
		self['key_blue'] = StaticText(_('Restore Original'))
		self['introduction'] = StaticText(_('Press OK to set the MAC-address.'))

		self['OkCancelActions'] = HelpableActionMap(self, 'OkCancelActions',
				{
						'cancel': (self.cancel, _('Exit nameserver configuration')),
						'ok': (self.ok, _('Activate current configuration')),
				})

		self['ColorActions'] = HelpableActionMap(self, 'ColorActions',
				{
						'red': (self.cancel, _('Exit MAC-address configuration')),
						'green': (self.ok, _('Activate MAC-address configuration')),
						'yellow': (self.newRandom, _('Random')),
						'blue': (self.OriginalMac, _('Restore Original')),
				})

		self.writereadMAC()
		self.createSetup()


	def createSetup(self):
		self.list = []
		self.list.append((_("Interface to change MAC"), config.macaddress.interfaces))
		self.list.append((_("Set new MAC address"), config.macaddress.change))
		self["config"].list = self.list

	def macCurrent(self):
		macaddress = configmac.mac.value
		macdata = open("/etc/enigma2/hwmac", "w")
		macdata.write(macaddress)
		macdata.close()

	def writereadMAC(self):
		configmac.mac.value = str(dict(netifaces.ifaddresses("eth0")[netifaces.AF_LINK][0])["addr"].upper())
		self.macCurrent()
		with open("/etc/enigma2/hwmac") as hwmac:
				self.macUpdated = hwmac.read()

		config.macaddress.change.value = str(self.macUpdated.upper().strip())

	def ok(self):
		self.session.openWithCallback(self.changeMac, MessageBox, _("Do you want to change the current MAC address?\n") + configmac.mac.value, MessageBox.TYPE_YESNO)

	def changeMac(self, answer=False):
		self.Console = Console()
		if answer:
				if re.match("\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}", config.macaddress.change.value):
						config.macaddress.change.save()
						self.Console.ePopen("ifconfig eth0 down && ifconfig eth0 down hw ether " + str(config.macaddress.change.value) + " ifconfig eth0 up")
						self.checkInterfaces()
						self.Console.ePopen("ifdown -v -f eth0; ifup -v eth0")
						try:
								CurrentIP = str(dict(netifaces.ifaddresses("eth0")[netifaces.AF_INET][0])["addr"])
						except:
								CurrentIP = "unknown"
						self.session.open(MessageBox, _("MAC address successfully changed.\nNew MAC address is: ") + config.macaddress.change.value + "\nIP: " + CurrentIP, MessageBox.TYPE_INFO, timeout=10)
						self.close()
		else:
				self.session.open(MessageBox, _("Not a valid MAC address"), MessageBox.TYPE_INFO, timeout=10)

	def backMac(self, answer=False):
		if answer:
				self.Console = Console()
				os.system("macadr=`echo $(ethtool -P eth0 | awk '{print $3}')`&& echo $macadr > /etc/enigma2/hwmac")
				f=open("/etc/enigma2/hwmac")
				config.macaddress.change.value=f.read()
				f.close()
				if re.match("\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}", config.macaddress.change.value):
						config.macaddress.change.save()
						self.Console.ePopen("ifconfig eth0 down && ifconfig eth0 down hw ether " + str(config.macaddress.change.value) + " ifconfig eth0 up")
						self.checkInterfaces()
						self.Console.ePopen("ifdown -v -f eth0; ifup -v eth0")
						try:
								CurrentIP = str(dict(netifaces.ifaddresses("eth0")[netifaces.AF_INET][0])["addr"])
						except:
								CurrentIP = "unknown"
						self.session.open(MessageBox, _("MAC address successfully changed.\nNew MAC address is: ") + config.macaddress.change.value + "\nIP: " + CurrentIP, MessageBox.TYPE_INFO, timeout=10)
						self.close()
		else:
				self.session.open(MessageBox, _("Not a valid MAC address"), MessageBox.TYPE_INFO, timeout=10)

	def checkInterfaces(self):
		with open("/etc/network/interfaces") as interfaces:
						interfacesdata = interfaces.read()
		if "hwaddress ether" in interfacesdata:
						oldMac = re.findall(r"hwaddress ether (\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2})", interfacesdata)[0]
						interfacesdata = interfacesdata.replace(oldMac, config.macaddress.change.value)
						with open("/etc/network/interfaces", "w") as interfaces:
								interfaces.write(interfacesdata)
		else:
						interfacesdata = open("/etc/network/interfaces", "r").readlines()
						interfaceswrite = open("/etc/network/interfaces", "w")
						for line in interfacesdata:
								interfaceswrite.write(line)
								if "iface eth0 inet dhcp" in line or "iface eth0 inet static" in line:
										newmac = "      hwaddress ether " + config.macaddress.change.value
										interfaceswrite.write(newmac + "\n")
						interfaceswrite.close()


	def OriginalMac(self):
		self.session.openWithCallback(self.backMac, MessageBox, _("Do you want to back the Original MAC address?\n") , MessageBox.TYPE_YESNO)

	def newRandom(self):
		config.macaddress.change.value = self.GenerateMacAddress()
		self['config'].invalidateCurrent()

	def GenerateMacAddress(self):
		random.choice('0123456789abcdef')
		create_random_mac = "00:1d:ec:%02x:%02x:%02x" % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
		MAC = config.macaddress.change.value
		MAC = create_random_mac
		return create_random_mac

	def cancel(self):
		self.close()


class AdapterSetup(ConfigListScreen, Screen):
		def __init__(self, session, networkinfo, essid=None):
				Screen.__init__(self, session, enableHelp=True)
				self.setTitle(_("Network setup"))
				if isinstance(networkinfo, (list, tuple)):
						self.iface = networkinfo[0]
						self.essid = networkinfo[1]
				else:
						self.iface = networkinfo
						self.essid = essid

				self.extended = None
				self.applyConfigRef = None
				self.finished_cb = None
				self.oktext = _("Press OK on your remote control to continue.")
				self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")

				self.createConfig()

				self.list = []
				ConfigListScreen.__init__(self, self.list, session=self.session, fullUI=True)
				self.createSetup()
				self.onLayoutFinish.append(self.layoutFinished)
				self.onClose.append(self.cleanup)

				self["DNS1text"] = StaticText(_("Primary DNS"))
				self["DNS2text"] = StaticText(_("Secondary DNS"))
				self["DNS1"] = StaticText()
				self["DNS2"] = StaticText()
				self["introduction"] = StaticText(_("Current settings:"))

				self["IPtext"] = StaticText(_("IP address"))
				self["Netmasktext"] = StaticText(_("Netmask"))
				self["Gatewaytext"] = StaticText(_("Gateway"))

				self["IP"] = StaticText()
				self["Mask"] = StaticText()
				self["Gateway"] = StaticText()

				self["Adaptertext"] = StaticText(_("Network:"))
				self["Adapter"] = StaticText()
				self["introduction2"] = StaticText(_("Press OK to activate the settings."))
				self["key_red"] = StaticText(_("Cancel"))
				self["key_green"] = StaticText(_("Save"))
				self["key_blue"] = StaticText(_("Edit DNS"))

				self["VKeyIcon"] = Boolean(False)
				self["HelpWindow"] = Pixmap()
				self["HelpWindow"].hide()

		def layoutFinished(self):
				self["DNS1"].setText(self.primaryDNS.getText())
				self["DNS2"].setText(self.secondaryDNS.getText())
				if self.ipConfigEntry.getText() is not None:
						if self.ipConfigEntry.getText() == "0.0.0.0":
								self["IP"].setText(_("N/A"))
						else:
								self["IP"].setText(self.ipConfigEntry.getText())
				else:
						self["IP"].setText(_("N/A"))
				if self.netmaskConfigEntry.getText() is not None:
						if self.netmaskConfigEntry.getText() == "0.0.0.0":
								self["Mask"].setText(_("N/A"))
						else:
								self["Mask"].setText(self.netmaskConfigEntry.getText())
				else:
						self["IP"].setText(_("N/A"))
				if iNetwork.getAdapterAttribute(self.iface, "gateway"):
						if self.gatewayConfigEntry.getText() == "0.0.0.0":
								self["Gatewaytext"].setText(_("Gateway"))
								self["Gateway"].setText(_("N/A"))
						else:
								self["Gatewaytext"].setText(_("Gateway"))
								self["Gateway"].setText(self.gatewayConfigEntry.getText())
				else:
						self["Gateway"].setText("")
						self["Gatewaytext"].setText("")
				self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))

		def createConfig(self):
				self.InterfaceEntry = None
				self.dhcpEntry = None
				self.gatewayEntry = None
				self.hiddenSSID = None
				self.wlanSSID = None
				self.encryption = None
				self.encryptionType = None
				self.encryptionKey = None
				self.encryptionlist = None
				self.weplist = None
				self.wsconfig = None
				self.default = None
				self.ws = None

				if iNetwork.isWirelessInterface(self.iface) and hasattr(config.plugins, "wlan"):
						from Plugins.SystemPlugins.WirelessLan.Wlan import wpaSupplicant
						self.ws = wpaSupplicant()
						self.encryptionlist = []
						self.encryptionlist.append(("Unencrypted", _("Unencrypted")))
						self.encryptionlist.append(("WEP", "WEP"))
						self.encryptionlist.append(("WPA", "WPA"))
						if not os.path.exists("/tmp/bcm/" + self.iface):
								self.encryptionlist.append(("WPA/WPA2", "WPA/WPA2"))
						self.encryptionlist.append(("WPA2", "WPA2"))
						self.weplist = []
						self.weplist.append("ASCII")
						self.weplist.append("HEX")

						self.wsconfig = self.ws.loadConfig(self.iface)
						if self.essid is None:
								self.essid = self.wsconfig['ssid']

						config.plugins.wlan.hiddenessid = NoSave(ConfigYesNo(default=self.wsconfig['hiddenessid']))
						config.plugins.wlan.essid = NoSave(ConfigText(default=self.essid, visible_width=50, fixed_size=False))
						config.plugins.wlan.encryption = NoSave(ConfigSelection(self.encryptionlist, default=self.wsconfig['encryption']))
						config.plugins.wlan.wepkeytype = NoSave(ConfigSelection(self.weplist, default=self.wsconfig['wepkeytype']))
						config.plugins.wlan.psk = NoSave(ConfigPassword(default=self.wsconfig['key'], visible_width=50, fixed_size=False))

				self.activateInterfaceEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "up") or False))
				self.dhcpConfigEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "dhcp") or False))
				self.ipConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "ip")) or [0, 0, 0, 0])
				self.netmaskConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "netmask") or [255, 0, 0, 0]))
				if iNetwork.getAdapterAttribute(self.iface, "gateway"):
						self.dhcpdefault = True
				else:
						self.dhcpdefault = False
				self.hasGatewayConfigEntry = NoSave(ConfigYesNo(default=self.dhcpdefault or False))
				self.gatewayConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "gateway") or [0, 0, 0, 0]))
				nameserver = (iNetwork.getNameserverList() + [[0, 0, 0, 0]] * 2)[0:2]
				self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
				self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))

		def createSetup(self):
				self.list = []
				self.InterfaceEntry = (_("Use interface"), self.activateInterfaceEntry)

				self.list.append(self.InterfaceEntry)
				if self.activateInterfaceEntry.value:
						self.dhcpEntry = (_("Use DHCP"), self.dhcpConfigEntry)
						self.list.append(self.dhcpEntry)
						if not self.dhcpConfigEntry.value:
								self.list.append((_('IP address'), self.ipConfigEntry))
								self.list.append((_('Netmask'), self.netmaskConfigEntry))
								self.gatewayEntry = (_('Use a gateway'), self.hasGatewayConfigEntry)
								self.list.append(self.gatewayEntry)
								if self.hasGatewayConfigEntry.value:
										self.list.append((_('Gateway'), self.gatewayConfigEntry))

						self.extended = None
						self.configStrings = None
						for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
								callFnc = p.fnc["ifaceSupported"](self.iface)
								if callFnc is not None:
										if "WlanPluginEntry" in p.fnc: # internally used only for WLAN Plugin
												self.extended = callFnc
												if "configStrings" in p.fnc:
														self.configStrings = p.fnc["configStrings"]
												isExistBcmWifi = os.path.exists("/tmp/bcm/" + self.iface)
												if not isExistBcmWifi:
														self.hiddenSSID = (_("Hidden network"), config.plugins.wlan.hiddenessid)
														self.list.append(self.hiddenSSID)
												self.wlanSSID = (_("Network name (SSID)"), config.plugins.wlan.essid)
												self.list.append(self.wlanSSID)
												self.encryption = (_("Encryption"), config.plugins.wlan.encryption)
												self.list.append(self.encryption)
												if not isExistBcmWifi:
														self.encryptionType = (_("Encryption key type"), config.plugins.wlan.wepkeytype)
												self.encryptionKey = (_("Encryption key"), config.plugins.wlan.psk)

												if config.plugins.wlan.encryption.value != "Unencrypted":
														if config.plugins.wlan.encryption.value == 'WEP':
																if not isExistBcmWifi:
																		self.list.append(self.encryptionType)
														self.list.append(self.encryptionKey)
				self["config"].list = self.list

		def KeyBlue(self):
				self.session.openWithCallback(self.NameserverSetupClosed, NameserverSetup)

		def newConfig(self):
				if self["config"].getCurrent() == self.InterfaceEntry:
						self.createSetup()
				if self["config"].getCurrent() == self.dhcpEntry:
						self.createSetup()
				if self["config"].getCurrent() == self.gatewayEntry:
						self.createSetup()
				if iNetwork.isWirelessInterface(self.iface):
						if self["config"].getCurrent() == self.encryption:
								self.createSetup()

		def keyLeft(self):
				ConfigListScreen.keyLeft(self)
				self.newConfig()

		def keyRight(self):
				ConfigListScreen.keyRight(self)
				self.newConfig()

		def keySave(self):
				self.hideInputHelp()
				if self["config"].isChanged():
						self.session.openWithCallback(self.keySaveConfirm, MessageBox, (_("Are you sure you want to activate this network configuration?\n\n") + self.oktext))
				else:
						if self.finished_cb:
								self.finished_cb()
						else:
								self.close('cancel')

		def keySaveConfirm(self, ret=False):
				if ret:
						num_configured_if = len(iNetwork.getConfiguredAdapters())
						if num_configured_if >= 1:
								if self.iface in iNetwork.getConfiguredAdapters():
										self.applyConfig(True)
								else:
										self.session.openWithCallback(self.secondIfaceFoundCB, MessageBox, _("A second configured interface has been found.\n\nDo you want to disable the second network interface?"), default=True)
						else:
								self.applyConfig(True)
				else:
						self.keyCancel()

		def secondIfaceFoundCB(self, data):
				if not data:
						self.applyConfig(True)
				else:
						configuredInterfaces = iNetwork.getConfiguredAdapters()
						for interface in configuredInterfaces:
								if interface == self.iface:
										continue
								iNetwork.setAdapterAttribute(interface, "up", False)
						iNetwork.deactivateInterface(configuredInterfaces, self.deactivateSecondInterfaceCB)

		def deactivateSecondInterfaceCB(self, data):
				if data:
						self.applyConfig(True)

		def applyConfig(self, ret=False):
				if ret:
						self.applyConfigRef = None
						iNetwork.setAdapterAttribute(self.iface, "up", self.activateInterfaceEntry.value)
						iNetwork.setAdapterAttribute(self.iface, "dhcp", self.dhcpConfigEntry.value)
						iNetwork.setAdapterAttribute(self.iface, "ip", self.ipConfigEntry.value)
						iNetwork.setAdapterAttribute(self.iface, "netmask", self.netmaskConfigEntry.value)
						if self.hasGatewayConfigEntry.value:
								iNetwork.setAdapterAttribute(self.iface, "gateway", self.gatewayConfigEntry.value)
						else:
								iNetwork.removeAdapterAttribute(self.iface, "gateway")

						if self.extended is not None and self.configStrings is not None:
								iNetwork.setAdapterAttribute(self.iface, "configStrings", self.configStrings(self.iface))
								if self.ws:
										self.ws.writeConfig(self.iface)

						if not self.activateInterfaceEntry.value:
								iNetwork.deactivateInterface(self.iface, self.deactivateInterfaceCB)
								iNetwork.writeNetworkConfig()
								self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type=MessageBox.TYPE_INFO, enable_input=False)
						else:
								if not self.oldInterfaceState:
										iNetwork.activateInterface(self.iface, self.deactivateInterfaceCB)
								else:
										iNetwork.deactivateInterface(self.iface, self.activateInterfaceCB)
								iNetwork.writeNetworkConfig()
								self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type=MessageBox.TYPE_INFO, enable_input=False)
				else:
						self.keyCancel()

		def deactivateInterfaceCB(self, data):
				if data:
						self.applyConfigDataAvail(True)

		def activateInterfaceCB(self, data):
				if data:
						iNetwork.activateInterface(self.iface, self.applyConfigDataAvail)

		def applyConfigDataAvail(self, data):
				if data:
						iNetwork.getInterfaces(self.getInterfacesDataAvail)

		def getInterfacesDataAvail(self, data):
				if data:
						self.applyConfigRef.close(True)

		def applyConfigfinishedCB(self, data):
				if data:
						if self.finished_cb:
								self.session.openWithCallback(lambda x: self.finished_cb(), MessageBox, _("Your network configuration has been activated."), type=MessageBox.TYPE_INFO, timeout=10)
						else:
								self.session.openWithCallback(self.ConfigfinishedCB, MessageBox, _("Your network configuration has been activated."), type=MessageBox.TYPE_INFO, timeout=10)

		def ConfigfinishedCB(self, data):
				if data is not None and data:
						self.close('ok')

		def keyCancelConfirm(self, result):
				if not result:
						return
				if not self.oldInterfaceState:
						iNetwork.deactivateInterface(self.iface, self.keyCancelCB)
				else:
						self.close('cancel')

		def keyCancel(self):
				self.hideInputHelp()
				if self["config"].isChanged():
						self.session.openWithCallback(self.keyCancelConfirm, MessageBox, _("Really close without saving settings?"))
				else:
						self.close('cancel')

		def keyCancelCB(self, data):
				if data is not None:
						if data:
								self.close('cancel')

		def runAsync(self, finished_cb):
				self.finished_cb = finished_cb
				self.keySave()

		def NameserverSetupClosed(self, *ret):
				iNetwork.loadNameserverConfig()
				nameserver = (iNetwork.getNameserverList() + [[0, 0, 0, 0]] * 2)[0:2]
				self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
				self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))
				self.createSetup()
				self.layoutFinished()

		def cleanup(self):
				iNetwork.stopLinkStateConsole()

		def hideInputHelp(self):
				current = self["config"].getCurrent()
				if current == self.wlanSSID:
						if current[1].help_window.instance is not None:
								current[1].help_window.instance.hide()
				elif current == self.encryptionKey and config.plugins.wlan.encryption.value != "Unencrypted":
						if current[1].help_window.instance is not None:
								current[1].help_window.instance.hide()


class AdapterSetupConfiguration(Screen):
		def __init__(self, session, iface):
				Screen.__init__(self, session, enableHelp=True)
				self.setTitle(_("Network configuration"))
				self.iface = iface
				self.restartLanRef = None
				self.LinkState = None
				self.mainmenu = self.genMainMenu()
				self["menulist"] = MenuList(self.mainmenu)
				self["key_red"] = StaticText(_("Close"))
				self["description"] = StaticText()
				self["IFtext"] = StaticText()
				self["IF"] = StaticText()
				self["Statustext"] = StaticText()
				self["statuspic"] = MultiPixmap()
				self["statuspic"].hide()

				self.oktext = _("Press OK on your remote control to continue.")
				self.reboottext = _("Your receiver will restart after pressing OK on your remote control.")
				self.errortext = _("No working wireless network interface found.\n Please verify that you have attached a compatible WLAN device or enable your local network interface.")
				self.missingwlanplugintxt = _("The wireless LAN plugin is not installed!\nPlease install it.")

				self["WizardActions"] = HelpableActionMap(self, ["WizardActions"],
						{
						"up": (self.up, _("move up to previous entry")),
						"down": (self.down, _("move down to next entry")),
						"left": (self.left, _("move up to first entry")),
						"right": (self.right, _("move down to last entry")),
						})

				self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions"],
						{
						"cancel": (self.close, _("exit networkadapter setup menu")),
						"ok": (self.ok, _("select menu entry")),
						})

				self["ColorActions"] = HelpableActionMap(self, ["ColorActions"],
						{
						"red": (self.close, _("exit networkadapter setup menu")),
						})

				self["actions"] = NumberActionMap(["WizardActions", "ShortcutActions"],
				{
						"ok": self.ok,
						"back": self.close,
						"up": self.up,
						"down": self.down,
						"red": self.close,
						"left": self.left,
						"right": self.right,
				}, -2)

				self.updateStatusbar()
				self.onLayoutFinish.append(self.layoutFinished)
				self.onClose.append(self.cleanup)

		def queryWirelessDevice(self, iface):
				try:
						from pythonwifi.iwlibs import Wireless
						import errno
				except ImportError:
						return False
				else:
						try:
								ifobj = Wireless(iface) # a Wireless NIC Object
								wlanresponse = ifobj.getAPaddr()
						except IOError as xxx_todo_changeme:
								(error_no, error_str) = xxx_todo_changeme.args
								if error_no in (errno.EOPNOTSUPP, errno.ENODEV, errno.EPERM):
										return False
								else:
										print("error: ", error_no, error_str)
										return True
						else:
								return True

		def ok(self):
				self.cleanup()
				if self["menulist"].getCurrent()[1] == 'edit':
						if iNetwork.isWirelessInterface(self.iface):
								try:
										from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
								except ImportError:
										self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
								else:
										if self.queryWirelessDevice(self.iface):
												self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface)
										else:
												self.showErrorMessage() # Display Wlan not available Message
						else:
								self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface)
				if self["menulist"].getCurrent()[1] == 'test':
						self.session.open(NetworkAdapterTest, self.iface)
				if self["menulist"].getCurrent()[1] == 'dns':
						self.session.open(NameserverSetup)
				if self["menulist"].getCurrent()[1] == "mac":
						self.session.open(NetworkMacSetup)
				if self["menulist"].getCurrent()[1] == 'scanwlan':
						try:
								from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
						except ImportError:
								self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
						else:
								if self.queryWirelessDevice(self.iface):
										self.session.openWithCallback(self.WlanScanClosed, WlanScan, self.iface)
								else:
										self.showErrorMessage() # Display Wlan not available Message
				if self["menulist"].getCurrent()[1] == 'wlanstatus':
						try:
								from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
						except ImportError:
								self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
						else:
								if self.queryWirelessDevice(self.iface):
										self.session.openWithCallback(self.WlanStatusClosed, WlanStatus, self.iface)
								else:
										self.showErrorMessage() # Display Wlan not available Message
				if self["menulist"].getCurrent()[1] == 'lanrestart':
						self.session.openWithCallback(self.restartLan, MessageBox, (_("Are you sure you want to restart your network interfaces?\n\n") + self.oktext))
				if self["menulist"].getCurrent()[1] == 'openwizard':
						from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
						self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, self.iface)
				if self["menulist"].getCurrent()[1][0] == 'extendedSetup':
						self.extended = self["menulist"].getCurrent()[1][2]
						self.extended(self.session, self.iface)

		def up(self):
				self["menulist"].up()
				self.loadDescription()

		def down(self):
				self["menulist"].down()
				self.loadDescription()

		def left(self):
				self["menulist"].pageUp()
				self.loadDescription()

		def right(self):
				self["menulist"].pageDown()
				self.loadDescription()

		def layoutFinished(self):
				idx = 0
				self["menulist"].moveToIndex(idx)
				self.loadDescription()

		def loadDescription(self):
				if self["menulist"].getCurrent()[1] == 'edit':
						self["description"].setText(_("Edit the network configuration of your receiver.\n") + self.oktext)
				if self["menulist"].getCurrent()[1] == 'test':
						self["description"].setText(_("Test the network configuration of your receiver.\n") + self.oktext)
				if self["menulist"].getCurrent()[1] == 'dns':
						self["description"].setText(_("Edit the nameserver configuration of your receiver.\n") + self.oktext)
				if self["menulist"].getCurrent()[1] == 'scanwlan':
						self["description"].setText(_("Scan your network for wireless access points and connect to them using your selected wireless device.\n") + self.oktext)
				if self["menulist"].getCurrent()[1] == 'wlanstatus':
						self["description"].setText(_("Shows the state of your wireless LAN connection.\n") + self.oktext)
				if self["menulist"].getCurrent()[1] == 'lanrestart':
						self["description"].setText(_("Restart your network connection and interfaces.\n") + self.oktext)
				if self["menulist"].getCurrent()[1] == 'openwizard':
						self["description"].setText(_("Use the network wizard to configure your network\n") + self.oktext)
				if self["menulist"].getCurrent()[1][0] == 'extendedSetup':
						self["description"].setText(_(self["menulist"].getCurrent()[1][1]) + self.oktext)
				if self["menulist"].getCurrent()[1] == "mac":
						self["description"].setText(_("Set the MAC address of your receiver\n.") + self.oktext)

		def updateStatusbar(self, data=None):
				self.mainmenu = self.genMainMenu()
				self["menulist"].l.setList(self.mainmenu)
				self["IFtext"].setText(_("Network:"))
				self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
				self["Statustext"].setText(_("Link:"))

				if iNetwork.isWirelessInterface(self.iface):
						try:
								from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
						except:
								self["statuspic"].setPixmapNum(1)
								self["statuspic"].show()
						else:
								iStatus.getDataForInterface(self.iface, self.getInfoCB)
				else:
						iNetwork.getLinkState(self.iface, self.dataAvail)

		def doNothing(self):
				pass

		def genMainMenu(self):
				menu = []
				menu.append((_("Adapter settings"), "edit"))
				menu.append((_("Nameserver settings"), "dns"))
				menu.append((_("Network test"), "test"))
				menu.append((_("Restart network"), "lanrestart"))
				menu.append((_("Network MAC settings"), "mac"))

				self.extended = None
				self.extendedSetup = None
				for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
						callFnc = p.fnc["ifaceSupported"](self.iface)
						if callFnc is not None:
								self.extended = callFnc
								if "WlanPluginEntry" in p.fnc: # internally used only for WLAN Plugin
										menu.append((_("Scan wireless networks"), "scanwlan"))
										if iNetwork.getAdapterAttribute(self.iface, "up"):
												menu.append((_("Show WLAN status"), "wlanstatus"))
								else:
										if "menuEntryName" in p.fnc:
												menuEntryName = p.fnc["menuEntryName"](self.iface)
										else:
												menuEntryName = _('Extended setup...')
										if "menuEntryDescription" in p.fnc:
												menuEntryDescription = p.fnc["menuEntryDescription"](self.iface)
										else:
												menuEntryDescription = _('Extended network setup plugin...')
										self.extendedSetup = ('extendedSetup', menuEntryDescription, self.extended)
										menu.append((menuEntryName, self.extendedSetup))

				if os.path.exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
						menu.append((_("Network wizard"), "openwizard"))

				return menu

		def AdapterSetupClosed(self, *ret):
				if ret is not None and len(ret):
						if ret[0] == 'ok' and (iNetwork.isWirelessInterface(self.iface) and iNetwork.getAdapterAttribute(self.iface, "up")):
								try:
										from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
								except ImportError:
										self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
								else:
										if self.queryWirelessDevice(self.iface):
												self.session.openWithCallback(self.WlanStatusClosed, WlanStatus, self.iface)
										else:
												self.showErrorMessage() # Display Wlan not available Message
						else:
								self.updateStatusbar()
				else:
						self.updateStatusbar()

		def WlanStatusClosed(self, *ret):
				if ret is not None and len(ret):
						from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
						iStatus.stopWlanConsole()
						self.updateStatusbar()

		def WlanScanClosed(self, *ret):
				if ret[0] is not None:
						self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface, ret[0])
				else:
						from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
						iStatus.stopWlanConsole()
						self.updateStatusbar()

		def restartLan(self, ret=False):
				if ret:
						iNetwork.restartNetwork(self.restartLanDataAvail)
						self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while your network is restarting..."), type=MessageBox.TYPE_INFO, enable_input=False)

		def restartLanDataAvail(self, data):
				if data:
						iNetwork.getInterfaces(self.getInterfacesDataAvail)

		def getInterfacesDataAvail(self, data):
				if data:
						self.restartLanRef.close(True)

		def restartfinishedCB(self, data):
				if data:
						self.session.open(MessageBox, _("Finished restarting your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)

		def dataAvail(self, data):
				self.LinkState = None
				for line in data.splitlines():
						line = line.strip()
						if 'Link detected:' in line:
								if "yes" in line:
										self.LinkState = True
								else:
										self.LinkState = False
				if self.LinkState:
						iNetwork.checkNetworkState(self.checkNetworkCB)
				else:
						self["statuspic"].setPixmapNum(1)
						self["statuspic"].show()

		def showErrorMessage(self):
				self.session.open(MessageBox, self.errortext, type=MessageBox.TYPE_INFO, timeout=10)

		def cleanup(self):
				iNetwork.stopLinkStateConsole()
				iNetwork.stopDeactivateInterfaceConsole()
				iNetwork.stopActivateInterfaceConsole()
				iNetwork.stopPingConsole()
				try:
						from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
				except ImportError:
						pass
				else:
						iStatus.stopWlanConsole()

		def getInfoCB(self, data, status):
				self.LinkState = None
				if data is not None:
						if data:
								if status is not None:
										if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or not status[self.iface]["accesspoint"]:
												self.LinkState = False
												self["statuspic"].setPixmapNum(1)
												self["statuspic"].show()
										else:
												self.LinkState = True
												iNetwork.checkNetworkState(self.checkNetworkCB)

		def checkNetworkCB(self, data):
				if iNetwork.getAdapterAttribute(self.iface, "up"):
						if self.LinkState:
								if data <= 2:
										self["statuspic"].setPixmapNum(0)
								else:
										self["statuspic"].setPixmapNum(1)
								self["statuspic"].show()
						else:
								self["statuspic"].setPixmapNum(1)
								self["statuspic"].show()
				else:
						self["statuspic"].setPixmapNum(1)
						self["statuspic"].show()


class NetworkAdapterTest(Screen):
		def __init__(self, session, iface):
				Screen.__init__(self, session)
				self.iface = iface
				self.setTitle(_("Network test: ") + iNetwork.getFriendlyAdapterName(self.iface))
				self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
				self.setLabels()
				self.onClose.append(self.cleanup)
				self.onHide.append(self.cleanup)

				self["updown_actions"] = NumberActionMap(["WizardActions", "ShortcutActions"],
				{
						"ok": self.KeyOK,
						"blue": self.KeyOK,
						"up": lambda: self.updownhandler('up'),
						"down": lambda: self.updownhandler('down'),

				}, -2)

				self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
				{
						"red": self.cancel,
						"back": self.cancel,
				}, -2)
				self["infoshortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
				{
						"red": self.closeInfo,
						"back": self.closeInfo,
				}, -2)
				self["shortcutsgreen"] = ActionMap(["ShortcutActions"],
				{
						"green": self.KeyGreen,
				}, -2)
				self["shortcutsgreen_restart"] = ActionMap(["ShortcutActions"],
				{
						"green": self.KeyGreenRestart,
				}, -2)
				self["shortcutsyellow"] = ActionMap(["ShortcutActions"],
				{
						"yellow": self.KeyYellow,
				}, -2)

				self["shortcutsgreen_restart"].setEnabled(False)
				self["updown_actions"].setEnabled(False)
				self["infoshortcuts"].setEnabled(False)
				self.onClose.append(self.delTimer)
				self.onLayoutFinish.append(self.layoutFinished)
				self.steptimer = False
				self.nextstep = 0
				self.activebutton = 0
				self.nextStepTimer = eTimer()
				self.nextStepTimer.callback.append(self.nextStepTimerFire)

		def cancel(self):
				if not self.oldInterfaceState:
						iNetwork.setAdapterAttribute(self.iface, "up", self.oldInterfaceState)
						iNetwork.deactivateInterface(self.iface)
				self.close()

		def closeInfo(self):
				self["shortcuts"].setEnabled(True)
				self["infoshortcuts"].setEnabled(False)
				self["InfoText"].hide()
				self["InfoTextBorder"].hide()
				self["key_red"].setText(_("Close"))

		def delTimer(self):
				del self.steptimer
				del self.nextStepTimer

		def nextStepTimerFire(self):
				self.nextStepTimer.stop()
				self.steptimer = False
				self.runTest()

		def updownhandler(self, direction):
				if direction == 'up':
						if self.activebutton >= 2:
								self.activebutton -= 1
						else:
								self.activebutton = 6
						self.setActiveButton(self.activebutton)
				if direction == 'down':
						if self.activebutton <= 5:
								self.activebutton += 1
						else:
								self.activebutton = 1
						self.setActiveButton(self.activebutton)

		def setActiveButton(self, button):
				if button == 1:
						self["EditSettingsButton"].setPixmapNum(0)
						self["EditSettings_Text"].setForegroundColorNum(0)
						self["NetworkInfo"].setPixmapNum(0)
						self["NetworkInfo_Text"].setForegroundColorNum(1)
						self["AdapterInfo"].setPixmapNum(1)               # active
						self["AdapterInfo_Text"].setForegroundColorNum(2) # active
				if button == 2:
						self["AdapterInfo_Text"].setForegroundColorNum(1)
						self["AdapterInfo"].setPixmapNum(0)
						self["DhcpInfo"].setPixmapNum(0)
						self["DhcpInfo_Text"].setForegroundColorNum(1)
						self["NetworkInfo"].setPixmapNum(1)               # active
						self["NetworkInfo_Text"].setForegroundColorNum(2) # active
				if button == 3:
						self["NetworkInfo"].setPixmapNum(0)
						self["NetworkInfo_Text"].setForegroundColorNum(1)
						self["IPInfo"].setPixmapNum(0)
						self["IPInfo_Text"].setForegroundColorNum(1)
						self["DhcpInfo"].setPixmapNum(1)                  # active
						self["DhcpInfo_Text"].setForegroundColorNum(2)    # active
				if button == 4:
						self["DhcpInfo"].setPixmapNum(0)
						self["DhcpInfo_Text"].setForegroundColorNum(1)
						self["DNSInfo"].setPixmapNum(0)
						self["DNSInfo_Text"].setForegroundColorNum(1)
						self["IPInfo"].setPixmapNum(1)                  # active
						self["IPInfo_Text"].setForegroundColorNum(2)    # active
				if button == 5:
						self["IPInfo"].setPixmapNum(0)
						self["IPInfo_Text"].setForegroundColorNum(1)
						self["EditSettingsButton"].setPixmapNum(0)
						self["EditSettings_Text"].setForegroundColorNum(0)
						self["DNSInfo"].setPixmapNum(1)                 # active
						self["DNSInfo_Text"].setForegroundColorNum(2)   # active
				if button == 6:
						self["DNSInfo"].setPixmapNum(0)
						self["DNSInfo_Text"].setForegroundColorNum(1)
						self["EditSettingsButton"].setPixmapNum(1)         # active
						self["EditSettings_Text"].setForegroundColorNum(2) # active
						self["AdapterInfo"].setPixmapNum(0)
						self["AdapterInfo_Text"].setForegroundColorNum(1)

		def runTest(self):
				next = self.nextstep
				if next == 0:
						self.doStep1()
				elif next == 1:
						self.doStep2()
				elif next == 2:
						self.doStep3()
				elif next == 3:
						self.doStep4()
				elif next == 4:
						self.doStep5()
				elif next == 5:
						self.doStep6()
				self.nextstep += 1

		def doStep1(self):
				self.steptimer = True
				self.nextStepTimer.start(300)
				self["key_yellow"].setText(_("Stop test"))

		def doStep2(self):
				self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))
				self["Adapter"].setForegroundColorNum(2)
				self["Adaptertext"].setForegroundColorNum(1)
				self["AdapterInfo_Text"].setForegroundColorNum(1)
				self["AdapterInfo_OK"].show()
				self.steptimer = True
				self.nextStepTimer.start(300)

		def doStep3(self):
				self["Networktext"].setForegroundColorNum(1)
				self["Network"].setText(_("Please wait..."))
				self.getLinkState(self.iface)
				self["NetworkInfo_Text"].setForegroundColorNum(1)
				self.steptimer = True
				self.nextStepTimer.start(1000)

		def doStep4(self):
				self["Dhcptext"].setForegroundColorNum(1)
				if iNetwork.getAdapterAttribute(self.iface, 'dhcp'):
						self["Dhcp"].setForegroundColorNum(2)
						self["Dhcp"].setText(_("enabled"))
						self["DhcpInfo_Check"].setPixmapNum(0)
				else:
						self["Dhcp"].setForegroundColorNum(1)
						self["Dhcp"].setText(_("disabled"))
						self["DhcpInfo_Check"].setPixmapNum(1)
				self["DhcpInfo_Check"].show()
				self["DhcpInfo_Text"].setForegroundColorNum(1)
				self.steptimer = True
				self.nextStepTimer.start(1000)

		def doStep5(self):
				self["IPtext"].setForegroundColorNum(1)
				self["IP"].setText(_("Please wait..."))
				iNetwork.checkNetworkState(self.NetworkStatedataAvail)

		def doStep6(self):
				self.steptimer = False
				self.nextStepTimer.stop()
				self["DNStext"].setForegroundColorNum(1)
				self["DNS"].setText(_("Please wait..."))
				iNetwork.checkDNSLookup(self.DNSLookupdataAvail)

		def KeyGreen(self):
				self["shortcutsgreen"].setEnabled(False)
				self["shortcutsyellow"].setEnabled(True)
				self["updown_actions"].setEnabled(False)
				self["key_yellow"].setText("")
				self["key_green"].setText("")
				self.steptimer = True
				self.nextStepTimer.start(1000)

		def KeyGreenRestart(self):
				self.nextstep = 0
				self.layoutFinished()
				self["Adapter"].setText("")
				self["Network"].setText("")
				self["Dhcp"].setText("")
				self["IP"].setText("")
				self["DNS"].setText("")
				self["AdapterInfo_Text"].setForegroundColorNum(0)
				self["NetworkInfo_Text"].setForegroundColorNum(0)
				self["DhcpInfo_Text"].setForegroundColorNum(0)
				self["IPInfo_Text"].setForegroundColorNum(0)
				self["DNSInfo_Text"].setForegroundColorNum(0)
				self["shortcutsgreen_restart"].setEnabled(False)
				self["shortcutsgreen"].setEnabled(False)
				self["shortcutsyellow"].setEnabled(True)
				self["updown_actions"].setEnabled(False)
				self["key_yellow"].setText("")
				self["key_green"].setText("")
				self.steptimer = True
				self.nextStepTimer.start(1000)

		def KeyOK(self):
				self["infoshortcuts"].setEnabled(True)
				self["shortcuts"].setEnabled(False)
				if self.activebutton == 1: # Adapter Check
						self["InfoText"].setText(_("This test detects your configured LAN adapter."))
						self["InfoTextBorder"].show()
						self["InfoText"].show()
						self["key_red"].setText(_("Back"))
				if self.activebutton == 2: #LAN Check
						self["InfoText"].setText(_("This test checks whether a network cable is connected to your LAN adapter.\nIf you get a \"disconnected\" message:\n- verify that a network cable is attached\n- verify that the cable is not broken"))
						self["InfoTextBorder"].show()
						self["InfoText"].show()
						self["key_red"].setText(_("Back"))
				if self.activebutton == 3: #DHCP Check
						self["InfoText"].setText(_("This test checks whether your LAN adapter is set up for automatic IP address configuration with DHCP.\nIf you get a \"disabled\" message:\n- then your LAN adapter is configured for manual IP setup\n- verify thay you have entered the correct IP information in the adapter setup dialog.\nIf you get an \"enabeld\" message:\n- verify that you have a configured and working DHCP server in your network."))
						self["InfoTextBorder"].show()
						self["InfoText"].show()
						self["key_red"].setText(_("Back"))
				if self.activebutton == 4: # IP Check
						self["InfoText"].setText(_("This test checks whether a valid IP address is found for your LAN adapter.\nIf you get a \"unconfirmed\" message:\n- no valid IP address was found\n- please check your DHCP, cabling and adapter setup"))
						self["InfoTextBorder"].show()
						self["InfoText"].show()
						self["key_red"].setText(_("Back"))
				if self.activebutton == 5: # DNS Check
						self["InfoText"].setText(_("This test checks for configured nameservers.\nIf you get a \"unconfirmed\" message:\n- please check your DHCP, cabling and adapter setup\n- if you configured your nameservers manually please verify your entries in the \"Nameserver\" configuration"))
						self["InfoTextBorder"].show()
						self["InfoText"].show()
						self["key_red"].setText(_("Back"))
				if self.activebutton == 6: # Edit Settings
						self.session.open(AdapterSetup, self.iface)

		def KeyYellow(self):
				self.nextstep = 0
				self["shortcutsgreen_restart"].setEnabled(True)
				self["shortcutsgreen"].setEnabled(False)
				self["shortcutsyellow"].setEnabled(False)
				self["key_green"].setText(_("Restart test"))
				self["key_yellow"].setText("")
				self.steptimer = False
				self.nextStepTimer.stop()

		def layoutFinished(self):
				self["shortcutsyellow"].setEnabled(False)
				self["AdapterInfo_OK"].hide()
				self["NetworkInfo_Check"].hide()
				self["DhcpInfo_Check"].hide()
				self["IPInfo_Check"].hide()
				self["DNSInfo_Check"].hide()
				self["EditSettings_Text"].hide()
				self["EditSettingsButton"].hide()
				self["InfoText"].hide()
				self["InfoTextBorder"].hide()
				self["key_yellow"].setText("")

		def setLabels(self):
				self["Adaptertext"] = MultiColorLabel(_("LAN adapter"))
				self["Adapter"] = MultiColorLabel()
				self["AdapterInfo"] = MultiPixmap()
				self["AdapterInfo_Text"] = MultiColorLabel(_("Show info"))
				self["AdapterInfo_OK"] = Pixmap()

				if self.iface in iNetwork.wlan_interfaces:
						self["Networktext"] = MultiColorLabel(_("Wireless network"))
				else:
						self["Networktext"] = MultiColorLabel(_("Local network"))

				self["Network"] = MultiColorLabel()
				self["NetworkInfo"] = MultiPixmap()
				self["NetworkInfo_Text"] = MultiColorLabel(_("Show info"))
				self["NetworkInfo_Check"] = MultiPixmap()

				self["Dhcptext"] = MultiColorLabel(_("DHCP"))
				self["Dhcp"] = MultiColorLabel()
				self["DhcpInfo"] = MultiPixmap()
				self["DhcpInfo_Text"] = MultiColorLabel(_("Show info"))
				self["DhcpInfo_Check"] = MultiPixmap()

				self["IPtext"] = MultiColorLabel(_("IP address"))
				self["IP"] = MultiColorLabel()
				self["IPInfo"] = MultiPixmap()
				self["IPInfo_Text"] = MultiColorLabel(_("Show info"))
				self["IPInfo_Check"] = MultiPixmap()

				self["DNStext"] = MultiColorLabel(_("Nameserver"))
				self["DNS"] = MultiColorLabel()
				self["DNSInfo"] = MultiPixmap()
				self["DNSInfo_Text"] = MultiColorLabel(_("Show info"))
				self["DNSInfo_Check"] = MultiPixmap()

				self["EditSettings_Text"] = MultiColorLabel(_("Edit settings"))
				self["EditSettingsButton"] = MultiPixmap()

				self["key_red"] = StaticText(_("Close"))
				self["key_green"] = StaticText(_("Start test"))
				self["key_yellow"] = StaticText(_("Stop test"))

				self["InfoTextBorder"] = Pixmap()
				self["InfoText"] = Label()

		def getLinkState(self, iface):
				if iface in iNetwork.wlan_interfaces:
						try:
								from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
						except:
								self["Network"].setForegroundColorNum(1)
								self["Network"].setText(_("disconnected"))
								self["NetworkInfo_Check"].setPixmapNum(1)
								self["NetworkInfo_Check"].show()
						else:
								iStatus.getDataForInterface(self.iface, self.getInfoCB)
				else:
						iNetwork.getLinkState(iface, self.LinkStatedataAvail)

		def LinkStatedataAvail(self, data):
				for item in data.splitlines():
						if "Link detected:" in item:
								if "yes" in item:
										self["Network"].setForegroundColorNum(2)
										self["Network"].setText(_("connected"))
										self["NetworkInfo_Check"].setPixmapNum(0)
								else:
										self["Network"].setForegroundColorNum(1)
										self["Network"].setText(_("disconnected"))
										self["NetworkInfo_Check"].setPixmapNum(1)
								break
				else:
						self["Network"].setText(_("unknown"))
				self["NetworkInfo_Check"].show()

		def NetworkStatedataAvail(self, data):
				if data <= 2:
						self["IP"].setForegroundColorNum(2)
						self["IP"].setText(_("confirmed"))
						self["IPInfo_Check"].setPixmapNum(0)
				else:
						self["IP"].setForegroundColorNum(1)
						self["IP"].setText(_("unconfirmed"))
						self["IPInfo_Check"].setPixmapNum(1)
				self["IPInfo_Check"].show()
				self["IPInfo_Text"].setForegroundColorNum(1)
				self.steptimer = True
				self.nextStepTimer.start(300)

		def DNSLookupdataAvail(self, data):
				if data <= 2:
						self["DNS"].setForegroundColorNum(2)
						self["DNS"].setText(_("confirmed"))
						self["DNSInfo_Check"].setPixmapNum(0)
				else:
						self["DNS"].setForegroundColorNum(1)
						self["DNS"].setText(_("unconfirmed"))
						self["DNSInfo_Check"].setPixmapNum(1)
				self["DNSInfo_Check"].show()
				self["DNSInfo_Text"].setForegroundColorNum(1)
				self["EditSettings_Text"].show()
				self["EditSettingsButton"].setPixmapNum(1)
				self["EditSettings_Text"].setForegroundColorNum(2) # active
				self["EditSettingsButton"].show()
				self["key_yellow"].setText("")
				self["key_green"].setText(_("Restart test"))
				self["shortcutsgreen"].setEnabled(False)
				self["shortcutsgreen_restart"].setEnabled(True)
				self["shortcutsyellow"].setEnabled(False)
				self["updown_actions"].setEnabled(True)
				self.activebutton = 6

		def getInfoCB(self, data, status):
				if data is not None:
						if data:
								if status is not None:
										if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or not status[self.iface]["accesspoint"]:
												self["Network"].setForegroundColorNum(1)
												self["Network"].setText(_("disconnected"))
												self["NetworkInfo_Check"].setPixmapNum(1)
												self["NetworkInfo_Check"].show()
										else:
												self["Network"].setForegroundColorNum(2)
												self["Network"].setText(_("connected"))
												self["NetworkInfo_Check"].setPixmapNum(0)
												self["NetworkInfo_Check"].show()

		def cleanup(self):
				iNetwork.stopLinkStateConsole()
				iNetwork.stopDNSConsole()
				try:
						from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
				except ImportError:
						pass
				else:
						iStatus.stopWlanConsole()
