from glob import glob
from os.path import dirname, isfile, join as pathjoin, splitext
from os import listdir, unlink
from xml.etree.cElementTree import Element, ElementTree, fromstring

from enigma import BT_ALPHABLEND, BT_ALPHATEST, BT_HALIGN_CENTER, BT_HALIGN_LEFT, BT_HALIGN_RIGHT, BT_KEEP_ASPECT_RATIO, BT_SCALE, BT_VALIGN_BOTTOM, BT_VALIGN_CENTER, BT_VALIGN_TOP, addFont, eLabel, eListbox, ePixmap, ePoint, eRect, eSize, eSlider, eSubtitleWidget, eWindow, eWindowStyleManager, eWindowStyleSkinned, getDesktop, gFont, getFontFaces, gMainDC, gRGB

from Components.config import ConfigSubsection, ConfigText, config
from Components.SystemInfo import SystemInfo
from Components.Sources.Source import ObsoleteSource
from Tools.Directories import SCOPE_LCDSKIN, SCOPE_GUISKIN, SCOPE_FONTS, SCOPE_SKINS, pathExists, resolveFilename, fileReadXML
from Tools.Import import my_import
from Tools.LoadPixmap import LoadPixmap

MODULE_NAME = __name__.split(".")[-1].capitalize()

DEFAULT_SKIN = SystemInfo["HasFullHDSkinSupport"] and "PLi-FullNightHD/skin.xml" or "PLi-HD/skin.xml"  # SD hardware is no longer supported by the default skin.
EMERGENCY_SKIN = "skin_default/skin.xml"
EMERGENCY_NAME = "Stone II"
DEFAULT_DISPLAY_SKIN = "skin_default/skin_display.xml"
USER_SKIN = "skin_user.xml"
USER_SKIN_TEMPLATE = "skin_user_%s.xml"
SUBTITLE_SKIN = "skin_subtitles.xml"

GUI_SKIN_ID = 0  # Main frame-buffer.
DISPLAY_SKIN_ID = 1  # Front panel / display / LCD.

domScreens = {}  # Dictionary of skin based screens.
colors = {  # Dictionary of skin color names.
	"key_back": gRGB(0x00313131),
	"key_blue": gRGB(0x0018188B),
	"key_green": gRGB(0x001F771F),
	"key_red": gRGB(0x009F1313),
	"key_text": gRGB(0x00FFFFFF),
	"key_yellow": gRGB(0x00A08500)
}
fonts = {  # Dictionary of predefined and skin defined font aliases.
	"Body": ("Regular", 18, 22, 16),
	"ChoiceList": ("Regular", 20, 24, 18)
}
menus = {}  # Dictionary of images associated with menu entries.
parameters = {}  # Dictionary of skin parameters used to modify code behavior.
setups = {}  # Dictionary of images associated with setup menus.
switchPixmap = {}  # Dictionary of switch images.
windowStyles = {}  # Dictionary of window styles for each screen ID.
resolutions = {}  # Dictionary of screen resolutions for each screen ID.
scrollLabelStyle = {}  # Dictionary of scrollLabel widget defaults.
constantWidgets = {}
variables = {}
isVTISkin = False  # Temporary flag to suppress errors in OpenATV.

config.skin = ConfigSubsection()
skin = resolveFilename(SCOPE_SKINS, DEFAULT_SKIN)
if not isfile(skin):
	print("[Skin] Error: Default skin '%s' is not readable or is not a file!  Using emergency skin." % skin)
	DEFAULT_SKIN = EMERGENCY_SKIN
config.skin.primary_skin = ConfigText(default=DEFAULT_SKIN)
config.skin.display_skin = ConfigText(default=DEFAULT_DISPLAY_SKIN)

currentPrimarySkin = None
currentDisplaySkin = None
callbacks = []
runCallbacks = False


