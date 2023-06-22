# -*- coding: utf-8 -*-
from Tools.Profile import profile

from Screens.Screen import Screen
import Screens.InfoBar
from Screens.ScreenSaver import InfoBarScreenSaver
import Components.ParentalControl
from Components.Button import Button
from Components.ServiceList import ServiceList, refreshServiceList
from Components.ActionMap import NumberActionMap, ActionMap, HelpableActionMap
from Components.MenuList import MenuList
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
profile("ChannelSelection.py 1")
from Screens.EpgSelection import EPGSelection
from enigma import eServiceReference, eEPGCache, eServiceCenter, eRCInput, eTimer, eDVBDB, iPlayableService, iServiceInformation, getPrevAsciiCode, loadPNG
from Components.config import config, configfile, ConfigSubsection, ConfigText, ConfigYesNo
from Tools.NumericalTextInput import NumericalTextInput
profile("ChannelSelection.py 2")
from Components.NimManager import nimmanager
profile("ChannelSelection.py 2.1")
from Components.Sources.RdsDecoder import RdsDecoder
profile("ChannelSelection.py 2.2")
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.Event import Event
profile("ChannelSelection.py 2.3")
from Components.Input import Input
profile("ChannelSelection.py 3")
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.SystemInfo import SystemInfo
from Screens.InputBox import PinInput
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox
from Screens.ServiceInfo import ServiceInfo
from Screens.Hotkey import InfoBarHotkey, hotkeyActionMap, hotkey
profile("ChannelSelection.py 4")
from Screens.PictureInPicture import PictureInPicture
from Screens.RdsDisplay import RassInteractive
from ServiceReference import ServiceReference
from Tools.BoundFunction import boundFunction
from Tools.Notifications import RemovePopup
from Tools.Alternatives import GetWithAlternative, CompareWithAlternatives
from Tools.Directories import fileExists, resolveFilename, sanitizeFilename, SCOPE_PLUGINS
from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins
from Screens.ChoiceBox import ChoiceBox
from Screens.EventView import EventViewEPGSelect
import os
from time import time, localtime
from Components.Sources.List import List
from Components.Renderer.Picon import getPiconName
profile("ChannelSelection.py after imports")

FLAG_SERVICE_NEW_FOUND = 64
FLAG_IS_DEDICATED_3D = 128
FLAG_CENTER_DVB_SUBS = 2048 #define in lib/dvb/idvb.h as dxNewFound = 64 and dxIsDedicated3D = 128


class BouquetSelector(Screen):
	def __init__(self, session, bouquets, selectedFunc, enableWrapAround=True):
		Screen.__init__(self, session)
		self.setTitle(_("Choose bouquet"))

		self.selectedFunc = selectedFunc

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick
			})
		entrys = [(x[0], x[1]) for x in bouquets]
		self["menu"] = MenuList(entrys, enableWrapAround)

	def getCurrent(self):
		cur = self["menu"].getCurrent()
		return cur and cur[1]

	def okbuttonClick(self):
		self.selectedFunc(self.getCurrent())

	def up(self):
		self["menu"].up()

	def down(self):
		self["menu"].down()

	def cancelClick(self):
		self.close(False)


class SilentBouquetSelector:
	def __init__(self, bouquets, enableWrapAround=False, current=0):
		self.bouquets = [b[1] for b in bouquets]
		self.pos = current
		self.count = len(bouquets)
		self.enableWrapAround = enableWrapAround

	def up(self):
		if self.pos > 0 or self.enableWrapAround:
			self.pos = (self.pos - 1) % self.count

	def down(self):
		if self.pos < (self.count - 1) or self.enableWrapAround:
			self.pos = (self.pos + 1) % self.count

	def getCurrent(self):
		return self.bouquets[self.pos]


# csel.bouquet_mark_edit values
OFF = 0
EDIT_BOUQUET = 1
EDIT_ALTERNATIVES = 2


def append_when_current_valid(current, menu, args, level=0, key="dummy"):
	if current and current.valid() and level <= config.usage.setup_level.index:
		menu.append(ChoiceEntryComponent(key, args))


def removed_userbouquets_available():
	for file in os.listdir("/etc/enigma2/"):
		if file.startswith("userbouquet") and file.endswith(".del"):
			return True
	return False


