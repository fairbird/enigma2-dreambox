# -*- coding: utf-8 -*-
from hashlib import md5
from os import R_OK, access
from os.path import exists as fileAccess, isdir, isfile, join as pathjoin
from re import findall

from enigma import Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl
from Tools.Directories import SCOPE_PLUGINS, SCOPE_LIBDIR, SCOPE_SKIN, fileCheck, fileReadLine, fileReadLines, resolveFilename, fileExists, fileHas, fileReadLine, pathExists
from boxbranding import getHaveVFDSymbol

MODULE_NAME = __name__.split(".")[-1]

SystemInfo = {}

class BoxInformation:  # To maintain data integrity class variables should not be accessed from outside of this class!
	def __init__(self):
		self.immutableList = []
		self.boxInfo = {}
		self.enigmaInfoList = []
		self.enigmaConfList = []
		lines = fileReadLines(pathjoin(resolveFilename(SCOPE_LIBDIR), "enigma.info"), source=MODULE_NAME)
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
						self.boxInfo[item] = self.processValue(value)
			self.enigmaInfoList = sorted(self.enigmaInfoList)
			print("[SystemInfo] Enigma information file data loaded into BoxInfo.")
		else:
			print("[SystemInfo] ERROR: Enigma information file is not available!  The system is unlikely to boot or operate correctly.")
		filename = isfile(resolveFilename(SCOPE_LIBDIR, "enigma.conf"))
		if filename:
			lines = fileReadLines(pathjoin(resolveFilename(SCOPE_LIBDIR), "enigma.conf"), source=MODULE_NAME)
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
							print("[SystemInfo] Note: Enigma information value '%s' with value '%s' being overridden to '%s'." % (item, self.boxInfo[item], value))
						self.boxInfo[item] = self.processValue(value)
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

	def processValue(self, value):
		valueTest = value.upper() if value else ""
		if (value.startswith("\"") or value.startswith("'")) and value.endswith(value[0]):
			value = value[1:-1]
		elif value.startswith("(") and value.endswith(")"):
			data = []
			for item in [x.strip() for x in value[1:-1].split(",")]:
				data.append(self.processValue(item))
			value = tuple(data)
		elif value.startswith("[") and value.endswith("]"):
			data = []
			for item in [x.strip() for x in value[1:-1].split(",")]:
				data.append(self.processValue(item))
			value = list(data)
		elif valueTest == "NONE":
			value = None
		elif valueTest in ("FALSE", "NO", "OFF", "DISABLED", "DISABLE"):
			value = False
		elif valueTest in ("TRUE", "YES", "ON", "ENABLED", "ENABLE"):
			value = True
		elif value.isdigit() or ((value[0:1] == "-" or value[0:1] == "+") and value[1:].isdigit()):
			value = int(value)
		elif valueTest.startswith("0X"):
			try:
				value = int(value, 16)
			except ValueError:
				pass
		elif valueTest.startswith("0O"):
			try:
				value = int(value, 8)
			except ValueError:
				pass
		elif valueTest.startswith("0B"):
			try:
				value = int(value, 2)
			except ValueError:
				pass
		else:
			try:
				value = float(value)
			except ValueError:
				pass
		return value

	def getEnigmaInfoList(self):
		return self.enigmaInfoList

	def getEnigmaConfList(self):
		return self.enigmaConfList

	def getItemsList(self):
		return sorted(list(self.boxInfo.keys()))

	def getItem(self, item, default=None):
		if item in self.boxInfo:
			value = self.boxInfo[item]
		elif item in SystemInfo:
			value = SystemInfo[item]
		else:
			value = default
		return value

	def setItem(self, item, value, immutable=False):
		if item in self.immutableList:
			print("[BoxInfo] Error: Item '%s' is immutable and can not be %s!" % (item, "changed" if item in self.boxInfo else "added"))
			return False
		if immutable:
			self.immutableList.append(item)
		self.boxInfo[item] = value
		SystemInfo[item] = value
		return True

	def deleteItem(self, item):
		if item in self.immutableList:
			print("[BoxInfo] Error: Item '%s' is immutable and can not be deleted!" % item)
		elif item in self.boxInfo:
			del self.boxInfo[item]
			return True
		return False


