# -*- coding: utf-8 -*-
from twisted.internet import threads
from Components.config import config
from enigma import eTimer, iPlayableService, iServiceInformation
import NavigationInstance
from os.path import isfile
from Components.ParentalControl import parentalControl
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
from time import time, sleep

model = BoxInfo.getItem("model")
brand = BoxInfo.getItem("brand")
platform = BoxInfo.getItem("platform")

POLLTIME = 5 # seconds


def SymbolsCheck(session, **kwargs):
		global symbolspoller, POLLTIME
		if BoxInfo.getItem("VFDSymbol"):
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
		if platform == "u41":
			self.Resolution()
			self.Audio()
			self.Crypted()
			self.Teletext()
			self.Hbbtv()
			self.PauseSymbol()
			self.PlaySymbol()
			self.PowerSymbol()
			self.Timer()
		self.Subtitle()
		self.ParentalControl()
		del self.service

	def Recording(self):
		if BoxInfo.getItem("FrontpanelLEDBrightnessControl"):
			BRIGHTNESS_DEFAULT = 0xff
			if config.lcd.ledbrightnesscontrol.value > 0xff or config.lcd.ledbrightnesscontrol.value < 0:
				print("[VfdSymbols] LED brightness has to be between 0x0 and 0xff! Using default value (%x)" % (BRIGHTNESS_DEFAULT))
				config.lcd.ledbrightnesscontrol.value = BRIGHTNESS_DEFAULT
			open("/proc/stb/fp/led_brightness", "w").write(config.lcd.ledbrightnesscontrol.value)
		elif BoxInfo.getItem("FrontpanelLEDColorControl"):
			COLOR_DEFAULT = 0xffffff
			if config.lcd.ledcolorcontrolcolor.value > 0xffffff or config.lcd.ledcolorcontrolcolor.value < 0:
				print("[VfdSymbols] LED color has to be between 0x0 and 0xffffff (r, g b)! Using default value (%x)" % (COLOR_DEFAULT))
				config.lcd.ledcolorcontrolcolor.value = COLOR_DEFAULT
			open("/proc/stb/fp/led_color", "w").write(config.lcd.ledcolorcontrolcolor.value)
		elif isfile("/proc/stb/lcd/symbol_circle"):
			recordings = len(NavigationInstance.instance.getRecordings())
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_circle")
			if recordings > 0:
				open("/proc/stb/lcd/symbol_circle", "w").write("3")
			else:
				open("/proc/stb/lcd/symbol_circle", "w").write("0")
		elif model in ("alphatriplehd", "sf3038") or brand == "ebox" and isfile("/proc/stb/lcd/symbol_recording"):
			recordings = len(NavigationInstance.instance.getRecordings())
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_recording")
			if recordings > 0:
				open("/proc/stb/lcd/symbol_recording", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_recording", "w").write("0")
		elif platform == "u41" and isfile("/proc/stb/lcd/symbol_pvr2"):
			recordings = len(NavigationInstance.instance.getRecordings())
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_pvr2")
			if recordings > 0:
				open("/proc/stb/lcd/symbol_pvr2", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_pvr2", "w").write("0")
		elif platform == "edisionmipsgen1" or model in ("9910lx", "9911lx", "9920lx") or brand in ("wetek", "ixuss") and isfile("/proc/stb/lcd/powerled"):
			recordings = len(NavigationInstance.instance.getRecordings())
			self.blink = not self.blink
			print("[VfdSymbols] Write to /proc/stb/lcd/powerled")
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/powerled", "w").write("1")
					self.led = "1"
				else:
					open("/proc/stb/lcd/powerled", "w").write("0")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/powerled", "w").write("0")
		elif model in ("mbmicrov2", "mbmicro", "e4hd", "e4hdhybrid") and isfile("/proc/stb/lcd/powerled"):
			recordings = len(NavigationInstance.instance.getRecordings())
			self.blink = not self.blink
			print("[VfdSymbols] Write to /proc/stb/lcd/powerled")
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/powerled", "w").write("0")
					self.led = "1"
				else:
					open("/proc/stb/lcd/powerled", "w").write("1")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/powerled", "w").write("1")
		elif model in ("dm7020hd", "dm7020hdv2") and isfile("/proc/stb/fp/led_set"):
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
		elif platform in ("dags7362", "dags73625") or model in ("tmtwin4k", "revo4k", "force3uhd") and isfile("/proc/stb/lcd/symbol_rec"):
			recordings = len(NavigationInstance.instance.getRecordings())
			self.blink = not self.blink
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_rec")
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/symbol_rec", "w").write("1")
					self.led = "1"
				else:
					open("/proc/stb/lcd/symbol_rec", "w").write("0")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/symbol_rec", "w").write("0")
		elif BoxInfo.getItem("HiSilicon") and isfile("/proc/stb/fp/ledpowercolor"):
			import Screens.Standby
			recordings = len(NavigationInstance.instance.getRecordings(False))
			if recordings > 0 and not Screens.Standby.inStandby:
				if config.usage.frontledrec_color.value == "2":
					open("/proc/stb/fp/ledpowercolor", "w").write("2")
				elif config.usage.frontledrec_color.value == "4":
					open("/proc/stb/fp/ledpowercolor", "w").write("0")
					sleep(10) # blinking
					open("/proc/stb/fp/ledpowercolor", "w").write("2")
				elif config.usage.frontledrec_color.value == "3":
					open("/proc/stb/fp/ledpowercolor", "w").write("0")
					sleep(10) # blinking
					open("/proc/stb/fp/ledpowercolor", "w").write("1")
				elif config.usage.frontledrec_color.value == "1":
					open("/proc/stb/fp/ledpowercolor", "w").write("1")
				elif config.usage.frontledrec_color.value == "0":
					open("/proc/stb/fp/ledpowercolor", "w").write("0")
			if recordings > 0 and Screens.Standby.inStandby:
				if config.usage.frontledrecstdby_color.value == "2":
					open("/proc/stb/fp/ledpowercolor", "w").write("2")
				elif config.usage.frontledrecstdby_color.value == "4":
					open("/proc/stb/fp/ledpowercolor", "w").write("0")
					sleep(10) # blinking standby
					open("/proc/stb/fp/ledpowercolor", "w").write("2")
				elif config.usage.frontledrecstdby_color.value == "3":
					open("/proc/stb/fp/ledpowercolor", "w").write("0")
					sleep(10) # blinking standby
					open("/proc/stb/fp/ledpowercolor", "w").write("1")
				elif config.usage.frontledrecstdby_color.value == "1":
					open("/proc/stb/fp/ledpowercolor", "w").write("1")
				elif config.usage.frontledrecstdby_color.value == "0":
					open("/proc/stb/fp/ledpowercolor", "w").write("0")
			if not recordings:
				if Screens.Standby.inStandby:
					if config.usage.frontledstdby_color.value == "4":
						open("/proc/stb/fp/ledpowercolor", "w").write("0")
						sleep(10) # blinking standby
						open("/proc/stb/fp/ledpowercolor", "w").write("2")
					elif config.usage.frontledstdby_color.value == "3":
						open("/proc/stb/fp/ledpowercolor", "w").write("0")
						sleep(10) # blinking standby
						open("/proc/stb/fp/ledpowercolor", "w").write("1")
					open("/proc/stb/fp/ledpowercolor", "w").write(config.usage.frontledstdby_color.value)
				else:
					open("/proc/stb/fp/ledpowercolor", "w").write(config.lcd.ledpowercolor.value)
		elif BoxInfo.getItem("FrontpanelLEDFadeControl"):
			FADE_DEFAULT = 0x7
			if config.lcd.ledfadecontrolcolor.value > 0xff or config.lcd.ledfadecontrolcolor.value < 0:
				print("[VfdSymbols] LED fade has to be between 0x0 and 0xff! Using default value (%x)" % (FADE_DEFAULT))
				config.lcd.ledfadecontrolcolor.value = FADE_DEFAULT
			open("/proc/stb/fp/led_fade", "w").write(config.lcd.ledfadecontrolcolor.value)
		elif BoxInfo.getItem("FrontpanelLEDBlinkControl"):
			BLINK_DEFAULT = 0x0710ff
			if config.lcd.ledblinkcontrolcolor.value > 0xffffff or config.lcd.ledblinkcontrolcolor.value < 0:
				print("[VfdSymbols] LED blink has to be between 0x0 and 0xffffff (on, total, repeats)! Using default value (%x)" % (BLINK_DEFAULT))
				config.lcd.ledblinkcontrolcolor.value = BLINK_DEFAULT
			open("/proc/stb/fp/led_blink", "w").write(config.lcd.ledblinkcontrolcolor.value)
		else:
			if not isfile("/proc/stb/lcd/symbol_recording") or not isfile("/proc/stb/lcd/symbol_record_1") or not isfile("/proc/stb/lcd/symbol_record_2"):
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
		if not isfile("/proc/stb/lcd/symbol_smartcard") and not isfile("/proc/stb/lcd/symbol_subtitle"):
			return

		subtitle = self.service and self.service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()

		if subtitlelist:
			subtitles = len(subtitlelist)
			if isfile("/proc/stb/lcd/symbol_subtitle"):
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
			if isfile("/proc/stb/lcd/symbol_smartcard"):
				print("[VfdSymbols] Write to /proc/stb/lcd/symbol_smartcard")
				open("/proc/stb/lcd/symbol_smartcard", "w").write("0")

	def ParentalControl(self):
		if not isfile("/proc/stb/lcd/symbol_parent_rating"):
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
		if not isfile("/proc/stb/lcd/symbol_play"):
			return

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_play")
		if BoxInfo.getItem("SeekStatePlay"):
			open("/proc/stb/lcd/symbol_play", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_play", "w").write("0")

	def PauseSymbol(self):
		if not isfile("/proc/stb/lcd/symbol_pause"):
			return

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_pause")
		if BoxInfo.getItem("StatePlayPause"):
			open("/proc/stb/lcd/symbol_pause", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_pause", "w").write("0")

	def PowerSymbol(self):
		if not isfile("/proc/stb/lcd/symbol_power"):
			return

		print("[VfdSymbols] Write to /proc/stb/lcd/symbol_power")
		if BoxInfo.getItem("StandbyState"):
			open("/proc/stb/lcd/symbol_power", "w").write("0")
		else:
			open("/proc/stb/lcd/symbol_power", "w").write("1")

	def Resolution(self):
		if not isfile("/proc/stb/lcd/symbol_hd"):
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
		if not isfile("/proc/stb/lcd/symbol_scramled"):
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
		if not isfile("/proc/stb/lcd/symbol_teletext"):
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
		if not isfile("/proc/stb/lcd/symbol_epg"):
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
		if not isfile("/proc/stb/lcd/symbol_dolby_audio"):
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
		if isfile("/proc/stb/lcd/symbol_timer"):
			timer = NavigationInstance.instance.RecordTimer.getNextRecordingTime()
			print("[VfdSymbols] Write to /proc/stb/lcd/symbol_timer")
			if timer > 0:
				open("/proc/stb/lcd/symbol_timer", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_timer", "w").write("0")
