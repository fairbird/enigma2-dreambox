# -*- coding: utf-8 -*-
from xml.etree.ElementTree import parse

from skin import findSkinScreen, menus, parameters, menus, menuicons
from Components.config import ConfigDictionarySet, NoSave, config, configfile
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.SystemInfo import SystemInfo
from Components.Button import Button
from Plugins.Plugin import PluginDescriptor
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_GUISKIN, SCOPE_SKINS
from Tools.LoadPixmap import LoadPixmap

from enigma import eTimer
from os.path import exists

from Components.NimManager import nimmanager  # nimmanager is used in eval(conditional), do not remove this import


# read the menu
file = open(resolveFilename(SCOPE_SKINS, "menu.xml"))
mdom = parse(file)
file.close()


def MenuEntryPixmap(key, png_cache):
	if not menuicons:
		return None
	w, h = parameters.get("MenuIconSize", (50, 50))
	png = png_cache.get(key)
	if png is None:  # no cached entry
		pngPath = menuicons.get(key, menuicons.get("default", ""))
		if pngPath:
			png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, pngPath), cached=True, width=w, height=0 if pngPath.endswith(".svg") else h)
	return png


def default_skin():
	for line in open("/etc/enigma2/settings"):
		if not "config.skin.primary_skin" in line:
			return default_skin

def MenuEntryName(name):
	def splitUpperCase(name, maxlen):
		for c in range(len(name), 0, -1):
			if name[c - 1].isupper() and c - 1 and c - 1 <= maxlen:
				return name[:c - 1] + "-:-" + name[c - 1:]
		return name

	def splitLowerCase(name, maxlen):
		for c in range(len(name), 0, -1):
			if name[c - 1].islower() and c - 1 and c - 1 <= maxlen:
				return name[:c - 1] + "-:-" + name[c - 1:]
		return name

	def splitName(name, maxlen):
		for s in (" ", "-", "/"):
			pos = name.rfind(s, 0, maxlen + 1)
			if pos > 1:
				return [name[:pos + 1] if pos + 1 <= maxlen and s != " " else name[:pos], name[pos + 1:]]
		return splitUpperCase(name, maxlen).split("-:-", 1)

	maxrow = 3
	maxlen = 18
	namesplit = []
	if len(name) > maxlen and maxrow > 1:
		namesplit = splitName(name, maxlen)
		if len(namesplit) == 1 or (len(namesplit) == 2 and len(namesplit[1]) > maxlen * (maxrow - 1)):
			tmp = splitLowerCase(name, maxlen).split("-:-", 1)
			if len(tmp[0]) > len(namesplit[0]) or len(namesplit) < 2:
				namesplit = tmp
		for x in range(1, maxrow):
			if len(namesplit) > x and len(namesplit) < maxrow and len(namesplit[x]) > maxlen:
				tmp = splitName(namesplit[x], maxlen)
				if len(tmp) == 1 or (len(tmp) == 2 and len(tmp[1]) > maxlen * (maxrow - x)):
					tmp = splitLowerCase(namesplit[x], maxlen).split("-:-", 1)
				if len(tmp) == 2:
					namesplit.pop(x)
					namesplit.extend(tmp)
			else:
				break
	return name if len(namesplit) < 2 else "\n".join(namesplit)


class title_History():
	def __init__(self):
		self.thistory = ""

	def reset(self):
		self.thistory = ""
 
	def reducehistory(self):
		history_len = len(self.thistory.split(">"))
		if history_len < 3:
			self.reset()
			return
		if self.thistory == "":
			return
		result = self.thistory.rsplit(">", 2)
		if result[0] == "":
			self.reset()
			return
		self.thistory = result[0] + "> "


t_history = title_History()


class MenuSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["Title"] = StaticText(parent.getTitle())