BoxInfo = BoxInformation()

ARCHITECTURE = BoxInfo.getItem("architecture")
BRAND = BoxInfo.getItem("brand")
MODEL = BoxInfo.getItem("model")
SOCFAMILY = BoxInfo.getItem("socfamily")
DISPLAYTYPE = BoxInfo.getItem("displaytype")
MTDROOTFS = BoxInfo.getItem("mtdrootfs")
DISPLAYMODEL = BoxInfo.getItem("displaymodel")
DISPLAYBRAND = BoxInfo.getItem("displaybrand")
MACHINEBUILD = MODEL

from Tools.Multiboot import getMultibootStartupDevice, getMultibootslots  # This import needs to be here to avoid a SystemInfo load loop!

# Parse the boot commandline.
#
cmdline = fileReadLine("/proc/cmdline", source=MODULE_NAME)
cmdline = {k: v.strip('"') for k, v in findall(r'(\S+)=(".*?"|\S+)', cmdline)}


def getBoxDisplayName():  # This function returns a tuple like ("BRANDNAME", "BOXNAME")
	return (DISPLAYBRAND, DISPLAYMODEL)


def getNumVideoDecoders():
	numVideoDecoders = 0
	while fileExists("/dev/dvb/adapter0/video%d" % numVideoDecoders, "f"):
		numVideoDecoders += 1
	return numVideoDecoders


def countFrontpanelLEDs():
	numLeds = fileExists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while fileExists("/proc/stb/fp/led%d_pattern" % numLeds):
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
	filename = resolveFilename(SCOPE_SKIN, pathjoin("rc_models", "%s.%s" % (BoxInfo.getItem("rcname"), ext)))
	if not isfile(filename):
		filename = resolveFilename(SCOPE_SKIN, pathjoin("rc_models", "dmm1.%s" % ext))
	return filename


