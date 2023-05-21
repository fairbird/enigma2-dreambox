# -*- coding: utf-8 -*-
class TestError(Exception):
	def __init__(self, error):
		Exception.__init__(self, error)
