# -*- coding: utf-8 -*-
from Screens.MessageBox import MessageBox
from Components.config import ConfigSubsection, ConfigYesNo, config, ConfigSelection
from enigma import eTimer, eConsoleAppContainer, getBoxType, eDVBDB
from Components.Label import Label
from time import time, strftime, localtime
from Tools import Notifications
from Screens.ChoiceBox import ChoiceBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Components.ActionMap import ActionMap
from Components.Opkg import OpkgComponent
from Components.Sources.StaticText import StaticText
from Components.Slider import Slider
from Screens.TextBox import TextBox
from Tools.BoundFunction import boundFunction
from urllib.request import urlopen
import datetime, os
import gettext, json

opkg_ugradable_filename = '/tmp/.opkg_ugradable'

config.updatecheck = ConfigSubsection()
config.updatecheck.check_update_notifier = ConfigSelection(default='604800', choices=[('-1', _('disabled')),
        ('43200', _('12 hours')),
        ('86400', _('daily')),
        ('604800', _('week')),
        ('2419200', _('monthly'))])
config.updatecheck.check_update_on_boot = ConfigYesNo(default=True)

REDC = '\x1b[31m'
YELLOWC = '\x1b[33m'
GRENC = '\x1b[32m'
ENDC = '\x1b[m'
def cprint(text):
        print(YELLOWC + text + ENDC)

def cprintoff(text):
        print(REDC + text + ENDC)

def cprinton(text):
        print(GRENC + text + ENDC)

def connected_to_internet():
        import requests
        try:
            _ = requests.get('https://github.com', timeout=5)
            return True
        except requests.ConnectionError:
            cprintoff("No internet connection available.")
            return False
        print(connected_to_internet())

def logdata(label_name = '', data = None):
        try:
            data = str(data)
            fp = open('/tmp/updatecheck_log', 'a')
            fp.write('\n:' + str(label_name) + ': ' + data)
            fp.close()
        except:
            pass

def AutoCheck(session = None, **kwargs):
        global installerupdatecheck
        #logdata('kwargs', kwargs)
        installerupdatecheck = InstallerUpdateCheck(session)
        installerupdatecheck.configChange()

class InstallerUpdateCheck:

        def __init__(self, session):
            if os.path.exists(opkg_ugradable_filename):
                os.remove(opkg_ugradable_filename)
            self.total_packages = None
            self.session = session
            self.timer = eTimer()
            self.timer.callback.append(self.checkForUpdate)
            config.updatecheck.check_update_notifier.addNotifier(self.configChange, initial_call=True)
            #logdata('config.updatecheck.check_update_on_boot.value', config.updatecheck.check_update_on_boot.value)
            if config.updatecheck.check_update_on_boot.value:
                if connected_to_internet() == True:
                       cprinton('[CheckInetrnet] we are Online')
                       self.checkForUpdate()
                else:
                       cprintoff('[CheckInetrnet] we are Offline')

        def configChange(self, configElement = None):
            if self.timer.isActive():
                self.timer.stop()
            cprint('[UpdateCheck] timer changed')
            self.startTimer()

        def startTimer(self):
            #logdata('config.updatecheck.check_update_notifier.value', config.updatecheck.check_update_notifier.value)
            self.value = int(config.updatecheck.check_update_notifier.value)
            if self.value > 0:
                nextupdate = strftime('%c', localtime(time() + self.value))
                cprinton('[startTimer-UpdateCheck] next check at ' + nextupdate)
                self.timer.startLongTimer(self.value)
            else:
                cprintoff('[startTimer-UpdateCheck] is offline')

        def checkForUpdate(self):
            #logdata('checkForUpdate', 'started')
            self.upgradableListData = ''
            self.container = eConsoleAppContainer()
            self.container.appClosed.append(self.runFinished)
            cprint('[UpdateCheck] Check...')
            self.container.execute('opkg update')

        def runFinished(self, retval):
            #logdata('runFinished', 'started')
            self.container.dataAvail.append(self.dataAvail)
            self.container.appClosed.remove(self.runFinished)
            self.container.appClosed.append(self.upgradableListFinished)
            self.container.execute('opkg list_upgradable && opkg list_upgradable > %s' % opkg_ugradable_filename)

        def dataAvail(self, line):
            #logdata('line dataAvail', line)
            if line.find(b'Read-only') == -1 and line.find(b'Permission denied') == -1 and line.find(b'HOLD') == -1 and line.find(b'PREFER') == -1:
                self.upgradableListData += str(line)

        def getOpkgUpgradale(self):
            count = None
            try:
                f = open(opkg_ugradable_filename, 'r')
                line = 'dummy'
                count = 0
                while line:
                    line = f.readline()
                    if not line == '':
                        count = count + 1
                f.close()
                print('[upgradable_list] updatable packages: %d' % count)
            except:
                pass
            return count

        def upgradableListFinished(self, value):
            #logdata('value', value)
            self.total_packages = self.getOpkgUpgradale()
            if self.upgradableListData:
                (cprint('[UpdateCheck] Updates available...'), self.upgradableListData)
                Notifications.AddNotificationWithCallback(self.runUpgrade, MessageBox, '\n' + _('[ %s ] updated package available.') % self.total_packages + '\n' + _('\nDo you want to start the firmware upgrade now?'), timeout=10, default=False)
            else:
                cprint('[UpdateCheck] No updates available')
            self.container = None
            self.startTimer()

        def runUpgrade(self, result):
            #logdata('runUpgrade', result)
            if result:
            	from Screens.SoftwareUpdate import SoftwareUpdate
            	self.session.open(SoftwareUpdate)
            	#self.session.open(UpdatePlugin) # Old method