BoxInfo.setItem("RCImage", getRCFile("png"))
BoxInfo.setItem("RCMapping", getRCFile("xml"))
SystemInfo["InDebugMode"] = eGetEnigmaDebugLvl() >= 4
SystemInfo["CommonInterface"] = MODEL in ("h9combo", "h9combose", "h10", "pulse4kmini") and 1 or eDVBCIInterfaces.getInstance().getNumOfSlots()
SystemInfo["CommonInterfaceCIDelay"] = fileCheck("/proc/stb/tsmux/rmx_delay")
for cislot in range(0, SystemInfo["CommonInterface"]):
	SystemInfo["CI%dSupportsHighBitrates" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_tsclk" % cislot)
	SystemInfo["CI%dRelevantPidsRoutingSupport" % cislot] = fileCheck("/proc/stb/tsmux/ci%d_relevant_pids_routing" % cislot)
SystemInfo["HasSoftcamInstalled"] = hassoftcaminstalled()
SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["PIPAvailable"] = SystemInfo["NumVideoDecoders"] > 1
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()
SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["LCDsymbol_circle_recording"] = fileCheck("/proc/stb/lcd/symbol_circle") or MODEL in ("hd51", "vs1500") and fileCheck("/proc/stb/lcd/symbol_recording")
SystemInfo["LCDsymbol_timeshift"] = fileCheck("/proc/stb/lcd/symbol_timeshift")
SystemInfo["LCDshow_symbols"] = (MODEL.startswith("et9") or MODEL in ("hd51", "vs1500")) and fileCheck("/proc/stb/lcd/show_symbols")
SystemInfo["LCDsymbol_hdd"] = MODEL in ("hd51", "vs1500") and fileCheck("/proc/stb/lcd/symbol_hdd")
SystemInfo["FrontpanelDisplayGrayscale"] = fileExists("/dev/dbox/oled0")
SystemInfo["CanUse3DModeChoices"] = fileExists("/proc/stb/fb/3dmode_choices") and True or False
SystemInfo["DeepstandbySupport"] = MODEL != "dm800"
SystemInfo["OLDE2API"] = MODEL in ("dm800")
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["PowerLED"] = fileCheck("/proc/stb/power/powerled") or MODEL in ("gbue4k", "gbquad4k") and fileCheck("/proc/stb/fp/led1_pattern")
SystemInfo["StandbyLED"] = fileCheck("/proc/stb/power/standbyled") or MODEL in ("gbue4k", "gbquad4k") and fileCheck("/proc/stb/fp/led0_pattern")
SystemInfo["SuspendLED"] = fileCheck("/proc/stb/power/suspendled") or fileCheck("/proc/stb/fp/enable_led")
SystemInfo["Display"] = SystemInfo["FrontpanelDisplay"] or SystemInfo["StandbyLED"] or MODEL in ("dreamone", "dreamtwo")
SystemInfo["LedPowerColor"] = fileCheck("/proc/stb/fp/ledpowercolor")
SystemInfo["LedStandbyColor"] = fileCheck("/proc/stb/fp/ledstandbycolor")
SystemInfo["LedSuspendColor"] = fileCheck("/proc/stb/fp/ledsuspendledcolor")
SystemInfo["Power4x7On"] = fileCheck("/proc/stb/fp/power4x7on")
SystemInfo["Power4x7Standby"] = fileCheck("/proc/stb/fp/power4x7standby")
SystemInfo["Power4x7Suspend"] = fileCheck("/proc/stb/fp/power4x7suspend")
SystemInfo["PowerOffDisplay"] = MODEL not in "formuler1" and fileCheck("/proc/stb/power/vfd") or fileCheck("/proc/stb/lcd/vfd")
SystemInfo["WakeOnLAN"] = not MODEL.startswith("et8000") and fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HasExternalPIP"] = not (MODEL.startswith("et9") or MODEL in ("e4hd",)) and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["HasGPT"] = MODEL in ("dreamone", "dreamtwo") and pathExists("/dev/mmcblk0p7")
SystemInfo["MaxPIPSize"] = MODEL in ("hd51", "h7", "vs1500", "e4hd") and (360, 288) or (540, 432)
SystemInfo["VFD_scroll_repeats"] = not MODEL.startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_repeats")
SystemInfo["VFD_scroll_delay"] = not MODEL.startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_delay")
SystemInfo["VFD_initial_scroll_delay"] = not MODEL.startswith("et8500") and fileCheck("/proc/stb/lcd/initial_scroll_delay")
SystemInfo["VFD_final_scroll_delay"] = not MODEL.startswith("et8500") and fileCheck("/proc/stb/lcd/final_scroll_delay")
SystemInfo["LcdLiveTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["LcdLiveTVMode"] = fileCheck("/proc/stb/lcd/mode")
SystemInfo["LcdLiveDecoder"] = fileCheck("/proc/stb/lcd/live_decoder")
SystemInfo["LCDMiniTV"] = fileExists("/proc/stb/lcd/mode")
SystemInfo["ConfigDisplay"] = SystemInfo["FrontpanelDisplay"]
SystemInfo["DefaultDisplayBrightness"] = MODEL in ("dm900", "dm920", "dreamone", "dreamtwo") and 8 or 5
SystemInfo["FastChannelChange"] = False
SystemInfo["3DMode"] = fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d")
SystemInfo["3DZNorm"] = fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset")
SystemInfo["Blindscan_t2_available"] = fileCheck("/proc/stb/info/vuMODEL") and MODEL.startswith("vu")
SystemInfo["RcTypeChangable"] = not (MODEL in ("gbquad4k", "gbue4k", "et8500") or MODEL.startswith("et7")) and pathExists("/proc/stb/ir/rc/type")
SystemInfo["HasFullHDSkinSupport"] = MODEL not in ("et4000", "et5000", "sh1", "hd500c", "hd1100", "xp1000", "lc")
SystemInfo["HasBypassEdidChecking"] = fileCheck("/proc/stb/hdmi/bypass_edid_checking")
SystemInfo["HasMMC"] = "root" in cmdline and cmdline["root"].startswith("/dev/mmcblk")
SystemInfo["HasColorspace"] = fileCheck("/proc/stb/video/hdmi_colorspace")
SystemInfo["HasColorspaceSimple"] = SystemInfo["HasColorspace"] and SystemInfo["HasMMC"] and SystemInfo["Blindscan_t2_available"]
SystemInfo["HasTranscoding"] = pathExists("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0")
SystemInfo["HasH265Encoder"] = fileHas("/proc/stb/encoder/0/vcodec_choices", "h265")
SystemInfo["CanNotDoSimultaneousTranscodeAndPIP"] = MODEL in ("vusolo4k", "gbquad4k", "gbue4k")
SystemInfo["HasColordepth"] = fileCheck("/proc/stb/video/hdmi_colordepth")
SystemInfo["HasColorimetryChoices"] = fileCheck("/proc/stb/video/hdmi_colorimetry_choices")
SystemInfo["HasFrontDisplayPicon"] = MODEL in ("et8500", "vusolo4k", "vuuno4kse", "vuduo4k", "vuduo4kse", "vuultimo4k", "gbquad4k", "gbue4k")
SystemInfo["Has24hz"] = fileCheck("/proc/stb/video/videomode_24hz")
SystemInfo["Has2160p"] = fileHas("/proc/stb/video/videomode_preferred", "2160p50")
SystemInfo["HasHDMIpreemphasis"] = fileCheck("/proc/stb/hdmi/preemphasis")
SystemInfo["HasColorimetry"] = fileCheck("/proc/stb/video/hdmi_colorimetry")
SystemInfo["HasColorspaceChoices"] = fileCheck("/proc/stb/video/hdmi_colorspace_choices")
SystemInfo["HasColordepthChoices"] = fileCheck("/proc/stb/video/hdmi_colordepth_choices")
SystemInfo["HasHdrType"] = fileCheck("/proc/stb/video/hdmi_hdrtype")
SystemInfo["HasScaler_sharpness"] = pathExists("/proc/stb/vmpeg/0/pep_scaler_sharpness")
SystemInfo["VFDSymbol"] = getHaveVFDSymbol() == "True"
SystemInfo["DreamBoxAudio"] = MODEL in ("dm7080", "dm800", "dm900", "dm920", "dreamone", "dreamtwo")
SystemInfo["DreamBoxDVI"] = MODEL in ("dm8000", "dm800")
SystemInfo["HasHDMIin"] = MODEL in ("dm7080", "dm820")
SystemInfo["HasHDMIinFHD"] = MODEL in ("dm900", "dm920", "dreamone", "dreamtwo")
SystemInfo["HDMIin"] = SystemInfo["HasHDMIin"] or SystemInfo["HasHDMIinFHD"]
SystemInfo["HasHDMIinPiP"] = SystemInfo["HasHDMIin"] and BRAND != "dreambox"
SystemInfo["HasHDMI-CEC"] = BoxInfo.getItem("hdmi") and fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/HdmiCEC/plugin.pyc")) and (fileExists("/dev/cec0") or fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0"))
SystemInfo["HasYPbPr"] = MODEL in ("dm8000", "et5000", "et6000", "et6500", "et9000", "et9200", "et9500", "et10000", "formuler1", "mbtwinplus", "spycat", "vusolo", "vuduo", "vuduo2", "vuultimo")
SystemInfo["HasScart"] = MODEL in ("dm8000", "et4000", "et6500", "et8000", "et9000", "et9200", "et9500", "et10000", "formuler1", "hd1100", "hd1200", "hd1265", "hd2400", "vusolo", "vusolo2", "vuduo", "vuduo2", "vuultimo", "vuuno", "xp1000")
SystemInfo["HasSVideo"] = MODEL in ("dm8000")
SystemInfo["RecoveryMode"] = fileCheck("/proc/stb/fp/boot_mode") or MODEL in ("dreamone", "dreamtwo")
SystemInfo["AmlogicFamily"] = SOCFAMILY.startswith(("aml", "meson")) or fileCheck("/proc/device-tree/amlogic-dt-id") or isfile("/usr/bin/amlhalt") or fileAccess("/sys/module/amports")
SystemInfo["HasComposite"] = MODEL not in ("i55", "gbquad4k", "gbue4k", "hd1500", "osnino", "osninoplus", "purehd", "purehdse", "revo4k", "vusolo4k", "vuzero4k", "vuduo4k", "vuduo4kse", "vuuno4k", "vuuno4kse", "vuultimo4k")
SystemInfo["hasXcoreVFD"] = MODEL in ("osmega", "spycat4k", "spycat4kmini", "spycat4kcombo") and fileCheck("/sys/module/brcmstb_%s/parameters/pt6302_cgram" % MODEL)
SystemInfo["HasOfflineDecoding"] = MODEL not in ("osmini", "osminiplus", "et7000mini", "et11000", "mbmicro", "mbtwinplus", "mbmicrov2", "et7000", "et8500")
SystemInfo["hasKexec"] = fileHas("/proc/cmdline", "kexec=1")
SystemInfo["canKexec"] = not SystemInfo["hasKexec"] and fileExists("/usr/bin/kernel_auto.bin") and fileExists("/usr/bin/STARTUP.cpio.gz") and (MODEL in ("vuduo4k", "vuduo4kse") and ["mmcblk0p9", "mmcblk0p6"] or MODEL in ("vusolo4k", "vuultimo4k", "vuuno4k", "vuuno4kse") and ["mmcblk0p4", "mmcblk0p1"] or MODEL == "vuzero4k" and ["mmcblk0p7", "mmcblk0p4"])
SystemInfo["MultibootStartupDevice"] = getMultibootStartupDevice()
SystemInfo["canMode12"] = "%s_4.boxmode" % MODEL in cmdline and cmdline["%s_4.boxmode" % MODEL] in ("1", "12") and "192M"
SystemInfo["canMultiBoot"] = getMultibootslots()
SystemInfo["canDualBoot"] = fileExists("/dev/block/by-name/flag")
SystemInfo["canFlashWithOfgwrite"] = not(MODEL.startswith("dm"))
SystemInfo["CanProc"] = SystemInfo["HasMMC"] and not SystemInfo["Blindscan_t2_available"]
SystemInfo["HasMultichannelPCM"] = fileCheck("/proc/stb/audio/multichannel_pcm")
SystemInfo["HasAutoVolume"] = fileExists("/proc/stb/audio/avl_choices") and fileCheck("/proc/stb/audio/avl")
SystemInfo["HasAutoVolumeLevel"] = fileExists("/proc/stb/audio/autovolumelevel_choices") and fileCheck("/proc/stb/audio/autovolumelevel")
SystemInfo["Has3DSurround"] = fileExists("/proc/stb/audio/3d_surround_choices") and fileCheck("/proc/stb/audio/3d_surround")
SystemInfo["Has3DSpeaker"] = fileExists("/proc/stb/audio/3d_surround_speaker_position_choices") and fileCheck("/proc/stb/audio/3d_surround_speaker_position")
SystemInfo["Has3DSurroundSpeaker"] = fileExists("/proc/stb/audio/3dsurround_choices") and fileCheck("/proc/stb/audio/3dsurround")
SystemInfo["Has3DSurroundSoftLimiter"] = fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") and fileCheck("/proc/stb/audio/3dsurround_softlimiter")
SystemInfo["CanDownmixAC3"] = fileHas("/proc/stb/audio/ac3_choices", "downmix")
SystemInfo["CanDownmixDTS"] = fileHas("/proc/stb/audio/dts_choices", "downmix")
SystemInfo["CanDownmixAAC"] = fileHas("/proc/stb/audio/aac_choices", "downmix")
SystemInfo["CanDownmixAACPlus"] = fileHas("/proc/stb/audio/aacplus_choices", "downmix")
SystemInfo["HDMIAudioSource"] = fileCheck("/proc/stb/hdmi/audio_source") or fileCheck("/sys/devices/virtual/amhdmitx/amhdmitx0/audio_source")
SystemInfo["CanAC3Transcode"] = fileHas("/proc/stb/audio/ac3plus_choices", "force_ac3")
SystemInfo["CanDTSHD"] = fileHas("/proc/stb/audio/dtshd_choices", "downmix")
SystemInfo["CanAACTranscode"] = fileHas("/proc/stb/audio/aac_transcode_choices", "off")
SystemInfo["CanWMAPRO"] = fileHas("/proc/stb/audio/wmapro_choices", "downmix")
SystemInfo["CanAC3plusTranscode"] = fileExists("/proc/stb/audio/ac3plus_choices")
SystemInfo["CanAudioDelay"] = fileCheck("/proc/stb/audio/audio_delay_pcm") or fileCheck("/proc/stb/audio/audio_delay_bitstream")
SystemInfo["CanSyncMode"] = fileExists("/proc/stb/video/sync_mode_choices")
SystemInfo["CanBTAudio"] = fileHas("/proc/stb/audio/btaudio_choices", "off")
SystemInfo["CanBTAudioDelay"] = fileCheck("/proc/stb/audio/btaudio_delay") or fileCheck("/proc/stb/audio/btaudio_delay_pcm")
SystemInfo["CanChangeOsdAlpha"] = access("/proc/stb/video/alpha", R_OK) and True or False
SystemInfo["CanChangeOsdPlaneAlpha"] = access("/sys/class/graphics/fb0/osd_plane_alpha", R_OK) and True or False
SystemInfo["CanChangeOsdPositionAML"] = access('/sys/class/graphics/fb0/free_scale', R_OK) and True or False
SystemInfo["ScalerSharpness"] = fileCheck("/proc/stb/vmpeg/0/pep_scaler_sharpness")
SystemInfo["BootDevice"] = getBootdevice()
SystemInfo["NimExceptionVuSolo2"] = MODEL == "vusolo2"
SystemInfo["NimExceptionVuDuo2"] = MODEL == "vuduo2"
SystemInfo["NimExceptionDMM8000"] = MODEL == "dm8000"
SystemInfo["FbcTunerPowerAlwaysOn"] = MODEL in ("vusolo4k", "vuduo4k", "vuduo4kse", "vuultimo4k", "vuuno4k", "vuuno4kse")
SystemInfo["HasPhysicalLoopthrough"] = ["Vuplus DVB-S NIM(AVL2108)", "GIGA DVB-S2 NIM (Internal)"]
if MODEL in ("et7500", "et8500"):
	SystemInfo["HasPhysicalLoopthrough"].append("AVL6211")
