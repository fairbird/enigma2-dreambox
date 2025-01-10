# -*- coding: utf-8 -*-
from xml.etree.ElementTree import fromstring

from gettext import dgettext
from os.path import getmtime, join as pathjoin
from skin import findSkinScreen, parameters  # noqa: F401  used in <item conditional="..."> to check if a screen name is available in the skin

from Components.config import ConfigBoolean, ConfigNothing, ConfigSelection, config
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen, ScreenSummary
from Tools.Directories import SCOPE_PLUGINS, SCOPE_SKIN, fileReadXML, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

domSetups = {}
setupModTimes = {}


class Setup(ConfigListScreen, Screen, HelpableScreen):
	def __init__(self, session, setup=None, plugin=None, PluginLanguageDomain=None, yellow_button=None, blue_button=None, menu_button=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setup = setup
		self.plugin = plugin
		self.pluginLanguageDomain = PluginLanguageDomain
		if not isinstance(self.skinName, list):
			self.skinName = [self.skinName]
		if setup:
			self.skinName.append("Setup%s" % setup)  # DEBUG: Proposed for new setup screens.
			self.skinName.append("setup_%s" % setup)
			self.setImage(setup, "setup")
		self.skinName.append("Setup")
		self.list = []
		xmlData = setupDom(self.setup, self.plugin)
		allowDefault = False
		for setup in xmlData.findall("setup"):
			if setup.get("key") == self.setup:
				allowDefault = setup.get("allowDefault", "") in ("1", "allowDefault", "enabled", "on", "true", "yes")
				break
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry, fullUI=True, yellow_button=yellow_button, blue_button=blue_button, menu_button=menu_button)
		self["footnote"] = Label()
		self["footnote"].hide()
		self["description"] = Label()
		self.createSetup()
		if self.layoutFinished not in self.onLayoutFinish:
			self.onLayoutFinish.append(self.layoutFinished)
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def changedEntry(self):
		if isinstance(self["config"].getCurrent()[1], (ConfigBoolean, ConfigSelection)):
			self.createSetup()

	def createSetup(self, appendItems=None, prependItems=None):
		if self.setup:
			oldList = self.list
			self.showDefaultChanged = False
			self.graphicSwitchChanged = False
			self.list = prependItems or []
			title = None
			xmlData = setupDom(self.setup, self.plugin)
			for setup in xmlData.findall("setup"):
				if setup.get("key") == self.setup:
					self.addItems(setup)
					skin = setup.get("skin", None)
					if skin and skin != "":
						self.skinName.insert(0, skin)
					title = setup.get("title", None)
					# print("[Setup] [createSetup] %s" % title)
					# If this break is executed then there can only be one setup tag with this key.
					# This may not be appropriate if conditional setup blocks become available.
					break
			if appendItems:
				self.list += appendItems
			if title:
				title = dgettext(self.pluginLanguageDomain, title) if self.pluginLanguageDomain else _(title)
			self.setTitle(title if title else _("Setup"))
			if not self.list:  #If there are no eligible items available to be displayed then show at least one ConfigNothing item indicating this
				self["config"].list = [(_("No config items available"),)]
			elif self.list != oldList or self.showDefaultChanged or self.graphicSwitchChanged:
				currentItem = self["config"].getCurrent()
				self["config"].list = self.list
				if config.usage.sort_settings.value:
					self["config"].list.sort(key=lambda x: x[0])
				self.moveToItem(currentItem)

	def addItems(self, parentNode, including=True):
		for element in parentNode:
			if not element.tag:
				continue
			if element.tag in ("elif", "else") and including:
				break  # End of succesful if/elif branch - short-circuit rest of children.
			include = self.includeElement(element)
			if element.tag == "item":
				if including and include:
					self.addItem(element)
			elif element.tag == "if":
				if including:
					self.addItems(element, including=include)
			elif element.tag == "elif":
				including = include
			elif element.tag == "else":
				including = True

	def addItem(self, element):
		indent = parameters.get("SetupIndent", "  ") * int(element.get("indents", 0))
		if self.pluginLanguageDomain:
			itemText = indent + (dgettext(self.pluginLanguageDomain, x) if (x := element.get("text")) else "* fix me *")
			itemDescription = dgettext(self.pluginLanguageDomain, x) if (x := element.get("description")) else ""
		else:
			itemText = indent + (_(x) if (x := element.get("text")) else "* fix me *")
			itemDescription = _(x) if (x := element.get("description")) else ""
		restart = element.get("restart", "").lower()
		if restart == "gui" and not itemText.endswith("*"):  # Add "*" as restart indicator based on the restart attribute.
			itemText = f"{itemText}*"
		elif restart == "system" and not itemText.endswith("#"):  # Add "#" as reboot indicator based on the restart attribute.
			itemText = f"{itemText}#"
		item = eval(element.text or "")
		if item == "":
			self.list.append((self.formatItemText(itemText),))  # Add the comment line to the config list.
		elif not isinstance(item, ConfigNothing):
			self.list.append((self.formatItemText(itemText), item, self.formatItemDescription(item, itemDescription)))  # Add the item to the config list.
		if item is config.usage.setupShowDefault:
			self.showDefaultChanged = True
		if item is config.usage.boolean_graphic:
			self.graphicSwitchChanged = True

	def formatItemText(self, itemText):
		return itemText.replace("%s %s", "%s %s" % getBoxDisplayName())

	def formatItemDescription(self, item, itemDescription):
		itemDescription = itemDescription.replace("%s %s", "%s %s" % getBoxDisplayName())
		if config.usage.setupShowDefault.value != "no":
			spacer = "\n" if config.usage.setupShowDefault.value == "newline" else "  "
			itemDefault = item.toDisplayString(item.default)
			itemDescription = _("%s%s(Default: %s)") % (itemDescription, spacer, itemDefault) if itemDescription and itemDescription != " " else _("Default: '%s'.") % itemDefault
		return itemDescription

	def includeElement(self, element):
		itemLevel = int(element.get("level", 0))
		if itemLevel > config.usage.setup_level.index:  # The item is higher than the current setup level.
			return False
		requires = element.get("requires")
		if requires:
			for require in [x.strip() for x in requires.split(";")]:
				negate = require.startswith("!")
				if negate:
					require = require[1:]
				if require.startswith("config."):
					try:
						result = eval(require)
						result = bool(result.value and str(result.value).lower() not in ("0", "Disable", "disable", "False", "false", "No", "no", "Off", "off"))
					except Exception:
						return self.logIncludeElementError(element, "requires", require)
				else:
					result = bool(BoxInfo.getItem(require, False))
				if require and negate == result:  # The item requirements are not met.
					return False
		conditional = element.get("conditional")
		if conditional:
			try:
				if not bool(eval(conditional)):
					return False
			except Exception:
				return self.logIncludeElementError(element, "conditional", conditional)
		return True

	def logIncludeElementError(self, element, type, token):
		item = "title" if element.tag == "screen" else "text"
		text = element.get(item)
		print("[Setup]")
		print("[Setup] Error: Tag '%s' with %s of '%s' has a %s '%s' that can't be evaluated!" % (element.tag, item, text, type, token))
		print("[Setup] NOTE: Ignoring this error may have consequences like unexpected operation or system failures!")
		print("[Setup]")
		return False

	def layoutFinished(self):
		if not self["config"]:
			print("[Setup] No setup items available!")

	def selectionChanged(self):
		if self["config"]:
			self.setFootnote(None)
			self["description"].setText(self.getCurrentDescription())
		else:
			self["description"].setText(_("There are no items currently available for this screen."))

	def setFootnote(self, footnote):
		if footnote is None:
			if self.getCurrentEntry().endswith("*"):
				self["footnote"].setText(_("* = Restart Required"))
				self["footnote"].show()
			elif self.getCurrentEntry().endswith("#"):
				self["footnote"].setText(_("# = Reboot Required"))
				self["footnote"].show()
			else:
				self["footnote"].setText("")
				self["footnote"].hide()
		else:
			self["footnote"].setText(footnote)
			self["footnote"].setVisible(footnote != "")

	def getFootnote(self):
		return self["footnote"].text

	def moveToItem(self, item):
		if item != self["config"].getCurrent():
			self["config"].setCurrentIndex(self.getIndexFromItem(item))

	def getIndexFromItem(self, item):
		if item is None:  # If there is no item position at the top of the config list.
			return 0
		if item in self["config"].list:  # If the item is in the config list position to that item.
			return self["config"].list.index(item)
		for pos, data in enumerate(self["config"].list):
			if data[0] == item[0] and data[1] == item[1]:  # If the label and config class match then position to that item.
				return pos
		return 0  # We can't match the item to the config list then position to the top of the list.

	def createSummary(self):
		return SetupSummary


