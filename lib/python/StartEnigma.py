# -*- coding: utf-8 -*-
import sys
import os
from time import time

# Don't remove this line. It may seem to do nothing, but if removed,
# it will break output redirection for crash logs.
import Tools.RedirectOutput
import enigma
import eConsoleImpl
import eBaseImpl
enigma.eTimer = eBaseImpl.eTimer
enigma.eSocketNotifier = eBaseImpl.eSocketNotifier
enigma.eConsoleAppContainer = eConsoleImpl.eConsoleAppContainer
from Components.config import config, configfile, ConfigText, ConfigYesNo, ConfigInteger, ConfigSelection, ConfigSubsection, NoSave
from Components.SystemInfo import BoxInfo

from traceback import print_exc

MODEL = BoxInfo.getItem("model")

# These entries should be moved back to UsageConfig.py when it is safe to bring UsageConfig init to this location in StartEnigma.py.
#
config.crash = ConfigSubsection()
config.crash.debugOpkg = ConfigYesNo(default=False)
config.crash.debugScreens = ConfigYesNo(default=False)
config.crash.debugMultiBoot = ConfigYesNo(default=False)
config.crash.debugActionMaps = ConfigYesNo(default=False)
config.crash.debugKeyboards = ConfigYesNo(default=False)
config.crash.debugRemoteControls = ConfigYesNo(default=False)
config.crash.debugDVBScan = ConfigYesNo(default=False)
config.crash.debugDVBTime = ConfigYesNo(default=False)
config.crash.debugDVB = ConfigYesNo(default=False)
config.crash.debugInternational = ConfigYesNo(default=False)
config.crash.debugTeletext = ConfigYesNo(default=False)
config.crash.debugStorage = ConfigYesNo(default=False)

# config.plugins needs to be defined before InputDevice < HelpMenu < MessageBox < InfoBar.
config.plugins = ConfigSubsection()
config.plugins.remotecontroltype = ConfigSubsection()
config.plugins.remotecontroltype.rctype = ConfigInteger(default=0)

# New Plugin Style (Do not move it to other file)
config.misc.plugin_style = ConfigSelection(default="list", choices=[
	("list", _("View as list")),
	("grid1", _("View as grid 1")),
	("grid2", _("View as grid 2")),
	("grid3", _("View as grid 3")),
	("grid4", _("View as grid 4")),
	("grid5", _("View as grid 5")),
	("grid6", _("View as grid 6"))])

# New VirtualkeyBoard Style
config.misc.virtualkeyBoardstyle = ConfigSelection(default="new", choices=[
	("new", _("New style")),
	("e2", _("Enigma2 default"))])

enigma.eProfileWrite("SimpleSummary")
from Screens import InfoBar
from Screens.SimpleSummary import SimpleSummary

from sys import stdout

enigma.eProfileWrite("Bouquets")
config.misc.load_unlinked_userbouquets = ConfigSelection(default="1", choices=[("0", _("Off")), ("1", _("Top")), ("2", _("Bottom"))])
if config.misc.load_unlinked_userbouquets.value.lower() in ("true", "false"):
	config.misc.load_unlinked_userbouquets.value = "1" if config.misc.load_unlinked_userbouquets.value.lower() == "true" else "0"


def localeNotifier(configElement):
	international.activateLocale(configElement.value)


enigma.eProfileWrite("International")
from Components.International import international

config.misc.locale = ConfigText(default="en_US")
config.misc.locale.addNotifier(localeNotifier)
config.misc.language = ConfigText(default=international.getLanguage("en_US"))
config.misc.country = ConfigText(default=international.getCountry("en_US"))


def setLoadUnlinkedUserbouquets(configElement):
	enigma.eDVBDB.getInstance().setLoadUnlinkedUserbouquets(int(configElement.value))


config.misc.load_unlinked_userbouquets.addNotifier(setLoadUnlinkedUserbouquets)
enigma.eDVBDB.getInstance().reloadBouquets()

enigma.eProfileWrite("ParentalControl")
import Components.ParentalControl
Components.ParentalControl.InitParentalControl()

enigma.eProfileWrite("LOAD:Navigation")
from Navigation import Navigation

enigma.eProfileWrite("LOAD:skin")
from skin import readSkin

