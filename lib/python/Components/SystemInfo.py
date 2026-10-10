# -*- coding: utf-8 -*-
from ast import literal_eval
from binascii import hexlify
from hashlib import md5
from locale import format_string
from os import R_OK, access, listdir, readlink, stat
from os.path import exists as fileAccess, isdir, isfile, join
from re import findall
from platform import libc_ver
from re import search
from sys import version as pyversion
from time import localtime, strftime

from enigma import eAVControl, Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl, eDVBCSAEngine
from Tools.Directories import SCOPE_PLUGINS, SCOPE_LIBDIR, SCOPE_SKIN, fileCheck, fileReadLine, fileReadLines, resolveFilename, fileExists, fileHas, fileReadLine, pathExists
from Tools.MultiBoot import MultiBoot

MODULE_NAME = __name__.split(".")[-1]
DEGREE = "\u00B0"


class BoxInformation:  # To maintain data integrity class variables should not be accessed from outside of this class!
	def __init__(self):
		self.immutableList = []
		self.boxInfo = {}
		self.enigmaInfoList = []
		self.enigmaConfList = []
		lines = fileReadLines(join(resolveFilename(SCOPE_LIBDIR), "enigma.info"), source=MODULE_NAME)
		if lines:
			modified = self.checkChecksum(lines)
			if modified:
				print("[SystemInfo] WARNING: Enigma information file checksum is incorrect!  File appears to have been modified.")
				self.boxInfo["checksumerror"] = True
			else:
				print("[SystemInfo] Enigma information file checksum is correct.")
				self.boxInfo["checksumerror"] = False
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = (x.strip() for x in line.split("=", 1))
					if item:
						self.immutableList.append(item)
						self.enigmaInfoList.append(item)
						try:
							self.boxInfo[item] = literal_eval(value)
						except Exception:  # Remove this code when the build system is updated.
							self.boxInfo[item] = value
						# except Exception as err:  # Activate this replacement code when the build system is updated.
						# 	print(f"[SystemInfo] Error: Information variable '{item}' with a value of '{value}' can not be loaded into BoxInfo!  ({err})")
			self.enigmaInfoList = sorted(self.enigmaInfoList)
			print("[SystemInfo] Enigma information file data loaded into BoxInfo.")
		else:
			print("[SystemInfo] ERROR: Enigma information file is not available!  The system is unlikely to boot or operate correctly.")
		filename = isfile(resolveFilename(SCOPE_LIBDIR, "enigma.conf"))
		if filename:
			lines = fileReadLines(join(resolveFilename(SCOPE_LIBDIR), "enigma.conf"), source=MODULE_NAME)
			print("[SystemInfo] Enigma config override file available and data loaded into BoxInfo.")
			self.boxInfo["overrideactive"] = True
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = (x.strip() for x in line.split("=", 1))
					if item:
						self.enigmaConfList.append(item)
						if item in self.boxInfo:
							print(f"[SystemInfo] Note: Enigma information value '{item}' with value '{self.boxInfo[item]}' being overridden to '{value}'.")
						try:
							self.boxInfo[item] = literal_eval(value)
						except Exception:  # Remove this code when the build system is updated.
							self.boxInfo[item] = value
						# except Exception as err:  # Activate this replacement code when the build system is updated.
						# 	print(f"[SystemInfo] Error: Information override variable '{item}' with a value of '{value}' can not be loaded into BoxInfo!  ({err})")
			self.enigmaConfList = sorted(self.enigmaConfList)
		else:
			self.boxInfo["overrideactive"] = False

	def checkChecksum(self, lines):
		value = "Undefined!"
		data = []
		for line in lines:
			if line.startswith("checksum"):
				item, value = (x.strip() for x in line.split("=", 1))
			else:
				data.append(line)
		data.append("")
		result = md5(bytearray("\n".join(data), "UTF-8", errors="ignore")).hexdigest()  # NOSONAR
		return value != result

	def getEnigmaInfoList(self):
		return self.enigmaInfoList

	def getEnigmaConfList(self):
		return self.enigmaConfList

	def getItemsList(self):
		return sorted(list(self.boxInfo.keys()))

	def getItem(self, item, default=None):
		return self.boxInfo.get(item, default)

	def setItem(self, item, value, immutable=False):
		if item in self.immutableList:
			print(f"[BoxInfo] Error: Item '{item}' is immutable and can not be {'changed' if item in self.boxInfo else 'added'}!")
			return False
		if immutable:
			self.immutableList.append(item)
		self.boxInfo[item] = value
		return True

	def setMutableItem(self, item, value):
		self.boxInfo[item] = value

	def deleteItem(self, item):
		if item in self.immutableList:
			print(f"[BoxInfo] Error: Item '{item}' is immutable and can not be deleted!")
		elif item in self.boxInfo:
			del self.boxInfo[item]
			return True
		return False


