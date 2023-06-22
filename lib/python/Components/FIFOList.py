# -*- coding: utf-8 -*-
from Components.MenuList import MenuList


class FIFOList(MenuList):
	def __init__(self, len=10):
		self.len = len
		self.menuList = []
		MenuList.__init__(self, self.menuList)

	def addItem(self, item):
		self.menuList.append(item)
		self.l.setList(self.menuList[-self.len:])

	def clear(self):
		del self.menuList[:]
		self.l.setList(self.menuList)

	def getCurrentSelection(self):
		return self.menuList and self.getCurrent() or None

	def listAll(self):
		self.l.setList(self.menuList)
		self.selectionEnabled(True)