enigma.eProfileWrite("LOAD:Tools")
from Tools.Directories import InitFallbackFiles, resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
InitFallbackFiles()

enigma.eProfileWrite("config.misc")
config.misc.radiopic = ConfigText(default=resolveFilename(SCOPE_CURRENT_SKIN, "radio.mvi"))
config.misc.blackradiopic = ConfigText(default=resolveFilename(SCOPE_CURRENT_SKIN, "black.mvi"))
config.misc.startCounter = ConfigInteger(default=0) # number of e2 starts...
config.misc.standbyCounter = NoSave(ConfigInteger(default=0)) # number of standby
config.misc.DeepStandby = NoSave(ConfigYesNo(default=False)) # detect deepstandby
config.misc.RestartUI = ConfigYesNo(default=False) # detect user interface restart
config.misc.prev_wakeup_time = ConfigInteger(default=0)
#config.misc.prev_wakeup_time_type is only valid when wakeup_time is not 0
config.misc.prev_wakeup_time_type = ConfigInteger(default=0)
# 0 = RecordTimer, 1 = ZapTimer, 2 = Plugins, 3 = WakeupTimer
config.misc.epgcache_filename = ConfigText(default="/media/hdd/epg.dat", fixed_size=False)
config.misc.SyncTimeUsing = ConfigSelection(default="0", choices=[
	("0", _("Transponder Time")),
	("1", _("NTP"))
])
config.misc.NTPserver = ConfigText(default="pool.ntp.org", fixed_size=False)

def setEPGCachePath(configElement):
	if os.path.isdir(configElement.value) or os.path.islink(configElement.value):
		configElement.value = os.path.join(configElement.value, "epg.dat")
	enigma.eEPGCache.getInstance().setCacheFile(configElement.value)

#demo code for use of standby enter leave callbacks
#def leaveStandby():
#	print "!!!!!!!!!!!!!!!!!leave standby"

#def standbyCountChanged(configElement):
#	print "!!!!!!!!!!!!!!!!!enter standby num", configElement.value
#	from Screens.Standby import inStandby
#	inStandby.onClose.append(leaveStandby)

#config.misc.standbyCounter.addNotifier(standbyCountChanged, initial_call = False)
####################################################

enigma.eProfileWrite("Twisted")
try:
	import twisted.python.runtime

	import e2reactor
	e2reactor.install()

	from twisted.internet import reactor

	def runReactor():
		reactor.run(installSignalHandlers=False)
except ImportError:
	print("[StartEnigma] Twisted not available")

	def runReactor():
		enigma.runMainloop()

enigma.eProfileWrite("LOAD:Plugin")

from twisted.python import log
config.misc.enabletwistedlog = ConfigYesNo(default=False)
if config.misc.enabletwistedlog.value == True:
	log.startLogging(open('/tmp/twisted.log', 'w'))
else:
	log.startLogging(sys.stdout)

# initialize autorun plugins and plugin menu entries
from Components.PluginComponent import plugins

enigma.eProfileWrite("LOAD:Wizard")
config.misc.rcused = ConfigInteger(default=1)
from Screens.Wizard import wizardManager
from Screens.StartWizard import *
#import Screens.Rc
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor

enigma.eProfileWrite("misc")
had = dict()


def dump(dir, p=""):
	if isinstance(dir, dict):
		for (entry, val) in dir.items():
			dump(val, p + "(dict)/" + entry)
	if hasattr(dir, "__dict__"):
		for name, value in dir.__dict__.items():
			if str(value) not in had:
				had[str(value)] = 1
				dump(value, p + "/" + str(name))
			else:
				print(p + "/" + str(name) + ":" + str(dir.__class__) + "(cycle)")
	else:
		print(p + ":" + str(dir))

# + ":" + str(dir.__class__)

# display


enigma.eProfileWrite("LOAD:ScreenGlobals")
from Screens.Globals import Globals
from Screens.SessionGlobals import SessionGlobals
from Screens.Screen import Screen

enigma.eProfileWrite("Screen")
Screen.globalScreen = Globals()

