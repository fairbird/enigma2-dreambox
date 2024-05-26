# -*- coding: utf-8 -*-
import os
from os import fsync, rename, sep
from os.path import realpath
from copy import copy as shallowcopy
from time import localtime, strftime, struct_time

from enigma import getPrevAsciiCode

from Tools.Directories import SCOPE_CONFIG, fileExists, fileAccess, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput
from Components.Harddisk import harddiskmanager  # This import is order critical!


ACTIONKEY_LEFT = 0
ACTIONKEY_RIGHT = 1
ACTIONKEY_SELECT = 2
ACTIONKEY_DELETE = 3
ACTIONKEY_BACKSPACE = 4
ACTIONKEY_FIRST = 5
ACTIONKEY_LAST = 6
ACTIONKEY_TOGGLE = 7
ACTIONKEY_ASCII = 8
ACTIONKEY_TIMEOUT = 9
ACTIONKEY_NUMBERS = list(range(12, 12 + 10))
ACTIONKEY_0 = 12
ACTIONKEY_1 = 13
ACTIONKEY_2 = 14
ACTIONKEY_3 = 15
ACTIONKEY_4 = 16
ACTIONKEY_5 = 17
ACTIONKEY_6 = 18
ACTIONKEY_7 = 19
ACTIONKEY_8 = 20
ACTIONKEY_9 = 21
ACTIONKEY_PAGEUP = 22
ACTIONKEY_PAGEDOWN = 23
ACTIONKEY_PREV = 24
ACTIONKEY_NEXT = 25
ACTIONKEY_ERASE = 26

# Deprecated / Legacy action key names...
#
# (These should be removed when all Enigma2 uses the new and less confusing names.)
#
KEY_LEFT = ACTIONKEY_LEFT
KEY_RIGHT = ACTIONKEY_RIGHT
KEY_OK = ACTIONKEY_SELECT
KEY_DELETE = ACTIONKEY_DELETE
KEY_BACKSPACE = ACTIONKEY_BACKSPACE
KEY_HOME = ACTIONKEY_FIRST
KEY_END = ACTIONKEY_LAST
KEY_TOGGLEOW = ACTIONKEY_TOGGLE
KEY_ASCII = ACTIONKEY_ASCII
KEY_TIMEOUT = ACTIONKEY_TIMEOUT
KEY_NUMBERS = ACTIONKEY_NUMBERS
KEY_0 = ACTIONKEY_0
KEY_9 = ACTIONKEY_9


def getKeyNumber(key):
	if key not in ACTIONKEY_NUMBERS:
		raise ValueError("[Config] Error: The key '%s' is not a numeric digit!" % key)
	return key - ACTIONKEY_0


def getConfigListEntry(*args):
	assert len(args) > 0, "getConfigListEntry needs a minimum of one argument (descr, configElement)"
	return args


def updateConfigElement(element, newelement):
	newelement.value = element.value
	return newelement


def NoSave(element):
	element.disableSave()
	return element


# ConfigElement, the base class of all ConfigElements.

# it stores:
#   value    the current value.
#            usually a property which retrieves _value,
#            and maybe does some reformatting
#   _value   the value as it's going to be saved in the configfile,
#            though still in non-string form.
#            this is the object which is actually worked on.
#   default  the initial value. If _value is equal to default,
#            it will not be stored in the config file
#   saved_value is a text representation of _value, stored in the config file
#
# and has (at least) the following methods:
#   save()   stores _value into saved_value,
#            (or stores 'None' if it should not be stored)
#   load()   loads _value from saved_value, or loads
#            the default if saved_value is 'None' (default)
#            or invalid.
#
class ConfigElement(object):
	def __init__(self):
		self.saved_value = None
		self.save_forced = False
		self.lastValue = None
		self.save_disabled = False
		self.__notifiers = None
		self.__notifiers_final = None
		self.enabled = True
		self.callNotifiersOnSaveAndCancel = False

	def getNotifiers(self):
		if self.__notifiers is None:
			self.__notifiers = []
		return self.__notifiers

	def setNotifiers(self, val):
		self.__notifiers = val

	notifiers = property(getNotifiers, setNotifiers)

	def getNotifiersFinal(self):
		if self.__notifiers_final is None:
			self.__notifiers_final = []
		return self.__notifiers_final

	def setNotifiersFinal(self, val):
		self.__notifiers_final = val

	notifiers_final = property(getNotifiersFinal, setNotifiersFinal)

	# you need to override this to do input validation
	def setValue(self, value):
		self._value = value
		self.changed()

	def getNotifierNeeded(self):
		if self.prev_value != self.value:
			self.prev_value = self.value
			return True

	def getValue(self):
		return self._value

	value = property(getValue, setValue)

	# you need to override this if self.value is not a string
	def fromString(self, value):
		return value

	# you can overide this for fancy default handling
	def load(self):
		sv = self.saved_value
		if sv is None:
			self.value = self.default
		else:
			self.value = self.fromString(sv)

	def toString(self, value):
		return str(value)

	# You need to override this to do appropriate value conversion to a displayable string in the Setup / ConfigList UI.
	def toDisplayString(self, value):
		return str(value)

	# you need to override this if str(self.value) doesn't work
	def save(self):
		if self.save_disabled or (self.value == self.default and not self.save_forced):
			self.saved_value = None
		else:
			self.saved_value = self.toString(self.value)
		if self.callNotifiersOnSaveAndCancel:
			self.changed()

	def cancel(self):
		self.load()
		if self.callNotifiersOnSaveAndCancel:
			self.changed()

	def isChanged(self):
		sv = self.saved_value
		if sv is None and self.value == self.default:
			return False
		return self.toString(self.value) != sv

	def changed(self):
		if self.__notifiers:
			for x in self.notifiers:
				x(self)

	def changedFinal(self):
		if self.__notifiers_final:
			for x in self.notifiers_final:
				x(self)

	def addNotifier(self, notifier, initial_call=True, immediate_feedback=True):
		assert callable(notifier), "notifiers must be callable"
		if immediate_feedback:
			self.notifiers.append(notifier)
		else:
			self.notifiers_final.append(notifier)
		# CHECKME:
		# do we want to call the notifier
		#  - at all when adding it? (yes, though optional)
		#  - when the default is active? (yes)
		#  - when no value *yet* has been set,
		#    because no config has ever been read (currently yes)
		#    (though that's not so easy to detect.
		#     the entry could just be new.)
		if initial_call:
			notifier(self)

	def removeNotifier(self, notifier):
		notifier in self.notifiers and self.notifiers.remove(notifier)
		notifier in self.notifiers_final and self.notifiers_final.remove(notifier)

	def disableSave(self):
		self.save_disabled = True

	def __call__(self, selected):
		return self.getMulti(selected)

	def onSelect(self, session):
		pass

	def onDeselect(self, session):
		if not self.lastValue == self.value:
			self.changedFinal()
			self.lastValue = self.value

	def hideHelp(self, session):
		pass

	def showHelp(self, session):
		pass


class choicesList():  # XXX: we might want a better name for this
	LIST_TYPE_LIST = 1
	LIST_TYPE_DICT = 2

	def __init__(self, choices, type=None):
		self.choices = choices
		if type is None:
			if isinstance(choices, list):
				self.type = choicesList.LIST_TYPE_LIST
			elif isinstance(choices, dict):
				self.type = choicesList.LIST_TYPE_DICT
			else:
				assert False, "choices must be dict or list!"
		else:
			self.type = type

	def __list__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[0] for x in self.choices]
		else:
			ret = list(self.choices.keys())
		return ret or [""]

	def __iter__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[0] for x in self.choices]
		else:
			ret = self.choices
		return iter(ret or [""])

	def __len__(self):
		return len(self.choices) or 1

	def __getitem__(self, index):
		if index == 0 and not self.choices:
			return ""
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = self.choices[index]
			if isinstance(ret, tuple):
				ret = ret[0]
			return ret
		return list(self.choices.keys())[index]

	def index(self, value):
		try:
			return list(map(str, self.__list__())).index(str(value))
		except (ValueError, IndexError):
			# occurs e.g. when default is not in list
			return 0

	def __setitem__(self, index, value):
		if index == 0 and not self.choices:
			return
		if self.type == choicesList.LIST_TYPE_LIST:
			orig = self.choices[index]
			if isinstance(orig, tuple):
				self.choices[index] = (value, orig[1])
			else:
				self.choices[index] = value
		else:
			key = list(self.choices.keys())[index]
			orig = self.choices[key]
			del self.choices[key]
			self.choices[value] = orig

	def default(self):
		choices = self.choices
		if not choices:
			return ""
		if self.type is choicesList.LIST_TYPE_LIST:
			default = choices[0]
			if isinstance(default, tuple):
				default = default[0]
		else:
			default = list(choices.keys())[0]
		return default


