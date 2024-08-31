# -*- coding: utf-8 -*-
import mmap
import re

from enigma import ePicLoad, getDesktop
from os import listdir
from os.path import dirname, exists, isdir, join

from skin import DEFAULT_SKIN, DEFAULT_DISPLAY_SKIN, EMERGENCY_NAME, EMERGENCY_SKIN, currentDisplaySkin, currentPrimarySkin, domScreens
from Components.ActionMap import HelpableNumberActionMap
from Components.config import config
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary
from Screens.Standby import TryQuitMainloop, QUIT_RESTART
from Tools.Directories import resolveFilename, SCOPE_GUISKIN, SCOPE_LCDSKIN, SCOPE_SKIN, fileReadXML


class SkinSelector(Screen):
	skin = ["""
	<screen name="SkinSelector" position="center,center" size="%d,%d">
		<widget name="preview" position="center,%d" size="%d,%d" alphatest="blend" />
		<widget source="skins" render="Listbox" position="center,%d" size="%d,%d" enableWrapAround="1" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template": [
					MultiContentEntryText(pos = (%d, 0), size = (%d, %d), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 1),
					MultiContentEntryText(pos = (%d, 0), size = (%d, %d), font = 0, flags = RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text = 2)
				],
				"fonts": [gFont("Regular",%d)],
				"itemHeight": %d
				}
			</convert>
		</widget>
		<widget source="description" render="Label" position="center,e-%d" size="%d,%d" font="Regular;%d" verticalAlignment="center" />
		<widget source="key_red" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_red" font="Regular;%d" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" />
		<widget source="key_green" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_green" font="Regular;%d" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" />
	</screen>""",
		670, 570,
		10, 356, 200,
		230, 650, 240,
		10, 350, 30,
		370, 260, 30,
		25,
		30,
		85, 650, 25, 20,
		10, 50, 140, 40, 20,
		160, 50, 140, 40, 20
	]

	def __init__(self, session, screenTitle=_("GUI Skin")):
		Screen.__init__(self, session, enableHelp=True, mandatoryWidgets=["skins"])

		element = domScreens.get("SkinSelector", (None, None))[0]
		Screen.setTitle(self, screenTitle)
		self.rootDir = resolveFilename(SCOPE_SKIN)
		self.config = config.skin.primary_skin
		self.current = currentPrimarySkin
		self.xmlList = ["skin.xml"]
		self.onChangedEntry = []
		self["skins"] = List(enableWrapAround=True)
		self["preview"] = Pixmap()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = StaticText(_("Please wait... Loading list..."))
		self["actions"] = HelpableNumberActionMap(self, ["OkActions", "SetupActions", "DirectionActions", "ColorActions", "ConfigListActions"], {
			"upUp": self.doNothing,
			"downUp": self.doNothing,
			"rightUp": self.doNothing,
			"leftUp": self.doNothing,
			"upRepeated": self.up,
			"downRepeated": self.down,
			"leftRepeated": self.up,
			"rightRepeated": self.down,
			"ok": (self.save, _("Save and activate the currently selected skin")),
			"cancel": (self.cancel, _("Cancel any changes to the currently active skin")),
			"close": (self.cancelRecursive, _("Cancel any changes to the currently active skin and exit all menus")),
			"red": (self.cancel, _("Cancel any changes to the currently active skin")),
			"green": (self.save, _("Save and activate the currently selected skin")),
			"up": (self.up, _("Move to the previous skin")),
			"down": (self.down, _("Move to the next skin")),
			"left": (self.left, _("Move to the previous page")),
			"right": (self.right, _("Move to the next page"))
		}, -1, description=_("Skin Selection Actions"))
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)
		self.onLayoutFinish.append(self.layoutFinished)

	def showPic(self, picInfo=""):
		ptr = self.picload.getData()
		if ptr is not None:
			self["preview"].instance.setPixmap(ptr.__deref__())

	def layoutFinished(self):
		self.picload.setPara((self["preview"].instance.size().width(), self["preview"].instance.size().height(), 1, 1, 1, 1, "#ff000000"))
		self.refreshList()

	def refreshList(self):
		emergency = _("Emergency")
		default = _("Default")
		defaultPicon = _("Default+Picon")
		current = _("Current")
		displayPicon = join(dirname(DEFAULT_DISPLAY_SKIN), "skin_display_picon.xml")
		displayGrautec = join(dirname(DEFAULT_DISPLAY_SKIN), "skin_display_grautec.xml")
		skinList = []
		# Find and list the available skins...
		for dir in [dir for dir in listdir(self.rootDir) if isdir(join(self.rootDir, dir))]:
			previewPath = join(self.rootDir, dir)
			for skinFile in self.xmlList:
				skin = join(dir, skinFile)
				skinPath = join(self.rootDir, skin)
				if exists(skinPath):
					parseDone = fileReadXML(skinPath)
					parseError = _("File error %s") % skin
					resolution = None
					if skinFile == "skin.xml":
						try:
							with open(skinPath, "rb") as fd:
								resolutions = {
									"480": _("NTSC"),
									"576": _("PAL"),
									"720": _("HD"),
									"1080": _("FHD"),
									"2160": _("4K"),
									"4320": _("8K"),
									"8640": _("16K")
								}
								mm = mmap.mmap(fd.fileno(), 0, prot=mmap.PROT_READ)
								skinheight = re.search(b"\<?resolution.*?\syres\s*=\s*\"(\d+)\"", mm).group(1)
								resolution = skinheight and resolutions.get(skinheight.decode(), None)
								mm.close()
						except:
							pass
						print("[SkinSelector] Resolution of skin '%s': '%s'." % (skinPath, "Unknown" if resolution is None else resolution))
						# Code can be added here to reject unsupported resolutions.
					# The "piconprev.png" image should be "prevpicon.png" to keep it with its partner preview image.
					preview = join(previewPath, "piconprev.png" if skinFile == "skin_display_picon.xml" else "prev.png")
					if skin == EMERGENCY_SKIN:
						list = [EMERGENCY_NAME, emergency, dir, skin, resolution, preview]
					elif skin == DEFAULT_SKIN:
						list = [dir, default, dir, skin, resolution, preview]
					elif skin == DEFAULT_DISPLAY_SKIN:
						list = [DEFAULT_DISPLAY_SKIN.split(".")[0].split("/")[1], default, dir, skin, DEFAULT_DISPLAY_SKIN.split("/skin_")[1], preview]
					elif skin == displayPicon:
						list = [displayPicon.split(".")[0].split("/")[1], default, dir, skin, displayPicon.split("/skin_")[1], preview]
					elif skin == displayGrautec:
						list = [displayGrautec.split(".")[0].split("/")[1], default, dir, skin, displayGrautec.split("/skin_")[1], preview]
					else:
						list = [dir, "", dir, skin, resolution, preview]
					if not parseDone:
						list[1] = parseError
					elif skin == self.current and "fallback" in skin:
						list[1] = "%s %s" % (current, emergency)
					elif skin == self.current and EMERGENCY_NAME in skin:
						list[1] = current
					elif skin != self.current and EMERGENCY_NAME in skin:
						list[1] = default
					elif skin == self.current:
						list[1] = current
					list.append("%s (%s)" % (list[0], list[1]) if list[1] else list[0])
					if list[1]:
						list[1] = "<%s>" % list[1]
					#0=SortKey, 1=Label, 2=Flag, 3=Directory, 4=Skin, 5=Resolution, 6=Preview, 7=Label + Flag
					skinList.append(tuple([list[0].upper()] + list))
		skinList.sort()
		self["skins"].setList(skinList)
		# Set the list pointer to the current skin...
		for index in range(len(skinList)):
			if skinList[index][4] == self.config.value:
				self["skins"].setIndex(index)
				break
		self.loadPreview()

	def loadPreview(self):
		self.currentSelectedSkin = self["skins"].getCurrent()
		preview, resolution, skin = self.currentSelectedSkin[6], self.currentSelectedSkin[5], self.currentSelectedSkin[4]
		self.changedEntry()
		if not exists(preview):
			preview = resolveFilename(SCOPE_GUISKIN, "noprev.png")
		self.picload.startDecode(preview)
		if skin == self.config.value:
			self["description"].setText(_("Press OK to keep the currently selected skin %s.") % resolution)
		else:
			self["description"].setText(_("Press OK to activate the selected skin %s.") % resolution)

	def cancel(self):
		self.close(False)

	def cancelRecursive(self):
		self.close(True)

	def save(self):
		label, skin = self.currentSelectedSkin[1], self.currentSelectedSkin[4]
		if skin == self.config.value:
			if skin == self.current:
				print("[SkinSelector] Selected skin: '%s' (Unchanged!)" % join(self.rootDir, skin))
				self.cancel()
			else:
				print("[SkinSelector] Selected skin: '%s' (Trying to restart again!)" % join(self.rootDir, skin))
				restartBox = self.session.openWithCallback(self.restartGUI, MessageBox, _("To apply the selected '%s' skin the GUI needs to restart.\nWould you like to restart the GUI now?") % label, MessageBox.TYPE_YESNO)
				restartBox.setTitle(_("SkinSelector: Restart GUI"))
		elif skin == self.current:
			print("[SkinSelector] Selected skin: '%s' (Pending skin '%s' cancelled!)" % (join(self.rootDir, skin), join(self.rootDir, self.config.value)))
			self.config.value = skin
			self.config.save()
			self.cancel()
		else:
			print("[SkinSelector] Selected skin: '%s'" % join(self.rootDir, skin))
			restartBox = self.session.openWithCallback(self.restartGUI, MessageBox, _("To save and apply the selected '%s' skin the GUI needs to restart.\nWould you like to save the selection and restart the GUI now?") % label, MessageBox.TYPE_YESNO)
			restartBox.setTitle(_("SkinSelector: Restart GUI"))

		if config.channelSelection.screenStyle.isChanged() or config.channelSelection.widgetStyle.isChanged():
			from Screens.ChannelSelection import ChannelSelectionSetup
			ChannelSelectionSetup.updateSettings(self.session)

	def restartGUI(self, answer):
		if answer:
			self.config.value = self.currentSelectedSkin[4]
			self.config.save()
			self.session.open(TryQuitMainloop, QUIT_RESTART)
		self.refreshList()

	def up(self):
		self["skins"].up()
		self.loadPreview()

	def down(self):
		self["skins"].down()
		self.loadPreview()

	def left(self):
		self["skins"].pageUp()
		self.loadPreview()

	def right(self):
		self["skins"].pageDown()
		self.loadPreview()

	# For summary screen.
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def createSummary(self):
		return SkinSelectorSummary

	def getCurrentName(self):
		current = self["skins"].getCurrent()[1]
		if current:
			current = current.replace("_", " ")
		return current

	def doNothing(self):
		pass


