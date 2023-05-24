# -*- coding: utf-8 -*-
from enigma import ePixmap

from Components.Renderer.Renderer import Renderer


class Pixmap(Renderer):
	def __init__(self):
		Renderer.__init__(self)

	GUI_WIDGET = ePixmap

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.source and hasattr(self.source, "pixmap") and self.instance:
			if what[0] == self.CHANGED_CLEAR:
				self.instance.setPixmap(None)
			else:
				self.instance.setPixmap(self.source.pixmap)