class ChannelContextMenu(Screen):
	def __init__(self, session, csel):

		Screen.__init__(self, session)
		self.setTitle(_("Channel context menu"))
		self.csel = csel
		self.bsel = None
		if self.isProtected():
			self.onFirstExecBegin.append(boundFunction(self.session.openWithCallback, self.protectResult, PinInput, pinList=[x.value for x in config.ParentalControl.servicepin], triesEntry=config.ParentalControl.retries.servicepin, title=_("Please enter the correct PIN code"), windowTitle=_("Enter PIN code")))

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "MenuActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick,
				"blue": self.showServiceInPiP,
				"red": self.playMain,
				"menu": self.openSetup,
				"1": self.unhideParentalServices,
				"2": self.renameEntry,
				"3": self.findCurrentlyPlayed,
				"5": self.addServiceToBouquetOrAlternative,
				"6": self.toggleMoveModeSelect,
				"8": self.removeEntry
			})
		menu = []

		self.removeFunction = False
		self.addFunction = False
		self.PiPAvailable = False
		current = csel.getCurrentSelection()
		current_root = csel.getRoot()
		current_sel_path = current.getPath()
		current_sel_flags = current.flags
		inBouquetRootList = current_root and 'FROM BOUQUET "bouquets.' in current_root.getPath() #FIXME HACK
		inAlternativeList = current_root and 'FROM BOUQUET "alternatives' in current_root.getPath()
		self.inBouquet = csel.getMutableList() is not None
		haveBouquets = config.usage.multibouquet.value
		from Components.ParentalControl import parentalControl
		self.parentalControl = parentalControl
		self.parentalControlEnabled = config.ParentalControl.servicepin[0].value and config.ParentalControl.servicepinactive.value
		if not (current_sel_path or current_sel_flags & (eServiceReference.isDirectory | eServiceReference.isMarker)) or current_sel_flags & eServiceReference.isGroup:
			append_when_current_valid(current, menu, (_("Show transponder info"), self.showServiceInformations), level=2)
		if csel.bouquet_mark_edit == OFF and not csel.entry_marked:
			if not inBouquetRootList:
				isPlayable = not (current_sel_flags & (eServiceReference.isMarker | eServiceReference.isDirectory))
				if isPlayable:
					for p in plugins.getPlugins(PluginDescriptor.WHERE_CHANNEL_CONTEXT_MENU):
						append_when_current_valid(current, menu, (p.name, boundFunction(self.runPlugin, p)), key="bullet")
					if config.servicelist.startupservice.value == current.toString():
						append_when_current_valid(current, menu, (_("Stop using as startup service"), self.unsetStartupService), level=0)
					else:
						append_when_current_valid(current, menu, (_("Set as startup service"), self.setStartupService), level=0)
					if self.parentalControlEnabled:
						if self.parentalControl.getProtectionLevel(current.toCompareString()) == -1:
							append_when_current_valid(current, menu, (_("Add to parental protection"), boundFunction(self.addParentalProtection, current)), level=0)
						else:
							if self.parentalControl.isServiceProtectionBouquet(current.toCompareString()):
								append_when_current_valid(current, menu, (_("Service belongs to a parental protected bouquet"), self.cancelClick), level=0)
							else:
								append_when_current_valid(current, menu, (_("Remove from parental protection"), boundFunction(self.removeParentalProtection, current)), level=0)
						if self.parentalControl.blacklist and config.ParentalControl.hideBlacklist.value and not self.parentalControl.sessionPinCached and config.ParentalControl.storeservicepin.value != "never":
							append_when_current_valid(current, menu, (_("Unhide parental control services"), self.unhideParentalServices), level=0, key="1")
					if SystemInfo["3DMode"] and fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/OSD3DSetup/plugin.pyc")):
						if eDVBDB.getInstance().getFlag(eServiceReference(current.toString())) & FLAG_IS_DEDICATED_3D:
							append_when_current_valid(current, menu, (_("Unmark service as dedicated 3D service"), self.removeDedicated3DFlag), level=2)
						else:
							append_when_current_valid(current, menu, (_("Mark service as dedicated 3D service"), self.addDedicated3DFlag), level=2)
					if not (current_sel_path):
						if Screens.InfoBar.InfoBar.instance.checkHideVBI(current):
							append_when_current_valid(current, menu, (_("Uncover dashed flickering line for this service"), self.toggleVBI), level=1)
						else:
							append_when_current_valid(current, menu, (_("Cover dashed flickering line for this service"), self.toggleVBI), level=1)
						if eDVBDB.getInstance().getCachedPid(eServiceReference(current.toString()), 9) >> 16 not in (-1, eDVBDB.getInstance().getCachedPid(eServiceReference(current.toString()), 2)):
							#Only show when a DVB subtitle is cached on this service
							if eDVBDB.getInstance().getFlag(eServiceReference(current.toString())) & FLAG_CENTER_DVB_SUBS:
								append_when_current_valid(current, menu, (_("Do not center DVB subs on this service"), self.removeCenterDVBSubsFlag), level=2)
							else:
								append_when_current_valid(current, menu, (_("Do center DVB subs on this service"), self.addCenterDVBSubsFlag), level=2)

					if haveBouquets:
						bouquets = self.csel.getBouquetList()
						if bouquets is None:
							bouquetCnt = 0
						else:
							bouquetCnt = len(bouquets)
						if not self.inBouquet or bouquetCnt > 1:
							append_when_current_valid(current, menu, (_("Add service to bouquet"), self.addServiceToBouquetSelected), level=0, key="5")
							self.addFunction = self.addServiceToBouquetSelected
						if not self.inBouquet:
							append_when_current_valid(current, menu, (_("Remove entry"), self.removeEntry), level=0, key="8")
							self.removeFunction = self.removeSatelliteService
					else:
						if not self.inBouquet:
							append_when_current_valid(current, menu, (_("Add service to favourites"), self.addServiceToBouquetSelected), level=0, key="5")
							self.addFunction = self.addServiceToBouquetSelected
					if SystemInfo["PIPAvailable"]:
						self.PiPAvailable = True
						if self.csel.dopipzap:
							append_when_current_valid(current, menu, (_("Play in main window"), self.playMain), level=0, key="red")
						else:
							append_when_current_valid(current, menu, (_("Play as Picture in Picture"), self.showServiceInPiP), level=0, key="blue")
					append_when_current_valid(current, menu, (_("Find currently playing service"), self.findCurrentlyPlayed), level=0, key="3")
				else:
					if 'FROM SATELLITES' in current_root.getPath() and current and _("Services") in eServiceCenter.getInstance().info(current).getName(current):
						unsigned_orbpos = current.getUnsignedData(4) >> 16
						if unsigned_orbpos == 0xFFFF:
							append_when_current_valid(current, menu, (_("Remove cable services"), self.removeSatelliteServices), level=0)
						elif unsigned_orbpos == 0xEEEE:
							append_when_current_valid(current, menu, (_("Remove terrestrial services"), self.removeSatelliteServices), level=0)
						else:
							append_when_current_valid(current, menu, (_("Remove selected satellite"), self.removeSatelliteServices), level=0)
					if haveBouquets:
						if not self.inBouquet and not "PROVIDERS" in current_sel_path:
							append_when_current_valid(current, menu, (_("Copy to bouquets"), self.copyCurrentToBouquetList), level=0)
					if ("flags == %d" % (FLAG_SERVICE_NEW_FOUND)) in current_sel_path:
						append_when_current_valid(current, menu, (_("Remove all new found flags"), self.removeAllNewFoundFlags), level=0)
				if self.inBouquet:
					append_when_current_valid(current, menu, (_("Rename entry"), self.renameEntry), level=0, key="2")
					if not inAlternativeList:
						append_when_current_valid(current, menu, (_("Remove entry"), self.removeEntry), level=0, key="8")
						self.removeFunction = self.removeCurrentService
				if current_root and ("flags == %d" % (FLAG_SERVICE_NEW_FOUND)) in current_root.getPath():
					append_when_current_valid(current, menu, (_("Remove new found flag"), self.removeNewFoundFlag), level=0)
			else:
				if self.parentalControlEnabled:
					if self.parentalControl.blacklist and config.ParentalControl.hideBlacklist.value and not self.parentalControl.sessionPinCached and config.ParentalControl.storeservicepin.value != "never":
						append_when_current_valid(current, menu, (_("Unhide parental control services"), self.unhideParentalServices), level=0, key="1")
					if self.parentalControl.getProtectionLevel(current.toCompareString()) == -1:
						append_when_current_valid(current, menu, (_("Add bouquet to parental protection"), boundFunction(self.addParentalProtection, current)), level=0)
					else:
						append_when_current_valid(current, menu, (_("Remove bouquet from parental protection"), boundFunction(self.removeParentalProtection, current)), level=0)
				menu.append(ChoiceEntryComponent("dummy", (_("Add bouquet"), self.showBouquetInputBox)))
				append_when_current_valid(current, menu, (_("Rename entry"), self.renameEntry), level=0, key="2")
				append_when_current_valid(current, menu, (_("Remove entry"), self.removeEntry), level=0, key="8")
				self.removeFunction = self.removeBouquet
				if removed_userbouquets_available():
					append_when_current_valid(current, menu, (_("Purge deleted user bouquets"), self.purgeDeletedBouquets), level=0)
					append_when_current_valid(current, menu, (_("Restore deleted user bouquets"), self.restoreDeletedBouquets), level=0)
				append_when_current_valid(current, menu, (_("Reload services/bouquets list"), self.reloadServicesBouquets), level=2)
		if self.inBouquet: # current list is editable?
			if csel.bouquet_mark_edit == OFF:
				if csel.movemode:
					append_when_current_valid(current, menu, (_("Disable move mode"), self.toggleMoveMode), level=0, key="6")
				else:
					append_when_current_valid(current, menu, (_("Enable move mode"), self.toggleMoveMode), level=0, key="6")
				if csel.entry_marked and not inAlternativeList:
					append_when_current_valid(current, menu, (_("Remove entry"), self.removeEntry), level=0, key="8")
					self.removeFunction = self.removeCurrentService
				if not csel.entry_marked and not inBouquetRootList and current_root and not (current_root.flags & eServiceReference.isGroup):
					if current.type != -1:
						menu.append(ChoiceEntryComponent("dummy", (_("Add marker"), self.showMarkerInputBox)))
					if not csel.movemode:
						if haveBouquets:
							append_when_current_valid(current, menu, (_("Enable bouquet edit"), self.bouquetMarkStart), level=0)
						else:
							append_when_current_valid(current, menu, (_("Enable favourites edit"), self.bouquetMarkStart), level=0)
					if current_sel_flags & eServiceReference.isGroup:
						append_when_current_valid(current, menu, (_("Edit alternatives"), self.editAlternativeServices), level=2)
						append_when_current_valid(current, menu, (_("Show alternatives"), self.showAlternativeServices), level=2)
						append_when_current_valid(current, menu, (_("Remove all alternatives"), self.removeAlternativeServices), level=2)
					elif not current_sel_flags & eServiceReference.isMarker:
						append_when_current_valid(current, menu, (_("Add alternatives"), self.addAlternativeServices), level=2)
			else:
				if csel.bouquet_mark_edit == EDIT_BOUQUET:
					if haveBouquets:
						append_when_current_valid(current, menu, (_("End bouquet edit"), self.bouquetMarkEnd), level=0)
						append_when_current_valid(current, menu, (_("Abort bouquet edit"), self.bouquetMarkAbort), level=0)
					else:
						append_when_current_valid(current, menu, (_("End favourites edit"), self.bouquetMarkEnd), level=0)
						append_when_current_valid(current, menu, (_("Abort favourites edit"), self.bouquetMarkAbort), level=0)
					if current_sel_flags & eServiceReference.isMarker:
						append_when_current_valid(current, menu, (_("Rename entry"), self.renameEntry), level=0, key="2")
						append_when_current_valid(current, menu, (_("Remove entry"), self.removeEntry), level=0, key="8")
						self.removeFunction = self.removeCurrentService
				else:
					append_when_current_valid(current, menu, (_("End alternatives edit"), self.bouquetMarkEnd), level=0)
					append_when_current_valid(current, menu, (_("Abort alternatives edit"), self.bouquetMarkAbort), level=0)

		menu.append(ChoiceEntryComponent("menu", (_("Settings..."), self.openSetup)))
		self["menu"] = ChoiceList(menu)

	def set3DMode(self, value):
		playingref = self.session.nav.getCurrentlyPlayingServiceReference()
		if config.plugins.OSD3DSetup.mode.value == "auto" and (playingref and playingref == self.csel.getCurrentSelection()):
			from Plugins.SystemPlugins.OSD3DSetup.plugin import applySettings
			applySettings(value and "sidebyside" or config.plugins.OSD3DSetup.mode.value)

	def addDedicated3DFlag(self):
		eDVBDB.getInstance().addFlag(eServiceReference(self.csel.getCurrentSelection().toString()), FLAG_IS_DEDICATED_3D)
		eDVBDB.getInstance().reloadBouquets()
		self.set3DMode(True)
		self.close()

	def removeDedicated3DFlag(self):
		eDVBDB.getInstance().removeFlag(eServiceReference(self.csel.getCurrentSelection().toString()), FLAG_IS_DEDICATED_3D)
		eDVBDB.getInstance().reloadBouquets()
		self.set3DMode(False)
		self.close()

	def toggleVBI(self):
		Screens.InfoBar.InfoBar.instance.ToggleHideVBI(self.csel.getCurrentSelection())
		Screens.InfoBar.InfoBar.instance.showHideVBI()
		self.close()

	def addCenterDVBSubsFlag(self):
		eDVBDB.getInstance().addFlag(eServiceReference(self.csel.getCurrentSelection().toString()), FLAG_CENTER_DVB_SUBS)
		eDVBDB.getInstance().reloadBouquets()
		config.subtitles.dvb_subtitles_centered.value = True
		self.close()

	def removeCenterDVBSubsFlag(self):
		eDVBDB.getInstance().removeFlag(eServiceReference(self.csel.getCurrentSelection().toString()), FLAG_CENTER_DVB_SUBS)
		eDVBDB.getInstance().reloadBouquets()
		config.subtitles.dvb_subtitles_centered.value = False
		self.close()

	def isProtected(self):
		return self.csel.protectContextMenu and config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.context_menus.value

	def protectResult(self, answer):
		if answer:
			self.csel.protectContextMenu = False
		elif answer is not None:
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code you entered is wrong."), MessageBox.TYPE_ERROR)
		else:
			self.close()

	def addServiceToBouquetOrAlternative(self):
		if self.addFunction:
			self.addFunction()
		else:
			return 0

	def getCurrentSelectionName(self):
		cur = self.csel.getCurrentSelection()
		if cur and cur.valid():
			name = eServiceCenter.getInstance().info(cur) and hasattr(eServiceCenter.getInstance().info(cur), "getName") and eServiceCenter.getInstance().info(cur).getName(cur) or ServiceReference(cur).getServiceName() or ""
			name = name.replace('\xc2\x86', '').replace('\xc2\x87', '')
			return name
		return ""

	def removeEntry(self):
		if self.removeFunction and self.csel.servicelist.getCurrent() and self.csel.servicelist.getCurrent().valid():
			if self.csel.confirmRemove:
				list = [(_("yes"), True), (_("no"), False), (_("yes") + " " + _("and never ask in this session again"), "never")]
				self.session.openWithCallback(self.removeFunction, MessageBox, _("Are you sure to remove this entry?") + "\n%s" % self.getCurrentSelectionName(), list=list)
			else:
				self.removeFunction(True)
		else:
			return 0

	def removeCurrentService(self, answer):
		if answer:
			if answer == "never":
				self.csel.confirmRemove = False
			self.csel.removeCurrentService()
			self.close()

	def removeSatelliteService(self, answer):
		if answer:
			if answer == "never":
				self.csel.confirmRemove = False
			self.csel.removeSatelliteService()
			self.close()

	def removeBouquet(self, answer):
		if answer:
			if answer == "never":
				self.csel.confirmRemove = False
			if self.csel.movemode:
				self.csel.toggleMoveMode()
			self.csel.removeBouquet()
			eDVBDB.getInstance().reloadBouquets()
			self.close()

	def purgeDeletedBouquets(self):
		self.session.openWithCallback(self.purgeDeletedBouquetsCallback, MessageBox, _("Are you sure to purge all deleted user bouquets?"))

	def purgeDeletedBouquetsCallback(self, answer):
		if answer:
			for file in os.listdir("/etc/enigma2/"):
				if file.startswith("userbouquet") and file.endswith(".del"):
					file = "/etc/enigma2/" + file
					print("permantly remove file ", file)
					os.remove(file)
			self.close()

	def restoreDeletedBouquets(self):
		for file in os.listdir("/etc/enigma2/"):
			if file.startswith("userbouquet") and file.endswith(".del"):
				file = "/etc/enigma2/" + file
				print("restore file ", file[:-4])
				os.rename(file, file[:-4])
		eDVBDBInstance = eDVBDB.getInstance()
		eDVBDBInstance.setLoadUnlinkedUserbouquets(True)
		eDVBDBInstance.reloadBouquets()
		eDVBDBInstance.setLoadUnlinkedUserbouquets(config.misc.load_unlinked_userbouquets.value)
		refreshServiceList()
		self.csel.showFavourites()
		self.close()

	def playMain(self):
		ref = self.csel.getCurrentSelection()
		if ref and ref.valid() and self.PiPAvailable and self.csel.dopipzap:
			self.csel.zap()
			self.csel.startServiceRef = None
			self.csel.startRoot = None
			self.csel.correctChannelNumber()
			self.close(True)
		else:
			return 0

	def okbuttonClick(self):
		self["menu"].getCurrent()[0][1]()

	def openSetup(self):
		from Screens.Setup import Setup
		self.session.openWithCallback(self.cancelClick, Setup, "userinterface")

	def cancelClick(self, dummy=False):
		self.close(False)

	def reloadServicesBouquets(self):
		eDVBDB.getInstance().reloadBouquets()
		eDVBDB.getInstance().reloadServicelist()
		self.session.openWithCallback(self.close, MessageBox, _("The services/bouquets list is reloaded!"), MessageBox.TYPE_INFO, timeout=5)

	def showServiceInformations(self):
		current = self.csel.getCurrentSelection()
		if current.flags & eServiceReference.isGroup:
			playingref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if playingref and playingref == current:
				current = self.session.nav.getCurrentlyPlayingServiceReference()
			else:
				current = eServiceReference(GetWithAlternative(current.toString()))
		self.session.open(ServiceInfo, current)
		self.close()

	def setStartupService(self):
		self.session.openWithCallback(self.setStartupServiceCallback, MessageBox, _("Set startup service"), list=[(_("Only on startup"), "startup"), (_("Also on standby"), "standby")])

	def setStartupServiceCallback(self, answer):
		if answer:
			config.servicelist.startupservice.value = self.csel.getCurrentSelection().toString()
			path = ';'.join([i.toString() for i in self.csel.servicePath])
			config.servicelist.startuproot.value = path
			config.servicelist.startupmode.value = config.servicelist.lastmode.value
			config.servicelist.startupservice_onstandby.value = answer == "standby"
			config.servicelist.save()
			configfile.save()
			self.close()

	def unsetStartupService(self):
		config.servicelist.startupservice.value = ''
		config.servicelist.startupservice_onstandby.value = False
		config.servicelist.save()
		configfile.save()
		self.close()

	def showBouquetInputBox(self):
		self.session.openWithCallback(self.bouquetInputCallback, VirtualKeyBoard, title=_("Please enter a name for the new bouquet"), text="", maxSize=False, visible_width=56, type=Input.TEXT)

	def bouquetInputCallback(self, bouquet):
		if bouquet is not None:
			self.csel.addBouquet(bouquet, None)
		self.close()

	def addParentalProtection(self, service):
		self.parentalControl.protectService(service.toCompareString())
		if config.ParentalControl.hideBlacklist.value and not self.parentalControl.sessionPinCached:
			self.csel.servicelist.resetRoot()
		self.close()

	def removeParentalProtection(self, service):
		self.session.openWithCallback(boundFunction(self.pinEntered, service.toCompareString()), PinInput, pinList=[config.ParentalControl.servicepin[0].value], triesEntry=config.ParentalControl.retries.servicepin, title=_("Enter the service PIN"), windowTitle=_("Enter PIN code"))

	def pinEntered(self, service, answer):
		if answer:
			self.parentalControl.unProtectService(service)
			if config.ParentalControl.hideBlacklist.value and not self.parentalControl.sessionPinCached:
				self.csel.servicelist.resetRoot()
			self.close()
		elif answer is not None:
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code you entered is wrong."), MessageBox.TYPE_ERROR)
		else:
			self.close()

	def unhideParentalServices(self):
		if self.csel.protectContextMenu:
			self.session.openWithCallback(self.unhideParentalServicesCallback, PinInput, pinList=[config.ParentalControl.servicepin[0].value], triesEntry=config.ParentalControl.retries.servicepin, title=_("Enter the service PIN"), windowTitle=_("Enter PIN code"))
		else:
			self.unhideParentalServicesCallback(True)

	def unhideParentalServicesCallback(self, answer):
		if answer:
			service = self.csel.servicelist.getCurrent()
			self.parentalControl.setSessionPinCached()
			self.parentalControl.hideBlacklist()
			self.csel.servicelist.resetRoot()
			self.csel.servicelist.setCurrent(service)
			self.close()
		elif answer is not None:
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code you entered is wrong."), MessageBox.TYPE_ERROR)
		else:
			self.close()

	def showServiceInPiP(self, root=None, ref=None):
		newservice = ref or self.csel.getCurrentSelection()
		currentBouquet = root or self.csel.getRoot()
		if ref and root or (self.PiPAvailable and not self.csel.dopipzap and newservice and newservice.valid() and Components.ParentalControl.parentalControl.isServicePlayable(newservice, boundFunction(self.showServiceInPiP, root=currentBouquet), self.session)):
			if hasattr(self.session, 'pipshown') and self.session.pipshown and hasattr(self.session, 'pip'):
				del self.session.pip
			self.session.pip = self.session.instantiateDialog(PictureInPicture)
			self.session.pip.show()
			if self.session.pip.playService(newservice):
				self.session.pipshown = True
				self.session.pip.servicePath = self.csel.getCurrentServicePath()
				self.session.pip.servicePath[1] = currentBouquet
				self.close(True)
			else:
				self.session.pipshown = False
				del self.session.pip
				self.session.openWithCallback(self.close, MessageBox, _("Could not open Picture in Picture"), MessageBox.TYPE_ERROR)
		else:
			return 0

	def addServiceToBouquetSelected(self):
		bouquets = self.csel.getBouquetList()
		if bouquets is None:
			cnt = 0
		else:
			cnt = len(bouquets)
		if cnt > 1: # show bouquet list
			self.bsel = self.session.openWithCallback(self.bouquetSelClosed, BouquetSelector, bouquets, self.addCurrentServiceToBouquet)
		elif cnt == 1: # add to only one existing bouquet
			self.addCurrentServiceToBouquet(bouquets[0][1], closeBouquetSelection=False)

	def bouquetSelClosed(self, recursive):
		self.bsel = None
		if recursive:
			self.close(False)

	def removeSatelliteServices(self):
		self.csel.removeSatelliteServices()
		self.close()

	def copyCurrentToBouquetList(self):
		self.csel.copyCurrentToBouquetList()
		self.close()

	def showMarkerInputBox(self):
		self.session.openWithCallback(self.markerInputCallback, VirtualKeyBoard, title=_("Please enter a name for the new marker"), text="markername", maxSize=False, visible_width=56, type=Input.TEXT)

	def markerInputCallback(self, marker):
		if marker is not None:
			self.csel.addMarker(marker)
		self.close()

	def addCurrentServiceToBouquet(self, dest, closeBouquetSelection=True):
		self.csel.addServiceToBouquet(dest)
		if self.bsel is not None:
			self.bsel.close(True)
		else:
			self.close(closeBouquetSelection) # close bouquet selection

	def renameEntry(self):
		if self.inBouquet and self.csel.servicelist.getCurrent() and self.csel.servicelist.getCurrent().valid() and not self.csel.entry_marked:
			self.csel.renameEntry()
			self.close()
		else:
			return 0

	def toggleMoveMode(self):
		if self.inBouquet and self.csel.servicelist.getCurrent() and self.csel.servicelist.getCurrent().valid():
			self.csel.toggleMoveMode()
			self.close()
		else:
			return 0

	def toggleMoveModeSelect(self):
		if self.inBouquet and self.csel.servicelist.getCurrent() and self.csel.servicelist.getCurrent().valid():
			self.csel.toggleMoveMode(True)
			self.close()
		else:
			return 0

	def bouquetMarkStart(self):
		self.csel.startMarkedEdit(EDIT_BOUQUET)
		self.close()

	def bouquetMarkEnd(self):
		self.csel.endMarkedEdit(abort=False)
		self.close()

	def bouquetMarkAbort(self):
		self.csel.endMarkedEdit(abort=True)
		self.close()

	def removeNewFoundFlag(self):
		eDVBDB.getInstance().removeFlag(self.csel.getCurrentSelection(), FLAG_SERVICE_NEW_FOUND)
		self.close()

	def removeAllNewFoundFlags(self):
		curpath = self.csel.getCurrentSelection().getPath()
		idx = curpath.find("satellitePosition == ")
		if idx != -1:
			tmp = curpath[idx + 21:]
			idx = tmp.find(')')
			if idx != -1:
				satpos = int(tmp[:idx])
				eDVBDB.getInstance().removeFlags(FLAG_SERVICE_NEW_FOUND, -1, -1, -1, satpos)
		self.close()

	def editAlternativeServices(self):
		self.csel.startMarkedEdit(EDIT_ALTERNATIVES)
		self.close()

	def showAlternativeServices(self):
		self.csel["Service"].editmode = True
		self.csel.enterPath(self.csel.getCurrentSelection())
		self.close()

	def removeAlternativeServices(self):
		self.csel.removeAlternativeServices()
		self.close()

	def addAlternativeServices(self):
		self.csel.addAlternativeServices()
		self.csel.startMarkedEdit(EDIT_ALTERNATIVES)
		self.close()

	def findCurrentlyPlayed(self):
		sel = self.csel.getCurrentSelection()
		if sel and sel.valid() and not self.csel.entry_marked:
			currentPlayingService = (hasattr(self.csel, "dopipzap") and self.csel.dopipzap) and self.session.pip.getCurrentService() or self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if currentPlayingService:
				self.csel.servicelist.setCurrent(currentPlayingService, adjust=False)
				if self.csel.getCurrentSelection() != currentPlayingService:
					self.csel.setCurrentSelection(sel)
				self.close()
		else:
			return 0

	def runPlugin(self, plugin):
		plugin(session=self.session, service=self.csel.getCurrentSelection())
		self.close()