# Skins are loaded in order of priority.  Skin with highest priority is
# loaded last.  This is usually the user-specified skin.  In this way
# any duplicated screens will be replaced by a screen of the same name
# with a higher priority.
#
# GUI skins are saved in the settings file as the path relative to
# SCOPE_SKINS.  The full path is NOT saved.  E.g. "MySkin/skin.xml"
#
# Display skins are saved in the settings file as the path relative to
# SCOPE_LCDSKIN.  The full path is NOT saved.
# E.g. "MySkin/skin_display.xml"
#
def InitSkins():
	global currentPrimarySkin, currentDisplaySkin, resolutions
	# #################################################################################################
	if isfile("/etc/.restore_skins"):
		unlink("/etc/.restore_skins")
		lastPath = ""
		for skin in sorted(glob("/usr/lib/enigma2/python/Plugins/Extensions/*/ActivateSkinSettings.py*")):
			try:
				print("[Skin] RESTORE_SKIN: Restore skin from '%s'..." % skin)
				skinPath, skinExt = splitext(skin)
				if skinPath == lastPath or skinExt not in (".py", ".pyc", ".pyo"):
					print("[Skin] RESTORE_SKIN: Skip!")
					continue
				lastPath = skinPath
				if getattr(__import__(skin.replace("/usr/lib/enigma2/python/", "").replace(skinExt, "").replace("/", "."), fromlist=["ActivateSkinSettings"]), "ActivateSkinSettings")().WriteSkin(True):
					print("[Skin] RESTORE_SKIN: Failed!")
				else:
					print("[Skin] RESTORE_SKIN: Done!")
			except Exception as err:
				print("[Skin] RESTORE_SKIN: Error occurred!  (%s)" % err)
	# #################################################################################################
	runCallbacks = False
	# Add the emergency skin.  This skin should provide enough functionality
	# to enable basic GUI functions to work.
	loadSkin(EMERGENCY_SKIN, scope=SCOPE_GUISKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	# Add the subtitle skin.
	loadSkin(SUBTITLE_SKIN, scope=SCOPE_GUISKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	# Add the main GUI skin.
	result = []
	for skin, name in [(config.skin.primary_skin.value, "current"), (DEFAULT_SKIN, "default")]:
		if skin in result:  # Don't try to add a skin that has already failed.
			continue
		config.skin.primary_skin.value = skin
		if loadSkin(config.skin.primary_skin.value, scope=SCOPE_GUISKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID):
			currentPrimarySkin = config.skin.primary_skin.value
			break
		print("[Skin] Error: Adding %s GUI skin '%s' has failed!" % (name, config.skin.primary_skin.value))
		result.append(skin)
	# Add the front panel / display / lcd skin.
	result = []
	for skin, name in [(config.skin.display_skin.value, "current"), (DEFAULT_DISPLAY_SKIN, "default")]:
		if skin in result:  # Don't try to add a skin that has already failed.
			continue
		config.skin.display_skin.value = skin
		if loadSkin(config.skin.display_skin.value, scope=SCOPE_LCDSKIN, desktop=getDesktop(DISPLAY_SKIN_ID), screenID=DISPLAY_SKIN_ID):
			currentDisplaySkin = config.skin.display_skin.value
			break
		print("[Skin] Error: Adding %s display skin '%s' has failed!" % (name, config.skin.display_skin.value))
		result.append(skin)
	# Add the activated optional skin parts.
	if currentPrimarySkin != None:
		partsDir = resolveFilename(SCOPE_GUISKIN, pathjoin(dirname(currentPrimarySkin), "mySkin", ""))
		if pathExists(partsDir) and currentPrimarySkin != DEFAULT_SKIN:
			for file in sorted(listdir(partsDir)):
				if file.startswith("skin_") and file.endswith(".xml"):
					partsFile = pathjoin(partsDir, file)
					if not loadSkin(partsFile, scope=SCOPE_GUISKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID):
						print("[Skin] Error: Failed to load modular skin file '%s'!" % partsFile)
	# Add an optional skin related user skin "user_skin_<SkinName>.xml".  If there is
	# not a skin related user skin then try to add am optional generic user skin.
	result = None
	if isfile(resolveFilename(SCOPE_SKINS, config.skin.primary_skin.value)):
		name = USER_SKIN_TEMPLATE % dirname(config.skin.primary_skin.value)
		if isfile(resolveFilename(SCOPE_GUISKIN, name)):
			result = loadSkin(name, scope=SCOPE_GUISKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	if result is None:
		loadSkin(USER_SKIN, scope=SCOPE_GUISKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	resolution = resolutions.get(GUI_SKIN_ID, (0, 0, 0))
	if resolution[0] and resolution[1]:
		gMainDC.getInstance().setResolution(resolution[0], resolution[1])
		getDesktop(GUI_SKIN_ID).resize(eSize(resolution[0], resolution[1]))
	runCallbacks = True


# Method to load a skin XML file into the skin data structures.
#
def loadSkin(filename, scope=SCOPE_SKINS, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID):
	global windowStyles, resolutions
	filename = resolveFilename(scope, filename)
	print("[Skin] Loading skin file '%s'." % filename)
	domSkin = fileReadXML(filename, source=MODULE_NAME)
	if domSkin:
		# For loadSingleSkinData colors, bordersets etc. are applied one after
		# the other in order of ascending priority.
		loadSingleSkinData(desktop, screenID, domSkin, filename, scope=scope)
		resolution = resolutions.get(screenID, (0, 0, 0))
		print("[Skin] Skin resolution is %dx%d and color depth is %d bits." % (resolution[0], resolution[1], resolution[2]))
		for element in domSkin:
			if element.tag == "screen":  # Process all screen elements.
				name = element.attrib.get("name")
				if name:  # Without a name, it's useless!
					scrnID = element.attrib.get("id")
					if scrnID is None or scrnID == screenID:  # If there is a screen ID is it for this display.
						res = element.attrib.get("resolution", "%s,%s" % (resolution[0], resolution[1]))
						if res != "0,0":
							element.attrib["resolution"] = res
						domScreens[name] = (element, "%s/" % dirname(filename))
			elif element.tag == "windowstyle":  # Process the windowstyle element.
				scrnID = element.attrib.get("id")
				if scrnID is not None:  # Without an scrnID, it is useless!
					scrnID = parseInteger(scrnID)
					domStyle = ElementTree(Element("skin"))
					domStyle.getroot().append(element)
					windowStyles[scrnID] = (desktop, screenID, domStyle.getroot(), filename, scope)
			# Element is not a screen or windowstyle element so no need for it any longer.
		print("[Skin] Loading skin file '%s' complete." % filename)
		if runCallbacks:
			for method in callbacks:
				if method:
					method()
		return True
	return False


def reloadSkins():
	global colors, domScreens, fonts, menus, parameters, setups, switchPixmap
	domScreens.clear()
	colors.clear()
	colors = {
		"key_back": gRGB(0x00313131),
		"key_blue": gRGB(0x0018188B),
		"key_green": gRGB(0x001F771F),
		"key_red": gRGB(0x009F1313),
		"key_text": gRGB(0x00FFFFFF),
		"key_yellow": gRGB(0x00A08500)
	}
	fonts.clear()
	fonts = {
		"Body": ("Regular", 18, 22, 16),
		"ChoiceList": ("Regular", 20, 24, 18)
	}
	menus.clear()
	parameters.clear()
	setups.clear()
	switchPixmap.clear()
	InitSkins()


def addCallback(callback):
	global callbacks
	if callback not in callbacks:
		callbacks.append(callback)


def removeCallback(callback):
	global callbacks
	if callback in callbacks:
		callbacks.remove(callback)


def getParentSize(object, desktop):
	if object:
		parent = object.getParent()
		# For some widgets (e.g. ScrollLabel) the skin attributes are applied to a
		# child widget, instead of to the widget itself.  In that case, the parent
		# we have here is not the real parent, but it is the main widget.  We have
		# to go one level higher to get the actual parent.  We can detect this
		# because the 'parent' will not have a size yet.  (The main widget's size
		# will be calculated internally, as soon as the child widget has parsed the
		# skin attributes.)
		if parent and parent.size().isEmpty():
			parent = parent.getParent()
		if parent:
			return parent.size()
		elif desktop:
			return desktop.size()  # Widget has no parent, use desktop size instead for relative coordinates.
	return eSize()


def skinError(errorMessage):
	print("[Skin] Error: %s!" % errorMessage)


def attribDeprecationWarning(attribute, replacement):
	print("[Skin] Warning: Attribute '%s' has been deprecated, use '%s' instead!" % (attribute, replacement))


def parseOptions(options, attribute, value, default):
	if options and isinstance(options, dict):
		if value in options.keys():
			value = options[value]
		else:
			skinError("The '%s' value '%s' is invalid, acceptable options are '%s'" % (attribute, value, "', '".join(options.keys())))
			value = default
	else:
		skinError("The '%s' parser is not correctly initialized")
		value = default
	return value


def parseAlphaTest(value):
	options = {
		"on": BT_ALPHATEST,
		"off": 0,
		"blend": BT_ALPHABLEND
	}
	return parseOptions(options, "alphaTest", value, 0)


def parseAnimationMode(value):
	options = {
		"disable": 0x00,
		"off": 0x00,
		"offshow": 0x10,
		"offhide": 0x01,
		"onshow": 0x01,
		"onhide": 0x10,
		"disable_onshow": 0x10,
		"disable_onhide": 0x01
	}
	return parseOptions(options, "animationMode", value, 0x00)


def parseBoolean(attribute, value):
	return value.lower() in ("1", attribute, "enabled", "on", "true", "yes")


def parseColor(value, default=0x00FFFFFF):
	if value[0] == "#":
		try:
			value = gRGB(int(value[1:], 0x10))
		except ValueError:
			skinError("The color code '%s' must be #aarrggbb, using #00ffffff (White)" % value)
			value = gRGB(default)
	elif value in colors:
		value = colors[value]
	else:
		skinError("The color '%s' must be #aarrggbb or valid named color, using #00ffffff (White)" % value)
		value = gRGB(default)
	return value


# Convert a coordinate string into a number.  Used to convert object position and
# size attributes into a number.
#    s is the input string.
#    e is the the parent object size to do relative calculations on parent
#    size is the size of the object size (e.g. width or height)
#    font is a font object to calculate relative to font sizes
# Note some constructs for speeding up simple cases that are very common.
#
# Can do things like:  10+center-10w+4%
# To center the widget on the parent widget,
#    but move forward 10 pixels and 4% of parent width
#    and 10 character widths backward
# Multiplication, division and subexpressions are also allowed: 3*(e-c/2)
#
# Usage:  center : Center the object on parent based on parent size and object size.
#         e      : Take the parent size/width.
#         c      : Take the center point of parent size/width.
#         %      : Take given percentage of parent size/width.
#         w      : Multiply by current font width. (Only to be used in elements where the font attribute is available, i.e. not "None")
#         h      : Multiply by current font height. (Only to be used in elements where the font attribute is available, i.e. not "None")
#         f      : Replace with getSkinFactor().
#
def parseCoordinate(value, parent, size=0, font=None, scale=(1, 1)):
	def scaleNumbers(coordinate, scale):
		inNumber = False
		chars = []
		digits = []
		for char in list("%s " % coordinate):
			if char.isdigit():
				inNumber = True
				digits.append(char)
			elif inNumber:
				inNumber = False
				chars.append(str(int(int("".join(digits)) * scale[0] / scale[1])))
				digits = []
				chars.append(char)
			else:
				chars.append(char)
		return "".join(chars).strip()

	value = value.strip()
	try:
		result = int(int(value) * scale[0] / scale[1])  # For speed try a simple number first.
	except ValueError:
		if value == "center":  # For speed as this can be common case.
			return max(int((parent - size) // 2) if size else 0, 0)
		elif value == "*":
			return None
		if font is None:
			font = "Body"
			if "w" in value or "h" in value:
				print("[Skin] Warning: Coordinate 'w' and/or 'h' used but font is None, '%s' font ('%s', width=%d, height=%d) assumed!" % (font, fonts[font][0], fonts[font][3], fonts[font][2]))
		val = scaleNumbers(value, scale)
		if "center" in val:
			val = val.replace("center", str((parent - size) / 2.0))
		if "e" in val:
			val = val.replace("e", str(parent))
		if "c" in val:
			val = val.replace("c", str(parent / 2.0))
		if "%" in val:
			val = val.replace("%", "*%s" % (parent / 100.0))
		if "w" in val:
			val = val.replace("w", "*%s" % fonts[font][3])
		if "h" in val:
			val = val.replace("h", "*%s" % fonts[font][2])
		if "f" in val:
			val = val.replace("f", "%s" % getSkinFactor())
		try:
			result = int(val)  # For speed try a simple number first.
		except ValueError:
			try:
				result = int(eval(val))
			except Exception as err:
				print("[Skin] Error (%s - %s): Coordinate '%s', calculated to '%s', can't be evaluated!" % (type(err).__name__, err, value, val))
				result = 0
	# print("[Skin] parseCoordinate DEBUG: value='%s', parent='%s', size=%s, font='%s', scale='%s', result='%s'." % (value, parent, size, font, scale, result))
	return 0 if result < 0 else result


def parseFont(value, scale=((1, 1), (1, 1))):
	if ";" in value:
		(name, size) = value.split(";")
		try:
			size = int(size)
		except ValueError:
			try:
				val = size.replace("f", "%s" % getSkinFactor())
				size = int(eval(val))
			except Exception as err:
				print("[Skin] Error (%s - %s): Font size in '%s', evaluated to '%s', can't be processed!" % (type(err).__name__, err, value, val))
				size = None
	else:
		name = value
		size = None
	try:
		font = fonts[name]
		name = font[0]
		size = font[1] if size is None else size
	except KeyError:
		if name not in getFontFaces():
			font = fonts["Body"]
			print("[Skin] Error: Font '%s' (in '%s') is not defined!  Using 'Body' font ('%s') instead." % (name, value, font[0]))
			name = font[0]
			size = font[1] if size is None else size
	# print("[Skin] DEBUG: Scale font %d -> %d." % (size, int(size * scale[1][0] / scale[1][1])))
	return gFont(name, int(size * scale[1][0] / scale[1][1]))


def parseHorizontalAlignment(value):
	options = {
		"left": 0,
		"center": 1,
		"right": 2,
		"block": 3
	}
	return parseOptions(options, "horizontalAlignment", value, 0)


def parseInteger(value, default=0):
	try:
		value = int(value)
	except (TypeError, ValueError):
		skinError("The value '%s' is not a valid integer" % value)
		value = default
	return value


def parseItemAlignment(value):
	options = {
		"default": eListbox.itemAlignDefault,
		"center": eListbox.itemAlignCenter,
		"justify": eListbox.itemAlignJustify,
	}
	return parseOptions(options, "scrollbarItemAlignment", value, eListbox.itemAlignDefault)


def parseListOrientation(value):
	options = {
		"vertical": 0b01,
		"horizontal": 0b10,
		"grid": 0b11
	}
	return options.get(value, 0b01)


def parseOrientation(value):
	options = {
		"orHorizontal": 0x00,
		"orLeftToRight": 0x00,
		"orRightToLeft": 0x01,
		"orVertical": 0x10,
		"orTopToBottom": 0x10,
		"orBottomToTop": 0x11
	}
	value = parseOptions(options, "orientation", value, 0x00)
	return (value & 0x10, value & 0x01)  # (orHorizontal / orVertical, not swapped / swapped)


# Convert a parameter string into a value based on string triggers.  The type
# and value returned is based on the trigger.
#
# Usage:  *string   : The paramater is a string with the "*" is removed (Type: String).
#         #aarrggbb : The parameter is a HEX color string (Type: Integer).
#         0xABCD    : The parameter is a HEX integer (Type: Integer).
#         5.3       : The parameter is a floating point number (Type: Float).
#         red       : The parameter is a named color (Type: Integer).
#         font;zize : The parameter is a font name with a font size (Type: List[Font, Size]).
#         123       : The parameter is an integer (Type: Integer).
#
def parseParameter(value):
	"""This function is responsible for parsing parameters in the skin, it can parse integers, floats, hex colors, hex integers, named colors, fonts and strings."""
	if value[0] == "*":  # String.
		return value[1:]
	elif value[0] == "#":  # HEX Color.
		return int(value[1:], 16)
	elif value[:2] == "0x":  # HEX Integer.
		return int(value, 16)
	elif "." in value:  # Float number.
		return float(value)
	elif value in colors:  # Named color.
		return colors[value].argb()
	elif value.find(";") != -1:  # Font.
		(font, size) = [x.strip() for x in value.split(";", 1)]
		return [font, int(size)]
	else:  # Integer.
		return int(value)


def parsePixmap(path, desktop):
	option = path.find("#")
	if option != -1:
		path = path[:option]
	if isfile(path):
		pixmap = LoadPixmap(path, desktop=desktop)
		if pixmap is None:
			skinError("Pixmap file '%s' could not be loaded" % path)
	else:
		skinError("Pixmap '%s' is not found or is not a file" % path)
		pixmap = None
	return pixmap


def parsePosition(value, scale, object=None, desktop=None, size=None):
	return ePoint(*parseValuePair(value, scale, object, desktop, size))


def parseSize(value, scale, object=None, desktop=None):
	return eSize(*parseValuePair(value, scale, object, desktop))


def parseValuePair(value, scale, object=None, desktop=None, size=None):
	if value in variables:
		value = variables[value]
	(xValue, yValue) = value.split(",")  # These values will be stripped in parseCoordinate().
	parentsize = eSize()
	if object and ("c" in xValue or "c" in yValue or "e" in xValue or "e" in yValue or "%" in xValue or "%" in yValue):  # Need parent size for 'c', 'e' and '%'.
		parentsize = getParentSize(object, desktop)
	# x = xValue
	# y = yValue
	xValue = parseCoordinate(xValue, parentsize.width(), size and size.width() or 0, None, scale[0])
	yValue = parseCoordinate(yValue, parentsize.height(), size and size.height() or 0, None, scale[1])
	# print("[Skin] parseValuePair DEBUG: Scaled pair X %s -> %d, Y %s -> %d." % (x, xValue, y, yValue))
	return (xValue, yValue)


def parseScaleFlags(value):
	options = {
		"none": 0,
		"scale": BT_SCALE,
		"scaleKeepAspect": BT_SCALE | BT_KEEP_ASPECT_RATIO,
		"scaleLeftTop": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_LEFT | BT_VALIGN_TOP,
		"scaleLeftCenter": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_LEFT | BT_VALIGN_CENTER,
		"scaleLeftMiddle": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_LEFT | BT_VALIGN_CENTER,
		"scaleLeftBottom": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_LEFT | BT_VALIGN_BOTTOM,
		"scaleCenterTop": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_TOP,
		"scaleMiddleTop": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_TOP,
		"scaleCenter": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_CENTER,
		"scaleMiddle": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_CENTER,
		"scaleCenterBottom": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_BOTTOM,
		"scaleMiddleBottom": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_BOTTOM,
		"scaleRightTop": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_RIGHT | BT_VALIGN_TOP,
		"scaleRightCenter": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_RIGHT | BT_VALIGN_CENTER,
		"scaleRightMiddle": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_RIGHT | BT_VALIGN_CENTER,
		"scaleRightBottom": BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_RIGHT | BT_VALIGN_BOTTOM,
		"moveLeftTop": BT_HALIGN_LEFT | BT_VALIGN_TOP,
		"moveLeftCenter": BT_HALIGN_LEFT | BT_VALIGN_CENTER,
		"moveLeftMiddle": BT_HALIGN_LEFT | BT_VALIGN_CENTER,
		"moveLeftBottom": BT_HALIGN_LEFT | BT_VALIGN_BOTTOM,
		"moveCenterTop": BT_HALIGN_CENTER | BT_VALIGN_TOP,
		"moveMiddleTop": BT_HALIGN_CENTER | BT_VALIGN_TOP,
		"moveCenter": BT_HALIGN_CENTER | BT_VALIGN_CENTER,
		"moveMiddle": BT_HALIGN_CENTER | BT_VALIGN_CENTER,
		"moveCenterBottom": BT_HALIGN_CENTER | BT_VALIGN_BOTTOM,
		"moveMiddleBottom": BT_HALIGN_CENTER | BT_VALIGN_BOTTOM,
		"moveRightTop": BT_HALIGN_RIGHT | BT_VALIGN_TOP,
		"moveRightCenter": BT_HALIGN_RIGHT | BT_VALIGN_CENTER,
		"moveRightMiddle": BT_HALIGN_RIGHT | BT_VALIGN_CENTER,
		"moveRightBottom": BT_HALIGN_RIGHT | BT_VALIGN_BOTTOM
	}
	return parseOptions(options, "scaleFlags", value, 0)


def parseScrollbarMode(value):
	options = {
		"showOnDemand": eListbox.showOnDemand,
		"showAlways": eListbox.showAlways,
		"showNever": eListbox.showNever,
		"showLeft": eListbox.showLeftOnDemand,  # This value is deprecated to better allow option symmetry, use "showLeftOnDemand" instead.
		"showLeftOnDemand": eListbox.showLeftOnDemand,
		"showLeftAlways": eListbox.showLeftAlways,
		"showTopOnDemand": eListbox.showTopOnDemand,
		"showTopAlways": eListbox.showTopAlways
	}
	return parseOptions(options, "scrollbarMode", value, eListbox.showOnDemand)


def parseScrollbarScroll(value):
	options = {
		"byPage": 0,
		"byLine": 1
	}
	return parseOptions(options, "scrollbarScroll", value, 0)


def parseTextPadding(value):
	if value in variables:
		value = variables[value]
	padding = [parseInteger(x.strip()) for x in value.split(",")]
	count = len(padding)
	if count == 1:
		return padding * 4
	elif count == 2:
		return padding * 2
	elif count == 4:
		return padding
	print("[Skin] Error: Attribute 'textPadding' with value '%s' is invalid!  Attribute must have 1, 2 or 4 values." % value)
	return [0, 0, 0, 0]


def parseVerticalAlignment(value):
	options = {
		"top": 0,
		"center": 1,
		"middle": 1,
		"bottom": 2
	}
	return parseOptions(options, "verticalAlignment", value, 1)


def collectAttributes(skinAttributes, node, context, skinPath=None, ignore=(), filenames=frozenset(("pixmap", "pointer", "seekPointer", "seek_pointer", "backgroundPixmap", "selectionPixmap", "sliderPixmap", "scrollbarBackgroundPixmap", "scrollbarForegroundPixmap", "scrollbarbackgroundPixmap", "scrollbarBackgroundPicture", "scrollbarSliderPicture"))):
	size = None
	pos = None
	font = None
	for attrib, value in node.items():  # Walk all attributes.
		if attrib not in ignore:
			newValue = value
			if attrib in filenames:
				# DEBUG: Why does a SCOPE_LCDSKIN image replace the GUI image?!?!?!
				pngFile = resolveFilename(SCOPE_GUISKIN, value, path_prefix=skinPath)
				if not isfile(pngFile) and isfile(resolveFilename(SCOPE_LCDSKIN, value, path_prefix=skinPath)):
					pngFile = resolveFilename(SCOPE_LCDSKIN, value, path_prefix=skinPath)
				newValue = pngFile
			# Bit of a hack this, really.  When a window has a flag (e.g. wfNoBorder)
			# it needs to be set at least before the size is set, in order for the
			# window dimensions to be calculated correctly in all situations.
			# If wfNoBorder is applied after the size has been set, the window will
			# fail to clear the title area.  Similar situation for a scrollbar in a
			# listbox; when the scrollbar setting is applied after the size, a scrollbar
			# will not be shown until the selection moves for the first time.
			if attrib == "size":
				size = newValue
			elif attrib == "position":
				pos = newValue
			elif attrib == "font":
				font = newValue
				skinAttributes.append((attrib, newValue))
			else:
				skinAttributes.append((attrib, newValue))
	if pos is not None:
		pos, size = context.parse(pos, size, font)
		skinAttributes.append(("position", pos))
	if size is not None:
		skinAttributes.append(("size", size))


class AttributeParser:
	def __init__(self, guiObject, desktop, scale=((1, 1), (1, 1))):
		self.guiObject = guiObject
		self.desktop = desktop
		self.scaleTuple = scale

	def applyAll(self, attributes):
		# attributes.sort(key=lambda x: {"pixmap": 1}.get(x[0], 0))  # For SVG pixmap scale required the size, so sort pixmap last.
		for attribute, value in attributes:
			self.applyOne(attribute, value)

	def applyOne(self, attribute, value):
		try:
			getattr(self, attribute)(value)
		except Exception as err:
			print("[Skin] Error: Attribute '%s' with value '%s' in object of type '%s' (%s)!" % (attribute, value, self.guiObject.__class__.__name__, err))

	def applyHorizontalScale(self, value):
		return int(parseInteger(value) * self.scaleTuple[0][0] / self.scaleTuple[0][1])

	def applyVerticalScale(self, value):
		return int(parseInteger(value) * self.scaleTuple[1][0] / self.scaleTuple[1][1])

	def alphaTest(self, value):
		self.guiObject.setAlphatest(parseAlphaTest(value))

	def alphatest(self, value):  # This legacy definition uses an inconsistent name, use 'alphaTest' instead!
		self.alphaTest(value)
		# attribDeprecationWarning("alphatest", "alphaTest")

	def animationMode(self, value):
		self.guiObject.setAnimationMode(parseAnimationMode(value))

	def animationPaused(self, value):
		pass

	def backgroundColor(self, value):
		self.guiObject.setBackgroundColor(parseColor(value, 0x00000000))

	def backgroundColorSelected(self, value):
		self.guiObject.setBackgroundColorSelected(parseColor(value, 0x00000000))

	def backgroundCrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value, 0x00000000))

	def backgroundEncrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value, 0x00000000))

	def backgroundNotCrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value, 0x00000000))

	def backgroundPixmap(self, value):
		self.guiObject.setBackgroundPixmap(parsePixmap(value, self.desktop))

	def borderColor(self, value):
		self.guiObject.setBorderColor(parseColor(value, 0x00FFFFFF))

	def borderWidth(self, value):
		self.guiObject.setBorderWidth(self.applyVerticalScale(value))

	def conditional(self, value):
		pass

	def enableWrapAround(self, value):
		self.guiObject.setWrapAround(parseBoolean("enablewraparound", value))

	def entryFont(self, value):
		self.guiObject.setEntryFont(parseFont(value, self.scaleTuple))

	def excludes(self, value):
		pass

	def flags(self, value):
		if value in variables:
			value = variables[value]
		errors = []
		flags = [x.strip() for x in value.split(",")]
		for flag in flags:
			try:
				self.guiObject.setFlag(eWindow.__dict__[flag])
			except KeyError:
				errors.append(flag)
		if errors:
			print("[Skin] Error: Attribute 'flags' with value '%s' has invalid element(s) '%s'!" % (value, "'%s' % "', '.join(errors)))

	def font(self, value):
		self.guiObject.setFont(parseFont(value, self.scaleTuple))

	def foregroundColor(self, value):
		self.guiObject.setForegroundColor(parseColor(value, 0x00FFFFFF))

	def foregroundColorSelected(self, value):
		self.guiObject.setForegroundColorSelected(parseColor(value, 0x00FFFFFF))

	def foregroundCrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value, 0x00FFFFFF))

	def foregroundEncrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value, 0x00FFFFFF))

	def foregroundNotCrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value, 0x00FFFFFF))

	def halign(self, value):  # This legacy definition uses an inconsistent name, use 'horizontalAlignment' instead!
		self.horizontalAlignment(value)
		# attribDeprecationWarning("halign", "horizontalAlignment")

	def hAlign(self, value):  # This typo catcher definition uses an inconsistent name, use 'horizontalAlignment' instead!
		self.horizontalAlignment(value)
		# attribDeprecationWarning("hAlign", "horizontalAlignment")

	def horizontalAlignment(self, value):
		self.guiObject.setHAlign(parseHorizontalAlignment(value))

	def includes(self, value):  # Same as conditional.  Created to partner new "excludes" attribute.
		pass

	def itemHeight(self, value):
		# print("[Skin] DEBUG: Scale itemHeight %d -> %d." % (int(value), self.applyVerticalScale(value)))
		self.guiObject.setItemHeight(self.applyVerticalScale(value))

	def itemWidth(self, value):
		# print("[Skin] DEBUG: Scale itemWidth %d -> %d." % (int(value), self.applyHorizontalScale(value)))
		self.guiObject.setItemWidth(self.applyHorizontalScale(value))

	def listOrientation(self, value):  # Used by eListBox.
		self.guiObject.setOrientation(parseListOrientation(value))

	def noWrap(self, value):
		self.guiObject.setNoWrap(1 if parseBoolean("nowrap", value) else 0)
		# attribDeprecationWarning("noWrap", "wrap")

	def objectTypes(self, value):
		pass

	def orientation(self, value):  # Used by eSlider.
		self.guiObject.setOrientation(*parseOrientation(value))

	def OverScan(self, value):  # This legacy definition uses an inconsistent name, use 'overScan' instead!
		self.overScan(value)
		attribDeprecationWarning("OverScan", "overScan")

	def overScan(self, value):
		self.guiObject.setOverscan(value)

	def pixmap(self, value):
		self.guiObject.setPixmap(parsePixmap(value, self.desktop))

	def pointer(self, value):
		(name, pos) = [x.strip() for x in value.split(":", 1)]
		ptr = parsePixmap(name, self.desktop)
		pos = parsePosition(pos, self.scaleTuple)
		self.guiObject.setPointer(0, ptr, pos)

	def position(self, value):
		self.guiObject.move(ePoint(*value) if isinstance(value, tuple) else parsePosition(value, self.scaleTuple, self.guiObject, self.desktop, self.guiObject.csize()))

	def resolution(self, value):
		pass

	def scale(self, value):
		self.guiObject.setScale(1 if parseBoolean("scale", value) else 0)

	def scaleFlags(self, value):
		self.guiObject.setPixmapScaleFlags(parseScaleFlags(value))

	def scrollbarBackgroundPixmap(self, value):
		self.guiObject.setScrollbarBackgroundPixmap(parsePixmap(value, self.desktop))

	def scrollbarBackgroundPicture(self, value):  # For compatibility same as 'scrollbarBackgroundPixmap', use 'scrollbarBackgroundPixmap' instead.
		self.scrollbarBackgroundPixmap(value)
		attribDeprecationWarning("scrollbarBackgroundPicture", "scrollbarBackgroundPixmap")

	def scrollbarbackgroundPixmap(self, value):  # This legacy definition uses an inconsistent name, use'scrollbarBackgroundPixmap' instead!
		self.scrollbarBackgroundPixmap(value)
		attribDeprecationWarning("scrollbarbackgroundPixmap", "scrollbarBackgroundPixmap")

	def scrollbarItemAlignment(self, value):
		self.guiObject.setItemAlignment(parseItemAlignment(value))

	def scrollbarMode(self, value):
		self.guiObject.setScrollbarMode(parseScrollbarMode(value))

	def scrollbarScroll(self, value):
		self.guiObject.setScrollbarScroll(parseScrollbarScroll(value))

	def scrollbarBackgroundColor(self, value):
		self.guiObject.setScrollbarBackgroundColor(parseColor(value, 0x00000000))

	def scrollbarBorderColor(self, value):
		self.guiObject.setScrollbarBorderColor(parseColor(value, 0x00FFFFFF))

	def scrollbarSliderBorderColor(self, value):  # This legacy definition uses an inconsistent name, use'scrollbarBorderColor' instead!
		self.scrollbarBorderColor(value)
		attribDeprecationWarning("scrollbarSliderBorderColor", "scrollbarBorderColor")

	def scrollbarBorderWidth(self, value):
		self.guiObject.setScrollbarBorderWidth(self.applyHorizontalScale(value))

	def scrollbarSliderBorderWidth(self, value):  # This legacy definition uses an inconsistent name, use'scrollbarBorderWidth' instead!
		self.scrollbarBorderWidth(value)
		attribDeprecationWarning("scrollbarSliderBorderWidth", "scrollbarBorderWidth")

	def scrollbarForegroundColor(self, value):
		self.guiObject.setScrollbarForegroundColor(parseColor(value, 0x00FFFFFF))

	def scrollbarSliderForegroundColor(self, value):  # This legacy definition uses an inconsistent name, use'scrollbarForegroundColor' instead!
		self.scrollbarForegroundColor(value)
		attribDeprecationWarning("scrollbarSliderForegroundColor", "scrollbarForegroundColor")

	def scrollbarForegroundPixmap(self, value):
		self.guiObject.setScrollbarForegroundPixmap(parsePixmap(value, self.desktop))

	def scrollbarSliderPicture(self, value):  # This legacy definition uses an inconsistent name, use'scrollbarForegroundPixmap' instead!
		self.scrollbarForegroundPixmap(value)
		attribDeprecationWarning("scrollbarSliderPicture", "scrollbarForegroundPixmap")

	def scrollbarSliderPixmap(self, value):  # This legacy definition uses an inconsistent name, use'scrollbarForegroundPixmap' instead!
		self.scrollbarForegroundPixmap(value)
		attribDeprecationWarning("scrollbarSliderPixmap", "scrollbarForegroundPixmap")

	def scrollbarWidth(self, value):
		self.guiObject.setScrollbarWidth(self.applyHorizontalScale(value))

	def secondFont(self, value):
		self.valueFont(value)
		attribDeprecationWarning("secondFont", "valueFont")

	def secondfont(self, value):  # This legacy definition uses an inconsistent name, use 'secondFont' instead!
		self.valueFont(value)
		attribDeprecationWarning("secondfont", "valueFont")

	def seek_pointer(self, value):  # This legacy definition uses an inconsistent name, use 'seekPointer' instead!
		self.seekPointer(value)
		# attribDeprecationWarning("seek_pointer", "seekPointer")

	def seekPointer(self, value):
		(name, pos) = [x.strip() for x in value.split(":", 1)]
		ptr = parsePixmap(name, self.desktop)
		pos = parsePosition(pos, self.scaleTuple)
		self.guiObject.setPointer(1, ptr, pos)

	def selection(self, value):
		self.guiObject.setSelectionEnable(1 if parseBoolean("selection", value) else 0)

	def selectionDisabled(self, value):  # This legacy definition is a redundant option and is uncharacteristic, use 'selection="0"' etc instead!
		self.guiObject.setSelectionEnable(0 if parseBoolean("selection", value) else 1)
		# attribDeprecationWarning("selectionDisabled", "selection")

	def selectionPixmap(self, value):
		self.guiObject.setSelectionPixmap(parsePixmap(value, self.desktop))

	def shadowColor(self, value):
		self.guiObject.setShadowColor(parseColor(value, 0x00000000))

	def shadowOffset(self, value):
		self.guiObject.setShadowOffset(parsePosition(value, self.scaleTuple))

	def size(self, value):
		self.guiObject.resize(eSize(*value) if isinstance(value, tuple) else parseSize(value, self.scaleTuple, self.guiObject, self.desktop))

	def sliderPixmap(self, value):  # For compatibility same as 'scrollbarSliderPixmap', use 'scrollbarForegroundPixmap' instead.
		self.scrollbarForegroundPixmap(value)
		attribDeprecationWarning("sliderPixmap", "scrollbarForegroundPixmap")

	def text(self, value):
		if value:
			value = _(value)
		self.guiObject.setText(value)

	def textOffset(self, value):
		self.textPadding(value)
		attribDeprecationWarning("textOffset", "textPadding")

	def textPadding(self, value):
		leftPadding, topPadding, rightPadding, bottomPadding = parseTextPadding(value)
		leftPadding = self.applyHorizontalScale(leftPadding)
		topPadding = self.applyVerticalScale(topPadding)
		rightPadding = self.applyHorizontalScale(rightPadding)
		bottomPadding = self.applyVerticalScale(topPadding)
		self.guiObject.setTextPadding(eRect(leftPadding, topPadding, rightPadding, bottomPadding))

	def title(self, value):
		if value:
			value = _(value)
		self.guiObject.setTitle(value)

	def transparent(self, value):
		self.guiObject.setTransparent(1 if parseBoolean("transparent", value) else 0)

	def valign(self, value):  # This legacy definition uses an inconsistent name, use 'verticalAlignment' instead!
		self.verticalAlignment(value)
		# attribDeprecationWarning("valign", "verticalAlignment")

	def vAlign(self, value):  # This typo catcher definition uses an inconsistent name, use 'verticalAlignment' instead!
		self.verticalAlignment(value)
		# attribDeprecationWarning("vAlign", "verticalAlignment")

	def valueFont(self, value):
		self.guiObject.setValueFont(parseFont(value, self.scaleTuple))

	def verticalAlignment(self, value):
		self.guiObject.setVAlign(parseVerticalAlignment(value))

	def wrap(self, value):
		self.guiObject.setNoWrap(0 if parseBoolean("wrap", value) else 1)

	def zPosition(self, value):
		self.guiObject.setZPosition(parseInteger(value))


