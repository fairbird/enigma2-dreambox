# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap, MultiPixmap
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from enigma import eTimer, eSize


class MessageBox(Screen):
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

	def __init__(self, session, text, type=TYPE_YESNO, timeout=-1, close_on_any_key=False, default=True, enable_input=True, enableInput=True, msgBoxID=None, picon=None, simple=False, list=[], timeout_default=None, windowTitle=None, skinName=None, skin_name=None, title=None, showYESNO=False, closeOnAnyKey=False, typeIcon=None, timeoutDefault=None):
		self.type = type
		Screen.__init__(self, session)

		self.msgBoxID = msgBoxID

		self["text"] = Label(text)
		self["Text"] = StaticText(text)
		self["selectedChoice"] = StaticText()

		self["key_help"] = StaticText(_("HELP"))

		self.text = text
		self.close_on_any_key = close_on_any_key
		self.timeout_default = timeout_default

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
			if list:
				self.list = list
			elif default:
				self.list = [(_("yes"), True), (_("no"), False)]
			else:
				self.list = [(_("no"), False), (_("yes"), True)]
		else:
			self.list = []

		self["list"] = MenuList(self.list)
		if self.list:
			self["selectedChoice"].setText(self.list[0][0])
		else:
			self["list"].hide()
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
				"ok": self.ok,
				"alwaysOK": self.alwaysOK,
				"up": self.up,
				"down": self.down,
				"left": self.left,
				"right": self.right,
				"upRepeated": self.up,
				"downRepeated": self.down,
				"leftRepeated": self.left,
				"rightRepeated": self.right
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
		if self.timeout_default is not None:
			self.close(self.timeout_default)
		else:
			self.ok()

	def cancel(self):
		self.close(False)

	def ok(self):
		if self.list:
			self.close(self["list"].getCurrent()[1])
		else:
			self.close(True)

	def alwaysOK(self):
		self.close(True)

	def up(self):
		self.move(self["list"].instance.moveUp)

	def down(self):
		self.move(self["list"].instance.moveDown)

	def left(self):
		self.move(self["list"].instance.pageUp)

	def right(self):
		self.move(self["list"].instance.pageDown)

	def move(self, direction):
		if self.close_on_any_key:
			self.close(True)
		self["list"].instance.moveSelection(direction)
		if self.list:
			self["selectedChoice"].setText(self["list"].getCurrent()[0])
		self.stopTimer()

	def __repr__(self):
		return "%s(%s)" % (str(type(self)), self.text if hasattr(self, "text") else "<title>")

	def getListWidth(self):
		return self["list"].instance.getMaxItemTextWidth()

	def reloadLayout(self):
		for method in self.onLayoutFinish:
			if not isinstance(method, type(self.close)):
				exec(method, globals(), locals())
			else:
				method()
		self.layoutFinished()


class ModalMessageBox:
	instance = None

	def __init__(self, session):
		if ModalMessageBox.instance:
			print("[ModalMessageBox] Error: Only one ModalMessageBox instance is allowed!")
		else:
			ModalMessageBox.instance = self
			self.dialog = session.instantiateDialog(MessageBox, "", enableInput=False, skinName="MessageBoxModal")
			self.dialog.setAnimationMode(0)

	def showMessageBox(self, text=None, timeout=-1, list=None, default=True, closeOnAnyKey=False, timeoutDefault=None, windowTitle=None, msgBoxID=None, typeIcon=MessageBox.TYPE_YESNO, enableInput=True, callback=None):
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
