from errno import ENOENT
from os import _exit, listdir, remove, system
from os.path import isdir, join as pathjoin
from shutil import rmtree

from Screens.Screen import Screen
from Screens.Setup import Setup
from Components.ActionMap import ActionMap
from Components.config import ConfigYesNo, config, ConfigSubsection, getConfigListEntry
from Components.Sources.StaticText import StaticText
from Components.ConfigList import ConfigListScreen
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Tools.Directories import SCOPE_CONFIG, SCOPE_SKIN, resolveFilename

config.FactoryReset = ConfigSubsection()
config.FactoryReset.resetFull = ConfigYesNo(default=True)
config.FactoryReset.resetBouquets = ConfigYesNo(default=True)
config.FactoryReset.resetKeymaps = ConfigYesNo(default=True)
config.FactoryReset.resetNetworks = ConfigYesNo(default=True)
config.FactoryReset.resetPlugins = ConfigYesNo(default=True)
config.FactoryReset.resetResumePoints = ConfigYesNo(default=True)
config.FactoryReset.resetSettings = ConfigYesNo(default=True)
config.FactoryReset.resetSkins = ConfigYesNo(default=True)
config.FactoryReset.resetTimers = ConfigYesNo(default=True)
config.FactoryReset.resetOthers = ConfigYesNo(default=True)