def applyAllAttributes(guiObject, desktop, attributes, scale=((1, 1), (1, 1))):
	AttributeParser(guiObject, desktop, scale).applyAll(attributes)


def reloadWindowStyles():
	for screenID in windowStyles:
		desktop, screenID, domSkin, pathSkin, scope = windowStyles[screenID]
		loadSingleSkinData(desktop, screenID, domSkin, pathSkin, scope=scope)


def loadSingleSkinData(desktop, screenID, domSkin, pathSkin, scope=SCOPE_GUISKIN):
	"""Loads skin data like colors, windowstyle etc."""
	assert domSkin.tag == "skin", "root element in skin must be 'skin'!"
	global colors, fonts, menus, parameters, setups, switchPixmap, resolutions, scrollLabelStyle
	for tag in domSkin.findall("output"):
		scrnID = parseInteger(tag.attrib.get("id", GUI_SKIN_ID), GUI_SKIN_ID)
		if scrnID == GUI_SKIN_ID:
			for res in tag.findall("resolution"):
				xres = parseInteger(res.attrib.get("xres", 720), 720)
				yres = parseInteger(res.attrib.get("yres", 576), 576)
				bpp = parseInteger(res.attrib.get("bpp", 32), 32)
				resolutions[scrnID] = (xres, yres, bpp)
				if bpp != 32:
					pass  # Load palette (Not yet implemented!)
	for tag in domSkin.findall("include"):
		filename = tag.attrib.get("filename")
		if filename:
			resolved = resolveFilename(scope, filename, path_prefix=pathSkin)
			if isfile(resolved):
				loadSkin(resolved, scope=scope, desktop=desktop, screenID=screenID)
			else:
				skinError("Tag 'include' needs an existing filename, got filename '%s' (%s)" % (filename, resolved))
	for tag in domSkin.findall("switchpixmap"):
		for pixmap in tag.findall("pixmap"):
			name = pixmap.attrib.get("name")
			filename = pixmap.attrib.get("filename")
			resolved = resolveFilename(scope, filename, path_prefix=pathSkin)
			if name and isfile(resolved):
				switchPixmap[name] = LoadPixmap(resolved, cached=True)
			else:
				skinError("Tag 'pixmap' needs a name and existing filename, got name='%s' and filename='%s' (%s)" % (name, filename, resolved))
	for tag in domSkin.findall("colors"):
		for color in tag.findall("color"):
			name = color.attrib.get("name")
			color = color.attrib.get("value")
			if name and color:
				colors[name] = parseColor(color, 0x00FFFFFF)
			else:
				skinError("Tag 'color' needs a name and color, got name='%s' and color='%s'" % (name, color))
	for tag in domSkin.findall("fonts"):
		for font in tag.findall("font"):
			filename = font.attrib.get("filename", "<NONAME>")
			name = font.attrib.get("name", "Regular")
			scale = font.attrib.get("scale")
			scale = int(scale) if scale and scale.isdigit() else 100
			isReplacement = font.attrib.get("replacement") and True or False
			render = font.attrib.get("render")
			render = int(render) if render and render.isdigit() else 0
			resolved = resolveFilename(SCOPE_FONTS, filename, path_prefix=pathSkin)
			if isfile(resolved) and name:
				addFont(resolved, name, scale, isReplacement, render)
				# Log provided by C++ addFont code.
				# print("[Skin] DEBUG: Font filename='%s', path='%s', name='%s', scale=%d, isReplacement=%s, render=%d." % (filename, resolved, name, scale, isReplacement, render))
			else:
				skinError("Tag 'font' needs an existing filename and name, got filename='%s' (%s) and name='%s'" % (filename, resolved, name))
		fallbackFont = resolveFilename(SCOPE_FONTS, "fallback.font", path_prefix=pathSkin)
		if isfile(fallbackFont):
			addFont(fallbackFont, "Fallback", 100, -1, 0)
		for alias in tag.findall("alias"):
			name = alias.attrib.get("name")
			font = alias.attrib.get("font")
			size = parseInteger(alias.attrib.get("size", 20), 20)
			height = parseInteger(alias.attrib.get("height", 25), 25)  # To be calculated some day.
			width = parseInteger(alias.attrib.get("width", 18), 18)  # To be calculated some day.
			if name and font and size:
				fonts[name] = (font, size, height, width)
				# print("[Skin] Add font alias: name='%s', font='%s', size=%d, height=%s, width=%d." % (name, font, size, height, width))
			else:
				skinError("Tag 'alias' needs a name, font and size, got name='%s', font'%s' and size='%s'" % (name, font, size))
	for tag in domSkin.findall("parameters"):
		for parameter in tag.findall("parameter"):
			name = parameter.attrib.get("name")
			value = parameter.attrib.get("value")
			if name and value:
				parameters[name] = list(map(parseParameter, [x.strip() for x in value.split(",")])) if "," in value else parseParameter(value)
			else:
				skinError("Tag 'parameter' needs a name and value, got name='%s' and size='%s'" % (name, value))
	for tag in domSkin.findall("menus"):
		for setup in tag.findall("menu"):
			key = setup.attrib.get("key")
			image = setup.attrib.get("image")
			if key and image:
				menus[key] = image
				# print("[Skin] DEBUG: Menu key='%s', image='%s'." % (key, image))
			else:
				skinError("Tag 'menu' needs key and image, got key='%s' and image='%s'" % (key, image))
	for tag in domSkin.findall("setups"):
		for setup in tag.findall("setup"):
			key = setup.attrib.get("key")
			image = setup.attrib.get("image")
			if key and image:
				setups[key] = image
				# print("[Skin] DEBUG: Setup key='%s', image='%s'." % (key, image))
			else:
				skinError("Tag 'setup' needs key and image, got key='%s' and image='%s'" % (key, image))
	for tag in domSkin.findall("constant-widgets"):
		for constant_widget in tag.findall("constant-widget"):
			name = constant_widget.attrib.get("name")
			if name:
				constantWidgets[name] = constant_widget
	for tag in domSkin.findall("variables"):
		for parameter in tag.findall("variable"):
			name = parameter.attrib.get("name")
			value = parameter.attrib.get("value")
			x, y = value.split(",")
			if value and name:
				variables[name] = "%s,%s" % (str(x), str(y))
	for tag in domSkin.findall("subtitles"):
		for substyle in tag.findall("sub"):
			face = eSubtitleWidget.__dict__[substyle.attrib.get("name")]
			font = parseFont(substyle.attrib.get("font"), scale=((1, 1), (1, 1)))
			foregroundColor = substyle.attrib.get("foregroundColor")
			if foregroundColor:
				haveColor = 1
				foregroundColor = parseColor(foregroundColor, 0x00FFFFFF)
			else:
				haveColor = 0
				foregroundColor = gRGB(0x00FFFFFF)
			borderColor = parseColor(substyle.attrib.get("borderColor", substyle.attrib.get("shadowColor")), 0x00000000)
			borderWidth = parseInteger(substyle.attrib.get("borderWidth", 3), 3)  # Default: Use a subtitle border.
			eSubtitleWidget.setFontStyle(face, font, haveColor, foregroundColor, borderColor, borderWidth)
	colorNameConversions = {
		"LabelForeground": "Foreground",
		"ListboxMarkedBackground": "ListboxBackgroundMarked",
		"ListboxMarkedForeground": "ListboxForegroundMarked",
		"ListboxMarkedAndSelectedBackground": "ListboxBackgroundMarkedSelected",
		"ListboxMarkedAndSelectedForeground": "ListboxForegroundMarkedSelected",
		"ListboxSelectedBackground": "ListboxBackgroundSelected",
		"ListboxSelectedForeground": "ListboxForegroundSelected"
	}
	scrollbarModes = {
		eListbox.showOnDemand: "showOnDemand",
		eListbox.showAlways: "showAlways",
		eListbox.showNever: "showNever",
		eListbox.showLeftOnDemand: "showLeftOnDemand",
		eListbox.showLeftAlways: "showLeftAlways"
	}
	scrollbarScrolls = {
		0: "byPage",
		1: "byLine"
	}
	for tag in domSkin.findall("windowstyle"):
		style = eWindowStyleSkinned()
		for borderset in tag.findall("borderset"):
			bsName = str(borderset.attrib.get("name"))
			for pixmap in borderset.findall("pixmap"):
				bpName = pixmap.attrib.get("pos")
				filename = pixmap.attrib.get("filename")
				if filename and bpName:
					png = parsePixmap(resolveFilename(scope, filename, path_prefix=pathSkin), desktop)
					try:
						style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], png)
					except Exception as err:
						skinError("Unknown style borderset name '%s' (%s)" % (bpName, err))
		for color in tag.findall("color"):
			name = color.attrib.get("name")
			name = colorNameConversions.get(name, name)
			color = parseColor(color.attrib.get("color"), 0x00FFFFFF)
			if not isinstance(color, str):
				try:
					style.setColor(eWindowStyleSkinned.__dict__["col%s" % name], color)
				except Exception as err:
					skinError("Unknown style color name '%s' (%s)" % (name, err))
		for configList in tag.findall("configList"):
			style.setEntryFont(parseFont(configList.attrib.get("entryFont", "Regular;20"), ((1, 1), (1, 1))))
			style.setValueFont(parseFont(configList.attrib.get("valueFont", "Regular;20"), ((1, 1), (1, 1))))
		for label in tag.findall("label"):
			style.setLabelFont(parseFont(label.attrib.get("font", "Regular;20"), ((1, 1), (1, 1))))
		for listBox in tag.findall("listbox"):
			pageSize = parseInteger(listBox.attrib.get("pageSize", eListbox.DefaultPageSize), eListbox.DefaultPageSize)
			enableWrapAround = parseBoolean("enableWrapAround", listBox.attrib.get("enableWrapAround", "True" if eListbox.DefaultWrapAround else "False"))
			style.setListboxFont(parseFont(listBox.attrib.get("font", "Regular;20"), ((1, 1), (1, 1))))
			scrollbarBorderWidth = parseInteger(listBox.attrib.get("scrollbarBorderWidth", eListbox.DefaultScrollBarBorderWidth), eListbox.DefaultScrollBarBorderWidth)
			if "scrollbarBorderWidth" not in scrollLabelStyle:
				scrollLabelStyle["scrollbarBorderWidth"] = scrollbarBorderWidth
			scrollbarMode = parseScrollbarMode(listBox.attrib.get("scrollbarMode", scrollbarModes[eListbox.DefaultScrollBarMode]))
			if "scrollbarMode" not in scrollLabelStyle and scrollbarMode != eListbox.showNever:
				scrollLabelStyle["scrollbarMode"] = scrollbarMode
			scrollbarOffset = parseInteger(listBox.attrib.get("scrollbarOffset", eListbox.DefaultScrollBarOffset), eListbox.DefaultScrollBarOffset)
			if "scrollbarOffset" not in scrollLabelStyle:
				scrollLabelStyle["scrollbarOffset"] = scrollbarOffset
			scrollbarScroll = parseScrollbarScroll(listBox.attrib.get("scrollbarScroll", scrollbarScrolls[eListbox.DefaultScrollBarScroll]))
			if "scrollbarScroll" not in scrollLabelStyle:
				scrollLabelStyle["scrollbarScroll"] = scrollbarScroll
			scrollbarWidth = parseInteger(listBox.attrib.get("scrollbarWidth", eListbox.DefaultScrollBarWidth), eListbox.DefaultScrollBarWidth)
			if "scrollbarWidth" not in scrollLabelStyle:
				scrollLabelStyle["scrollbarWidth"] = scrollbarWidth
			eListbox.setDefaultScrollbarStyle(scrollbarWidth, scrollbarOffset, scrollbarBorderWidth, scrollbarScroll, scrollbarMode, enableWrapAround, pageSize)
		for scrollLabel in tag.findall("scrolllabel"):
			scrollLabelStyle["scrollbarBorderWidth"] = parseInteger(scrollLabel.attrib.get("scrollbarBorderWidth", eListbox.DefaultScrollBarBorderWidth), eListbox.DefaultScrollBarBorderWidth)
			scrollLabelStyle["scrollbarMode"] = parseScrollbarMode(scrollLabel.attrib.get("scrollbarMode", scrollbarModes[eListbox.showOnDemand]))
			scrollLabelStyle["scrollbarOffset"] = parseInteger(scrollLabel.attrib.get("scrollbarOffset", eListbox.DefaultScrollBarOffset), eListbox.DefaultScrollBarOffset)
			scrollLabelStyle["scrollbarScroll"] = parseScrollbarScroll(scrollLabel.attrib.get("scrollbarScroll", scrollbarScrolls[eListbox.DefaultScrollBarScroll]))
			scrollLabelStyle["scrollbarWidth"] = parseInteger(scrollLabel.attrib.get("scrollbarWidth", eListbox.DefaultScrollBarWidth), eListbox.DefaultScrollBarWidth)
		for slider in tag.findall("slider"):
			borderWidth = parseInteger(slider.attrib.get("borderWidth", eSlider.DefaultBorderWidth), eSlider.DefaultBorderWidth)
			eSlider.setDefaultBorderWidth(borderWidth)
		for stringList in tag.findall("stringList"):
			leftPadding, topPadding, rightPadding, bottomPadding = parseTextPadding(stringList.attrib.get("textPadding", "0,0,0,0"))
			eListbox.setDefaultPadding(eRect(leftPadding, topPadding, rightPadding, bottomPadding))
		for title in tag.findall("title"):
			style.setTitleFont(parseFont(title.attrib.get("font", "Regular;20"), ((1, 1), (1, 1))))
			style.setTitleOffset(parseSize(title.attrib.get("offset", "20,5"), ((1, 1), (1, 1))))
		x = eWindowStyleManager.getInstance()
		x.setStyle(parseInteger(tag.attrib.get("id", GUI_SKIN_ID), GUI_SKIN_ID), style)
	for tag in domSkin.findall("margin"):
		r = eRect(0, 0, 0, 0)
		v = tag.attrib.get("left")
		if v:
			r.setLeft(parseInteger(v))
		v = tag.attrib.get("top")
		if v:
			r.setTop(parseInteger(v))
		v = tag.attrib.get("right")
		if v:
			r.setRight(parseInteger(v))
		v = tag.attrib.get("bottom")
		if v:
			r.setBottom(parseInteger(v))
		# The "desktop" parameter is hard-coded to the GUI screen, so we must ask
		# for the one that this actually applies to.
		getDesktop(parseInteger(tag.attrib.get("id", GUI_SKIN_ID))).setMargins(r)