class SelectionEventInfo:
	def __init__(self):
		self["Service"] = self["ServiceEvent"] = ServiceEvent()
		self["Event"] = Event()
		self.servicelist.connectSelChanged(self.__selectionChanged)
		self.timer = eTimer()
		self.timer.callback.append(self.updateEventInfo)
		self.onShown.append(self.__selectionChanged)
		self.onHide.append(self.__stopTimer)

	def __stopTimer(self):
		self.timer.stop()

	def __selectionChanged(self):
		self.timer.stop()
		if self.execing:
			self.update_root = False
			self.timer.start(100, True)

	def updateEventInfo(self):
		cur = self.getCurrentSelection()
		service = self["Service"]
		try:
			service.newService(cur)
			self["Event"].newEvent(service.event)
			if cur and service.event:
				if self.update_root and self.shown and self.getMutableList():
					root = self.getRoot()
					if root and hasattr(self, "editMode") and not self.editMode:
						self.clearPath()
						if self.bouquet_root:
							self.enterPath(self.bouquet_root)
						self.enterPath(root)
						self.setCurrentSelection(cur)
						self.update_root = False
				if not self.update_root:
					now = int(time())
					end_time = service.event.getBeginTime() + service.event.getDuration()
					if end_time > now:
						self.update_root = True
						self.timer.start((end_time - now) * 1000, True)
		except:
			pass


class ChannelSelectionEPG(InfoBarHotkey):
	def __init__(self):
		self.hotkeys = [("Info (EPG)", "info", "Infobar/openEventView"),
			("Info (EPG)" + " " + _("long"), "info_long", "Infobar/showEventInfoPlugins"),
			("EPG/Guide", "epg", "Plugins/Extensions/GraphMultiEPG/1"),
			("EPG/Guide" + " " + _("long"), "epg_long", "Infobar/showEventInfoPlugins")]
		self["ChannelSelectEPGActions"] = hotkeyActionMap(["ChannelSelectEPGActions"], dict((x[1], self.hotkeyGlobal) for x in self.hotkeys))
		self.eventViewEPG = self.start_bouquet = self.epg_bouquet = None
		self.currentSavedPath = []

	def getKeyFunctions(self, key):
		selection = eval("config.misc.hotkey." + key + ".value.split(',')")
		selected = []
		for x in selection:
			function = list(function for function in hotkey.functions if function[1] == x and function[2] == "EPG")
			if function:
				selected.append(function[0])
		return selected

	def runPlugin(self, plugin):
		Screens.InfoBar.InfoBar.instance.runPlugin(plugin)

	def getEPGPluginList(self, getAll=False):
		pluginlist = [(p.name, boundFunction(self.runPlugin, p), p.description or p.name) for p in plugins.getPlugins(where=PluginDescriptor.WHERE_EVENTINFO)
				if 'selectedevent' not in p.fnc.__code__.co_varnames] or []
		from Components.ServiceEventTracker import InfoBarCount
		if getAll or InfoBarCount == 1:
			pluginlist.append((_("Show EPG for current channel..."), self.openSingleServiceEPG, _("Display EPG list for current channel")))
		pluginlist.append((_("Multi EPG"), self.openMultiServiceEPG, _("Display EPG as MultiEPG")))
		pluginlist.append((_("Current event EPG"), self.openEventView, _("Display EPG info for current event")))
		return pluginlist

	def showEventInfoPlugins(self):
		pluginlist = self.getEPGPluginList()
		if pluginlist:
			self.session.openWithCallback(self.EventInfoPluginChosen, ChoiceBox, title=_("Please choose an extension..."), list=pluginlist, skin_name="EPGExtensionsList")
		else:
			self.openSingleServiceEPG()

	def EventInfoPluginChosen(self, answer):
		if answer is not None:
			answer[1]()

	def openEventView(self):
		epglist = []
		self.epglist = epglist
		ref = self.getCurrentSelection()
		epg = eEPGCache.getInstance()
		now_event = epg.lookupEventTime(ref, -1, 0)
		if now_event:
			epglist.append(now_event)
			next_event = epg.lookupEventTime(ref, -1, 1)
			if next_event:
				epglist.append(next_event)
		if epglist:
			self.eventViewEPG = self.session.openWithCallback(self.eventViewEPGClosed, EventViewEPGSelect, epglist[0], ServiceReference(ref), self.eventViewEPGCallback, self.openSingleServiceEPG, self.openMultiServiceEPG, self.openSimilarList)

	def eventViewEPGCallback(self, setEvent, setService, val):
		epglist = self.epglist
		if len(epglist) > 1:
			tmp = epglist[0]
			epglist[0] = epglist[1]
			epglist[1] = tmp
			setEvent(epglist[0])

	def eventViewEPGClosed(self, ret=False):
		self.eventViewEPG = None
		if ret:
			self.close()

	def openMultiServiceEPG(self):
		ref = self.getCurrentSelection()
		if ref:
			self.start_bouquet = self.epg_bouquet = self.servicelist.getRoot()
			self.savedService = ref
			self.currentSavedPath = self.servicePath[:]
			services = self.getServicesList(self.servicelist.getRoot())
			self.session.openWithCallback(self.SingleMultiEPGClosed, EPGSelection, services, self.zapToService, None, bouquetChangeCB=self.changeBouquetForMultiEPG)

	def openSingleServiceEPG(self):
		ref = self.getCurrentSelection()
		if ref:
			self.start_bouquet = self.epg_bouquet = self.servicelist.getRoot()
			self.savedService = ref
			self.currentSavedPath = self.servicePath[:]
			self.session.openWithCallback(self.SingleMultiEPGClosed, EPGSelection, ref, self.zapToService, serviceChangeCB=self.changeServiceCB, bouquetChangeCB=self.changeBouquetForSingleEPG)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def getServicesList(self, root):
		services = []
		servicelist = root and eServiceCenter.getInstance().list(root)
		if not servicelist is None:
			while True:
				service = servicelist.getNext()
				if not service.valid():
					break
				if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker):
					continue
				services.append(ServiceReference(service))
		return services

	def SingleMultiEPGClosed(self, ret=False):
		if ret:
			service = self.getCurrentSelection()
			if self.eventViewEPG:
				self.eventViewEPG.close(service)
			elif service is not None:
				self.close()
		else:
			if self.start_bouquet != self.epg_bouquet and len(self.currentSavedPath) > 0:
				self.clearPath()
				self.enterPath(self.bouquet_root)
				self.epg_bouquet = self.start_bouquet
				self.enterPath(self.epg_bouquet)
			self.setCurrentSelection(self.savedService)

	def changeBouquetForSingleEPG(self, direction, epg):
		if config.usage.multibouquet.value:
			inBouquet = self.getMutableList() is not None
			if inBouquet and len(self.servicePath) > 1:
				self.pathUp()
				if direction < 0:
					self.moveUp()
				else:
					self.moveDown()
				cur = self.getCurrentSelection()
				self.enterPath(cur)
				self.epg_bouquet = self.servicelist.getRoot()
				epg.setService(ServiceReference(self.getCurrentSelection()))

	def changeBouquetForMultiEPG(self, direction, epg):
		if config.usage.multibouquet.value:
			inBouquet = self.getMutableList() is not None
			if inBouquet and len(self.servicePath) > 1:
				self.pathUp()
				if direction < 0:
					self.moveUp()
				else:
					self.moveDown()
				cur = self.getCurrentSelection()
				self.enterPath(cur)
				self.epg_bouquet = self.servicelist.getRoot()
				services = self.getServicesList(self.epg_bouquet)
				epg.setServices(services)

	def changeServiceCB(self, direction, epg):
		beg = self.getCurrentSelection()
		while True:
			if direction > 0:
				self.moveDown()
			else:
				self.moveUp()
			cur = self.getCurrentSelection()
			if cur == beg or not (cur.flags & eServiceReference.isMarker):
				break
		epg.setService(ServiceReference(self.getCurrentSelection()))

	def zapToService(self, service, preview=False, zapback=False):
		if self.startServiceRef is None:
			self.startServiceRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if service is not None:
			if self.servicelist.getRoot() != self.epg_bouquet:
				self.servicelist.clearPath()
				if self.servicelist.bouquet_root != self.epg_bouquet:
					self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(self.epg_bouquet)
			self.servicelist.setCurrent(service)
		if not zapback or preview:
			self.zap(enable_pipzap=True)
		if (self.dopipzap or zapback) and not preview:
			self.zapBack()
		if not preview:
			self.startServiceRef = None
			self.startRoot = None
			self.revertMode = None