class FactoryReset(Screen, ConfigListScreen, ProtectedScreen):
        def __init__(self, session):
                Screen.__init__(self, session)
                ProtectedScreen.__init__(self)
                self.skinName = ["ParentalControlSetup", "Setup"]
                self.title = _("Factory Reset")
                self.onChangedEntry = []

                self.list = []
                ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)
                self.createSetup()

                self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
                {
                        "red": self.cancel,
                        "cancel": self.cancel,
                        "green": self.keySave,
                }, -2)
                self["key_green"] = StaticText("Reset")
                self.onLayoutFinish.append(self.layoutFinished)

        def layoutFinished(self):
                self.setTitle(self.title)

        def isProtected(self):
                return config.ParentalControl.configured.value and config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.manufacturer_reset.value

        def createSetup(self):
                self.bouquets = []
                self.keymaps = []
                self.networks = []
                self.plugins = []
                self.resumePoints = []
                self.settings = []
                self.skins = []
                self.timers = []
                self.others = []

                self.resetFull = config.FactoryReset.resetFull
                self.resetBouquets = config.FactoryReset.resetBouquets
                self.resetKeymaps = config.FactoryReset.resetKeymaps
                self.resetNetworks = config.FactoryReset.resetNetworks
                self.resetPlugins = config.FactoryReset.resetPlugins
                self.resetResumePoints = config.FactoryReset.resetResumePoints
                self.resetSettings = config.FactoryReset.resetSettings
                self.resetSkins = config.FactoryReset.resetSkins
                self.resetTimers = config.FactoryReset.resetTimers
                self.resetOthers = config.FactoryReset.resetOthers

                for file in sorted(listdir(resolveFilename(SCOPE_CONFIG))):
                        if isdir(file):
                                self.skins.append(file)
                        elif file in ("lamedb", "lamedb5"):
                                self.bouquets.append(file)
                        elif file in ("keymap.xml",):
                                self.keymaps.append(file)
                        elif file in ("automounts.xml",):
                                self.networks.append(file)
                        elif file in ("resumepoints.pkl",):
                                self.resumePoints.append(file)
                        elif file in ("settings",):
                                self.settings.append(file)
                        elif file in ("autotimer.xml", "pm_timers.xml", "timers.xml"):
                                self.timers.append(file)
                        elif file.startswith("bouquets."):
                                self.bouquets.append(file)
                        elif file.startswith("userbouquet."):
                                self.bouquets.append(file)
                        elif file.endswith(".cache"):
                                self.networks.append(file)
                        elif not file.startswith("skin_user") and file.endswith(".xml"):
                                self.plugins.append(file)
                        elif file.startswith("skin_user") and file.endswith(".xml"):
                                self.skins.append(file)
                        elif file.endswith(".mvi"):
                                self.skins.append(file)
                        else:
                                # print("[FactoryReset] DEBUG: Unclassified file='%s'." % file)
                                self.others.append(file)

                self.list = []
                self.list.append(getConfigListEntry(_("Full factory reset"), self.resetFull, _("Select 'Yes' to remove all settings, tuning data, timers, resume pointers etc. Selecting this option will restore the configuration to the initial settings before any configuration settings were applied. This is the most reliable form of Factory Reset.")))
                if not self.resetFull.value:
                        if len(self.bouquets):
                                self.list.append(getConfigListEntry(_("Remove all bouquet/tuning data"), self.resetBouquets, _("Select 'Yes' to remove all tuning data. Selecting this option will remove all tuning and bouquet data and will make timers non functional until the receiver is retuned.")))
                        if len(self.keymaps):
                                self.list.append(getConfigListEntry(_("Remove all keymap data"), self.resetKeymaps, _("Select 'Yes' to remove all keymap data. Selecting this option will remove all keymap override data and restore the default keymap definitions.")))
                        if len(self.networks):
                                self.list.append(getConfigListEntry(_("Remove all network data"), self.resetNetworks, _("Select 'Yes' to remove all network data. Selecting this option will remove all network data including automounts and network connection data including connection accounts and passwords. This could cause some Enigma2 functions to fail if they are configured to use these network resources.")))
                        if len(self.plugins):
                                self.list.append(getConfigListEntry(_("Remove all plugin setting data"), self.resetPlugins, _("Select 'Yes' to remove all plugin configuration data. Selecting this option will remove all plugin configuration data that is stored in the Enigma2 configuration folder. This will cause all affected plugins to return to their default settings. This could cause some plugins to not function until configured.")))
                        if len(self.resumePoints):
                                self.list.append(getConfigListEntry(_("Remove all resume point data"), self.resetResumePoints, _("Select 'Yes' to remove all media player resume data. Selecting this option will remove the data used to allow playback of media files to resume from the position where playback was last stopped. Playback position of recordings is not affected.")))
                        if len(self.settings):
                                self.list.append(getConfigListEntry(_("Remove all settings data"), self.resetSettings, _("Select 'Yes' to remove all main settings configuration data. Selecting this option will set all Enigma2 settings back to their default values.  This will also cause Enigma2 to run the Welcome Wizard on restart.")))
                        if len(self.skins):
                                self.list.append(getConfigListEntry(_("Remove all skin data"), self.resetSkins, _("Select 'Yes' to remove all user customisations of skin data. Selecting this option will remove all user based skin customisations. All affected skins will return to their standard settings. This will also clear any customied boot logos and backdrops.")))
                        if len(self.timers):
                                self.list.append(getConfigListEntry(_("Remove all timer data"), self.resetTimers, _("Select 'Yes' to remove all timer configuration data. Selecting this option will clear all timers, autotimers and power timers.")))
                        if len(self.others):
                                self.list.append(getConfigListEntry(_("Remove all other data"), self.resetOthers, _("Select 'Yes' to remove all other files and directories not covered by the options above.")))
                currentItem = self["config"].getCurrent()
                self["config"].setList(self.list)
                if config.usage.sort_settings.value:
                        self["config"].list.sort()
                self.moveToItem(currentItem)

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

        def keyLeft(self):
                ConfigListScreen.keyLeft(self)
                self.createSetup()

        def keyRight(self):
                ConfigListScreen.keyRight(self)
                self.createSetup()

        def keySave(self):
                self.session.openWithCallback(self.keySaveCallback, MessageBox, _("Selecting 'Yes' will delete the currently selected user data. This action can't be undone. You may want to create a backup before continuing.\n\nAre you sure you want to continue with the factory reset?"), default=False, title=_("Factory Reset"))

        def keySaveCallback(self, answer):
                if not answer:
                        return
                configDir = resolveFilename(SCOPE_CONFIG)
                if self.resetFull.value:
                        print("[FactoryReset] Performing a full factory reset.")
                        self.wipeFiles(configDir, [""])
                        defaultFiles = pathjoin(resolveFilename(SCOPE_SKIN), "defaults", ".")
                        if isdir(defaultFiles):
                                print("[FactoryReset] Copying default configuration from '%s'." % defaultFiles)
                                system("cp -a %s %s" % (defaultFiles, configDir))
                        else:
                                print("[FactoryReset] Warning: No default configuration is available!")
                else:
                        if len(self.bouquets) and self.resetBouquets.value:
                                print("[FactoryReset] Performing a bouquets reset.")
                                self.wipeFiles(configDir, self.bouquets)
                        if len(self.keymaps) and self.resetKeymaps.value:
                                print("[FactoryReset] Performing a keymap reset.")
                                self.wipeFiles(configDir, self.keymaps)
                        if len(self.networks) and self.resetNetworks.value:
                                print("[FactoryReset] Performing a networks reset.")
                                self.wipeFiles(configDir, self.networks)
                        if len(self.plugins) and self.resetPlugins.value:
                                print("[FactoryReset] Performing a plugins reset.")
                                self.wipeFiles(configDir, self.plugins)
                        if len(self.resumePoints) and self.resetResumePoints.value:
                                print("[FactoryReset] Performing a resume points reset.")
                                self.wipeFiles(configDir, self.resumePoints)
                        if len(self.settings) and self.resetSettings.value:
                                print("[FactoryReset] Performing a settings reset.")
                                self.wipeFiles(configDir, self.settings)
                        if len(self.skins) and self.resetSkins.value:
                                print("[FactoryReset] Performing a skins reset.")
                                self.wipeFiles(configDir, self.skins)
                        if len(self.timers) and self.resetTimers.value:
                                print("[FactoryReset] Performing a timers reset.")
                                self.wipeFiles(configDir, self.timers)
                        if len(self.others) and self.resetOthers.value:
                                print("[FactoryReset] Performing an other files reset.")
                                self.wipeFiles(configDir, self.others)
                print("[FactoryReset] Stopping the active service to display the backdrop.")
                self.session.nav.stopService()
                system("/usr/bin/showiframe /usr/share/backdrop.mvi")
                print("[FactoryReset] Stopping and exiting enigma2.")
                _exit(0)
                self.close()  # We should never get to here!

        def wipeFiles(self, path, fileList):
                for file in fileList:
                        target = pathjoin(path, file)
                        try:
                                if isdir(target):
                                        # print("[FactoryReset] DEBUG: Removing directory '%s'." % target)
                                        rmtree(target)
                                else:
                                        # print("[FactoryReset] DEBUG: Removing file '%s'." % target)
                                        remove(target)
                        except (IOError, OSError) as err:
                                if err.errno != ENOENT:
                                        print("[FactoryReset] Error: Unable to delete '%s'!  (%s)" % (target, str(err)))

        def closeConfigList(self, closeParameters=()):  # Suppress the save settings pop up on exit.
                self.close(*closeParameters)

        def cancel(self):
                for i in self["config"].list:
                        if len(i)>1:
                                i[1].cancel()
                self.close(False)