class Menu(Screen, ProtectedScreen):
	png_cache = {}

	def okbuttonClick(self):
		if self.number:
			self["menu"].setIndex(self.number - 1)
		self.resetNumberKey()
		selection = self["menu"].getCurrent()
		if selection and selection[1]:
			selection[1]()

	def execText(self, text):
		exec(text)

	def runScreen(self, arg):
		# arg[0] is the module (as string)
		# arg[1] is Screen inside this module
		#	plus possible arguments, as
		#	string (as we want to reference
		#	stuff which is just imported)
		if arg[0] != "":
			exec("from %s import %s" % (arg[0], arg[1].split(",")[0]))
			self.openDialog(*eval(arg[1]))

	def nothing(self): #dummy
		pass

	def openDialog(self, *dialog): # in every layer needed
		self.session.openWithCallback(self.menuClosed, *dialog)

	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def addMenu(self, destList, node):
		if not (key := node.get("key")):
			return
		requires = node.get("requires")
		if requires:
			if requires[0] == '!':
				if SystemInfo.get(requires[1:], False):
					return
			elif not SystemInfo.get(requires, False):
				return
		conditional = node.get("conditional")
		if conditional and not eval(conditional):
			return
		menu_text = _(x) if (x := node.get("text")) else "* fix me *"
		weight = node.get("weight", 50)
		description = _(x) if (x := node.get("description", "")) else None
		menupng = MenuEntryPixmap(key, self.png_cache)
		x = node.get("flushConfigOnClose")
		if x:
			a = boundFunction(self.session.openWithCallback, self.menuClosedWithConfigFlush, Menu, node)
		else:
			a = boundFunction(self.session.openWithCallback, self.menuClosed, Menu, node)
		#TODO add check if !empty(node.childNodes)
		destList.append((menu_text, a, key, weight, description, menupng))

	def menuClosedWithConfigFlush(self, *res):
		configfile.save()
		self.menuClosed(*res)

	def menuClosed(self, *res):
		if res and res[0]:
			self.close(True)
		elif len(self.list) == 1:
			self.close()
		else:
			self.createMenuList()

	def addItem(self, destList, node):
		if not (key := node.get("key")):
			return
		requires = node.get("requires")
		if requires:
			if requires[0] == '!':
				if SystemInfo.get(requires[1:], False):
					return
			elif not SystemInfo.get(requires, False):
				return
		conditional = node.get("conditional")
		if conditional and not eval(conditional):
			return
		item_text = _(x) if (x := node.get("text")) else "* fix me *"
		weight = node.get("weight", 50)
		description = _(x) if (x := node.get("description", "")) else None
		menupng = MenuEntryPixmap(key, self.png_cache)
		for x in node:
			if x.tag == 'screen':
				module = x.get("module")
				screen = x.get("screen")

				if screen is None:
					screen = module

				if module:
					module = "Screens." + module
				else:
					module = ""

				# check for arguments. they will be appended to the
				# openDialog call
				args = x.text or ""
				screen += ", " + args

				destList.append((item_text, boundFunction(self.runScreen, (module, screen)), key, weight, description, menupng))
				return
			elif x.tag == 'plugin':
				extensions = x.get("extensions")
				system = x.get("system")
				screen = x.get("screen")

				if extensions:
					module = extensions
				elif system:
					module = system

				if screen is None:
					screen = module

				if extensions:
					module = "Plugins.Extensions." + extensions + '.plugin'
				elif system:
					module = "Plugins.SystemPlugins." + system + '.plugin'
				else:
					module = ""

				# check for arguments. they will be appended to the
				# openDialog call
				args = x.text or ""
				screen += ", " + args

				destList.append((item_text, boundFunction(self.runScreen, (module, screen)), key, weight, description, menupng))
				return
			elif x.tag == 'code':
				destList.append((item_text, boundFunction(self.execText, x.text), key, weight, description, menupng))
				return
			elif x.tag == 'setup':
				id = x.get("id")
				destList.append((item_text, boundFunction(self.openSetup, id), key, weight, description, menupng))
				return
		destList.append((item_text, self.nothing, key, weight, description, menupng))

	def sortByName(self, listentry):
		return listentry[0].lower()

	def __init__(self, session, parent):
		self.parentmenu = parent
		Screen.__init__(self, session)
		self.menulength = 0
		self["key_blue"] = StaticText("")
		self["key_previous"] = StaticText(_("PREVIOUS"))
		self["key_next"] = StaticText(_("NEXT"))
		self["menu"] = List([])
		self["menu"].enableWrapAround = True
		self.showNumericHelp = False
		self.createMenuList()

		# for the skin: first try a menu_<menuID>, then Menu
		self.skinName = []
		if self.menuID is not None:
			if config.usage.menutype.value == "horzanim" and findSkinScreen("Animmain"):
				self.skinName.append("Animmain")
			elif config.usage.menutype.value == "horzicon" and findSkinScreen("Iconmain"):
				self.skinName.append("Iconmain")
			else:
				self.skinName.append("menu_" + self.menuID)
		self.skinName.append("Menu")

		ProtectedScreen.__init__(self)

		self["actions"] = NumberActionMap(["OkCancelActions", "MenuActions", "NumberActions", "HelpActions", "ColorActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.closeNonRecursive,
				"menu": self.closeRecursive,
				"0": self.keyNumberGlobal,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"displayHelp": self.showHelp,
				"blue": self.keyBlue,
			})
		title = parent.get("title", "") or None
		title = title and _(title) or _(parent.get("text", ""))
		title = self.__class__.__name__ == "MenuSort" and _("Menusort (%s)") % title or title
		if title is None:
			title = _(parent.get("text", "").encode("UTF-8", "ignore"))
		else:
			t_history.reset()
		self["title"] = StaticText(title)
		self.setTitle(title)
		self.loadMenuImage()

		self.menu_title = title
		self["thistory"] = StaticText(t_history.thistory)
		history_len = len(t_history.thistory)
		self["title0"] = StaticText("")
		self["title1"] = StaticText("")
		self["title2"] = StaticText("")
		if history_len < 13:
			self["title0"] = StaticText(title)
		elif history_len < 21:
			self["title0"] = StaticText("")
			self["title1"] = StaticText(title)
		else:
			self["title0"] = StaticText("")
			self["title1"] = StaticText("")
			self["title2"] = StaticText(title)
		if t_history.thistory == "":
			t_history.thistory = str(title) + " > "
		else:
			t_history.thistory = t_history.thistory + str(title) + " > "
		if config.usage.menutype.value == "horzanim" and findSkinScreen("Animmain"):
			self["label1"] = StaticText()
			self["label2"] = StaticText()
			self["label3"] = StaticText()
			self["label4"] = StaticText()
			self["label5"] = StaticText()
			self.onShown.append(self.openTestA)
		elif config.usage.menutype.value == "horzicon" and findSkinScreen("Iconmain"):
			self["label1"] = StaticText()
			self["label2"] = StaticText()
			self["label3"] = StaticText()
			self["label4"] = StaticText()
			self["label5"] = StaticText()
			self["label6"] = StaticText()
			self["label1s"] = StaticText()
			self["label2s"] = StaticText()
			self["label3s"] = StaticText()
			self["label4s"] = StaticText()
			self["label5s"] = StaticText()
			self["label6s"] = StaticText()
			self["pointer"] = Pixmap()
			self["pixmap1"] = Pixmap()
			self["pixmap2"] = Pixmap()
			self["pixmap3"] = Pixmap()
			self["pixmap4"] = Pixmap()
			self["pixmap5"] = Pixmap()
			self["pixmap6"] = Pixmap()
			self.onShown.append(self.openTestB)

		self.number = 0
		self.nextNumberTimer = eTimer()
		self.nextNumberTimer.callback.append(self.okbuttonClick)
		if len(self.list) == 1:
			self.onExecBegin.append(self.__onExecBegin)
		if self.layoutFinished not in self.onLayoutFinish:
			self.onLayoutFinish.append(self.layoutFinished)

	def openTestA(self):
		self.session.open(AnimMain, self.list, self.menu_title)
		self.close()

	def openTestB(self):
		self.session.open(IconMain, self.list, self.menu_title)
		self.close()

	def __onExecBegin(self):
		self.onExecBegin.remove(self.__onExecBegin)
		self.okbuttonClick()

	def layoutFinished(self):
		self.screenContentChanged()
		if self.menuImage and "menuimage" in self:
			self["menuimage"].instance.setPixmap(self.menuImage)

	def loadMenuImage(self):
		self.menuImage = None
		if menus and self.menuID:
			menuImage = menus.get(self.menuID, menus.get("default", ""))
			if menuImage:
				self.menuImage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, menuImage))
				if self.menuImage:
					self["menuimage"] = Pixmap()

	def showHelp(self):
		if config.usage.menu_show_numbers.value not in ("menu&plugins", "menu"):
			self.showNumericHelp = not self.showNumericHelp
			self.createMenuList(self.showNumericHelp)

	def createMenuList(self, showNumericHelp=False):
		self["key_blue"].text = _("Edit menu") if config.usage.menu_sort_mode.value == "user" else ""
		self.list = []
		self.menuID = self.parentmenu.get("key")
		for x in self.parentmenu: #walk through the actual nodelist
			if not x.tag:
				continue
			if x.tag == 'item':
				if int(x.get("level", 0)) <= config.usage.setup_level.index:
					self.addItem(self.list, x)
			elif x.tag == 'menu':
				if int(x.get("level", 0)) <= config.usage.setup_level.index:
					self.addMenu(self.list, x)

		if self.menuID:
			# plugins
			for l, description in plugins.getPluginsForMenuWithDescription(self.menuID):
				# check if a plugin overrides an existing menu
				plugin_menuid = l[2]
				for x in self.list:
					if x[2] == plugin_menuid:
						self.list.remove(x)
						break
				menupng = MenuEntryPixmap(l[2], self.png_cache)
				self.list.append((l[0], boundFunction(l[1], self.session, close=self.close), l[2], l[3] or 50, description, menupng))

		if "user" in config.usage.menu_sort_mode.value and self.menuID == "mainmenu":
			plugin_list = []
			id_list = []
			for l in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
				l.id = (l.name.lower()).replace(' ', '_')
				if l.id not in id_list:
					id_list.append(l.id)
					plugin_list.append((l.name, boundFunction(l.fnc, self.session), l.id, 200))

		if self.menuID is not None and "user" in config.usage.menu_sort_mode.value:
			self.sub_menu_sort = NoSave(ConfigDictionarySet())
			self.sub_menu_sort.value = config.usage.menu_sort_weight.getConfigValue(self.menuID, "submenu") or {}
			idx = 0
			for x in self.list:
				entry = list(self.list.pop(idx))
				m_weight = self.sub_menu_sort.getConfigValue(entry[2], "sort") or entry[3]
				entry.append(m_weight)
				self.list.insert(idx, tuple(entry))
				self.sub_menu_sort.changeConfigValue(entry[2], "sort", m_weight)
				idx += 1
			self.full_list = list(self.list)

		if config.usage.menu_sort_mode.value == "a_z":
			# Sort by Name
			self.list.sort(key=self.sortByName)
		elif "user" in config.usage.menu_sort_mode.value:
			self.hide_show_entries()
		else:
			# Sort by Weight
			self.list.sort(key=lambda x: int(x[3]))

		if config.usage.menu_show_numbers.value in ("menu&plugins", "menu") or showNumericHelp:
			self.list = [(str(x[0] + 1) + " " + x[1][0], x[1][1], x[1][2]) for x in enumerate(self.list)]

		if self.menulength != len(self.list): # updateList must only be used on a list of the same length. If length is different we call setList.
			self["menu"].setList(self.list)
			self.menulength = len(self.list)

		self["menu"].setList(self.list)
		self.screenContentChanged()

	def _onSelectionChanged(self):
		current = self["menu"].current
		description, pixmap = "", None
		if current:
			description, pixmap = current[4:]
		self["description"].setText(_(description))
		if pixmap:
			self["pixmap"].setPixmap(pixmap)

	def keyNumberGlobal(self, number):
		self.number = self.number * 10 + number
		if self.number and self.number <= len(self["menu"].list):
			if number * 10 > len(self["menu"].list) or self.number >= 10:
				self.okbuttonClick()
			else:
				self.nextNumberTimer.start(1500, True)
		else:
			self.resetNumberKey()

	def resetNumberKey(self):
		self.nextNumberTimer.stop()
		self.number = 0

	def closeNonRecursive(self):
		self.resetNumberKey()
		self.close(False)

	def closeRecursive(self):
		self.resetNumberKey()
		self.close(True)

	def createSummary(self):
		if config.usage.menutype.value == "standard":
			return MenuSummary

	def isProtected(self):
		if config.ParentalControl.setuppinactive.value:
			if config.ParentalControl.config_sections.main_menu.value and not (hasattr(self.session, 'infobar') and self.session.infobar is None):
				return self.menuID == "mainmenu"
			elif config.ParentalControl.config_sections.configuration.value and self.menuID == "setup":
				return True
			elif config.ParentalControl.config_sections.timer_menu.value and self.menuID == "timermenu":
				return True
			elif config.ParentalControl.config_sections.standby_menu.value and self.menuID == "shutdown":
				return True

	def keyBlue(self):
		if "user" in config.usage.menu_sort_mode.value:
			self.session.openWithCallback(self.menuSortCallBack, MenuSort, self.parentmenu)
		else:
			return 0

	def menuSortCallBack(self, key=False):
		self.createMenuList()

	def keyCancel(self):
		self.closeNonRecursive()

	def hide_show_entries(self):
		self.list = []
		for entry in self.full_list:
			if not self.sub_menu_sort.getConfigValue(entry[2], "hidden"):
				self.list.append(entry)
		if not self.list:
			self.list.append(('', None, 'dummy', '10', None, None, 10))
		self.list.sort(key=lambda listweight: int(listweight[-1]))