class ChannelSelectionEdit:
	def __init__(self):
		self.entry_marked = False
		self.bouquet_mark_edit = OFF
		self.mutableList = None
		self.__marked = []
		self.saved_title = None
		self.saved_root = None
		self.current_ref = None
		self.editMode = False
		self.confirmRemove = True

		class ChannelSelectionEditActionMap(ActionMap):
			def __init__(self, csel, contexts=[], actions={}, prio=0):
				ActionMap.__init__(self, contexts, actions, prio)
				self.csel = csel

			def action(self, contexts, action):
				if action == "cancel":
					self.csel.handleEditCancel()
					return 0 # fall-trough
				elif action == "ok":
					return 0 # fall-trough
				else:
					return ActionMap.action(self, contexts, action)

		self["ChannelSelectEditActions"] = ChannelSelectionEditActionMap(self, ["ChannelSelectEditActions", "OkCancelActions"],
			{
				"contextMenu": self.doContext,
			})

	def getMutableList(self, root=eServiceReference()):
		if not self.mutableList is None:
			return self.mutableList
		serviceHandler = eServiceCenter.getInstance()
		if not root.valid():
			root = self.getRoot()
		list = root and serviceHandler.list(root)
		if list is not None:
			return list.startEdit()
		return None

	def renameEntry(self):
		self.editMode = True
		cur = self.getCurrentSelection()
		if cur and cur.valid():
			name = eServiceCenter.getInstance().info(cur) and hasattr(eServiceCenter.getInstance().info(cur), "getName") and eServiceCenter.getInstance().info(cur).getName(cur) or ServiceReference(cur).getServiceName() or ""
			name = name.replace('\xc2\x86', '').replace('\xc2\x87', '')
			if name:
				self.session.openWithCallback(self.renameEntryCallback, VirtualKeyBoard, title=_("Please enter new name:"), text=name)
		else:
			return 0

	def renameEntryCallback(self, name):
		if name:
			mutableList = self.getMutableList()
			if mutableList:
				current = self.servicelist.getCurrent()
				current.setName(name)
				index = self.servicelist.getCurrentIndex()
				mutableList.removeService(current, False)
				mutableList.addService(current)
				mutableList.moveService(current, index)
				mutableList.flushChanges()
				self.servicelist.addService(current, True)
				self.servicelist.removeCurrent()
				if not self.servicelist.atEnd():
					self.servicelist.moveUp()

	def addMarker(self, name):
		current = self.servicelist.getCurrent()
		mutableList = self.getMutableList()
		cnt = 0
		while mutableList:
			str = '1:64:%d:0:0:0:0:0:0:0::%s' % (cnt, name)
			ref = eServiceReference(str)
			if current and current.valid():
				if not mutableList.addService(ref, current):
					self.servicelist.addService(ref, True)
					mutableList.flushChanges()
					break
			elif not mutableList.addService(ref):
				self.servicelist.addService(ref, True)
				mutableList.flushChanges()
				break
			cnt += 1

	def addAlternativeServices(self):
		cur_service = ServiceReference(self.getCurrentSelection())
		end = self.atEnd()
		root = self.getRoot()
		cur_root = root and ServiceReference(root)
		mutableBouquet = cur_root.list().startEdit()
		if mutableBouquet:
			name = cur_service.getServiceName()
			refstr = '_'.join(cur_service.ref.toString().split(':'))
			if self.mode == MODE_TV:
				str = '1:134:1:0:0:0:0:0:0:0:FROM BOUQUET \"alternatives.%s.tv\" ORDER BY bouquet' % (refstr)
			else:
				str = '1:134:2:0:0:0:0:0:0:0:FROM BOUQUET \"alternatives.%s.radio\" ORDER BY bouquet' % (refstr)
			new_ref = ServiceReference(str)
			if not mutableBouquet.addService(new_ref.ref, cur_service.ref):
				mutableBouquet.removeService(cur_service.ref)
				mutableBouquet.flushChanges()
				eDVBDB.getInstance().reloadBouquets()
				mutableAlternatives = new_ref.list().startEdit()
				if mutableAlternatives:
					mutableAlternatives.setListName(name)
					if mutableAlternatives.addService(cur_service.ref):
						print("add", cur_service.ref.toString(), "to new alternatives failed")
					mutableAlternatives.flushChanges()
					self.servicelist.addService(new_ref.ref, True)
					self.servicelist.removeCurrent()
					if not end:
						self.servicelist.moveUp()
					if cur_service.ref.toString() == self.lastservice.value:
						self.saveChannel(new_ref.ref)
					if self.startServiceRef and cur_service.ref == self.startServiceRef:
						self.startServiceRef = new_ref.ref
				else:
					print("get mutable list for new created alternatives failed")
			else:
				print("add", str, "to", cur_root.getServiceName(), "failed")
		else:
			print("bouquetlist is not editable")

	def addBouquet(self, bName, services):
		serviceHandler = eServiceCenter.getInstance()
		mutableBouquetList = serviceHandler.list(self.bouquet_root).startEdit()
		if mutableBouquetList:
			name = sanitizeFilename(bName)
			while os.path.isfile((self.mode == MODE_TV and '/etc/enigma2/userbouquet.%s.tv' or '/etc/enigma2/userbouquet.%s.radio') % name):
				name = name.rsplit('_', 1)
				name = ('_').join((name[0], len(name) == 2 and name[1].isdigit() and str(int(name[1]) + 1) or '1'))
			new_bouquet_ref = eServiceReference((self.mode == MODE_TV and '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.%s.tv" ORDER BY bouquet' or '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.%s.radio" ORDER BY bouquet') % name)
			if not mutableBouquetList.addService(new_bouquet_ref):
				mutableBouquetList.flushChanges()
				eDVBDB.getInstance().reloadBouquets()
				mutableBouquet = serviceHandler.list(new_bouquet_ref).startEdit()
				if mutableBouquet:
					mutableBouquet.setListName(bName)
					if services is not None:
						for service in services:
							if mutableBouquet.addService(service):
								print("add", service.toString(), "to new bouquet failed")
					mutableBouquet.flushChanges()
				else:
					print("get mutable list for new created bouquet failed")
				# do some voodoo to check if current_root is equal to bouquet_root
				cur_root = self.getRoot()
				str1 = cur_root and cur_root.toString()
				pos1 = str1 and str1.find("FROM BOUQUET") or -1
				pos2 = self.bouquet_rootstr.find("FROM BOUQUET")
				if pos1 != -1 and pos2 != -1 and str1[pos1:] == self.bouquet_rootstr[pos2:]:
					self.servicelist.addService(new_bouquet_ref)
					self.servicelist.resetRoot()
			else:
				print("add", str, "to bouquets failed")
		else:
			print("bouquetlist is not editable")

	def copyCurrentToBouquetList(self):
		provider = ServiceReference(self.getCurrentSelection())
		providerName = provider.getServiceName()
		serviceHandler = eServiceCenter.getInstance()
		services = serviceHandler.list(provider.ref)
		self.addBouquet(providerName, services and services.getContent('R', True))

	def removeAlternativeServices(self):
		cur_service = ServiceReference(self.getCurrentSelection())
		end = self.atEnd()
		root = self.getRoot()
		cur_root = root and ServiceReference(root)
		list = cur_service.list()
		first_in_alternative = list and list.getNext()
		if first_in_alternative:
			edit_root = cur_root and cur_root.list().startEdit()
			if edit_root:
				if not edit_root.addService(first_in_alternative, cur_service.ref):
					self.servicelist.addService(first_in_alternative, True)
					if cur_service.ref.toString() == self.lastservice.value:
						self.saveChannel(first_in_alternative)
					if self.startServiceRef and cur_service.ref == self.startServiceRef:
						self.startServiceRef = first_in_alternative
				else:
					print("couldn't add first alternative service to current root")
			else:
				print("couldn't edit current root!!")
		else:
			print("remove empty alternative list !!")
		self.removeBouquet()
		if not end:
			self.servicelist.moveUp()

	def removeBouquet(self):
		refstr = self.getCurrentSelection().toString()
		print("removeBouquet", refstr)
		pos = refstr.find('FROM BOUQUET "')
		filename = None
		self.removeCurrentService(bouquet=True)

	def removeSatelliteService(self):
		current = self.getCurrentSelection()
		eDVBDB.getInstance().removeService(current)
		refreshServiceList()
		if not self.atEnd():
			self.servicelist.moveUp()

	def removeSatelliteServices(self):
		current = self.getCurrentSelection()
		unsigned_orbpos = current.getUnsignedData(4) >> 16
		if unsigned_orbpos == 0xFFFF:
			messageText = _("Are you sure to remove all cable services?")
		elif unsigned_orbpos == 0xEEEE:
			messageText = _("Are you sure to remove all terrestrial services?")
		else:
			if unsigned_orbpos > 1800:
				orbpos = _("%.1f° W") % ((3600 - unsigned_orbpos) / 10.0)
			else:
				orbpos = _("%.1f° E") % (unsigned_orbpos / 10.0)
			# TRANSLATORS: The user is asked to delete all satellite services from a specific orbital position after a configuration change
			messageText = _("Are you sure to remove all %s services?") % orbpos
		self.session.openWithCallback(self.removeSatelliteServicesCallback, MessageBox, messageText)

	def removeSatelliteServicesCallback(self, answer):
		if answer:
			currentIndex = self.servicelist.getCurrentIndex()
			current = self.getCurrentSelection()
			unsigned_orbpos = current.getUnsignedData(4) >> 16
			if unsigned_orbpos == 0xFFFF:
				eDVBDB.getInstance().removeServices(int("0xFFFF0000", 16) - 0x100000000)
			elif unsigned_orbpos == 0xEEEE:
				eDVBDB.getInstance().removeServices(int("0xEEEE0000", 16) - 0x100000000)
			else:
				curpath = current.getPath()
				idx = curpath.find("satellitePosition == ")
				if idx != -1:
					tmp = curpath[idx + 21:]
					idx = tmp.find(')')
					if idx != -1:
						satpos = int(tmp[:idx])
						eDVBDB.getInstance().removeServices(-1, -1, -1, satpos)
			refreshServiceList()
			if hasattr(self, 'showSatellites'):
				self.showSatellites()
				self.servicelist.moveToIndex(currentIndex)
				if currentIndex != self.servicelist.getCurrentIndex():
					self.servicelist.instance.moveSelection(self.servicelist.instance.moveEnd)

#  multiple marked entry stuff ( edit mode, later multiepg selection )
	def startMarkedEdit(self, type):
		self.savedPath = self.servicePath[:]
		if type == EDIT_ALTERNATIVES:
			self.current_ref = self.getCurrentSelection()
			self.enterPath(self.current_ref)
		self.mutableList = self.getMutableList()
		# add all services from the current list to internal marked set in listboxservicecontent
		self.clearMarks() # this clears the internal marked set in the listboxservicecontent
		if type == EDIT_ALTERNATIVES:
			self.bouquet_mark_edit = EDIT_ALTERNATIVES
			self.functiontitle = ' ' + _("[alternative edit]")
		else:
			self.bouquet_mark_edit = EDIT_BOUQUET
			if config.usage.multibouquet.value:
				self.functiontitle = ' ' + _("[bouquet edit]")
			else:
				self.functiontitle = ' ' + _("[favourite edit]")
		self.compileTitle()
		self.__marked = self.servicelist.getRootServices()
		for x in self.__marked:
			self.servicelist.addMarked(eServiceReference(x))
		self["Service"].editmode = True

	def endMarkedEdit(self, abort):
		if not abort and self.mutableList is not None:
			new_marked = set(self.servicelist.getMarked())
			old_marked = set(self.__marked)
			removed = old_marked - new_marked
			added = new_marked - old_marked
			changed = False
			for x in removed:
				changed = True
				self.mutableList.removeService(eServiceReference(x))
			for x in added:
				changed = True
				self.mutableList.addService(eServiceReference(x))
			if changed:
				if self.bouquet_mark_edit == EDIT_ALTERNATIVES and not new_marked and self.__marked:
					self.mutableList.addService(eServiceReference(self.__marked[0]))
				self.mutableList.flushChanges()
		self.__marked = []
		self.clearMarks()
		self.bouquet_mark_edit = OFF
		self.mutableList = None
		self.functiontitle = ""
		self.compileTitle()
		# self.servicePath is just a reference to servicePathTv or Radio...
		# so we never ever do use the asignment operator in self.servicePath
		del self.servicePath[:] # remove all elements
		self.servicePath += self.savedPath # add saved elements
		del self.savedPath
		self.setRoot(self.servicePath[-1])
		if self.current_ref:
			self.setCurrentSelection(self.current_ref)
			self.current_ref = None

	def clearMarks(self):
		self.servicelist.clearMarks()

	def doMark(self):
		ref = self.servicelist.getCurrent()
		if self.servicelist.isMarked(ref):
			self.servicelist.removeMarked(ref)
		else:
			self.servicelist.addMarked(ref)

	def removeCurrentEntry(self, bouquet=False):
		if self.confirmRemove:
			list = [(_("yes"), True), (_("no"), False), (_("yes") + " " + _("and never ask in this session again"), "never")]
			self.session.openWithCallback(boundFunction(self.removeCurrentEntryCallback, bouquet), MessageBox, _("Are you sure to remove this entry?"), list=list)
		else:
			self.removeCurrentEntryCallback(bouquet, True)

	def removeCurrentEntryCallback(self, bouquet, answer):
		if answer:
			if answer == "never":
				self.confirmRemove = False
			if bouquet:
				self.removeBouquet()
			else:
				self.removeCurrentService()

	def removeCurrentService(self, bouquet=False):
		if self.movemode and self.entry_marked:
			self.toggleMoveMarked() # unmark current entry
		self.editMode = True
		ref = self.servicelist.getCurrent()
		mutableList = self.getMutableList()
		if ref.valid() and mutableList is not None:
			if not mutableList.removeService(ref):
				mutableList.flushChanges() #FIXME dont flush on each single removed service
				self.servicelist.removeCurrent()
				self.servicelist.resetRoot()
				playingref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
				if not bouquet and playingref and ref == playingref:
					self.channelSelected(doClose=False)

	def addServiceToBouquet(self, dest, service=None):
		mutableList = self.getMutableList(dest)
		if not mutableList is None:
			if service is None: #use current selected service
				service = self.servicelist.getCurrent()
			if not mutableList.addService(service):
				mutableList.flushChanges()
				# do some voodoo to check if current_root is equal to dest
				cur_root = self.getRoot()
				str1 = cur_root and cur_root.toString() or -1
				str2 = dest.toString()
				pos1 = str1.find("FROM BOUQUET")
				pos2 = str2.find("FROM BOUQUET")
				if pos1 != -1 and pos2 != -1 and str1[pos1:] == str2[pos2:]:
					self.servicelist.addService(service)
				self.servicelist.resetRoot()

	def toggleMoveMode(self, select=False):
		self.editMode = True
		if self.movemode:
			if self.entry_marked:
				self.toggleMoveMarked() # unmark current entry
			self.movemode = False
			self.mutableList.flushChanges() # FIXME add check if changes was made
			self.mutableList = None
			self.functiontitle = ""
			self.compileTitle()
			self.saved_title = None
			self.servicelist.resetRoot()
			self.servicelist.l.setHideNumberMarker(config.usage.hide_number_markers.value)
			self.setCurrentSelection(self.servicelist.getCurrent())
		else:
			self.mutableList = self.getMutableList()
			self.movemode = True
			select and self.toggleMoveMarked()
			self.saved_title = self.getTitle()
			self.functiontitle = ' ' + _("[move mode]")
			self.compileTitle()
			self.servicelist.l.setHideNumberMarker(False)
			self.setCurrentSelection(self.servicelist.getCurrent())
		self["Service"].editmode = True

	def handleEditCancel(self):
		if self.movemode: #movemode active?
			self.toggleMoveMode() # disable move mode
		elif self.bouquet_mark_edit != OFF:
			self.endMarkedEdit(True) # abort edit mode

	def toggleMoveMarked(self):
		if self.entry_marked:
			self.servicelist.setCurrentMarked(False)
			self.entry_marked = False
			self.pathChangeDisabled = False # re-enable path change
		else:
			self.servicelist.setCurrentMarked(True)
			self.entry_marked = True
			self.pathChangeDisabled = True # no path change allowed in movemod

	def doContext(self):
		self.session.openWithCallback(self.exitContext, ChannelContextMenu, self)

	def exitContext(self, close=False):
		l = self["list"]
		l.setFontsize()
		l.setItemsPerPage()
		l.setMode("MODE_TV")
		# l.setMode("MODE_TV") automatically sets "hide number marker" to
		# the config.usage.hide_number_markers.value so when we are in "move mode"
		# we need to force display of the markers here after l.setMode("MODE_TV")
		# has run. If l.setMode("MODE_TV") were ever removed above,
		# "self.servicelist.l.setHideNumberMarker(False)" could be moved
		# directly to the "else" clause of "def toggleMoveMode".
		if self.movemode:
			self.servicelist.l.setHideNumberMarker(False)
		if close:
			self.cancel()


