# -*- coding: utf-8 -*-
from Components.VariableText import VariableText
from Components.Renderer.Renderer import Renderer

from enigma import eLabel


class Label(VariableText, Renderer):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	GUI_WIDGET = eLabel

	def connect(self, source):
		if source:
			Renderer.connect(self, source)
			self.changed((self.CHANGED_DEFAULT,))
		else:
			print("SKINERROR: render label has no source")

	def changed(self, what):
		source = self.source
		if what[0] == self.CHANGED_CLEAR:
			self.text = ""
		elif source:
			try:
				text = source.text
			except AttributeError:
				pass
			else:
				if source is self.source:  # Ignore updates from a disconnected or replaced source.
					self.text = text
		else:
			self.text = "<No Source>"
			print("SKINERROR: render label has no source")