# Session.open:
# * push current active dialog ('current_dialog') onto stack
# * call execEnd for this dialog
#   * clear in_exec flag
#   * hide screen
# * instantiate new dialog into 'current_dialog'
#   * create screens, components
#   * read, apply skin
#   * create GUI for screen
# * call execBegin for new dialog
#   * set in_exec
#   * show gui screen
#   * call components' / screen's onExecBegin
# ... screen is active, until it calls 'close'...
# Session.close:
# * assert in_exec
# * save return value
# * start deferred close handler ('onClose')
# * execEnd
#   * clear in_exec
#   * hide screen
# .. a moment later:
# Session.doClose:
# * destroy screen


class Session:
	def __init__(self, desktop=None, summary_desktop=None, navigation=None):
		self.desktop = desktop
		self.summary_desktop = summary_desktop
		self.nav = navigation
		self.delay_timer = enigma.eTimer()
		self.delay_timer.callback.append(self.processDelay)

		self.current_dialog = None

		self.dialog_stack = []
		self.summary_stack = []
		self.onShutdown = []
		self.summary = None

		self.in_exec = False

		self.screen = SessionGlobals(self)
		from Components.FrontPanelLed import frontPanelLed
		frontPanelLed.init(self)
		self.allDialogs = []

		for p in plugins.getPlugins(PluginDescriptor.WHERE_SESSIONSTART):
			try:
				p(reason=0, session=self)
			except:
				print("[StartEnigma] Plugin raised exception at WHERE_SESSIONSTART")
				import traceback
				traceback.print_exc()

	def processDelay(self):
		callback = self.current_dialog.callback

		retval = self.current_dialog.returnValue

		if self.current_dialog.isTmp:
			self.current_dialog.doClose()
#			dump(self.current_dialog)
			del self.current_dialog
		else:
			del self.current_dialog.callback

		self.popCurrent()
		if callback is not None:
			callback(*retval)

	def execBegin(self, first=True, do_show=True):
		assert not self.in_exec
		self.in_exec = True
		c = self.current_dialog

		# when this is an execbegin after a execend of a "higher" dialog,
		# popSummary already did the right thing.
		if first:
			self.instantiateSummaryDialog(c)

		c.saveKeyboardMode()
		c.execBegin()

		# when execBegin opened a new dialog, don't bother showing the old one.
		if c == self.current_dialog and do_show:
			c.show()

	def execEnd(self, last=True):
		assert self.in_exec
		self.in_exec = False

		self.current_dialog.execEnd()
		self.current_dialog.restoreKeyboardMode()
		self.current_dialog.hide()

		if last and self.summary:
			self.current_dialog.removeSummary(self.summary)
			self.popSummary()

	def instantiateDialog(self, screen, *arguments, **kwargs):
		return self.doInstantiateDialog(screen, arguments, kwargs, self.desktop)

	def deleteDialog(self, screen):
		if screen in self.allDialogs:
			self.allDialogs.remove(screen)
		screen.hide()
		screen.doClose()

	def deleteDialogWithCallback(self, callback, screen, *retVal):
		self.deleteDialog(screen)
		if callback is not None:
			callback(*retVal)

	def instantiateSummaryDialog(self, screen, **kwargs):
		if self.summary_desktop is not None:
			self.pushSummary()
			summary = screen.createSummary() or SimpleSummary
			arguments = (screen,)
			self.summary = self.doInstantiateDialog(summary, arguments, kwargs, self.summary_desktop)
			self.summary.show()
			screen.addSummary(self.summary)

	def doInstantiateDialog(self, screen, arguments, kwargs, desktop):
		# create dialog
		dlg = screen(self, *arguments, **kwargs)
		if dlg is None:
			return
		# read skin data
		readSkin(dlg, None, dlg.skinName, desktop)
		# create GUI view of this dialog
		dlg.setDesktop(desktop)
		dlg.applySkin()
		self.allDialogs.append(dlg)
		return dlg

	def pushCurrent(self):
		if self.current_dialog is not None:
			self.dialog_stack.append((self.current_dialog, self.current_dialog.shown))
			self.execEnd(last=False)

	def popCurrent(self):
		if self.dialog_stack:
			(self.current_dialog, do_show) = self.dialog_stack.pop()
			self.execBegin(first=False, do_show=do_show)
		else:
			self.current_dialog = None

	def execDialog(self, dialog):
		self.pushCurrent()
		self.current_dialog = dialog
		self.current_dialog.isTmp = False
		self.current_dialog.callback = None # would cause re-entrancy problems.
		self.execBegin()

	def openWithCallback(self, callback, screen, *arguments, **kwargs):
		dlg = self.open(screen, *arguments, **kwargs)
		if dlg != 'config.crash.bsodpython.value=True':
			dlg.callback = callback
			return dlg

	def open(self, screen, *arguments, **kwargs):
		if self.dialog_stack and not self.in_exec:
			raise RuntimeError("modal open are allowed only from a screen which is modal!")
			# ...unless it's the very first screen.

		self.pushCurrent()
		if config.crash.bsodpython.value:
			try:
				dlg = self.current_dialog = self.instantiateDialog(screen, *arguments, **kwargs)
			except:
				self.popCurrent()
				raise
				return 'config.crash.bsodpython.value=True'
		else:
			dlg = self.current_dialog = self.instantiateDialog(screen, *arguments, **kwargs)
		dlg.isTmp = True
		dlg.callback = None
		self.execBegin()
		return dlg

	def close(self, screen, *retval):
		if not self.in_exec:
			print("[StartEnigma] Close after exec!")
			return

		# be sure that the close is for the right dialog!
		# if it's not, you probably closed after another dialog
		# was opened. this can happen if you open a dialog
		# onExecBegin, and forget to do this only once.
		# after close of the top dialog, the underlying will
		# gain focus again (for a short time), thus triggering
		# the onExec, which opens the dialog again, closing the loop.
		assert screen == self.current_dialog

		self.current_dialog.returnValue = retval
		self.delay_timer.start(0, 1)
		self.execEnd()

	def pushSummary(self):
		if self.summary:
			self.summary.hide()
			self.summary_stack.append(self.summary)
			self.summary = None

	def popSummary(self):
		if self.summary:
			self.summary.doClose()
		self.summary = self.summary_stack and self.summary_stack.pop()
		if self.summary:
			self.summary.show()

	def doShutdown(self):
		for function in self.onShutdown:
			if callable(function):
				function()

	def reloadDialogs(self):
		for dlg in self.allDialogs:
			if hasattr(dlg, "desktop"):
				oldDesktop = dlg.desktop
				readSkin(dlg, None, dlg.skinName, oldDesktop)
				dlg.applySkin()


