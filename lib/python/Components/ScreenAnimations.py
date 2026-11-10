# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET

from enigma import getDesktop, setAnimation_spec
try:
	from enigma import registerAnimation_spec
except ImportError:  # enigma2 binary built without per-window animations
	registerAnimation_spec = None
try:
	from enigma import setListboxSmoothSelection
except ImportError:  # enigma2 binary built without smooth list selection
	setListboxSmoothSelection = None
from Components.config import config, ConfigOnOff, ConfigSelection, ConfigSelectionNumber, ConfigText, ConfigYesNo
from Tools.Directories import fileExists, resolveFilename, SCOPE_SKIN
from Tools.HardwareInfo import HardwareInfo

config.osd.window_animation = ConfigOnOff(default=False)
config.osd.window_animation_default = ConfigText(default="simple_fade")
config.osd.widget_animation = ConfigSelection(default="off", choices=[("off", _("No")), ("on", _("Yes"))])
config.osd.widget_animation_display = ConfigSelection(default="off", choices=[("off", _("No")), ("on", _("Yes"))])
config.osd.widget_animation_duration = ConfigSelection(default="400", choices=[(str(ms), "%04d" % ms) for ms in (50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000)])

# styles that can be chosen per window type ("default" = the global window animation)
PROFILE_STYLES = [
	("default", _("Window animation")),
	("disabled", _("Disable Animations")),
	("modern_adaptive", _("Modern adaptive")),
	("fade_in_out", _("Fade in / fade out")),
	("dialog_pop", _("Dialog pop")),
	("toast_slide", _("Toast slide")),
	("side_sheet", _("Side sheet")),
	("zoom_fade", _("Zoom and fade")),
]
INFOBAR_STYLES = [
	("disabled", _("Disabled")),
	("fade_in_out", _("Fade in / fade out")),
	("infobar_slide", _("Slide in from bottom / out to bottom")),
	("infobar_slide_fade", _("Slide from bottom with fade")),
]
config.osd.animation_speed = ConfigSelectionNumber(5, 30, 1, default=15)
config.osd.animation_profiles = ConfigYesNo(default=True)
config.osd.animation_dialog = ConfigSelection(default="dialog_pop", choices=PROFILE_STYLES)
config.osd.animation_popup = ConfigSelection(default="modern_adaptive", choices=PROFILE_STYLES)
config.osd.animation_toast = ConfigSelection(default="fade_in_out", choices=PROFILE_STYLES)
config.osd.animation_infobar = ConfigSelection(default="disabled", choices=INFOBAR_STYLES)
config.osd.animation_mediainfobar = ConfigSelection(default="disabled", choices=INFOBAR_STYLES)
config.osd.animation_infobar_duration = ConfigSelectionNumber(100, 1000, 50, default=250)
config.osd.animation_toast_duration = ConfigSelectionNumber(100, 1000, 50, default=300)
config.osd.animation_smooth_list = ConfigYesNo(default=False)
config.osd.animation_memory_limit = ConfigSelection(default="32", choices=[(str(mib), "%d MiB" % mib) for mib in (8, 16, 32, 64, 128)])
config.osd.animation_wizard = ConfigYesNo(default=False)
config.osd.animation_picture_crossfade = ConfigYesNo(default=False)
config.osd.animation_picture_crossfade_duration = ConfigSelectionNumber(500, 5000, 250, default=2000)

INTERPOLATORS = {"linear": 0, "accelerate": 1, "decelerate": 2, "overshoot": 3, "bounce": 4}


class WindowAnimationSet:
	def __init__(self, key, name, internal, spec):
		self.key = key
		self.name = name
		self.internal = internal
		self.spec = spec


