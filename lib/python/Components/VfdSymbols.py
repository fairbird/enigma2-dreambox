# -*- coding: utf-8 -*-
from twisted.internet import threads
from Components.config import config
from enigma import eTimer, iPlayableService, iServiceInformation
import NavigationInstance
from Tools.Directories import fileExists
from Components.ParentalControl import parentalControl
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import SystemInfo
from Tools.HardwareInfo import HardwareInfo
from time import time, sleep


POLLTIME = 5 # seconds


def SymbolsCheck(session, **kwargs):
		global symbolspoller, POLLTIME
		if SystemInfo["VFDSymbol"]:
			POLLTIME = 1
		symbolspoller = SymbolsCheckPoller(session)
		symbolspoller.start()


class SymbolsCheckPoller:
	def __init__(self, session):
		self.session = session
		self.blink = False
		self.led = "0"
		self.timer = eTimer()
		self.onClose = []
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
			})

	def __onClose(self):
		pass

	def start(self):
		if self.symbolscheck not in self.timer.callback:
			self.timer.callback.append(self.symbolscheck)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.symbolscheck in self.timer.callback:
			self.timer.callback.remove(self.symbolscheck)
		self.timer.stop()

	def symbolscheck(self):
		threads.deferToThread(self.JobTask)
		self.timer.startLongTimer(POLLTIME)

	def JobTask(self):
		self.Recording()
		self.PlaySymbol()
		self.timer.startLongTimer(POLLTIME)

	def __evUpdatedInfo(self):
		self.service = self.session.nav.getCurrentService()
		self.Subtitle()
		self.ParentalControl()
		del self.service

	def Recording(self):
		if SystemInfo["FrontpanelLEDBrightnessControl"]:
			BRIGHTNESS_DEFAULT = 0xff
			if config.lcd.ledbrightnesscontrol.value > 0xff or config.lcd.ledbrightnesscontrol.value < 0:
				print("[VfdSymbols] LED brightness has to be between 0x0 and 0xff! Using default value (%x)" % (BRIGHTNESS_DEFAULT))
				config.lcd.ledbrightnesscontrol.value = BRIGHTNESS_DEFAULT
			open(SystemInfo["FrontpanelLEDBrightnessControl"], "w").write(config.lcd.ledbrightnesscontrol.value)
		elif SystemInfo["FrontpanelLEDColorControl"]:
			COLOR_DEFAULT = 0xffffff
			if config.lcd.ledcolorcontrolcolor.value > 0xffffff or config.lcd.ledcolorcontrolcolor.value < 0:
				print("[VfdSymbols] LED color has to be between 0x0 and 0xffffff (r, g b)! Using default value (%x)" % (COLOR_DEFAULT))
				config.lcd.ledcolorcontrolcolor.value = COLOR_DEFAULT
			open(SystemInfo["FrontpanelLEDColorControl"], "w").write(config.lcd.ledcolorcontrolcolor.value)
		elif fileExists("/proc/stb/lcd/symbol_circle"):
			recordings = len(NavigationInstance.instance.getRecordings())
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_circle")
			if recordings > 0:
				open("/proc/stb/lcd/symbol_circle", "w").write("3")
			else:
				open("/proc/stb/lcd/symbol_circle", "w").write("0")
		elif HardwareInfo().get_device_name() in ("dm7020hd") and fileExists("/proc/stb/fp/led_set"):
			recordings = len(NavigationInstance.instance.getRecordings())
			self.blink = not self.blink
			print("[VfdSymbols] Write to /proc/stb/fp/led_set")
			if recordings > 0:
				if self.blink:
					open("/proc/stb/fp/led_set", "w").write("0x00000000")
					self.led = "1"
				else:
					open("/proc/stb/fp/led_set", "w").write("0xffffffff")
					self.led = "0"
			else:
				open("/proc/stb/fp/led_set", "w").write("0xffffffff")
		elif SystemInfo["FrontpanelLEDFadeControl"]:
			FADE_DEFAULT = 0x7
			if config.lcd.ledfadecontrolcolor.value > 0xff or config.lcd.ledfadecontrolcolor.value < 0:
				print("[VfdSymbols] LED fade has to be between 0x0 and 0xff! Using default value (%x)" % (FADE_DEFAULT))
				config.lcd.ledfadecontrolcolor.value = FADE_DEFAULT
			open(SystemInfo["FrontpanelLEDFadeControl"], "w").write(config.lcd.ledfadecontrolcolor.value)
		elif SystemInfo["FrontpanelLEDBlinkControl"]:
			BLINK_DEFAULT = 0x0710ff
			if config.lcd.ledblinkcontrolcolor.value > 0xffffff or config.lcd.ledblinkcontrolcolor.value < 0:
				print("[VfdSymbols] LED blink has to be between 0x0 and 0xffffff (on, total, repeats)! Using default value (%x)" % (BLINK_DEFAULT))
				config.lcd.ledblinkcontrolcolor.value = BLINK_DEFAULT
			open(SystemInfo["FrontpanelLEDBlinkControl"], "w").write(config.lcd.ledblinkcontrolcolor.value)
		else:
			if not fileExists("/proc/stb/lcd/symbol_recording") or not fileExists("/proc/stb/lcd/symbol_record_1") or not fileExists("/proc/stb/lcd/symbol_record_2"):
				return

			recordings = len(NavigationInstance.instance.getRecordings())

			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_recording")
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_record_1")
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_record_2")
			if recordings > 0:
				open("/proc/stb/lcd/symbol_recording", "w").write("1")
				if recordings == 1:
					open("/proc/stb/lcd/symbol_record_1", "w").write("1")
					open("/proc/stb/lcd/symbol_record_2", "w").write("0")
				elif recordings >= 2:
					open("/proc/stb/lcd/symbol_record_1", "w").write("1")
					open("/proc/stb/lcd/symbol_record_2", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_recording", "w").write("0")
				open("/proc/stb/lcd/symbol_record_1", "w").write("0")
				open("/proc/stb/lcd/symbol_record_2", "w").write("0")

	def Subtitle(self):
		if not fileExists("/proc/stb/lcd/symbol_smartcard") and not fileExists("/proc/stb/lcd/symbol_subtitle"):
			return

		subtitle = self.service and self.service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()

		if subtitlelist:
			subtitles = len(subtitlelist)
			if fileExists("/proc/stb/lcd/symbol_subtitle"):
				print("[VfdSymbols] Write to /proc/stb/lcd/symbol_subtitle")
				if subtitles > 0:
					open("/proc/stb/lcd/symbol_subtitle", "w").write("1")
				else:
					open("/proc/stb/lcd/symbol_subtitle", "w").write("0")
			else:
				print("[VfdSymbols] Write to /proc/stb/lcd/symbol_smartcard")
				if subtitles > 0:
					open("/proc/stb/lcd/symbol_smartcard", "w").write("1")
				else:
					open("/proc/stb/lcd/symbol_smartcard", "w").write("0")
		else:
			if fileExists("/proc/stb/lcd/symbol_smartcard"):
				print("[VfdSymbols] Write to /proc/stb/lcd/symbol_smartcard")
				open("/proc/stb/lcd/symbol_smartcard", "w").write("0")

	def ParentalControl(self):
		if not fileExists("/proc/stb/lcd/symbol_parent_rating"):
			return

		service = self.session.nav.getCurrentlyPlayingServiceReference()

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_parent_rating")
		if service:
			if parentalControl.getProtectionLevel(service.toCompareString()) == -1:
				open("/proc/stb/lcd/symbol_parent_rating", "w").write("0")
			else:
				open("/proc/stb/lcd/symbol_parent_rating", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_parent_rating", "w").write("0")

	def PlaySymbol(self):
		if not fileExists("/proc/stb/lcd/symbol_play"):
			return

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_play")
		if SystemInfo["SeekStatePlay"]:
			open("/proc/stb/lcd/symbol_play", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_play", "w").write("0")

	def PauseSymbol(self):
		if not fileExists("/proc/stb/lcd/symbol_pause"):
			return

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_pause")
		if SystemInfo["StatePlayPause"]:
			open("/proc/stb/lcd/symbol_pause", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_pause", "w").write("0")

	def PowerSymbol(self):
		if not fileExists("/proc/stb/lcd/symbol_power"):
			return

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_power")
		if SystemInfo["StandbyState"]:
			open("/proc/stb/lcd/symbol_power", "w").write("0")
		else:
			open("/proc/stb/lcd/symbol_power", "w").write("1")

	def Resolution(self):
		if not fileExists("/proc/stb/lcd/symbol_hd"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		videosize = int(info.getInfo(iServiceInformation.sVideoWidth))

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_hd")
		if videosize >= 1280:
			open("/proc/stb/lcd/symbol_hd", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_hd", "w").write("0")

	def Crypted(self):
		if not fileExists("/proc/stb/lcd/symbol_scramled"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		crypted = int(info.getInfo(iServiceInformation.sIsCrypted))

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_scramled")
		if crypted == 1:
			open("/proc/stb/lcd/symbol_scramled", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_scramled", "w").write("0")

	def Teletext(self):
		if not fileExists("/proc/stb/lcd/symbol_teletext"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		tpid = int(info.getInfo(iServiceInformation.sTXTPID))

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_teletext")
		if tpid != -1:
			open("/proc/stb/lcd/symbol_teletext", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_teletext", "w").write("0")

	def Hbbtv(self):
		if not fileExists("/proc/stb/lcd/symbol_epg"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		hbbtv = int(info.getInfo(iServiceInformation.sHBBTVUrl))

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_epg")
		if hbbtv != -1:
			open("/proc/stb/lcd/symbol_epg", "w").write("0")
		else:
			open("/proc/stb/lcd/symbol_epg", "w").write("1")

	def Audio(self):
		if not fileExists("/proc/stb/lcd/symbol_dolby_audio"):
			return

		audio = self.service.audioTracks()
		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_dolby_audio")
		if audio:
			n = audio.getNumberOfTracks()
			idx = 0
			while idx < n:
				i = audio.getTrackInfo(idx)
				description = i.getDescription()
				if "AC3" in description or "AC-3" in description or "DTS" in description:
					open("/proc/stb/lcd/symbol_dolby_audio", "w").write("1")
					return
				idx += 1
		open("/proc/stb/lcd/symbol_dolby_audio", "w").write("0")

	def Timer(self):
		if fileExists("/proc/stb/lcd/symbol_timer"):
			timer = NavigationInstance.instance.RecordTimer.getNextRecordingTime()
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_timer")
			if timer > 0:
				open("/proc/stb/lcd/symbol_timer", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_timer", "w").write("0")
