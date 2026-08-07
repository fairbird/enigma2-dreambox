#================ MXGreytransparent_MenuIcon =============
# ============================================================================
# This file was created by italia2012.
# Everyone can modify and use it ,
# but don't tell it's yours, or your idea!
# EDit by RAED
# =================================================================

from Components.Converter.Converter import Converter
from Components.Element import cached
from Tools.LoadPixmap import LoadPixmap
# Add by RAED
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from skin import menus
#


class MenuGrid_MenuIcon(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type

	@cached
	def getPixmap(self):
		png = None
		try:
			#menuEntryID = str(self.source.current[2])
			# Edit by RAED
			curr = self.source.current
			menuEntryID = str(curr[5] if len(curr) > 5 and isinstance(curr[5], str) else curr[2])
			png = getMenuIcon(menuEntryID)
		except:
			pass
		return png

	pixmap = property(getPixmap)

	def selChanged(self):
		self.downstream_elements.changed((self.CHANGED_ALL, 0))

	def changed(self, what):
		if what[0] == self.CHANGED_DEFAULT:
			self.source.onSelectionChanged.append(self.selChanged)
		Converter.changed(self, what)

#getMenuIcon(Rend:MXGreytransparent_MenuWall,Conv:MXGreytransparent_MenuIcon)


def getMenuIcon(menuEntryID):
	png = None
	iconPath = resolveFilename(SCOPE_GUISKIN, "icons_Menu/")
	#iconName = menuEntryID
	# Edit by RAED
	iconName = menuEntryID.replace(" ", "")

	#png = LoadPixmap(cached = True, path = iconPath + iconName + ".png")
	# Edit by RAED
	skinPath = menus.get(iconName)
	if not skinPath:
		clean = lambda s: s.lower().replace(" ", "").replace("_", "").replace("-", "").replace("&", "")
		target = clean(iconName)
		for k, v in menus.items():
			if clean(k) == target:
				skinPath = v
				break
	if skinPath:
		png = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, skinPath))
	if png == None:
		for name in (iconName, iconName.lower(), iconName.replace(" ", ""), iconName.replace(" ", "").lower()):
			png = LoadPixmap(cached=True, path=iconPath + name + ".png")
			if png:
				break
	#
	if png == None:
		png = LoadPixmap(cached=True, path=iconPath + "Undefined.png")
	return png

# =========================================================
