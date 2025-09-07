# -*- coding: utf-8 -*-
from enigma import eTimer, eSize
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap, MultiPixmap
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen, ScreenSummary


class MessageBox(Screen):
	skin = """
	<screen name="MessageBox" position="center,center" size="520,225" resolution="1280,720">
		<widget name="icon" pixmaps="icons/input_question.png,icons/input_info.png,icons/input_warning.png,icons/input_error.png,icons/input_message.png" position="10,10" size="53,53" alphatest="blend" conditional="icon" scale="1" transparent="1" />
		<widget name="text" position="75,10" size="435,120" font="Regular;22" transparent="1" />
		<widget name="list" position="10,e-80" size="500,70" conditional="list" enableWrapAround="1" font="Regular;25" itemHeight="35" scrollbarMode="showOnDemand" transparent="1" />
	</screen>"""

	TYPE_NOICON = 0
	TYPE_YESNO = 1
	TYPE_INFO = 2
	TYPE_WARNING = 3
	TYPE_ERROR = 4
	TYPE_MESSAGE = 5
	TYPE_PREFIX = {
		TYPE_YESNO: _("Question"),
		TYPE_INFO: _("Information"),
		TYPE_WARNING: _("Warning"),
		TYPE_ERROR: _("Error"),
		TYPE_MESSAGE: _("Message")
	}

	def __init__(self, session, text, type=TYPE_YESNO, timeout=-1, list=None, close_on_any_key=False, default=True, enable_input=True, enableInput=True, msgBoxID=None, picon=None, simple=False, timeout_default=None, windowTitle=None, skinName=None, skin_name=None, title=None, showYESNO=False, closeOnAnyKey=False, typeIcon=None, timeoutDefault=None):
		self.type = type
		Screen.__init__(self, session, enableHelp=True)
		self.text = text

		self["text"] = Label(text)
		self["Text"] = StaticText(text)
		self["selectedChoice"] = StaticText()
		self["key_help"] = StaticText(_("HELP"))
		self["ErrorPixmap"] = Pixmap()
		self["QuestionPixmap"] = Pixmap()
		self["InfoPixmap"] = Pixmap()
		self["WarningPixmap"] = Pixmap()
		self.timerRunning = False
		self.initTimeout(timeout)

		if enable_input is False:  # Process legacy enable_input argument.
			enableInput = False
		if enableInput:
			self.createActionMap(0)
		self.msgBoxID = msgBoxID
		picon = picon or type
		if picon != self.TYPE_ERROR:
			self["ErrorPixmap"].hide()
		if picon != self.TYPE_YESNO:
			self["QuestionPixmap"].hide()
		if picon != self.TYPE_INFO:
			self["InfoPixmap"].hide()
		if picon != self.TYPE_WARNING:
			self["WarningPixmap"].hide()
		if picon is not None:  # Process legacy picon argument.
			typeIcon = picon
		if typeIcon is None:
			typeIcon = type
		self.typeIcon = typeIcon
		self.picon = (typeIcon != self.TYPE_NOICON)  # Legacy picon argument to support old skins.
		if typeIcon:
			self["icon"] = MultiPixmap()
		if timeout_default is not None:  # Process legacy timeout_default argument.
			timeoutDefault = timeout_default
		self.timeoutDefault = timeoutDefault
		if close_on_any_key is True:  # Process legacy close_on_any_key argument.
			closeOnAnyKey = True
		self.closeOnAnyKey = closeOnAnyKey
		if skin_name is not None:  # Process legacy skin_name argument.
			skinName = skin_name
		self.skinName = ["MessageBox"]
		if simple:  # Process legacy simple argument, use skinName instead.
			self.skinName.insert(0, "MessageBoxSimple")
		if skinName:
			if isinstance(skinName, str):
				self.skinName.insert(0, skinName)
			else:
				self.skinName = skinName + self.skinName
		if title is not None:  # Process legacy title argument.
			windowTitle = title
		self.windowTitle = windowTitle or self.TYPE_PREFIX.get(type, _("Message"))
		self.baseTitle = self.windowTitle
		self.activeTitle = self.windowTitle
		if type == self.TYPE_YESNO or showYESNO:
			self.list = [(_("Yes"), True), (_("No"), False)] if list is None else list
			self["list"] = MenuList(self.list)
			if isinstance(default, bool):
				self.startIndex = 0 if default else 1
			elif isinstance(default, int):
				self.startIndex = default
			else:
				print(f"[MessageBox] Error: The context of the default ({default}) can't be determined!")
		else:
			self["list"] = MenuList([])
			self["list"].hide()
			self.list = None
		self.onLayoutFinish.append(self.layoutFinished)

	def __repr__(self):
		return f"{str(type(self))}({self.text})"

	def layoutFinished(self):
		if self.list:
			self["list"].enableAutoNavigation(False)  # Override listbox navigation.
		if self.typeIcon:
			self["icon"].setPixmapNum(self.typeIcon - 1)
		prefix = self.TYPE_PREFIX.get(self.type, _("Unknown"))
		if self.baseTitle is None:
			title = self.getTitle()
			if title:
				self.baseTitle = title % prefix if "%s" in title else title
			else:
				self.baseTitle = prefix
		elif "%s" in self.baseTitle:
			self.baseTitle = self.baseTitle % prefix
		self.setTitle(self.baseTitle, showPath=False)
		if self.timeout > 0:
			print(f"[MessageBox] Timeout set to {self.timeout} seconds.")
			self.timer.start(25)

	def createActionMap(self, prio):
		self["actions"] = ActionMap(["MsgBoxActions", "DirectionActions"],
			{
				"cancel": self.cancel,
				"select": self.select,
				"selectOk": self.selectOk,
				"up": self.up,
				"down": self.down,
				"left": self.pageUp,
				"right": self.pageDown,
				"upRepeated": self.up,
				"downRepeated": self.down,
				"leftRepeated": self.pageUp,
				"rightRepeated": self.pageDown
			}, -1)

	def initTimeout(self, timeout):
		self.timeout = timeout
		if timeout > 0:
			self.timer = eTimer()
			self.timer.callback.append(self.timerTick)
			self.onExecBegin.append(self.startTimer)
			self.origTitle = None
			if self.execing:
				self.timerTick()
			else:
				self.onShown.append(self.__onShown)
			self.timerRunning = True
		else:
			self.timerRunning = False

	def __onShown(self):
		self.onShown.remove(self.__onShown)
		self.timerTick()

	def startTimer(self):
		self.timer.start(1000)

	def stopTimer(self):
		if self.timerRunning:
			del self.timer
			self.onExecBegin.remove(self.startTimer)
			self.setTitle(self.origTitle, showPath=False)
			self.timerRunning = False

	def timerTick(self):
		if self.execing:
			self.timeout -= 1
			if self.origTitle is None:
				self.origTitle = self.instance.getTitle()
			self.setTitle(self.origTitle + " (" + str(self.timeout) + ")", showPath=False)
			if self.timeout == 0:
				self.timer.stop()
				self.timerRunning = False
				self.timeoutCallback()

	def timeoutCallback(self):
		if self.timeoutDefault is not None:
			self.close(self.timeoutDefault)
		else:
			self.selectOk()

	def cancel(self):
		self.close(False)

	def select(self):
		if self.list:
			self.close(self["list"].getCurrent()[1])
		else:
			self.close(True)

	def selectOk(self):
		self.close(True)

	def top(self):
		self.move(self["list"].instance.moveTop)

	def up(self):
		self.move(self["list"].instance.moveUp)

	def down(self):
		self.move(self["list"].instance.moveDown)

	def pageUp(self):
		self.move(self["list"].instance.pageUp)

	def pageDown(self):
		self.move(self["list"].instance.pageDown)

	def bottom(self):
		self.move(self["list"].instance.moveEnd)

	def move(self, direction):
		if self.closeOnAnyKey:
			self.close(True)
		self["list"].instance.moveSelection(direction)
		if self.list:
			self["selectedChoice"].setText(self["list"].getCurrent()[0])
		self.stopTimer()

	def __repr__(self):
		return "%s(%s)" % (str(type(self)), self.text if hasattr(self, "text") else "<title>")

	def getListWidth(self):
		return self["list"].instance.getMaxItemTextWidth()

	def createSummary(self):
		return MessageBoxSummary

	def reloadLayout(self):
		for method in self.onLayoutFinish:
			if not isinstance(method, type(self.close)):
				exec(method, globals(), locals())
			else:
				method()
		self.layoutFinished()


class MessageBoxSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["text"] = StaticText(parent.text)
		self["option"] = StaticText("")
		if parent.list:
			if self.addWatcher not in self.onShow:
				self.onShow.append(self.addWatcher)
			if self.removeWatcher not in self.onHide:
				self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent["list"].onSelectionChanged:
			self.parent["list"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent["list"].onSelectionChanged:
			self.parent["list"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["option"].setText(self.parent["list"].getCurrent()[0])


class ModalMessageBox:
	instance = None

	def __init__(self, session):
		if ModalMessageBox.instance:
			print("[ModalMessageBox] Error: Only one ModalMessageBox instance is allowed!")
		else:
			ModalMessageBox.instance = self
			self.dialog = session.instantiateDialog(MessageBox, "", enableInput=False, skinName="MessageBoxModal")
			self.dialog.setAnimationMode(0)

	def showMessageBox(self, text=None, timeout=-1, list=None, default=True, closeOnAnyKey=False, windowTitle=None, msgBoxID=None, typeIcon=MessageBox.TYPE_YESNO, enableInput=True, callback=None):
		self.dialog.text = text
		self.dialog["text"].setText(text)
		self.dialog.typeIcon = typeIcon
		self.dialog.type = typeIcon
		self.dialog.picon = (typeIcon != MessageBox.TYPE_NOICON)  # Legacy picon argument to support old skins.
		if typeIcon == MessageBox.TYPE_YESNO:
			self.dialog.list = [(_("Yes"), True), (_("No"), False)] if list is None else list
			self.dialog["list"].setList(self.dialog.list)
			if isinstance(default, bool):
				self.dialog.startIndex = 0 if default else 1
			elif isinstance(default, int):
				self.dialog.startIndex = default
			else:
				print(f"[MessageBox] Error: The context of the default ({default}) can't be determined!")
			self.dialog["list"].show()
		else:
			self.dialog["list"].hide()
			self.dialog.list = None
		self.callback = callback
		self.dialog.timeout = timeout
		self.dialog.msgBoxID = msgBoxID
		self.dialog.enableInput = enableInput
		if enableInput:
			self.dialog.createActionMap(-20)
			self.dialog["actions"].execBegin()
		self.dialog.closeOnAnyKey = closeOnAnyKey
		self.dialog.timeoutDefault = timeoutDefault
		self.dialog.windowTitle = windowTitle or self.dialog.TYPE_PREFIX.get(type, _("Message"))
		self.dialog.baseTitle = self.dialog.windowTitle
		self.dialog.activeTitle = self.dialog.windowTitle
		self.dialog.reloadLayout()
		self.dialog.close = self.close
		self.dialog.show()

	def close(self, *retVal):
		if self.callback and callable(self.callback):
			self.callback(*retVal)
		if self.dialog.enableInput:
			self.dialog["actions"].execEnd()
		self.dialog.hide()