class additionalWidget:
	def __init__(self):
		pass


# Class that makes a tuple look like something else. Some plugins just assume
# that size is a string and try to parse it. This class makes that work.
#
class SizeTuple(tuple):
	def __str__(self):
		return "%s,%s" % self

	def split(self, *args):
		return str(self[0]), str(self[1])

	def strip(self, *args):
		return "%s,%s" % self


class SkinContext:
	def __init__(self, parent=None, pos=None, size=None, font=None):
		if parent:
			if pos is None:
				self.x = None
				self.y = None
				self.w = None
				self.h = None
				self.scale = ((1, 1), (1, 1))
			else:
				pos, size = parent.parse(pos, size, font)
				self.x, self.y = pos
				self.w, self.h = size
				self.scale = parent.scale
		else:
			self.x = None
			self.y = None
			self.w = None
			self.h = None
			self.scale = ((1, 1), (1, 1))
		# print("[Skin] SkinContext DEBUG: parent=%s, pos=%s, size=%s, x=%s, y=%s, w=%s, h=%s, scale=%s." % (parent, pos, size, self.x, self.y, self.w, self.h, self.scale))

	def __str__(self):
		return "Context (%s,%s)+(%s,%s)" % (self.x, self.y, self.w, self.h)

	def parse(self, pos, size, font):
		if size in variables:
			size = variables[size]
		if pos == "fill":
			pos = (self.x, self.y)
			size = (self.w, self.h)
			self.w = 0
			self.h = 0
		else:
			(w, h) = size.split(",")
			w = parseCoordinate(w, self.w, 0, font, self.scale[0])
			h = parseCoordinate(h, self.h, 0, font, self.scale[1])
			if pos == "bottom":
				pos = (self.x, self.y + self.h - h)
				size = (self.w, h)
				self.h -= h
			elif pos == "top":
				pos = (self.x, self.y)
				size = (self.w, h)
				self.h -= h
				self.y += h
			elif pos == "left":
				pos = (self.x, self.y)
				size = (w, self.h)
				self.x += w
				self.w -= w
			elif pos == "right":
				pos = (self.x + self.w - w, self.y)
				size = (w, self.h)
				self.w -= w
			else:
				if pos in variables:
					pos = variables[pos]
				size = (w, h)
				pos = pos.split(",")
				pos = (self.x + parseCoordinate(pos[0], self.w, size[0], font, self.scale[0]), self.y + parseCoordinate(pos[1], self.h, size[1], font, self.scale[1]))
		# print("[Skin] SkinContext DEBUG: Scale=%s, Pos=%s, Size=%s." % (self.scale, SizeTuple(pos), SizeTuple(size)))
		return (SizeTuple(pos), SizeTuple(size))