MODE_TV = 0
MODE_RADIO = 1

# type 1 = digital television service
# type 4 = nvod reference service (NYI)
# type 17 = MPEG-2 HD digital television service
# type 22 = advanced codec SD digital television
# type 24 = advanced codec SD NVOD reference service (NYI)
# type 25 = advanced codec HD digital television
# type 27 = advanced codec HD NVOD reference service (NYI)
# type 31 = HEVC digital television service
# type 32 = HEVC UHD digital television service with HDR and/or a frame rate of 100 Hz, 120 000/1 001 Hz, or 120 Hz, or any combination of HDR and these frame rates
# type 2 = digital radio sound service
# type 10 = advanced codec digital radio sound service

service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 31) || (type == 32) || (type == 134) || (type == 195)'
service_types_radio = '1:7:2:0:0:0:0:0:0:0:(type == 2) || (type == 10)'


class ChannelSelectionBase(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["key_red"] = Button(_("All"))
		self["key_green"] = Button(_("Satellites"))
		self["key_yellow"] = Button(_("Provider"))
		self["key_blue"] = Button(_("Favourites"))

		self["list"] = ServiceList(self)
		self.servicelist = self["list"]

		self.numericalTextInput = NumericalTextInput(handleTimeout=False)
		self.numericalTextInput.setUseableChars('1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ')

		self.servicePathTV = []
		self.servicePathRadio = []
		self.servicePath = []
		self.history = []
		self.rootChanged = False
		self.startRoot = None
		self.selectionNumber = ""
		self.clearNumberSelectionNumberTimer = eTimer()
		self.clearNumberSelectionNumberTimer.callback.append(self.clearNumberSelectionNumber)
		self.protectContextMenu = True

		self.mode = MODE_TV
		self.dopipzap = False
		self.pathChangeDisabled = False
		self.movemode = False
		self.showSatDetails = False

		self["ChannelSelectBaseActions"] = NumberActionMap(["ChannelSelectBaseActions", "NumberActions", "InputAsciiActions"],
			{
				"showFavourites": self.showFavourites,
				"showAllServices": self.showAllServices,
				"showProviders": self.showProviders,
				"showSatellites": boundFunction(self.showSatellites, changeMode=True),
				"nextBouquet": self.nextBouquet,
				"prevBouquet": self.prevBouquet,
				"nextMarker": self.nextMarker,
				"prevMarker": self.prevMarker,
				"gotAsciiCode": self.keyAsciiCode,
				"keyLeft": self.keyLeft,
				"keyRight": self.keyRight,
				"keyRecord": self.keyRecord,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumber0
			}, -2)
		self.maintitle = _("Channel selection")
		self.modetitle = ""
		self.servicetitle = ""
		self.functiontitle = ""
		self.recallBouquetMode()

	def compileTitle(self):
		self.setTitle("%s%s%s%s" % (self.maintitle, self.modetitle, self.functiontitle, self.servicetitle))

	def getBouquetNumOffset(self, bouquet):
		if not config.usage.multibouquet.value:
			return 0
		str = bouquet.toString()
		offset = 0
		if 'userbouquet.' in bouquet.toCompareString():
			serviceHandler = eServiceCenter.getInstance()
			servicelist = serviceHandler.list(bouquet)
			if not servicelist is None:
				while True:
					serviceIterator = servicelist.getNext()
					if not serviceIterator.valid(): #check if end of list
						break
					number = serviceIterator.getChannelNum()
					if number > 0:
						offset = number - 1
						break
		return offset

	def recallBouquetMode(self):
		if self.mode == MODE_TV:
			self.service_types = service_types_tv
			if config.usage.multibouquet.value:
				self.bouquet_rootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
			else:
				self.bouquet_rootstr = '%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' % (self.service_types)
		else:
			self.service_types = service_types_radio
			if config.usage.multibouquet.value:
				self.bouquet_rootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet'
			else:
				self.bouquet_rootstr = '%s FROM BOUQUET "userbouquet.favourites.radio" ORDER BY bouquet' % (self.service_types)
		self.bouquet_root = eServiceReference(self.bouquet_rootstr)

	def setTvMode(self):
		self.mode = MODE_TV
		self.servicePath = self.servicePathTV
		self.recallBouquetMode()
		self.modetitle = _(" (TV)")
		self.compileTitle()

	def setRadioMode(self):
		self.mode = MODE_RADIO
		self.servicePath = self.servicePathRadio
		self.recallBouquetMode()
		self.modetitle = _(" (Radio)")
		self.compileTitle()

	def setRoot(self, root, justSet=False):
		if self.startRoot is None:
			self.startRoot = self.getRoot()
		path = root.getPath()
		isBouquet = 'FROM BOUQUET' in path and (root.flags & eServiceReference.isDirectory)
		inBouquetRootList = 'FROM BOUQUET "bouquets.' in path #FIXME HACK
		if not inBouquetRootList and isBouquet:
			self.servicelist.setMode(ServiceList.MODE_FAVOURITES)
		else:
			self.servicelist.setMode(ServiceList.MODE_NORMAL)
		self.servicelist.setRoot(root, justSet)
		self.rootChanged = True
		self.buildTitleString()

	def removeModeStr(self, str):
		if self.mode == MODE_TV:
			pos = str.find(_(" (TV)"))
		else:
			pos = str.find(_(" (Radio)"))
		if pos != -1:
			return str[:pos]
		return str

	def getServiceName(self, ref):
		str = self.removeModeStr(ServiceReference(ref).getServiceName())
		if 'bouquets' in str.lower():
			return _("User bouquets")
		if not str:
			pathstr = ref.getPath()
			if 'FROM PROVIDERS' in pathstr:
				return _("Provider")
			if 'FROM SATELLITES' in pathstr:
				return _("Satellites")
			if ') ORDER BY name' in pathstr:
				return _("All")
		return str

	def buildTitleString(self):
		self.servicetitle = ""
		pathlen = len(self.servicePath)
		if pathlen > 0:
			self.servicetitle = " - %s" % self.getServiceName(self.servicePath[0])
			if pathlen > 1:
				self.servicetitle += '/'
				if pathlen > 2:
					self.servicetitle += '../'
				self.servicetitle += self.getServiceName(self.servicePath[pathlen - 1])
		self.compileTitle()

	def moveUp(self):
		self.servicelist.moveUp()

	def moveDown(self):
		self.servicelist.moveDown()

	def clearPath(self):
		del self.servicePath[:]

	def enterPath(self, ref, justSet=False):
		self.servicePath.append(ref)
		self.setRoot(ref, justSet)

	def enterUserbouquet(self, root, save_root=True):
		self.clearPath()
		self.recallBouquetMode()
		if self.bouquet_root:
			self.enterPath(self.bouquet_root)
		self.enterPath(root)
		self.startRoot = None
		if save_root:
			self.saveRoot()

	def pathUp(self, justSet=False):
		prev = self.servicePath.pop()
		if self.servicePath:
			current = self.servicePath[-1]
			self.setRoot(current, justSet)
			if not justSet:
				self.setCurrentSelection(prev)
		return prev

	def isBasePathEqual(self, ref):
		if len(self.servicePath) > 1 and self.servicePath[0] == ref:
			return True
		return False

	def isPrevPathEqual(self, ref):
		length = len(self.servicePath)
		if length > 1 and self.servicePath[length - 2] == ref:
			return True
		return False

	def preEnterPath(self, refstr):
		return False

	def showAllServices(self):
		if not self.pathChangeDisabled:
			refstr = '%s ORDER BY name' % (self.service_types)
			if not self.preEnterPath(refstr):
				ref = eServiceReference(refstr)
				currentRoot = self.getRoot()
				if currentRoot is None or currentRoot != ref:
					self.clearPath()
					self.enterPath(ref)
					playingref = self.session.nav.getCurrentlyPlayingServiceReference()
					if playingref:
						self.setCurrentSelectionAlternative(playingref)

	def showSatellites(self, changeMode=False):
		if not self.pathChangeDisabled:
			refstr = '%s FROM SATELLITES ORDER BY satellitePosition' % (self.service_types)
			if not self.preEnterPath(refstr):
				ref = eServiceReference(refstr)
				justSet = False
				prev = None

				if self.isBasePathEqual(ref):
					if self.isPrevPathEqual(ref):
						justSet = True
					prev = self.pathUp(justSet)
				else:
					currentRoot = self.getRoot()
					if currentRoot is None or currentRoot != ref:
						justSet = True
						self.clearPath()
						self.enterPath(ref, True)
					if changeMode and currentRoot and currentRoot == ref:
						self.showSatDetails = not self.showSatDetails
						justSet = True
						self.clearPath()
						self.enterPath(ref, True)
				if justSet:
					addCableAndTerrestrialLater = []
					serviceHandler = eServiceCenter.getInstance()
					servicelist = serviceHandler.list(ref)
					if not servicelist is None:
						while True:
							service = servicelist.getNext()
							if not service.valid(): #check if end of list
								break
							unsigned_orbpos = service.getUnsignedData(4) >> 16
							orbpos = service.getData(4) >> 16
							if orbpos < 0:
								orbpos += 3600
							if "FROM PROVIDER" in service.getPath():
								service_type = self.showSatDetails and _("Providers")
							elif ("flags == %d" % (FLAG_SERVICE_NEW_FOUND)) in service.getPath():
								service_type = self.showSatDetails and _("New")
							else:
								service_type = _("Services")
							if service_type:
								if unsigned_orbpos == 0xFFFF: #Cable
									service_name = _("Cable")
									addCableAndTerrestrialLater.append(("%s - %s" % (service_name, service_type), service.toString()))
								elif unsigned_orbpos == 0xEEEE: #Terrestrial
									service_name = _("Terrestrial")
									addCableAndTerrestrialLater.append(("%s - %s" % (service_name, service_type), service.toString()))
								else:
									try:
										service_name = str(nimmanager.getSatDescription(orbpos))
									except:
										if orbpos > 1800: # west
											orbpos = 3600 - orbpos
											h = _("W")
										else:
											h = _("E")
										service_name = ("%d.%d" + h) % (orbpos / 10, orbpos % 10)
									service.setName("%s - %s" % (service_name, service_type))
									self.servicelist.addService(service)
						cur_ref = self.session.nav.getCurrentlyPlayingServiceReference()
						self.servicelist.l.sort()
						if cur_ref:
							pos = self.service_types.rfind(':')
							refstr = '%s (channelID == %08x%04x%04x) && %s ORDER BY name' % (self.service_types[:pos + 1],
								cur_ref.getUnsignedData(4), # NAMESPACE
								cur_ref.getUnsignedData(2), # TSID
								cur_ref.getUnsignedData(3), # ONID
								self.service_types[pos + 1:])
							ref = eServiceReference(refstr)
							ref.setName(_("Current transponder"))
							self.servicelist.addService(ref, beforeCurrent=True)
						for (service_name, service_ref) in addCableAndTerrestrialLater:
							ref = eServiceReference(service_ref)
							ref.setName(service_name)
							self.servicelist.addService(ref, beforeCurrent=True)
						self.servicelist.l.FillFinished()
						if prev is not None:
							self.setCurrentSelection(prev)
						elif cur_ref:
							refstr = cur_ref.toString()
							op = "".join(refstr.split(':', 10)[6:7])
							if len(op) >= 4:
								hop = int(op[:-4], 16)
								if len(op) >= 7 and not op.endswith('0000'):
									op = op[:-4] + '0000'
								refstr = '1:7:0:0:0:0:%s:0:0:0:(satellitePosition == %s) && %s ORDER BY name' % (op, hop, self.service_types[self.service_types.rfind(':') + 1:])
								self.setCurrentSelectionAlternative(eServiceReference(refstr))

	def showProviders(self):
		if not self.pathChangeDisabled:
			refstr = '%s FROM PROVIDERS ORDER BY name' % (self.service_types)
			if not self.preEnterPath(refstr):
				ref = eServiceReference(refstr)
				if self.isBasePathEqual(ref):
					self.pathUp()
				else:
					currentRoot = self.getRoot()
					if currentRoot is None or currentRoot != ref:
						self.clearPath()
						self.enterPath(ref)
						service = self.session.nav.getCurrentService()
						if service:
							info = service.info()
							if info:
								provider = info.getInfoString(iServiceInformation.sProvider)
								refstr = '1:7:0:0:0:0:0:0:0:0:(provider == \"%s\") && %s ORDER BY name:%s' % (provider, self.service_types[self.service_types.rfind(':') + 1:], provider)
								self.setCurrentSelectionAlternative(eServiceReference(refstr))

	def changeBouquet(self, direction):
		if not self.pathChangeDisabled:
			if len(self.servicePath) > 1:
				#when enter satellite root list we must do some magic stuff..
				ref = eServiceReference('%s FROM SATELLITES ORDER BY satellitePosition' % (self.service_types))
				if self.isBasePathEqual(ref):
					self.showSatellites()
				else:
					self.pathUp()
				if direction < 0:
					self.moveUp()
				else:
					self.moveDown()
				ref = self.getCurrentSelection()
				if not self.getMutableList() or Components.ParentalControl.parentalControl.isServicePlayable(ref, self.changeBouquetParentalControlCallback, self.session):
					self.changeBouquetParentalControlCallback(ref)

	def changeBouquetParentalControlCallback(self, ref):
		self.enterPath(ref)
		self.revertMode = None
		if config.usage.changebouquet_set_history.value and self.shown:
			live_ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			pip_ref = hasattr(self.session, "pip") and self.session.pip.getCurrentService()
			dopipzap = hasattr(self, "dopipzap") and self.dopipzap
			if live_ref and not pip_ref and not dopipzap:
				if live_ref and self.servicelist.setCurrent(live_ref, adjust=False) is None:
					return
			elif live_ref and pip_ref and not dopipzap:
				if live_ref and self.servicelist.setCurrent(live_ref, adjust=False) is None:
					return
			elif dopipzap:
				if pip_ref and self.servicelist.setCurrent(pip_ref, adjust=False) is None:
					return
				elif live_ref and self.servicelist.setCurrent(live_ref, adjust=False) is None:
					return
			root = self.getRoot()
			prev = None
			for path in self.history:
				if len(path) > 2 and path[1] == root:
					prev = path[2]
			if prev is not None:
				self.setCurrentSelection(prev)

	def inBouquet(self):
		if self.servicePath and self.servicePath[0] == self.bouquet_root:
			return True
		return False

	def atBegin(self):
		return self.servicelist.atBegin()

	def atEnd(self):
		return self.servicelist.atEnd()

	def nextBouquet(self):
		if self.shown and config.usage.oldstyle_channel_select_controls.value:
			self.servicelist.instance.moveSelection(self.servicelist.instance.pageUp)
		elif "reverseB" in config.usage.servicelist_cursor_behavior.value:
			self.changeBouquet(-1)
		else:
			self.changeBouquet(+1)

	def prevBouquet(self):
		if self.shown and config.usage.oldstyle_channel_select_controls.value:
			self.servicelist.instance.moveSelection(self.servicelist.instance.pageDown)
		elif "reverseB" in config.usage.servicelist_cursor_behavior.value:
			self.changeBouquet(+1)
		else:
			self.changeBouquet(-1)

	def keyLeft(self):
		if config.usage.oldstyle_channel_select_controls.value:
			self.changeBouquet(-1)
		else:
			self.servicelist.instance.moveSelection(self.servicelist.instance.pageUp)

	def keyRight(self):
		if config.usage.oldstyle_channel_select_controls.value:
			self.changeBouquet(+1)
		else:
			self.servicelist.instance.moveSelection(self.servicelist.instance.pageDown)

	def keyRecord(self):
		ref = self.getCurrentSelection()
		if ref and not (ref.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)):
			Screens.InfoBar.InfoBar.instance.instantRecord(serviceRef=ref)

	def showFavourites(self):
		if not self.pathChangeDisabled:
			if not self.preEnterPath(self.bouquet_rootstr):
				if self.isBasePathEqual(self.bouquet_root):
					self.pathUp()
				else:
					currentRoot = self.getRoot()
					if currentRoot is None or currentRoot != self.bouquet_root:
						self.clearPath()
						self.enterPath(self.bouquet_root)

	def keyNumber0(self, number):
		if len(self.servicePath) > 1 and not self.selectionNumber:
			self.keyGoUp()
		else:
			self.keyNumberGlobal(number)

	def keyNumberGlobal(self, number):
		if self.isBasePathEqual(self.bouquet_root):
			if hasattr(self, "editMode") and self.editMode:
				if number == 2:
					self.renameEntry()
				if number == 6:
					self.toggleMoveMode(select=True)
				if number == 8:
					self.removeCurrentEntry(bouquet=False)
			else:
				self.numberSelectionActions(number)
		else:
			current_root = self.getRoot()
			if current_root and 'FROM BOUQUET "bouquets.' in current_root.getPath():
				if hasattr(self, "editMode") and self.editMode:
					if number == 2:
						self.renameEntry()
					if number == 6:
						self.toggleMoveMode(select=True)
					if number == 8:
						self.removeCurrentEntry(bouquet=True)
				else:
					self.numberSelectionActions(number)
			else:
				unichar = self.numericalTextInput.getKey(number)
				if len(unichar) == 1:
					self.servicelist.moveToChar(unichar[0])

	def numberSelectionActions(self, number):
		if not (hasattr(self, "movemode") and self.movemode):
			if len(self.selectionNumber) > 4:
				self.clearNumberSelectionNumber()
			self.selectionNumber = self.selectionNumber + str(number)
			ref, bouquet = Screens.InfoBar.InfoBar.instance.searchNumber(int(self.selectionNumber), bouquet=self.getRoot())
			if ref:
				if not ref.flags & eServiceReference.isMarker:
					self.enterUserbouquet(bouquet, save_root=False)
					self.setCurrentSelection(ref)
				self.clearNumberSelectionNumberTimer.start(1000, True)
			else:
				self.clearNumberSelectionNumber()

	def clearNumberSelectionNumber(self):
		self.clearNumberSelectionNumberTimer.stop()
		self.selectionNumber = ""

	def keyAsciiCode(self):
		unichar = chr(getPrevAsciiCode())
		if len(unichar) == 1:
			self.servicelist.moveToChar(unichar[0])

	def getRoot(self):
		return self.servicelist.getRoot()

	def getCurrentSelection(self):
		return self.servicelist.getCurrent()

	def setCurrentSelection(self, service):
		if service:
			self.servicelist.setCurrent(service, adjust=False)

	def setCurrentSelectionAlternative(self, ref):
		if self.bouquet_mark_edit == EDIT_ALTERNATIVES and not (ref.flags & eServiceReference.isDirectory):
			for markedService in self.servicelist.getMarked():
				markedService = eServiceReference(markedService)
				self.setCurrentSelection(markedService)
				if markedService == self.getCurrentSelection():
					return
		self.setCurrentSelection(ref)

	def getBouquetList(self):
		bouquets = []
		serviceHandler = eServiceCenter.getInstance()
		if config.usage.multibouquet.value:
			list = serviceHandler.list(self.bouquet_root)
			if list:
				while True:
					s = list.getNext()
					if not s.valid():
						break
					if s.flags & eServiceReference.isDirectory and not s.flags & eServiceReference.isInvisible:
						info = serviceHandler.info(s)
						if info:
							bouquets.append((info.getName(s), s))
				return bouquets
		else:
			info = serviceHandler.info(self.bouquet_root)
			if info:
				bouquets.append((info.getName(self.bouquet_root), self.bouquet_root))
			return bouquets
		return None

	def keyGoUp(self):
		if len(self.servicePath) > 1:
			if self.isBasePathEqual(self.bouquet_root):
				self.showFavourites()
			else:
				ref = eServiceReference('%s FROM SATELLITES ORDER BY satellitePosition' % (self.service_types))
				if self.isBasePathEqual(ref):
					self.showSatellites()
				else:
					ref = eServiceReference('%s FROM PROVIDERS ORDER BY name' % (self.service_types))
					if self.isBasePathEqual(ref):
						self.showProviders()
					else:
						self.showAllServices()

	def nextMarker(self):
		self.servicelist.moveToNextMarker()

	def prevMarker(self):
		self.servicelist.moveToPrevMarker()

	def gotoCurrentServiceOrProvider(self, ref):
		str = ref.toString()
		playingref = self.session.nav.getCurrentlyPlayingServiceReference()
		if _("Providers") in str:
			service = self.session.nav.getCurrentService()
			if service:
				info = service.info()
				if info and playingref:
					provider = info.getInfoString(iServiceInformation.sProvider)
					op = int(playingref.toString().split(':')[6][:-4] or "0", 16)
					refstr = '1:7:0:0:0:0:0:0:0:0:(provider == \"%s\") && (satellitePosition == %s) && %s ORDER BY name:%s' % (provider, op, self.service_types[self.service_types.rfind(':') + 1:], provider)
					self.setCurrentSelection(eServiceReference(refstr))
		elif not self.isBasePathEqual(self.bouquet_root) or self.bouquet_mark_edit == EDIT_ALTERNATIVES:
			if playingref:
				self.setCurrentSelectionAlternative(playingref)