class UpdatePlugin(Screen, ProtectedScreen):
        skin = '''<screen name="UpdatePlugin" position="center,center" size="550,300">
                        <widget name="activityslider" position="0,0" size="550,5"  />
                        <widget name="slider" position="0,150" size="550,30"  />
                        <widget source="package" render="Label" position="10,30" size="540,20" font="Regular;18" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
                        <widget source="status" render="Label" position="10,180" size="540,100" font="Regular;20" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
                </screen>'''

        def __init__(self, session, *args):
            Screen.__init__(self, session)
            ProtectedScreen.__init__(self)
            self.sliderPackages = {"dreambox-dvb-modules": 1, "enigma2": 2, "tuxbox-image-info": 3}
            self.setTitle(_('Software update'))
            self.slider = Slider(0, 4)
            self['slider'] = self.slider
            self.activityslider = Slider(0, 100)
            self['activityslider'] = self.activityslider
            self.status = StaticText(_('Please wait...'))
            self['status'] = self.status
            self.package = StaticText(_('Package list update'))
            self['package'] = self.package
            self.oktext = _('Press OK on your remote control to continue.')
            self.packages = 0
            self.error = 0
            self.processed_packages = []
            self.total_packages = None
            self.updating = False
            self.opkg = OpkgComponent()
            self.opkg.addCallback(self.opkgCallback)
            self.onClose.append(self.__close)
            self['actions'] = ActionMap(['WizardActions'], {'ok': self.exit, 'back': self.exit}, -1)
            self.activity = 0
            self.activityTimer = eTimer()
            self.activityTimer.callback.append(self.checkTraficLight)
            self.activityTimer.callback.append(self.doActivityTimer)
            self.activityTimer.start(100, True)

        def checkTraficLight(self):
            self.activityTimer.callback.remove(self.checkTraficLight)
            self.activityTimer.start(100, False)
            self.startActualUpdate()

        def startActualUpdate(self):
            self.updating = True
            self.opkg.startCmd(OpkgComponent.CMD_UPDATE)

        def doActivityTimer(self):
            self.activity += 1
            if self.activity == 100:
                self.activity = 0
            self.activityslider.setValue(self.activity)

        def showUpdateCompletedMessage(self):
            self.setEndMessage(ngettext("Update completed, %d package was installed.", "Update completed, %d packages were installed.", self.packages) % self.packages)

        def opkgCallback(self, event, param):
            if event == OpkgComponent.EVENT_DOWNLOAD:
                self.status.setText(_('Downloading'))
            elif event == OpkgComponent.EVENT_UPGRADE:
                if param in self.sliderPackages:
                    self.slider.setValue(self.sliderPackages[param])
                self.package.setText(param)
                self.status.setText(_('Updating') + ': %s/%s' % (self.packages, self.total_packages))
                if param not in self.processed_packages:
                    self.processed_packages.append(param)
                    self.packages += 1
            elif event == OpkgComponent.EVENT_INSTALL:
                self.package.setText(param)
                self.status.setText(_('Installing'))
                if param not in self.processed_packages:
                    self.processed_packages.append(param)
                    self.packages += 1
            elif event == OpkgComponent.EVENT_REMOVE:
                self.package.setText(param)
                self.status.setText(_('Removing'))
                if param not in self.processed_packages:
                    self.processed_packages.append(param)
                    self.packages += 1
            elif event == OpkgComponent.EVENT_CONFIGURING:
                self.package.setText(param)
                self.status.setText(_('Configuring'))
            elif event == OpkgComponent.EVENT_MODIFIED:
                if config.plugins.softwaremanager.overwriteConfigFiles.value in ('N', 'Y'):
                    self.opkg.write(True and config.plugins.softwaremanager.overwriteConfigFiles.value)
                else:
                    self.session.openWithCallback(self.modificationCallback, MessageBox, _('A configuration file (%s) has been modified since it was installed.\nDo you want to keep your modifications?') % param)
            elif event == OpkgComponent.EVENT_ERROR:
                self.error += 1
            elif event == OpkgComponent.EVENT_DONE:
                if self.updating:
                    self.updating = False
                    self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
                elif self.opkg.currentCommand == OpkgComponent.CMD_UPGRADE_LIST:
                    self.total_packages = len(self.opkg.getFetchedList())
                    if self.total_packages:
                            if self.total_packages > 150:
                                choices = [(_('Update and Full Reboot'), 'cold')]
                                message = ' ' + _('Reflash recommended!')
                            else:
                                choices = [(_('Update and Full Reboot (recommended)'), 'cold'), (_('Update and ask to Restart GUI'), 'hot')]
                            choices.append((_("Show packages to be updated"), "showlist"))
                    else:
                            message = _('No updates available')
                            choices = []
                    choices.append((_('Cancel'), ''))
                    self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, list=choices, windowTitle=self.title)
                elif self.error == 0:
                    self.showUpdateCompletedMessage()
                else:
                    self.activityTimer.stop()
                    self.activityslider.setValue(0)
                    error = _('Your receiver might be unusable now. Please consult the manual for further assistance before rebooting your receiver.')
                    if self.packages == 0:
                            error = _('No updates available. Please try again later.')
                    if self.updating:
                            error = _('Update failed. Your receiver does not have a working internet connection.')
                    self.status.setText(_('Error') + ' - ' + error)

        def setEndMessage(self, txt):
            self.slider.setValue(4)
            self.activityTimer.stop()
            self.activityslider.setValue(0)
            self.package.setText(txt)
            self.status.setText(self.oktext)

        def startActualUpgrade(self, answer):
            if not answer or not answer[1]:
                self.close()
                return
            if answer[1] == "cold":
                self.session.open(TryQuitMainloop, retvalue=42)
                self.close()
            elif answer[1] == "showlist":
                text = "\n".join([x[0] for x in sorted(self.opkg.getFetchedList(), key=lambda d: d[0])])
                self.session.openWithCallback(boundFunction(self.opkgCallback, OpkgComponent.EVENT_DONE, None), TextBox, text, _("Packages to update"), True)
            else:
                self.opkg.startCmd(OpkgComponent.CMD_UPGRADE, args={'test_only': False})

        def modificationCallback(self, res):
            self.opkg.write(res and 'N' or 'Y')

        def exit(self):
            if not self.opkg.isRunning():
                if self.packages != 0 and self.error == 0:
                    self.session.openWithCallback(self.exitAnswer, MessageBox, _('Update completed. Do you want to Restart GUI NoW?'))
                else:
                    self.close()
            elif not self.updating:
                self.close()

        def exitAnswer(self, result):
            if result is not None and result:
                self.session.open(TryQuitMainloop, retvalue=3)
            self.close()

        def __close(self):
            self.opkg.removeCallback(self.opkgCallback)