# Hardware related functions

	def getCPUSerial(self):
		result = _("Undefined")
		for line in fileReadLines("/proc/cpuinfo", default=[], source=MODULE_NAME):
			if line[0:6] == "Serial":
				result = line[10:26]
				break
		return result

	def getCPUSpeedMhz(self):
		result = 0
		model = self.getItem("model")
		if model in ("hzero", "h8", "sfx6008", "sfx6018"):
			result = 1200
		elif model in ("dreamone", "dreamtwo", "dreamseven"):
			result = 1800
		elif model in ("vuduo4k",):
			result = 2100
		return result

	def getCPUInfoString(self):
		cpuCount = 0
		cpuSpeedStr = "-"
		cpuSpeedMhz = self.getCPUSpeedMhz()
		processor = ""
		for line in fileReadLines("/proc/cpuinfo", default=[], source=MODULE_NAME):
			line = [x.strip() for x in line.strip().split(":", 1)]
			if not processor and line[0] in ("system type", "model name", "Processor"):
				processor = line[1].split()[0]
			elif not cpuSpeedMhz and line[0] == "cpu MHz":
				cpuSpeedMhz = float(line[1])
			elif line[0] == "processor":
				cpuCount += 1
		if not cpuCount:
			cpuCount = len(glob("/sys/devices/system/cpu/cpu[0-9]*"))
		if not cpuCount:
			cpuCount = 1
		if processor.startswith("ARM") and isfile("/proc/stb/info/chipset"):
			processor = f"{fileReadLine("/proc/stb/info/chipset", default="", source=MODULE_NAME).upper()} ({processor})"
		if not cpuSpeedMhz:
			cpuSpeed = fileReadLine("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq", default="", source=MODULE_NAME)
			if cpuSpeed:
				cpuSpeedMhz = int(cpuSpeed) / 1000
			else:
				try:
					cpuSpeedMhz = int(int(hexlify(open("/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency", "rb").read()), 16) / 100000000) * 100
				except Exception:
					cpuSpeedMhz = 1500
		temperature = None
		if isfile("/proc/stb/fp/temp_sensor_avs"):
			temperature = fileReadLine("/proc/stb/fp/temp_sensor_avs", default=None, source=MODULE_NAME)
		elif isfile("/proc/stb/power/avs"):
			temperature = fileReadLine("/proc/stb/power/avs", default=None, source=MODULE_NAME)
		elif isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
			temperature = fileReadLine("/sys/devices/virtual/thermal/thermal_zone0/temp", default=None, source=MODULE_NAME)
			if temperature:
				temperature = int(temperature) / 1000
		elif isfile("/sys/class/thermal/thermal_zone0/temp"):
			temperature = fileReadLine("/sys/class/thermal/thermal_zone0/temp", default=None, source=MODULE_NAME)
			if temperature:
				temperature = int(temperature) / 1000
		elif isfile("/proc/hisi/msp/pm_cpu"):
			for line in fileReadLines("/proc/hisi/msp/pm_cpu", default=[], source=MODULE_NAME):
				if "temperature = " in line:
					temperature = int(line.split("temperature = ")[1].split()[0])
					# break  # Without this break the code returns the last line containing the string!
		cpuSpeedStr = _("%s GHz") % format_string("%.1f", cpuSpeedMhz / 1000) if cpuSpeedMhz and cpuSpeedMhz >= 1000 else _("%d MHz") % int(cpuSpeedMhz)
		if temperature:
			temperature = f"{format_string("%.1f", temperature) if isinstance(temperature, float) else temperature}{DEGREE}C"
		return (processor, cpuSpeedStr, ngettext("%d core", "%d cores", cpuCount) % cpuCount, temperature or "")

	def getSystemTemperature(self):
		if isfile("/proc/stb/sensors/temp0/value"):
			temperature = fileReadLine("/proc/stb/sensors/temp0/value", default=None, source=MODULE_NAME)
		elif isfile("/proc/stb/sensors/temp/value"):
			temperature = fileReadLine("/proc/stb/sensors/temp/value", default=None, source=MODULE_NAME)
		elif isfile("/proc/stb/fp/temp_sensor"):
			temperature = fileReadLine("/proc/stb/fp/temp_sensor", default=None, source=MODULE_NAME)
		else:
			temperature = None
		return f"{temperature}{DEGREE}C" if temperature else ""

	def getRAMTemperature(self):
		result = ""
		for zone in glob("/sys/class/thermal/thermal_zone*"):
			if fileReadLine(f"{zone}/type", default="", source=MODULE_NAME) == "ddr_thermal":
				temperature = fileReadLine(f"{zone}/temp", default="", source=MODULE_NAME)
				if temperature.lstrip("-").isdigit():
					result = f"{format_string("%.1f", int(temperature) / 1000)}{DEGREE}C"
					break
		return result

	def getCPUCurrentSpeed(self):
		speeds = []
		for policy in sorted(glob("/sys/devices/system/cpu/cpufreq/policy*")):
			khz = fileReadLine(f"{policy}/scaling_cur_freq", default="", source=MODULE_NAME)
			if khz.isdigit():
				speeds.append(int(khz) / 1000)  # MHz, one entry per cluster
		result = ""
		if speeds:
			if max(speeds) >= 1000:
				result = _("%s GHz") % " / ".join(format_string("%.1f", x / 1000) for x in speeds)
			else:
				result = _("%s MHz") % " / ".join(str(int(x)) for x in speeds)
			for device in glob("/sys/class/thermal/cooling_device*"):
				if fileReadLine(f"{device}/type", default="", source=MODULE_NAME).startswith("thermal-cpufreq"):
					state = fileReadLine(f"{device}/cur_state", default="0", source=MODULE_NAME)
					if state.isdigit() and int(state) > 0:
						result = f"{result} ({_("throttled")})"
						break
		return result

	def getCPUBrand(self):
		socFamily = self.getItem("socfamily")
		if self.getItem("AmlogicFamily"):
			result = _("Amlogic")
		elif self.getItem("HiSilicon"):
			result = _("HiSilicon")
		elif socFamily.startswith("smp"):
			result = _("Sigma Designs")
		elif socFamily.startswith("bcm") or self.getItem("brand") == "rpi":
			result = _("Broadcom")
		else:
			print("[BoxInfo] Error: No CPU brand!")
			result = _("Undefined")
		return result

	def getCPUArch(self):
		if self.getItem("ArchIsARM64"):
			result = _("ARM64")
		elif self.getItem("ArchIsARM"):
			result = _("ARM")
		else:
			result = _("Mipsel")
		return result

	def getFlashType(self):
		if self.getItem("SmallFlash"):
			result = _("Small - Tiny image")
		elif self.getItem("MiddleFlash"):
			result = _("Middle - Lite image")
		else:
			result = _("Normal - Standard image")
		return result

	def getDriverInstalledDate(self):
		result = None
		for template in ("/var/lib/opkg/info/*dvb-modules*.control", "/var/lib/opkg/info/*dvb-proxy*.control", "/var/lib/opkg/info/*platform-util*.control"):
			fileNames = glob(template)
			if fileNames:
				for line in fileReadLines(fileNames[0], default=[], source=MODULE_NAME):
					if line[0:8] == "Version:":
						value = line[8:].strip()
						match = search(r"\d{8}", value)
						result = match[0] if match else value
						break
			if result:
				break
		return result if result else _("Unknown")

	def getBoxUptime(self):
		upTime = fileReadLine("/proc/uptime", default=None, source=MODULE_NAME)
		if upTime:
			seconds = int(upTime.split(".")[0])
			times = []
			if seconds > 86400:
				days = seconds // 86400
				seconds = seconds % 86400
				times.append(ngettext("%d Day", "%d Days", days) % days)
			hours = seconds // 3600
			minutes = (seconds % 3600) // 60
			times.append(ngettext("%d Hour", "%d Hours", hours) % hours)
			times.append(ngettext("%d Minute", "%d Minutes", minutes) % minutes)
			result = " ".join(times)
		else:
			result = "-"
		return result

	def getKernelVersionString(self):
		version = fileReadLine("/proc/version", default="", source=MODULE_NAME)
		return version.split(" ", 4)[2].split("-", 2)[0] if version else _("Unknown")

	def getFlashDateString(self):
		try:
			localTime = localtime(stat("/home").st_ctime)
			result = strftime(_("%Y-%m-%d"), localTime) if localTime.tm_year >= 2011 else _("Unknown")
		except Exception:
			result = _("Unknown")
		return result

	def getGlibcVersion(self):
		try:
			result = libc_ver()[1]
		except Exception:
			print("[BoxInfo] Error: Get glibc version failed!")
			result = _("Unknown")
		return result

	def getGccVersion(self):
		try:
			result = pyversion.split("[GCC ")[1].replace("]", "")
		except Exception:
			print("[BoxInfo] Error: Get gcc version failed!")
			result = _("Unknown")
		return result

	def getPythonVersionString(self):
		try:
			result = pyversion.split(" ")[0]
		except Exception:
			result = _("Unknown")
		return result

	def getImageVersionString(self):
		return str(self.getItem("imageversion"))

	def getBuildDateString(self):
		version = fileReadLine("/etc/version", default="", source=MODULE_NAME)
		return f"{version[:4]}-{version[4:6]}-{version[6:8]}" if version else _("Unknown")

	def getUpdateDateString(self):
		build = self.getItem("compiledate")
		return f"{build[:4]}-{build[4:6]}-{build[6:]}" if build and build.isdigit() else _("Unknown")

	def getVersionFromOpkg(self, fileName):
		return next((line[9:].split("+")[0] for line in fileReadLines(f"/var/lib/opkg/info/{fileName}.control", default=[], source=MODULE_NAME) if line.startswith("Version:")), _("Not Installed"))