class descriptionList(choicesList):  # XXX: we might want a better name for this
	def __list__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[1] for x in self.choices]
		else:
			ret = list(self.choices.values())
		return ret or [""]

	def __iter__(self):
		return iter(self.__list__())

	def __getitem__(self, index):
		if self.type == choicesList.LIST_TYPE_LIST:
			for x in self.choices:
				if isinstance(x, tuple):
					if str(x[0]) == str(index):
						return str(x[1])
				elif str(x) == str(index):
					return str(x)
			return str(index)  # Fallback!
		else:
			return str(self.choices.get(index, ""))

	def __setitem__(self, index, value):
		if not self.choices:
			return
		if self.type == choicesList.LIST_TYPE_LIST:
			i = self.index(index)
			orig = self.choices[i]
			if isinstance(orig, tuple):
				self.choices[i] = (orig[0], value)
			else:
				self.choices[i] = value
		else:
			self.choices[index] = value

#
# ConfigSelection is a "one of.."-type.  it has the "choices", usually
# a list, which contains (id, desc)-tuples (or just only the ids, in
# case str(id) will be used as description)
#
# The ids in "choices" may be of any type, provided that for there
# is a one-to-one mapping between x and str(x) for every x in "choices".
# The ids do not necessarily all have to have the same type, but
# managing that is left to the programmer.  For example:
#  choices=[1, 2, "3", "4"] is permitted, but
#  choices=[1, 2, "1", "2"] is not,
# because str(1) == "1" and str("1") =="1", and because str(2) == "2"
# and str("2") == "2".
#
# This requirement is not enforced by the code.
#
# config.item.value and config.item.getValue always return an object
# of the type of the selected item.
#
# When assigning to config.item.value or using config.item.setValue,
# where x is in the "choices" list, either x or str(x) may be used
# to set the choice. The form of the assignment will not affect the
# choices list or the type returned by the ConfigSelection instance.
#
# This replaces the former requirement that all ids MUST be plain
# strings, but is compatible with that requirement.
#


class ConfigSelection(ConfigElement):
	def __init__(self, choices, default=None, graphic=True):
		ConfigElement.__init__(self)
		self.choices = choicesList(choices)

		if default is None:
			default = self.choices.default()

		self._descr = None
		self.default = self._value = self.lastValue = self.prev_value = default
		self.graphic = graphic

	def setSelectionList(self, choices, default=None):
		value = self.value
		self.choices = choicesList(choices)
		if default is None:
			default = self.choices.default()
		self.default = default
		if self.value not in self.choices:
			self.value = default
		if self.value != value:
			self.changed()

	def setChoices(self, choices, default=None):
		return self.setSelectionList(choices, default=default)

	def getChoices(self):
		return self.choices.choices

	def getDescriptions(self):
		return self.description.__list__()

	def getSelectionList(self):
		return list(zip(self.choices.__list__(), self.description.__list__()))

	def setValue(self, value):
		if str(value) in map(str, self.choices):
			self._value = self.choices[self.choices.index(value)]
		else:
			self._value = self.default
		self._descr = None
		self.changed()

	def toString(self, val):
		return str(val)

	def toDisplayString(self, val):
		return self.description[val]

	def getValue(self):
		return self._value

	def load(self):
		sv = self.saved_value
		if sv is None:
			self.value = self.default
		else:
			self.value = self.choices[self.choices.index(sv)]

	def setCurrentText(self, text):
		i = self.choices.index(self.value)
		self.choices[i] = text
		self._descr = self.description[text] = text
		self._value = text

	value = property(getValue, setValue)

	def getIndex(self):
		return self.choices.index(self.value)

	index = property(getIndex)

	# GUI
	def handleKey(self, key):
		count = len(self.choices)
		if count > 1:
			prev = str(self.value)
			index = self.choices.index(str(self.value))  # Temporary hack until keys don't have to be strings.
			if key == ACTIONKEY_LEFT:
				self.value = self.choices[(index + count - 1) % count]
			elif key == ACTIONKEY_RIGHT:
				self.value = self.choices[(index + 1) % count]
			elif key == ACTIONKEY_FIRST:
				self.value = self.choices[0]
			elif key == ACTIONKEY_LAST:
				self.value = self.choices[count - 1]
			if str(self.value) != prev:
				self.changed()

	def selectNext(self):
		nchoices = len(self.choices)
		i = self.choices.index(self.value)
		self.value = self.choices[(i + 1) % nchoices]

	def getText(self):
		if self._descr is None:
			self._descr = self.description[self.value]
		return self._descr

	def getMulti(self, selected):
		if self._descr is None:
			self._descr = self.description[self.value]
		from Components.config import config
		from skin import switchPixmap
		if self.graphic and config.usage.boolean_graphic.value == "true" and "menu_on" in switchPixmap and "menu_off" in switchPixmap:
			pixmap = "menu_on" if self._descr in (_('True'), _('true'), _('Yes'), _('yes'), _('Enable'), _('enable'), _('Enabled'), _('enabled'), _('On'), _('on')) else "menu_off" if self._descr in (_('False'), _('false'), _('No'), _('no'), _("Disable"), _('disable'), _('Disabled'), _('disabled'), _('Off'), _('off'), _('None'), _('none')) else None
			if pixmap:
				return ('pixmap', switchPixmap[pixmap])
		return ("text", self._descr)

	# HTML
	def getHTML(self, id):
		res = ""
		for v in self.choices:
			descr = self.description[v]
			if self.value == v:
				checked = 'checked="checked" '
			else:
				checked = ''
			res += '<input type="radio" name="' + id + '" ' + checked + 'value="' + v + '">' + descr + "</input></br>\n"
		return res

	def unsafeAssign(self, value):
		# setValue does check if value is in choices. This is safe enough.
		self.value = value

	description = property(lambda self: descriptionList(self.choices.choices, self.choices.type))

# a binary decision.
#
# several customized versions exist for different
# descriptions.
#


class ConfigBoolean(ConfigElement):
	def __init__(self, default=False, descriptions={False: _("false"), True: _("true")}, graphic=True):
		ConfigElement.__init__(self)
		self.descriptions = descriptions
		self.value = self.lastValue = self.prev_value = self.default = default
		self.graphic = graphic

	def handleKey(self, key):
		if key in (ACTIONKEY_TOGGLE, ACTIONKEY_SELECT, ACTIONKEY_LEFT, ACTIONKEY_RIGHT):
			self.value = not self.value
		elif key == ACTIONKEY_FIRST:
			self.value = False
		elif key == ACTIONKEY_LAST:
			self.value = True

	def getText(self):
		return self.descriptions[self.value]

	def getMulti(self, selected):
		from Components.config import config
		from skin import switchPixmap
		if self.graphic and config.usage.boolean_graphic.value in ("true", "only_bool") and "menu_on" in switchPixmap and "menu_off" in switchPixmap:
			return ('pixmap', switchPixmap["menu_on" if self.value else "menu_off"])
		return ("text", self.descriptions[self.value])

	def toString(self, value):
		if not value:
			return "false"
		else:
			return "true"

	def fromString(self, val):
		if val == "true":
			return True
		else:
			return False

	def getHTML(self, id):
		if self.value:
			checked = ' checked="checked"'
		else:
			checked = ''
		return '<input type="checkbox" name="' + id + '" value="1" ' + checked + " />"

	# this is FLAWED. and must be fixed.
	def unsafeAssign(self, value):
		if value == "1":
			self.value = True
		else:
			self.value = False

	def onDeselect(self, session):
		if not self.lastValue == self.value:
			self.changedFinal()
			self.lastValue = self.value

	def toDisplayString(self, value):
		return self.descriptions[True] if value or str(value).lower() in self.trueValues else self.descriptions[False]


class ConfigYesNo(ConfigBoolean):
	def __init__(self, default=False, graphic=True):
		ConfigBoolean.__init__(self, default=default, descriptions={False: _("no"), True: _("yes")}, graphic=graphic)


class ConfigOnOff(ConfigBoolean):
	def __init__(self, default=False, graphic=True):
		ConfigBoolean.__init__(self, default=default, descriptions={False: _("off"), True: _("on")}, graphic=graphic)