# A context that stacks things instead of aligning them.
#
class SkinContextStack(SkinContext):
	def parse(self, pos, size, font):
		if size in variables:
			size = variables[size]
		if pos == "fill":
			pos = (self.x, self.y)
			size = (self.w, self.h)
		else:
			(w, h) = size.split(",")
			w = parseCoordinate(w, self.w, 0, font, self.scale[0])
			h = parseCoordinate(h, self.h, 0, font, self.scale[1])
			if pos == "bottom":
				pos = (self.x, self.y + self.h - h)
				size = (self.w, h)
			elif pos == "top":
				pos = (self.x, self.y)
				size = (self.w, h)
			elif pos == "left":
				pos = (self.x, self.y)
				size = (w, self.h)
			elif pos == "right":
				pos = (self.x + self.w - w, self.y)
				size = (w, self.h)
			else:
				if pos in variables:
					pos = variables[pos]
				size = (w, h)
				pos = pos.split(",")
				pos = (self.x + parseCoordinate(pos[0], self.w, size[0], font, self.scale[0]), self.y + parseCoordinate(pos[1], self.h, size[1], font, self.scale[1]))
		# print("[Skin] SkinContextStack DEBUG: Scale=%s, Pos=%s, Size=%s." % (self.scale, SizeTuple(pos), SizeTuple(size)))
		return (SizeTuple(pos), SizeTuple(size))


