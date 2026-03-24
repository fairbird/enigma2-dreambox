# -*- coding: utf-8 -*-
from re import sub
from time import localtime
from enigma import eConsoleAppContainer
from Screens.Screen import Screen
from Components.ActionMap import HelpableActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Tools.Directories import fileWriteLines


MODULE_NAME = __name__.split(".")[-1]


class Console(Screen):
	#TODO move this to skin.xml
	skin = """
		<screen position="100,100" size="550,400" title="Command execution..." >
			<widget name="text" position="0,0" size="550,400" font="Console;14" />
		</screen>"""

	def __init__(self, session, title="Console", cmdlist=None, finishedCallback=None, closeOnSuccess=False, showStartStopText=True, skin=None, windowTitle=None):
		Screen.__init__(self, session)
		if windowTitle:
			title = windowTitle
		self.finishedCallback = finishedCallback
		self.closeOnSuccess = closeOnSuccess
		self.showStartStopText = showStartStopText
		if skin:
			self.skinName = [skin, "Console"]

		self.errorOcurred = False

		self["text"] = ScrollLabel("")
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Hide"))
		self["key_yellow"] = StaticText()
		self["summary_description"] = StaticText()

		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"ok": (self.closeConsole, _("Close the screen")),
			"cancel": (self.closeConsole, _("Close the screen")),
			"red": (self.cancel, _("Close this screen")),
			"up": (self["text"].pageUp, _("Move up a line")),
			"down": (self["text"].pageDown, _("Move down a line"))
		}, prio=0, description=_("Console Actions"))
		self["hideAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.toggleHideShow, _("Hide/Show the console screen"), _("NOTE: While the console screen is hidden from view the buttons are still active. Pressing any enabled button will cause the screen to reappear but the button will not be actioned.")),
		}, prio=0, description=_("Console Actions"))
		self["saveAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keySaveLog, _("Save the log of the console messages to a file")),
		}, prio=0, description=_("Console Actions"))
		self["saveAction"].setEnabled(False)

		self.cmdlist = isinstance(cmdlist, (list, tuple)) and list(cmdlist) or [cmdlist]
		self.newtitle = title == "Console" and _("Console") or title
		self.cancel_msg = None

		self.onShown.append(self.updateTitle)

		self.container = eConsoleAppContainer()
		self.run = 0
		self.finished = False
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun)  # dont start before gui is finished

	def updateTitle(self):
		self.setTitle(self.newtitle)

	def startRun(self):
		if self.showStartStopText:
			self["text"].setText(_("Execution progress:") + "\n\n")
		print("Console: executing in run", self.run, " the command:", self.cmdlist[self.run])
		if self.container.execute(self.cmdlist[self.run]):  # start of container application failed...
			self.runFinished(-1)  # so we must call runFinished manual

	def runFinished(self, retval):
		if retval:
			self.errorOcurred = True
			self.show()
		self.run += 1
		if self.run != len(self.cmdlist):
			if self.container.execute(self.cmdlist[self.run]):  # start of container application failed...
				self.runFinished(-1)  # so we must call runFinished manual
		else:
			self.show()
			self.finished = True
			lastpage = self["text"].isAtLastPage()
			text = ngettext("Command finished.", "Commands finished.", len(self.cmdlist))
			if self.cancel_msg:
				self.cancel_msg.close()
			if self.showStartStopText:
				self["text"].appendText(_("Execution finished!!"))
			self["summary_description"].setText(text)
			if self.finishedCallback is not None:
				self.finishedCallback()
			if not self.errorOcurred and self.closeOnSuccess:
				self.closeConsole()
			else:
				self["text"].appendText(_("\nPress OK or Exit to abort!"))
				self["key_red"].setText(_("Exit"))
				self["key_green"].setText("")
				self["key_yellow"].setText(_("Save Log"))
				self["saveAction"].setEnabled(True)

	def toggleHideShow(self):
		if self.finished:
			return
		if self.shown:
			self.hide()
		else:
			self.show()

	def cancel(self):
		if self.finished:
			self.closeConsole()
		else:
			self.cancel_msg = self.session.openWithCallback(self.cancelCallback, MessageBox, _("Cancel execution?"), type=MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())

	def cancelCallback(self, ret=None):
		self.cancel_msg = None
		if ret:
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)
			self.container.kill()
			self.close()

	def closeConsole(self):
		if self.finished:
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)
			self.close()
		else:
			self.show()

	def dataAvail(self, data):
		if isinstance(data, bytes):
			data = data.decode(errors='ignore')
		self["text"].appendText(data)

	def keySaveLog(self):
		def saveLogCallback(answer=None):
			if answer:
				text = sub(r"\\c[0-9A-F]{8}", "", self["text"].getText())
				if not fileWriteLines(self.outputFile, text, source=MODULE_NAME):
					self.session.open(MessageBox, _("Error: Unable to write log file '%s'!") % self.outputFile, type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
				self["key_yellow"].setText("")

		localTime = localtime()
		self.outputFile = f"/tmp/{localTime[3]:02d}{localTime[4]:02d}{localTime[5]:02d}_console.txt"
		self.session.openWithCallback(saveLogCallback, MessageBox, f"{_("Save the commands and output to the log file?")}\n('{self.outputFile}')", type=MessageBox.TYPE_YESNO, default=True, windowTitle=self.getTitle())
