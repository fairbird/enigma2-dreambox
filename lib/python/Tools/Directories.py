# -*- coding: utf-8 -*-
from errno import ENOENT, EXDEV
from os import F_OK, R_OK, W_OK, access, chmod, link, listdir, makedirs, mkdir, readlink, remove, rename, rmdir, sep, stat, statvfs, symlink, utime, walk, popen
from os.path import basename, dirname, exists, getsize, isdir, isfile, islink, join as pathjoin, normpath, splitext
from re import compile
from stat import S_IMODE
from shutil import copy2
from traceback import print_exc
from sys import _getframe as getframe
from unicodedata import normalize
from tempfile import mkstemp
from xml.etree.cElementTree import Element, ParseError, fromstring, parse

from enigma import eEnv, getDesktop, eGetEnigmaDebugLvl

DEFAULT_MODULE_NAME = __name__.split(".")[-1]

forceDebug = eGetEnigmaDebugLvl() > 4
pathExists = exists

SCOPE_HOME = 0  # DEBUG: Not currently used in Enigma2.
SCOPE_TRANSPONDERDATA = 1
SCOPE_SYSETC = 2
SCOPE_FONTS = 3
SCOPE_CONFIG = 4
SCOPE_LANGUAGE = 5
SCOPE_HDD = 6
SCOPE_PLUGINS = 7
SCOPE_PLUGIN = 8
SCOPE_MEDIA = 9
SCOPE_SKINS = 10
SCOPE_GUISKIN = 11
SCOPE_PLAYLIST = 12
SCOPE_CURRENT_PLUGIN_ABSOLUTE = 13
SCOPE_CURRENT_PLUGIN_RELATIVE = 14
SCOPE_KEYMAPS = 15
SCOPE_METADIR = 16
SCOPE_TIMESHIFT = 17
SCOPE_LCDSKIN = 18
SCOPE_AUTORECORD = 19
SCOPE_DEFAULTDIR = 20
SCOPE_DEFAULTPARTITION = 21
SCOPE_DEFAULTPARTITIONMOUNTDIR = 22
SCOPE_LIBDIR = 23

# Deprecated scopes:
SCOPE_ACTIVE_LCDSKIN = SCOPE_LCDSKIN
SCOPE_ACTIVE_SKIN = SCOPE_GUISKIN
SCOPE_CURRENT_LCDSKIN = SCOPE_LCDSKIN
SCOPE_CURRENT_PLUGIN = SCOPE_PLUGIN
SCOPE_CURRENT_SKIN = SCOPE_GUISKIN
SCOPE_SKIN = SCOPE_SKINS
SCOPE_SKIN_IMAGE = SCOPE_SKINS
SCOPE_USERETC = SCOPE_HOME
SCOPE_PLUGIN_ABSOLUTE = SCOPE_CURRENT_PLUGIN_ABSOLUTE
SCOPE_PLUGIN_RELATIVE = SCOPE_CURRENT_PLUGIN_RELATIVE

PATH_CREATE = 0
PATH_DONTCREATE = 1