SystemInfo["HasFBCtuner"] = ["Vuplus DVB-C NIM(BCM3158)", "Vuplus DVB-C NIM(BCM3148)", "Vuplus DVB-S NIM(7376 FBC)", "Vuplus DVB-S NIM(45308X FBC)", "Vuplus DVB-S NIM(45208 FBC)", "DVB-S2 NIM(45208 FBC)", "DVB-S2X NIM(45308X FBC)", "DVB-S2 NIM(45308 FBC)", "DVB-C NIM(3128 FBC)", "BCM45208", "BCM45308X", "BCM3158"]
SystemInfo["HasHiSi"] = pathExists("/proc/hisi")
SystemInfo["SeekStatePlay"] = False
SystemInfo["StatePlayPause"] = False
SystemInfo["StandbyState"] = False
SystemInfo["OScamInstalled"] = fileExists("/usr/bin/oscam") or fileExists("/usr/bin/oscam-emu") or fileExists("/usr/bin/oscam-smod")
SystemInfo["OScamIsActive"] = SystemInfo["OScamInstalled"] and fileExists("/tmp/.oscam/oscam.version")
SystemInfo["NCamInstalled"] = fileExists("/usr/bin/ncam")
SystemInfo["NCamIsActive"] = SystemInfo["NCamInstalled"] and fileExists("/tmp/.ncam/ncam.version")
SystemInfo["FrontpanelLEDBlinkControl"] = fileExists("/proc/stb/fp/led_blink")
SystemInfo["FrontpanelLEDBrightnessControl"] = fileExists("/proc/stb/fp/led_brightness")
SystemInfo["FrontpanelLEDColorControl"] = fileExists("/proc/stb/fp/led_color")
SystemInfo["FrontpanelLEDFadeControl"] = fileExists("/proc/stb/fp/led_fade")
SystemInfo["FCCactive"] = False
SystemInfo["Autoresolution_proc_videomode"] = MODEL in ("gbue4k", "gbquad4k") and "/proc/stb/video/videomode_50hz" or "/proc/stb/video/videomode"
SystemInfo["HDRSupport"] = fileExists("/proc/stb/hdmi/hlg_support_choices") and fileCheck("/proc/stb/hdmi/hlg_support")
SystemInfo["AmlHDRSupport"] = isfile("/sys/class/amhdmitx/amhdmitx0/config")
