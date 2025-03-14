# -*- coding: utf-8 -*-
from ast import literal_eval
from hashlib import md5
from os import R_OK, access
from os.path import exists as fileAccess, isdir, isfile, join
from re import findall

from enigma import eAVControl, Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl
from Tools.Directories import SCOPE_PLUGINS, SCOPE_LIBDIR, SCOPE_SKIN, fileCheck, fileReadLine, fileReadLines, resolveFilename, fileExists, fileHas, fileReadLine, pathExists
from Tools.MultiBoot import MultiBoot

MODULE_NAME = __name__.split(".")[-1]


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
						except:  # Remove this code when the build system is updated.
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


def getChipsetString():
	if MODEL in ("dm7080", "dm820"):
		chipset = "7435"
	elif MODEL in ("dm520", "dm525"):
		chipset = "73625"
	elif MODEL in ("dm900", "dm920", "et13000"):
		chipset = "7252S"
	elif MODEL in ("hd51", "vs1500", "h7"):
		chipset = "7251S"
	elif MODEL in ("dreamone", "dreamtwo"):
		chipset = "S922X"
	else:
		chipset = fileReadLine("/proc/stb/info/chipset", default=_("Undefined"), source=MODULE_NAME)
		chipset = chipset.lower().replace("\n", "").replace("bcm", "").replace("brcm", "").replace("sti", "")
	return chipset


def getModuleLayout():
	module = None
	modulePath = BoxInfo.getItem("enigmamodule")
	if modulePath:
		process = Popen(("/sbin/modprobe", "--dump-modversions", modulePath), stdout=PIPE, stderr=PIPE, universal_newlines=True)
		stdout, stderr = process.communicate()
		if process.returncode == 0:
			for detail in stdout.split("\n"):
				if "module_layout" in detail:
					module = detail.split("\t")[0]
	return module


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
BoxInfo.setItem("ModuleLayout", getModuleLayout())

BoxInfo.setItem("BoxName", getBoxName())
BoxInfo.setItem("RCImage", getRCFile("png"))
BoxInfo.setItem("RCMapping", getRCFile("xml"))