class MenuSort(Menu):
	def __init__(self, session, parent):
		self.somethingChanged = False
		Menu.__init__(self, session, parent)
		self.skinName = "MenuSort"
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save changes"))
		self["key_yellow"] = StaticText(_("Toggle show/hide"))
		self["key_blue"] = StaticText(_("Reset order (All)"))
		self["menu"].onSelectionChanged.append(self.selectionChanged)

		self["MoveActions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"moveUp": boundFunction(self.moveChoosen, -1),
			"moveDown": boundFunction(self.moveChoosen, +1),
			}, -1
		)
		self["EditActions"] = ActionMap(["ColorActions"],
		{
			"red": self.closeMenuSort,
			"green": self.keySave,
			"yellow": self.keyToggleShowHide,
			"blue": self.resetSortOrder,
		})
		self.onLayoutFinish.append(self.selectionChanged)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.menu_sort.value

	def resetSortOrder(self, key=None):
		config.usage.menu_sort_weight.value = {"mainmenu": {"submenu": {}}}
		config.usage.menu_sort_weight.save()
		self.createMenuList()

	def hide_show_entries(self):
		self.list = list(self.full_list)
		if not self.list:
			self.list.append(('', None, 'dummy', '10', None, None, 10))
		self.list.sort(key=lambda listweight: int(listweight[-1]))

	def selectionChanged(self):
		selection = self["menu"].getCurrent() and len(self["menu"].getCurrent()) > 2 and self["menu"].getCurrent()[2] or ""
		if self.sub_menu_sort.getConfigValue(selection, "hidden"):
			self["key_yellow"].setText(_("Show"))
		else:
			self["key_yellow"].setText(_("Hide"))

	def keySave(self):
		if self.somethingChanged:
			i = 10
			idx = 0
			for x in self.list:
				self.sub_menu_sort.changeConfigValue(x[2], "sort", i)
				if len(x) >= 5:
					entry = list(x)
					entry[4] = i
					entry = tuple(entry)
					self.list.pop(idx)
					self.list.insert(idx, entry)
				i += 10
				idx += 1
			config.usage.menu_sort_weight.changeConfigValue(self.menuID, "submenu", self.sub_menu_sort.value)
			config.usage.menu_sort_weight.save()
		self.close()

	def closeNonRecursive(self):
		self.closeMenuSort()

	def closeRecursive(self):
		self.closeMenuSort()

	def closeMenuSort(self):
		if self.somethingChanged:
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def cancelConfirm(self, result):
		if result:
			config.usage.menu_sort_weight.cancel()
			self.close()

	def okbuttonClick(self):
		self.keyToggleShowHide()

	def keyToggleShowHide(self):
		self.somethingChanged = True
		selection = self["menu"].getCurrent()[2]
		if self.sub_menu_sort.getConfigValue(selection, "hidden"):
			self.sub_menu_sort.removeConfigValue(selection, "hidden")
			self["key_yellow"].setText(_("Hide"))
		else:
			self.sub_menu_sort.changeConfigValue(selection, "hidden", 1)
			self["key_yellow"].setText(_("Show"))

	def moveChoosen(self, direction):
		self.somethingChanged = True
		currentIndex = self["menu"].getSelectedIndex()
		swapIndex = (currentIndex + direction) % len(self["menu"].list)
		self["menu"].list[currentIndex], self["menu"].list[swapIndex] = self["menu"].list[swapIndex], self["menu"].list[currentIndex]
		self["menu"].updateList(self["menu"].list)
		if direction > 0:
			self["menu"].down()
		else:
			self["menu"].up()