HISTORYSIZE = 20

#config for lastservice
config.tv = ConfigSubsection()
config.tv.lastservice = ConfigText()
config.tv.lastroot = ConfigText()
config.radio = ConfigSubsection()
config.radio.lastservice = ConfigText()
config.radio.lastroot = ConfigText()
config.servicelist = ConfigSubsection()
config.servicelist.lastmode = ConfigText(default="tv")
config.servicelist.startupservice = ConfigText()
config.servicelist.startupservice_onstandby = ConfigYesNo(default=False)
config.servicelist.startuproot = ConfigText()
config.servicelist.startupmode = ConfigText(default="tv")


class ChannelSelection(ChannelSelectionBase, ChannelSelectionEdit, ChannelSelectionEPG, SelectionEventInfo):
	ALLOW_SUSPEND = True

	def __init__(self, session):
		ChannelSelectionBase.__init__(self, session)
		ChannelSelectionEdit.__init__(self)
		ChannelSelectionEPG.__init__(self)
		SelectionEventInfo.__init__(self)

		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"cancel": self.cancel,
				"ok": self.channelSelected,
				"keyRadio": self.doRadioButton,
				"keyTV": self.doTVButton,
			})

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStart: self.__evServiceStart,
				iPlayableService.evEnd: self.__evServiceEnd
			})

		self.startServiceRef = None

		self.history = []
		self.history_pos = 0
		self.delhistpoint = None

		if config.servicelist.startupservice.value and config.servicelist.startuproot.value:
			config.servicelist.lastmode.value = config.servicelist.startupmode.value
			if config.servicelist.lastmode.value == "tv":
				config.tv.lastservice.value = config.servicelist.startupservice.value
				config.tv.lastroot.value = config.servicelist.startuproot.value
			elif config.servicelist.lastmode.value == "radio":
				config.radio.lastservice.value = config.servicelist.startupservice.value
				config.radio.lastroot.value = config.servicelist.startuproot.value

		self.lastservice = config.tv.lastservice
		self.lastroot = config.tv.lastroot
		self.revertMode = None
		config.usage.multibouquet.addNotifier(self.multibouquet_config_changed)
		self.new_service_played = False
		self.dopipzap = False
		self.onExecBegin.append(self.asciiOn)
		self.mainScreenMode = None
		self.mainScreenRoot = None

		self.lastChannelRootTimer = eTimer()
		self.lastChannelRootTimer.callback.append(self.__onCreate)
		self.lastChannelRootTimer.start(100, True)
		self.pipzaptimer = eTimer()

	def asciiOn(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def asciiOff(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)

	def multibouquet_config_changed(self, val):
		self.recallBouquetMode()

	def __evServiceStart(self):
		if self.dopipzap and hasattr(self.session, 'pip'):
			self.servicelist.setPlayableIgnoreService(self.session.pip.getCurrentServiceReference() or eServiceReference())
		else:
			service = self.session.nav.getCurrentService()
			if service:
				info = service.info()
				if info:
					refstr = info.getInfoString(iServiceInformation.sServiceref)
					self.servicelist.setPlayableIgnoreService(eServiceReference(refstr))

	def __evServiceEnd(self):
		self.servicelist.setPlayableIgnoreService(eServiceReference())

	def setMode(self):
		self.rootChanged = True
		self.restoreRoot()
		lastservice = eServiceReference(self.lastservice.value)
		if lastservice.valid():
			self.setCurrentSelection(lastservice)
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref and Components.ParentalControl.parentalControl.isProtected(ref):
				if self.getCurrentSelection() and self.getCurrentSelection() != ref:
					self.setCurrentSelection(ref)

	def doTVButton(self):
		if self.mode == MODE_TV:
			self.channelSelected(doClose=False)
		else:
			self.setModeTv()

	def setModeTv(self):
		if self.revertMode is None:
			self.revertMode = self.mode
		self.lastservice = config.tv.lastservice
		self.lastroot = config.tv.lastroot
		config.servicelist.lastmode.value = "tv"
		self.setTvMode()
		self.setMode()

	def doRadioButton(self):
		if self.mode == MODE_RADIO:
			self.channelSelected(doClose=False)
		else:
			self.setModeRadio()

	def setModeRadio(self):
		if self.revertMode is None:
			self.revertMode = self.mode
		if config.usage.e1like_radio_mode.value:
			self.lastservice = config.radio.lastservice
			self.lastroot = config.radio.lastroot
			config.servicelist.lastmode.value = "radio"
			self.setRadioMode()
			self.setMode()

	def __onCreate(self):
		if config.usage.e1like_radio_mode.value:
			if config.servicelist.lastmode.value == "tv":
				self.setModeTv()
			else:
				self.setModeRadio()
		else:
			self.setModeTv()
		lastservice = eServiceReference(self.lastservice.value)
		if lastservice.valid():
			self.zap()

	def channelSelected(self, doClose=True):
		ref = self.getCurrentSelection()
		if ref.type == -1:
			return
		playingref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if config.usage.channelselection_preview.value and (playingref is None or self.getCurrentSelection() != playingref):
			doClose = False
		if not self.startServiceRef and not doClose:
			self.startServiceRef = playingref
		if self.movemode and (self.isBasePathEqual(self.bouquet_root) or "userbouquet." in ref.toString()):
			self.toggleMoveMarked()
		elif (ref.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
			if Components.ParentalControl.parentalControl.isServicePlayable(ref, self.bouquetParentalControlCallback, self.session):
				self.enterPath(ref)
				self.gotoCurrentServiceOrProvider(ref)
				self.revertMode = None
		elif self.bouquet_mark_edit != OFF:
			if not (self.bouquet_mark_edit == EDIT_ALTERNATIVES and ref.flags & eServiceReference.isGroup):
				self.doMark()
		elif not ref.flags & eServiceReference.isMarker:
			root = self.getRoot()
			if not root or not (root.flags & eServiceReference.isGroup):
				self.zap(enable_pipzap=doClose, preview_zap=not doClose)
				self.asciiOff()
				if doClose:
					if self.dopipzap:
						self.zapBack()
					self.startServiceRef = None
					self.startRoot = None
					self.correctChannelNumber()
					self.movemode and self.toggleMoveMode()
					self.editMode = False
					self.protectContextMenu = True
					self.close(ref)

	def bouquetParentalControlCallback(self, ref):
		self.enterPath(ref)
		self.gotoCurrentServiceOrProvider(ref)
		self.revertMode = None

	def togglePipzap(self):
		assert (self.session.pip)
		if self.dopipzap:
			# Mark PiP as inactive and effectively deactivate pipzap
			self.hidePipzapMessage()
			self.dopipzap = False

			# Disable PiP if not playing a service
			if self.session.pip.pipservice is None:
				self.session.pipshown = False
				del self.session.pip
			self.__evServiceStart()
			# Move to playing service
			lastservice = eServiceReference(self.lastservice.value)
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref and Components.ParentalControl.parentalControl.isProtected(ref):
				lastservice = ref
			if lastservice.valid() and self.getCurrentSelection() != lastservice:
				self.setCurrentSelection(lastservice)
				if self.getCurrentSelection() != lastservice:
					self.servicelist.setCurrent(lastservice)

			self.modetitle = _(" (TV)")
		else:
			# Mark PiP as active and effectively active pipzap
			self.showPipzapMessage()
			self.dopipzap = True
			self.__evServiceStart()
			# Move to service playing in pip (will not work with subservices)
			self.setCurrentSelection(self.session.pip.getCurrentService())
			self.modetitle = _(" (PiP)")
		self.buildTitleString()

	def showPipzapMessage(self):
		time = config.usage.infobar_timeout.index
		if time:
			self.pipzaptimer.callback.append(self.hidePipzapMessage)
			self.pipzaptimer.startLongTimer(time)
		self.session.pip.active()

	def hidePipzapMessage(self):
		if self.pipzaptimer.isActive():
			self.pipzaptimer.callback.remove(self.hidePipzapMessage)
			self.pipzaptimer.stop()
		self.session.pip.inactive()

	#called from infoBar and channelSelected
	def zap(self, enable_pipzap=False, preview_zap=False, checkParentalControl=True, ref=None):
		self.curRoot = self.startRoot
		nref = ref or self.getCurrentSelection()
		ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if enable_pipzap and self.dopipzap:
			ref = self.session.pip.getCurrentService()
			if ref is None or ref != nref:
				if nref:
					if not checkParentalControl or Components.ParentalControl.parentalControl.isServicePlayable(nref, boundFunction(self.zap, enable_pipzap=True, checkParentalControl=False)):
						self.session.pip.playService(nref)
						self.__evServiceStart()
						self.showPipzapMessage()
						self.setCurrentSelection(nref)
				else:
					self.setStartRoot(self.curRoot)
					self.setCurrentSelection(ref)
		elif ref is None or ref != nref:
			Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(boundFunction(self.zapCheckTimeshiftCallback, preview_zap, nref))
		elif not preview_zap:
			self.saveRoot()
			self.saveChannel(nref)
			config.servicelist.lastmode.save()
			self.setCurrentSelection(nref)
			if self.startServiceRef is None or nref != self.startServiceRef:
				self.addToHistory(nref)
			self.rootChanged = False
			self.revertMode = None

	def zapCheckTimeshiftCallback(self, preview_zap, nref, answer):
		if answer:
			self.new_service_played = True
			self.session.nav.playService(nref, adjust=preview_zap and [0, self.session] or True)
			if not preview_zap:
				self.saveRoot()
				self.saveChannel(nref)
				config.servicelist.lastmode.save()
				if self.startServiceRef is None or nref != self.startServiceRef:
					self.addToHistory(nref)
				if self.dopipzap:
					self.session.pip.servicePath = self.getCurrentServicePath()
					self.setCurrentSelection(self.session.pip.getCurrentService())
				else:
					self.mainScreenMode = config.servicelist.lastmode.value
					self.mainScreenRoot = self.getRoot()
				self.revertMode = None
			else:
				RemovePopup("Parental control")
				self.setCurrentSelection(nref)
		elif not self.dopipzap:
			self.setStartRoot(self.curRoot)
			self.setCurrentSelection(self.session.nav.getCurrentlyPlayingServiceOrGroup())
		if not preview_zap:
			self.hide()

	def newServicePlayed(self):
		ret = self.new_service_played
		self.new_service_played = False
		return ret

	def addToHistory(self, ref):
		if self.delhistpoint is not None:
			x = self.delhistpoint
			while x <= len(self.history)-1:
				del self.history[x]
		self.delhistpoint = None

		if self.servicePath is not None:
			tmp = self.servicePath[:]
			tmp.append(ref)
			self.history.append(tmp)
			hlen = len(self.history)
			x = 0
			while x < hlen - 1:
				if self.history[x][-1] == ref:
					del self.history[x]
					hlen -= 1
				else:
					x += 1

			if hlen > HISTORYSIZE:
				del self.history[0]
				hlen -= 1
			self.history_pos = hlen - 1

	def historyBack(self):
		hlen = len(self.history)
		currentPlayedRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if hlen > 0 and currentPlayedRef and self.history[self.history_pos][-1] != currentPlayedRef:
			self.addToHistory(currentPlayedRef)
			hlen = len(self.history)
		if hlen > 1 and self.history_pos > 0:
			self.history_pos -= 1
			self.setHistoryPath()
		self.delhistpoint = self.history_pos+1

	def historyNext(self):
		self.delhistpoint = None
		hlen = len(self.history)
		if hlen > 1 and self.history_pos < (hlen - 1):
			self.history_pos += 1
			self.setHistoryPath()

	def setHistoryPath(self, doZap=True):
		path = self.history[self.history_pos][:]
		ref = path.pop()
		del self.servicePath[:]
		self.servicePath += path
		self.saveRoot()
		root = path[-1]
		cur_root = self.getRoot()
		if cur_root and cur_root != root:
			self.setRoot(root)
		if doZap:
			self.session.nav.playService(ref, adjust=False)
		if self.dopipzap:
			self.setCurrentSelection(self.session.pip.getCurrentService())
		else:
			self.setCurrentSelection(ref)
		self.saveChannel(ref)

	def historyClear(self):
		if self and self.servicelist:
			for i in range(0, len(self.history)-1):
				del self.history[0]
			self.history_pos = len(self.history)-1
			return True
		return False

	def historyZap(self, direction):
		hlen = len(self.history)
		if hlen < 1: return
		mark = self.history_pos
		selpos = self.history_pos + direction
		if selpos < 0: selpos = 0
		if selpos > hlen-1: selpos = hlen-1
		serviceHandler = eServiceCenter.getInstance()
		historylist = [ ]
		for x in self.history:
			info = serviceHandler.info(x[-1])
			if info: historylist.append((info.getName(x[-1]), x[-1]))
		self.session.openWithCallback(self.historyMenuClosed, HistoryZapSelector, historylist, selpos, mark, invert_items=True, redirect_buttons=True, wrap_around=True)

	def historyMenuClosed(self, retval):
		if not retval: return
		hlen = len(self.history)
		pos = 0
		for x in self.history:
			if x[-1] == retval: break
			pos += 1
		self.delhistpoint = pos+1
		if pos < hlen and pos != self.history_pos:
			tmp = self.history[pos]
			# self.history.append(tmp)
			# del self.history[pos]
			self.history_pos = pos
			self.setHistoryPath()

	def saveRoot(self):
		path = ""
		for i in self.servicePath:
			path += i.toString()
			path += ";"
		if path and path != self.lastroot.value:
			if self.mode == MODE_RADIO and "FROM BOUQUET \"bouquets.tv\"" in path:
				self.setModeTv()
			elif self.mode == MODE_TV and "FROM BOUQUET \"bouquets.radio\"" in path:
				self.setModeRadio()
			self.lastroot.value = path
			self.lastroot.save()

	def restoreRoot(self):
		tmp = [x for x in self.lastroot.value.split(';') if x != '']
		current = [x.toString() for x in self.servicePath]
		if tmp != current or self.rootChanged:
			self.clearPath()
			cnt = 0
			for i in tmp:
				self.servicePath.append(eServiceReference(i))
				cnt += 1
			if cnt:
				path = self.servicePath.pop()
				self.enterPath(path)
			else:
				self.showFavourites()
				self.saveRoot()
			self.rootChanged = False

	def preEnterPath(self, refstr):
		if self.servicePath and self.servicePath[0] != eServiceReference(refstr):
			pathstr = self.lastroot.value
			if pathstr is not None and refstr in pathstr:
				self.restoreRoot()
				lastservice = eServiceReference(self.lastservice.value)
				if lastservice.valid():
					self.setCurrentSelection(lastservice)
				return True
		return False

	def saveChannel(self, ref):
		if ref is not None:
			refstr = ref.toString()
		else:
			refstr = ""
		if refstr != self.lastservice.value and not Components.ParentalControl.parentalControl.isProtected(ref):
			self.lastservice.value = refstr
			self.lastservice.save()

	def setCurrentServicePath(self, path, doZap=True):
		hlen = len(self.history)
		if not hlen:
			self.history.append(path)
			self.history_pos = 0
		if hlen == 1:
			self.history[self.history_pos] = path
		else:
			if path in self.history:
				self.history.remove(path)
				self.history_pos -= 1
			tmp = self.history[self.history_pos][:]
			self.history.append(tmp)
			self.history_pos += 1
			self.history[self.history_pos] = path
		self.setHistoryPath(doZap)

	def getCurrentServicePath(self):
		if self.history:
			return self.history[self.history_pos]
		return None

	def recallPrevService(self):
		hlen = len(self.history)
		currentPlayedRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if hlen > 0 and currentPlayedRef and self.history[self.history_pos][-1] != currentPlayedRef:
			self.addToHistory(currentPlayedRef)
			hlen = len(self.history)
		if hlen > 1:
			if self.history_pos == hlen - 1:
				tmp = self.history[self.history_pos]
				self.history[self.history_pos] = self.history[self.history_pos - 1]
				self.history[self.history_pos - 1] = tmp
			else:
				tmp = self.history[self.history_pos + 1]
				self.history[self.history_pos + 1] = self.history[self.history_pos]
				self.history[self.history_pos] = tmp
			self.setHistoryPath()

	def cancel(self):
		if self.revertMode is None:
			self.restoreRoot()
			if self.dopipzap:
				# This unfortunately won't work with subservices
				self.setCurrentSelection(self.session.pip.getCurrentService())
			else:
				lastservice = eServiceReference(self.lastservice.value)
				ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
				if ref and Components.ParentalControl.parentalControl.isProtected(ref):
					lastservice = ref
				if lastservice.valid() and self.getCurrentSelection() != lastservice:
					self.setCurrentSelection(lastservice)
		self.asciiOff()
		self.zapBack()
		self.correctChannelNumber()
		self.editMode = False
		self.protectContextMenu = True
		self.close(None)

	def zapBack(self):
		playingref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if self.startServiceRef and (playingref is None or playingref != self.startServiceRef):
			self.setStartRoot(self.startRoot)
			self.new_service_played = True
			self.session.nav.playService(self.startServiceRef)
			self.saveChannel(self.startServiceRef)
		else:
			self.restoreMode()
		self.startServiceRef = None
		self.startRoot = None
		if self.dopipzap:
			# This unfortunately won't work with subservices
			self.setCurrentSelection(self.session.pip.getCurrentService())
		else:
			lastservice = eServiceReference(self.lastservice.value)
			if lastservice.valid() and self.getCurrentSelection() == lastservice:
				pass	# keep current selection
			else:
				self.setCurrentSelection(playingref)

	def setStartRoot(self, root):
		if root:
			if self.revertMode == MODE_TV:
				self.setModeTv()
			elif self.revertMode == MODE_RADIO:
				self.setModeRadio()
			self.revertMode = None
			self.enterUserbouquet(root)

	def restoreMode(self):
		if self.revertMode == MODE_TV:
			self.setModeTv()
		elif self.revertMode == MODE_RADIO:
			self.setModeRadio()
		self.revertMode = None

	def correctChannelNumber(self):
		current_ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if self.dopipzap:
			tmp_mode = config.servicelist.lastmode.value
			tmp_root = self.getRoot()
			tmp_ref = self.getCurrentSelection()
			pip_ref = self.session.pip.getCurrentService()
			if tmp_ref and pip_ref and tmp_ref != pip_ref:
				self.revertMode = None
				return
			if self.mainScreenMode == "tv":
				self.setModeTv()
			elif self.mainScreenMode == "radio":
				self.setModeRadio()
			if self.mainScreenRoot:
				self.setRoot(self.mainScreenRoot)
				self.setCurrentSelection(current_ref)
		selected_ref = self.getCurrentSelection()
		if selected_ref and current_ref and selected_ref.getChannelNum() != current_ref.getChannelNum():
			oldref = self.session.nav.currentlyPlayingServiceReference
			if oldref and selected_ref == oldref or (oldref != current_ref and selected_ref == current_ref):
				self.session.nav.currentlyPlayingServiceOrGroup = selected_ref
				self.session.nav.pnav.navEvent(iPlayableService.evStart)
		if self.dopipzap:
			if tmp_mode == "tv":
				self.setModeTv()
			elif tmp_mode == "radio":
				self.setModeRadio()
			self.enterUserbouquet(tmp_root)
			self.modetitle = _(" (PiP)")
			self.buildTitleString()
			if tmp_ref and pip_ref and tmp_ref.getChannelNum() != pip_ref.getChannelNum():
				self.session.pip.currentService = tmp_ref
			self.setCurrentSelection(tmp_ref)
		self.revertMode = None


class RadioInfoBar(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["RdsDecoder"] = RdsDecoder(self.session.nav)


class ChannelSelectionRadio(ChannelSelectionBase, ChannelSelectionEdit, ChannelSelectionEPG, InfoBarBase, SelectionEventInfo, InfoBarScreenSaver):
	ALLOW_SUSPEND = True

	def __init__(self, session, infobar):
		ChannelSelectionBase.__init__(self, session)
		ChannelSelectionEdit.__init__(self)
		ChannelSelectionEPG.__init__(self)
		InfoBarBase.__init__(self)
		SelectionEventInfo.__init__(self)
		InfoBarScreenSaver.__init__(self)
		self.infobar = infobar
		self.startServiceRef = None
		self.onLayoutFinish.append(self.onCreate)

		self.info = session.instantiateDialog(RadioInfoBar) # our simple infobar

		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"keyTV": self.cancel,
				"keyRadio": self.cancel,
				"cancel": self.cancel,
				"ok": self.channelSelected,
				"audio": self.audioSelection
			})

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStart: self.__evServiceStart,
				iPlayableService.evEnd: self.__evServiceEnd
			})