class ConfigEnableDisable(ConfigBoolean):
	def __init__(self, default=False, graphic=True):
		ConfigBoolean.__init__(self, default=default, descriptions={False: _("disable"), True: _("enable")}, graphic=graphic)


class ConfigDateTime(ConfigElement):
	def __init__(self, default, formatstring, increment=86400):
		ConfigElement.__init__(self)
		self.increment = increment
		self.formatstring = formatstring
		self.value = self.lastValue = self.prev_value = self.default = int(default)

	def handleKey(self, key):
		if key == ACTIONKEY_LEFT:
			self.value -= self.increment
		elif key == ACTIONKEY_RIGHT:
			self.value += self.increment
		elif key == ACTIONKEY_FIRST or key == ACTIONKEY_LAST:
			self.value = self.default

	def getText(self):
		return strftime(self.formatstring, localtime(self.value))

	def getMulti(self, selected):
		return ("text", strftime(self.formatstring, localtime(self.value)))

	def fromString(self, val):
		return int(val)

	def toDisplayString(self, value):
		return strftime(self.formatString, localtime(value))

# *THE* mighty config element class
#
# allows you to store/edit a sequence of values.
# can be used for IP-addresses, dates, plain integers, ...
# several helper exist to ease this up a bit.
#


class ConfigSequence(ConfigElement):
	def __init__(self, seperator, limits, default, censor="", censor_char=None):  # Should we also have a flag to select blocks on first entry?
		ConfigElement.__init__(self)
		if not isinstance(limits, list) and len(limits[0]) != 2:
			raise TypeError("[Config] Error: Limits must be [(min, max), ...] tuple-list!")
		# if not isinstance(default, list):
		# 	raise TypeError("[Config] Error: Default must be a list!")
		# if not all([isinstance(x, int) for x in default]):
		# 	raise TypeError("[Config] Error: Default list must consist of numbers!")
		# if len(default) != len(limits):
		# 	raise ValueError("[Config] Error: Lengths of default and limits must match!")
		if censor_char is not None:  # DEBUG: This captures the censor character from legacy code!
			censor = censor_char
		if censor != "" and (isinstance(censor, str) and len(censor) != 1) and (isinstance(censor, unicode) and len(censor) != 1):
			raise ValueError("[Config] Error: Censor must be a single char (or \"\")!")
		self.seperator = seperator
		self.limits = limits
		self.blockLen = [len(str(x[1])) for x in limits]
		self.totalLen = sum(self.blockLen) - 1
		self.censor = censor
		self.lastValue = self.prev_value = self.default = default
		self.value = shallowcopy(default)
		self.hidden = censor != ""
		self.endNotifier = None
		self.markedPos = 0
		self.zeroPad = True

	def handleKey(self, key, callback=None):
		if key == ACTIONKEY_FIRST:
			self.markedPos = 0
		elif key == ACTIONKEY_LEFT:
			if self.markedPos > 0:
				self.markedPos -= 1
		elif key == ACTIONKEY_RIGHT:
			if self.markedPos < self.totalLen:
				self.markedPos += 1
		elif key == ACTIONKEY_LAST:
			self.markedPos = self.totalLen
		elif key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			# prev = self._value
			if key == ACTIONKEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)
			pos = 0
			blockNumber = 0
			block_len_total = [0]
			for x in self.blockLen:
				pos += self.blockLen[blockNumber]
				block_len_total.append(pos)
				if pos - 1 >= self.markedPos:
					pass
				else:
					blockNumber += 1
			number_len = len(str(self.limits[blockNumber][1]))  # Length of number block.
			posinblock = self.markedPos - block_len_total[blockNumber]  # Position in the block.
			oldvalue = abs(self._value[blockNumber])  # We are using abs() in order to allow change negative values like default -1.
			olddec = oldvalue % 10 ** (number_len - posinblock) - (oldvalue % 10 ** (number_len - posinblock - 1))
			newvalue = oldvalue - olddec + (10 ** (number_len - posinblock - 1) * number)
			self._value[blockNumber] = newvalue
			self.markedPos += 1
			self.validate()
			# if self._value != prev:
			self.changed()
			if callable(callback):
				callback()

	def validate(self):
		maxPos = 0
		num = 0
		for i in self._value:
			maxPos += len(str(self.limits[num][1]))

			if self._value[num] < self.limits[num][0]:
				self._value[num] = self.limits[num][0]
			if self._value[num] > self.limits[num][1]:
				self._value[num] = self.limits[num][1]
			num += 1
		if self.markedPos >= maxPos:
			if self.endNotifier:
				for x in self.endNotifier:
					x(self)
			self.markedPos = maxPos - 1
		if self.markedPos < 0:
			self.markedPos = 0

	def getText(self):
		(value, mPos) = self.genText()
		return value

	def getMulti(self, selected):
		(value, mPos) = self.genText()
		# Only mark cursor when we are selected.  (This code is heavily ink optimized!)
		if self.enabled:
			return ("mtext"[1 - selected:], value, [mPos])
		else:
			return ("text", value)

	def genText(self):
		value = ""
		mPos = self.markedPos
		num = 0
		for i in self._value:
			if value:  # Fixme no heading separator possible!
				value += self.seperator
				if mPos >= len(value) - 1:
					mPos += 1
			if self.censor == "" or not self.hidden:
				value += ("%0" + str(len(str(self.limits[num][1]))) + "d") % i
			else:
				value += (self.censor * len(str(self.limits[num][1])))
			num += 1
		return (value, mPos)

	def fromString(self, value):
		ret = [int(x) for x in value.split(self.seperator)]
		return ret + [int(x[0]) for x in self.limits[len(ret):]]

	def toString(self, value):
		return self.seperator.join([str(x) for x in value])

	def toDisplayString(self, value):
		return self.seperator.join(["%%0%sd" % (str(self.blockLen[index]) if self.zeroPad else "") % value for index, value in enumerate(self._value)])

	def onSelect(self, session):
		self.hidden = False

	def onDeselect(self, session):
		self.hidden = self.censor != ""
		# DEBUG: This triggers false deselection change notifications!
		# if self.lastValue != self._value:
		# 	self.changedFinal()
		# 	self.lastValue = shallowcopy(self._value)

	def addEndNotifier(self, notifier):
		if self.endNotifier is None:
			self.endNotifier = []
		self.endNotifier.append(notifier)


ip_limits = [(0, 255), (0, 255), (0, 255), (0, 255)]


class ConfigIP(ConfigSequence):
	def __init__(self, default, auto_jump=False):
		ConfigSequence.__init__(self, seperator=".", limits=ip_limits, default=default)
		self.blockLen = [len(str(x[1])) for x in self.limits]
		self.marked_block = 0
		self.overwrite = True
		self.auto_jump = auto_jump

	def handleKey(self, key):
		if key == ACTIONKEY_FIRST:
			self.markedPos = 0
			self.overwrite = True
		elif key == ACTIONKEY_LEFT:
			if self.markedPos > 0:
				self.markedPos -= 1
			self.overwrite = True
		elif key == ACTIONKEY_RIGHT:
			if self.markedPos < len(self.limits) - 1:
				self.markedPos += 1
			self.overwrite = True
		elif key == ACTIONKEY_LAST:
			self.markedPos = len(self.limits) - 1
			self.overwrite = True
		elif key in (ACTIONKEY_DELETE, ACTIONKEY_BACKSPACE):
			self._value[self.markedPos] = 0
			self.overwrite = True
		elif key == ACTIONKEY_ERASE:
			self.markedPos = 0
			self._value = [0, 0, 0, 0]
			self.overwrite = True
		elif key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			if key == ACTIONKEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)
			prev = self._value[:]
			if self.overwrite:
				self._value[self.markedPos] = number
				self.overwrite = False
			else:
				newValue = (self._value[self.markedPos] * 10) + number
				if self.auto_jump and newValue > self.limits[self.markedPos][1] and self.markedPos < len(self.limits) - 1:
					self.handleKey(ACTIONKEY_RIGHT)
					self.handleKey(key)
					return
				else:
					self._value[self.markedPos] = newValue
			if len(str(self._value[self.markedPos])) >= self.blockLen[self.markedPos]:
				self.handleKey(ACTIONKEY_RIGHT)
			self.validate()
			if self._value != prev:
				self.changed()

	def genText(self):
		value = self.seperator.join([str(x) for x in self._value])
		blockLen = [len(str(x)) for x in self._value]
		leftPos = sum(blockLen[:self.markedPos]) + self.markedPos
		rightPos = sum(blockLen[:self.markedPos + 1]) + self.markedPos
		mBlock = list(range(leftPos, rightPos))
		return (value, mBlock)

	def getMulti(self, selected):
		(value, mBlock) = self.genText()
		return ("mtext"[1 - selected:], value, mBlock) if self.enabled else ("text", value)

	def getHTML(self, id=0):
		# I do not know why id is here but it is used in the sources renderer and I'm afraid we should keep it for compatibily. It is not used here but I give at a default value
		# we definitely don't want leading zeros
		return '.'.join(["%d" % d for d in self.value])


