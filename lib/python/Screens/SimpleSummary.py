# -*- coding: utf-8 -*-
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen


class SimpleSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="56,46" size="82,18" font="Regular;16">
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
		<widget source="Title" render="Label" position="6,4" size="120,42" font="Regular;18" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["Title"] = StaticText(parent.getTitle())
		names = parent.skinName
		if not isinstance(names, list):
			names = [names]
		self.skinName = ["%s_summary" % x for x in names]
		self.skinName.append("SimpleSummary")
		# If parent has a "skin_summary" defined, use that as default.
		self.skin = parent.__dict__.get("skin_summary", self.skin)
