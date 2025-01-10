# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.MovieList import AUDIO_EXTENSIONS
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Pixmap import Pixmap
from Components.config import config
import Screens.Standby
from enigma import ePoint, eTimer, iPlayableService, eActionMap
import os
import random
from sys import maxsize


class InfoBarScreenSaver:
	def __init__(self):
		self.onExecBegin.append(self.__onExecBegin)
		self.onExecEnd.append(self.__onExecEnd)
		self.screenSaverTimer = eTimer()
		self.screenSaverTimer.callback.append(self.screenSaverTimeout)
		self.screenSaver = self.session.instantiateDialog(screenSaver)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self.screenSaver.hide()

	def __onExecBegin(self):
		self.screenSaverTimerStart()

	def __onExecEnd(self):
		if self.screenSaver.shown:
			self.screenSaver.hide()
			eActionMap.getInstance().unbindAction("", self.screenSaverKeyPress)
		self.screenSaverTimer.stop()

	def screenSaverTimerStart(self):
		startTimer = config.usage.screenSaverStartTimer.value
		time = int(config.usage.screenSaverStartTimer.value)
		flag = hasattr(self, "seekstate") and self.seekstate[0]
		pip_show = hasattr(self.session, "pipshown") and self.session.pipshown
		if not flag:
			ref = self.session.nav.getCurrentlyPlayingServiceReference()
			if ref and not pip_show:
				ref = ref.toString().split(":")
				flag = ref[2] in ("2", "A") or os.path.splitext(ref[10])[1].lower() in AUDIO_EXTENSIONS
		if startTimer and flag:
			self.screenSaverTimer.startLongTimer(startTimer)
		else:
			self.screenSaverTimer.stop()

	def screenSaverTimeout(self):
		if self.execing and not Screens.Standby.inStandby and not Screens.Standby.inTryQuitMainloop:
			self.hide()
			if hasattr(self, "pvrStateDialog"):
				self.pvrStateDialog.hide()
			self.screenSaver.show()
			eActionMap.getInstance().bindAction("", -maxsize - 1, self.screenSaverKeyPress)

	def screenSaverKeyPress(self, key, flag):
		if flag:
			self.screenSaver.hide()
			self.show()
			self.screenSaverTimerStart()
			eActionMap.getInstance().unbindAction("", self.screenSaverKeyPress)


class screenSaver(Screen):
	def __init__(self, session):

		self.skin = """
			<screen name="Screensaver" position="fill" flags="wfNoBorder">
				<eLabel position="fill" backgroundColor="#54000000" zPosition="0"/>
				<widget name="picture" pixmap="screensaverpicture.png" position="0,0" size="150,119" alphaTest="blend" transparent="1" zPosition="1"/>
			</screen>"""

		Screen.__init__(self, session)

		self.moveLogoTimer = eTimer()
		self.moveLogoTimer.callback.append(self.movePicture)
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStart: self.serviceStarted
			})

		self["picture"] = Pixmap()

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		picturesize = self["picture"].getSize()
		self.maxx = self.instance.size().width() - picturesize[0]
		self.maxy = self.instance.size().height() - picturesize[1]
		self.movePicture(timerActive=False)

	def __onHide(self):
		self.moveLogoTimer.stop()

	def __onShow(self):
		self.moveTimer = config.usage.screenSaverMoveTimer.value
		self.moveLogoTimer.startLongTimer(self.moveTimer)

	def serviceStarted(self):
		if self.shown:
			ref = self.session.nav.getCurrentlyPlayingServiceReference()
			if ref:
				ref = ref.toString().split(":")
				if not os.path.splitext(ref[10])[1].lower() in AUDIO_EXTENSIONS:
					self.hide()

	def movePicture(self, timerActive=True):
		self.posx = random.randint(1, self.maxx)
		self.posy = random.randint(1, self.maxy)
		self["picture"].instance.move(ePoint(self.posx, self.posy))
		if timerActive:
			self.moveLogoTimer.startLongTimer(self.moveTimer)