class LcdSkinSelector(SkinSelector):
	def __init__(self, session, screenTitle=_("Display Skin")):
		SkinSelector.__init__(self, session, screenTitle=screenTitle)
		self.skinName = ["LcdSkinSelector", "SkinSelector"]
		self.rootDir = resolveFilename(SCOPE_LCDSKIN)
		self.config = config.skin.display_skin
		self.current = currentDisplaySkin
		self.xmlList = ["skin_display.xml", "skin_display_picon.xml", "skin_display_grautec.xml"]


class SkinSelectorSummary(ScreenSummary):
	skin = '''
	<screen name="SkinSelectorSummary" position="0,0" size="400,240"> 
		<widget source="Name" render="Label" position="0,30" size="400,100" font="FdLcD;35" halign="center" valign="center" zPosition="2"/>
		<widget source="value" render="Label" position="0,140" size="400,100" font="FdLcD;35" halign="center" zPosition="2"/>
	</screen>
	'''
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")
		self["value"] = StaticText("")
		self["Name"] = StaticText("")
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent.onChangedEntry:
			self.parent.onChangedEntry.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent.onChangedEntry:
			self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self):
		currentEntry = self.parent["skins"].getCurrent()  # Label
		self["entry"].setText(currentEntry[1])
		self["value"].setText("%s   %s" % (currentEntry[5], currentEntry[2]) if currentEntry[5] and currentEntry[2] else currentEntry[5] or currentEntry[2])  # Resolution and/or Flag.
		self["Name"].setText(self["entry"].getText())