BoxInfo = BoxInformation()


class SystemInformation(dict):
	def __getitem__(self, item):
		return BoxInfo.boxInfo[item]

	def __setitem__(self, item, value):
		if item in BoxInfo.immutableList:
			print(f"[SystemInfo] Error: Item '{item}' is immutable and can not be {'changed' if item in BoxInfo.boxInfo else 'added'}!")
		else:
			BoxInfo.boxInfo[item] = value

	def __delitem__(self, item):
		if item in BoxInfo.immutableList:
			print(f"[SystemInfo] Error: Item '{item}' is immutable and can not be deleted!")
		else:
			del BoxInfo.boxInfo[item]

	def get(self, item, default=None):
		return BoxInfo.boxInfo[item] if item in BoxInfo.boxInfo else default


SystemInfo = SystemInformation()

ARCHITECTURE = BoxInfo.getItem("architecture")
BRAND = BoxInfo.getItem("brand")
MODEL = BoxInfo.getItem("model")
SOC_FAMILY = BoxInfo.getItem("socfamily")
DISPLAYTYPE = BoxInfo.getItem("displaytype")
MTDROOTFS = BoxInfo.getItem("mtdrootfs")
DISPLAYMODEL = BoxInfo.getItem("displaymodel")
DISPLAYBRAND = BoxInfo.getItem("displaybrand")
MACHINEBUILD = MODEL


