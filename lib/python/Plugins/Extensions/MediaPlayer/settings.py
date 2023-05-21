# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Components.FileList import FileList
from Components.Sources.StaticText import StaticText
from Components.MediaPlayer import PlayList
from Components.config import config, ConfigYesNo, ConfigDirectory
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap

config.mediaplayer.repeat = ConfigYesNo(default=False)
config.mediaplayer.savePlaylistOnExit = ConfigYesNo(default=True)
config.mediaplayer.saveDirOnExit = ConfigYesNo(default=False)
config.mediaplayer.defaultDir = ConfigDirectory()
config.mediaplayer.sortPlaylists = ConfigYesNo(default=False)
config.mediaplayer.alwaysHideInfoBar = ConfigYesNo(default=True)
config.mediaplayer.onMainMenu = ConfigYesNo(default=False)


class DirectoryBrowser(Screen, HelpableScreen):

	def __init__(self, session, currDir):
		Screen.__init__(self, session)
		# for the skin: first try MediaPlayerDirectoryBrowser, then FileBrowser, this allows individual skinning
		self.skinName = ["MediaPlayerDirectoryBrowser", "FileBrowser"]
		self.setTitle(_("Directory browser"))

		HelpableScreen.__init__(self)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Use"))

		self.filelist = FileList(currDir, matchingPattern="")
		self["filelist"] = self.filelist

		self["FilelistActions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"green": self.use,
				"red": self.exit,
				"ok": self.ok,
				"cancel": self.exit
			})

	def ok(self):
		if self.filelist.canDescent():
			self.filelist.descent()

	def use(self):
		if self["filelist"].getCurrentDirectory() is not None:
			if self.filelist.canDescent() and self["filelist"].getFilename() and len(self["filelist"].getFilename()) > len(self["filelist"].getCurrentDirectory()):
				self.filelist.descent()
				self.close(self["filelist"].getCurrentDirectory())
		else:
				self.close(self["filelist"].getFilename())

	def exit(self):
		self.close(False)


class MediaPlayerSettings(ConfigListScreen, Screen):

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		# for the skin: first try MediaPlayerSettings, then Setup, this allows individual skinning
		self.skinName = ["MediaPlayerSettings", "Setup"]
		self.setTitle(_("Edit settings"))

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		ConfigListScreen.__init__(self, [], session)
		self.parent = parent
		self.initConfigList()
		config.mediaplayer.saveDirOnExit.addNotifier(self.initConfigList)

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.keySave,
			"red": self.keyCancel,
			"cancel": self.keyCancel,
			"ok": self.ok,
		}, -2)

	def initConfigList(self, element=None):
		print("[initConfigList]", element)
		try:
			self.list = []
			self.list.append((_("Repeat playlist"), config.mediaplayer.repeat))
			self.list.append((_("Save playlist on exit"), config.mediaplayer.savePlaylistOnExit))
			self.list.append((_("Save last directory on exit"), config.mediaplayer.saveDirOnExit))
			if not config.mediaplayer.saveDirOnExit.getValue():
				self.list.append((_("Start directory"), config.mediaplayer.defaultDir))
			self.list.append((_("Sorting of playlists"), config.mediaplayer.sortPlaylists))
			self.list.append((_("Always hide infobar"), config.mediaplayer.alwaysHideInfoBar))
			self.list.append((_("Show media player on main menu"), config.mediaplayer.onMainMenu))
			self["config"].setList(self.list)
		except KeyError:
			print("keyError")

	def ok(self):
		if self["config"].getCurrent()[1] == config.mediaplayer.defaultDir:
			self.session.openWithCallback(self.DirectoryBrowserClosed, DirectoryBrowser, self.parent.filelist.getCurrentDirectory())
		else:
			self.keySave()

	def DirectoryBrowserClosed(self, path):
		print("PathBrowserClosed:" + str(path))
		if path != False:
			config.mediaplayer.defaultDir.setValue(path)
