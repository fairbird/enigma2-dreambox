# -*- coding: utf-8 -*-
from Components.Harddisk import harddiskmanager
from Components.International import international
from Components.Console import Console
from Components.config import ConfigSubsection, ConfigDirectory, ConfigYesNo, config, ConfigSelection, ConfigText, ConfigNumber, ConfigSet, ConfigLocations, ConfigSelectionNumber, ConfigSelectionInteger, ConfigClock, ConfigSlider, ConfigEnableDisable, ConfigSubDict, ConfigDictionarySet, ConfigInteger, ConfigIP, ConfigPassword, ConfigSequence, NoSave, ConfigBoolean, configfile
from Tools.Directories import SCOPE_HDD, SCOPE_TIMESHIFT, defaultRecordingLocation, fileContains, resolveFilename, fileHas, fileReadXML, SCOPE_SKIN
from enigma import setTunerTypePriorityOrder, setPreferredTuner, setSpinnerOnOff, setEnableTtCachingOnOff, eActionMap, eEnv, eDVBDB, Misc_Options, eBackgroundFileEraser, eServiceEvent, eSubtitleSettings, eSettings, eDVBLocalTimeHandler, eEPGCache
from Components.About import GetIPsFromNetworkInterfaces
from Components.NimManager import nimmanager
from Components.Renderer.FrontpanelLed import ledPatterns, PATTERN_ON, PATTERN_OFF, PATTERN_BLINK
from Components.ServiceList import refreshServiceList
from Components.SystemInfo import BoxInfo
from skin import getcomponentTemplateNames, parameters, domScreens
from os import makedirs, unlink
from os.path import exists, isfile, join as pathjoin, normpath
import os, time, locale
from boxbranding import getDisplayType

displaytype = getDisplayType()

MODULE_NAME = __name__.split(".")[-1]

originalAudioTracks = "orj dos ory org esl qaa qaf und qae mis mul ORY ORJ Audio_ORJ oth"
visuallyImpairedCommentary = "NAR qad"