BoxInfo.setItem("canMultiBoot", MultiBoot.getBootSlots())
BoxInfo.setItem("HasKexecMultiboot", fileHas("/proc/cmdline", "kexec=1"))
BoxInfo.setItem("cankexec", BoxInfo.getItem("kexecmb") and fileExists("/usr/bin/kernel_auto.bin") and fileExists("/usr/bin/STARTUP.cpio.gz") and not BoxInfo.getItem("HasKexecMultiboot"))
BoxInfo.setItem("HasSDmmc", MultiBoot.canMultiBoot() and "sd" in MultiBoot.getBootSlots()["2"] and "mmcblk" in MTDROOTFS)
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
BoxInfo.setItem("VideoDestinationConfigurable", fileExists("/proc/stb/vmpeg/0/dst_left"))
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
BoxInfo.setItem("HasBypassEdidChecking", fileCheck("/proc/stb/hdmi/bypass_edid_checking"))
BoxInfo.setItem("HasMMC", "root" in cmdline and cmdline["root"].startswith("/dev/mmcblk"))
BoxInfo.setItem("HasColorspace", fileCheck("/proc/stb/video/hdmi_colorspace"))
BoxInfo.setItem("HasColorspaceSimple", BoxInfo.getItem("HasColorspace") and BoxInfo.getItem("HasMMC") and BoxInfo.getItem("Blindscan_t2_available"))
BoxInfo.setItem("HasTranscoding", pathExists("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0"))
BoxInfo.setItem("HasH265Encoder", fileHas("/proc/stb/encoder/0/vcodec_choices", "h265"))
BoxInfo.setItem("CanNotDoSimultaneousTranscodeAndPIP", MODEL in ("vusolo4k", "gbquad4k", "gbue4k"))
BoxInfo.setItem("HasColordepth", fileCheck("/proc/stb/video/hdmi_colordepth"))
BoxInfo.setItem("HasFrontDisplayPicon", MODEL in ("et8500", "vusolo4k", "vuuno4kse", "vuduo4k", "vuduo4kse", "vuultimo4k", "gbquad4k", "gbue4k"))
BoxInfo.setItem("Has24hz", fileCheck("/proc/stb/video/videomode_24hz"))
BoxInfo.setItem("Has2160p", fileHas("/proc/stb/video/videomode_preferred", "2160p50"))
BoxInfo.setItem("HasHDMIpreemphasis", fileCheck("/proc/stb/hdmi/preemphasis"))
BoxInfo.setItem("HasColorimetry", fileCheck("/proc/stb/video/hdmi_colorimetry"))
BoxInfo.setItem("HasHdrType", fileCheck("/proc/stb/video/hdmi_hdrtype"))
BoxInfo.setItem("HasScaler_sharpness", pathExists("/proc/stb/vmpeg/0/pep_scaler_sharpness"))
BoxInfo.setItem("HasColorimetryChoices", fileCheck("/proc/stb/video/hdmi_colorimetry_choices"))
BoxInfo.setItem("HasColorspaceChoices", fileCheck("/proc/stb/video/hdmi_colorspace_choices"))
BoxInfo.setItem("HasColordepthChoices", fileCheck("/proc/stb/video/hdmi_colordepth_choices"))
BoxInfo.setItem("HasHDMIin", BoxInfo.getItem("hdmifhdin") or BoxInfo.getItem("hdmihdin"))
BoxInfo.setItem("HasHDMIinFHD", MODEL in ("dm900", "dm920", "dreamone", "dreamtwo"))
BoxInfo.setItem("HasHDMIinPiP", BoxInfo.getItem("HasHDMIin") and BRAND != "dreambox")
BoxInfo.setItem("DreamBoxAudio", MODEL in ("dm7080", "dm800", "dm900", "dm920", "dreamone", "dreamtwo"))
BoxInfo.setItem("DreamBoxDVI", MODEL in ("dm8000", "dm800"))
BoxInfo.setItem("VFDSymbol", BoxInfo.getItem("vfdsymbol"))
BoxInfo.setItem("HasHDMI-CEC", BoxInfo.getItem("hdmi") and fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/HdmiCEC/plugin.pyc")) and (fileExists("/dev/cec0") or fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0")))
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
BoxInfo.setItem("HDRSupport", fileExists("/proc/stb/hdmi/hlg_support_choices") and fileCheck("/proc/stb/hdmi/hlg_support"))
BoxInfo.setItem("AmlHDRSupport", isfile("/sys/class/amhdmitx/amhdmitx0/config"))
BoxInfo.setItem("CanProc", BoxInfo.getItem("HasMMC") and not BoxInfo.getItem("Blindscan_t2_available"))
BoxInfo.setItem("HasMultichannelPCM", fileCheck("/proc/stb/audio/multichannel_pcm"))
BoxInfo.setItem("HasAutoVolume", fileExists("/proc/stb/audio/avl_choices") and fileCheck("/proc/stb/audio/avl"))
BoxInfo.setItem("HasAutoVolumeLevel", fileExists("/proc/stb/audio/autovolumelevel_choices") and fileCheck("/proc/stb/audio/autovolumelevel"))
BoxInfo.setItem("Has3DSurround", fileExists("/proc/stb/audio/3d_surround_choices") and fileCheck("/proc/stb/audio/3d_surround"))
BoxInfo.setItem("Has3DSpeaker", fileExists("/proc/stb/audio/3d_surround_speaker_position_choices") and fileCheck("/proc/stb/audio/3d_surround_speaker_position"))
BoxInfo.setItem("Has3DSurroundSpeaker", fileExists("/proc/stb/audio/3dsurround_choices") and fileCheck("/proc/stb/audio/3dsurround"))
BoxInfo.setItem("Has3DSurroundSoftLimiter", fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") and fileCheck("/proc/stb/audio/3dsurround_softlimiter"))
BoxInfo.setItem("CanDownmixAC3", fileHas("/proc/stb/audio/ac3_choices", "downmix"))
BoxInfo.setItem("CanDownmixDTS", fileHas("/proc/stb/audio/dts_choices", "downmix"))
BoxInfo.setItem("CanDownmixAAC", fileHas("/proc/stb/audio/aac_choices", "downmix"))
BoxInfo.setItem("HDMIAudioSource", fileCheck("/proc/stb/hdmi/audio_source"))
BoxInfo.setItem("CanAC3Transcode", fileHas("/proc/stb/audio/ac3plus_choices", "force_ac3"))
BoxInfo.setItem("CanDTSHD", fileHas("/proc/stb/audio/dtshd_choices", "downmix"))
BoxInfo.setItem("CanDownmixAACPlus", fileHas("/proc/stb/audio/aacplus_choices", "downmix"))
BoxInfo.setItem("CanAACTranscode", fileHas("/proc/stb/audio/aac_transcode_choices", "off"))
BoxInfo.setItem("CanWMAPRO", fileHas("/proc/stb/audio/wmapro_choices", "downmix"))
BoxInfo.setItem("CanBTAudio", fileHas("/proc/stb/audio/btaudio_choices", "off"))
BoxInfo.setItem("CanBTAudioDelay", fileCheck("/proc/stb/audio/btaudio_delay") or fileCheck("/proc/stb/audio/btaudio_delay_pcm"))
BoxInfo.setItem("BootDevice", getBootdevice())
BoxInfo.setItem("NimExceptionVuSolo2", MODEL == "vusolo2")
BoxInfo.setItem("NimExceptionVuDuo2", MODEL == "vuduo2")
BoxInfo.setItem("NimExceptionDMM8000", MODEL == "dm8000")
BoxInfo.setItem("FbcTunerPowerAlwaysOn", MODEL in ("vusolo4k", "vuduo4k", "vuduo4kse", "vuultimo4k", "vuuno4k", "vuuno4kse", "dm900", "dm920"))
BoxInfo.setItem("HasPhysicalLoopthrough", ["Vuplus DVB-S NIM(AVL2108)", "GIGA DVB-S2 NIM (Internal)"])
BoxInfo.setItem("CanAC3plusTranscode", fileExists("/proc/stb/audio/ac3plus_choices"))
BoxInfo.setItem("CanAudioDelay", fileCheck("/proc/stb/audio/audio_delay_pcm") or fileCheck("/proc/stb/audio/audio_delay_bitstream"))
BoxInfo.setItem("CanSyncMode", fileExists("/proc/stb/video/sync_mode_choices"))
BoxInfo.setItem("CanChangeOsdAlpha", eAVControl.getInstance().hasOSDAlpha())
BoxInfo.setItem("CanChangeOsdPlaneAlpha", access("/sys/class/graphics/fb0/osd_plane_alpha", R_OK) and True or False)
BoxInfo.setItem("CanChangeOsdPositionAML", access("/sys/class/graphics/fb0/free_scale", R_OK) and True or False)
BoxInfo.setItem("ScalerSharpness", fileCheck("/proc/stb/vmpeg/0/pep_scaler_sharpness"))
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

# AI
BoxInfo.setItem("AISubs", False)

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