enigma.eProfileWrite("Standby,PowerKey")
import Screens.Standby
from Screens.Menu import MainMenu, mdom
from GlobalActions import globalActionMap


class PowerKey:
	""" PowerKey stuff - handles the powerkey press and powerkey release actions"""

	def __init__(self, session):
		self.session = session
		globalActionMap.actions["power_down"] = lambda *args: None
		globalActionMap.actions["power_up"] = self.powerup
		globalActionMap.actions["power_long"] = self.powerlong
		globalActionMap.actions["deepstandby"] = self.shutdown # frontpanel long power button press
		globalActionMap.actions["discrete_off"] = self.standby

	def shutdown(self):
		print("[StartEnigma] PowerOff - Now!")
		if not Screens.Standby.inTryQuitMainloop and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND:
			self.session.open(Screens.Standby.TryQuitMainloop, 1)
		else:
			return 0

	def powerup(self):
		if not Screens.Standby.inStandby and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND and self.session.in_exec:
			self.doAction(config.misc.hotkey.power.value)
		else:
			return 0

	def powerlong(self):
		if not Screens.Standby.inStandby and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND and self.session.in_exec:
			self.doAction(config.misc.hotkey.power_long.value)
		else:
			return 0

	def doAction(self, selected):
		if selected:
			selected = selected.split("/")
			if selected[0] == "Module":
				try:
					exec("from " + selected[1] + " import *")
					exec("self.session.open(" + ",".join(selected[2:]) + ")")
				except:
					print("[StartEnigma] Error during executing module %s, screen %s" % (selected[1], selected[2]))
			elif selected[0] == "Menu":
				from Screens.Menu import MainMenu, mdom
				root = mdom.getroot()
				for x in root.findall("menu"):
					if x.get("key") == "shutdown":
						self.session.infobar = self
						menu_screen = self.session.openWithCallback(self.MenuClosed, MainMenu, x)
						menu_screen.setTitle(_("Standby / restart"))
						break

	def standby(self):
		if not Screens.Standby.inStandby and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND and self.session.in_exec:
			self.session.open(Screens.Standby.Standby)
		else:
			return 0