def InitUsageConfig():
	config.usage = ConfigSubsection()
	if isfile("/etc/crontab") and not fileContains("/etc/crontab", "registry.arm.bin"):
		if isfile("/home/root/.cache/gstreamer-1.0/registry.arm.bin"):
			Console().ePopen("sed -i '$a@reboot root rm -f /home/root/.cache/gstreamer-1.0/registry.arm.bin' /etc/crontab")
		elif isfile("/home/root/.cache/gstreamer-0.10/registry.arm.bin"):
			Console().ePopen("sed -i '$a@reboot root rm -f /home/root/.cache/gstreamer-0.10/registry.arm.bin' /etc/crontab")
		else:
			print("[UsageConfig] No registry.arm.bin?")

	showrotorpositionChoicesUpdate()
	config.usage.maxchannelnumlen = ConfigSelection(default="4", choices=[
		("3", _("3")),
		("4", _("4")),
		("5", _("5")),
		("6", _("6"))
	])

	def setNumberModeChange(configElement):
		eDVBDB.getInstance().setNumberingMode(configElement.value)
		config.usage.alternative_number_mode.value = config.usage.numberMode.value != 0
		refreshServiceList()

	config.usage.numberMode = ConfigSelection(default=0, choices=[
		(0, _("Unique numbering")),
		(1, _("Bouquets start at 1")),
		(2, _("LCN numbering"))
	])
	config.usage.numberMode.addNotifier(setNumberModeChange, initial_call=False)

	# Fallback old settigs will be removed later because this setting is probably used in plugins
	config.usage.alternative_number_mode = ConfigYesNo(default=config.usage.numberMode.value != 0)

	config.usage.hide_number_markers = ConfigYesNo(default=True)
	config.usage.hide_number_markers.addNotifier(refreshServiceList)

	config.usage.servicetype_icon_mode = ConfigSelection(default="0", choices=[
		("0", _("None")),
		("1", _("Left from service name")),
		("2", _("Right from service name"))
	])
	config.usage.servicetype_icon_mode.addNotifier(refreshServiceList)
	config.usage.crypto_icon_mode = ConfigSelection(default="0", choices=[
		("0", _("None")),
		("1", _("Left from service name")),
		("2", _("Right from service name"))
	])
	config.usage.crypto_icon_mode.addNotifier(refreshServiceList)
	config.usage.record_indicator_mode = ConfigSelection(default="3", choices=[
		("0", _("None")),
		("1", _("Left from service name")),
		("2", _("Right from service name")),
		("3", _("Red colored"))
	])
	config.usage.record_indicator_mode.addNotifier(refreshServiceList)

	config.network = ConfigSubsection()
	choices = [
		("dhcp-router", _("Router / Gateway")),
		("custom", _("Static IP / Custom"))
	]
	fileDom = fileReadXML(resolveFilename(SCOPE_SKIN, "dnsservers.xml"), source=MODULE_NAME)
	for dns in fileDom.findall("dnsserver"):
		if dns.get("key", ""):
			choices.append((dns.get("key"), _(dns.get("title"))))

	config.usage.dns = ConfigSelection(default="dhcp-router", choices=choices)
	config.usage.dnsMode = ConfigSelection(default=0, choices=[
		(0, _("Prefer IPv4")),
		(1, _("Prefer IPv6")),
		(2, _("IPv4 only")),
		(3, _("IPv6 only"))
	])
	config.usage.dnsSuffix = ConfigText(default="")
	config.usage.dnsRotate = ConfigYesNo(default=False)
	config.usage.subnetwork = ConfigYesNo(default=True)
	config.usage.subnetwork_cable = ConfigYesNo(default=True)
	config.usage.subnetwork_terrestrial = ConfigYesNo(default=True)
	config.usage.showdish = ConfigYesNo(default=True)
	config.usage.multibouquet = ConfigYesNo(default=True)

	# Just merge note, config.usage.servicelist_column was already there.
	config.usage.servicelist_column = ConfigSelection(default="-1", choices=[("-1", _("Disable"))
	] + [(str(x), ngettext("%d Pixel wide", "%d Pixels wide", x) % x) for x in range(100, 1325, 25)])
	config.usage.servicelist_column.addNotifier(refreshServiceList)
	# Two lines options.
	config.usage.servicelist_twolines = ConfigYesNo(default=False)
	config.usage.servicelist_twolines.addNotifier(refreshServiceList)
	config.usage.serviceitems_per_page_twolines = ConfigSelectionNumber(default=12, stepwidth=1, min=4, max=20, wraparound=True)
	config.usage.servicelist_servicenumber_valign = ConfigSelection(default="0", choices=[
		("0", _("Centered")),
		("1", _("Upper line"))
	])
	config.usage.servicelist_servicenumber_valign.addNotifier(refreshServiceList)
	config.usage.servicelist_eventprogress_valign = ConfigSelection(default="0", choices=[
		("0", _("Centered")),
		("1", _("Upper line"))
	])
	config.usage.servicelist_eventprogress_valign.addNotifier(refreshServiceList)
	config.usage.servicelist_eventprogress_view_mode = ConfigSelection(default="0_barright", choices=[
		# Single.
		("0_no", _("No")),
		("0_barleft", _("Progress bar left")),
		("0_barright", _("Progress bar right")),
		("0_percleft", _("Percentage left")),
		("0_percright", _("Percentage right")),
		("0_minsleft", _("Remaining minutes left")),
		("0_minsright", _("Remaining minutes right")),
		# Bar value.
		("1_barpercleft", _("Progress bar/Percentage left")),
		("1_barpercright", _("Progress bar/Percentage right")),
		("1_barminsleft", _("Progress bar/Remaining minutes left")),
		("1_barminsright", _("Progress bar/Remaining minutes right")),
		# Value bar.
		("2_percbarleft", _("Percentage/Progress bar left")),
		("2_percbarright", _("Percentage/Progress bar right")),
		("2_minsbarleft", _("Remaining minutes/Progress bar left")),
		("2_minsbarright", _("Remaining minutes/Progress bar right"))
	])
	config.usage.servicelist_eventprogress_view_mode.addNotifier(refreshServiceList)
	#

	config.usage.service_icon_enable = ConfigYesNo(default=False)
	config.usage.service_icon_enable.addNotifier(refreshServiceList)
	config.usage.servicelist_picon_downsize = ConfigSelectionNumber(default=-2, stepwidth=1, min=-10, max=0, wraparound=True)
	config.usage.servicelist_picon_ratio = ConfigSelection(default="167", choices=[
		("167", _("XPicon, ZZZPicon")),
		("235", _("ZZPicon")),
		("250", _("ZPicon"))
	])
	config.usage.show_picon_bkgrn = ConfigSelection(default="transparent", choices=[
		("none", _("Disabled")),
		("transparent", _("Transparent")),
		("blue", _("Blue")),
		("red", _("Red")),
		("black", _("Black")),
		("white", _("White")),
		("lightgrey", _("Light Grey")),
		("grey", _("Grey"))
	])
	config.usage.servicelist_cursor_behavior = ConfigSelection(default="keep", choices=[
		("standard", _("Standard")),
		("keep", _("Keep service")),
		("reverseB", _("Reverse bouquet buttons")),
		("keep reverseB", _("Keep service") + " + " + _("Reverse bouquet buttons"))])

	choicelist = [("by skin", _("As defined by the skin"))]
	for i in range(5, 41):
		choicelist.append((str(i)))
	config.usage.servicelist_number_of_services = ConfigSelection(default="by skin", choices=choicelist)
	config.usage.servicelist_number_of_services.addNotifier(refreshServiceList)
	config.usage.multiepg_ask_bouquet = ConfigYesNo(default=False)

	# New ServiceList
	config.channelSelection = ConfigSubsection()
	config.channelSelection.showNumber = ConfigYesNo(default=True)
	config.channelSelection.showPicon = ConfigYesNo(default=False)
	config.channelSelection.showServiceTypeIcon = ConfigYesNo(default=False)
	config.channelSelection.showCryptoIcon = ConfigYesNo(default=False)
	config.channelSelection.recordIndicatorMode = ConfigSelection(default=2, choices=[
		(0, _("None")),
		(1, _("Record Icon")),
		(2, _("Colored Text"))
	])
	config.channelSelection.piconRatio = ConfigSelection(default=167, choices=[
		(167, _("XPicon, ZZZPicon")),
		(235, _("ZZPicon")),
		(250, _("ZPicon"))
	])

	config.channelSelection.showTimers = ConfigYesNo(default=False)

	screenChoiceList = [("", _("Legacy mode"))]
	widgetChoiceList = []
	styles = getcomponentTemplateNames("serviceList")
	default = ""
	if styles:
		for screen in domScreens:
			element, path = domScreens.get(screen, (None, None))
			if element.get("base") == "ChannelSelection":
				label = element.get("label", screen)
				screenChoiceList.append((screen, label))

		default = styles[0]
		for style in styles:
			widgetChoiceList.append((style, style))

	config.channelSelection.screenStyle = ConfigSelection(default="", choices=screenChoiceList)
	config.channelSelection.widgetStyle = ConfigSelection(default=default, choices=widgetChoiceList)

	# ########  Workaround for VTI Skins   ##############
	config.usage.picon_dir = ConfigDirectory(default="/usr/share/enigma2/picon")
	config.usage.movielist_show_picon = ConfigYesNo(default=False)
	config.usage.use_extended_pig = ConfigYesNo(default=False)
	config.usage.use_extended_pig_channelselection = ConfigYesNo(default=False)
	config.usage.servicelist_preview_mode = ConfigYesNo(default=False)
	config.usage.numberzap_show_picon = ConfigYesNo(default=False)
	config.usage.numberzap_show_servicename = ConfigYesNo(default=False)
	# ####################################################

	config.usage.quickzap_bouquet_change = ConfigYesNo(default=False)
	config.usage.e1like_radio_mode = ConfigYesNo(default=True)
	config.usage.e1like_radio_mode_last_play = ConfigYesNo(default=True)
	choicelist = [("0", _("No timeout"))]
	for i in range(1, 12):
		choicelist.append((str(i), ngettext("%d second", "%d seconds", i) % i))
	config.usage.infobar_timeout = ConfigSelection(default="5", choices=choicelist)
	config.usage.show_infobar_do_dimming = ConfigYesNo(default = True)
	config.usage.show_infobar_dimming_speed = ConfigSelectionNumber(min = 1, max = 40, stepwidth = 1, default = 40, wraparound = True)
	config.usage.show_infobar_on_zap = ConfigYesNo(default=True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default=True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default=False)
	config.usage.show_second_infobar = ConfigSelection(default="0", choices=[("no", _("None"))] + choicelist + [("EPG", _("EPG"))])
	config.usage.show_simple_second_infobar = ConfigYesNo(default=False)
	config.usage.show_infobar_adds = ConfigYesNo(default=False)
	config.usage.infobar_frontend_source = ConfigSelection(default="settings", choices=[("settings", _("Settings")), ("tuner", _("Tuner"))])
	config.usage.oldstyle_zap_controls = ConfigYesNo(default=False)
	config.usage.oldstyle_channel_select_controls = ConfigYesNo(default=False)
	config.usage.zap_with_ch_buttons = ConfigYesNo(default=False)
	config.usage.ok_is_channelselection = ConfigYesNo(default=False)
	config.usage.changebouquet_set_history = ConfigYesNo(default=False)
	config.usage.volume_instead_of_channelselection = ConfigYesNo(default=False)
	config.usage.channelselection_preview = ConfigYesNo(default=False)
	config.usage.show_spinner = ConfigYesNo(default=True)
	config.usage.enable_blinking = ConfigYesNo(default=False)
	config.usage.menu_sort_weight = ConfigDictionarySet(default={"mainmenu": {"submenu": {}}})
	config.usage.menu_sort_mode = ConfigSelection(default="default", choices=[("a_z", _("alphabetical")), ("default", _("Default")), ("user", _("user defined")), ("user_hidden", _("user defined hidden"))])
	config.usage.menu_show_numbers = ConfigSelection(default="no", choices=[("no", _("no")), ("menu&plugins", _("in menu and plugins")), ("menu", _("in menu only")), ("plugins", _("in plugins only"))])
	config.usage.showScreenPath = ConfigSelection(default="small", choices=[("off", _("Disabled")), ("small", _("Small")), ("large", _("Large"))])
	config.usage.enable_tt_caching = ConfigYesNo(default=True)
	config.usage.sort_settings = ConfigYesNo(default=False)
	choicelist = []
	for i in (10, 30):
		choicelist.append((str(i), ngettext("%d second", "%d seconds", i) % i))
	for i in (60, 120, 300, 600, 1200, 1800):
		m = i / 60
		choicelist.append((str(i), ngettext("%d minute", "%d minutes", m) % m))
	for i in (3600, 7200, 14400):
		h = i / 3600
		choicelist.append((str(i), ngettext("%d hour", "%d hours", h) % h))
	choiceList = [
		("0", _("No standby"))
	] + [(str(x), _("%d Seconds") % x) for x in (10, 30)] + [(str(x * 60), ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 2, 5, 10, 20, 30)] + [(str(x * 3600), ngettext("%d Hour", "%d Hours", x) % x) for x in (1, 2, 4)]
	config.usage.hdd_standby = ConfigSelection(default="300", choices=choiceList)
	config.usage.hdd_standby_in_standby = ConfigSelection(default="-1", choices=[("-1", _("Same as in active"))] + choiceList)
	config.usage.hdd_timer = ConfigYesNo(default=False)
	config.usage.output_12V = ConfigSelection(default="do not change", choices=[
		("do not change", _("Do not change")), ("off", _("Off")), ("on", _("On"))])

	config.usage.pip_zero_button = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")), ("swap", _("Swap PiP and main picture")),
		("swapstop", _("Move PiP to main picture")), ("stop", _("Stop PiP"))])
	config.usage.pip_hideOnExit = ConfigSelection(default="without popup", choices=[
		("no", _("no")), ("popup", _("With popup")), ("without popup", _("Without popup"))])
	choicelist = [("-1", _("Disabled")), ("0", _("No timeout"))]
	for i in [60, 300, 600, 900, 1800, 2700, 3600]:
		m = i / 60
		choicelist.append((str(i), ngettext("%d minute", "%d minutes", m) % m))
	config.usage.pip_last_service_timeout = ConfigSelection(default="0", choices=choicelist)

	if not exists(resolveFilename(SCOPE_HDD)):
		try:
			os.mkdir(resolveFilename(SCOPE_HDD), 0o755)
		except (IOError, OSError):
			pass
	defaultPath = resolveFilename(SCOPE_HDD)
	config.usage.default_path = ConfigSelection(default=defaultPath, choices=[(defaultPath, defaultPath)])
	config.usage.default_path.load()
	savedPath = config.usage.default_path.saved_value
	if savedPath:
		savedPath = pathjoin(savedPath, "")
		if savedPath and savedPath != defaultPath:
			config.usage.default_path.setChoices(default=defaultPath, choices=[(defaultPath, defaultPath), (savedPath, savedPath)])
			config.usage.default_path.value = savedPath
	config.usage.default_path.save()
	currentPath = config.usage.default_path.value
	print("[UsageConfig] Checking/Creating current movie directory '%s'." % currentPath)
	try:
		makedirs(currentPath, 0o755, exist_ok=True)
	except OSError as err:
		print("[UsageConfig] Error %d: Unable to create current movie directory '%s'!  (%s)" % (err.errno, currentPath, err.strerror))
		if defaultPath != currentPath:
			print("[UsageConfig] Checking/Creating default movie directory '%s'." % defaultPath)
			try:
				makedirs(defaultPath, 0o755, exist_ok=True)
			except OSError as err:
				print("[UsageConfig] Error %d: Unable to create default movie directory '%s'!  (%s)" % (err.errno, defaultPath, err.strerror))

	choiceList = [("<default>", "<default>"), ("<current>", "<current>"), ("<timer>", "<timer>")]
	config.usage.timer_path = ConfigSelection(default="<default>", choices=choiceList)
	config.usage.timer_path.load()
	if config.usage.timer_path.saved_value:
		savedValue = config.usage.timer_path.saved_value if config.usage.timer_path.saved_value.startswith("<") else pathjoin(config.usage.timer_path.saved_value, "")
		if savedValue and savedValue not in choiceList:
			config.usage.timer_path.setChoices(choiceList + [(savedValue, savedValue)], default="<default>")
			config.usage.timer_path.value = savedValue
	config.usage.timer_path.save()
	config.usage.instantrec_path = ConfigSelection(default="<default>", choices=choiceList)
	config.usage.instantrec_path.load()
	if config.usage.instantrec_path.saved_value:
		savedValue = config.usage.instantrec_path.saved_value if config.usage.instantrec_path.saved_value.startswith("<") else pathjoin(config.usage.instantrec_path.saved_value, "")
		if savedValue and savedValue not in choiceList:
			config.usage.instantrec_path.setChoices(choiceList + [(savedValue, savedValue)], default="<default>")
			config.usage.instantrec_path.value = savedValue
	config.usage.instantrec_path.save()
	if not exists(resolveFilename(SCOPE_TIMESHIFT)):
		try:
			os.mkdir(resolveFilename(SCOPE_TIMESHIFT), 0o755)
		except:
			pass
	config.timeshift = ConfigSubsection()
	defaultPath = resolveFilename(SCOPE_TIMESHIFT)
	config.timeshift.allowedPaths = ConfigLocations(default=[defaultPath])
	config.usage.timeshift_path = ConfigText(default="")
	if config.usage.timeshift_path.value:
		defaultPath = config.usage.timeshift_path.value
		config.usage.timeshift_path.value = config.usage.timeshift_path.default
		config.usage.timeshift_path.save()
		configfile.save()  # This needs to be done once here to reset the legacy value.
	config.timeshift.path = ConfigSelection(default=defaultPath, choices=[(defaultPath, defaultPath)])
	config.timeshift.path.load()
	savedPath = config.timeshift.path.saved_value
	if savedPath:
		savedPath = pathjoin(savedPath, "")
		if savedPath and savedPath != defaultPath:
			config.timeshift.path.setChoices(default=defaultPath, choices=[(defaultPath, defaultPath), (savedPath, savedPath)])
			config.timeshift.path.value = savedPath
	config.timeshift.path.save()
	currentPath = config.timeshift.path.value
	print("[UsageConfig] Checking/Creating current time shift directory '%s'." % currentPath)
	try:
		makedirs(currentPath, 0o755, exist_ok=True)
	except OSError as err:
		print("[UsageConfig] Error %d: Unable to create current time shift directory '%s'!  (%s)" % (err.errno, currentPath, err.strerror))
		if defaultPath != currentPath:
			print("[UsageConfig] Checking/Creating default time shift directory '%s'." % defaultPath)
			try:
				makedirs(defaultPath, 0o755, exist_ok=True)
			except OSError as err:
				print("[UsageConfig] Error %d: Unable to create default time shift directory '%s'!  (%s)" % (err.errno, defaultPath, err.strerror))

	# The following code temporarily maintains the deprecated timeshift_path so it is available for external plug ins.
	config.usage.timeshift_path = NoSave(ConfigText(default=config.timeshift.path.value))

	def setTimeshiftPath(configElement):
		config.usage.timeshift_path.value = configElement.value
		eSettings.setTimeshiftPath(configElement.value)

	config.timeshift.path.addNotifier(setTimeshiftPath)
	config.timeshift.skipReturnToLive = ConfigYesNo(default=False)

	config.usage.movielist_trashcan = ConfigYesNo(default=True)
	config.usage.movielist_trashcan_days = ConfigNumber(default=8)
	config.usage.movielist_trashcan_reserve = ConfigNumber(default=40)
	config.usage.on_movie_start = ConfigSelection(default="resume", choices=[
		("ask yes", _("Ask user") + " " + _("default") + " " + _("yes")),
		("ask no", _("Ask user") + " " + _("default") + " " + _("no")),
		("resume", _("Resume from last position")),
		("beginning", _("Start from the beginning"))])
	config.usage.on_movie_stop = ConfigSelection(default="movielist", choices=[
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service"))])
	config.usage.on_movie_eof = ConfigSelection(default="movielist", choices=[
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")), ("pause", _("Pause movie at end")), ("playlist", _("Play next (return to movie list)")),
		("playlistquit", _("Play next (return to previous service)")), ("loop", _("Continuous play (loop)")), ("repeatcurrent", _("Repeat"))])
	config.usage.next_movie_msg = ConfigYesNo(default=True)
	config.usage.last_movie_played = ConfigText()
	config.usage.leave_movieplayer_onExit = ConfigSelection(default="popup", choices=[
		("no", _("no")), ("popup", _("With popup")), ("without popup", _("Without popup")), ("movielist", _("Return to movie list"))])

	config.usage.setup_level = ConfigSelection(default="expert", choices=[
		("simple", _("Normal")),
		("intermediate", _("Advanced")),
		("expert", _("Expert"))])

	config.usage.sortExtensionslist = ConfigSelection(default="", choices=[
		("alpha", _("Alphabetical")),
		("", _("Default")),
		("user", _("User defined"))
	])

	config.usage.helpSortOrder = ConfigSelection(default="headings+alphabetic", choices=[
		("headings+alphabetic", _("Alphabetical under headings")),
		("flat+alphabetic", _("Flat alphabetical")),
		("flat+remotepos", _("Flat by position on remote")),
		("flat+remotegroups", _("Flat by key group on remote"))
	])

	config.usage.helpAnimationSpeed = ConfigSelection(default="10", choices=[
		("1", _("Very fast")),
		("5", _("Fast")),
		("10", _("Default")),
		("20", _("Slow")),
		("50", _("Very slow"))
	])

	config.usage.startup_to_standby = ConfigSelection(default="no", choices=[
		("no", _("no")),
		("yes", _("yes")),
		("except", _("No, except Wakeup timer"))])

	config.usage.wakeup_enabled = ConfigSelection(default="no", choices=[
		("no", _("no")),
		("yes", _("yes")),
		("standby", _("Yes, only from standby")),
		("deepstandby", _("Yes, only from deep standby"))])
	config.usage.wakeup_day = ConfigSubDict()
	config.usage.wakeup_time = ConfigSubDict()
	for i in range(7):
		config.usage.wakeup_day[i] = ConfigEnableDisable(default=False)
		config.usage.wakeup_time[i] = ConfigClock(default=((6 * 60 + 0) * 60))

	config.usage.poweroff_enabled = ConfigYesNo(default=False)
	config.usage.poweroff_force = ConfigYesNo(default=False)
	config.usage.poweroff_nextday = ConfigClock(default=((6 * 60 + 0) * 60))
	config.usage.poweroff_day = ConfigSubDict()
	config.usage.poweroff_time = ConfigSubDict()
	for i in range(7):
		config.usage.poweroff_day[i] = ConfigEnableDisable(default=False)
		config.usage.poweroff_time[i] = ConfigClock(default=((1 * 60 + 0) * 60))

	choicelist = [("0", _("Do nothing")), ("1800", _("Standby in ") + _("half an hour"))]
	for i in range(3600, 21601, 3600):
		h = abs(i / 3600)
		h = ngettext("%d hour", "%d hours", h) % h
		choicelist.append((str(i), _("Standby in ") + h))
	config.usage.inactivity_timer = ConfigSelection(default="0", choices=choicelist)
	config.usage.inactivity_timer_blocktime = ConfigYesNo(default=True)
	config.usage.inactivity_timer_blocktime_begin = ConfigClock(default=time.mktime((1970, 1, 1, 18, 0, 0, 0, 0, 0)))
	config.usage.inactivity_timer_blocktime_end = ConfigClock(default=time.mktime((1970, 1, 1, 23, 0, 0, 0, 0, 0)))
	config.usage.inactivity_timer_blocktime_extra = ConfigYesNo(default=False)
	config.usage.inactivity_timer_blocktime_extra_begin = ConfigClock(default=time.mktime((1970, 1, 1, 6, 0, 0, 0, 0, 0)))
	config.usage.inactivity_timer_blocktime_extra_end = ConfigClock(default=time.mktime((1970, 1, 1, 9, 0, 0, 0, 0, 0)))
	config.usage.inactivity_timer_blocktime_by_weekdays = ConfigYesNo(default=False)
	config.usage.inactivity_timer_blocktime_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_begin_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_end_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_extra_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_extra_begin_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_extra_end_day = ConfigSubDict()
	for i in range(7):
		config.usage.inactivity_timer_blocktime_day[i] = ConfigYesNo(default=False)
		config.usage.inactivity_timer_blocktime_begin_day[i] = ConfigClock(default=time.mktime((1970, 1, 1, 18, 0, 0, 0, 0, 0)))
		config.usage.inactivity_timer_blocktime_end_day[i] = ConfigClock(default=time.mktime((1970, 1, 1, 23, 0, 0, 0, 0, 0)))
		config.usage.inactivity_timer_blocktime_extra_day[i] = ConfigYesNo(default=False)
		config.usage.inactivity_timer_blocktime_extra_begin_day[i] = ConfigClock(default=time.mktime((1970, 1, 1, 6, 0, 0, 0, 0, 0)))
		config.usage.inactivity_timer_blocktime_extra_end_day[i] = ConfigClock(default=time.mktime((1970, 1, 1, 9, 0, 0, 0, 0, 0)))

	choicelist = [("0", _("Disabled")), ("event_standby", _("Standby after current event"))]
	for i in range(900, 7201, 900):
		m = abs(i / 60)
		m = ngettext("%d minute", "%d minutes", m) % m
		choicelist.append((str(i), _("Standby in ") + m))
	config.usage.sleep_timer = ConfigSelection(default="0", choices=choicelist)

	choicelist = [("0", _("Disabled"))]
	for i in [300, 600] + list(range(900, 14401, 900)):
		m = abs(i / 60)
		m = ngettext("%d minute", "%d minutes", m) % m
		choicelist.append((str(i), _("after ") + m))
	config.usage.standby_to_shutdown_timer = ConfigSelection(default="0", choices=choicelist)
	config.usage.standby_to_shutdown_timer_blocktime = ConfigYesNo(default=False)
	config.usage.standby_to_shutdown_timer_blocktime_begin = ConfigClock(default=time.mktime((1970, 1, 1, 6, 0, 0, 0, 0, 0)))
	config.usage.standby_to_shutdown_timer_blocktime_end = ConfigClock(default=time.mktime((1970, 1, 1, 23, 0, 0, 0, 0, 0)))

	config.usage.screenSaverStartTimer = ConfigSelection(default=0, choices=[(0, _("Disabled"))] + [(x, _("%d Seconds") % x) for x in (5, 10, 20, 30, 40, 50)] + [(x * 60, ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 5, 10, 15, 20, 30, 45, 60)])
	config.usage.screenSaverMoveTimer = ConfigSelection(default=10, choices=[(x, ngettext("%d Second", "%d Seconds", x) % x) for x in range(1, 61)])

	config.usage.check_timeshift = ConfigYesNo(default=True)

	choicelist = [("0", _("Disabled"))]
	for i in (2, 3, 4, 5, 10, 20, 30):
		choicelist.append((str(i), ngettext("%d second", "%d seconds", i) % i))
	for i in (60, 120, 300):
		m = i / 60
		choicelist.append((str(i), ngettext("%d minute", "%d minutes", m) % m))
	config.usage.timeshift_start_delay = ConfigSelection(default="0", choices=choicelist)

	config.usage.alternatives_priority = ConfigSelection(default="0", choices=[
		("0", "DVB-S/-C/-T"),
		("1", "DVB-S/-T/-C"),
		("2", "DVB-C/-S/-T"),
		("3", "DVB-C/-T/-S"),
		("4", "DVB-T/-C/-S"),
		("5", "DVB-T/-S/-C"),
		("127", _("No priority"))])

	config.usage.frontled_color = ConfigSelection(default="2", choices=[
		("0", _("Off")),
		("1", _("Blue")),
		("2", _("Red")),
		("3", _("Blinking blue")),
		("4", _("Blinking red"))
	])
	config.usage.frontledrec_color = ConfigSelection(default="3", choices=[
		("0", _("Off")),
		("1", _("Blue")),
		("2", _("Red")),
		("3", _("Blinking blue")),
		("4", _("Blinking red"))
	])
	config.usage.frontledstdby_color = ConfigSelection(default="0", choices=[
		("0", _("Off")),
		("1", _("Blue")),
		("2", _("Red")),
		("3", _("Blinking blue")),
		("4", _("Blinking red"))
	])
	config.usage.frontledrecstdby_color = ConfigSelection(default="3", choices=[
		("0", _("Off")),
		("1", _("Blue")),
		("2", _("Red")),
		("3", _("Blinking blue")),
		("4", _("Blinking red"))
	])

	def remote_fallback_changed(configElement):
		if configElement.value:
			configElement.value = "%s%s" % (not configElement.value.startswith("http://") and "http://" or "", configElement.value)
			configElement.value = "%s%s" % (configElement.value, configElement.value.count(":") == 1 and ":8001" or "")
	config.usage.remote_fallback_enabled = ConfigYesNo(default=False)
	config.usage.remote_fallback = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_import_url = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_import_url.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_alternative = ConfigYesNo(default=False)
	config.usage.remote_fallback_dvb_t = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_dvb_t.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_dvb_c = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_dvb_c.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_atsc = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_atsc.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_import = ConfigSelection(default="", choices=[("", _("No")), ("channels", _("Channels only")), ("channels_epg", _("Channels and EPG")), ("epg", _("EPG only"))])
	config.usage.remote_fallback_import_restart = ConfigYesNo(default=False)
	config.usage.remote_fallback_import_standby = ConfigYesNo(default=False)
	config.usage.remote_fallback_ok = ConfigYesNo(default=False)
	config.usage.remote_fallback_nok = ConfigYesNo(default=False)
	config.usage.remote_fallback_extension_menu = ConfigYesNo(default=False)
	config.usage.remote_fallback_external_timer = ConfigYesNo(default=False)
	config.usage.remote_fallback_external_timer_default = ConfigYesNo(default=True)
	config.usage.remote_fallback_openwebif_customize = ConfigYesNo(default=False)
	config.usage.remote_fallback_openwebif_userid = ConfigText(default="root")
	config.usage.remote_fallback_openwebif_password = ConfigPassword(default="default")
	config.usage.remote_fallback_openwebif_port = ConfigInteger(default=80, limits=(0, 65535))
	config.usage.remote_fallback_dvbt_region = ConfigText(default="fallback DVB-T/T2 Europe")

	def setHttpStartDelay(configElement):
		eSettings.setHttpStartDelay(configElement.value)

	config.usage.http_startdelay = ConfigSelection(default=0, choices=[(0, _("Disabled"))] + [(x, _("%d ms") % x) for x in (10, 50, 100, 500, 1000, 2000)])
	config.usage.http_startdelay.addNotifier(setHttpStartDelay)

	config.usage.show_timer_conflict_warning = ConfigYesNo(default=True)

	config.usage.alternateGitHubDNS = ConfigYesNo(default=False)

	preferredTunerChoicesUpdate()

	config.misc.disable_background_scan = ConfigYesNo(default=False)

	def setUseCIAssignment(configElement):
		eSettings.setUseCIAssignment(configElement.value)

	config.misc.use_ci_assignment = ConfigYesNo(default=True)
	config.misc.use_ci_assignment.addNotifier(setUseCIAssignment)

	config.usage.servicenum_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.usage.servicename_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.usage.serviceinfo_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.usage.progressinfo_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.usage.serviceitems_per_page = ConfigSelectionNumber(default=18, stepwidth=1, min=8, max=40, wraparound=True)

	config.usage.show_event_progress_in_servicelist = ConfigSelection(default="barright", choices=[
		("barleft", _("Progress bar left")),
		("barright", _("Progress bar right")),
		("percleft", _("Percentage left")),
		("percright", _("Percentage right")),
		("minsleft", _("Remaining minutes left")),
		("minsright", _("Remaining minutes right")),
		("no", _("No"))
	])
	config.usage.show_event_progress_in_servicelist.addNotifier(refreshServiceList)
	config.usage.show_channel_numbers_in_servicelist = ConfigYesNo(default=True)
	config.usage.show_channel_numbers_in_servicelist.addNotifier(refreshServiceList)

	config.usage.blinking_display_clock_during_recording = ConfigYesNo(default=False)

	if displaytype == "textlcd" or "text" in displaytype:
		config.usage.blinking_rec_symbol_during_recording = ConfigSelection(default="Channel", choices=[
			("Rec", _("REC symbol")),
			("RecBlink", _("Blinking REC symbol")),
			("Channel", _("Channel name"))
		])
	config.usage.blinking_rec_symbol_during_recording = ConfigYesNo(default=True)

	config.usage.show_message_when_recording_starts = ConfigYesNo(default=True)

	config.usage.load_length_of_movies_in_moviellist = ConfigYesNo(default=True)
	config.usage.show_icons_in_movielist = ConfigSelection(default='i', choices=[
		('o', _("Off")),
		('p', _("Progress")),
		('s', _("Small progress")),
		('i', _("Icons")),
	])
	config.usage.movielist_unseen = ConfigYesNo(default=False)

	config.usage.swap_snr_on_osd = ConfigYesNo(default=False)
	config.usage.swap_time_display_on_osd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_media_time_display_on_osd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_time_remaining_on_osd = ConfigSelection(default = "0", choices = [("0", _("Remaining")), ("1", _("Elapsed")), ("2", _("Elapsed & Remaining")), ("3", _("Remaining & Elapsed"))])
	config.usage.elapsed_time_positive_osd = ConfigYesNo(default = False)
	config.usage.swap_time_display_on_vfd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_media_time_display_on_vfd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_time_remaining_on_vfd = ConfigSelection(default = "0", choices = [("0", _("Remaining")), ("1", _("Elapsed")), ("2", _("Elapsed & Remaining")), ("3", _("Remaining & Elapsed"))])
	config.usage.elapsed_time_positive_vfd = ConfigYesNo(default = False)

	def SpinnerOnOffChanged(configElement):
		setSpinnerOnOff(int(configElement.value))
	config.usage.show_spinner.addNotifier(SpinnerOnOffChanged)

	def EnableTtCachingChanged(configElement):
		setEnableTtCachingOnOff(int(configElement.value))
	config.usage.enable_tt_caching.addNotifier(EnableTtCachingChanged)

	def TunerTypePriorityOrderChanged(configElement):
		setTunerTypePriorityOrder(int(configElement.value))
	config.usage.alternatives_priority.addNotifier(TunerTypePriorityOrderChanged, immediate_feedback=False)

	def PreferredTunerChanged(configElement):
		setPreferredTuner(int(configElement.value))
	config.usage.frontend_priority.addNotifier(PreferredTunerChanged)

	config.usage.show_picon_in_display = ConfigYesNo(default=True)
	config.usage.hide_zap_errors = ConfigYesNo(default=False)
	config.usage.show_cryptoinfo = ConfigYesNo(default=True)
	config.usage.show_eit_nownext = ConfigYesNo(default=True)
	config.usage.show_vcr_scart = ConfigYesNo(default=False)
	config.usage.show_update_disclaimer = ConfigYesNo(default=True)
	config.usage.pic_resolution = ConfigSelection(default=None, choices=[(None, _("Same resolution as skin")), ("(720, 576)", "720x576"), ("(1280, 720)", "1280x720"), ("(1920, 1080)", "1920x1080")][:BoxInfo.getItem("HasFullHDSkinSupport") and 4 or 3])

	config.usage.date = ConfigSubsection()
	config.usage.date.enabled = NoSave(ConfigBoolean(default=False))
	config.usage.date.enabled_display = NoSave(ConfigBoolean(default=False))
	config.usage.time = ConfigSubsection()
	config.usage.time.enabled = NoSave(ConfigBoolean(default=False))
	config.usage.time.disabled = NoSave(ConfigBoolean(default=True))
	config.usage.time.enabled_display = NoSave(ConfigBoolean(default=False))
	config.usage.time.wide = NoSave(ConfigBoolean(default=False))
	config.usage.time.wide_display = NoSave(ConfigBoolean(default=False))

	# TRANSLATORS: full date representation dayname daynum monthname year in strftime() format! See 'man strftime'
	config.usage.date.dayfull = ConfigSelection(default=_("%A %-d %B %Y"), choices=[
		(_("%A %d %B %Y"), _("Dayname DD Month Year")),
		(_("%A %-d %B %Y"), _("Dayname D Month Year")),
		(_("%A %d-%B-%Y"), _("Dayname DD-Month-Year")),
		(_("%A %-d-%B-%Y"), _("Dayname D-Month-Year")),
		(_("%A %d/%m/%Y"), _("Dayname DD/MM/Year")),
		(_("%A %-d/%m/%Y"), _("Dayname D/MM/Year")),
		(_("%A %d/%-m/%Y"), _("Dayname DD/M/Year")),
		(_("%A %-d/%-m/%Y"), _("Dayname D/M/Year")),
		(_("%A %B %d %Y"), _("Dayname Month DD Year")),
		(_("%A %B %-d %Y"), _("Dayname Month D Year")),
		(_("%A %B-%d-%Y"), _("Dayname Month-DD-Year")),
		(_("%A %B-%-d-%Y"), _("Dayname Month-D-Year")),
		(_("%A %m/%d/%Y"), _("Dayname MM/DD/Year")),
		(_("%A %-m/%d/%Y"), _("Dayname M/DD/Year")),
		(_("%A %m/%-d/%Y"), _("Dayname MM/D/Year")),
		(_("%A %-m/%-d/%Y"), _("Dayname M/D/Year")),
		(_("%A %Y %B %d"), _("Dayname Year Month DD")),
		(_("%A %Y %B %-d"), _("Dayname Year Month D")),
		(_("%A %Y-%B-%d"), _("Dayname Year-Month-DD")),
		(_("%A %Y-%B-%-d"), _("Dayname Year-Month-D")),
		(_("%A %Y/%m/%d"), _("Dayname Year/MM/DD")),
		(_("%A %Y/%m/%-d"), _("Dayname Year/MM/D")),
		(_("%A %Y/%-m/%d"), _("Dayname Year/M/DD")),
		(_("%A %Y/%-m/%-d"), _("Dayname Year/M/D"))
	])

	# TRANSLATORS: long date representation short dayname daynum monthname year in strftime() format! See 'man strftime'
	config.usage.date.shortdayfull = ConfigText(default=_("%a %-d %B %Y"))

	# TRANSLATORS: long date representation short dayname daynum short monthname year in strftime() format! See 'man strftime'
	config.usage.date.daylong = ConfigText(default=_("%a %-d %b %Y"))

	# TRANSLATORS: short date representation dayname daynum short monthname in strftime() format! See 'man strftime'
	config.usage.date.dayshortfull = ConfigText(default=_("%A %-d %B"))

	# TRANSLATORS: short date representation short dayname daynum short monthname in strftime() format! See 'man strftime'
	config.usage.date.dayshort = ConfigText(default=_("%a %-d %b"))

	# TRANSLATORS: small date representation short dayname daynum in strftime() format! See 'man strftime'
	config.usage.date.daysmall = ConfigText(default=_("%a %-d"))

	# TRANSLATORS: full date representation daynum monthname year in strftime() format! See 'man strftime'
	config.usage.date.full = ConfigText(default=_("%-d %B %Y"))

	# TRANSLATORS: long date representation daynum short monthname year in strftime() format! See 'man strftime'
	config.usage.date.long = ConfigText(default=_("%-d %b %Y"))

	# TRANSLATORS: small date representation daynum short monthname in strftime() format! See 'man strftime'
	config.usage.date.short = ConfigText(default=_("%-d %b"))

	def setDateStyles(configElement):
		dateStyles = {
			# dayfull            shortdayfull      daylong           dayshortfull   dayshort       daysmall    full           long           short
			_("%A %d %B %Y"): (_("%a %d %B %Y"), _("%a %d %b %Y"), _("%A %d %B"), _("%a %d %b"), _("%a %d"), _("%d %B %Y"), _("%d %b %Y"), _("%d %b")),
			_("%A %-d %B %Y"): (_("%a %-d %B %Y"), _("%a %-d %b %Y"), _("%A %-d %B"), _("%a %-d %b"), _("%a %-d"), _("%-d %B %Y"), _("%-d %b %Y"), _("%-d %b")),
			_("%A %d-%B-%Y"): (_("%a %d-%B-%Y"), _("%a %d-%b-%Y"), _("%A %d-%B"), _("%a %d-%b"), _("%a %d"), _("%d-%B-%Y"), _("%d-%b-%Y"), _("%d-%b")),
			_("%A %-d-%B-%Y"): (_("%a %-d-%B-%Y"), _("%a %-d-%b-%Y"), _("%A %-d-%B"), _("%a %-d-%b"), _("%a %-d"), _("%-d-%B-%Y"), _("%-d-%b-%Y"), _("%-d-%b")),
			_("%A %d/%m/%Y"): (_("%a %d/%m/%Y"), _("%a %d/%m/%Y"), _("%A %d/%m"), _("%a %d/%m"), _("%a %d"), _("%d/%m/%Y"), _("%d/%m/%Y"), _("%d/%m")),
			_("%A %-d/%m/%Y"): (_("%a %-d/%m/%Y"), _("%a %-d/%m/%Y"), _("%A %-d/%m"), _("%a %-d/%m"), _("%a %-d"), _("%-d/%m/%Y"), _("%-d/%m/%Y"), _("%-d/%m")),
			_("%A %d/%-m/%Y"): (_("%a %d/%-m/%Y"), _("%a %d/%-m/%Y"), _("%A %d/%-m"), _("%a %d/%-m"), _("%a %d"), _("%d/%-m/%Y"), _("%d/%-m/%Y"), _("%d/%-m")),
			_("%A %-d/%-m/%Y"): (_("%a %-d/%-m/%Y"), _("%a %-d/%-m/%Y"), _("%A %-d/%-m"), _("%a %-d/%-m"), _("%a %-d"), _("%-d/%-m/%Y"), _("%-d/%-m/%Y"), _("%-d/%-m")),
			_("%A %B %d %Y"): (_("%a %B %d %Y"), _("%a %b %d %Y"), _("%A %B %d"), _("%a %b %d"), _("%a %d"), _("%B %d %Y"), _("%b %d %Y"), _("%b %d")),
			_("%A %B %-d %Y"): (_("%a %B %-d %Y"), _("%a %b %-d %Y"), _("%A %B %-d"), _("%a %b %-d"), _("%a %-d"), _("%B %-d %Y"), _("%b %-d %Y"), _("%b %-d")),
			_("%A %B-%d-%Y"): (_("%a %B-%d-%Y"), _("%a %b-%d-%Y"), _("%A %B-%d"), _("%a %b-%d"), _("%a %d"), _("%B-%d-%Y"), _("%b-%d-%Y"), _("%b-%d")),
			_("%A %B-%-d-%Y"): (_("%a %B-%-d-%Y"), _("%a %b-%-d-%Y"), _("%A %B-%-d"), _("%a %b-%-d"), _("%a %-d"), _("%B-%-d-%Y"), _("%b-%-d-%Y"), _("%b-%-d")),
			_("%A %m/%d/%Y"): (_("%a %m/%d/%Y"), _("%a %m/%d/%Y"), _("%A %m/%d"), _("%a %m/%d"), _("%a %d"), _("%m/%d/%Y"), _("%m/%d/%Y"), _("%m/%d")),
			_("%A %-m/%d/%Y"): (_("%a %-m/%d/%Y"), _("%a %-m/%d/%Y"), _("%A %-m/%d"), _("%a %-m/%d"), _("%a %d"), _("%-m/%d/%Y"), _("%-m/%d/%Y"), _("%-m/%d")),
			_("%A %m/%-d/%Y"): (_("%a %m/%-d/%Y"), _("%a %m/%-d/%Y"), _("%A %m/%-d"), _("%a %m/%-d"), _("%a %-d"), _("%m/%-d/%Y"), _("%m/%-d/%Y"), _("%m/%-d")),
			_("%A %-m/%-d/%Y"): (_("%a %-m/%-d/%Y"), _("%a %-m/%-d/%Y"), _("%A %-m/%-d"), _("%a %-m/%-d"), _("%a %-d"), _("%-m/%-d/%Y"), _("%-m/%-d/%Y"), _("%-m/%-d")),
			_("%A %Y %B %d"): (_("%a %Y %B %d"), _("%a %Y %b %d"), _("%A %B %d"), _("%a %b %d"), _("%a %d"), _("%Y %B %d"), _("%Y %b %d"), _("%b %d")),
			_("%A %Y %B %-d"): (_("%a %Y %B %-d"), _("%a %Y %b %-d"), _("%A %B %-d"), _("%a %b %-d"), _("%a %-d"), _("%Y %B %-d"), _("%Y %b %-d"), _("%b %-d")),
			_("%A %Y-%B-%d"): (_("%a %Y-%B-%d"), _("%a %Y-%b-%d"), _("%A %B-%d"), _("%a %b-%d"), _("%a %d"), _("%Y-%B-%d"), _("%Y-%b-%d"), _("%b-%d")),
			_("%A %Y-%B-%-d"): (_("%a %Y-%B-%-d"), _("%a %Y-%b-%-d"), _("%A %B-%-d"), _("%a %b-%-d"), _("%a %-d"), _("%Y-%B-%-d"), _("%Y-%b-%-d"), _("%b-%-d")),
			_("%A %Y/%m/%d"): (_("%a %Y/%m/%d"), _("%a %Y/%m/%d"), _("%A %m/%d"), _("%a %m/%d"), _("%a %d"), _("%Y/%m/%d"), _("%Y/%m/%d"), _("%m/%d")),
			_("%A %Y/%m/%-d"): (_("%a %Y/%m/%-d"), _("%a %Y/%m/%-d"), _("%A %m/%-d"), _("%a %m/%-d"), _("%a %-d"), _("%Y/%m/%-d"), _("%Y/%m/%-d"), _("%m/%-d")),
			_("%A %Y/%-m/%d"): (_("%a %Y/%-m/%d"), _("%a %Y/%-m/%d"), _("%A %-m/%d"), _("%a %-m/%d"), _("%a %d"), _("%Y/%-m/%d"), _("%Y/%-m/%d"), _("%-m/%d")),
			_("%A %Y/%-m/%-d"): (_("%a %Y/%-m/%-d"), _("%a %Y/%-m/%-d"), _("%A %-m/%-d"), _("%a %-m/%-d"), _("%a %-d"), _("%Y/%-m/%-d"), _("%Y/%-m/%-d"), _("%-m/%-d"))
		}
		style = dateStyles.get(configElement.value, ((_("Invalid")) * 8))
		config.usage.date.shortdayfull.value = style[0]
		config.usage.date.shortdayfull.save()
		config.usage.date.daylong.value = style[1]
		config.usage.date.daylong.save()
		config.usage.date.dayshortfull.value = style[2]
		config.usage.date.dayshortfull.save()
		config.usage.date.dayshort.value = style[3]
		config.usage.date.dayshort.save()
		config.usage.date.daysmall.value = style[4]
		config.usage.date.daysmall.save()
		config.usage.date.full.value = style[5]
		config.usage.date.full.save()
		config.usage.date.long.value = style[6]
		config.usage.date.long.save()
		config.usage.date.short.value = style[7]
		config.usage.date.short.save()

	config.usage.date.dayfull.addNotifier(setDateStyles)

	# TRANSLATORS: full time representation hour:minute:seconds
	if locale.nl_langinfo(locale.AM_STR) and locale.nl_langinfo(locale.PM_STR):
		config.usage.time.long = ConfigSelection(default=_("%T"), choices=[
			(_("%T"), _("HH:mm:ss")),
			(_("%-H:%M:%S"), _("H:mm:ss")),
			(_("%I:%M:%S%^p"), _("hh:mm:ssAM/PM")),
			(_("%-I:%M:%S%^p"), _("h:mm:ssAM/PM")),
			(_("%I:%M:%S%P"), _("hh:mm:ssam/pm")),
			(_("%-I:%M:%S%P"), _("h:mm:ssam/pm")),
			(_("%I:%M:%S"), _("hh:mm:ss")),
			(_("%-I:%M:%S"), _("h:mm:ss"))
		])
	else:
		config.usage.time.long = ConfigSelection(default=_("%T"), choices=[
			(_("%T"), _("HH:mm:ss")),
			(_("%-H:%M:%S"), _("H:mm:ss")),
			(_("%I:%M:%S"), _("hh:mm:ss")),
			(_("%-I:%M:%S"), _("h:mm:ss"))
		])

	# TRANSLATORS: time representation hour:minute:seconds for 24 hour clock or 12 hour clock without AM/PM and hour:minute for 12 hour clocks with AM/PM
	config.usage.time.mixed = ConfigText(default=_("%T"))

	# TRANSLATORS: short time representation hour:minute (Same as "Default")
	config.usage.time.short = ConfigText(default=_("%R"))

	def setTimeStyles(configElement):
		timeStyles = {
			# long      mixed    short
			_("%T"): (_("%T"), _("%R")),
			_("%-H:%M:%S"): (_("%-H:%M:%S"), _("%-H:%M")),
			_("%I:%M:%S%^p"): (_("%I:%M%^p"), _("%I:%M%^p")),
			_("%-I:%M:%S%^p"): (_("%-I:%M%^p"), _("%-I:%M%^p")),
			_("%I:%M:%S%P"): (_("%I:%M%P"), _("%I:%M%P")),
			_("%-I:%M:%S%P"): (_("%-I:%M%P"), _("%-I:%M%P")),
			_("%I:%M:%S"): (_("%I:%M:%S"), _("%I:%M")),
			_("%-I:%M:%S"): (_("%-I:%M:%S"), _("%-I:%M"))
		}
		style = timeStyles.get(configElement.value, ((_("Invalid")) * 2))
		config.usage.time.mixed.value = style[0]
		config.usage.time.mixed.save()
		config.usage.time.short.value = style[1]
		config.usage.time.short.save()
		config.usage.time.wide.value = style[1].endswith(("P", "p"))

	config.usage.time.long.addNotifier(setTimeStyles)

	try:
		dateEnabled, timeEnabled = parameters.get("AllowUserDatesAndTimes", (0, 0))
	except Exception as error:
		print("[UsageConfig] Error loading 'AllowUserDatesAndTimes' skin parameter! (%s)" % error)
		dateEnabled, timeEnabled = (0, 0)
	if dateEnabled:
		config.usage.date.enabled.value = True
	else:
		config.usage.date.enabled.value = False
		config.usage.date.dayfull.value = config.usage.date.dayfull.default
	if timeEnabled:
		config.usage.time.enabled.value = True
		config.usage.time.disabled.value = not config.usage.time.enabled.value
	else:
		config.usage.time.enabled.value = False
		config.usage.time.disabled.value = not config.usage.time.enabled.value
		config.usage.time.long.value = config.usage.time.long.default

	# TRANSLATORS: compact date representation (for VFD) daynum short monthname in strftime() format! See 'man strftime'
	config.usage.date.display = ConfigSelection(default=_("%-d %b"), choices=[
		("", _("Hidden / Blank")),
		(_("%d %b"), _("Day DD Mon")),
		(_("%-d %b"), _("Day D Mon")),
		(_("%d-%b"), _("Day DD-Mon")),
		(_("%-d-%b"), _("Day D-Mon")),
		(_("%d/%m"), _("Day DD/MM")),
		(_("%-d/%m"), _("Day D/MM")),
		(_("%d/%-m"), _("Day DD/M")),
		(_("%-d/%-m"), _("Day D/M")),
		(_("%b %d"), _("Day Mon DD")),
		(_("%b %-d"), _("Day Mon D")),
		(_("%b-%d"), _("Day Mon-DD")),
		(_("%b-%-d"), _("Day Mon-D")),
		(_("%m/%d"), _("Day MM/DD")),
		(_("%m/%-d"), _("Day MM/D")),
		(_("%-m/%d"), _("Day M/DD")),
		(_("%-m/%-d"), _("Day M/D"))
	])

	config.usage.date.displayday = ConfigText(default=_("%a %-d+%b_"))
	config.usage.date.display_template = ConfigText(default=_("%-d+%b_"))
	config.usage.date.compact = ConfigText(default=_("%-d+%b_"))
	config.usage.date.compressed = ConfigText(default=_("%-d+%b_"))

	timeDisplayValue = [_("%R")]

	def adjustDisplayDates():
		if timeDisplayValue[0] == "":
			if config.usage.date.display.value == "":  # If the date and time are both hidden output a space to blank the VFD display.
				config.usage.date.compact.value = " "
				config.usage.date.compressed.value = " "
			else:
				config.usage.date.compact.value = config.usage.date.displayday.value
				config.usage.date.compressed.value = config.usage.date.displayday.value
		else:
			if config.usage.time.wide_display.value:
				config.usage.date.compact.value = config.usage.date.display_template.value.replace("_", "").replace("=", "").replace("+", "")
				config.usage.date.compressed.value = config.usage.date.display_template.value.replace("_", "").replace("=", "").replace("+", "")
			else:
				config.usage.date.compact.value = config.usage.date.display_template.value.replace("_", " ").replace("=", "-").replace("+", " ")
				config.usage.date.compressed.value = config.usage.date.display_template.value.replace("_", " ").replace("=", "").replace("+", "")
		config.usage.date.compact.save()
		config.usage.date.compressed.save()

	def setDateDisplayStyles(configElement):
		dateDisplayStyles = {
			# display      displayday     template
			"": ("", ""),
			_("%d %b"): (_("%a %d %b"), _("%d+%b_")),
			_("%-d %b"): (_("%a %-d %b"), _("%-d+%b_")),
			_("%d-%b"): (_("%a %d-%b"), _("%d=%b_")),
			_("%-d-%b"): (_("%a %-d-%b"), _("%-d=%b_")),
			_("%d/%m"): (_("%a %d/%m"), _("%d/%m ")),
			_("%-d/%m"): (_("%a %-d/%m"), _("%-d/%m ")),
			_("%d/%-m"): (_("%a %d/%-m"), _("%d/%-m ")),
			_("%-d/%-m"): (_("%a %-d/%-m"), _("%-d/%-m ")),
			_("%b %d"): (_("%a %b %d"), _("%b+%d ")),
			_("%b %-d"): (_("%a %b %-d"), _("%b+%-d ")),
			_("%b-%d"): (_("%a %b-%d"), _("%b=%d ")),
			_("%b-%-d"): (_("%a %b-%-d"), _("%b=%-d ")),
			_("%m/%d"): (_("%a %m/%d"), _("%m/%d ")),
			_("%m/%-d"): (_("%a %m/%-d"), _("%m/%-d ")),
			_("%-m/%d"): (_("%a %-m/%d"), _("%-m/%d ")),
			_("%-m/%-d"): (_("%a %-m/%-d"), _("%-m/%-d "))
		}
		style = dateDisplayStyles.get(configElement.value, ((_("Invalid")) * 2))
		config.usage.date.displayday.value = style[0]
		config.usage.date.displayday.save()
		config.usage.date.display_template.value = style[1]
		config.usage.date.display_template.save()
		adjustDisplayDates()

	config.usage.date.display.addNotifier(setDateDisplayStyles)

	# TRANSLATORS: short time representation hour:minute (Same as "Default")
	if locale.nl_langinfo(locale.AM_STR) and locale.nl_langinfo(locale.PM_STR):
		config.usage.time.display = ConfigSelection(default=_("%R"), choices=[
			("", _("Hidden / Blank")),
			(_("%R"), _("HH:mm")),
			(_("%-H:%M"), _("H:mm")),
			(_("%I:%M%^p"), _("hh:mmAM/PM")),
			(_("%-I:%M%^p"), _("h:mmAM/PM")),
			(_("%I:%M%P"), _("hh:mmam/pm")),
			(_("%-I:%M%P"), _("h:mmam/pm")),
			(_("%I:%M"), _("hh:mm")),
			(_("%-I:%M"), _("h:mm"))
		])
	else:
		config.usage.time.display = ConfigSelection(default=_("%R"), choices=[
			("", _("Hidden / Blank")),
			(_("%R"), _("HH:mm")),
			(_("%-H:%M"), _("H:mm")),
			(_("%I:%M"), _("hh:mm")),
			(_("%-I:%M"), _("h:mm"))
		])

	def setTimeDisplayStyles(configElement):
		timeDisplayValue[0] = config.usage.time.display.value
		config.usage.time.wide_display.value = configElement.value.endswith(("P", "p"))
		adjustDisplayDates()

	config.usage.time.display.addNotifier(setTimeDisplayStyles)

	try:
		dateDisplayEnabled, timeDisplayEnabled = parameters.get("AllowUserDatesAndTimesDisplay", (0, 0))
	except Exception as error:
		print("[UsageConfig] Error loading 'AllowUserDatesAndTimesDisplay' display skin parameter! (%s)" % error)
		dateDisplayEnabled, timeDisplayEnabled = (0, 0)
	if dateDisplayEnabled:
		config.usage.date.enabled_display.value = True
	else:
		config.usage.date.enabled_display.value = False
		config.usage.date.display.value = config.usage.date.display.default
	if timeDisplayEnabled:
		config.usage.time.enabled_display.value = True
	else:
		config.usage.time.enabled_display.value = False
		config.usage.time.display.value = config.usage.time.display.default

	config.usage.boolean_graphic = ConfigYesNo(default=False)
	config.usage.show_slider_value = ConfigYesNo(default=True)
	config.usage.cursorscroll = ConfigSelectionNumber(min=0, max=50, stepwidth=5, default=0, wraparound=True)

	if BoxInfo.getItem("Fan"):
		choicelist = [('off', _("Off")), ('on', _("On")), ('auto', _("Auto"))]
		if exists("/proc/stb/fp/fan_choices"):
			choicelist = [x for x in choicelist if x[0] in open("/proc/stb/fp/fan_choices", "r").read().strip().split(" ")]
		config.usage.fan = ConfigSelection(choicelist)

		def fanChanged(configElement):
			with open(BoxInfo.getItem("Fan"), "w") as fd:
				fd.write(configElement.value)
		config.usage.fan.addNotifier(fanChanged)

	if BoxInfo.getItem("FanPWM"):
		def fanSpeedChanged(configElement):
			with open(BoxInfo.getItem("FanPWM"), "w") as fd:
				fd.write(hex(configElement.value)[2:])
		config.usage.fanspeed = ConfigSlider(default=127, increment=8, limits=(0, 255))
		config.usage.fanspeed.addNotifier(fanSpeedChanged)

	if BoxInfo.getItem("PowerLED"):
		def powerLEDChanged(configElement):
			if "fp" in BoxInfo.getItem("PowerLED"):
				with open(BoxInfo.getItem("PowerLED"), "w") as fd:
					fd.write(configElement.value and "1" or "0")
				patterns = [PATTERN_ON, PATTERN_ON, PATTERN_OFF, PATTERN_ON] if configElement.value else [PATTERN_OFF, PATTERN_OFF, PATTERN_OFF, PATTERN_OFF]
				ledPatterns.setLedPatterns(1, patterns)
			else:
				with open(BoxInfo.getItem("PowerLED"), "w") as fd:
					fd.write(configElement.value and "on" or "off")
		config.usage.powerLED = ConfigYesNo(default=True)
		config.usage.powerLED.addNotifier(powerLEDChanged)

	if BoxInfo.getItem("StandbyLED"):
		def standbyLEDChanged(configElement):
			if "fp" in BoxInfo.getItem("StandbyLED"):
				patterns = [PATTERN_OFF, PATTERN_BLINK, PATTERN_ON, PATTERN_BLINK] if configElement.value else [PATTERN_OFF, PATTERN_OFF, PATTERN_OFF, PATTERN_OFF]
				ledPatterns.setLedPatterns(0, patterns)
			else:
				with open(BoxInfo.getItem("StandbyLED"), "w") as fd:
					fd.write(configElement.value and "on" or "off")
		config.usage.standbyLED = ConfigYesNo(default=True)
		config.usage.standbyLED.addNotifier(standbyLEDChanged)

	if BoxInfo.getItem("SuspendLED"):
		def suspendLEDChanged(configElement):
			if "fp" in BoxInfo.getItem("SuspendLED"):
				with open(BoxInfo.getItem("SuspendLED"), "w") as fd:
					fd.write(configElement.value and "1" or "0")
			else:
				with open(BoxInfo.getItem("SuspendLED"), "w") as fd:
					fd.write(configElement.value and "on" or "off")
		config.usage.suspendLED = ConfigYesNo(default=True)
		config.usage.suspendLED.addNotifier(suspendLEDChanged)

	if BoxInfo.getItem("PowerOffDisplay"):
		def powerOffDisplayChanged(configElement):
			with open(BoxInfo.getItem("PowerOffDisplay"), "w") as fd:
				fd.write(configElement.value and "1" or "0")
		config.usage.powerOffDisplay = ConfigYesNo(default=True)
		config.usage.powerOffDisplay.addNotifier(powerOffDisplayChanged)

	if BoxInfo.getItem("LCDshow_symbols"):
		def lcdShowSymbols(configElement):
			with open(BoxInfo.getItem("LCDshow_symbols"), "w") as fd:
				fd.write(configElement.value and "1" or "0")
		config.usage.lcd_show_symbols = ConfigYesNo(default=True)
		config.usage.lcd_show_symbols.addNotifier(lcdShowSymbols)

	if BoxInfo.getItem("WakeOnLAN"):
		f = open(BoxInfo.getItem("WakeOnLAN"), "r")
		status = f.read().strip()
		f.close()

		def wakeOnLANChanged(configElement):
			if status in ("enable", "disable"):
				with open(BoxInfo.getItem("WakeOnLAN"), "w") as fd:
					fd.write(configElement.value and "enable" or "disable")
			else:
				with open(BoxInfo.getItem("WakeOnLAN"), "w") as fd:
					fd.write(configElement.value and "on" or "off")
		config.usage.wakeOnLAN = ConfigYesNo(default=False)
		config.usage.wakeOnLAN.addNotifier(wakeOnLANChanged)

	if BoxInfo.getItem("hasXcoreVFD"):
		def set12to8characterVFD(configElement):
			with open(BoxInfo.getItem("hasXcoreVFD"), "w") as fd:
				fd.write(not configElement.value and "1" or "0")
		config.usage.toggle12to8characterVFD = ConfigYesNo(default=False)
		config.usage.toggle12to8characterVFD.addNotifier(set12to8characterVFD)

	if BoxInfo.getItem("LcdLiveTVMode"):
		def setLcdLiveTVMode(configElement):
			with open(BoxInfo.getItem("LcdLiveTVMode"), "w") as fd:
				fd.write(configElement.value)
		config.usage.LcdLiveTVMode = ConfigSelection(default="0", choices=[str(x) for x in range(0, 9)])
		config.usage.LcdLiveTVMode.addNotifier(setLcdLiveTVMode)

	if BoxInfo.getItem("LcdLiveDecoder"):
		def setLcdLiveDecoder(configElement):
			with open(BoxInfo.getItem("LcdLiveDecoder"), "w") as fd:
				fd.write(configElement.value)
		config.usage.LcdLiveDecoder = ConfigSelection(default="0", choices=[str(x) for x in range(0, 4)])
		config.usage.LcdLiveDecoder.addNotifier(setLcdLiveDecoder)

	config.usage.boolean_graphic = ConfigSelection(default="true", choices={"false": _("no"), "true": _("yes"), "only_bool": _("yes, but not in multi selections")})

	config.usage.multiboot_order = ConfigYesNo(default=True)

	config.usage.setupShowDefault = ConfigSelection(default="spaces", choices=[
		("no", _("Don't show default")),
		("spaces", _("Show default after description")),
		("newline", _("Show default on new line"))
	])

	config.epg = ConfigSubsection()
	config.epg.eit = ConfigYesNo(default=True)
	config.epg.mhw = ConfigYesNo(default=False)
	config.epg.freesat = ConfigYesNo(default=True)
	config.epg.viasat = ConfigYesNo(default=True)
	config.epg.netmed = ConfigYesNo(default=True)
	config.epg.virgin = ConfigYesNo(default=False)
	config.epg.opentv = ConfigYesNo(default=False)
	config.epg.saveepg = ConfigYesNo(default=True)

	config.epg.maxdays = ConfigSelectionNumber(min=1, max=365, stepwidth=1, default=7, wraparound=True)
	config.epg.joinAbbreviatedEventNames = ConfigYesNo(default=True)
	config.epg.eventNamePrefixes = ConfigText(default="")
	config.epg.eventNamePrefixMode = ConfigSelection(choices=[(0, _("Off")), (1, _("Remove")), (2, _("Move to description"))])

	def EpgmaxdaysChanged(configElement):
		eEPGCache.getInstance().setEpgmaxdays(config.epg.maxdays.getValue())
	config.epg.maxdays.addNotifier(EpgmaxdaysChanged)

	config.misc.epgratingcountry = ConfigSelection(default="", choices=[
		("", _("Auto detect")),
		("ETSI", _("Generic")),
		("AUS", _("Australia"))
	])
	config.misc.epggenrecountry = ConfigSelection(default="", choices=[
		("", _("Auto detect")),
		("ETSI", _("Generic")),
		("AUS", _("Australia"))
	])

	def EpgSettingsChanged(configElement):
		mask = 0xffffffff
		if not config.epg.eit.value:
			mask &= ~(eEPGCache.NOWNEXT | eEPGCache.SCHEDULE | eEPGCache.SCHEDULE_OTHER)
		if not config.epg.mhw.value:
			mask &= ~eEPGCache.MHW
		if not config.epg.freesat.value:
			mask &= ~(eEPGCache.FREESAT_NOWNEXT | eEPGCache.FREESAT_SCHEDULE | eEPGCache.FREESAT_SCHEDULE_OTHER)
		if not config.epg.viasat.value:
			mask &= ~eEPGCache.VIASAT
		if not config.epg.netmed.value:
			mask &= ~(eEPGCache.NETMED_SCHEDULE | eEPGCache.NETMED_SCHEDULE_OTHER)
		if not config.epg.virgin.value:
			mask &= ~(eEPGCache.VIRGIN_NOWNEXT | eEPGCache.VIRGIN_SCHEDULE)
		if not config.epg.opentv.value:
			mask &= ~eEPGCache.OPENTV
		eEPGCache.getInstance().setEpgSources(mask)
	config.epg.eit.addNotifier(EpgSettingsChanged)
	config.epg.mhw.addNotifier(EpgSettingsChanged)
	config.epg.freesat.addNotifier(EpgSettingsChanged)
	config.epg.viasat.addNotifier(EpgSettingsChanged)
	config.epg.netmed.addNotifier(EpgSettingsChanged)
	config.epg.virgin.addNotifier(EpgSettingsChanged)
	config.epg.opentv.addNotifier(EpgSettingsChanged)

	def wdhm(number):
		units = (7 * 24 * 60, 24 * 60, 60, 1)
		for i, d in enumerate(units):
			if unit := int(number / d):
				if i == 3:
					return "%s" % (ngettext("%d minute", "%d minuts", unit) % unit)
				elif i == 2:
					return "%s" % (ngettext("%d hour", "%d hours", unit) % unit)
				elif i == 1:
					return "%s" % (ngettext("%d day", "%d days", unit) % unit)
				else:
					return "%s" % (ngettext("%d week", "%d weeks", unit) % unit)
		return _("0 minutes")
	choices = [(0, _('None'))] + [(i, wdhm(i)) for i in [i * 15 for i in range(1, 4)] + [i * 60 for i in range(1, 9)] + [i * 120 for i in range(5, 12)] + [i * 24 * 60 for i in range(1, 8)]]
	config.epg.histminutes = ConfigSelection(default=0, choices=choices)

	def EpgHistorySecondsChanged(configElement):
		from enigma import eEPGCache
		eEPGCache.getInstance().setEpgHistorySeconds(int(configElement.value) * 60)
	config.epg.histminutes.addNotifier(EpgHistorySecondsChanged)

	config.epg.cacheloadsched = ConfigYesNo(default = False)
	config.epg.cachesavesched = ConfigYesNo(default = False)

	def EpgCacheLoadSchedChanged(configElement):
		import Components.EpgLoadSave
		Components.EpgLoadSave.EpgCacheLoadCheck()

	def EpgCacheSaveSchedChanged(configElement):
		import Components.EpgLoadSave
		Components.EpgLoadSave.EpgCacheSaveCheck()
	config.epg.cacheloadsched.addNotifier(EpgCacheLoadSchedChanged, immediate_feedback = False)
	config.epg.cachesavesched.addNotifier(EpgCacheSaveSchedChanged, immediate_feedback = False)
	config.epg.cacheloadtimer = ConfigSelectionNumber(default = 24, stepwidth = 1, min = 1, max = 24, wraparound = True)
	config.epg.cachesavetimer = ConfigSelectionNumber(default = 24, stepwidth = 1, min = 1, max = 24, wraparound = True)

	if BoxInfo.getItem("AmlogicFamily"):
		from Plugins.SystemPlugins.Videomode.VideoHardware import video_hw
		limits = [int(x) for x in video_hw.getWindowsAxis().split()]
		config.osd.dst_left = ConfigSelectionNumber(default=limits[0], stepwidth=1, min=limits[0] - 255, max=limits[0] + 255, wraparound=False)
		config.osd.dst_top = ConfigSelectionNumber(default=limits[1], stepwidth=1, min=limits[1] - 255, max=limits[1] + 255, wraparound=False)
		config.osd.dst_width = ConfigSelectionNumber(default=limits[2], stepwidth=1, min=limits[2] - 255, max=limits[2] + 255, wraparound=False)
		config.osd.dst_height = ConfigSelectionNumber(default=limits[3], stepwidth=1, min=limits[3] - 255, max=limits[3] + 255, wraparound=False)
	else:
		config.osd.dst_left = ConfigSelectionInteger(default=0, first=0, last=720, step=1, wrap=False)
		config.osd.dst_top = ConfigSelectionInteger(default=0, first=0, last=576, step=1, wrap=False)
		config.osd.dst_width = ConfigSelectionInteger(default=720, first=0, last=720, step=1, wrap=False)
		config.osd.dst_height = ConfigSelectionInteger(default=576, first=0, last=576, step=1, wrap=False)

	config.osd.alpha = ConfigSelectionInteger(default=255, first=0, last=255, step=1, wrap=False)
	config.osd.alpha_teletext = ConfigSelectionInteger(default=255, first=0, last=255, step=1, wrap=False)
	config.osd.alpha_webbrowser = ConfigSelectionInteger(default=255, first=0, last=255, step=1, wrap=False)
	config.osd.threeDmode = ConfigSelection(default="auto", choices=[
		("off", _("Off")),
		("auto", _("Auto")),
		("sidebyside", _("Side by Side")),
		("topandbottom", _("Top and Bottom"))
	])
	config.osd.threeDznorm = ConfigSlider(default=50, increment=1, limits=(0, 100))
	config.osd.show3dextensions = ConfigYesNo(default=False)
	config.osd.threeDsetmode = ConfigSelection(default="mode1", choices=[
		("mode1", _("Mode 1")),
		("mode2", _("Mode 2"))
	])

	hddchoises = [('/etc/enigma2/', 'Internal Flash')]
	for p in harddiskmanager.getMountedPartitions():
		if exists(p.mountpoint):
			d = normpath(p.mountpoint)
			if p.mountpoint != '/':
				hddchoises.append((p.mountpoint, d))
	config.misc.epgcachepath = ConfigSelection(default = '/etc/enigma2/', choices = hddchoises)
	config.misc.epgcachefilename = ConfigText(default='epg', fixed_size=False)
	config.misc.epgcache_filename = ConfigText(default = (config.misc.epgcachepath.value + config.misc.epgcachefilename.value.replace('.dat','') + '.dat'))
	def EpgCacheChanged(configElement):
		config.misc.epgcache_filename.setValue(pathjoin(config.misc.epgcachepath.value, config.misc.epgcachefilename.value.replace('.dat','') + '.dat'))
		config.misc.epgcache_filename.save()
		eEPGCache.getInstance().setCacheFile(config.misc.epgcache_filename.value)
		epgcache = eEPGCache.getInstance()
		epgcache.save()
		if not config.misc.epgcache_filename.value.startswith("/etc/enigma2/"):
			if exists('/etc/enigma2/' + config.misc.epgcachefilename.value.replace('.dat','') + '.dat'):
				os.remove('/etc/enigma2/' + config.misc.epgcachefilename.value.replace('.dat','') + '.dat')
	config.misc.epgcachepath.addNotifier(EpgCacheChanged, immediate_feedback = False)
	config.misc.epgcachefilename.addNotifier(EpgCacheChanged, immediate_feedback = False)

	config.misc.epgratingcountry = ConfigSelection(default="", choices=[("", _("Auto Detect")), ("ETSI", _("Generic")), ("AUS", _("Australia"))])
	config.misc.epggenrecountry = ConfigSelection(default="", choices=[("", _("Auto Detect")), ("ETSI", _("Generic")), ("AUS", _("Australia"))])

	config.misc.showradiopic = ConfigYesNo(default = True)

	choicelist = [("newline", _("new line")), ("2newlines", _("2 new lines")), ("space", _("space")), ("dot", " . "), ("dash", " - "), ("asterisk", " * "), ("nothing", _("nothing"))]
	config.epg.fulldescription_separator = ConfigSelection(default="2newlines", choices=choicelist)
	choicelist = [("no", _("no")), ("nothing", _("omit")), ("space", _("space")), ("dot", ". "), ("dash", " - "), ("asterisk", " * "), ("hashtag", " # ")]
	config.epg.replace_newlines = ConfigSelection(default="no", choices=choicelist)

	config.misc.usegstplaybin3 = ConfigYesNo(default=False)

	config.misc.spinnerPosition = ConfigSequence(default=[50, 50], limits=[(0, 1260), (0, 700)], seperator=",")

	def correctInvalidEPGDataChange(configElement):
		eServiceEvent.setUTF8CorrectMode(int(configElement.value))
	config.epg.correct_invalid_epgdata = ConfigSelection(default="1", choices=[("0", _("Disabled")), ("1", _("Enabled")), ("2", _("Debug"))])
	config.epg.correct_invalid_epgdata.addNotifier(correctInvalidEPGDataChange)

	def setHDDStandby(configElement):
		for hdd in harddiskmanager.HDDList():
			hdd[1].setIdleTime(int(configElement.value))
	config.usage.hdd_standby.addNotifier(setHDDStandby, immediate_feedback=False)

	if BoxInfo.getItem("12V_Output"):
		def set12VOutput(configElement):
			Misc_Options.getInstance().set_12V_output(configElement.value == "on" and 1 or 0)
		config.usage.output_12V.addNotifier(set12VOutput, immediate_feedback=False)

	config.usage.keymap = ConfigText(default=eEnv.resolve("${datadir}/enigma2/keymap.xml"))
	keytranslation = eEnv.resolve("${sysconfdir}/enigma2/keytranslation.xml")
	if not exists(keytranslation):
		keytranslation = eEnv.resolve("${datadir}/enigma2/keytranslation.xml")
	config.usage.keytrans = ConfigText(default=keytranslation)

	# This is already in StartEniga.py.
	# config.crash = ConfigSubsection()

	# Handle python crashes.
	config.crash.bsodpython = ConfigYesNo(default=True)
	config.crash.bsodpython_ready = NoSave(ConfigYesNo(default=False))
	choiceList = [("0", _("Never"))] + [(str(x), str(x)) for x in range(1, 11)]
	config.crash.bsodhide = ConfigSelection(default="0", choices=choiceList)
	config.crash.bsodmax = ConfigSelection(default="3", choices=choiceList)

	config.crash.enabledebug = ConfigYesNo(default=False)
	config.crash.debugLevel = ConfigSelection(default=0, choices=[
		(0, _("Disabled")),
		(4, _("Enabled")),
		(5, _("Verbose"))
	])

	# Migrate old debug
	if config.crash.enabledebug.value:
		config.crash.debugLevel.value = 4
		config.crash.enabledebug.value = False
		config.crash.enabledebug.save()

	config.crash.debugloglimit = ConfigSelectionNumber(min=1, max=10, stepwidth=1, default=4, wraparound=True)
	config.crash.daysloglimit = ConfigSelectionNumber(min=1, max=30, stepwidth=1, default=8, wraparound=True)
	config.crash.sizeloglimit = ConfigSelectionNumber(min=1, max=250, stepwidth=1, default=10, wraparound=True)
	config.crash.lastfulljobtrashtime = ConfigInteger(default=-1)

	# The config.crash.debugTimeFormat item is used to set ENIGMA_DEBUG_TIME environmental variable on enigma2 start from enigma2.sh.
	config.crash.debugTimeFormat = ConfigSelection(default="2", choices=[
		("0", _("None")),
		("1", _("Boot time")),
		("2", _("Local time")),
		("3", _("Boot time and local time")),
		("6", _("Local date/time")),
		("7", _("Boot time and local date/time"))
	])
	config.crash.debugTimeFormat.save_forced = True

	config.crash.gstdebug = ConfigYesNo(default=False)
	config.crash.gstdebugcategory = ConfigSelection(default="*", choices=[
		("*", _("All")),
		("*audio*", _("Audio")),
		("*video*", _("Video"))
	])
	config.crash.gstdebuglevel = ConfigSelection(default="INFO", choices=[
		"none",
		"ERROR",
		"WARNING",
		"FIXME",
		"INFO",
		"DEBUG",
		"LOG",
		"TRACE",
		"MEMDUMP"
	])
	config.crash.gstdot = ConfigYesNo(default=False)

	config.crash.coredump = ConfigYesNo(default=False)

	def updateDebugPath(configElement):
		debugPath = config.crash.debugPath.value
		try:
			makedirs(debugPath, 0o755, exist_ok=True)
		except OSError as err:
			print("[UsageConfig] Error %d: Unable to create log directory '%s'!  (%s)" % (err.errno, debugPath, err.strerror))

	choiceList = [("/home/root/logs/", "/home/root/")]
	for partition in harddiskmanager.getMountedPartitions():
		if exists(partition.mountpoint) and partition.mountpoint != "/":
			choiceList.append((pathjoin(partition.mountpoint, "logs", ""), normpath(partition.mountpoint)))
	config.crash.debugPath = ConfigSelection(default="/home/root/logs/", choices=choiceList)
	config.crash.debugPath.addNotifier(updateDebugPath, immediate_feedback=False)

	crashlogheader = _("We are really sorry. Your receiver encountered "
		"a software problem, and needs to be restarted.\n"
		"Please send the logfile %senigma2_crash_xxxxxx.log to https://github.com/fairbird/enigma2-dreambox.\n"
		"Your receiver restarts in 10 seconds!\n"
		"Component: enigma2") % config.crash.debugPath.value
	config.crash.debug_text = ConfigText(default=crashlogheader, fixed_size=False)
	config.crash.skin_error_crash = ConfigYesNo(default=True)

	def updateStackTracePrinter(configElement):
		from Components.StackTrace import StackTracePrinter
		if configElement.value:
			if (isfile("/tmp/doPythonStackTrace")):
				os.remove("/tmp/doPythonStackTrace")
			from threading import current_thread
			StackTracePrinter.getInstance().activate(current_thread().ident)
		else:
			StackTracePrinter.getInstance().deactivate()

	config.crash.pystackonspinner = ConfigYesNo(default=False)
	config.crash.pystackonspinner.addNotifier(updateStackTracePrinter, immediate_feedback=False, initial_call=True)

	def debugStorageChanged(configElement):
		udevDebugFile = "/etc/udev/udev.debug"
		if configElement.value:
			fileWriteLine(udevDebugFile, "", source=MODULE_NAME)
		elif exists(udevDebugFile):
			unlink(udevDebugFile)
		harddiskmanager.debug = configElement.value

	config.crash.debugStorage.addNotifier(debugStorageChanged)

	config.seek = ConfigSubsection()
	config.seek.selfdefined_13 = ConfigNumber(default=15)
	config.seek.selfdefined_46 = ConfigNumber(default=60)
	config.seek.selfdefined_79 = ConfigNumber(default=300)

	config.seek.speeds_forward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_backward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_slowmotion = ConfigSet(default=[2, 4, 8], choices=[2, 4, 6, 8, 12, 16, 25])

	config.seek.enter_forward = ConfigSelection(default="2", choices=["2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])
	config.seek.enter_backward = ConfigSelection(default="1", choices=["1", "2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])

	config.seek.on_pause = ConfigSelection(default="play", choices=[
		("play", _("Play")),
		("step", _("Single step (GOP)")),
		("last", _("Last speed"))])

	config.usage.timerlist_finished_timer_position = ConfigSelection(default="end", choices=[("beginning", _("At beginning")), ("end", _("At end"))])

	def updateEnterForward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_forward, configElement.value)

	config.seek.speeds_forward.addNotifier(updateEnterForward, immediate_feedback=False)

	def updateEnterBackward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_backward, configElement.value)

	config.seek.speeds_backward.addNotifier(updateEnterBackward, immediate_feedback=False)

	def updateEraseSpeed(el):
		eBackgroundFileEraser.getInstance().setEraseSpeed(int(el.value))

	def updateEraseFlags(el):
		eBackgroundFileEraser.getInstance().setEraseFlags(int(el.value))
	config.misc.erase_speed = ConfigSelection(default="20", choices=[
		("10", _("10 MB/s")),
		("20", _("20 MB/s")),
		("50", _("50 MB/s")),
		("100", _("100 MB/s"))])
	config.misc.erase_speed.addNotifier(updateEraseSpeed, immediate_feedback=False)
	config.misc.erase_flags = ConfigSelection(default="1", choices=[
		("0", _("Disable")),
		("1", _("Internal hdd only")),
		("3", _("Everywhere"))])
	config.misc.erase_flags.addNotifier(updateEraseFlags, immediate_feedback=False)

	config.misc.zapkey_delay = ConfigSelectionNumber(default=5, stepwidth=1, min=0, max=20, wraparound=True)
	config.misc.numzap_picon = ConfigYesNo(default=False)

	if BoxInfo.getItem("ZapMode"):
		def setZapmode(el):
			with open(BoxInfo.getItem("ZapMode"), "w") as fd:
				fd.write(el.value)
		config.misc.zapmode = ConfigSelection(default="mute", choices=[
			("mute", _("Black screen")), ("hold", _("Hold screen")), ("mutetilllock", _("Black screen till locked")), ("holdtilllock", _("Hold till locked"))])
		config.misc.zapmode.addNotifier(setZapmode, immediate_feedback=False)

	config.usage.historymode = ConfigSelection(default='1', choices=[('0', _('Just zap')), ('1', _('Show menu'))])
	config.usage.zapHistorySort = ConfigSelection(default=0, choices=[(0, _("Most recent first")),(1, _("Most recent last"))])

	if not BoxInfo.getItem("ZapMode") and exists("/proc/stb/info/model"):
		def setZapmodeDM(el):
			print('[UsageConfig] >>> zapmodeDM')
		config.misc.zapmodeDM = ConfigSelection(default="black", choices=[("black", _("Black screen")), ("hold", _("Hold screen"))])
		config.misc.zapmodeDM.addNotifier(setZapmodeDM, immediate_feedback = False)

	if BoxInfo.getItem("VFD_scroll_repeats"):
		def scroll_repeats(el):
			with open(BoxInfo.getItem("VFD_scroll_repeats"), "w") as fd:
				fd.write(el.value)
		choicelist = []
		for i in range(1, 11, 1):
			choicelist.append((str(i)))
		config.usage.vfd_scroll_repeats = ConfigSelection(default="3", choices=choicelist)
		config.usage.vfd_scroll_repeats.addNotifier(scroll_repeats, immediate_feedback=False)

	if BoxInfo.getItem("VFD_scroll_delay"):
		def scroll_delay(el):
			with open(BoxInfo.getItem("VFD_scroll_delay"), "w") as fd:
				fd.write(el.value)
		choicelist = []
		for i in range(0, 1001, 50):
			choicelist.append((str(i)))
		config.usage.vfd_scroll_delay = ConfigSelection(default="150", choices=choicelist)
		config.usage.vfd_scroll_delay.addNotifier(scroll_delay, immediate_feedback=False)

	if BoxInfo.getItem("VFD_initial_scroll_delay"):
		def initial_scroll_delay(el):
			with open(BoxInfo.getItem("VFD_initial_scroll_delay"), "w") as fd:
				fd.write(el.value)
		choicelist = []
		for i in range(0, 20001, 500):
			choicelist.append((str(i)))
		config.usage.vfd_initial_scroll_delay = ConfigSelection(default="1000", choices=choicelist)
		config.usage.vfd_initial_scroll_delay.addNotifier(initial_scroll_delay, immediate_feedback=False)

	if BoxInfo.getItem("VFD_final_scroll_delay"):
		def final_scroll_delay(el):
			with open(BoxInfo.getItem("VFD_final_scroll_delay"), "w") as fd:
				fd.write(el.value)
		choicelist = []
		for i in range(0, 20001, 500):
			choicelist.append((str(i)))
		config.usage.vfd_final_scroll_delay = ConfigSelection(default="1000", choices=choicelist)
		config.usage.vfd_final_scroll_delay.addNotifier(final_scroll_delay, immediate_feedback=False)

	def quadpip_mode_notifier(configElement):
		if BoxInfo.getItem("HasQuadpip"):
			open(BoxInfo.getItem("HasQuadpip"), "w").write("mosaic" if configElement.value else "normal")
	config.usage.QuadpipMode = NoSave(ConfigYesNo(default=False))
	config.usage.QuadpipMode.addNotifier(quadpip_mode_notifier)

	if BoxInfo.getItem("HasBypassEdidChecking"):
		def setHasBypassEdidChecking(configElement):
			with open(BoxInfo.getItem("HasBypassEdidChecking"), "w") as fd:
				fd.write("00000001" if configElement.value else "00000000")
		config.av.bypassEdidChecking = ConfigYesNo(default=False)
		config.av.bypassEdidChecking.addNotifier(setHasBypassEdidChecking)

	if BoxInfo.getItem("HasColorspace"):
		def setHaveColorspace(configElement):
			with open(BoxInfo.getItem("HasColorspace"), "w") as fd:
				fd.write(configElement.value)
		if BoxInfo.getItem("HasColorspaceSimple"):
			config.av.hdmicolorspace = ConfigSelection(default="Edid(Auto)", choices={"Edid(Auto)": _("auto"), "Hdmi_Rgb": "RGB", "444": "YCbCr 4:4:4", "422": "YCbCr 4:2:2", "420": "YCbCr 4:2:0"})
		else:
			config.av.hdmicolorspace = ConfigSelection(default="auto", choices={"auto": _("auto"), "rgb": "RGB", "420": "4:2:0", "422": "4:2:2", "444": "4:4:4"})
		config.av.hdmicolorspace.addNotifier(setHaveColorspace)

	if BoxInfo.getItem("HasColordepth"):
		def setHaveColordepth(configElement):
			with open(BoxInfo.getItem("HasColordepth"), "w") as fd:
				fd.write(configElement.value)
		config.av.hdmicolordepth = ConfigSelection(default="auto", choices={"auto": _("auto"), "8bit": "8bit", "10bit": "10bit", "12bit": "12bit"})
		config.av.hdmicolordepth.addNotifier(setHaveColordepth)

	if BoxInfo.getItem("HasHDMIpreemphasis"):
		def setHDMIpreemphasis(configElement):
			with open(BoxInfo.getItem("HasHDMIpreemphasis"), "w") as fd:
				fd.write("on" if configElement.value else "off")
		config.av.hdmipreemphasis = ConfigYesNo(default=False)
		config.av.hdmipreemphasis.addNotifier(setHDMIpreemphasis)

	if BoxInfo.getItem("HasColorimetry"):
		def setColorimetry(configElement):
			with open(BoxInfo.getItem("HasColorimetry"), "w") as fd:
				fd.write(configElement.value)
		config.av.hdmicolorimetry = ConfigSelection(default="auto", choices=[("auto", _("auto")), ("bt2020ncl", "BT 2020 NCL"), ("bt2020cl", "BT 2020 CL"), ("bt709", "BT 709")])
		config.av.hdmicolorimetry.addNotifier(setColorimetry)

	if BoxInfo.getItem("HasHdrType"):
		def setHdmiHdrType(configElement):
			with open(BoxInfo.getItem("HasHdrType"), "w") as fd:
				fd.write(configElement.value)
		config.av.hdmihdrtype = ConfigSelection(default="auto", choices={"auto": _("auto"), "none": "SDR", "hdr10": "HDR10", "hlg": "HLG", "dolby": "Dolby Vision"})
		config.av.hdmihdrtype.addNotifier(setHdmiHdrType)

	if BoxInfo.getItem("HDRSupport"):
		def setHlgSupport(configElement):
			with open("/proc/stb/hdmi/hlg_support", "w") as fd:
				fd.write(configElement.value)
		config.av.hlg_support = ConfigSelection(default="auto(EDID)",
			choices=[("auto(EDID)", _("controlled by HDMI")), ("yes", _("force enabled")), ("no", _("force disabled"))])
		config.av.hlg_support.addNotifier(setHlgSupport)

		def setHdr10Support(configElement):
			with open("/proc/stb/hdmi/hdr10_support", "w") as fd:
				fd.write(configElement.value)
		config.av.hdr10_support = ConfigSelection(default="auto(EDID)",
			choices=[("auto(EDID)", _("controlled by HDMI")), ("yes", _("force enabled")), ("no", _("force disabled"))])
		config.av.hdr10_support.addNotifier(setHdr10Support)

		def setDisable12Bit(configElement):
			with open("/proc/stb/video/disable_12bit", "w") as fd:
				fd.write("on" if configElement.value else "off")
		config.av.allow_12bit = ConfigYesNo(default=False)
		config.av.allow_12bit.addNotifier(setDisable12Bit)

		def setDisable10Bit(configElement):
			with open("/proc/stb/video/disable_10bit", "w") as fd:
				fd.write("on" if configElement.value else "off")
		config.av.allow_10bit = ConfigYesNo(default=False)
		config.av.allow_10bit.addNotifier(setDisable10Bit)

	if BoxInfo.getItem("CanSyncMode"):
		def setSyncMode(configElement):
			print("[UsageConfig] Read /proc/stb/video/sync_mode")
			with open("/proc/stb/video/sync_mode", "w") as fd:
				fd.write(configElement.value)
		config.av.sync_mode = ConfigSelection(default="slow", choices={
			"slow": _("Slow motion"),
			"hold": _("Hold first frame"),
			"black": _("Black screen")
		})
		config.av.sync_mode.addNotifier(setSyncMode)

	config.subtitles = ConfigSubsection()

	config.subtitles.show = ConfigYesNo(default=True)

	def setTTXSubtitleColors(configElement):
		eSubtitleSettings.setTTXSubtitleColors(configElement.value)

	config.subtitles.ttx_subtitle_colors = ConfigSelection(default=1, choices=[
		(0, _("Original")),
		(1, _("White")),
		(2, _("Yellow"))
	])
	config.subtitles.ttx_subtitle_colors.addNotifier(setTTXSubtitleColors)

	def setTTXSubtitleOriginalPosition(configElement):
		eSubtitleSettings.setTTXSubtitleOriginalPosition(configElement.value)

	config.subtitles.ttx_subtitle_original_position = ConfigYesNo(default=False)
	config.subtitles.ttx_subtitle_original_position.addNotifier(setTTXSubtitleOriginalPosition)

	def setSubtitlePosition(configElement):
		eSubtitleSettings.setSubtitlePosition(configElement.value)

	config.subtitles.subtitle_position = ConfigSelection(default=50, choices=[(x, _("%d Pixels") % x) for x in list(range(0, 91, 10)) + list(range(100, 451, 50))])
	config.subtitles.subtitle_position.addNotifier(setSubtitlePosition)

	def setSubtitleAligment(configElement):
		aligments = {
			"left": 1,
			"center": 4,
			"right": 2
		}
		eSubtitleSettings.setSubtitleAligment(aligments.get(configElement.value, 4))

	config.subtitles.subtitle_alignment = ConfigSelection(default="center", choices=[
		("left", _("Left")),
		("center", _("Center")),
		("right", _("Right"))
	])
	config.subtitles.subtitle_alignment.addNotifier(setSubtitleAligment)

	def setSubtitleReWrap(configElement):
		eSubtitleSettings.setSubtitleReWrap(configElement.value)

	config.subtitles.subtitle_rewrap = ConfigYesNo(default=False)
	config.subtitles.subtitle_rewrap.addNotifier(setSubtitleReWrap)

	def setSubtitleColoriseDialogs(configElement):
		eSubtitleSettings.setSubtitleColoriseDialogs(configElement.value)

	config.subtitles.colourise_dialogs = ConfigYesNo(default=False)
	config.subtitles.colourise_dialogs.addNotifier(setSubtitleColoriseDialogs)

	def setSubtitleBorderWith(configElement):
		eSubtitleSettings.setSubtitleBorderWith(configElement.value)

	config.subtitles.subtitle_borderwidth = ConfigSelection(default=3, choices=[(x, str(x)) for x in range(1, 6)])
	config.subtitles.subtitle_borderwidth.addNotifier(setSubtitleBorderWith)

	def setSubtitleFontSize(configElement):
		eSubtitleSettings.setSubtitleFontSize(configElement.value)

	config.subtitles.subtitle_fontsize = ConfigSelection(default=40, choices=[(x, str(x)) for x in range(16, 101) if not x % 2])
	config.subtitles.subtitle_fontsize.addNotifier(setSubtitleFontSize)

	def setSubtitleBacktrans(configElement):
		eSubtitleSettings.setSubtitleBacktrans(configElement.value)

	choiceList = [
		(0, _("No transparency")),
		(12, "5%"),
		(25, "10%"),
		(38, "15%"),
		(50, "20%"),
		(75, "30%"),
		(100, "40%"),
		(125, "50%"),
		(150, "60%"),
		(175, "70%"),
		(200, "80%"),
		(225, "90%"),
		(255, _("Full transparency"))]
	config.subtitles.subtitles_backtrans = ConfigSelection(default=255, choices=choiceList)
	config.subtitles.subtitles_backtrans.addNotifier(setSubtitleBacktrans)

	def setDVBSubtitleBacktrans(configElement):
		eSubtitleSettings.setDVBSubtitleBacktrans(configElement.value)

	config.subtitles.dvb_subtitles_backtrans = ConfigSelection(default=0, choices=choiceList)
	config.subtitles.dvb_subtitles_backtrans.addNotifier(setDVBSubtitleBacktrans)

	choiceList = []
	for x in range(-54000000, 54045000, 45000):
		if x == 0:
			choiceList.append((0, _("No delay")))
		else:
			choiceList.append((x, _("%2.1f Seconds") % (x / 90000.0)))

	def setSubtitleNoPTSDelay(configElement):
		eSubtitleSettings.setSubtitleNoPTSDelay(configElement.value)

	config.subtitles.subtitle_noPTSrecordingdelay = ConfigSelection(default=315000, choices=choiceList)
	config.subtitles.subtitle_noPTSrecordingdelay.addNotifier(setSubtitleNoPTSDelay)

	def setSubtitleBadTimingDelay(configElement):
		eSubtitleSettings.setSubtitleBadTimingDelay(configElement.value)

	config.subtitles.subtitle_bad_timing_delay = ConfigSelection(default=0, choices=choiceList)
	config.subtitles.subtitle_bad_timing_delay.addNotifier(setSubtitleBadTimingDelay)

	def setPangoSubtitleDelay(configElement):
		eSubtitleSettings.setPangoSubtitleDelay(configElement.value)

	config.subtitles.pango_subtitles_delay = ConfigSelection(default=0, choices=choiceList)
	config.subtitles.pango_subtitles_delay.addNotifier(setPangoSubtitleDelay)

	def setDVBSubtitleColor(configElement):
		eSubtitleSettings.setDVBSubtitleColor(configElement.value)

	config.subtitles.dvb_subtitles_color = ConfigSelection(default=0, choices=[(0, _("Original")), (1, _("Yellow")), (2, _("Green")), (3, _("Magenta")), (4, _("Cyan"))])
	config.subtitles.dvb_subtitles_color.addNotifier(setDVBSubtitleColor)

	def setDVBSubtitleOriginalPosition(configElement):
		eSubtitleSettings.setDVBSubtitleOriginalPosition(configElement.value)

	config.subtitles.dvb_subtitles_original_position = ConfigSelection(default=0, choices=[
		(0, _("Original")),
		(1, _("Fixed")),
		(2, _("Relative"))
	])
	config.subtitles.dvb_subtitles_original_position.addNotifier(setDVBSubtitleOriginalPosition)

	def setDVBSubtitleCentered(configElement):
		eSubtitleSettings.setDVBSubtitleCentered(configElement.value)

	config.subtitles.dvb_subtitles_centered = ConfigYesNo(default=False)
	config.subtitles.dvb_subtitles_centered.addNotifier(setDVBSubtitleCentered)

	def setPangoSubtitleColors(configElement):
		eSubtitleSettings.setPangoSubtitleColors(configElement.value)

	config.subtitles.pango_subtitle_colors = ConfigSelection(default=1, choices=[
		(0, _("Alternative")),
		(1, _("White")),
		(2, _("Yellow"))
	])
	config.subtitles.pango_subtitle_colors.addNotifier(setPangoSubtitleColors)

	def setPangoSubtitleFontWitch(configElement):
		eSubtitleSettings.setPangoSubtitleFontWitch(configElement.value)

	config.subtitles.pango_subtitle_fontswitch = ConfigYesNo(default=True)
	config.subtitles.pango_subtitle_fontswitch.addNotifier(setPangoSubtitleFontWitch)

	def setPangoSubtitleFPS(configElement):
		eSubtitleSettings.setPangoSubtitleFPS(configElement.value)

	config.subtitles.pango_subtitles_fps = ConfigSelection(default=1, choices=[
		(1, _("Original")),
		(23976, "23.976"),
		(24000, "24"),
		(25000, "25"),
		(29970, "29.97"),
		(30000, "30")
	])
	config.subtitles.pango_subtitles_fps.addNotifier(setPangoSubtitleFPS)

	def setPangoSubtitleRemovehi(configElement):
		eSubtitleSettings.setPangoSubtitleRemovehi(configElement.value)

	config.subtitles.pango_subtitle_removehi = ConfigYesNo(default=False)
	config.subtitles.pango_subtitle_removehi.addNotifier(setPangoSubtitleRemovehi)

	def setPangoSubtitleAutoRun(configElement):
		eSubtitleSettings.setPangoSubtitleAutoRun(configElement.value)

	config.subtitles.pango_autoturnon = ConfigYesNo(default=True)
	config.subtitles.pango_autoturnon.addNotifier(setPangoSubtitleAutoRun)

	# AI start
	def setAiEnabled(configElement):
		eSubtitleSettings.setAiEnabled(configElement.value)

	config.subtitles.ai_enabled = ConfigYesNo(default=False)
	config.subtitles.ai_enabled.addNotifier(setAiEnabled)

	def setAiSubscriptionCode(configElement):
		eSubtitleSettings.setAiSubscriptionCode(str(configElement.value))

	config.subtitles.ai_subscription_code = ConfigNumber(default=15)
	config.subtitles.ai_subscription_code.addNotifier(setAiSubscriptionCode)

	def setAiSubtitleColors(configElement):
		eSubtitleSettings.setAiSubtitleColors(configElement.value)

	config.subtitles.ai_subtitle_colors = ConfigSelection(default=1, choices=[
		(1, _("White")),
		(2, _("Yellow")),
		(3, _("Red")),
		(4, _("Green")),
		(5, _("Blue"))
	])
	config.subtitles.ai_subtitle_colors.addNotifier(setAiSubtitleColors)

	def setAiConnectionSpeed(configElement):
		eSubtitleSettings.setAiConnectionSpeed(configElement.value)

	config.subtitles.ai_connection_speed = ConfigSelection(default=1, choices=[
		(1, _("Up to 50 Mbps")),
		(2, _("50-200 Mbps")),
		(3, _("Above 200 Mbps"))
	])
	config.subtitles.ai_connection_speed.addNotifier(setAiConnectionSpeed)

	langsAI = ['af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca', 'zh', 'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo', 'fr', 'fi', 'fy', 'gl', 'ka', 'de', 'el', 'ht', 'ha', 'hu', 'is', 'ig', 'ga', 'it', 'ja', 'jv', 'kn', 'kk', 'km', 'rw', 'ko', 'ku', 'ky', 'lo', 'la', 'lv', 'lt', 'lb', 'mk', 'mg', 'ms', 'mt', 'mi', 'mr', 'mn', 'no', 'ny', 'or', 'ps', 'fa', 'pl', 'pt', 'ro', 'ru', 'sm', 'gd', 'sr', 'st', 'sn', 'sk', 'sl', 'so', 'es', 'su', 'sw', 'sv', 'tl', 'tg', 'te', 'th', 'tr', 'tk', 'uk', 'ur', 'ug', 'uz', 'cy', 'xh', 'yi', 'yo', 'zu']
	langsAI = [(x, international.LANGUAGE_DATA[x][1]) for x in langsAI]
	langsAI.append(("zh-CN", _("Chinese (Simplified)")))
	langsAI.append(("ceb", _("Cebuano")))
	langsAI.append(("haw", _("Hawaiian")))
	langsAI.append(("iw", _("Hebrew")))
	langsAI.append(("hmn", _("Hmong")))
	langsAI.append(("ar_eg", _("Arabic (Egyptian)")))
	langsAI.append(("ar_ma", _("Arabic (Moroccan)")))
	langsAI.append(("ar_sy", _("Arabic (Syro-Lebanese)")))
	langsAI.append(("ar_tn", _("Arabic (Tunisian)")))
	langsAI.sort(key=lambda x: x[1])

	default = config.misc.locale.value
	default = default.split("_")[0] if "_" in default else default
	if default == "zh":
		default = "zh-CN"
	if default not in [x[0] for x in langsAI]:
		default = "en"

	def setAiTranslateTo(configElement):
		eSubtitleSettings.setAiTranslateTo(configElement.value)

	config.subtitles.ai_translate_to = ConfigSelection(default=default, choices=langsAI)
	config.subtitles.ai_translate_to.addNotifier(setAiTranslateTo)
	# AI end

	config.autolanguage = ConfigSubsection()
	languageChoiceList = [
		("", _("None")),
		("und", _("Undetermined")),
		(originalAudioTracks, _("Original")),
		("ara", _("Arabic")),
		("eus baq", _("Basque")),
		("bul", _("Bulgarian")),
		("hrv", _("Croatian")),
		("chn sgp", _("Simplified Chinese")),
		("twn hkn", _("Traditional Chinese")),
		("ces cze", _("Czech")),
		("dan", _("Danish")),
		("dut ndl nld Dutch", _("Dutch")),
		("eng Englisch", _("English")),
		("est", _("Estonian")),
		("fin", _("Finnish")),
		("fra fre", _("French")),
		("deu ger", _("German")),
		("ell gre grc", _("Greek")),
		("heb", _("Hebrew")),
		("hun", _("Hungarian")),
		("ind", _("Indonesian")),
		("ita", _("Italian")),
		("lav", _("Latvian")),
		("lit", _("Lithuanian")),
		("ltz", _("Luxembourgish")),
		("nor", _("Norwegian")),
		("pol", _("Polish")),
		("por dub Dub DUB ud1 LEG", _("Portuguese")),
		("fas per fa pes", _("Persian")),
		("ron rum", _("Romanian")),
		("rus", _("Russian")),
		("srp scc", _("Serbian")),
		("slk slo", _("Slovak")),
		("slv", _("Slovenian")),
		("spa", _("Spanish")),
		("swe", _("Swedish")),
		("tha", _("Thai")),
		("tur Audio_TUR", _("Turkish")),
		("ukr Ukr", _("Ukrainian")),
		(visuallyImpairedCommentary, _("Visual impaired commentary"))
	]
	epgChoiceList = languageChoiceList[:1] + languageChoiceList[2:]
	subtitleChoiceList = languageChoiceList[:1] + languageChoiceList[2:]

	def setEpgLanguage(configElement):
		eServiceEvent.setEPGLanguage(configElement.value)

	def setEpgLanguageAlternative(configElement):
		eServiceEvent.setEPGLanguageAlternative(configElement.value)

	def epglanguage(configElement):
		config.autolanguage.audio_epglanguage.setChoices([x for x in epgChoiceList if x[0] and x[0] != config.autolanguage.audio_epglanguage_alternative.value or not x[0] and not config.autolanguage.audio_epglanguage_alternative.value])
		config.autolanguage.audio_epglanguage_alternative.setChoices([x for x in epgChoiceList if x[0] and x[0] != config.autolanguage.audio_epglanguage.value or not x[0]])
	config.autolanguage.audio_epglanguage = ConfigSelection(default="", choices=epgChoiceList)
	config.autolanguage.audio_epglanguage_alternative = ConfigSelection(default="", choices=epgChoiceList)
	config.autolanguage.audio_epglanguage.addNotifier(setEpgLanguage)
	config.autolanguage.audio_epglanguage.addNotifier(epglanguage, initial_call=False)
	config.autolanguage.audio_epglanguage_alternative.addNotifier(setEpgLanguageAlternative)
	config.autolanguage.audio_epglanguage_alternative.addNotifier(epglanguage)

	def getselectedlanguages(range):
		return [eval("config.autolanguage.audio_autoselect%x.value" % x) for x in range]

	def autolanguage(configElement):
		config.autolanguage.audio_autoselect1.setChoices([x for x in languageChoiceList if x[0] and x[0] not in getselectedlanguages((2, 3, 4)) or not x[0] and not config.autolanguage.audio_autoselect2.value])
		config.autolanguage.audio_autoselect2.setChoices([x for x in languageChoiceList if x[0] and x[0] not in getselectedlanguages((1, 3, 4)) or not x[0] and not config.autolanguage.audio_autoselect3.value])
		config.autolanguage.audio_autoselect3.setChoices([x for x in languageChoiceList if x[0] and x[0] not in getselectedlanguages((1, 2, 4)) or not x[0] and not config.autolanguage.audio_autoselect4.value])
		config.autolanguage.audio_autoselect4.setChoices([x for x in languageChoiceList if x[0] and x[0] not in getselectedlanguages((1, 2, 3)) or not x[0]])
		eSettings.setAudioLanguages(config.autolanguage.audio_autoselect1.value, config.autolanguage.audio_autoselect2.value, config.autolanguage.audio_autoselect3.value, config.autolanguage.audio_autoselect4.value)

	config.autolanguage.audio_autoselect1 = ConfigSelection(default="", choices=languageChoiceList)
	config.autolanguage.audio_autoselect2 = ConfigSelection(default="", choices=languageChoiceList)
	config.autolanguage.audio_autoselect3 = ConfigSelection(default="", choices=languageChoiceList)
	config.autolanguage.audio_autoselect4 = ConfigSelection(default="", choices=languageChoiceList)
	config.autolanguage.audio_autoselect1.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect2.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect3.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect4.addNotifier(autolanguage)

	def setAudioDefaultAC3(configElement):
		eSettings.setAudioDefaultAC3(configElement.value)

	config.autolanguage.audio_defaultac3 = ConfigYesNo(default=False)
	config.autolanguage.audio_defaultac3.addNotifier(setAudioDefaultAC3)

	def setAudioDefaultDDP(configElement):
		eSettings.setAudioDefaultDDP(configElement.value)

	config.autolanguage.audio_defaultddp = ConfigYesNo(default=False)
	config.autolanguage.audio_defaultddp.addNotifier(setAudioDefaultDDP)

	def setAudioUseCache(configElement):
		eSettings.setAudioUseCache(configElement.value)

	config.autolanguage.audio_usecache = ConfigYesNo(default=True)
	config.autolanguage.audio_usecache.addNotifier(setAudioUseCache)

	def getselectedsublanguages(range):
		return [eval("config.autolanguage.subtitle_autoselect%x.value" % x) for x in range]

	def autolanguagesub(configElement):
		config.autolanguage.subtitle_autoselect1.setChoices([x for x in subtitleChoiceList if x[0] and x[0] not in getselectedsublanguages((2, 3, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect2.value])
		config.autolanguage.subtitle_autoselect2.setChoices([x for x in subtitleChoiceList if x[0] and x[0] not in getselectedsublanguages((1, 3, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect3.value])
		config.autolanguage.subtitle_autoselect3.setChoices([x for x in subtitleChoiceList if x[0] and x[0] not in getselectedsublanguages((1, 2, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect4.value])
		config.autolanguage.subtitle_autoselect4.setChoices([x for x in subtitleChoiceList if x[0] and x[0] not in getselectedsublanguages((1, 2, 3)) or not x[0]])
		choiceList = [(0, _("None"))]
		for y in list(range(1, 15 if config.autolanguage.subtitle_autoselect4.value else (7 if config.autolanguage.subtitle_autoselect3.value else (4 if config.autolanguage.subtitle_autoselect2.value else (2 if config.autolanguage.subtitle_autoselect1.value else 0))))):
			choiceList.append((y, ", ".join([eval("config.autolanguage.subtitle_autoselect%x.getText()" % x) for x in (y & 1, y & 2, y & 4 and 3, y & 8 and 4) if x])))
		if config.autolanguage.subtitle_autoselect3.value:
			choiceList.append((y + 1, _("All")))
		config.autolanguage.equal_languages.setChoices(default=0, choices=choiceList)
		eSubtitleSettings.setSubtitleLanguages(config.autolanguage.subtitle_autoselect1.value, config.autolanguage.subtitle_autoselect2.value, config.autolanguage.subtitle_autoselect3.value, config.autolanguage.subtitle_autoselect4.value)

	def setSubtitleEqualLanguages(configElement):
		eSubtitleSettings.setSubtitleEqualLanguages(configElement.value)

	config.autolanguage.equal_languages = ConfigSelection(default=0, choices=[x for x in range(0, 16)])
	config.autolanguage.equal_languages.addNotifier(setSubtitleEqualLanguages)
	config.autolanguage.subtitle_autoselect1 = ConfigSelection(default="", choices=subtitleChoiceList)
	config.autolanguage.subtitle_autoselect2 = ConfigSelection(default="", choices=subtitleChoiceList)
	config.autolanguage.subtitle_autoselect3 = ConfigSelection(default="", choices=subtitleChoiceList)
	config.autolanguage.subtitle_autoselect4 = ConfigSelection(default="", choices=subtitleChoiceList)
	config.autolanguage.subtitle_autoselect1.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect2.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect3.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect4.addNotifier(autolanguagesub)

	def setSubtitleHearingImpaired(configElement):
		eSubtitleSettings.setSubtitleHearingImpaired(configElement.value)
	config.autolanguage.subtitle_hearingimpaired = ConfigYesNo(default=False)
	config.autolanguage.subtitle_hearingimpaired.addNotifier(setSubtitleHearingImpaired)

	def setSubtitleDefaultImpaired(configElement):
		eSubtitleSettings.setSubtitleDefaultImpaired(configElement.value)
	config.autolanguage.subtitle_defaultimpaired = ConfigYesNo(default=False)
	config.autolanguage.subtitle_defaultimpaired.addNotifier(setSubtitleDefaultImpaired)

	def setSubtitleDefaultDVB(configElement):
		eSubtitleSettings.setSubtitleDefaultDVB(configElement.value)
	config.autolanguage.subtitle_defaultdvb = ConfigYesNo(default=False)
	config.autolanguage.subtitle_defaultdvb.addNotifier(setSubtitleDefaultDVB)

	def setSubtitleUseCache(configElement):
		eSubtitleSettings.setSubtitleUseCache(configElement.value)
	config.autolanguage.subtitle_usecache = ConfigYesNo(default=True)
	config.autolanguage.subtitle_usecache.addNotifier(setSubtitleUseCache)

	config.oscaminfo = ConfigSubsection()
	if BoxInfo.getItem("OScamInstalled") or BoxInfo.getItem("NCamInstalled"):
		config.oscaminfo.showInExtensions = ConfigYesNo(default=True)
	else:
		config.oscaminfo.showInExtensions = ConfigYesNo(default=False)
	config.oscaminfo.userDataFromConf = ConfigYesNo(default=True)
	config.oscaminfo.username = ConfigText(default="username", fixed_size=False, visible_width=12)
	config.oscaminfo.password = ConfigPassword(default="password", fixed_size=False)
	config.oscaminfo.ip = ConfigText(default="127.0.0.1", fixed_size=False)
	config.oscaminfo.port = ConfigInteger(default=83, limits=(0, 65536))
	config.oscaminfo.usessl = ConfigYesNo(default=False)
	config.oscaminfo.verifycert = ConfigYesNo(default=False)
	choiceList = [
		(0, _("Disabled"))
	] + [(x, ngettext("%d Second", "%d Seconds", x) % x) for x in (2, 5, 10, 20, 30)] + [(x * 60, ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 2, 3)]
	config.oscaminfo.autoUpdate = ConfigSelection(default=10, choices=choiceList)
	choiceList = [
		(0, _("Disabled"))
	] + [(x, ngettext("%d Second", "%d Seconds", x) % x) for x in (2, 5, 10, 20, 30)] + [(x * 60, ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 2, 3)]
	config.oscaminfo.autoUpdateLog = ConfigSelection(default=0, choices=choiceList)

	config.streaming = ConfigSubsection()
	config.streaming.stream_ecm = ConfigYesNo(default=False)
	config.streaming.descramble = ConfigYesNo(default=True)
	config.streaming.descramble_client = ConfigYesNo(default=False)
	config.streaming.stream_eit = ConfigYesNo(default=True)
	config.streaming.stream_ait = ConfigYesNo(default=True)
	config.streaming.authentication = ConfigYesNo(default=False)

	config.mediaplayer = ConfigSubsection()
	config.mediaplayer.useAlternateUserAgent = ConfigYesNo(default=False)
	config.mediaplayer.alternateUserAgent = ConfigText(default="")

	config.misc.softcam_setup = ConfigSubsection()
	config.misc.softcam_setup.extension_menu = ConfigYesNo(default=True)
	config.misc.softcam_streamrelay_url = ConfigIP(default=[127, 0, 0, 1], auto_jump=True)
	config.misc.softcam_streamrelay_port = ConfigInteger(default=17999, limits=(0, 65535))
	config.misc.softcam_streamrelay_delay = ConfigSelectionNumber(min=0, max=2000, stepwidth=50, default=0, wraparound=True)
	config.misc.softcam_hideServerName = ConfigYesNo(default=False)

	config.logmanager = ConfigSubsection()
	config.logmanager.showinextensions = ConfigYesNo(default=False)
	config.logmanager.user = ConfigText(default='', fixed_size=False)
	config.logmanager.useremail = ConfigText(default='', fixed_size=False)
	config.logmanager.usersendcopy = ConfigYesNo(default=True)
	config.logmanager.path = ConfigText(default="/")
	config.logmanager.additionalinfo = NoSave(ConfigText(default=""))
	config.logmanager.sentfiles = ConfigLocations(default='')

	config.misc.useNTPminutes = ConfigSelection(default="30", choices=[("30", _("%d Minutes") % 30), ("60", _("%d Hour") % 1), ("1440", _("%d Hours") % 24)])

def updateChoices(sel, choices):
	if choices:
		defval = None
		val = int(sel.value)
		if not val in choices:
			tmp = choices[:]
			tmp.reverse()
			for x in tmp:
				if x < val:
					defval = str(x)
					break
		sel.setChoices(list(map(str, choices)), defval)


def preferredPath(path):
	if config.usage.setup_level.index < 2 or path == "<default>" or not path:
		return None  # config.usage.default_path.value, but delay lookup until usage
	elif path == "<current>":
		return config.movielist.last_videodir.value
	elif path == "<timer>":
		return config.movielist.last_timer_videodir.value
	else:
		return path


def preferredTimerPath():
	return preferredPath(config.usage.timer_path.value)


def preferredInstantRecordPath():
	return preferredPath(config.usage.instantrec_path.value)


def defaultMoviePath():
	return defaultRecordingLocation(config.usage.default_path.value)


def showrotorpositionChoicesUpdate(update=False):
	choiceslist = [("no", _("no")), ("yes", _("yes")), ("withtext", _("with text")), ("tunername", _("with tuner name"))]
	count = 0
	for x in nimmanager.nim_slots:
		if nimmanager.getRotorSatListForNim(x.slot, only_first=True):
			choiceslist.append((str(x.slot), x.getSlotName() + _(" (auto detection)")))
			count += 1
	if count > 1:
		choiceslist.append(("all", _("all tuners") + _(" (auto detection)")))
		choiceslist.remove(("tunername", _("with tuner name")))
	if not update:
		config.misc.showrotorposition = ConfigSelection(default="no", choices=choiceslist)
	else:
		config.misc.showrotorposition.setChoices(choiceslist, "no")
	BoxInfo.setItem("isRotorTuner", count > 0)


def preferredTunerChoicesUpdate(update=False):
	dvbs_nims = [("-2", _("disabled"))]
	dvbt_nims = [("-2", _("disabled"))]
	dvbc_nims = [("-2", _("disabled"))]
	atsc_nims = [("-2", _("disabled"))]

	nims = [("-1", _("auto"))]
	for slot in nimmanager.nim_slots:
		if hasattr(slot.config, "configMode") and slot.config.configMode.value == "nothing":
			continue
		if slot.isCompatible("DVB-S"):
			dvbs_nims.append((str(slot.slot), slot.getSlotName()))
		elif slot.isCompatible("DVB-T"):
			dvbt_nims.append((str(slot.slot), slot.getSlotName()))
		elif slot.isCompatible("DVB-C"):
			dvbc_nims.append((str(slot.slot), slot.getSlotName()))
		elif slot.isCompatible("ATSC"):
			atsc_nims.append((str(slot.slot), slot.getSlotName()))
		nims.append((str(slot.slot), slot.getSlotName()))

	config.usage.menutype = ConfigSelection(default="standard", choices=[
		("horzanim", _("Horizontal menu")),
		("horzicon", _("Horizontal icons")),
		("standard", _("Standard menu"))
	])

	if not update:
		config.usage.frontend_priority = ConfigSelection(default="-1", choices=list(nims))
	else:
		config.usage.frontend_priority.setChoices(list(nims), "-1")
	nims.insert(0, ("-2", _("disabled")))
	if not update:
		config.usage.recording_frontend_priority = ConfigSelection(default="-2", choices=nims)
	else:
		config.usage.recording_frontend_priority.setChoices(nims, "-2")
	if not update:
		config.usage.frontend_priority_dvbs = ConfigSelection(default="-2", choices=list(dvbs_nims))
	else:
		config.usage.frontend_priority_dvbs.setChoices(list(dvbs_nims), "-2")
	dvbs_nims.insert(1, ("-1", _("auto")))
	if not update:
		config.usage.recording_frontend_priority_dvbs = ConfigSelection(default="-2", choices=dvbs_nims)
	else:
		config.usage.recording_frontend_priority_dvbs.setChoices(dvbs_nims, "-2")
	if not update:
		config.usage.frontend_priority_dvbt = ConfigSelection(default="-2", choices=list(dvbt_nims))
	else:
		config.usage.frontend_priority_dvbt.setChoices(list(dvbt_nims), "-2")
	dvbt_nims.insert(1, ("-1", _("auto")))
	if not update:
		config.usage.recording_frontend_priority_dvbt = ConfigSelection(default="-2", choices=dvbt_nims)
	else:
		config.usage.recording_frontend_priority_dvbt.setChoices(dvbt_nims, "-2")
	if not update:
		config.usage.frontend_priority_dvbc = ConfigSelection(default="-2", choices=list(dvbc_nims))
	else:
		config.usage.frontend_priority_dvbc.setChoices(list(dvbc_nims), "-2")
	dvbc_nims.insert(1, ("-1", _("auto")))
	if not update:
		config.usage.recording_frontend_priority_dvbc = ConfigSelection(default="-2", choices=dvbc_nims)
	else:
		config.usage.recording_frontend_priority_dvbc.setChoices(dvbc_nims, "-2")
	if not update:
		config.usage.frontend_priority_atsc = ConfigSelection(default="-2", choices=list(atsc_nims))
	else:
		config.usage.frontend_priority_atsc.setChoices(list(atsc_nims), "-2")
	atsc_nims.insert(1, ("-1", _("auto")))
	if not update:
		config.usage.recording_frontend_priority_atsc = ConfigSelection(default="-2", choices=atsc_nims)
	else:
		config.usage.recording_frontend_priority_atsc.setChoices(atsc_nims, "-2")

	BoxInfo.setItem("DVB-S_priority_tuner_available", len(dvbs_nims) > 3 and any(len(i) > 2 for i in (dvbt_nims, dvbc_nims, atsc_nims)))
	BoxInfo.setItem("DVB-T_priority_tuner_available", len(dvbt_nims) > 3 and any(len(i) > 2 for i in (dvbs_nims, dvbc_nims, atsc_nims)))
	BoxInfo.setItem("DVB-C_priority_tuner_available", len(dvbc_nims) > 3 and any(len(i) > 2 for i in (dvbs_nims, dvbt_nims, atsc_nims)))
	BoxInfo.setItem("ATSC_priority_tuner_available", len(atsc_nims) > 3 and any(len(i) > 2 for i in (dvbs_nims, dvbc_nims, dvbt_nims)))


def dropEPGNewLines(text):
	if config.epg.replace_newlines.value != "no":
		text = text.replace('\x0a', replaceEPGSeparator(config.epg.replace_newlines.value))
	return text


def replaceEPGSeparator(code):
	return {"newline": "\n", "2newlines": "\n\n", "space": " ", "dash": " - ", "dot": " . ", "asterisk": " * ", "hashtag": " # ", "nothing": ""}.get(code)
