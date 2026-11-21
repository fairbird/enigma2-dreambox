# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET

try:
	from enigma import registerAnimation_spec
except ImportError:  # enigma2 binary built without XML window animations
	registerAnimation_spec = None
from Tools.Directories import SCOPE_SKIN, fileExists, resolveFilename

INTERPOLATORS = {"linear": 0, "accelerate": 1, "decelerate": 2, "overshoot": 3, "bounce": 4}

# these exist as built-in e2egl styles (or are used by the InfoBar) and are not registered here
SKIPPED_KEYS = ("fade_in_out", "modern_adaptive", "dialog_pop", "toast_slide", "side_sheet", "zoom_fade", "infobar_slide", "infobar_slide_fade")


def interpolator(attrib, inherit):
	name = attrib.get("interpolate")
	if name is None:
		return (-1, 1.0) if inherit else (0, 1.0)
	kind = INTERPOLATORS.get(name, 0)
	if kind == 3:
		return (kind, float(attrib.get("tension", "2.0")))
	return (kind, float(attrib.get("factor", "1.0")))


def propertyValues(item, kind):
	# eight numbers per property: on a b animateX/W animateY/H centered interpolator factor
	if item is None:
		return [0, 0.0, 0.0, 1, 1, 0, -1, 1.0]
	attrib = item.attrib
	interpolatorKind, factor = interpolator(attrib, True)
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


def buildSpec(attrib, duration, items):
	baseKind, baseFactor = interpolator(attrib, False)
	values = [duration / 1000.0, baseKind, baseFactor]
	for tag, kind in (("alpha", "alpha"), ("alpha_hide", "alpha"), ("position", "position"), ("position_hide", "position"), ("size", "size"), ("size_hide", "size")):
		values.extend(propertyValues(items.get(tag), kind))
	return " ".join("%g" % value for value in values)


def loadSpecAnimations():
	"""Registers the animations of animations.xml with e2egl, returns [(style id, title), ...]. The ids follow the file order."""
	choices = []
	path = resolveFilename(SCOPE_SKIN, "animations.xml")
	if registerAnimation_spec is None or not fileExists(path):
		return choices
	try:
		root = ET.parse(path).getroot()
	except Exception as err:
		print("[ScreenAnimations] Error: Unable to read '%s' (%s)!" % (path, str(err)))
		return choices
	for animation in root:
		try:
			attrib = animation.attrib
			key = attrib["key"]
			items = {item.tag: item for item in animation}
			duration = int(attrib.get("duration", 0))
			if key in SKIPPED_KEYS or "internal" in attrib or duration <= 0 or not items:
				continue
			styleId = registerAnimation_spec(buildSpec(attrib, duration, items))
			if styleId > 0:
				choices.append((styleId, _(attrib.get("title", key))))
		except Exception as err:
			print("[ScreenAnimations] Error: Unable to parse the animation '%s' (%s)!" % (animation.attrib, str(err)))
	return choices