class ConfigMAC(ConfigSequence):
	def __init__(self, default):
		ConfigSequence.__init__(self, seperator=":", limits=[(0, 255), (0, 255), (0, 255), (0, 255), (0, 255), (0, 255)], default=default)


class ConfigPosition(ConfigSequence):
	def __init__(self, default, args):
		ConfigSequence.__init__(self, seperator=",", limits=[(0, args[0]), (0, args[1]), (0, args[2]), (0, args[3])], default=default)


class ConfigClock(ConfigSequence):
	def __init__(self, default):
		self.time = localtime(default)
		ConfigSequence.__init__(self, seperator=":", limits=[(0, 23), (0, 59)], default=[self.time.tm_hour, self.time.tm_min])

	def handleKey(self, key, callback=None):
		if key == ACTIONKEY_DELETE and config.usage.time.wide.value:
			if self._value[0] < 12:
				self._value[0] += 12
				self.validate()
				self.changed()
		elif key == ACTIONKEY_BACKSPACE and config.usage.time.wide.value:
			if self._value[0] >= 12:
				self._value[0] -= 12
				self.validate()
				self.changed()
		elif key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			if key == ACTIONKEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				digit = code - 48
			else:
				digit = getKeyNumber(key)
			hour = self._value[0]
			pmadjust = 0
			if config.usage.time.wide.value:
				if hour > 11:  # All the PM times.
					hour -= 12
					pmadjust = 12
				if hour == 0:  # 12AM & 12PM map to 12.
					hour = 12
				if self.markedPos == 0 and digit >= 2:  # Only 0, 1 allowed (12 hour clock).
					return
				if self.markedPos == 1 and hour > 9 and digit >= 3:  # Only 10, 11, 12 allowed.
					return
				if self.markedPos == 1 and hour < 10 and digit == 0:  # Only 01, 02, ..., 09 allowed.
					return
			else:
				if self.markedPos == 0 and digit >= 3:  # Only 0, 1, 2 allowed (24 hour clock).
					return
				if self.markedPos == 1 and hour > 19 and digit >= 4:  # Only 20, 21, 22, 23 allowed.
					return
			if self.markedPos == 2 and digit >= 6:  # Only 0, 1, ..., 5 allowed (tens digit of minutes).
				return
			value = bytearray(b"%02d%02d" % (hour, self._value[1]))  # Must be ASCII!
			value[self.markedPos] = digit + ord(b"0")
			hour = int(value[:2])
			minute = int(value[2:])
			if config.usage.time.wide.value:
				if hour == 12:  # 12AM & 12PM map to back to 00.
					hour = 0
				elif hour > 12:
					hour = 10
				hour += pmadjust
			elif hour > 23:
				hour = 20
			self._value[0] = hour
			self._value[1] = minute
			self.markedPos += 1
			self.validate()
			self.changed()
		else:
			ConfigSequence.handleKey(self, key, callback)

	def increment(self):
		if self._value[1] == 59:  # Check if Minutes maxed out, increment Hour, reset Minutes.
			if self._value[0] < 23:
				self._value[0] += 1
			else:
				self._value[0] = 0
			self._value[1] = 0
		else:  # Increment Minutes.
			self._value[1] += 1
		self.changed()  # Trigger change.

	def decrement(self):
		if self._value[1] == 0:  # Check if Minutes is minimum, decrement Hour, set Minutes to 59.
			if self._value[0] > 0:
				self._value[0] -= 1
			else:
				self._value[0] = 23
			self._value[1] = 59
		else:  # Decrement Minutes.
			self._value[1] -= 1
		self.changed()  # Trigger change.

	def genText(self):
		mPos = self.markedPos
		if mPos >= 2:
			mPos += 1  # Skip over the separator.
		newtime = list(self.time)
		newtime[3] = self._value[0]
		newtime[4] = self._value[1]
		newtime = struct_time(newtime)
		value = strftime(config.usage.time.short.value.replace("%-I", "%_I").replace("%-H", "%_H"), newtime)
		return (value, mPos)


class ConfigDate(ConfigSequence):
	def __init__(self, default):
		date = localtime(default)
		ConfigSequence.__init__(self, seperator="/", limits=[(1, 31), (1, 12), (1970, 2050)], default=[date.tm_mday, date.tm_mon, date.tm_year])


class ConfigInteger(ConfigSequence):
	def __init__(self, default, limits=(0, 9999999999), censor=""):
		ConfigSequence.__init__(self, seperator=":", limits=[limits], default=default, censor=censor)
		self.length = len(str(limits[1]))  # DEBUG: Is this actually used?

	def fromString(self, value):
		return int(value)

	def toString(self, value):
		return str(value)

	def getValue(self):
		return self._value[0]

	def setValue(self, value):
		prev = self._value if hasattr(self, "_value") else None
		self._value = [value]
		if self._value != prev:
			self.changed()

	value = property(getValue, setValue)

	def getLimits(self):
		return self.limits


class ConfigPIN(ConfigInteger):
	def __init__(self, default, pinLength=4, censor=u"\u2022"):
		if not isinstance(default, int):
			raise TypeError("[Config] Error: 'ConfigPIN' default must be an integer!")
		if censor != "" and (isinstance(censor, str) and len(censor) != 1):  # and (isinstance(censor, unicode) and len(censor) != 1):
			raise ValueError("[Config] Error: Censor must be a single char (or \"\")!")
		ConfigInteger.__init__(self, default=default, limits=(0, (10 ** pinLength) - 1), censor=censor)
		self.pinLength = pinLength

	def getLength(self):
		return self.pinLength


class ConfigFloat(ConfigSequence):
	def __init__(self, default, limits):
		ConfigSequence.__init__(self, seperator=".", limits=limits, default=default)

	def getFloat(self):
		return float(self.value[1] / float(self.limits[1][1] + 1) + self.value[0])

	float = property(getFloat)

	def getFloatInt(self):
		return int(self.value[0] * float(self.limits[1][1] + 1) + self.value[1])

	def setFloatInt(self, val):
		self.value[0] = val / float(self.limits[1][1] + 1)
		self.value[1] = val % float(self.limits[1][1] + 1)

	floatint = property(getFloatInt, setFloatInt)

# an editable text...