defaultPaths = {
	SCOPE_HOME: ("", PATH_DONTCREATE),  # User home directory
	SCOPE_TRANSPONDERDATA: (eEnv.resolve("${sysconfdir}/"), PATH_DONTCREATE),
	SCOPE_SYSETC: (eEnv.resolve("${sysconfdir}/"), PATH_DONTCREATE),
	SCOPE_FONTS: (eEnv.resolve("${datadir}/fonts/"), PATH_DONTCREATE),
	SCOPE_CONFIG: (eEnv.resolve("${sysconfdir}/enigma2/"), PATH_CREATE),
	SCOPE_LANGUAGE: (eEnv.resolve("${datadir}/enigma2/po/"), PATH_DONTCREATE),
	SCOPE_HDD: ("/media/hdd/movie/", PATH_DONTCREATE),
	SCOPE_PLUGINS: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_CREATE),
	SCOPE_PLUGIN: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_CREATE),
	SCOPE_MEDIA: ("/media/", PATH_DONTCREATE),
	SCOPE_SKINS: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
	SCOPE_GUISKIN: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
	SCOPE_PLAYLIST: (eEnv.resolve("${sysconfdir}/enigma2/playlist/"), PATH_CREATE),
	SCOPE_CURRENT_PLUGIN_ABSOLUTE: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_DONTCREATE),
	SCOPE_CURRENT_PLUGIN_RELATIVE: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_DONTCREATE),
	SCOPE_KEYMAPS: (eEnv.resolve("${datadir}/keymaps/"), PATH_CREATE),
	SCOPE_METADIR: (eEnv.resolve("${datadir}/meta"), PATH_CREATE),
	SCOPE_TIMESHIFT: ("/media/hdd/timeshift/", PATH_DONTCREATE),
	SCOPE_LCDSKIN: (eEnv.resolve("${datadir}/enigma2/display/"), PATH_DONTCREATE),
	SCOPE_AUTORECORD: ("/media/hdd/movie/", PATH_DONTCREATE),
	SCOPE_DEFAULTDIR: (eEnv.resolve("${datadir}/enigma2/defaults/"), PATH_CREATE),
	SCOPE_DEFAULTPARTITION: ("/dev/mtdblock6", PATH_DONTCREATE),
	SCOPE_DEFAULTPARTITIONMOUNTDIR: (eEnv.resolve("${datadir}/enigma2/dealer"), PATH_CREATE),
	SCOPE_LIBDIR: (eEnv.resolve("${libdir}/"), PATH_DONTCREATE)
}

scopeConfig = defaultPaths[SCOPE_CONFIG][0]
scopeGUISkin = defaultPaths[SCOPE_GUISKIN][0]
scopeLCDSkin = defaultPaths[SCOPE_LCDSKIN][0]
scopeFonts = defaultPaths[SCOPE_FONTS][0]
scopePlugins = defaultPaths[SCOPE_PLUGINS][0]


def InitDefaultPaths():
	resolveFilename(SCOPE_CONFIG)