class SkinError(Exception):
	def __init__(self, errorMessage):
		self.errorMessage = errorMessage

	def __str__(self):
		return "[Skin] Error: %s!" % self.errorMessage


def readSkin(screen, skin, names, desktop):
	if not isinstance(names, list):
		names = [names]
	for n in names:  # Try all skins, first existing one has priority.
		myScreen, path = domScreens.get(n, (None, None))
		if myScreen is not None:
			if screen.mandatoryWidgets is None:
				screen.mandatoryWidgets = []
			else:
				widgets = findWidgets(n)
			if screen.mandatoryWidgets == [] or all(item in widgets for item in screen.mandatoryWidgets):
				name = n  # Use this name for debug output.
				break
			else:
				print("[Skin] Warning: Skin screen '%s' rejected as it does not offer all the mandatory widgets '%s'!" % (n, ", ".join(screen.mandatoryWidgets)))
				myScreen = None
	else:
		name = "<embedded-in-%s>" % screen.__class__.__name__
	if myScreen is None:  # Otherwise try embedded skin.
		myScreen = getattr(screen, "parsedSkin", None)
	if myScreen is None and getattr(screen, "skin", None):  # Try uncompiled embedded skin.
		if isinstance(screen.skin, list):
			print("[Skin] Resizable embedded skin template found in '%s'." % name)
			skin = screen.skin[0] % tuple([int(x * getSkinFactor()) for x in screen.skin[1:]])
		else:
			skin = screen.skin
		print("[Skin] Parsing embedded skin '%s'." % name)
		if isinstance(skin, tuple):
			for s in skin:
				candidate = fromstring(s)
				if candidate.tag == "screen":
					screenID = candidate.attrib.get("id")
					if (not screenID) or (parseInteger(screenID) == DISPLAY_SKIN_ID):
						myScreen = candidate
						break
			else:
				print("[Skin] No suitable screen found!")
		else:
			myScreen = fromstring(skin)
		if myScreen:
			screen.parsedSkin = myScreen
	if myScreen is None:
		print("[Skin] No skin to read or screen to display.")
		myScreen = screen.parsedSkin = fromstring("<screen></screen>")
	screen.skinAttributes = []
	skinPath = getattr(screen, "skin_path", path)  # TODO: It may be possible for "path" to be undefined!
	context = SkinContextStack()
	bounds = desktop.bounds()
	context.x = bounds.left()
	context.y = bounds.top()
	context.w = bounds.width()
	context.h = bounds.height()
	resolution = tuple([parseInteger(x.strip()) for x in myScreen.attrib.get("resolution", "%d,%d" % (context.w, context.h)).split(",")])
	context.scale = ((context.w, resolution[0]), (context.h, resolution[1]))
	del bounds
	collectAttributes(screen.skinAttributes, myScreen, context, skinPath, ignore=("name",))
	context = SkinContext(context, myScreen.attrib.get("position"), myScreen.attrib.get("size"))
	screen.additionalWidgets = []
	screen.renderer = []
	usedComponents = set()

	def processConstant(constant_widget, context):
		wname = constant_widget.attrib.get("name")
		if wname:
			try:
				cwvalue = constantWidgets[wname]
			except KeyError:
				raise SkinError("Given constant-widget '%s' not found in skin" % wname)
		if cwvalue:
			for x in cwvalue:
				myScreen.append((x))
		try:
			myScreen.remove(constant_widget)
		except ValueError:
			pass

	def processNone(widget, context):
		pass

	def processWidget(widget, context):
		# Okay, we either have 1:1-mapped widgets ("old style"), or 1:n-mapped
		# widgets (source->renderer).
		wname = widget.attrib.get("name")
		wsource = widget.attrib.get("source")
		if wname is None and wsource is None:
			raise SkinError("The widget has no name and no source")
			return
		if wname:
			# print("[Skin] DEBUG: Widget name='%s'." % wname)
			usedComponents.add(wname)
			try:  # Get corresponding "gui" object.
				attributes = screen[wname].skinAttributes = []
			except Exception:
				raise SkinError("Component with name '%s' was not found in skin of screen '%s'" % (wname, name))
			# assert screen[wname] is not Source
			collectAttributes(attributes, widget, context, skinPath, ignore=("name",))
		elif wsource:
			# print("[Skin] DEBUG: Widget source='%s'." % wsource)
			while True:  # Get corresponding source until we found a non-obsolete source.
				# Parse our current "wsource", which might specify a "related screen" before the dot,
				# for example to reference a parent, global or session-global screen.
				scr = screen
				path = wsource.split(".")  # Resolve all path components.
				while len(path) > 1:
					scr = screen.getRelatedScreen(path[0])
					if scr is None:
						raise SkinError("Specified related screen '%s' was not found in screen '%s'" % (wsource, name))
					path = path[1:]
				source = scr.get(path[0])  # Resolve the source.
				if isinstance(source, ObsoleteSource):
					# If we found an "obsolete source", issue warning, and resolve the real source.
					print("[Skin] WARNING: SKIN '%s' USES OBSOLETE SOURCE '%s', USE '%s' INSTEAD!" % (name, wsource, source.newSource))
					print("[Skin] OBSOLETE SOURCE WILL BE REMOVED %s, PLEASE UPDATE!" % source.removalDate)
					if source.description:
						print("[Skin] Source description: '%s'." % source.description)
					wsource = source.new_source
				else:
					break  # Otherwise, use the source.
			if source is None:
				raise SkinError("The source '%s' was not found in screen '%s'" % (wsource, name))
			wrender = widget.attrib.get("render")
			if not wrender:
				raise SkinError("For source '%s' a renderer must be defined with a 'render=' attribute" % wsource)
			for converter in widget.findall("convert"):
				ctype = converter.get("type")
				assert ctype, "[Skin] The 'convert' tag needs a 'type' attribute!"
				# print("[Skin] DEBUG: Converter='%s'." % ctype)
				try:
					parms = converter.text.strip()
				except Exception:
					parms = ""
				# print("[Skin] DEBUG: Params='%s'." % parms)
				try:
					converterClass = my_import(".".join(("Components", "Converter", ctype))).__dict__.get(ctype)
				except ImportError as err:
					raise SkinError("Converter '%s' not found" % ctype)
				c = None
				for i in source.downstream_elements:
					if isinstance(i, converterClass) and i.converter_arguments == parms:
						c = i
				if c is None:
					c = converterClass(parms)
					c.connect(source)
				source = c
			try:
				rendererClass = my_import(".".join(("Components", "Renderer", wrender))).__dict__.get(wrender)
			except ImportError as err:
				raise SkinError("Renderer '%s' not found" % wrender)
			renderer = rendererClass()  # Instantiate renderer.
			renderer.connect(source)  # Connect to source.
			attributes = renderer.skinAttributes = []
			collectAttributes(attributes, widget, context, skinPath, ignore=("render", "source"))
			screen.renderer.append(renderer)

	def processApplet(widget, context):
		try:
			codeText = widget.text.strip()
			widgetType = widget.attrib.get("type")
			code = compile(codeText, "skin applet", "exec")
		except Exception as err:
			raise SkinError("Applet failed to compile: '%s'" % str(err))
		if widgetType == "onLayoutFinish":
			screen.onLayoutFinish.append(code)
		else:
			raise SkinError("Applet type '%s' is unknown" % widgetType)

	def processLabel(widget, context):
		w = additionalWidget()
		w.widget = eLabel
		w.skinAttributes = []
		collectAttributes(w.skinAttributes, widget, context, skinPath, ignore=("name",))
		screen.additionalWidgets.append(w)

	def processPixmap(widget, context):
		w = additionalWidget()
		w.widget = ePixmap
		w.skinAttributes = []
		collectAttributes(w.skinAttributes, widget, context, skinPath, ignore=("name",))
		screen.additionalWidgets.append(w)

	def processScreen(widget, context):
		widgets = widget
		for w in widgets.findall('constant-widget'):
			processConstant(w, context)
		for w in widgets:
			conditional = w.attrib.get("conditional")
			if conditional and not [i for i in conditional.split(",") if i in screen.keys()]:
				continue
			objecttypes = w.attrib.get("objectTypes", "").split(",")
			if len(objecttypes) > 1 and (objecttypes[0] not in screen.keys() or not [i for i in objecttypes[1:] if i == screen[objecttypes[0]].__class__.__name__]):
				continue
			includes = w.attrib.get("includes")
			if includes and not [i for i in includes.split(",") if i in screen.keys()]:
				continue
			excludes = w.attrib.get("excludes")
			if excludes and [i for i in excludes.split(",") if i in screen.keys()]:
				continue
			p = processors.get(w.tag, processNone)
			try:
				p(w, context)
			except SkinError as err:
				print("[Skin] Error in screen '%s' widget '%s' %s!" % (name, w.tag, str(err)))

	def processPanel(widget, context):
		n = widget.attrib.get("name")
		if n:
			try:
				s = domScreens[n]
			except KeyError:
				print("[Skin] Error: Unable to find screen '%s' referred in screen '%s'!" % (n, name))
			else:
				processScreen(s[0], context)
		layout = widget.attrib.get("layout")
		cc = SkinContextStack if layout == "stack" else SkinContext
		try:
			c = cc(context, widget.attrib.get("position"), widget.attrib.get("size"), widget.attrib.get("font"))
		except Exception as err:
			raise SkinError("Failed to create skin context (position='%s', size='%s', font='%s') in context '%s': %s" % (widget.attrib.get("position"), widget.attrib.get("size"), widget.attrib.get("font"), context, err))
		processScreen(widget, c)

	processors = {
		None: processNone,
		"constant-widget": processConstant,
		"widget": processWidget,
		"applet": processApplet,
		"eLabel": processLabel,
		"ePixmap": processPixmap,
		"panel": processPanel
	}

	try:
		msg = " from list '%s'" % ", ".join(names) if len(names) > 1 else ""
		posX = "?" if context.x is None else str(context.x)
		posY = "?" if context.y is None else str(context.y)
		sizeW = "?" if context.w is None else str(context.w)
		sizeH = "?" if context.h is None else str(context.h)
		print("[Skin] Processing screen '%s'%s, position=(%s, %s), size=(%sx%s) for module '%s'." % (name, msg, posX, posY, sizeW, sizeH, screen.__class__.__name__))
		context.x = 0  # Reset offsets, all components are relative to screen coordinates.
		context.y = 0
		processScreen(myScreen, context)
	except Exception as err:
		print("[Skin] Error in screen '%s' %s!" % (name, str(err)))

	from Components.GUIComponent import GUIComponent
	unusedComponents = [x for x in set(screen.keys()) - usedComponents if isinstance(x, GUIComponent)]
	assert not unusedComponents, "[Skin] The following components in '%s' don't have a skin entry: %s" % (name, ", ".join(unusedComponents))
	# This may look pointless, but it unbinds "screen" from the nested scope. A better
	# solution is to avoid the nested scope above and use the context object to pass
	# things around.
	screen = None
	usedComponents = None