class ConfigText(ConfigElement, NumericalTextInput):
	def __init__(self, default="", fixed_size=True, visible_width=False):
		ConfigElement.__init__(self)
		NumericalTextInput.__init__(self, nextFunc=self.nextFunc, handleTimeout=False)

		self.markedPos = 0
		self.allmarked = (default != "")
		self.fixed_size = fixed_size
		self.visible_width = visible_width
		self.offset = 0
		self.overwrite = fixed_size
		self.help_window = None
		self.value = self.lastValue = self.prev_value = self.default = default

	def validateMarker(self):
		textlen = len(self.text)
		if self.fixed_size:
			if self.markedPos > textlen - 1:
				self.markedPos = textlen - 1
		else:
			if self.markedPos > textlen:
				self.markedPos = textlen
		if self.markedPos < 0:
			self.markedPos = 0
		if self.visible_width:
			if self.markedPos < self.offset:
				self.offset = self.markedPos
			if self.markedPos >= self.offset + self.visible_width:
				if self.markedPos == textlen:
					self.offset = self.markedPos - self.visible_width
				else:
					self.offset = self.markedPos - self.visible_width + 1
			if self.offset > 0 and self.offset + self.visible_width > textlen:
				self.offset = max(0, len - self.visible_width)

	def insertChar(self, ch, pos, owr):
		if owr or self.overwrite:
			self.text = self.text[0:pos] + ch + self.text[pos + 1:]
		elif self.fixed_size:
			self.text = self.text[0:pos] + ch + self.text[pos:-1]
		else:
			self.text = self.text[0:pos] + ch + self.text[pos:]

	def deleteChar(self, pos):
		if not self.fixed_size:
			self.text = self.text[0:pos] + self.text[pos + 1:]
		elif self.overwrite:
			self.text = self.text[0:pos] + " " + self.text[pos + 1:]
		else:
			self.text = self.text[0:pos] + self.text[pos + 1:] + " "

	def deleteAllChars(self):
		if self.fixed_size:
			self.text = " " * len(self.text)
		else:
			self.text = ""
		self.markedPos = 0

	def handleKey(self, key):  # This will not change anything on the value itself so we can handle it here in GUI element.
		if key == ACTIONKEY_FIRST:
			self.timeout()
			self.allmarked = False
			self.markedPos = 0
		elif key == ACTIONKEY_LEFT:
			self.timeout()
			if self.allmarked:
				self.markedPos = len(self.text)
				self.allmarked = False
			else:
				self.markedPos -= 1
		elif key == ACTIONKEY_RIGHT:
			self.timeout()
			if self.allmarked:
				self.markedPos = 0
				self.allmarked = False
			else:
				self.markedPos += 1
		elif key == ACTIONKEY_LAST:
			self.timeout()
			self.allmarked = False
			self.markedPos = len(self.text)
		elif key == ACTIONKEY_BACKSPACE:
			self.timeout()
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			elif self.markedPos > 0:
				self.deleteChar(self.markedPos - 1)
				if not self.fixed_size and self.offset > 0:
					self.offset -= 1
				self.markedPos -= 1
		elif key == ACTIONKEY_DELETE:
			self.timeout()
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			else:
				self.deleteChar(self.markedPos)
				if self.fixed_size and self.overwrite:
					self.markedPos += 1
		elif key == ACTIONKEY_ERASE:
			self.timeout()
			self.deleteAllChars()
		elif key == ACTIONKEY_TOGGLE:
			self.timeout()
			self.overwrite = not self.overwrite
		elif key == ACTIONKEY_ASCII:
			self.timeout()
			newChar = chr(getPrevAsciiCode())
			if not self.useableChars or newChar in self.useableChars:
				if self.allmarked:
					self.deleteAllChars()
					self.allmarked = False
				self.insertChar(newChar, self.markedPos, False)
				self.markedPos += 1
		elif key in ACTIONKEY_NUMBERS:
			owr = self.lastKey == getKeyNumber(key)
			newChar = self.getKey(getKeyNumber(key))
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			self.insertChar(newChar, self.markedPos, owr)
			if self.help_window:
				self.help_window.update(self)
			return
		elif key == ACTIONKEY_TIMEOUT:
			self.timeout()
			if self.help_window:
				self.help_window.update(self)
			return

		if self.help_window:
			self.help_window.update(self)
		self.validateMarker()
		self.changed()

	def nextFunc(self):
		self.markedPos += 1
		self.validateMarker()
		self.changed()

	def getValue(self):
		return self.text

	def setValue(self, val):
		self.text = val

	value = property(getValue, setValue)
	_value = property(getValue, setValue)

	def getText(self):
		return self.text

	def getMulti(self, selected):
		if self.visible_width:
			if self.allmarked:
				mark = list(range(0, min(self.visible_width, len(self.text))))
			else:
				mark = [self.markedPos - self.offset]
			return ("mtext"[1 - selected:], self.text[self.offset:self.offset + self.visible_width] + " ", mark)
		else:
			if self.allmarked:
				mark = list(range(0, len(self.text)))
			else:
				mark = [self.markedPos]
			return ("mtext"[1 - selected:], self.text + " ", mark)

	def onSelect(self, session):
		self.allmarked = (self.value != "")
		if session is not None:
			from Screens.NumericalTextInputHelpDialog import NumericalTextInputHelpDialog
			self.help_window = session.instantiateDialog(NumericalTextInputHelpDialog, self)
			self.help_window.show()

	def onDeselect(self, session):
		self.markedPos = 0
		self.offset = 0
		if self.help_window:
			session.deleteDialog(self.help_window)
			self.help_window = None
		if not self.lastValue == self.value:
			self.changedFinal()
			self.lastValue = self.value

	def hideHelp(self, session):
		if session is not None and self.help_window is not None:
			self.help_window.hide()

	def showHelp(self, session):
		if session is not None and self.help_window is not None:
			self.help_window.show()

	def getHTML(self, id):
		return '<input type="text" name="' + id + '" value="' + self.value + '" /><br>\n'

	def unsafeAssign(self, value):
		self.value = str(value)


class ConfigPassword(ConfigText):
	def __init__(self, default="", fixed_size=False, visible_width=False, censor=u"\u2022"):
		ConfigText.__init__(self, default=default, fixed_size=fixed_size, visible_width=visible_width)
		if censor != "" and (isinstance(censor, str) and len(censor) != 1) and (isinstance(censor, unicode) and len(censor) != 1):
			raise ValueError("[Config] Error: Censor must be a single char (or \"\")!")
		self.censor = censor
		self.hidden = True

	def getMulti(self, selected):
		mtext, text, mark = ConfigText.getMulti(self, selected)
		if self.hidden:
			text = self.censor * len(text)  # For more security a fixed length string can be used!
		return (mtext, text, mark)

	def onSelect(self, session):
		ConfigText.onSelect(self, session)
		self.hidden = False

	def onDeselect(self, session):
		self.hidden = True
		ConfigText.onDeselect(self, session)

# Let the user select from [first, first + step, first + (step * 2), ..., maxVal]
# with maxVal <= last depending on the step. The default, first, last and step
# are integer values.
#
# wrap: If set to True, pressing RIGHT key at last value brings you to first
# value and vice versa.
#
# units: This is a list or tuple with two strings that contain a "%d" formatting
# element that will be used, via ngettext(), to display the numbers in a more
# meaningful way.  The first string in the list/tuple is the singular string and
# the second is the one for other numbers.
#
# NOTE: If the units argument is used please ensure that the text to be used is
# 	already defined and translated elsewhere so that unit strings are properly
# 	available for translation. If the strings are not used elsewhere in the
# 	code then the translations can be added to the TranslationHelper.py file.
#
class ConfigSelectionInteger(ConfigSelection):
	def __init__(self, default=None, first=0, last=100, step=1, wrap=False, units=None):
		if default is None:
			default = first
		self.first = first
		self.last = last
		self.step = step
		self.wrap = wrap
		self.units = units
		ConfigSelection.__init__(self, choices=[(x, (ngettext(units[0], units[1], x) % x if units and isinstance(units, (list, tuple)) else str(x))) for x in range(first, last + 1, step)], default=default)

	def handleKey(self, key):
		if not self.wrap:
			if key == ACTIONKEY_RIGHT and self.choices.index(self.value) == len(self.choices) - 1:
				return
			if key == ACTIONKEY_LEFT and self.choices.index(self.value) == 0:
				return
		ConfigSelection.handleKey(self, key)

	def setChoices(self, default=None, first=None, last=None, step=None, wrap=None, units=None):
		self.first = self.first if first is None else first
		self.last = self.last if last is None else last
		self.step = self.step if step is None else step
		self.wrap = self.wrap if wrap is None else wrap
		self.units = self.units if units is None else units
		if default is None:
			default = self.default if first < self.default <= last else first
		if self.value < self.first or self.value > self.last:
			self.value = default
		return self.setSelectionList([(x, (ngettext(self.units[0], self.units[1], x) % x if self.units and isinstance(self.units, (list, tuple)) else str(x))) for x in range(self.first, self.last + 1, self.step)], default=default)


class ConfigSelectionNumber(ConfigSelectionInteger):
	def __init__(self, min, max, stepwidth, default=None, wraparound=False, units=None):
		ConfigSelectionInteger.__init__(self, default, min, max, stepwidth, wraparound, units)


