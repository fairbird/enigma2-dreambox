# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel


class TextBox(Screen):
	def __init__(self, session, text="", title=None, pigless=False):
		Screen.__init__(self, session)
		if pigless:
			self.skinName = ["TextBoxPigLess", "TextBox"]
		self.text = text
		self["text"] = ScrollLabel(self.text)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"],
				{
					"cancel": self.close,
					"ok": self.close,
					"up": self["text"].pageUp,
					"down": self["text"].pageDown,
				}, -1)

		if title:
			self.setTitle(title)
