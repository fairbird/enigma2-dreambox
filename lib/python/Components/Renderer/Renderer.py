# -*- coding: utf-8 -*-
from Components.GUIComponent import GUIComponent
from Components.Element import Element


class Renderer(GUIComponent, Element):
	def __init__(self):
		Element.__init__(self)
		GUIComponent.__init__(self)

	def onShow(self):
		self.updateAnimationPolicy()
		self.suspended = False

	def updateAnimationPolicy(self):
		if self.instance is not None:
			self.instance.setDefaultAnimationEnabled(bool(self.source and self.source.isAnimated))
		Element.updateAnimationPolicy(self)

	def onHide(self):
		self.suspended = True