class ConfigMACText(ConfigText):
	def __init__(self, default="", visible_width=17):
		ConfigText.__init__(self, default, fixed_size=True, visible_width=visible_width)
		NumericalTextInput.setMode(self, "HexFastLogicalUpper")  # HexFastUpper
		self.allmarked = False

	def handleKey(self, key, callback=None):
		if callable(callback):
			self.callback = callback
		prev = self.value
		if key == ACTIONKEY_FIRST:
			self.timeout()
			self.markedPos = 0
		elif key == ACTIONKEY_LEFT:
			self.timeout()
			self.markedPos -= 2 if self.text[self.markedPos - 1] == ":" else 1
		elif key == ACTIONKEY_RIGHT:
			self.timeout()
			self.markedPos += 2 if self.markedPos < self.visible_width - 1 and self.text[self.markedPos + 1] == ":" else 1
		elif key == ACTIONKEY_LAST:
			self.timeout()
			self.markedPos = len(self.text)
		elif key == ACTIONKEY_ERASE:
			self.timeout()
			self.text = self.text[2].join(["00"] * 6)
			self.markedPos = 0
		elif key in ACTIONKEY_NUMBERS:
			owr = self.lastKey == getKeyNumber(key)
			newChar = self.getKey(getKeyNumber(key))
			self.insertChar(newChar, self.markedPos, owr)
		elif key == ACTIONKEY_TIMEOUT:
			self.timeout()
			if self.help_window:
				self.help_window.update(self)
			if self.text[self.markedPos] == ":":
				self.markedPos += 1
			return
		if self.help_window:
			self.help_window.update(self)
		self.validateMarker()
		if self.value != prev:
			self.changed()
			if self.callback:
				self.callback()

	def validateMarker(self):
		textlen = len(self.text)
		if self.markedPos > textlen - 1:
			self.markedPos = textlen - 1
		elif self.markedPos < 0:
			self.markedPos = 0

	def insertChar(self, ch, pos, owr):
		if self.text[pos] == ":":
			pos += 1
		ConfigText.insertChar(self, ch, pos, owr)

	def onSelect(self, session):
		ConfigText.onSelect(self, session)
		self.allmarked = False


class ConfigMacText(ConfigMACText):  # Deprecated class name.
	def __init__(self, default="", visible_width=17):
		ConfigMACText.__init__(self, default=default, visible_width=visible_width)


class ConfigNumber(ConfigText):
	def __init__(self, default=0):
		if not isinstance(default, int):
			raise TypeError("[Config] Error: 'ConfigNumber' requires a default of type integer!")
		ConfigText.__init__(self, str(default), fixed_size=False)
		self.value = self.lastValue = self.default = default

	def handleKey(self, key, callback=None):
		if key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			prev = int(self.text)
			if key == ACTIONKEY_ASCII:
				ascii = getPrevAsciiCode()
				if not (48 <= ascii <= 57):
					return
			else:
				ascii = getKeyNumber(key) + 48
			newChar = chr(ascii)
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			self.insertChar(newChar, self.markedPos, False)
			self.markedPos += 1
			self.validateMarker()
			if int(self.text) != prev:
				self.changed()
				if callable(callback):
					callback()
		else:
			ConfigText.handleKey(self, key)

	def validateMarker(self):
		pos = len(self.text) - self.markedPos
		self.text = self.text.lstrip("0")
		if self.text == "":
			self.text = "0"
		if pos > len(self.text):
			self.markedPos = 0
		else:
			self.markedPos = len(self.text) - pos

	def getValue(self):
		try:
			return int(self.text)
		except ValueError:
			self.text = "1" if self.text.lower() == "true" else self.default
			return int(self.text)

	def setValue(self, value):
		prev = self.text if hasattr(self, "text") else None
		self.text = str(value)
		if self.text != prev:
			self.changed()

	value = property(getValue, setValue)
	_value = property(getValue, setValue)


class ConfigSearchText(ConfigText):
	def __init__(self, default="", fixed_size=False, visible_width=False):
		ConfigText.__init__(self, default=default, fixed_size=fixed_size, visible_width=visible_width)
		NumericalTextInput.__init__(self, nextFunc=self.nextFunc, handleTimeout=False, search=True)


class ConfigDirectory(ConfigText):
	def __init__(self, default="", visible_width=60):
		ConfigText.__init__(self, default, fixed_size=True, visible_width=visible_width)

	def handleKey(self, key):
		pass

	def getValue(self):
		if self.text == "":
			return None
		else:
			return ConfigText.getValue(self)

	def setValue(self, val):
		if val is None:
			val = ""
		ConfigText.setValue(self, val)

	def getMulti(self, selected):
		if self.text == "":
			return ("mtext"[1 - selected:], _("List of storage devices"), list(range(0)))
		else:
			return ConfigText.getMulti(self, selected)

	def onSelect(self, session):
		self.allmarked = (self.value != "")


# This is the control, and base class, for slider settings.
#
class ConfigSlider(ConfigElement):
	def __init__(self, default=0, increment=1, limits=(0, 100)):
		ConfigElement.__init__(self)
		if not isinstance(default, int):
			raise TypeError("[Config] Error: 'ConfigSlider' default must be an integer!")
		if not isinstance(increment, int):
			raise TypeError("[Config] Error: 'ConfigSlider' increment must be an integer!")
		if not isinstance(limits[0], int):
			raise TypeError("[Config] Error: 'ConfigSlider' minimum value must be an integer!")
		if not isinstance(limits[1], int):
			raise TypeError("[Config] Error: 'ConfigSlider' maximum value must be an integer!")
		if limits[0] >= limits[1]:
			raise ValueError("[Config] Error: 'ConfigSlider' minimum value must be less than maximum value!")
		self.default = default
		self.lastValue = default
		self.value = default
		self.increment = increment
		self.min = limits[0]
		self.max = limits[1]

	def handleKey(self, key, callback=None):
		value = self.value
		if key == ACTIONKEY_FIRST:
			value = self.min
		elif key == ACTIONKEY_LEFT:
			value -= self.increment
		elif key == ACTIONKEY_RIGHT:
			value += self.increment
		elif key == ACTIONKEY_LAST:
			value = self.max
		else:
			return
		if value < self.min:
			value = self.min
		elif value > self.max:
			value = self.max
		if value != self.value:
			self.value = value
			self.changed()
			if callable(callback):
				callback()

	def getText(self):
		return "%d / %d / %d" % (self.min, self.value, self.max)

	def getMulti(self, selected):
		return ("slider", self.value, self.min, self.max)

	def fromString(self, value):
		return int(value)


class ConfigSatlist(ConfigSelection):
	def __init__(self, list, default=None):
		if default is not None:
			default = str(default)
		ConfigSelection.__init__(self, choices=[(str(orbpos), desc) for (orbpos, desc, flags) in list], default=default)

	def getOrbitalPosition(self):
		if self.value == "":
			return None
		return int(self.value)

	orbital_position = property(getOrbitalPosition)


class ConfigSet(ConfigElement):
	def __init__(self, choices, default=[]):
		ConfigElement.__init__(self)
		if isinstance(choices, list):
			choices.sort()
			self.choices = choicesList(choices, choicesList.LIST_TYPE_LIST)
		else:
			assert False, "ConfigSet choices must be a list!"
		if default is None:
			default = []
		self.pos = -1
		default.sort()
		self.lastValue = self.default = self.prev_value = default
		self.value = default[:]

	def toggleChoice(self, choice):
		value = self.value
		if choice in value:
			value.remove(choice)
		else:
			value.append(choice)
			value.sort()
		self.changed()

	def handleKey(self, key):
		if key == ACTIONKEY_FIRST:
			self.pos = 0
		elif key == ACTIONKEY_LEFT:
			self.pos = self.pos - 1 if self.pos > 0 else len(self.choices) - 1
		elif key == ACTIONKEY_RIGHT:
			self.pos = self.pos + 1 if self.pos < len(self.choices) - 1 else 0
		elif key == ACTIONKEY_LAST:
			self.pos = len(self.choices) - 1
		elif key in [ACTIONKEY_TOGGLE, ACTIONKEY_SELECT, ACTIONKEY_DELETE, ACTIONKEY_BACKSPACE] + ACTIONKEY_NUMBERS:
			value = self.value
			choice = self.choices[self.pos]
			if choice in value:
				value.remove(choice)
			else:
				value.append(choice)
				value.sort()
			self.value = value
			self.changed()

	def genString(self, lst):
		res = ""
		for x in lst:
			res += self.description[x] + " "
		return res

	def getText(self):
		return self.genString(self.value)

	def getMulti(self, selected):
		if not selected or self.pos == -1:
			return ("text", self.genString(self.value))
		else:
			tmp = self.value[:]
			ch = self.choices[self.pos]
			mem = ch in self.value
			if not mem:
				tmp.append(ch)
				tmp.sort()
			ind = tmp.index(ch)
			val1 = self.genString(tmp[:ind])
			val2 = " " + self.genString(tmp[ind + 1:])
			if mem:
				chstr = " " + self.description[ch] + " "
			else:
				chstr = "(" + self.description[ch] + ")"
			len_val1 = len(val1)
			return ("mtext", val1 + chstr + val2, list(range(len_val1, len_val1 + len(chstr))))

	def onDeselect(self, session):
		self.pos = -1
		if not self.lastValue == self.value:
			self.changedFinal()
			self.lastValue = self.value[:]

	def toString(self, value):
		return str(value)

	def toDisplayString(self, value):
		return ", ".join([self.description[x] for x in value])

	def fromString(self, val):
		return eval(val)

	description = property(lambda self: descriptionList(self.choices.choices, choicesList.LIST_TYPE_LIST))


