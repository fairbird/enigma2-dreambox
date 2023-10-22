# -*- coding: utf-8 -*-
from enigma import RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont

from skin import fonts, parameters, parseVerticalAlignment
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


def ChoiceEntryComponent(key=None, text=None):
	verticalAlignment = parseVerticalAlignment(parameters.get("ChoicelistVerticalAlignment", "top")) << 4  # This is a hack until other images fix their code.
	text = ["--"] if text is None else text
	res = [text]
	if text[0] == "--":
		# Get are we want graphical separator (solid line with color) or dashed line
		isUseGraphicalSeparator = parameters.get("ChoicelistUseGraphicalSeparator", 0)
		x, y, w, h = parameters.get("ChoicelistDash", (0, 0, 1280, 25))
		if isUseGraphicalSeparator:
			bk_color = parameters.get("ChoicelistSeparatorColor", "0x00555556")
			res.append(MultiContentEntryText(
						pos=(x, y + 20),
						size=(w, 2),
						font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
						text="",
						color=None, color_sel=None,
						backcolor=bk_color, backcolor_sel=bk_color))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT | verticalAlignment, "\u2014" * 200))
	else:
		if key:
			x, y, w, h = parameters.get("ChoicelistName", (45, 0, 1235, 25))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT | verticalAlignment, text[0]))
			# separate the sizes definition for keybutton is=cons and the rest so there to be possibility to use different size images for different type icons
			iconKeyConfigName = "ChoicelistIcon"
			if key in ("dummy", "none"):
				png = None
			elif key == "expandable":
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/expandable.png"))
			elif key == "expanded":
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/expanded.png"))
			elif key == "verticalline":
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/verticalline.png"))
			elif key == "bullet":
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/bullet.png"))
			else:
				iconKeyConfigName = "ChoicelistButtonIcon"
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "buttons/key_%s.png" % key))
			if png:
				x, y, w, h = parameters.get(iconKeyConfigName, (5, 0, 35, 25))
				if key == "verticalline" and "ChoicelistIconVerticalline" in parameters:
					x, y, w, h = parameters.get("ChoicelistIconVerticalline", (5, 0, 35, 25))
				if key == "expanded" and "ChoicelistIconExpanded" in parameters:
					x, y, w, h = parameters.get("ChoicelistIconExpanded", (5, 0, 35, 25))
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, png))
		else:
			x, y, w, h = parameters.get("ChoicelistNameSingle", (5, 0, 1275, 25))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT | verticalAlignment, text[0]))
	return res


class ChoiceList(MenuList):
	def __init__(self, list, selection=0, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = fonts.get("ChoiceList", ("Regular", 20, 30))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.itemHeight = font[2]
		self.selection = selection

	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		self.moveToIndex(self.selection)

	def getItemHeight(self):
		return self.itemHeight
