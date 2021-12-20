from Screens.Screen import Screen
from Components.Sources.CurrentService import CurrentService
from Components.Sources.EventInfo import EventInfo
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.FrontendInfo import FrontendInfo
from Components.Sources.Source import Source
from Components.Sources.TunerInfo import TunerInfo
from Components.Sources.Boolean import Boolean
from Components.Sources.RecordState import RecordState
from Components.Converter.Combine import Combine
from Components.Renderer.FrontpanelLed import FrontpanelLed
from Components.config import config
from Components.SystemInfo import SystemInfo
from Tools.HardwareInfo import HardwareInfo


class SessionGlobals(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["CurrentService"] = CurrentService(session.nav)
		self["Event_Now"] = EventInfo(session.nav, EventInfo.NOW)
		self["Event_Next"] = EventInfo(session.nav, EventInfo.NEXT)
		self["FrontendStatus"] = FrontendStatus(service_source=session.nav.getCurrentService)
		self["FrontendInfo"] = FrontendInfo(navcore=session.nav)
		self["VideoPicture"] = Source()
		self["TunerInfo"] = TunerInfo()
		self["RecordState"] = RecordState(session)
		self["Standby"] = Boolean(fixed=False)

		combine = Combine(func=lambda s: {(False, False): 0, (False, True): 1, (True, False): 2, (True, True): 3}[(s[0].boolean, s[1].boolean)])
		combine.connect(self["Standby"])
		combine.connect(self["RecordState"])

		#                      |  two leds  | single led |
		# recordstate  standby   red green
		#    false      false    off   on     off
		#    true       false    blnk  on     blnk
		#    false      true      on   off    off
		#    true       true     blnk  off    blnk

		PATTERN_ON = (20, 0xffffffff, 0xffffffff)
		PATTERN_OFF = (20, 0, 0)
		PATTERN_BLINK = (20, 0x55555555, 0xa7fccf7a)

		NormalLed0 = PATTERN_OFF
		NormalLed1 = PATTERN_OFF
		if config.usage.frontled_color.value == "1":
			NormalLed0 = PATTERN_ON
		if config.usage.frontled_color.value == "2":
			NormalLed1 = PATTERN_ON
		if config.usage.frontled_color.value == "3":
			NormalLed0 = PATTERN_BLINK
		if config.usage.frontled_color.value == "4":
			NormalLed1 = PATTERN_BLINK

		RecLed0 = PATTERN_OFF
		RecLed1 = PATTERN_OFF
		if config.usage.frontledrec_color.value == "1":
			RecLed0 = PATTERN_ON
		if config.usage.frontledrec_color.value == "2":
			RecLed1 = PATTERN_ON
		if config.usage.frontledrec_color.value == "3":
			RecLed0 = PATTERN_BLINK
		if config.usage.frontledrec_color.value == "4":
			RecLed1 = PATTERN_BLINK

		StandbyLed0 = PATTERN_OFF
		StandbyLed1 = PATTERN_OFF
		if config.usage.frontledstdby_color.value == "1":
			StandbyLed0 = PATTERN_ON
		if config.usage.frontledstdby_color.value == "2":
			StandbyLed1 = PATTERN_ON
		if config.usage.frontledstdby_color.value == "3":
			StandbyLed0 = PATTERN_BLINK
		if config.usage.frontledstdby_color.value == "4":
			StandbyLed1 = PATTERN_BLINK

		RecstdbyLed0 = PATTERN_OFF
		RecstdbyLed1 = PATTERN_OFF
		if config.usage.frontledrecstdby_color.value == "1":
			RecstdbyLed0 = PATTERN_ON
		if config.usage.frontledrecstdby_color.value == "2":
			RecstdbyLed1 = PATTERN_ON
		if config.usage.frontledrecstdby_color.value == "3":
			RecstdbyLed0 = PATTERN_BLINK
		if config.usage.frontledrecstdby_color.value == "4":
			RecstdbyLed1 = PATTERN_BLINK

		nr_leds = SystemInfo.get("NumFrontpanelLEDs", 0)

		if nr_leds == 1:
			FrontpanelLed(which=0, boolean=False, patterns=[PATTERN_OFF, PATTERN_BLINK, PATTERN_OFF, PATTERN_BLINK]).connect(combine)
		elif nr_leds == 2:
			FrontpanelLed(which=0, boolean=False, patterns=[NormalLed0, RecLed0, StandbyLed0, RecstdbyLed0]).connect(combine)
			FrontpanelLed(which=1, boolean=False, patterns=[NormalLed1, RecLed1, StandbyLed1, RecstdbyLed1]).connect(combine)