class SetupSummary(ScreenSummary):

	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")  # DEBUG: Proposed for new summary screens.
		self["value"] = StaticText("")  # DEBUG: Proposed for new summary screens.
		self["SetupTitle"] = StaticText(parent.getTitle())
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent.onChangedEntry:
			self.parent.onChangedEntry.append(self.selectionChanged)
		if self.selectionChanged not in self.parent["config"].onSelectionChanged:
			self.parent["config"].onSelectionChanged.append(self.selectionChanged)
			self.selectionChanged()
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent.onChangedEntry:
			self.parent.onChangedEntry.remove(self.selectionChanged)
		if self.selectionChanged in self.parent["config"].onSelectionChanged:
			self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["entry"].text = self.parent.getCurrentEntry()  # DEBUG: Proposed for new summary screens.
		self["value"].text = self.parent.getCurrentValue()  # DEBUG: Proposed for new summary screens.
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()


# Read the setup XML file.
#
def setupDom(setup=None, plugin=None):
	# Constants for checkItems()
	ROOT_ALLOWED = ("setup", )  # Tags allowed in top level of setupxml entry.
	ELEMENT_ALLOWED = ("item", "if")  # noqa: F841 Tags allowed in top level of setup entry.
	IF_ALLOWED = ("item", "if", "elif", "else")  # Tags allowed inside <if />.
	AFTER_ELSE_ALLOWED = ("item", "if")  # Tags allowed after <elif /> or <else />.
	CHILDREN_ALLOWED = ("setup", "if", )  # Tags that may have children.
	TEXT_ALLOWED = ("item", )  # Tags that may have non-whitespace text (or tail).
	KEY_ATTRIBUTES = {  # Tags that have a reference key mandatory attribute.
		"setup": "key",
		"item": "text"
	}
	MANDATORY_ATTRIBUTES = {  # Tags that have a list of mandatory attributes.
		"setup": ("key", "title"),
		"item": ("text", )
	}

	def checkItems(parentNode, key, allowed=ROOT_ALLOWED, mandatory=MANDATORY_ATTRIBUTES, reference=KEY_ATTRIBUTES):
		keyText = " in '%s'" % key if key else ""
		for element in parentNode:
			if element.tag not in allowed:
				print("[Setup] Error: Tag '%s' not permitted%s!  (Permitted: '%s')" % (element.tag, keyText, ", ".join(allowed)))
				continue
			if mandatory and element.tag in mandatory:
				valid = True
				for attrib in mandatory[element.tag]:
					if element.get(attrib) is None:
						print("[Setup] Error: Tag '%s'%s does not contain the mandatory '%s' attribute!" % (element.tag, keyText, attrib))
						valid = False
				if not valid:
					continue
			if element.tag not in TEXT_ALLOWED:
				if element.text and not element.text.isspace():
					print("[Setup] Tag '%s'%s contains text '%s'." % (element.tag, keyText, element.text.strip()))
				if element.tail and not element.tail.isspace():
					print("[Setup] Tag '%s'%s has trailing text '%s'." % (element.tag, keyText, element.text.strip()))
			if element.tag not in CHILDREN_ALLOWED and len(element):
				itemKey = ""
				if element.tag in reference:
					itemKey = " (%s)" % element.get(reference[element.tag])
				print("[Setup] Tag '%s'%s%s contains children where none expected." % (element.tag, itemKey, keyText))
			if element.tag in CHILDREN_ALLOWED:
				if element.tag in reference:
					key = element.get(reference[element.tag])
				checkItems(element, key, allowed=IF_ALLOWED)
			elif element.tag == "else":
				allowed = AFTER_ELSE_ALLOWED  # else and elif not permitted after else
			elif element.tag == "elif":
				pass

	setupFileDom = fromstring("<setupxml />")
	setupFile = resolveFilename(SCOPE_PLUGINS, pathjoin(plugin, "setup.xml")) if plugin else resolveFilename(SCOPE_SKIN, "setup.xml")
	global domSetups, setupModTimes
	try:
		modTime = getmtime(setupFile)
	except OSError as err:
		print("[Setup] Error %d: Unable to get '%s' modified time!  (%s)" % (err.errno, setupFile, err.strerror))
		if setupFile in domSetups:
			del domSetups[setupFile]
		if setupFile in setupModTimes:
			del setupModTimes[setupFile]
		return setupFileDom  # we can't access setup.xml so return an empty dom
	cached = setupFile in domSetups and setupFile in setupModTimes and setupModTimes[setupFile] == modTime
	print("[Setup] XML%s setup file '%s', using element '%s'%s." % (" cached" if cached else "", setupFile, setup, " from plugin '%s'" % plugin if plugin else ""))
	if cached:
		return domSetups[setupFile]
	if setupFile in domSetups:
		del domSetups[setupFile]
	if setupFile in setupModTimes:
		del setupModTimes[setupFile]
	fileDom = fileReadXML(setupFile, source=MODULE_NAME)
	if fileDom is not None:
		checkItems(fileDom, None)
		setupFileDom = fileDom
		domSetups[setupFile] = setupFileDom
		setupModTimes[setupFile] = modTime
		for setup in setupFileDom.findall("setup"):
			key = setup.get("key")
			if key:  # If there is no key then this element is useless and can be skipped!
				title = setup.get("title", "")
				if title == "":
					print("[Setup] Error: Setup key '%s' title is missing or blank!" % key)
					title = "** Setup error: '%s' title is missing or blank!" % key
				# print("[Setup] DEBUG: XML setup load: key='%s', title='%s'." % (key, setup.get("title", "").encode("UTF-8", errors="ignore")))
	return setupFileDom


# Temporary legacy interface.
# Not used any enigma2 module. Known to be used by the Heinz plugin.
#

def setupdom(setup=None, plugin=None):
	return setupDom(setup, plugin)


# Only used in AudioSelection screen...
#

def getConfigMenuItem(configElement):
	for item in setupDom().findall("./setup/item/."):
		if item.text == configElement:
			return _(item.attrib["text"]), eval(configElement)
	return "", None

# Temporary legacy interfaces.  Only used in Menu screen.
#
def getSetupTitle(id):
	xmlData = setupDom()
	for x in xmlData.findall("setup"):
		if x.get("key") == id:
			return x.get("title", "")
	print("[Setup] Error: Unknown setup id '%s'!" % repr(id))
	return "Unknown setup id '%s'!" % repr(id)


def getSetupTitleLevel(setupId):
	xmlData = setupDom()
	for x in xmlData.findall("setup"):
		if x.get("key") == setupId:
			return int(x.get("level", 0))
	return 0