class AnimMain(Screen):
	def __init__(self, session, tlist, menuTitle):
		Screen.__init__(self, session)
		self.skinName = "Animmain"
		self.tlist = tlist
		ipage = 1
		list = []
		nopic = len(tlist)
		self.pos = []
		self.index = 0
		title = menuTitle
		self["title"] = Button(title)
		list = []
		tlist = []
		self["label1"] = StaticText()
		self["label2"] = StaticText()
		self["label3"] = StaticText()
		self["label4"] = StaticText()
		self["label5"] = StaticText()
		self["red"] = Button(_("Exit"))
		self["green"] = Button(_("Select"))
		self["yellow"] = Button(_("Config"))
		self["actions"] = NumberActionMap(["OkCancelActions", "MenuActions", "DirectionActions", "NumberActions", "ColorActions"], {
			"ok": self.okbuttonClick,
			"cancel": self.closeNonRecursive,
			"left": self.key_left,
			"right": self.key_right,
			"up": self.key_up,
			"down": self.key_down,
			"red": self.cancel,
			"green": self.okbuttonClick,
			"yellow": self.key_menu,
			"menu": self.closeRecursive,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal
		})
		nop = len(self.tlist)
		self.nop = nop
		nh = 1
		if nop == 1:
			nh = 1
		elif nop == 2:
			nh = 2
		elif nop == 3:
			nh = 2
		elif nop == 4:
			nh = 3
		elif nop == 5:
			nh = 3
		else:
			nh = int(float(nop) / 2)
		self.index = nh
		i = 0
		self.onShown.append(self.openTest)

	def key_menu(self):
		pass

	def cancel(self):
		self.close()

	def paintFrame(self):
		pass

	def openTest(self):
		i = self.index
		if i - 3 > -1:
			name1 = MenuEntryName(self.tlist[i - 3][0])
		else:
			name1 = " "
		if i - 2 > -1:
			name2 = MenuEntryName(self.tlist[i - 2][0])
		else:
			name2 = " "
		name3 = MenuEntryName(self.tlist[i - 1][0])
		if i < self.nop:
			name4 = MenuEntryName(self.tlist[i][0])
		else:
			name4 = " "
		if i + 1 < self.nop:
			name5 = MenuEntryName(self.tlist[i + 1][0])
		else:
			name5 = " "
		self["label1"].setText(name1)
		self["label2"].setText(name2)
		self["label3"].setText(name3)
		self["label4"].setText(name4)
		self["label5"].setText(name5)

	def key_left(self):
		self.index -= 1
		if self.index < 1:
			self.index = self.nop
		self.openTest()

	def key_right(self):
		self.index += 1
		if self.index > self.nop:
			self.index = 1
		self.openTest()

	def key_up(self):
		self.index = 1 if self.index > 1 else self.nop
		self.openTest()

	def key_down(self):
		self.index = self.nop if self.index < self.nop else 1
		self.openTest()

	def keyNumberGlobal(self, number):
		if number <= self.nop:
			self.index = number
			self.openTest()
			self.okbuttonClick()

	def closeNonRecursive(self):
		self.close(False)

	def closeRecursive(self):
		self.close(True)

	def createSummary(self):
		pass

	def okbuttonClick(self):
		idx = self.index - 1
		selection = self.tlist[idx]
		if selection is not None:
			selection[1]()