enigma.eProfileWrite("Scart")
from Screens.Scart import Scart


class AutoScartControl:
	def __init__(self, session):
		self.hasScart = BoxInfo.getItem("HasScart")
		if self.hasScart:
			self.force = False
			self.current_vcr_sb = enigma.eAVControl.getInstance().getVCRSlowBlanking()
			if self.current_vcr_sb and config.av.vcrswitch.value:
				self.scartDialog = session.instantiateDialog(Scart, True)
			else:
				self.scartDialog = session.instantiateDialog(Scart, False)
			config.av.vcrswitch.addNotifier(self.recheckVCRSb)
			enigma.eAVControl.getInstance().vcr_sb_notifier.get().append(self.VCRSbChanged)

	def recheckVCRSb(self, configElement):
		self.VCRSbChanged(self.current_vcr_sb)

	def VCRSbChanged(self, value):
		if self.hasScart:
			# print("[StartEnigma] VCR SB changed to '%s'." % value)
			self.current_vcr_sb = value
			if config.av.vcrswitch.value or value > 2:
				if value:
					self.scartDialog.showMessageBox()
				else:
					self.scartDialog.switchToTV()


enigma.eProfileWrite("Load:CI")
from Screens.Ci import CiHandler

enigma.eProfileWrite("Load:VolumeControl")
from Components.VolumeControl import VolumeControl

enigma.eProfileWrite("Load:Processing")
from Screens.Processing import Processing

enigma.eProfileWrite("Load:StackTracePrinter")
from Components.StackTrace import StackTracePrinter
StackTracePrinterInst = StackTracePrinter()


def runScreenTest():
	config.misc.startCounter.value += 1
	config.misc.startCounter.save()

	enigma.eProfileWrite("readPluginList")
	enigma.pauseInit()
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
	enigma.resumeInit()

	enigma.eProfileWrite("Init:Session")
	nav = Navigation()
	session = Session(desktop=enigma.getDesktop(0), summary_desktop=enigma.getDesktop(1), navigation=nav)

	CiHandler.setSession(session)
	powerOffTimer.setSession(session)

	screensToRun = [p.fnc for p in plugins.getPlugins(PluginDescriptor.WHERE_WIZARD)]

	enigma.eProfileWrite("wizards")
	screensToRun += wizardManager.getWizards()

	screensToRun.append((100, InfoBar.InfoBar))

	screensToRun.sort(key=lambda x: x[0])

	enigma.ePythonConfigQuery.setQueryFunc(configfile.getResolvedKey)

	def runNextScreen(session, screensToRun, *result):
		if result:
			enigma.quitMainloop(*result)
			return

		screen = screensToRun[0][1]
		args = screensToRun[0][2:]

		if screensToRun:
			session.openWithCallback(boundFunction(runNextScreen, session, screensToRun[1:]), screen, *args)
		else:
			session.open(screen, *args)

	config.misc.epgcache_filename.addNotifier(setEPGCachePath)

	runNextScreen(session, screensToRun)

	enigma.eProfileWrite("Init:VolumeControl")
	vol = VolumeControl(session)
	enigma.eProfileWrite("InitProcessing")
	processing = Processing(session)
	enigma.eProfileWrite("Init:PowerKey")
	power = PowerKey(session)

	from Screens.SwapManager import SwapAutostart
	SwapAutostart()

	# we need session.scart to access it from within menu.xml
	session.scart = AutoScartControl(session)

	enigma.eProfileWrite("Init:Trashcan")
	import Tools.Trashcan
	Tools.Trashcan.init(session)

	enigma.eProfileWrite("RunReactor")
	enigma.eProfileDone()
	runReactor()
	if MODEL in ("dreamone", "dreamtwo"):
		from Components.FrontPanelLed import FrontPanelLed
		session.shutdown = True
		FrontPanelLed.shutdown()
		print("[StartEnigma] Normal shutdown.")

	from time import time, strftime, localtime
	from Tools.StbHardware import setFPWakeuptime, setRTCtime
	from Screens.SleepTimerEdit import isNextWakeupTime
	#get currentTime
	nowTime = time()
	wakeupList = sorted([
		x for x in ((session.nav.RecordTimer.getNextRecordingTime(), 0),
					(session.nav.RecordTimer.getNextZapTime(isWakeup=True), 1),
					(plugins.getNextWakeupTime(), 2),
					(isNextWakeupTime(), 3))
		if x[0] != -1
	])
	if wakeupList:
		from time import strftime
		startTime = wakeupList[0]
		if (startTime[0] - nowTime) < 270: # no time to switch box back on
			wptime = nowTime + 30  # so switch back on in 30 seconds
		else:
			wptime = startTime[0] - 240
		if config.misc.SyncTimeUsing.value != "0":
			print("[StartEnigma] DVB time sync disabled, so set RTC now to current Linux time!  (%s)" % strftime("%Y/%m/%d %H:%M", localtime(nowTime)))
			setRTCtime(nowTime)
		setFPWakeuptime(wptime)
		config.misc.prev_wakeup_time.value = int(startTime[0])
		config.misc.prev_wakeup_time_type.value = startTime[1]
		config.misc.prev_wakeup_time_type.save()
	else:
		config.misc.prev_wakeup_time.value = 0
	config.misc.prev_wakeup_time.save()

	session.nav.stopService()
	enigma.eProfileWrite("nav shutdown")
	session.nav.shutdown()
	session.doShutdown()

	VolumeControl.instance.saveVolumeState()

	enigma.eProfileWrite("configfile.save")
	configfile.save()

	return 0