class WindowAnimationManager:
	KEY_DISABLED = "disabled"

	def __init__(self):
		self.sets = {}
		self.order = []
		self.default = self.KEY_DISABLED
		self.ids = {}

	def setAnimationSet(self, animset):
		if animset.key not in self.sets:
			self.order.append(animset.key)
		self.sets[animset.key] = animset

	def getAnimations(self):
		return {key: self.sets[key].name for key in self.order if not self.sets[key].internal}

	def scaledSpec(self, key, durationMs=None):
		animset = self.sets.get(key)
		if not animset or not animset.spec:
			return ""
		parts = animset.spec.split(" ", 1)
		if durationMs is None:
			durationMs = float(parts[0]) * 1000.0 * 15.0 / max(5, int(config.osd.animation_speed.value))
		return "%g %s" % (max(0.05, durationMs / 1000.0), parts[1])

	def profileId(self, key, durationMs=None):
		spec = self.scaledSpec(key, durationMs)
		if not spec:
			return 0
		if registerAnimation_spec is None:
			return 0
		if spec not in self.ids:
			self.ids[spec] = registerAnimation_spec(spec)
		return self.ids[spec]

	def applySmoothSelection(self):
		if setListboxSmoothSelection is not None:
			enabled = config.osd.animation_smooth_list.value
			setListboxSmoothSelection(int(150 * 15 / max(5, int(config.osd.animation_speed.value))) if enabled else 0)

	def setDefault(self, key):
		self.applySmoothSelection()
		self.default = key
		setAnimation_spec(self.scaledSpec(key) if config.osd.window_animation.value else "")

	def getScreenAnimationId(self, screen):
		"""0 = the global animation, -1 = no animation, >0 = a registered profile"""
		if not config.osd.window_animation.value:
			return 0
		profile = getattr(screen, "animationProfile", None) or self.classify(screen)
		if profile in ("infobar", "mediainfobar"):
			key = (config.osd.animation_infobar if profile == "infobar" else config.osd.animation_mediainfobar).value
			if key == "disabled":
				return -1
			return self.profileId(key, int(config.osd.animation_infobar_duration.value)) or 0
		if not profile or not config.osd.animation_profiles.value:
			return 0
		key = {"dialog": config.osd.animation_dialog, "popup": config.osd.animation_popup, "toast": config.osd.animation_toast}[profile].value
		if key == "default":
			return 0
		if key == "disabled":
			return -1
		return self.profileId(key, int(config.osd.animation_toast_duration.value) if profile == "toast" else None) or 0

	INFOBAR_NAMES = ("InfoBar",)
	MEDIA_NAMES = ("MoviePlayer", "EMCMediaCenter", "MediaPlayer")
	DIALOG_NAMES = ("MessageBox", "Processing", "ToastScreen")
	POPUP_NAMES = ("ChoiceBox", "ContextMenu", "HelpMenu", "InputBox", "PiPSetup")

	def isInfoBarScreen(self, screen):
		return self.classify(screen) in ("infobar", "mediainfobar")

	def classify(self, screen):
		names = [cls.__name__ for cls in type(screen).__mro__]
		if "ToastScreen" in names:
			return "toast"
		if names[0] in self.INFOBAR_NAMES:
			return "infobar"
		if any(name in self.MEDIA_NAMES for name in names[:1]):
			return "mediainfobar"
		if any(name in self.DIALOG_NAMES for name in names):
			return "dialog"
		if any(name in self.POPUP_NAMES for name in names):
			return "popup"
		try:
			size = screen.instance.size()
			desktop = screen.instance.getDesktop() if hasattr(screen.instance, "getDesktop") else getDesktop(0)
			full = desktop.size() if desktop else getDesktop(0).size()
			if size.width() * size.height() < 0.45 * full.width() * full.height() and screen.instance.position().y() > 0:
				return "popup"
		except Exception:
			pass
		return None

	def applyScreen(self, screen):
		instance = getattr(screen, "instance", None)
		if instance is None or not hasattr(instance, "setAnimationId"):
			return
		try:
			instance.setAnimationId(self.getScreenAnimationId(screen))
		except Exception as err:
			print("[ScreenAnimations] Error: Unable to select the animation (%s)!" % str(err))

	def setWidgetDefault(self):
		desktop = getDesktop(0)
		desktop.setWidgetAnimationsEnabled(config.osd.widget_animation.value == "on")
		desktop.setWidgetAnimationDuration(int(config.osd.widget_animation_duration.value))
		if HardwareInfo().get_device_name() in ("dm900", "dm920"):
			lcd = getDesktop(1)
			if lcd:
				lcd.setWidgetAnimationsEnabled(config.osd.widget_animation_display.value == "on")


eWindowAnimationManager = WindowAnimationManager()


class ScreenAnimations:
	def loadDefault(self):
		from Screens.Screen import Screen
		Screen.animationHook = eWindowAnimationManager.applyScreen
		eWindowAnimationManager.applySmoothSelection()
		eWindowAnimationManager.setAnimationSet(WindowAnimationSet(eWindowAnimationManager.KEY_DISABLED, _("Disable Animations"), False, ""))
		path = resolveFilename(SCOPE_SKIN, "animations.xml")
		if fileExists(path):
			self.fromXML(filesource=path)

	def fromXML(self, filesource=None, xml=None):
		root = ET.parse(filesource).getroot() if filesource else ET.fromstring(xml)
		for animation in root:
			try:
				attrib = animation.attrib
				key = attrib["key"]
				name = _(attrib.get("title", key))
				internal = "internal" in attrib
				duration = int(attrib.get("duration", 0))
				items = {item.tag: item for item in animation}
				if duration <= 0 or not items:
					continue
				eWindowAnimationManager.setAnimationSet(WindowAnimationSet(key, name, internal, self.buildSpec(attrib, duration, items)))
			except Exception as err:
				print("[ScreenAnimations] Error: Unable to parse the animation '%s' (%s)!" % (animation.attrib, str(err)))

	def interpolator(self, attrib, inherit):
		name = attrib.get("interpolate")
		if name is None:
			return (-1, 1.0) if inherit else (0, 1.0)
		kind = INTERPOLATORS.get(name, 0)
		if kind == 3:
			return (kind, float(attrib.get("tension", "2.0")))
		return (kind, float(attrib.get("factor", "1.0")))

	def propertyValues(self, item, kind):
		# eight numbers per property: on a b animateX/W animateY/H centered interpolator factor
		if item is None:
			return [0, 0.0, 0.0, 1, 1, 0, -1, 1.0]
		attrib = item.attrib
		interpolatorKind, factor = self.interpolator(attrib, True)
		value = attrib["val"]
		if kind == "alpha":
			return [1, float(value), 0.0, 1, 1, 0, interpolatorKind, factor]
		if kind == "position":
			animateX = "animateX" in attrib
			animateY = "animateY" in attrib
			if not animateX and not animateY:
				animateX = animateY = True
			return [1, float(value), 0.0, int(animateX), int(animateY), 0, interpolatorKind, factor]
		width, height = [float(part) for part in value.split(",")]
		animateW = "animateW" in attrib
		animateH = "animateH" in attrib
		if not animateW and not animateH:
			animateW = animateH = True
		return [1, width, height, int(animateW), int(animateH), int("centered" in attrib), interpolatorKind, factor]

	def buildSpec(self, attrib, duration, items):
		baseKind, baseFactor = self.interpolator(attrib, False)
		values = [duration / 1000.0, baseKind, baseFactor]
		for tag, kind in (("alpha", "alpha"), ("alpha_hide", "alpha"), ("position", "position"), ("position_hide", "position"), ("size", "size"), ("size_hide", "size")):
			values.extend(self.propertyValues(items.get(tag), kind))
		return " ".join("%g" % value for value in values)