########## RDS Radiotext / Rass Support BEGIN
		self.infobar = infobar # reference to real infobar (the one and only)
		self["RdsDecoder"] = self.info["RdsDecoder"]
		self["RdsActions"] = HelpableActionMap(self, ["InfobarRdsActions"],
		{
			"startRassInteractive": (self.startRassInteractive, _("View Rass interactive..."))
		}, -1)
		self["RdsActions"].setEnabled(False)
		infobar.rds_display.onRassInteractivePossibilityChanged.append(self.RassInteractivePossibilityChanged)
		self.onClose.append(self.__onClose)
		self.onExecBegin.append(self.__onExecBegin)
		self.onExecEnd.append(self.__onExecEnd)

	def __onClose(self):
		lastservice = eServiceReference(config.tv.lastservice.value)
		self.session.nav.playService(lastservice)

	def startRassInteractive(self):
		self.info.hide()
		self.infobar.rass_interactive = self.session.openWithCallback(self.RassInteractiveClosed, RassInteractive)

	def RassInteractiveClosed(self):
		self.info.show()
		self.infobar.rass_interactive = None
		self.infobar.RassSlidePicChanged()

	def RassInteractivePossibilityChanged(self, state):
		self["RdsActions"].setEnabled(state)
########## RDS Radiotext / Rass Support END

	def __onExecBegin(self):
		self.info.show()

	def __onExecEnd(self):
		self.info.hide()

	def cancel(self):
		self.infobar.rds_display.onRassInteractivePossibilityChanged.remove(self.RassInteractivePossibilityChanged)
		self.info.hide()
		#set previous tv service
		self.close(None)

	def __evServiceStart(self):
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				self.servicelist.setPlayableIgnoreService(eServiceReference(refstr))

	def __evServiceEnd(self):
		self.servicelist.setPlayableIgnoreService(eServiceReference())

	def saveRoot(self):
		path = ''
		for i in self.servicePathRadio:
			path += i.toString()
			path += ';'
		if path and path != config.radio.lastroot.value:
			config.radio.lastroot.value = path
			config.radio.lastroot.save()

	def restoreRoot(self):
		tmp = [x for x in config.radio.lastroot.value.split(';') if x != '']
		current = [x.toString() for x in self.servicePath]
		if tmp != current or self.rootChanged:
			cnt = 0
			for i in tmp:
				self.servicePathRadio.append(eServiceReference(i))
				cnt += 1
			if cnt:
				path = self.servicePathRadio.pop()
				self.enterPath(path)
			else:
				self.showFavourites()
				self.saveRoot()
			self.rootChanged = False

	def preEnterPath(self, refstr):
		if self.servicePathRadio and self.servicePathRadio[0] != eServiceReference(refstr):
			pathstr = config.radio.lastroot.value
			if pathstr is not None and refstr in pathstr:
				self.restoreRoot()
				lastservice = eServiceReference(config.radio.lastservice.value)
				if lastservice.valid():
					self.setCurrentSelection(lastservice)
				return True
		return False

	def onCreate(self):
		self.setRadioMode()
		self.restoreRoot()
		lastservice = eServiceReference(config.radio.lastservice.value)
		if lastservice.valid():
			self.servicelist.setCurrent(lastservice)
			if config.usage.e1like_radio_mode_last_play.value:
				self.session.nav.playService(lastservice)
			else:
				self.session.nav.stopService()
		else:
			self.session.nav.stopService()
		self.info.show()

	def channelSelected(self, doClose=False): # just return selected service
		ref = self.getCurrentSelection()
		if self.movemode:
			self.toggleMoveMarked()
		elif (ref.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
			self.enterPath(ref)
			self.gotoCurrentServiceOrProvider(ref)
		elif self.bouquet_mark_edit != OFF:
			if not (self.bouquet_mark_edit == EDIT_ALTERNATIVES and ref.flags & eServiceReference.isGroup):
				self.doMark()
		elif not (ref.flags & eServiceReference.isMarker): # no marker
			cur_root = self.getRoot()
			if not cur_root or not (cur_root.flags & eServiceReference.isGroup):
				playingref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
				if playingref is None or playingref != ref:
					self.session.nav.playService(ref)
					config.radio.lastservice.value = ref.toString()
					config.radio.lastservice.save()
				self.saveRoot()

	def zapBack(self):
		self.channelSelected()

	def audioSelection(self):
		Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.instance.audioSelection()


class SimpleChannelSelection(ChannelSelectionBase, SelectionEventInfo):
	def __init__(self, session, title, currentBouquet=False, returnBouquet=False, setService=None, setBouquet=None):
		ChannelSelectionBase.__init__(self, session)
		SelectionEventInfo.__init__(self)
		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"cancel": self.close,
				"ok": self.channelSelected,
				"keyRadio": self.setModeRadio,
				"keyTV": self.setModeTv,
			})
		self.bouquet_mark_edit = OFF
		if isinstance(title, str):
			self.maintitle = title
		self.currentBouquet = currentBouquet
		self.returnBouquet = returnBouquet
		self.setService = setService
		self.setBouquet = setBouquet
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setModeTv()
		if self.currentBouquet or self.setBouquet:
			ref = self.setBouquet or Screens.InfoBar.InfoBar.instance.servicelist.getRoot()
			if ref:
				self.enterPath(ref)
				self.gotoCurrentServiceOrProvider(ref)
		if self.setService:
			self.setCurrentSelection(self.setService)

	def saveRoot(self):
		pass

	def keyRecord(self):
		return 0

	def channelSelected(self): # just return selected service
		ref = self.getCurrentSelection()
		if (ref.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
			self.enterPath(ref)
			self.gotoCurrentServiceOrProvider(ref)
		elif not (ref.flags & eServiceReference.isMarker):
			ref = self.getCurrentSelection()
			if self.returnBouquet and len(self.servicePath):
				self.close(ref, self.servicePath[-1])
			else:
				self.close(ref)

	def setModeTv(self):
		self.setTvMode()
		self.showFavourites()

	def setModeRadio(self):
		self.setRadioMode()
		self.showFavourites()

	def getMutableList(self, root=None):
		return None

class HistoryZapSelector(Screen):
	def __init__(self, session, items=None, sel_item=0, mark_item=0, invert_items=False, redirect_buttons=False, wrap_around=True):
		if not items: items = []
		Screen.__init__(self, session)
		self.redirectButton = redirect_buttons
		self.invertItems = invert_items
		if self.invertItems:
			self.currentPos = len(items) - sel_item - 1
		else:
			self.currentPos = sel_item
		self["actions"] = ActionMap(["OkCancelActions", "InfobarCueSheetActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick,
				"jumpPreviousMark": self.prev,
				"jumpNextMark": self.next,
				"toggleMark": self.okbuttonClick,
			})
		self.setTitle(_("History zap..."))
		self.list = []
		cnt = 0
		serviceHandler = eServiceCenter.getInstance()
		for x in items:

			info = serviceHandler.info(x[-1])
			if info:
				serviceName = info.getName(x[-1])
				if serviceName is None:
					serviceName = ""
				eventName = ""
				descriptionName = ""
				durationTime = ""
				# if config.plugins.SetupZapSelector.event.value != "0":
				event = info.getEvent(x[-1])
				if event:
					eventName = event.getEventName()
					if eventName is None:
						eventName = ""
					else:
						eventName = eventName.replace('(18+)', '').replace('18+', '').replace('(16+)', '').replace('16+', '').replace('(12+)', '').replace('12+', '').replace('(7+)', '').replace('7+', '').replace('(6+)', '').replace('6+', '').replace('(0+)', '').replace('0+', '')
					# if config.plugins.SetupZapSelector.event.value == "2":
					descriptionName = event.getShortDescription()
					if descriptionName is None or descriptionName == "":
						descriptionName = event.getExtendedDescription()
						if descriptionName is None:
							descriptionName = ""
					# if config.plugins.SetupZapSelector.duration.value:
					begin = event.getBeginTime()
					if begin is not None:
						end = begin + event.getDuration()
						remaining = (end - int(time())) / 60
						prefix = ""
						if remaining > 0:
							prefix = "+"
						local_begin = localtime(begin)
						local_end = localtime(end)
						durationTime = _("%02d.%02d - %02d.%02d (%s%d min)") % (local_begin[3],local_begin[4],local_end[3],local_end[4],prefix, remaining)

			png = ""
			picon = getPiconName(str(ServiceReference(x[1])))
			if picon != "":
				png = loadPNG(picon)
			if self.invertItems:
				self.list.insert(0, (x[1], cnt == mark_item and "»" or "", x[0], eventName, descriptionName, durationTime, png))
			else:
				self.list.append((x[1], cnt == mark_item and "»" or "", x[0], eventName, descriptionName, durationTime, png))
			cnt += 1
		self["menu"] = List(self.list, enableWrapAround=wrap_around)
		self.onShown.append(self.__onShown)

	def __onShown(self):
		self["menu"].index = self.currentPos

	def prev(self):
		if self.redirectButton:
			self.down()
		else:
			self.up()

	def next(self):
		if self.redirectButton:
			self.up()
		else:
			self.down()

	def up(self):
		self["menu"].selectPrevious()

	def down(self):
		self["menu"].selectNext()

	def getCurrent(self):
		cur = self["menu"].current
		return cur and cur[0]

	def okbuttonClick(self):
		self.close(self.getCurrent())

	def cancelClick(self):
		self.close(None)