class ConfigDictionarySet(ConfigElement):
	def __init__(self, default={}):
		ConfigElement.__init__(self)
		self.default = default
		self.dirs = {}
		self.value = self.default

	def setValue(self, value):
		if isinstance(value, dict):
			self.dirs = value
			self.changed()

	def getValue(self):
		return self.dirs

	value = property(getValue, setValue)

	def toString(self, value):
		return str(value)

	def fromString(self, val):
		return eval(val)

	def load(self):
		sv = self.saved_value
		if sv is None:
			tmp = self.default
		else:
			tmp = self.fromString(sv)
		self.dirs = tmp

	def changeConfigValue(self, value, config_key, config_value):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs:
				self.dirs[value][config_key] = config_value
			else:
				self.dirs[value] = {config_key: config_value}
			self.changed()

	def getConfigValue(self, value, config_key):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs and config_key in self.dirs[value]:
				return self.dirs[value][config_key]
		return None

	def removeConfigValue(self, value, config_key):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs and config_key in self.dirs[value]:
				try:
					del self.dirs[value][config_key]
				except KeyError:
					pass
				self.changed()

	def save(self):
		del_keys = []
		for key in self.dirs:
			if not len(self.dirs[key]):
				del_keys.append(key)
		for del_key in del_keys:
			try:
				del self.dirs[del_key]
			except KeyError:
				pass
			self.changed()
		self.saved_value = self.toString(self.dirs)


class ConfigLocations(ConfigElement):
	def __init__(self, default=[], visible_width=False):
		ConfigElement.__init__(self)
		self.visible_width = visible_width
		self.pos = -1
		self.default = default
		self.locations = []
		self.mountpoints = []
		self.value = default[:]

	def setValue(self, value):
		locations = self.locations
		loc = [x[0] for x in locations if x[3]]
		add = [x for x in value if x not in loc]
		diff = add + [x for x in loc if x not in value]
		locations = [x for x in locations if x[0] not in diff] + [[x, self.getMountpoint(x), True, True] for x in add]
		locations.sort(key=lambda x: x[0])
		self.locations = locations
		self.changed()

	def getValue(self):
		self.checkChangedMountpoints()
		locations = self.locations
		for x in locations:
			x[3] = x[2]
		return [x[0] for x in locations if x[3]]

	value = property(getValue, setValue)

	def toString(self, value):
		return str(value)

	def fromString(self, val):
		return eval(val)

	def load(self):
		sv = self.saved_value
		if sv is None:
			tmp = self.default
		else:
			tmp = self.fromString(sv)
		locations = [[x, None, False, False] for x in tmp]
		self.refreshMountpoints()
		for x in locations:
			if fileExists(x[0]):
				x[1] = self.getMountpoint(x[0])
				x[2] = True
		self.locations = locations

	def save(self):
		locations = self.locations
		if self.save_disabled or not locations:
			self.saved_value = None
		else:
			self.saved_value = self.toString([x[0] for x in locations])

	def isChanged(self):
		sv = self.saved_value
		locations = self.locations
		if sv is None and not locations:
			return False
		return self.toString([x[0] for x in locations]) != sv

	def addedMount(self, mp):
		for x in self.locations:
			if x[1] == mp:
				x[2] = True
			elif x[1] is None and fileExists(x[0]):
				x[1] = self.getMountpoint(x[0])
				x[2] = True

	def removedMount(self, mp):
		for x in self.locations:
			if x[1] == mp:
				x[2] = False

	def refreshMountpoints(self):
		self.mountpoints = [p.mountpoint for p in harddiskmanager.getMountedPartitions() if p.mountpoint != "/"]
		self.mountpoints.sort(key=lambda x: -len(x))

	def checkChangedMountpoints(self):
		oldmounts = self.mountpoints
		self.refreshMountpoints()
		newmounts = self.mountpoints
		if oldmounts == newmounts:
			return
		for x in oldmounts:
			if x not in newmounts:
				self.removedMount(x)
		for x in newmounts:
			if x not in oldmounts:
				self.addedMount(x)

	def getMountpoint(self, file):
		file = os.path.realpath(file) + "/"
		for m in self.mountpoints:
			if file.startswith(m):
				return m
		return None

	def handleKey(self, key):
		count = len(self.value) - 1
		if key == ACTIONKEY_FIRST:
			self.item = 0
		elif key == ACTIONKEY_LEFT:
			self.item = self.item - 1 if self.item > 0 else count
		elif key == ACTIONKEY_RIGHT:
			self.item = self.item + 1 if self.item < count else 0
		elif key == ACTIONKEY_LAST:
			self.item = count

	def getText(self):
		return " ".join(self.value)

	def getMulti(self, selected):
		if not selected:
			valstr = " ".join(self.value)
			if self.visible_width and len(valstr) > self.visible_width:
				return ("text", valstr[0:self.visible_width])
			else:
				return ("text", valstr)
		else:
			i = 0
			valstr = ""
			ind1 = 0
			ind2 = 0
			for val in self.value:
				if i == self.pos:
					ind1 = len(valstr)
				valstr += str(val) + " "
				if i == self.pos:
					ind2 = len(valstr)
				i += 1
			if self.visible_width and len(valstr) > self.visible_width:
				if ind1 + 1 < self.visible_width / 2:
					off = 0
				else:
					off = min(ind1 + 1 - self.visible_width / 2, len(valstr) - self.visible_width)
				return ("mtext", valstr[off:off + self.visible_width], list(range(ind1 - off, ind2 - off)))
			else:
				return ("mtext", valstr, list(range(ind1, ind2)))

	def onDeselect(self, session):
		self.pos = -1

# nothing.


class ConfigNothing(ConfigSelection):
	def __init__(self):
		ConfigSelection.__init__(self, choices=[("", "")])

# until here, 'saved_value' always had to be a *string*.
# now, in ConfigSubsection, and only there, saved_value
# is a dict, essentially forming a tree.
#
# config.foo.bar=True
# config.foobar=False
#
# turns into:
# config.saved_value == {"foo": {"bar": "True"}, "foobar": "False"}
#


class ConfigSubsectionContent:
	pass

# we store a backup of the loaded configuration
# data in self.stored_values, to be able to deploy
# them when a new config element will be added,
# so non-default values are instantly available

# A list, for example:
# config.dipswitches = ConfigSubList()
# config.dipswitches.append(ConfigYesNo())
# config.dipswitches.append(ConfigYesNo())
# config.dipswitches.append(ConfigYesNo())


class ConfigSubList(list):
	def __init__(self):
		list.__init__(self)
		self.stored_values = {}

	def save(self):
		for x in self:
			x.save()

	def load(self):
		for x in self:
			x.load()

	def getSavedValue(self):
		res = {}
		for i, val in enumerate(self):
			sv = val.saved_value
			if sv is not None:
				res[str(i)] = sv
		return res

	def setSavedValue(self, values):
		self.stored_values = dict(values)
		for (key, val) in self.stored_values.items():
			if int(key) < len(self):
				self[int(key)].saved_value = val

	saved_value = property(getSavedValue, setSavedValue)

	def append(self, item):
		i = str(len(self))
		list.append(self, item)
		if i in self.stored_values:
			item.saved_value = self.stored_values[i]
			item.load()

	def dict(self):
		return dict([(str(index), value) for index, value in enumerate(self)])

# same as ConfigSubList, just as a dictionary.
# care must be taken that the 'key' has a proper
# str() method, because it will be used in the config
# file.


class ConfigSubDict(dict):
	def __init__(self):
		dict.__init__(self)
		self.stored_values = {}

	def save(self):
		for x in self.values():
			x.save()

	def load(self):
		for x in self.values():
			x.load()

	def getSavedValue(self):
		res = {}
		for (key, val) in self.items():
			sv = val.saved_value
			if sv is not None:
				res[str(key)] = sv
		return res

	def setSavedValue(self, values):
		self.stored_values = dict(values)
		for (key, val) in self.items():
			if str(key) in self.stored_values:
				val.saved_value = self.stored_values[str(key)]

	saved_value = property(getSavedValue, setSavedValue)

	def __setitem__(self, key, item):
		dict.__setitem__(self, key, item)
		if str(key) in self.stored_values:
			item.saved_value = self.stored_values[str(key)]
			item.load()

	def dict(self):
		return self