def resolveFilename(scope, base="", path_prefix=None):
	if str(base).startswith("~%s" % sep):  # You can only use the ~/ if we have a prefix directory.
		if path_prefix:
			base = pathjoin(path_prefix, base[2:])
		else:
			print("[Directories] Warning: resolveFilename called with base starting with '~%s' but 'path_prefix' is None!" % sep)
	if str(base).startswith(sep):  # Don't further resolve absolute paths.
		return normpath(base)
	if scope not in defaultPaths:  # If an invalid scope is specified log an error and return None.
		print("[Directories] Error: Invalid scope=%s provided to resolveFilename!" % scope)
		return None
	path, flag = defaultPaths[scope]  # Ensure that the defaultPath directory that should exist for this scope does exist.
	if flag == PATH_CREATE and not pathExists(path):
		try:
			makedirs(path)
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Couldn't create directory '%s'!  (%s)" % (err.errno, path, err.strerror))
			return None
	suffix = None  # Remove any suffix data and restore it at the end.
	data = base.split(":", 1)
	if len(data) > 1:
		base = data[0]
		suffix = data[1]
	path = base

	def itemExists(resolveList, base):
		# Disable png / svg interchange code for now.  SVG files are very CPU intensive.
		# baseList = [base]
		# if base.endswith(".png"):
		# 	baseList.append("%s%s" % (base[:-3], "svg"))
		# elif base.endswith(".svg"):
		# 	baseList.append("%s%s" % (base[:-3], "png"))
		for item in resolveList:
			# for base in baseList:
			file = pathjoin(item, base)
			if pathExists(file):
				return file
		return base

	if base == "":  # If base is "" then set path to the scope.  Otherwise use the scope to resolve the base filename.
		path, flags = defaultPaths.get(scope)
		if scope == SCOPE_GUISKIN:  # If the scope is SCOPE_GUISKIN append the current skin to the scope path.
			from Components.config import config  # This import must be here as this module finds the config file as part of the config initialization.
			skin = dirname(config.skin.primary_skin.value)
			path = pathjoin(path, skin)
		elif scope in (SCOPE_PLUGIN_ABSOLUTE, SCOPE_PLUGIN_RELATIVE):
			callingCode = normpath(getframe(1).f_code.co_filename)
			plugins = normpath(scopePlugins)
			path = None
			if comparePaths(plugins, callingCode):
				pluginCode = callingCode[len(plugins) + 1:].split(sep)
				if len(pluginCode) > 2:
					relative = "%s%s%s" % (pluginCode[0], sep, pluginCode[1])
					path = pathjoin(plugins, relative)
	elif scope == SCOPE_GUISKIN:
		from Components.config import config  # This import must be here as this module finds the config file as part of the config initialization.
		skin = dirname(config.skin.primary_skin.value)
		resolveList = [
			pathjoin(scopeConfig, skin),
			pathjoin(scopeConfig, "skin_common"),
			scopeConfig,  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
			pathjoin(scopeGUISkin, skin),
			pathjoin(scopeGUISkin, "skin_fallback_%d" % getDesktop(0).size().height()),
			pathjoin(scopeGUISkin, "skin_default"),
			scopeGUISkin  # Can we deprecate top level of SCOPE_GUISKIN directory to allow a clean up?
		]
		path = itemExists(resolveList, base)
	elif scope == SCOPE_LCDSKIN:
		from Components.config import config  # This import must be here as this module finds the config file as part of the config initialization.
		skin = dirname(config.skin.display_skin.value) if hasattr(config.skin, "display_skin") else ""
		resolveList = [
			pathjoin(scopeConfig, "display", skin),
			pathjoin(scopeConfig, "display", "skin_common"),
			scopeConfig,  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
			pathjoin(scopeLCDSkin, skin),
			pathjoin(scopeLCDSkin, "skin_fallback_%s" % getDesktop(1).size().height()),
			pathjoin(scopeLCDSkin, "skin_default"),
			scopeLCDSkin  # Can we deprecate top level of SCOPE_LCDSKIN directory to allow a clean up?
		]
		path = itemExists(resolveList, base)
	elif scope == SCOPE_FONTS:
		from Components.config import config  # This import must be here as this module finds the config file as part of the config initialization.
		skin = dirname(config.skin.primary_skin.value)
		display = dirname(config.skin.display_skin.value) if hasattr(config.skin, "display_skin") else None
		resolveList = [
			pathjoin(scopeConfig, "fonts"),
			pathjoin(scopeConfig, skin, "fonts"),
			pathjoin(scopeConfig, skin)
		]
		if display:
			resolveList.append(pathjoin(scopeConfig, "display", display, "fonts"))
			resolveList.append(pathjoin(scopeConfig, "display", display))
		resolveList.append(pathjoin(scopeConfig, "skin_common", "fonts"))
		resolveList.append(pathjoin(scopeConfig, "skin_common"))
		resolveList.append(scopeConfig)  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
		resolveList.append(pathjoin(scopeGUISkin, skin, "fonts"))
		resolveList.append(pathjoin(scopeGUISkin, skin))
		resolveList.append(pathjoin(scopeGUISkin, "skin_default", "fonts"))
		resolveList.append(pathjoin(scopeGUISkin, "skin_default"))
		if display:
			resolveList.append(pathjoin(scopeLCDSkin, display, "fonts"))
			resolveList.append(pathjoin(scopeLCDSkin, display))
		resolveList.append(pathjoin(scopeLCDSkin, "skin_default", "fonts"))
		resolveList.append(pathjoin(scopeLCDSkin, "skin_default"))
		resolveList.append(scopeFonts)
		path = itemExists(resolveList, base)
	elif scope == SCOPE_PLUGIN:
		file = pathjoin(scopePlugins, base)
		if pathExists(file):
			path = file
	elif scope in (SCOPE_PLUGIN_ABSOLUTE, SCOPE_PLUGIN_RELATIVE):
		callingCode = normpath(getframe(1).f_code.co_filename)
		plugins = normpath(scopePlugins)
		path = None
		if comparePaths(plugins, callingCode):
			pluginCode = callingCode[len(plugins) + 1:].split(sep)
			if len(pluginCode) > 2:
				relative = pathjoin("%s%s%s" % (pluginCode[0], sep, pluginCode[1]), base)
				path = pathjoin(plugins, relative)
	else:
		path, flags = defaultPaths.get(scope)
		path = pathjoin(path, base)
	path = normpath(path)
	if isdir(path) and not path.endswith(sep):  # If the path is a directory then ensure that it ends with a "/".
		path = "%s%s" % (path, sep)
	if scope == SCOPE_PLUGIN_RELATIVE:
		path = path[len(plugins) + 1:]
	if suffix is not None:  # If a suffix was supplier restore it.
		path = "%s:%s" % (path, suffix)
	return path