# Parse the boot commandline.
#
cmdline = fileReadLine("/proc/cmdline", source=MODULE_NAME)
cmdline = {k: v.strip('"') for k, v in findall(r'(\S+)=(".*?"|\S+)', cmdline)}


def getBoxDisplayName():  # This function returns a tuple like ("BRANDNAME", "BOXNAME")
	return (DISPLAYBRAND, DISPLAYMODEL)


def getDemodVersion():
	version = None
	if fileExists("/proc/stb/info/nim_firmware_version"):
		version = fileReadLine("/proc/stb/info/nim_firmware_version")
	return version and version.strip()


def getNumVideoDecoders():
	numVideoDecoders = 0
	while fileExists(f"/dev/dvb/adapter0/video{numVideoDecoders}", "f"):
		numVideoDecoders += 1
	return numVideoDecoders


def countFrontpanelLEDs():
	numLeds = fileExists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while fileExists(f"/proc/stb/fp/led{numLeds}_pattern"):
		numLeds += 1
	return numLeds


def hassoftcaminstalled():
	from Tools.camcontrol import CamControl
	return len(CamControl("softcam").getList()) > 1


def getBootdevice():
	dev = ("root" in cmdline and cmdline["root"].startswith("/dev/")) and cmdline["root"][5:]
	while dev and not fileExists("/sys/block/%s" % dev):
		dev = dev[:-1]
	return dev


def getRCFile(ext):
	filename = resolveFilename(SCOPE_SKIN, join("rc_models", f"{BoxInfo.getItem('rcname')}.{ext}"))
	if not isfile(filename):
		filename = resolveFilename(SCOPE_SKIN, join("rc_models", f"dmm1.{ext}"))
	return filename


def getChipSetString():
	if MODEL in ('dm7080', 'dm820'):
		return "7435"
	elif MODEL in ('dm520', 'dm525'):
		return "73625"
	elif MODEL in ('dm900', 'dm920', 'et13000', 'sf5008'):
		return "7252S"
	elif MODEL in ('hd51', 'vs1500', 'h7'):
		return "7251S"
	elif MODEL in ('alien5',):
		return "S905D"
	else:
		chipset = fileReadLine("/proc/stb/info/chipset", source=MODULE_NAME)
		if chipset is None:
			return _("Undefined")
		return str(chipset.lower().replace('\n', '').replace('bcm', '').replace('brcm', '').replace('sti', ''))


def hasInitCam():
	result = False
	for cam in listdir("/etc/init.d"):
		if cam.startswith("softcam.") and not cam.endswith("None"):
			result = True
			break
	return result


def getBoxName():
	box = MACHINEBUILD
	machinename = DISPLAYMODEL.lower()
	if box in ("uniboxhd1", "uniboxhd2", "uniboxhd3"):
		box = "ventonhdx"
	elif box == "odinm6":
		box = machinename
	elif box == "inihde" and machinename == "hd-1000":
		box = "sezam-1000hd"
	elif box == "ventonhdx" and machinename == "hd-5000":
		box = "sezam-5000hd"
	elif box == "ventonhdx" and machinename == "premium twin":
		box = "miraclebox-twin"
	elif box == "xp1000" and machinename == "sf8 hd":
		box = "sf8"
	elif box.startswith("et") and box not in ("et8000", "et8500", "et8500s", "et10000"):
		box = f"{box[0:3]}x00"
	elif box == "odinm9":
		box = "maram9"
	elif box.startswith("sf8008m"):
		box = "sf8008m"
	elif box.startswith("sf8008"):
		box = "sf8008"
	elif box.startswith("ustym4kpro"):
		box = "ustym4kpro"
	elif box.startswith("twinboxlcdci"):
		box = "twinboxlcd"
	elif box == "sfx6018":
		box = "sfx6008"
	elif box == "sx888":
		box = "sx88v2"
	return box


