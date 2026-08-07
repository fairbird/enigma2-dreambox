#================ MenuGrid_PageInfo =============
# ============================================================================
# This file was created by italia2012.
# Everyone can modify and use it ,
# but don't tell it's yours, or your idea!
# =================================================================

from Components.Converter.Converter import Converter
from Components.Element import cached

from Components.Renderer.MenuGrid import MenuGrid


class MenuGrid_PageInfo(Converter, object):
	def __init__(self, args):
		Converter.__init__(self, args)
		self.templateStr = "# / #"
		if args:
			self.templateStr = args

	def selChanged(self):
		self.downstream_elements.changed((self.CHANGED_ALL, 0))

	@cached
	def getText(self):
		ret = self.templateStr
		try:
			ret = ret.replace("#", str(MenuGrid.sGridActPage), 1)
			ret = ret.replace("#", str(MenuGrid.sGridPageCount), 1)
		except:
			pass
		return ret

	text = property(getText)

	def changed(self, what):
		if what[0] == self.CHANGED_DEFAULT:
			self.source.onSelectionChanged.append(self.selChanged)
		Converter.changed(self, what)

# =========================================================