# Like the classes above, just with a more "native"
# syntax.
#
# some evil stuff must be done to allow instant
# loading of added elements. this is why this class
# is so complex.
#
# we need the 'content' because we overwrite
# __setattr__.
# If you don't understand this, try adding
# __setattr__ to a usual exisiting class and you will.


class ConfigSubsection:
	def __init__(self):
		self.__dict__["content"] = ConfigSubsectionContent()
		self.content.items = {}
		self.content.stored_values = {}

	def __setattr__(self, name, value):
		if name == "saved_value":
			return self.setSavedValue(value)
		assert isinstance(value, (ConfigSubsection, ConfigElement, ConfigSubList, ConfigSubDict)), "ConfigSubsections can only store ConfigSubsections, ConfigSubLists, ConfigSubDicts or ConfigElements"
		content = self.content
		content.items[name] = value
		x = content.stored_values.get(name, None)
		if x is not None:
			# print "ok, now we have a new item,", name, "and have the following value for it:", x
			value.saved_value = x
			value.load()

	def __getattr__(self, name):
		if name in self.content.items:
			return self.content.items[name]
		raise AttributeError(name)

	def getSavedValue(self):
		res = self.content.stored_values
		for (key, val) in self.content.items.items():
			sv = val.saved_value
			if sv is not None:
				res[key] = sv
			elif key in res:
				del res[key]
		return res

	def setSavedValue(self, values):
		values = dict(values)
		self.content.stored_values = values
		for (key, val) in self.content.items.items():
			value = values.get(key, None)
			if value is not None:
				val.saved_value = value

	saved_value = property(getSavedValue, setSavedValue)

	def save(self):
		for x in self.content.items.values():
			x.save()

	def load(self):
		for x in self.content.items.values():
			x.load()

	def dict(self):
		return self.content.items

# the root config object, which also can "pickle" (=serialize)
# down the whole config tree.
#
# we try to keep non-existing config entries, to apply them whenever
# a new config entry is added to a subsection
# also, non-existing config entries will be saved, so they won't be
# lost when a config entry disappears.


class Config(ConfigSubsection):
	def __init__(self):
		ConfigSubsection.__init__(self)

	def pickle_this(self, prefix, topickle, result):
		for (key, val) in sorted(topickle.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0].lower()):
			name = '.'.join((prefix, key))
			if isinstance(val, dict):
				self.pickle_this(name, val, result)
			elif isinstance(val, tuple):
				result += [name, '=', val[0], '\n']
			else:
				result += [name, '=', val, '\n']

	def pickle(self):
		result = []
		self.pickle_this("config", self.saved_value, result)
		return ''.join(result)

	def unpickle(self, lines, base_file=True):
		tree = {}
		configbase = tree.setdefault("config", {})
		for l in lines:
			if not l or l[0] == '#':
				continue

			result = l.split('=', 1)
			if len(result) != 2:
				continue
			(name, val) = result
			val = val.strip()

			names = name.split('.')
			base = configbase

			for n in names[1:-1]:
				base = base.setdefault(n, {})

			base[names[-1]] = val

			if not base_file:  # not the initial config file..
				# update config.x.y.value when exist
				try:
					configEntry = eval(name)
					if configEntry is not None:
						configEntry.value = val
				except (SyntaxError, KeyError):
					pass

		# we inherit from ConfigSubsection, so ...
		# object.__setattr__(self, "saved_value", tree["config"])
		if "config" in tree:
			self.setSavedValue(tree["config"])

	def saveToFile(self, filename):
		text = self.pickle()
		try:
			import os
			f = open(filename + ".writing", "w", encoding="UTF-8")
			f.write(text)
			f.flush()
			os.fsync(f.fileno())
			f.close()
			os.rename(filename + ".writing", filename)
		except IOError:
			print("Config: Couldn't write %s" % filename)

	def loadFromFile(self, filename, base_file=True):
		self.unpickle(open(filename, "r", encoding="UTF-8"), base_file)


class ConfigFile:
	CONFIG_FILE = resolveFilename(SCOPE_CONFIG, "settings")

	def load(self):
		try:
			config.loadFromFile(self.CONFIG_FILE, True)
		except IOError as e:
			print("unable to load config (%s), assuming defaults..." % str(e))

	def save(self):
		# config.save()
		config.saveToFile(self.CONFIG_FILE)

	def __resolveValue(self, pickles, cmap):
		key = pickles[0]
		if key in cmap:
			if len(pickles) > 1:
				return self.__resolveValue(pickles[1:], cmap[key].dict())
			else:
				return str(cmap[key].value)
		return None

	def getResolvedKey(self, key):
		names = key.split('.')
		if len(names) > 1:
			if names[0] == "config":
				ret = self.__resolveValue(names[1:], config.content.items)
				if ret and len(ret) or ret == "":
					return ret
		print("getResolvedKey", key, "failed !! (Typo??)")
		return ""


config = Config()
config.misc = ConfigSubsection()
configfile = ConfigFile()
configfile.load()

# def _(x):
# 	return x
#
# config.bla = ConfigSubsection()
# config.bla.test = ConfigYesNo()
# config.nim = ConfigSubList()
# config.nim.append(ConfigSubsection())
# config.nim[0].bla = ConfigYesNo()
# config.nim.append(ConfigSubsection())
# config.nim[1].bla = ConfigYesNo()
# config.nim[1].blub = ConfigYesNo()
# config.arg = ConfigSubDict()
# config.arg["Hello"] = ConfigYesNo()
#
# config.arg["Hello"].handleKey(KEY_RIGHT)
# config.arg["Hello"].handleKey(KEY_RIGHT)
#
# #config.saved_value
#
# #configfile.save()
# config.save()
# print config.pickle()


cec_limits = [(0, 15), (0, 15), (0, 15), (0, 15)]


class ConfigCECAddress(ConfigSequence):
	def __init__(self, default, auto_jump=False):
		ConfigSequence.__init__(self, seperator=".", limits=cec_limits, default=default)
		self.marked_block = 0
		self.overwrite = True
		self.auto_jump = auto_jump

	def handleKey(self, key):
		if key == ACTIONKEY_LEFT:
			if self.marked_block > 0:
				self.marked_block -= 1
			self.overwrite = True
		elif key == ACTIONKEY_RIGHT:
			if self.marked_block < len(self.limits) - 1:
				self.marked_block += 1
			self.overwrite = True
		elif key == ACTIONKEY_FIRST:
			self.marked_block = 0
			self.overwrite = True
		elif key == ACTIONKEY_LAST:
			self.marked_block = len(self.limits) - 1
			self.overwrite = True
		elif key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			if key == ACTIONKEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)
			oldvalue = self._value[self.marked_block]
			if self.overwrite:
				self._value[self.marked_block] = number
				self.overwrite = False
			else:
				oldvalue *= 10
				newvalue = oldvalue + number
				if self.auto_jump and newvalue > self.limits[self.marked_block][1] and self.marked_block < len(self.limits) - 1:
					self.handleKey(ACTIONKEY_RIGHT)
					self.handleKey(key)
					return
				else:
					self._value[self.marked_block] = newvalue
			if len(str(self._value[self.marked_block])) >= self.blockLen[self.marked_block]:
				self.handleKey(ACTIONKEY_RIGHT)
			self.validate()
			self.changed()

	def genText(self):
		value = ""
		block_strlen = []
		for i in self._value:
			block_strlen.append(len(str(i)))
			if value:
				value += self.seperator
			value += str(i)
		leftPos = sum(block_strlen[:(self.marked_block)]) + self.marked_block
		rightPos = sum(block_strlen[:(self.marked_block + 1)]) + self.marked_block
		mBlock = list(range(leftPos, rightPos))
		return (value, mBlock)

	def getMulti(self, selected):
		(value, mBlock) = self.genText()
		if self.enabled:
			return ("mtext"[1 - selected:], value, mBlock)
		else:
			return ("text", value)

	def getHTML(self, id=0):
		# I do not know why id is here but it is used in the sources renderer and I'm afraid we should keep it for compatibily. It is not used here but I give at a default value
		# we definitely don't want leading zeros
		return '.'.join(["%d" % d for d in self.value])


class ConfigAction(ConfigElement):
	def __init__(self, action, *args):
		ConfigElement.__init__(self)
		self.value = "(OK)"
		self.action = action
		self.actionargs = args

	def handleKey(self, key):
		if (key == ACTIONKEY_SELECT):
			self.action(*self.actionargs)

	def getMulti(self, dummy):
		pass