BoxInfo.setItem("DebugLevel", eGetEnigmaDebugLvl())
BoxInfo.setItem("InDebugMode", eGetEnigmaDebugLvl() >= 4)

BoxInfo.setItem("BoxName", getBoxName())
BoxInfo.setItem("RCImage", getRCFile("png"))
BoxInfo.setItem("RCMapping", getRCFile("xml"))

BoxInfo.setItem("canMultiBoot", MultiBoot.getBootSlots())
BoxInfo.setItem("HasNewNativeMultiboot", fileExists("/.newMB"))
BoxInfo.setItem("HasKexecMultiboot", fileHas("/proc/cmdline", "kexec=1"))
BoxInfo.setItem("cankexec", BoxInfo.getItem("kexecmb") and fileExists("/usr/bin/kernel_auto.bin") and fileExists("/usr/bin/STARTUP.cpio.gz") and not BoxInfo.getItem("HasKexecMultiboot"))
BoxInfo.setItem("HasChkrootMultiboot", (MultiBoot.isFat32("/dev/block/by-name/others") or fileExists("/dev/block/by-name/startup")) and MODEL not in ("dreamone", "dreamtwo"))
BoxInfo.setItem("canchkroot", (BoxInfo.getItem("hasUBIMB") or fileExists("/dev/block/by-name/others")) and not BoxInfo.getItem("HasChkrootMultiboot") and not fileExists("/etc/.disableChkroot"))
BoxInfo.setItem("HasSDmmc", MultiBoot.canMultiBoot() and "sd" in MultiBoot.getBootSlots().get("2", "") and "mmcblk" in MTDROOTFS)
BoxInfo.setItem("HasSoftcamInstalled", hassoftcaminstalled())
BoxInfo.setItem("NumVideoDecoders", getNumVideoDecoders())
BoxInfo.setItem("PIPAvailable", BoxInfo.getItem("NumVideoDecoders") > 1)
BoxInfo.setItem("CanMeasureFrontendInputPower", eDVBResourceManager.getInstance().canMeasureFrontendInputPower())
BoxInfo.setItem("12V_Output", Misc_Options.getInstance().detected_12V_output())
BoxInfo.setItem("ZapMode", fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode"))
BoxInfo.setItem("NumFrontpanelLEDs", countFrontpanelLEDs())
BoxInfo.setItem("FrontpanelDisplay", fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0"))
BoxInfo.setItem("LCDsymbol_circle_recording", fileCheck("/proc/stb/lcd/symbol_circle") or MODEL in ("hd51", "vs1500") and fileCheck("/proc/stb/lcd/symbol_recording"))
BoxInfo.setItem("LCDsymbol_timeshift", fileCheck("/proc/stb/lcd/symbol_timeshift"))
BoxInfo.setItem("LCDshow_symbols", (MODEL.startswith("et9") or MODEL in ("hd51", "vs1500")) and fileCheck("/proc/stb/lcd/show_symbols"))
BoxInfo.setItem("LCDsymbol_hdd", MODEL in ("hd51", "vs1500") and fileCheck("/proc/stb/lcd/symbol_hdd"))
BoxInfo.setItem("FrontpanelDisplayGrayscale", fileExists("/dev/dbox/oled0"))
BoxInfo.setItem("CanUse3DModeChoices", fileExists("/proc/stb/fb/3dmode_choices") and True or False)
BoxInfo.setItem("DeepstandbySupport", MODEL != "dm800")
BoxInfo.setItem("OLDE2API", MODEL in ("dm800"))
BoxInfo.setItem("Fan", fileCheck("/proc/stb/fp/fan"))
BoxInfo.setItem("FanPWM", BoxInfo.getItem("Fan") and fileCheck("/proc/stb/fp/fan_pwm"))
BoxInfo.setItem("PowerLED", fileCheck("/proc/stb/power/powerled") or MODEL in ("gbue4k", "gbquad4k") and fileCheck("/proc/stb/fp/led1_pattern"))
BoxInfo.setItem("StandbyLED", fileCheck("/proc/stb/power/standbyled") or MODEL in ("gbue4k", "gbquad4k") and fileCheck("/proc/stb/fp/led0_pattern"))
BoxInfo.setItem("SuspendLED", fileCheck("/proc/stb/power/suspendled") or fileCheck("/proc/stb/fp/enable_led"))
BoxInfo.setItem("Display", BoxInfo.getItem("FrontpanelDisplay") or BoxInfo.getItem("StandbyLED") or MODEL in ("dreamone", "dreamtwo"))
BoxInfo.setItem("LEDControl", MODEL not in ("dreamone", "dreamtwo"))
BoxInfo.setItem("LEDColorControl", fileExists("/proc/stb/fp/led_color"))
BoxInfo.setItem("LedPowerColor", fileCheck("/proc/stb/fp/ledpowercolor"))
BoxInfo.setItem("LedStandbyColor", fileCheck("/proc/stb/fp/ledstandbycolor"))
BoxInfo.setItem("LedSuspendColor", fileCheck("/proc/stb/fp/ledsuspendledcolor"))
BoxInfo.setItem("Power4x7On", fileCheck("/proc/stb/fp/power4x7on"))
BoxInfo.setItem("Power4x7Standby", fileCheck("/proc/stb/fp/power4x7standby"))
BoxInfo.setItem("Power4x7Suspend", fileCheck("/proc/stb/fp/power4x7suspend"))
BoxInfo.setItem("PowerOffDisplay", MODEL not in "formuler1" and fileCheck("/proc/stb/power/vfd") or fileCheck("/proc/stb/lcd/vfd"))
BoxInfo.setItem("WakeOnLAN", not MODEL.startswith("et8000") and fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol"))
BoxInfo.setItem("HasExternalPIP", not (MODEL.startswith("et9") or MODEL in ("e4hd",)) and fileCheck("/proc/stb/vmpeg/1/external"))
BoxInfo.setItem("VideoDestinationConfigurable", fileExists("/proc/stb/vmpeg/0/dst_left") or fileExists("/sys/class/video/axis"))
BoxInfo.setItem("hasPIPVisibleProc", fileCheck("/proc/stb/vmpeg/1/visible"))
BoxInfo.setItem("MaxPIPSize", MODEL in ("hd51", "h7", "vs1500", "e4hd") and (360, 288) or (540, 432))
BoxInfo.setItem("HasGPT", MODEL in ("dreamone", "dreamtwo") and pathExists("/dev/mmcblk0p7"))
BoxInfo.setItem("VFD_scroll_repeats", not MODEL.startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_repeats"))
BoxInfo.setItem("VFD_scroll_delay", not MODEL.startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_delay"))
BoxInfo.setItem("VFD_initial_scroll_delay", not MODEL.startswith("et8500") and fileCheck("/proc/stb/lcd/initial_scroll_delay"))
BoxInfo.setItem("VFD_final_scroll_delay", not MODEL.startswith("et8500") and fileCheck("/proc/stb/lcd/final_scroll_delay"))
BoxInfo.setItem("LcdLiveTV", fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable"))
BoxInfo.setItem("LcdLiveTVMode", fileCheck("/proc/stb/lcd/mode"))
BoxInfo.setItem("LcdLiveDecoder", fileCheck("/proc/stb/lcd/live_decoder"))
BoxInfo.setItem("LCDMiniTV", fileExists("/proc/stb/lcd/mode"))
BoxInfo.setItem("LCDSKIN", fileExists("/usr/share/enigma2/display"))
BoxInfo.setItem("ConfigDisplay", BoxInfo.getItem("FrontpanelDisplay"))
BoxInfo.setItem("DefaultDisplayBrightness", MACHINEBUILD in ("dm900", "dm920", "dreamone", "dreamtwo") and 8 or 5)
BoxInfo.setItem("3DMode", fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d"))
BoxInfo.setItem("3DZNorm", fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset"))
BoxInfo.setItem("HasQuadpip", fileCheck("/proc/stb/video/decodermode"))
BoxInfo.setItem("Blindscan_t2_available", fileCheck("/proc/stb/info/vumodel") and MODEL.startswith("vu"))
BoxInfo.setItem("RcTypeChangable", not (MODEL in ("gbquad4k", "gbue4k", "et8500") or MODEL.startswith("et7")) and pathExists("/proc/stb/ir/rc/type"))
BoxInfo.setItem("HasFullHDSkinSupport", MODEL not in ("et4000", "et5000", "sh1", "hd500c", "hd1100", "xp1000", "lc"))
BoxInfo.setItem("HasMMC", "root" in cmdline and cmdline["root"].startswith("/dev/mmcblk"))
BoxInfo.setItem("HasTranscoding", pathExists("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0"))
BoxInfo.setItem("HasH265Encoder", fileHas("/proc/stb/encoder/0/vcodec_choices", "h265"))
BoxInfo.setItem("CanNotDoSimultaneousTranscodeAndPIP", MODEL in ("vusolo4k", "gbquad4k", "gbue4k"))
BoxInfo.setItem("canRecovery", MODEL in ("hd51", "vs1500", "h7", "8100s") and ("disk.img", "mmcblk0p1") or MODEL in ("xc7439", "osmio4k", "osmio4kplus", "osmini4k") and ("emmc.img", "mmcblk1p1") or MODEL in ("gbmv200", "sf8008", "sf8008m", "sx988", "ip8", "ustym4kpro", "ustym4kottpremium", "ustym4ks2ottx", "beyonwizv2", "viper4k", "og2ott4k", "og2s4k", "sx88v2", "sx888") and ("usb_update.bin", "none"))
BoxInfo.setItem("HasFrontDisplayPicon", MODEL in ("et8500", "vusolo4k", "vuuno4kse", "vuduo4k", "vuduo4kse", "vuultimo4k", "gbquad4k", "gbue4k"))
BoxInfo.setItem("Has24hz", fileCheck("/proc/stb/video/videomode_24hz"))
BoxInfo.setItem("Has2160p", fileHas("/proc/stb/video/videomode_preferred", "2160p50"))
BoxInfo.setItem("HasHDMIpreemphasis", fileCheck("/proc/stb/hdmi/preemphasis"))
BoxInfo.setItem("HasScaler_sharpness", pathExists("/proc/stb/vmpeg/0/pep_scaler_sharpness"))
BoxInfo.setItem("HasHDMIin", BoxInfo.getItem("hdmifhdin") or BoxInfo.getItem("hdmihdin"))
BoxInfo.setItem("HasHDMIinFHD", MODEL in ("dm900", "dm920", "dreamone", "dreamtwo"))
BoxInfo.setItem("HasHDMIinPiP", BoxInfo.getItem("HasHDMIin") and BRAND != "dreambox")
BoxInfo.setItem("HAVEINITCAM", hasInitCam())
BoxInfo.setItem("HasSoftCSA", eDVBCSAEngine.isAvailable())
BoxInfo.setItem("DreamBoxDVI", MODEL in ("dm8000", "dm800"))
BoxInfo.setItem("VFDSymbol", BoxInfo.getItem("vfdsymbol"))
BoxInfo.setItem("HasHDMI-CEC", BoxInfo.getItem("hdmi") and fileExists("/usr/lib/enigma2/python/Screens/HDMICEC.pyc") and (fileExists("/dev/cec0") or fileExists("/dev/cec") or fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0")))
BoxInfo.setItem("HasYPbPr", MODEL in ("dm8000", "et5000", "et6000", "et6500", "et9000", "et9200", "et9500", "et10000", "formuler1", "mbtwinplus", "spycat", "vusolo", "vuduo", "vuduo2", "vuultimo"))
BoxInfo.setItem("HasScart", MODEL in ("dm8000", "et4000", "et6500", "et8000", "et9000", "et9200", "et9500", "et10000", "formuler1", "hd1100", "hd1200", "hd1265", "hd2400", "vusolo", "vusolo2", "vuduo", "vuduo2", "vuultimo", "vuuno", "xp1000"))
BoxInfo.setItem("HasSVideo", MODEL in ("dm8000"))
BoxInfo.setItem("ArchIsARM64", ARCHITECTURE == "aarch64" or "64" in ARCHITECTURE)
BoxInfo.setItem("ArchIsARM", ARCHITECTURE.startswith(("arm", "cortex")))
BoxInfo.setItem("RecoveryMode", fileCheck("/proc/stb/fp/boot_mode") or MODEL in ("dreamone", "dreamtwo"))
BoxInfo.setItem("AmlogicFamily", SOC_FAMILY.startswith(("aml", "meson")) or fileExists("/proc/device-tree/amlogic-dt-id") or fileExists("/usr/bin/amlhalt") or fileExists("/sys/module/amports"))
BoxInfo.setItem("HasComposite", MODEL not in ("i55", "gbquad4k", "gbue4k", "hd1500", "osnino", "osninoplus", "purehd", "purehdse", "revo4k", "vusolo4k", "vuzero4k", "vuduo4k", "vuduo4kse", "vuuno4k", "vuuno4kse", "vuultimo4k"))
BoxInfo.setItem("hasXcoreVFD", MODEL in ("osmega", "spycat4k", "spycat4kmini", "spycat4kcombo") and fileCheck("/sys/module/brcmstb_%s/parameters/pt6302_cgram" % MODEL))
BoxInfo.setItem("HasOfflineDecoding", MODEL not in ("osmini", "osminiplus", "et7000mini", "et11000", "mbmicro", "mbtwinplus", "mbmicrov2", "et7000", "et8500"))
BoxInfo.setItem("canMode12", "%s_4.boxmode" % MODEL in cmdline and cmdline["%s_4.boxmode" % MODEL] in ("1", "12") and "192M")
BoxInfo.setItem("canDualBoot", fileExists("/dev/block/by-name/flag"))
BoxInfo.setItem("canFlashWithOfgwrite", not (MODEL.startswith("dm")))
BoxInfo.setItem("HasMultichannelPCM", fileCheck("/proc/stb/audio/multichannel_pcm"))
BoxInfo.setItem("HasAutoVolumeLevel", fileExists("/proc/stb/audio/autovolumelevel_choices") and fileCheck("/proc/stb/audio/autovolumelevel"))
BoxInfo.setItem("Has3DSurroundSoftLimiter", fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") and fileCheck("/proc/stb/audio/3dsurround_softlimiter"))
BoxInfo.setItem("HDMIAudioSource", fileCheck("/proc/stb/hdmi/audio_source"))
BoxInfo.setItem("CanAC3Transcode", fileHas("/proc/stb/audio/ac3plus_choices", "force_ac3"))
BoxInfo.setItem("BootDevice", getBootdevice())
BoxInfo.setItem("NimExceptionVuSolo2", MODEL == "vusolo2")
BoxInfo.setItem("NimExceptionVuDuo2", MODEL == "vuduo2")
BoxInfo.setItem("NimExceptionDMM8000", MODEL == "dm8000")
BoxInfo.setItem("FbcTunerPowerAlwaysOn", MODEL in ("vusolo4k", "vuduo4k", "vuduo4kse", "vuultimo4k", "vuuno4k", "vuuno4kse", "dm900", "dm920"))
BoxInfo.setItem("HasPhysicalLoopthrough", ["Vuplus DVB-S NIM(AVL2108)", "GIGA DVB-S2 NIM (Internal)"])
BoxInfo.setItem("CanChangeOsdAlpha", eAVControl.getInstance().hasOSDAlpha())
BoxInfo.setItem("CanChangeOsdPlaneAlpha", access("/sys/class/graphics/fb0/osd_plane_alpha", R_OK) and True or False)
BoxInfo.setItem("CanChangeOsdPositionAML", access("/sys/class/graphics/fb0/free_scale", R_OK) and True or False)
if MODEL in ("et7500", "et8500"):
	BoxInfo.setItem("HasPhysicalLoopthrough", BoxInfo.getItem("HasPhysicalLoopthrough") + ["AVL6211"])
BoxInfo.setItem("HasFBCtuner", ["Vuplus DVB-C NIM(BCM3158)", "Vuplus DVB-C NIM(BCM3148)", "Vuplus DVB-S NIM(7376 FBC)", "Vuplus DVB-S NIM(45308X FBC)", "Vuplus DVB-S NIM(45208 FBC)", "DVB-S2 NIM(45208 FBC)", "DVB-S2X NIM(45308X FBC)", "DVB-S2 NIM(45308 FBC)", "DVB-C NIM(3128 FBC)", "BCM45208", "BCM45308X", "BCM45308X FBC", "BCM3158"])
BoxInfo.setItem("HasHiSi", pathExists("/proc/hisi"))
BoxInfo.setItem("Autoresolution_proc_videomode", MODEL in ("gbue4k", "gbquad4k") and "/proc/stb/video/videomode_50hz" or "/proc/stb/video/videomode")
BoxInfo.setItem("OScamInstalled", fileExists("/usr/bin/oscam") or fileExists("/usr/bin/oscam-emu") or fileExists("/usr/bin/oscam-smod"))
BoxInfo.setItem("OScamIsActive", BoxInfo.getItem("OScamInstalled") and fileExists("/tmp/.oscam/oscam.version"))
BoxInfo.setItem("NCamInstalled", fileExists("/usr/bin/ncam"))
BoxInfo.setItem("NCamIsActive", BoxInfo.getItem("NCamInstalled") and fileExists("/tmp/.ncam/ncam.version"))
BoxInfo.setItem("FrontpanelLEDBlinkControl", fileExists("/proc/stb/fp/led_blink"))
BoxInfo.setItem("FrontpanelLEDBrightnessControl", fileExists("/proc/stb/fp/led_brightness"))
BoxInfo.setItem("FrontpanelLEDColorControl", fileExists("/proc/stb/fp/led_color"))
BoxInfo.setItem("FrontpanelLEDFadeControl", fileExists("/proc/stb/fp/led_fade"))
BoxInfo.setItem("DM9X0", MODEL in ("dm900", "dm920"))

# Network services.
BoxInfo.setItem("inadyn", fileExists("/etc/init.d/inadyn-mt"))
BoxInfo.setItem("minidlna", fileExists("/etc/init.d/minidlna"))
BoxInfo.setItem("ushare", fileExists("/etc/init.d/ushare"))
BoxInfo.setItem("nfsserver", fileExists("/etc/init.d/nfsserver"))
BoxInfo.setItem("samba", fileExists("/etc/init.d/samba"))
BoxInfo.setItem("zerotier", fileExists("/etc/init.d/zerotier"))

# AI
BoxInfo.setItem("AISubs", fileExists("/etc/init.d/aisocket"))

# Vu+ EAC3Fix
BoxInfo.setItem("VuEAC3Fix", MODEL in ("vuultimo4k", "vuduo4kse"))

# Dont't sort.
BoxInfo.setMutableItem("SeekStatePlay", False)
BoxInfo.setMutableItem("StatePlayPause", False)
BoxInfo.setMutableItem("StandbyState", False)
BoxInfo.setMutableItem("FastChannelChange", False)
BoxInfo.setMutableItem("FCCactive", False)

BoxInfo.setItem("CommonInterface", eDVBCIInterfaces.getInstance().getNumOfSlots())
BoxInfo.setItem("CommonInterfaceCIDelay", fileCheck("/proc/stb/tsmux/rmx_delay"))
for ciSlot in range(BoxInfo.getItem("CommonInterface")):
	BoxInfo.setItem(f"CI{ciSlot}SupportsHighBitrates", fileCheck(f"/proc/stb/tsmux/ci{ciSlot}_tsclk"))
	BoxInfo.setItem(f"CI{ciSlot}RelevantPidsRoutingSupport", fileCheck(f"/proc/stb/tsmux/ci{ciSlot}_relevant_pids_routing"))
