# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET

from enigma import setAnimation_spec
from Components.config import config, ConfigOnOff, ConfigText
from Tools.Directories import fileExists, resolveFilename, SCOPE_SKIN

config.osd.window_animation = ConfigOnOff(default=True)
config.osd.window_animation_default = ConfigText(default="simple_fade")

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

	def setAnimationSet(self, animset):
		if animset.key not in self.sets:
			self.order.append(animset.key)
		self.sets[animset.key] = animset

	def getAnimations(self):
		return {key: self.sets[key].name for key in self.order if not self.sets[key].internal}

	def setDefault(self, key):
		self.default = key
		animset = self.sets.get(key)
		setAnimation_spec(animset.spec if animset and config.osd.window_animation.value else "")

	def setWidgetDefault(self):
		pass


eWindowAnimationManager = WindowAnimationManager()


class ScreenAnimations:
	def loadDefault(self):
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