# Return a set of all the widgets found in a screen. Panels will be expanded
# recursively until all referenced widgets are captured. This code only performs
# a simple scan of the XML and no skin processing is performed.
#
def findWidgets(name):
	widgetSet = set()
	element, path = domScreens.get(name, (None, None))
	if element is not None:
		widgets = element.findall("widget")
		if widgets is not None:
			for widget in widgets:
				name = widget.get("name", None)
				if name is not None:
					widgetSet.add(name)
				source = widget.get("source", None)
				if source is not None:
					widgetSet.add(source)
		panels = element.findall("panel")
		if panels is not None:
			for panel in panels:
				name = panel.get("name", None)
				if name:
					widgetSet.update(findWidgets(name))
	return widgetSet


# This method emulates the C++ methods available to get Scrollbar style elements.
#
def getScrollLabelStyle(element):
	return scrollLabelStyle.get(element)


# Return a scaling factor (float) that can be used to rescale screen displays
# to suit the current resolution of the screen.  The scales are based on a
# default screen resolution of HD (720p).  That is the scale factor for a HD
# screen will be 1.
#
def getSkinFactor(screen=GUI_SKIN_ID):
	skinfactor = getDesktop(screen).size().height() / 720.0
	# if skinfactor not in [0.8, 1, 1.5, 3, 6]:
	# 	print("[Skin] Warning: Unexpected result for getSkinFactor '%0.4f'!" % skinfactor)
	return skinfactor


# Search the domScreens dictionary to see if any of the screen names provided
# have a skin based screen.  This will allow coders to know if the named
# screen will be skinned by the skin code.  A return of None implies that the
# code must provide its own skin for the screen to be displayed to the user.
#
def findSkinScreen(names):
	if not isinstance(names, list):
		names = [names]
	for name in names:  # Try all names given, the first one found is the one that will be used by the skin engine.
		screen, path = domScreens.get(name, (None, None))
		if screen is not None:
			return name
	return None


def dump(x, i=0):
	print(" " * i + str(x))
	try:
		for n in x.childNodes:
			dump(n, i + 1)
	except Exception:
		pass
