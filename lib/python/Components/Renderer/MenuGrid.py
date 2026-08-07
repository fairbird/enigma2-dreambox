# -*- coding: utf-8 -*-
# ============================================================================
# This file was created by italia2012. 
# Everyone can modify and use it ,
# but don't tell it's yours, or your idea!		

#================ MenuGrid (eListbox-based Wall replacement) =============


from Components.Renderer.Renderer import Renderer
from Components.ActionMap import ActionMap
from Components.config import config
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from enigma import eListbox, eListboxPythonMultiContent, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, BT_SCALE, BT_KEEP_ASPECT_RATIO, BT_HALIGN_CENTER, BT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap

from Components.Converter.MenuGrid_MenuIcon import getMenuIcon

from skin import parseColor, parseFont
from Screens.Menu import Menu
import skin
import types
import math


class MenuGrid(Renderer, object):
	sGridPageCount = 1  # static PageCount (يقرأها: MenuGrid_PageInfo)
	sGridActPage = 1    # static ActPage  (يقرأها: MenuGrid_PageInfo)

	def __init__(self):
		Renderer.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.gridBuildFunc)

		self.listLength = 0
		self.gridCols = 6           # يتحسب تلقائي في applySkin حسب عرض الشاشة
		self.gridOffsetX = 0        # هامش توسيط الشبكة أفقيًا، يتحسب في applySkin
		self.gridInstance = None

		self.textColor = "#a0b0c0"
		self.textColorSel = "#a0b0c0"
		self.textOrientation = RT_HALIGN_CENTER | RT_VALIGN_TOP | RT_WRAP

		self.itemWidth = 0
		self.itemHeight = 0
		self.itemSpace = 0

		self.itemBgPixmap = None      # خلفية المربع العادي (backgroundPixmap)
		self.itemSelPixmap = None     # خلفية المربع المحدد (selImages)

		self.flatList = []      # كل عناصر المنيو (مسطّحة، بدون تقسيم صفوف)
		self.rowList = []       # نفس العناصر مقسّمة كل gridCols في RowEntry
		self.currentIndex = 0
		self.currentRow = 0
		self.currentCol = 0

	GUI_WIDGET = eListbox

	def applySkin(self, desktop, parent):

		parent['MoveActions'] = ActionMap(['WizardActions'], {'left': self.gridMoveLeft, 'right': self.gridMoveRight, 'up': self.gridMoveUp, 'down': self.gridMoveDown}, -1)

		showOnlyText = "Screens.Menu" not in str(parent)

		itSpace = 0
		itWidth = 0
		itHeight = 0
		itScale = 100
		bdWidth = 0
		waWidth = 0
		iconPos = [0, 0, 100, 100]
		iconPosSel = [0, 0, 100, 100]
		textPos = [0, 0, 100, 100]
		selImages = []
		wallMode = ""
		bgPixmapPath = None
		attribs = []

		for (attrib, value) in self.skinAttributes:
			if attrib == 'font':
				self.l.setFont(0, parseFont(value, ((1, 1), (1, 1))))
				self.l.setFont(1, parseFont(value, ((1, 1), (1, 1))))
			elif attrib == "itemSpace":
				itSpace = int(value)
			elif attrib == "itemScale":
				itScale = int(value)
			elif attrib == "textColor":
				self.textColor = value
			elif attrib == "textColorSel":
				self.textColorSel = value
			elif attrib == "iconPos":
				iconPos = value.split(',')
			elif attrib == "iconPosSel":
				iconPosSel = value.split(',')
			elif attrib == "textPos":
				textPos = value.split(',')
			elif attrib == "selImages":
				selImages = value.split(',')
			elif attrib == "wallMode":
				wallMode = value
			elif attrib == "backgroundPixmap":
				bgPixmapPath = value          # ده شكل المربع نفسه، مش خلفية الشاشة كلها
			elif attrib == "backgroundColor":
				pass  # منمنعها عشان الفيديو يظهر بين المربعات بدل خلفية سودة معتمة
			elif attrib == "backgroundColorSelected":
				pass  # مستبدلة بصورة selImages
			elif attrib == "borderWidth":
				bdWidth = int(value)
			elif attrib == "itemWidth":
				itWidth = int(value)
			elif attrib == "itemHeight":
				itHeight = int(value)
			elif attrib == "size":
				waWidth = int(value.split(',')[0])
				attribs.append((attrib, value))  # لازم توصل فعليًا لـ eListbox
			else:
				attribs.append((attrib, value))

		# تحميل صورة خلفية المربع العادي
		if bgPixmapPath:
			try:
				self.itemBgPixmap = LoadPixmap(cached=True, path=bgPixmapPath)
			except Exception:
				self.itemBgPixmap = None

		# تحميل صورة خلفية المربع المحدد (نفس منطق eWall: اختيار لون حسب skin.parameters)
		self.itemSelPixmap = None
		if len(selImages) > 0:
			try:
				if wallMode != "Big":
					imgIndex = skin.parameters.get("MenuWall_SelImgIndex", (0,))[0]
				else:
					imgIndex = skin.parameters.get("MenuWall_Big_SelImgIndex", (0,))[0]
				if imgIndex < len(selImages):
					self.itemSelPixmap = LoadPixmap(cached=True, path=selImages[imgIndex])
			except Exception:
				self.itemSelPixmap = None
		if self.itemSelPixmap is None and self.itemBgPixmap is not None:
			self.itemSelPixmap = self.itemBgPixmap  # فallback: نفس خلفية المربع العادي

		self.iconX = int(iconPos[0]); self.iconY = int(iconPos[1])
		self.iconW = int(iconPos[2]); self.iconH = int(iconPos[3])

		self.iconXSel = int(iconPosSel[0]); self.iconYSel = int(iconPosSel[1])
		self.iconWSel = int(iconPosSel[2]); self.iconHSel = int(iconPosSel[3])

		self.textX = int(textPos[0]); self.textY = int(textPos[1])
		self.textW = int(textPos[2]); self.textH = int(textPos[3])

		if showOnlyText:
			self.iconW = self.iconH = self.iconWSel = self.iconHSel = 0
			self.textX, self.textY, self.textW, self.textH = 10, 10, 80, 80
			self.textOrientation = RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP

		self.itemWidth = itWidth
		self.itemHeight = itHeight
		self.itemSpace = itSpace

		# نفس معادلة حساب عدد الأعمدة من نسخة eWall الأصلية
		if itWidth != 0:
			scaleSpace = int(((itWidth * itScale) / 100) - itWidth)
			self.gridCols = max(1, (waWidth - 2 * bdWidth - scaleSpace) // (itWidth + itSpace))

		# توسيط الشبكة كلها أفقيًا: بنحسب المساحة اللي هتاخدها كل أعمدة الصف
		# ونوزع الفرق بينها وبين عرض الويدجت كهامش يمين وشمال متساوي
		totalGridWidth = (self.gridCols * self.itemWidth) + ((self.gridCols - 1) * self.itemSpace)
		self.gridOffsetX = max(0, (waWidth - totalGridWidth) // 2)

		# لو الـ widget اتعمل بالفعل (postWidgetCreate سبق applySkin) لازم نظبطله الارتفاع دلوقتي بعد ما اتحسب صح
		if self.gridInstance is not None:
			self.gridInstance.setItemHeight(self.itemHeight + self.itemSpace)
			self.gridInstance.invalidate()
			self.updatePageInfo()

		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		if (what[0] == self.CHANGED_DEFAULT or what[0] == self.CHANGED_ALL or what[0] == self.CHANGED_CLEAR or what[0] == self.CHANGED_SPECIFIC) and self.source:
			try:
				flatList = []
				for listEntry in self.source.list:
					print("[MenuGrid] DEBUG listEntry = %r" % (listEntry,))
					menuText = str(listEntry[0])
					candidates = [c for c in listEntry[1:] if isinstance(c, str) and c and not c.isdigit()]
					idLikeCandidates = [c for c in candidates if c == c.lower() and ' ' not in c]
					if idLikeCandidates:
						menuEntryID = idLikeCandidates[0]
					elif candidates:
						menuEntryID = candidates[0]
					else:
						menuEntryID = menuText
					flatList.append(GridEntry(menuText, menuEntryID))
				self.flatList = flatList
				self.listLength = len(flatList)

				rows = []
				for i in range(0, self.listLength, self.gridCols):
					rows.append(RowEntry(flatList[i:i + self.gridCols], i // self.gridCols))
				self.rowList = rows

				self.currentIndex = 0
				self.currentRow = 0
				self.currentCol = 0

				self.l.setList([(r,) for r in rows])
				self.updatePageInfo()
			except Exception as e:
				# بدل ما القائمة تفضل فاضية بصمت - نطبعها في اللوج عشان نقدر نشخصها
				print("[MenuGrid] changed() failed: %s" % e)

	# =========== بناء كل صف (Row) في الجدول ===========
	def gridBuildFunc(self, row):
		res = [None]
		for col, entry in enumerate(row.items):
			selected = (row.rowIndex == self.currentRow and col == self.currentCol)
			x0 = self.gridOffsetX + col * (self.itemWidth + self.itemSpace)

			# خلفية المربع نفسه (الشكل الغامق أو التظليل الفيروزي عند التحديد)
			bgPixmap = self.itemSelPixmap if selected else self.itemBgPixmap
			if bgPixmap is not None:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x0, 0), size=(self.itemWidth, self.itemHeight), png=bgPixmap, flags=BT_SCALE))

			# iconPos/textPos جايين كنسبة % من حجم المربع (زي السكين الأصلي) - لازم تتحول لبكسل هنا
			iconXp, iconYp, iconWp, iconHp = (self.iconXSel, self.iconYSel, self.iconWSel, self.iconHSel) if selected else (self.iconX, self.iconY, self.iconW, self.iconH)
			ix = x0 + (self.itemWidth * iconXp) // 100
			iy = (self.itemHeight * iconYp) // 100
			iw = (self.itemWidth * iconWp) // 100
			ih = (self.itemHeight * iconHp) // 100
			if iw > 0 and ih > 0 and entry.menuIcon:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(ix, iy), size=(iw, ih), png=entry.menuIcon, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_CENTER))

			tx = x0 + (self.itemWidth * self.textX) // 100
			ty = (self.itemHeight * self.textY) // 100
			tw = (self.itemWidth * self.textW) // 100
			th = (self.itemHeight * self.textH) // 100
			color = parseColor(self.textColorSel).argb() if selected else parseColor(self.textColor).argb()
			res.append(MultiContentEntryText(pos=(tx, ty), size=(tw, th), font=0, flags=self.textOrientation, text=entry.menuText, color=color, color_sel=color))
		return res

	# =========== KeyActions ===========
	def refreshRow(self, rowIndex):
		if self.gridInstance is None:
			return
		try:
			self.l.invalidateEntry(rowIndex)
		except Exception:
			self.gridInstance.invalidate()
		if self.source:
			self.source.selectionChanged(self.currentIndex)
		self.updatePageInfo()

	def gridMoveRight(self, obj=None):
		if self.listLength <= 0:
			return
		if self.currentCol < self.gridCols - 1 and self.currentIndex + 1 < self.listLength:
			self.currentIndex += 1
			self.currentCol += 1
			self.refreshRow(self.currentRow)

	def gridMoveLeft(self, obj=None):
		if self.currentCol > 0:
			self.currentIndex -= 1
			self.currentCol -= 1
			self.refreshRow(self.currentRow)

	def gridMoveUp(self, obj=None):
		if self.listLength <= 0 or len(self.rowList) <= 1:
			return
		oldRow = self.currentRow
		self.currentRow = len(self.rowList) - 1 if self.currentRow == 0 else self.currentRow - 1
		rowLen = len(self.rowList[self.currentRow].items)
		self.currentCol = min(self.currentCol, rowLen - 1)
		self.currentIndex = self.currentRow * self.gridCols + self.currentCol
		if self.gridInstance:
			self.gridInstance.moveSelectionTo(self.currentRow)
		self.refreshRow(self.currentRow)
		self.refreshRow(oldRow)

	def gridMoveDown(self, obj=None):
		if self.listLength <= 0 or len(self.rowList) <= 1:
			return
		oldRow = self.currentRow
		self.currentRow = 0 if self.currentRow == len(self.rowList) - 1 else self.currentRow + 1
		rowLen = len(self.rowList[self.currentRow].items)
		self.currentCol = min(self.currentCol, rowLen - 1)
		self.currentIndex = self.currentRow * self.gridCols + self.currentCol
		if self.gridInstance:
			self.gridInstance.moveSelectionTo(self.currentRow)
		self.refreshRow(self.currentRow)
		self.refreshRow(oldRow)

	def selectionChanged(self):
		# بيتنادى تلقائيًا لما eListbox يغيّر الصف المحدد (مثلاً pageUp/pageDown)
		if self.gridInstance:
			self.currentRow = self.gridInstance.getCurrentIndex()
			rowLen = len(self.rowList[self.currentRow].items) if self.rowList else 0
			self.currentCol = min(self.currentCol, max(0, rowLen - 1))
			self.currentIndex = self.currentRow * self.gridCols + self.currentCol
		if self.source:
			self.source.selectionChanged(self.currentIndex)
		self.updatePageInfo()

	def updatePageInfo(self):
		if self.gridInstance is None:
			return
		try:
			itemsPerPage = max(1, self.gridInstance.getItemsPerPage())
		except Exception:
			itemsPerPage = 1
		totalRows = len(self.rowList) if self.rowList else 1
		MenuGrid.sGridPageCount = max(1, int(math.ceil(float(totalRows) / itemsPerPage)))
		MenuGrid.sGridActPage = (self.currentRow // itemsPerPage) + 1

	def getIndex(self):
		return self.currentIndex

	def moveToIndex(self, index):
		# اختيار عنصر عن طريق الأرقام
		if self.gridInstance is None or self.listLength <= 0:
			return
		if 0 <= index < self.listLength:
			self.currentIndex = index
			self.currentRow = index // self.gridCols
			self.currentCol = index % self.gridCols
			self.gridInstance.moveSelectionTo(self.currentRow)
			self.gridInstance.invalidate()
			self.updatePageInfo()

	index = property(getIndex, moveToIndex)

	def getCurrent(self):
		if self.source is None or self.currentIndex >= len(self.source.list):
			return
		return self.source.list[self.currentIndex]

	current = property(getCurrent)

	def postWidgetCreate(self, instance):
		self.gridInstance = instance
		self.gridInstance.setContent(self.l)
		try:
			self.gridInstance.setSelectionEnable(0)
		except Exception:
			pass
		self.gridInstance.selectionChanged.get().append(self.selectionChanged)

		if self.source:
			self.source.pageDown = types.MethodType(self.gridMoveRight, self.source)
			self.source.pageUp = types.MethodType(self.gridMoveLeft, self.source)
			self.source.up = types.MethodType(self.gridMoveUp, self.source)
			self.source.down = types.MethodType(self.gridMoveDown, self.source)

		# لو itemHeight اتحسب فعلاً قبل كده (يعني applySkin سبق نفّذ) نطبقه فورًا
		if self.itemHeight or self.itemSpace:
			self.gridInstance.setItemHeight(self.itemHeight + self.itemSpace)

		self.updatePageInfo()

		self.updatePageInfo()


# عناصر منيو بأسماء ID غريبة (فيها مسافات/أقواس) مش صالحة كاسم ملف - بنستبدلها باسم مبسط
MENU_ICON_ALIASES = {
	"Linuxsat-Support.com (Addons Panel)": "linuxsat_panel",
	"oscam/Ncaminfo": "oscam_ncam_info",
}


class GridEntry():
	def __init__(self, menuText, menuEntryID):
		self.menuText = menuText
		menuEntryID = MENU_ICON_ALIASES.get(menuEntryID, menuEntryID)
		try:
			self.menuIcon = getMenuIcon(menuEntryID)
		except Exception as e:
			print("[MenuGrid] getMenuIcon('%s') failed: %s" % (menuEntryID, e))
			self.menuIcon = None


class RowEntry():
	def __init__(self, items, rowIndex):
		self.items = items
		self.rowIndex = rowIndex

# =========================================================