class IconMain(Screen):
	def __init__(self, session, tlist, menuTitle):
		Screen.__init__(self, session)
		self.skinName = "Iconmain"
		self.tlist = tlist
		ipage = 1
		list = []
		nopic = len(self.tlist)
		self.pos = []
		self.ipage = 1
		self.index = 0
		title = menuTitle
		self["title"] = Button(title)
		self.icons = []
		self.indx = []
		n1 = len(tlist)
		self.picnum = n1
		list = []
		tlist = []
		self["label1"] = StaticText()
		self["label2"] = StaticText()
		self["label3"] = StaticText()
		self["label4"] = StaticText()
		self["label5"] = StaticText()
		self["label6"] = StaticText()
		self["label1s"] = StaticText()
		self["label2s"] = StaticText()
		self["label3s"] = StaticText()
		self["label4s"] = StaticText()
		self["label5s"] = StaticText()
		self["label6s"] = StaticText()
		self["pointer"] = Pixmap()
		self["pixmap1"] = Pixmap()
		self["pixmap2"] = Pixmap()
		self["pixmap3"] = Pixmap()
		self["pixmap4"] = Pixmap()
		self["pixmap5"] = Pixmap()
		self["pixmap6"] = Pixmap()
		self["red"] = Button(_("Exit"))
		self["green"] = Button(_("Select"))
		self["yellow"] = Button(_("Config"))
		self["actions"] = NumberActionMap(["OkCancelActions", "MenuActions", "DirectionActions", "NumberActions", "ColorActions"], {
			"ok": self.okbuttonClick,
			"cancel": self.closeNonRecursive,
			"left": self.key_left,
			"right": self.key_right,
			"up": self.key_up,
			"down": self.key_down,
			"red": self.cancel,
			"green": self.okbuttonClick,
			"yellow": self.key_menu,
			"menu": self.closeRecursive,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal
		})
		self.index = 0
		i = 0
		self.maxentry = 29
		self.istart = 0
		i = 0
		self.onShown.append(self.openTest)

	def key_menu(self):
		pass

	def cancel(self):
		self.close()

	def paintFrame(self):
		pass

	def openTest(self):
		if self.ipage == 1:
			ii = 0
		elif self.ipage == 2:
			ii = 6
		elif self.ipage == 3:
			ii = 12
		elif self.ipage == 4:
			ii = 18
		elif self.ipage == 5:
			ii = 24
		dxml = config.skin.primary_skin.value
		dskin = dxml.split("/")
		j = 0
		i = ii
		while j < 6:
			j = j + 1
			if i > self.picnum - 1:
				icon = dskin[0] + "/blank.png"
				name = ""
			else:
				name = self.tlist[i][0]
			name = MenuEntryName(name)
			if j == self.index + 1:
				self["label" + str(j)].setText(" ")
				self["label" + str(j) + "s"].setText(name)
			else:
				self["label" + str(j)].setText(name)
				self["label" + str(j) + "s"].setText(" ")
			i = i + 1
		j = 0
		i = ii
		while j < 6:
			j = j + 1
			itot = (self.ipage - 1) * 6 + j
			if itot > self.picnum:
				if not default_skin():
					icon = "/usr/share/enigma2/" + dskin[0] + "/blank.png"
				else:
					icon = "/usr/share/enigma2/skin_default/buttons/blank.png"
			else:
				if not default_skin():
					icon = "/usr/share/enigma2/" + dskin[0] + "/buttons/icon1.png"
				else:
					icon = "/usr/share/enigma2/skin_default/buttons/icon1.png"
			pic = icon
			self["pixmap" + str(j)].instance.setPixmapFromFile(pic)
			i = i + 1
		if self.picnum > 6:
			try:
				dpointer = "/usr/share/enigma2/" + dskin[0] + "/pointer.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)
			except:
				dpointer = "/usr/share/enigma2/skin_default/pointer.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)
		else:
			try:
				dpointer = "/usr/share/enigma2/" + dskin[0] + "/blank.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)
			except:
				dpointer = "/usr/share/enigma2/skin_default/blank.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)

	def key_left(self):
		self.index -= 1
		if self.index < 0:
			self.key_up(True)
		else:
			self.openTest()

	def key_right(self):
		self.index += 1
		inum = self.picnum - 1 - (self.ipage - 1) * 6
		if self.index > inum or self.index > 5:
			self.key_down()
		else:
			self.openTest()

	def key_up(self, focusLastPic=False):
		self.ipage = self.ipage - 1
		if self.ipage < 1 and 7 > self.picnum > 0:
			self.ipage = 1
			focusLastPic = focusLastPic or self.index == 0
		elif self.ipage < 1 and 13 > self.picnum > 6:
			self.ipage = 2
		elif self.ipage < 1 and 19 > self.picnum > 12:
			self.ipage = 3
		elif self.ipage < 1 and 25 > self.picnum > 18:
			self.ipage = 4
		elif self.ipage < 1 and 31 > self.picnum > 24:
			self.ipage = 5
		if focusLastPic:
			inum = self.picnum - 1 - (self.ipage - 1) * 6
			self.index = inum if inum < 5 else 5
		else:
			self.index = 0
		self.openTest()

	def key_down(self, focusLastPic=False):
		self.ipage = self.ipage + 1
		if self.ipage == 2 and 7 > self.picnum > 0:
			self.ipage = 1
			focusLastPic = focusLastPic or self.index < self.picnum - 1 - (self.ipage - 1) * 6
		elif self.ipage == 3 and 13 > self.picnum > 6:
			self.ipage = 1
		elif self.ipage == 4 and 19 > self.picnum > 12:
			self.ipage = 1
		elif self.ipage == 5 and 25 > self.picnum > 18:
			self.ipage = 1
		elif self.ipage == 6 and 31 > self.picnum > 24:
			self.ipage = 1
		if focusLastPic:
			inum = self.picnum - 1 - (self.ipage - 1) * 6
			self.index = inum if inum < 5 else 5
		else:
			self.index = 0
		self.openTest()

	def keyNumberGlobal(self, number):
		if number == 7:
			self.key_up()
		elif number == 8:
			self.closeNonRecursive()
		elif number == 9:
			self.key_down()
		else:
			number -= 1
			if number <= self.picnum - 1 - (self.ipage - 1) * 6:
				self.index = number
				self.openTest()
				self.okbuttonClick()

	def closeNonRecursive(self):
		self.close(False)

	def closeRecursive(self):
		self.close(True)

	def createSummary(self):
		pass

	def okbuttonClick(self):
		if self.ipage == 1:
			idx = self.index
		elif self.ipage == 2:
			idx = self.index + 6
		elif self.ipage == 3:
			idx = self.index + 12
		elif self.ipage == 4:
			idx = self.index + 18
		elif self.ipage == 5:
			idx = self.index + 24
		if idx > self.picnum - 1:
			return
		if idx is None:
			return
		selection = self.tlist[idx]
		if selection is not None:
			selection[1]()




class MainMenu(Menu):
	#add file load functions for the xml-file

	def __init__(self, *x):
		self.skinName = "Menu"
		Menu.__init__(self, *x)