enigma.eProfileWrite("Skin")
from skin import InitSkins
InitSkins()

enigma.eProfileWrite("InputDevice")
import Components.InputDevice
Components.InputDevice.InitInputDevices()
import Components.InputHotplug

enigma.eProfileWrite("SetupDevices")
import Components.SetupDevices
Components.SetupDevices.InitSetupDevices()

enigma.eProfileWrite("AVSwitch")
import Components.AVSwitch
Components.AVSwitch.InitAVSwitch()

enigma.eProfileWrite("HdmiRecord")
import Components.HdmiRecord
Components.HdmiRecord.InitHdmiRecord()

enigma.eProfileWrite("RecordingConfig")
import Components.RecordingConfig
Components.RecordingConfig.InitRecordingConfig()

enigma.eProfileWrite("UsageConfig")
import Components.UsageConfig
Components.UsageConfig.InitUsageConfig()

enigma.eProfileWrite("Timezones")
import Components.Timezones
Components.Timezones.InitTimeZones()

enigma.eProfileWrite("Init:DebugLogCheck")
import Screens.LogManager
Screens.LogManager.AutoLogManager()

enigma.eProfileWrite("keymapparser")
import keymapparser
keymapparser.readKeymap(config.usage.keymap.value)
keymapparser.readKeymap(config.usage.keytrans.value)

enigma.eProfileWrite("Init:NTPSync")
from Components.NetworkTime import ntpSyncPoller
ntpSyncPoller.startTimer()

enigma.eProfileWrite("Network")
from Components.Network import InitNetwork
InitNetwork()

enigma.eProfileWrite("LCD")
import Components.Lcd
Components.Lcd.InitLcd()

enigma.eAVControl.getInstance().disableHDMIIn()

enigma.eProfileWrite("RFMod")
import Components.RFmod
Components.RFmod.InitRFmod()

enigma.eProfileWrite("Init:CI")
import Screens.Ci
Screens.Ci.InitCiConfig()

enigma.eProfileWrite("RcModel")
import Components.RcModel

enigma.eProfileWrite("EpgCacheSched")
import Components.EpgLoadSave
Components.EpgLoadSave.EpgCacheSaveCheck()
Components.EpgLoadSave.EpgCacheLoadCheck()

enigma.eProfileWrite("InitOSDCalibration")
from Screens.OSDCalibration import InitOSDCalibration
InitOSDCalibration()

enigma.eProfileWrite("Init:PowerOffTimer")
from Components.PowerOffTimer import powerOffTimer

#from enigma import dump_malloc_stats
#t = eTimer()
#t.callback.append(dump_malloc_stats)
#t.start(1000)

# first, setup a screen
try:
	runScreenTest()

	plugins.shutdown()

	Components.ParentalControl.parentalControl.save()
except:
	print('[StartEnigma] EXCEPTION IN PYTHON STARTUP CODE:')
	print('-' * 60)
	print_exc(file=stdout)
	enigma.quitMainloop(5)
	print('-' * 60)