def fileReadLine(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	line = None
	try:
		with open(filename, "r") as fd:
			line = fd.read().strip().replace("\0", "")
		msg = "Read"
	except (IOError, OSError) as err:
		if err.errno != ENOENT:  # ENOENT - No such file or directory.
			print("[%s] Error %d: Unable to read a line from file '%s'!  (%s)" % (source, err.errno, filename, err.strerror))
		line = default
		msg = "Default"
	if debug or forceDebug:
		print("[%s] Line %d: %s '%s' from file '%s'." % (source, getframe(1).f_lineno, msg, line, filename))
	return line


def fileWriteLine(filename, line, source=DEFAULT_MODULE_NAME, debug=False):
	try:
		with open(filename, "w") as fd:
			fd.write(str(line))
		msg = "Wrote"
		result = 1
	except (IOError, OSError) as err:
		print("[%s] Error %d: Unable to write a line to file '%s'!  (%s)" % (source, err.errno, filename, err.strerror))
		msg = "Failed to write"
		result = 0
	if debug or forceDebug:
		print("[%s] Line %d: %s '%s' to file '%s'." % (source, getframe(1).f_lineno, msg, line, filename))
	return result


def fileUpdateLine(filename, conditionValue, replacementValue, create=False, source=DEFAULT_MODULE_NAME, debug=False):
	line = fileReadLine(filename, default="", source=source, debug=debug)
	create = False if conditionValue and not line.startswith(conditionValue) else create
	return fileWriteLine(filename, replacementValue, source=source, debug=debug) if create or (conditionValue and line.startswith(conditionValue)) else 0


def fileReadLines(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	lines = None
	try:
		with open(filename, "r") as fd:
			lines = fd.read().splitlines()
		msg = "Read"
	except (IOError, OSError, UnicodeDecodeError) as err:
		print("UnicodeDecodeError: %s %s" % (err, filename))
		if not UnicodeDecodeError and err.errno != ENOENT:  # ENOENT - No such file or directory.
			print("[%s] Error %d: Unable to read lines from file '%s'!  (%s)" % (source, err.errno, filename, err.strerror))
		lines = default
		msg = "Default"
	if debug or forceDebug:
		length = len(lines) if lines else 0
		print("[%s] Line %d: %s %d lines from file '%s'." % (source, getframe(1).f_lineno, msg, length, filename))
	return lines


def fileReadLinesISO(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	lines = None
	try:
		with open(filename, "r", encoding="ISO 8859-1") as fd:
			lines = fd.read().splitlines()
		msg = "Read"
	except (IOError, OSError, UnicodeDecodeError) as err:
		if not UnicodeDecodeError and err.errno != ENOENT:  # ENOENT - No such file or directory.
			print("[%s] Error %d: Unable to read lines from file '%s'!  (%s)" % (source, err.errno, filename, err.strerror))
		lines = default
		msg = "Default"
	if debug or forceDebug:
		length = len(lines) if lines else 0
		print("[%s] Line %d: %s %d lines from file '%s'." % (source, getframe(1).f_lineno, msg, length, filename))
	return lines


def fileWriteLines(filename, lines, source=DEFAULT_MODULE_NAME, debug=False):
	try:
		with open(filename, "w") as fd:
			if isinstance(lines, list):
				lines.append("")
				lines = "\n".join(lines)
			fd.write(lines)
		msg = "Wrote"
		result = 1
	except (IOError, OSError) as err:
		print("[%s] Error %d: Unable to write %d lines to file '%s'!  (%s)" % (source, err.errno, len(lines), filename, err.strerror))
		msg = "Failed to write"
		result = 0
	if debug or forceDebug:
		print("[%s] Line %d: %s %d lines to file '%s'." % (source, getframe(1).f_lineno, msg, len(lines), filename))
	return result


def fileReadXML(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	dom = None
	try:
		with open(filename, "r", encoding="UTF-8") as fd:  # This open gets around a possible file handle leak in Python's XML parser.
			try:
				dom = parse(fd).getroot()
				msg = "Read"
			except ParseError as err:
				fd.seek(0)
				content = fd.readlines()
				line, column = err.position
				print("[%s] XML Parse Error: '%s' in '%s'!" % (source, err, filename))
				data = content[line - 1].replace("\t", " ").rstrip()
				print("[%s] XML Parse Error: '%s'" % (source, data))
				print("[%s] XML Parse Error: '%s^%s'" % (source, "-" * column, " " * (len(data) - column - 1)))
			except Exception as err:
				print("[%s] Error: Unable to parse data in '%s' - '%s'!" % (source, filename, err))
	except (IOError, OSError) as err:
		if err.errno == ENOENT:  # ENOENT - No such file or directory.
			print("[%s] Warning: File '%s' does not exist!" % (source, filename))
		else:
			print("[%s] Error %d: Opening file '%s'!  (%s)" % (source, err.errno, filename, err.strerror))
	except Exception as err:
		print("[%s] Error: Unexpected error opening/parsing file '%s'!  (%s)" % (source, filename, err))
		print_exc()
	if dom is None:
		if default and isinstance(default, str):
			dom = fromstring(default)
			msg = "Default (XML)"
		elif default and isinstance(default, type(Element(None))):  # This handles a bug in Python 2 where the Element object is *not* a class type in cElementTree!!!
			dom = default
			msg = "Default (DOM)"
		else:
			msg = "Failed to read"
	if debug or forceDebug:
		length = len(dom) if dom else 0
		print("[%s] %s Lines=%d from XML '%s'." % (source, msg, length, filename))
	return dom


def defaultRecordingLocation(candidate=None):
	if candidate and pathExists(candidate):
		return candidate
	try:
		path = readlink("/hdd")  # First, try whatever /hdd points to, or /media/hdd.
	except (IOError, OSError) as err:
		path = "/media/hdd"
	if not pathExists(path):  # Find the largest local disk.
		from Components import Harddisk
		mounts = [mount for mount in Harddisk.getProcMounts() if mount[1].startswith("/media/")]
		path = bestRecordingLocation([mount for mount in mounts if mount[0].startswith("/dev/")])  # Search local devices first, use the larger one.
		if not path:  # If we haven't found a viable candidate yet, try remote mounts.
			path = bestRecordingLocation([mount for mount in mounts if not mount[0].startswith("/dev/")])
	if path:
		movie = pathjoin(path, "movie", "")  # If there's a movie subdir, we'd probably want to use that (directories need to end in sep).
		if isdir(movie):
			path = movie
	return path


def bestRecordingLocation(candidates):
	path = ""
	biggest = 0
	for candidate in candidates:
		try:
			status = statvfs(candidate[1])  # Must have some free space (i.e. not read-only).
			if status.f_bavail:
				size = (status.f_blocks + status.f_bavail) * status.f_bsize  # Free space counts double.
				if size > biggest:
					biggest = size
					path = candidate[1]
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Couldn't get free space for '%s'!  (%s)" % (err.errno, candidate[1], err.strerror))
	return path


def getRecordingFilename(basename, dirname=None):
	nonAllowedCharacters = "/.\\:*?<>|\""  # Filter out non-allowed characters.
	basename = basename.replace("\x86", "").replace("\x87", "")
	filename = ""
	for character in basename:
		if character in nonAllowedCharacters or ord(character) < 32:
			character = "_"
		filename += character
	# Max filename length for ext4 is 255 (minus 8 characters for .ts.meta)
	# but must not truncate in the middle of a multi-byte utf8 character!
	# So convert the truncation to unicode and back, ignoring errors, the
	# result will be valid utf8 and so xml parsing will be OK.
	filename = ilename[:247]
	if dirname is None:
		dirname = defaultRecordingLocation()
	else:
		if not dirname.startswith(sep):
			dirname = pathjoin(defaultRecordingLocation(), dirname)
	filename = pathjoin(dirname, filename)
	next = 0
	path = filename
	while isfile("%s.ts" % path):
		next += 1
		path = "%s_%03d" % (filename, next)
	return path


def copyFile(src, dst):
	try:
		copy2(src, dst)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Copying file '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
		return -1
	return 0
	# if isdir(dst):
	# 	dst = pathjoin(dst, basename(src))
	# try:
	# 	with open(src, "rb") as fd1:
	# 		with open(dst, "w+b") as fd2:
	# 			while True:
	# 				buf = fd1.read(16 * 1024)
	# 				if not buf:
	# 					break
	# 				fd2.write(buf)
	# 	try:
	# 		status = stat(src)
	# 		try:
	# 			chmod(dst, S_IMODE(status.st_mode))
	# 		except (IOError, OSError) as err:
	# 			print("[Directories] Error %d: Setting modes from '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
	# 		try:
	# 			utime(dst, (status.st_atime, status.st_mtime))
	# 		except (IOError, OSError) as err:
	# 			print("[Directories] Error %d: Setting times from '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
	# 	except (IOError, OSError) as err:
	# 		print("[Directories] Error %d: Obtaining status from '%s'!  (%s)" % (err.errno, src, err.strerror))
	# except (IOError, OSError) as err:
	# 	print("[Directories] Error %d: Copying file '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
	# 	return -1
	# return 0


def copyfile(src, dst):
	return copyFile(src, dst)


def copyTree(src, dst, symlinks=False):
	names = listdir(src)
	if isdir(dst):
		dst = pathjoin(dst, basename(src))
		if not isdir(dst):
			mkdir(dst)
	else:
		makedirs(dst)
	for name in names:
		srcName = pathjoin(src, name)
		dstName = pathjoin(dst, name)
		try:
			if symlinks and islink(srcName):
				linkTo = readlink(srcName)
				symlink(linkTo, dstName)
			elif isdir(srcName):
				copytree(srcName, dstName, symlinks)
			else:
				copyfile(srcName, dstName)
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Copying tree '%s' to '%s'!  (%s)" % (err.errno, srcName, dstName, err.strerror))
	try:
		status = stat(src)
		try:
			chmod(dst, S_IMODE(status.st_mode))
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Setting modes from '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
		try:
			utime(dst, (status.st_atime, status.st_mtime))
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Setting times from '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Obtaining stats from '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))


def copytree(src, dst, symlinks=False):
	return copyTree(src, dst, symlinks=symlinks)


# Renames files or if source and destination are on different devices moves them in background
# input list of (source, destination)
#
def moveFiles(fileList):
	errorFlag = False
	movedList = []
	try:
		for item in fileList:
			rename(item[0], item[1])
			movedList.append(item)
	except (IOError, OSError) as err:
		if err.errno == EXDEV:  # EXDEV - Invalid cross-device link.
			print("[Directories] Warning: Cannot rename across devices, trying slower move.")
			from Tools.CopyFiles import moveFiles as extMoveFiles
			extMoveFiles(fileList, item[0])
			print("[Directories] Moving files in background.")
		else:
			print("[Directories] Error %d: Moving file '%s' to '%s'!  (%s)" % (err.errno, item[0], item[1], err.strerror))
			errorFlag = True
	if errorFlag:
		print("[Directories] Reversing renamed files due to error.")
		for item in movedList:
			try:
				rename(item[1], item[0])
			except (IOError, OSError) as err:
				print("[Directories] Error %d: Renaming '%s' to '%s'!  (%s)" % (err.errno, item[1], item[0], err.strerror))
				print("[Directories] Note: Failed to undo move of '%s' to '%s'!" % (item[0], item[1]))


def comparePaths(leftPath, rightPath):
	print("[Directories] comparePaths DEBUG: left='%s', right='%s'." % (leftPath, rightPath))
	if leftPath.endswith(sep):
		leftPath = leftPath[:-1]
	left = leftPath.split(sep)
	right = rightPath.split(sep)
	for index, segment in enumerate(left):
		if left[index] != right[index]:
			return False
	return True


def comparePaths(leftPath, rightPath):
	print("[Directories] comparePaths DEBUG: left='%s', right='%s'." % (leftPath, rightPath))
	if leftPath.endswith(sep):
		leftPath = leftPath[:-1]
	left = leftPath.split(sep)
	right = rightPath.split(sep)
	for index, segment in enumerate(left):
		if left[index] != right[index]:
			return False
	return True


# Returns a list of tuples containing pathname and filename matching the given pattern
# Example-pattern: match all txt-files: ".*\.txt$"
#
def crawlDirectory(directory, pattern):
	fileList = []
	if directory:
		expression = compile(pattern)
		for root, dirs, files in walk(directory):
			for file in files:
				if expression.match(file) is not None:
					fileList.append((root, file))
	return fileList


def createDir(path, makeParents=False):
	try:
		if makeParents:
			makedirs(path)
		else:
			mkdir(path)
		return 1
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Couldn't create directory '%s'!  (%s)" % (err.errno, path, err.strerror))
	return 0


def renameDir(oldPath, newPath):
	try:
		rename(oldPath, newPath)
		return 1
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Couldn't rename directory '%s' to '%s'!  (%s)" % (err.errno, oldPath, newPath, err.strerror))
	return 0


def removeDir(path):
	try:
		rmdir(path)
		return 1
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Couldn't remove directory '%s'!  (%s)" % (err.errno, path, err.strerror))
	return 0


def fileAccess(file, mode="r"):
	accMode = F_OK
	if "r" in mode:
		accMode |= R_OK
	if "w" in mode:
		accMode |= W_OK
	result = False
	try:
		result = access(file, accMode)
	except (IOError, OSError, UnicodeEncodeError) as err:
		print("[Directories] Error %d: Couldn't determine file '%s' access mode!  (%s)" % (err.errno, file, err.strerror))
	return result


def fileCheck(file, mode="r"):
	return fileAccess(file, mode) and file


def fileExists(file, mode="r"):
	return fileAccess(file, mode) and file


def fileContains(file, content, mode="r"):
	result = False
	if fileExists(file, mode):
		with open(file, mode) as fd:
			text = fd.read()
		if content in text:
			result = True
	return result


def fileHas(file, content, mode="r"):
	return fileContains(file, content, mode)


def hasHardLinks(path):  # Test if the volume containing path supports hard links.
	try:
		fd, srcName = mkstemp(prefix="HardLink_", suffix=".test", dir=path, text=False)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Creating temp file!  (%s)" % (err.errno, err.strerror))
		return False
	dstName = "%s.link" % splitext(srcName)[0]
	try:
		link(srcName, dstName)
		result = True
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Creating hard link!  (%s)" % (err.errno, err.strerror))
		result = False
	try:
		remove(srcName)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Removing source file!  (%s)" % (err.errno, err.strerror))
	try:
		remove(dstName)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Removing destination file!  (%s)" % (err.errno, err.strerror))
	return result


def getSize(path, pattern=".*"):
	pathSize = 0
	if isdir(path):
		for file in crawlDirectory(path, pattern):
			pathSize += getsize(pathjoin(file[0], file[1]))
	elif isfile(path):
		pathSize = getsize(path)
	return pathSize


# Prepare filenames for use in external shell processing. Filenames may
# contain spaces or other special characters.  This method adjusts the
# filename to be a safe and single entity for passing to a shell.
#
def shellQuote(string):
	return "'%s'" % string.replace("'", "'\\''")


def shellquote(string):
	return shellQuote(string)


def lsof():  # List of open files.
	lsof = []
	for pid in listdir("/proc"):
		if pid.isdigit():
			try:
				prog = readlink(pathjoin("/proc", pid, "exe"))
				dir = pathjoin("/proc", pid, "fd")
				for file in [pathjoin(dir, file) for file in listdir(dir)]:
					lsof.append((pid, prog, readlink(file)))
			except (IOError, OSError) as err:
				pass
	return lsof


def getExtension(file):
	filename, extension = splitext(file)
	return extension


def mediaFilesInUse(session):
	from Components.MovieList import KNOWN_EXTENSIONS
	TRANSMISSION_PART = fileExists("/usr/bin/transmission-daemon") and popen("pidof transmission-daemon").read() and ".part" or "N/A"
	files = [basename(x[2]) for x in lsof() if getExtension(x[2]) in (KNOWN_EXTENSIONS, TRANSMISSION_PART)]
	service = session.nav.getCurrentlyPlayingServiceOrGroup()
	filename = service and service.getPath()
	if filename:
		filename = None if "://" in filename else basename(filename)  # When path is a stream ignore it.
	return set([file for file in files if not (filename and file == filename and files.count(filename) < 2)])


def isPluginInstalled(pluginName, pluginFile="plugin", pluginType=None):
	types = ["Extensions", "SystemPlugins"]
	if pluginType:
		types = [pluginType]
	if PY2:
		extensions = ["o", ""]
	else:
		extensions = ["c", ""]
	for type in types:
		for extension in extensions:
			if isfile(pathjoin(scopePlugins, type, pluginName, "%s.py%s" % (pluginFile, extension))):
				return True
	return False


def InitFallbackFiles():
	resolveFilename(SCOPE_CONFIG, "userbouquet.favourites.tv")
	resolveFilename(SCOPE_CONFIG, "bouquets.tv")
	resolveFilename(SCOPE_CONFIG, "userbouquet.favourites.radio")
	resolveFilename(SCOPE_CONFIG, "bouquets.radio")

# Returns a list of tuples containing pathname and filename matching the given pattern
# Example-pattern: match all txt-files: ".*\.txt$"
#

def sanitizeFilename(filename):
	"""Return a fairly safe version of the filename.
	We don't limit ourselves to ascii, because we want to keep municipality
	names, etc, but we do want to get rid of anything potentially harmful,
	and make sure we do not exceed Windows filename length limits.
	Hence a less safe blacklist, rather than a whitelist.
	"""
	blacklist = ["\\", "/", ":", "*", "?", "\"", "<", ">", "|", "\0", "(", ")", " "]
	reserved = [
		"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
		"COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
		"LPT6", "LPT7", "LPT8", "LPT9",
	]  # Reserved words on Windows
	filename = "".pathjoin(c for c in filename if c not in blacklist)
	# Remove all charcters below code point 32
	filename = "".pathjoin(c for c in filename if 31 < ord(c))
	filename = normalize("NFKD", filename)
	filename = filename.rstrip(". ")  # Windows does not allow these at end
	filename = filename.strip()
	if all([x == "." for x in filename]):
		filename = "__" + filename
	if filename in reserved:
		filename = "__" + filename
	if len(filename) == 0:
		filename = "__"
	if len(filename) > 255:
		parts = split(r"/|\\", filename)[-1].split(".")
		if len(parts) > 1:
			ext = "." + parts.pop()
			filename = filename[:-len(ext)]
		else:
			ext = ""
		if filename == "":
			filename = "__"
		if len(ext) > 254:
			ext = ext[254:]
		maxl = 255 - len(ext)
		filename = filename[:maxl]
		filename = filename + ext
		# Re-check last character (if there was no extension)
		filename = filename.rstrip(". ")
		if len(filename) == 0:
			filename = "__"
	return filename
