# -*- coding: utf-8 -*-
from enigma import loadPNG, loadJPG, loadSVG, loadGIF, getDesktop, RT_HALIGN_CENTER

# If cached is not supplied, LoadPixmap defaults to caching PNGs and not caching JPGs
# Split alpha channel JPGs are never cached as the C++ layer's caching is based on
# a single file per image in the cache


def LoadPixmap(path, desktop=None, cached=None, width=0, height=0, scaletoFit=0, align=RT_HALIGN_CENTER):
	if path[-4:] == ".png":
		# cache unless caller explicity requests to not cache
		ptr = loadPNG(path, 0, 0 if not cached else 1)
	elif path[-4:] == ".gif":
		# don't cache unless caller explicity requests caching
		ptr = loadGIF(path, 1 if cached else 0)
	elif path[-4:] == ".jpg":
		# don't cache unless caller explicity requests caching
		ptr = loadJPG(path, 1 if cached else 0)
	elif path[-4:] == ".svg":
		scale = getDesktop(0).size().height() / 720.0 if height == 0 else 0
		ptr = loadSVG(path, 0 if cached == False else 1, width, height, scale, scaletoFit, align)
	elif path[-1:] == ".":
		# caching mechanism isn't suitable for multi file images, so it's explicitly disabled
		alpha = loadPNG(path + "a.png", 0, 0)
		ptr = loadJPG(path + "rgb.jpg", alpha, 0)
	else:
		raise Exception(_("Neither .png nor .jpg nor .svg nor .gif!"))
	if ptr and desktop:
		desktop.makeCompatiblePixmap(ptr)
	return ptr
