# -*- coding: utf-8 -*-
from Components.config import config, ConfigSlider, ConfigSelection, ConfigYesNo, ConfigEnableDisable, ConfigOnOff, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, NoSave
from enigma import eAVSwitch, eAVControl, getDesktop
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileWriteLine
from Tools.AVHelper import pChoice, readChoices
from os.path import isfile
import os

iAVSwitch = None # will be initialized later, allows to import name 'iAVSwitch' from 'Components.AVSwitch'

MODULE_NAME = __name__.split(".")[-1]

model = BoxInfo.getItem("model")


class AVSwitch:
	def setAspect(self, configElement):
		eAVControl.getInstance().setAspect(configElement.value, 1)

	def setAspectRatio(self, value):
		if value < 100:
			eAVControl.getInstance().setAspectRatio(value)
		else:  # Aspect Switcher
			value -= 100
			offset = config.av.aspectswitch.offsets[str(value)].value
			newheight = 576 - offset
			newtop = offset // 2
			if value:
				newwidth = 720
			else:
				newtop = 0
				newwidth = 0
				newheight = 0

			eAVControl.getInstance().setAspectRatio(2)  # 16:9
			eAVControl.getInstance().setVideoSize(newtop, 0, newwidth, newheight)

	def setColorFormat(self, value):
		eAVSwitch.getInstance().setColorFormat(value)

	def setInput(self, input):
		eAVControl.getInstance().setInput(input, 1)

	def setSystem(self, value):
		eAVSwitch.getInstance().setVideomode(value)

	def getOutputAspect(self):
		valstr = config.av.aspectratio.value
		if valstr in ("4_3_letterbox", "4_3_panscan"): # 4:3
			return (4, 3)
		elif valstr == "16_9": # auto ... 4:3 or 16:9
			if isfile("/proc/stb/vmpeg/0/aspect"):
				try:
					if "1" in open("/proc/stb/vmpeg/0/aspect", "r").read().split('\n', 1)[0]: # 4:3
						return (4, 3)
				except IOError:
					print("[AVSwitch] Read /proc/stb/vmpeg/0/aspect failed!")
			elif isfile("/sys/class/video/screen_mode"):
				try:
					if "1" in open("/sys/class/video/screen_mode", "r").read().split('\n', 1)[0]: # 4:3
						return (4, 3)
				except IOError:
					print("[AVSwitch] Read /sys/class/video/screen_mode failed!")
		elif valstr in ("16_9_always", "16_9_letterbox"): # 16:9
			pass
		elif valstr in ("16_10_letterbox", "16_10_panscan"): # 16:10
			return (16, 10)
		return (16, 9)

	def getFramebufferScale(self):
		aspect = self.getOutputAspect()
		fb_size = getDesktop(0).size()
		return (aspect[0] * fb_size.height(), aspect[1] * fb_size.width())

	def getAspectRatioSetting(self):
		valstr = config.av.aspectratio.value
		if valstr == "4_3_letterbox":
			val = 0
		elif valstr == "4_3_panscan":
			val = 1
		elif valstr == "16_9":
			val = 2
		elif valstr == "16_9_always":
			val = 3
		elif valstr == "16_10_letterbox":
			val = 4
		elif valstr == "16_10_panscan":
			val = 5
		elif valstr == "16_9_letterbox":
			val = 6
		return val

	def setAspectWSS(self, aspect=None):
		if not config.av.wss.value:
			value = 2 # auto(4:3_off)
		else:
			value = 1 # auto
		eAVSwitch.getInstance().setWSS(value)


def InitAVSwitch():
	config.av = ConfigSubsection()
	config.av.yuvenabled = ConfigBoolean(default=True)
	colorformat_choices = {"cvbs": "CVBS"}
	
	config.av.osd_alpha = ConfigSlider(default=255, increment=5, limits=(20, 255))  # Make Openpli compatible with some plugins who still use config.av.osd_alpha.

	# when YUV, Scart or S-Video is not support by HW, don't let the user select it
	if BoxInfo.getItem("HasYPbPr"):
		colorformat_choices["yuv"] = "YPbPr"
	if BoxInfo.getItem("HasScart"):
		colorformat_choices["rgb"] = "RGB"
	if BoxInfo.getItem("HasSVideo"):
		colorformat_choices["svideo"] = "S-Video"

	config.av.colorformat = ConfigSelection(choices=colorformat_choices, default="cvbs")
	config.av.aspectratio = ConfigSelection(choices={
			"4_3_letterbox": _("4:3 letterbox"),
			"4_3_panscan": _("4:3 panscan"),
			"16_9": _("16:9"),
			"16_9_always": _("16:9 always"),
			"16_10_letterbox": _("16:10 letterbox"),
			"16_10_panscan": _("16:10 panscan"),
			"16_9_letterbox": _("16:9 letterbox")},
			default="16_9")
	config.av.aspect = ConfigSelection(choices={
			"4_3": _("4:3"),
			"16_9": _("16:9"),
			"16_10": _("16:10"),
			"auto": _("Automatic")},
			default="auto")

	if isfile("/proc/stb/video/policy2"):
		if isfile("/proc/stb/video/policy2_choices"):
			policy2_choices_proc = "/proc/stb/video/policy2_choices"
		else:
			if isfile("/proc/stb/video/policy_choices"):
				policy2_choices_proc = "/proc/stb/video/policy_choices"
			else:
				policy2_choices_proc = None
		try:
			policy2_choices_raw = open(policy2_choices_proc, "r").read()
		except:
			policy2_choices_raw = "letterbox"

		policy2_choices = {}

		if policy2_choices_raw and policy2_choices_raw is not None:
			if "letterbox" in policy2_choices_raw:
				policy2_choices.update({"letterbox": _("Letterbox")})
			if "panscan" in policy2_choices_raw:
				policy2_choices.update({"panscan": _("Pan&scan")})
			if "nonliner" in policy2_choices_raw and not "nonlinear" in policy2_choices_raw:
				policy2_choices.update({"nonliner": _("Stretch nonlinear")})
			if "nonlinear" in policy2_choices_raw:
				policy2_choices.update({"nonlinear": _("Stretch nonlinear")})
			if "scale" in policy2_choices_raw and not "auto" in policy2_choices_raw and not "bestfit" in policy2_choices_raw:
				policy2_choices.update({"scale": _("Stretch linear")})
			if "full" in policy2_choices_raw:
				policy2_choices.update({"full": _("Stretch full")})
			if "auto" in policy2_choices_raw and not "bestfit" in policy2_choices_raw:
				policy2_choices.update({"auto": _("Stretch linear")})
			if "bestfit" in policy2_choices_raw:
				policy2_choices.update({"bestfit": _("Stretch linear")})
		config.av.policy_169 = ConfigSelection(choices=policy2_choices, default="letterbox")

	if isfile("/proc/stb/video/policy_choices"):
		policy_choices_proc = "/proc/stb/video/policy_choices"
	else:
		policy_choices_proc = None
	try:
		policy_choices_raw = open(policy_choices_proc, "r").read()
	except:
		policy_choices_raw = "panscan"

	policy_choices = {}

	if policy_choices_raw and policy_choices_raw is not None:
		if "pillarbox" in policy_choices_raw and not "panscan" in policy_choices_raw:
			policy_choices.update({"pillarbox": _("Pillarbox")})
		if "panscan" in policy_choices_raw:
			policy_choices.update({"panscan": _("Pillarbox")})
		if "letterbox" in policy_choices_raw:
			policy_choices.update({"letterbox": _("Pan&scan")})
		if "nonliner" in policy_choices_raw and not "nonlinear" in policy_choices_raw:
			policy_choices.update({"nonliner": _("Stretch nonlinear")})
		if "nonlinear" in policy_choices_raw:
			policy_choices.update({"nonlinear": _("Stretch nonlinear")})
		if "scale" in policy_choices_raw and not "auto" in policy_choices_raw and not "bestfit" in policy_choices_raw:
			policy_choices.update({"scale": _("Stretch linear")})
		if "full" in policy_choices_raw:
			policy_choices.update({"full": _("Stretch full")})
		if "auto" in policy_choices_raw and not "bestfit" in policy_choices_raw:
			policy_choices.update({"auto": _("Stretch linear")})
		if "bestfit" in policy_choices_raw:
			policy_choices.update({"bestfit": _("Stretch linear")})
	config.av.policy_43 = ConfigSelection(choices=policy_choices, default="panscan")

	config.av.tvsystem = ConfigSelection(choices={"pal": "PAL", "ntsc": "NTSC", "multinorm": "multinorm"}, default="pal")
	config.av.wss = ConfigEnableDisable(default=True)
	config.av.generalAC3delay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
	config.av.generalPCMdelay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
	config.av.vcrswitch = ConfigEnableDisable(default=False)

	def setColorFormat(configElement):
		map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		iAVSwitch.setColorFormat(map[configElement.value])
	config.av.colorformat.addNotifier(setColorFormat)

	def setAspectRatio(self, value):
		iAVSwitch.setAspectRatio(value)

	def setSystem(configElement):
		map = {"pal": 0, "ntsc": 1, "multinorm": 2}
		iAVSwitch.setSystem(map[configElement.value])

	def setWSS(configElement):
		iAVSwitch.setAspectWSS()

	# this will call the "setup-val" initial
	config.av.tvsystem.addNotifier(setSystem)
	config.av.wss.addNotifier(setWSS)

	iAVSwitch.setInput("encoder") # init on startup

	BoxInfo.setItem("ScartSwitch", eAVControl.getInstance().hasScartSwitch())

	if BoxInfo.getItem("HasBypassEdidChecking"):
		choices = [
			("00000000", _("Off")),
			("00000001", _("On"))
		]
		default = "00000000"

		def setEDIDBypass(configElement):
			try:
				open("/proc/stb/hdmi/bypass_edid_checking", "w").write("00000001" if configElement.value else "00000000")
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/hdmi/bypass_edid_checking failed!")
		config.av.bypass_edid_checking = ConfigSelection(choices=choices, default=default)
		config.av.bypass_edid_checking.addNotifier(setEDIDBypass)
	else:
		config.av.bypass_edid_checking = ConfigNothing()

	if BoxInfo.getItem("HasColorspace"):
		if BoxInfo.getItem("FbcTunerPowerAlwaysOn"):
			choices = [
				(pChoice("Edid(Auto)")),
				(pChoice("Hdmi_Rgb")),
				("444", _("YCbCr 444")),
				("422", _("YCbCr 422")),
				("420", _("YCbCr 420"))
			]
			default = "Edid(Auto)"
		else:
			if model in ("dm900", "dm920"):
				choices = [
					(pChoice("Edid(Auto)")),
					(pChoice("Hdmi_Rgb")),
					("Itu_R_BT_709", _("BT709")),
					("DVI_Full_Range_RGB", _("Full range RGB")),
					("FCC", _("FCC 1953")),
					("Itu_R_BT_470_2_BG", _("BT470 BG")),
					("Smpte_170M", _("SMPTE 170M")),
					("Smpte_240M", _("SMPTE 240M")),
					("Itu_R_BT_2020_NCL", _("BT2020 NCL")),
					("Itu_R_BT_2020_CL", _("BT2020 CL")),
					("XvYCC_709", _("BT709 XvYCC")),
					("XvYCC_601", _("BT601 XvYCC"))
				]
				default = "Edid(Auto)"
			else:
				choices = [
					(pChoice("auto")),
					(pChoice("rgb")),
					("420", "420"),
					("422", "422"),
					("444", "444")
				]
				default = "auto"

		def setHDMIColorspace(configElement):
			try:
				open("/proc/stb/video/hdmi_colorspace", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/video/hdmi_colorspace failed!")
		if isfile("/proc/stb/video/hdmi_colorspace_choices"):
			procfile = "/proc/stb/video/hdmi_colorspace_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.hdmicolorspace = ConfigSelection(choices=choices, default=default)
		config.av.hdmicolorspace.addNotifier(setHDMIColorspace)
	else:
		config.av.hdmicolorspace = ConfigNothing()

	if BoxInfo.getItem("HasColorimetry"):
		choices = [
			(pChoice("auto")),
			("bt2020ncl", _("BT2020 NCL")),
			("bt2020cl", _("BT2020 CL")),
			("bt709", _("BT709"))
		]
		default = "auto"

		def setHDMIColorimetry(configElement):
			try:
				open("/proc/stb/video/hdmi_colorimetry", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/video/hdmi_colorimetry failed!")
		if isfile("/proc/stb/video/hdmi_colorimetry_choices"):
			procfile = "/proc/stb/video/hdmi_colorimetry_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.hdmicolorimetry = ConfigSelection(choices=choices, default=default)
		config.av.hdmicolorimetry.addNotifier(setHDMIColorimetry)
	else:
		config.av.hdmicolorimetry = ConfigNothing()

	if BoxInfo.getItem("HasColordepth"):
		choices = [
			(pChoice("auto")),
			("8bit", _("8 bit")),
			("10bit", _("10 bit")),
			("12bit", _("12 bit"))
		]
		default = "auto"

		def setHdmiColordepth(configElement):
			try:
				open("/proc/stb/video/hdmi_colordepth", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/video/hdmi_colordepth failed!")
		if isfile("/proc/stb/video/hdmi_colordepth_choices"):
			procfile = "/proc/stb/video/hdmi_colordepth_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.hdmicolordepth = ConfigSelection(choices=choices, default=default)
		config.av.hdmicolordepth.addNotifier(setHdmiColordepth)
	else:
		config.av.hdmicolordepth = ConfigNothing()

	if BoxInfo.getItem("AmlHDRSupport"):
		def setAMLHDR10(configElement):
			try:
				open("/sys/class/amhdmitx/amhdmitx0/config", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /sys/class/amhdmitx/amhdmitx0/config failed!")
		config.av.amlhdr10_support = ConfigSelection(choices={
			"hdr10-0": _("Force enabled"),
			"hdr10-1": _("Force disabled"),
			"hdr10-2": _("Controlled by HDMI")
		}, default="hdr10-2")
		config.av.amlhdr10_support.addNotifier(setAMLHDR10)

		def setAMLHLG(configElement):
			try:
				open("/sys/class/amhdmitx/amhdmitx0/config", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /sys/class/amhdmitx/amhdmitx0/config failed!")
		config.av.amlhlg_support = ConfigSelection(choices={
			"hlg-0": _("Force enabled"),
			"hlg-1": _("Force disabled"),
			"hlg-2": _("Controlled by HDMI")
		}, default="hlg-2")
		config.av.amlhlg_support.addNotifier(setAMLHLG)
	else:
		config.av.amlhdr10_support = ConfigNothing()
		config.av.amlhlg_support = ConfigNothing()

	if BoxInfo.getItem("HasHdrType"):
		def setHdmiHdrType(configElement):
			try:
				open("/proc/stb/video/hdmi_hdrtype", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/video/hdmi_hdrtype failed!")
		config.av.hdmihdrtype = ConfigSelection(choices=[
			(pChoice("auto")),
			(pChoice("dolby")),
			("none", _("SDR")),
			(pChoice("hdr10")),
			(pChoice("hlg"))
		], default="auto")
		config.av.hdmihdrtype.addNotifier(setHdmiHdrType)
	else:
		config.av.hdmihdrtype = ConfigNothing()

	if BoxInfo.getItem("HasHDMIpreemphasis"):
		def setHDMIpreemphasis(configElement):
			try:
				open("/proc/stb/hdmi/preemphasis", "w").write("on" if configElement.value else "off")
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/hdmi/preemphasis failed!")
		config.av.hdmipreemphasis = ConfigYesNo(default=False)
		config.av.hdmipreemphasis.addNotifier(setHDMIpreemphasis)

	if BoxInfo.getItem("HDRSupport"):
		config.av.hlg_support = ConfigSelection(default="auto(EDID)", choices=[
			(pChoice("auto(EDID)")),
			("yes", _("Force enabled")),
			("no", _("Force disabled"))
		])

		def setHlgSupport(configElement):
			try:
				open("/proc/stb/hdmi/hlg_support", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/hdmi/hlg_support failed!")
		config.av.hlg_support.addNotifier(setHlgSupport)

		config.av.hdr10_support = ConfigSelection(default="auto(EDID)", choices=[
			(pChoice("auto(EDID)")),
			("yes", _("Force enabled")),
			("no", _("Force disabled"))
		])

		def setHdr10Support(configElement):
			try:
				open("/proc/stb/hdmi/hdr10_support", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/hdmi/hdr10_support failed!")
		config.av.hdr10_support.addNotifier(setHdr10Support)

		def setDisable12Bit(configElement):
			try:
				open("/proc/stb/video/disable_12bit", "w").write("1" if configElement.value else "0")
			except:
				print("[AVSwitch] Write to /proc/stb/video/disable_12bit failed!")
		config.av.allow_12bit = ConfigYesNo(default=False)
		config.av.allow_12bit.addNotifier(setDisable12Bit)

		def setDisable10Bit(configElement):
			try:
				open("/proc/stb/video/disable_10bit", "w").write("1" if configElement.value else "0")
			except:
				print("[AVSwitch] Write to /proc/stb/video/disable_10bit failed!")
		config.av.allow_10bit = ConfigYesNo(default=False)
		config.av.allow_10bit.addNotifier(setDisable10Bit)

	if BoxInfo.getItem("HDMIAudioSource"):
		if BoxInfo.getItem("AmlogicFamily"):
			choices = [
				("0", _("PCM")),
				("1", _("SPDIF")),
				("2", _("Bluetooth"))
			]
			default = "0"
		else:
			choices = [
				(pChoice("pcm")),
				(pChoice("spdif"))
			]
			default = "pcm"

		def setAudioSource(configElement):
			if BoxInfo.getItem("AmlogicFamily"):
				fileWriteLine("/sys/devices/virtual/amhdmitx/amhdmitx0/audio_source", configElement.value, source=MODULE_NAME)
			else:
				fileWriteLine("/proc/stb/hdmi/audio_source", configElement.value, source=MODULE_NAME)
		config.av.hdmi_audio_source = ConfigSelection(choices=choices, default=default)
		config.av.hdmi_audio_source.addNotifier(setAudioSource)
	else:
		config.av.hdmi_audio_source = ConfigNothing()

	if BoxInfo.getItem("CanSyncMode"):
		config.av.sync_mode = ConfigSelection(default="slow", choices={
			"slow": _("Slow motion"),
			"hold": _("Hold first frame"),
			"black": _("Black screen")
		})

		def setSyncMode(configElement):
			try:
				open("/proc/stb/video/sync_mode_choices", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/video/sync_mode_choices failed!")
		config.av.sync_mode.addNotifier(setSyncMode)
	else:
		config.av.sync_mode = ConfigNothing()

	if BoxInfo.getItem("HasMultichannelPCM"):
		def setPCMMultichannel(configElement):
			try:
				open("/proc/stb/audio/multichannel_pcm", "w").write(configElement.value and "enable" or "disable")
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/audio/multichannel_pcm failed!")
		config.av.multichannel_pcm = ConfigYesNo(default=False)
		config.av.multichannel_pcm.addNotifier(setPCMMultichannel)

	if BoxInfo.getItem("CanDownmixAC3"):
		default = "downmix"
		if BoxInfo.getItem("AmlogicFamily"):
			choices = [
				(pChoice("downmix")),
				(pChoice("passthrough")),
				(pChoice("hdmi_best"))
			]
		else:
			choices = [
				(pChoice("downmix")),
				(pChoice("passthrough"))
			]

		def setAC3Downmix(configElement):
			if BoxInfo.getItem("AmlogicFamily"):
				BoxInfo.setItem("CanPcmMultichannel", True)
				ac3proc = "/sys/class/audiodsp/digital_raw"
			else:
				ac3proc = "/proc/stb/audio/ac3"
			try:
				open(ac3proc, "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to %s failed!" % ac3proc)
			if BoxInfo.getItem("HasMultichannelPCM", False) and configElement.value == "passthrough":
				BoxInfo.setItem("CanPcmMultichannel", True)
			else:
				BoxInfo.setItem("CanPcmMultichannel", False)
				if BoxInfo.getItem("HasMultichannelPCM"):
					config.av.multichannel_pcm.setValue(False)
		if isfile("/proc/stb/audio/ac3_choices"):
			procfile = "/proc/stb/audio/ac3_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.downmix_ac3 = ConfigSelection(choices=choices, default=default)
		config.av.downmix_ac3.addNotifier(setAC3Downmix)

	if BoxInfo.getItem("CanDownmixAAC"):
		choices = [
			(pChoice("downmix")),
			(pChoice("passthrough"))
		]
		default = "downmix"

		def setAACDownmix(configElement):
			try:
				open("/proc/stb/audio/aac", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/aac failed!")
		if isfile("/proc/stb/audio/aac_choices"):
			procfile = "/proc/stb/audio/aac_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.downmix_aac = ConfigSelection(choices=choices, default=default)
		config.av.downmix_aac.addNotifier(setAACDownmix)

	if BoxInfo.getItem("CanDownmixAACPlus"):
		choices = [
			(pChoice("downmix")),
			(pChoice("passthrough")),
			(pChoice("multichannel")),
			(pChoice("force_ac3")),
			(pChoice("force_dts"))
		]
		default = "downmix"

		def setAACDownmixPlus(configElement):
			try:
				open("/proc/stb/audio/aacplus", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/aacplus failed!")
		if isfile("/proc/stb/audio/aacplus_choices"):
			procfile = "/proc/stb/audio/aacplus_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.downmix_aacplus = ConfigSelection(choices=choices, default=default)
		config.av.downmix_aacplus.addNotifier(setAACDownmixPlus)

	if BoxInfo.getItem("CanDownmixDTS"):
		choices = [
			(pChoice("downmix")),
			(pChoice("passthrough"))
		]
		default = "downmix"

		def setDTSDownmix(configElement):
			try:
				open("/proc/stb/audio/dts", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/dts failed!")
		if isfile("/proc/stb/audio/dts_choices"):
			procfile = "/proc/stb/audio/dts_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.downmix_dts = ConfigSelection(choices=choices, default=default)
		config.av.downmix_dts.addNotifier(setDTSDownmix)

	if BoxInfo.getItem("CanDTSHD"):
		if model not in ("dm7080", "dm820"):
			choices = [
				(pChoice("downmix")),
				(pChoice("force_dts")),
				(pChoice("use_hdmi_caps")),
				(pChoice("multichannel")),
				(pChoice("hdmi_best"))
			]
			default = "downmix"
		else:
			choices = [
				(pChoice("use_hdmi_caps")),
				(pChoice("force_dts"))
			]
			default = "use_hdmi_caps"

		def setDTSHD(configElement):
			try:
				open("/proc/stb/audio/dtshd", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/dtshd failed!")
		if isfile("/proc/stb/audio/dtshd_choices"):
			procfile = "/proc/stb/audio/dtshd_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.dtshd = ConfigSelection(choices=choices, default=default)
		config.av.dtshd.addNotifier(setDTSHD)

	if BoxInfo.getItem("CanAACTranscode"):
		choices = [
			(pChoice("off")),
			(pChoice("ac3")),
			(pChoice("dts"))
		]
		default = "off"

		def setAACTranscode(configElement):
			try:
				open("/proc/stb/audio/aac_transcode", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/aac_transcode failed!")
		if isfile("/proc/stb/audio/aac_transcode_choices"):
			procfile = "/proc/stb/audio/aac_transcode_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.transcodeaac = ConfigSelection(choices=choices, default=default)
		config.av.transcodeaac.addNotifier(setAACTranscode)
	else:
		config.av.transcodeaac = ConfigNothing()

	if BoxInfo.getItem("CanAC3plusTranscode"):
		if not BoxInfo.getItem("DreamBoxAudio"):
			choices = [
				("use_hdmi_caps", _("Controlled by HDMI")),
				("force_ac3", _("Convert to AC3"))
			]
			default = "force_ac3"
		elif BoxInfo.getItem("DreamBoxAudio"):
			choices = [
				("use_hdmi_caps", _("Controlled by HDMI")),
				("force_ac3", _("Convert to AC3")),
				("multichannel", _("Convert to multi-channel PCM")),
				("hdmi_best", _("Use best / Controlled by HDMI")),
				("force_ddp", _("Force AC3+"))
			]
			default = "force_ac3"
		else:
			choices = [
				("downmix", _("Downmix")),
				("passthrough", _("Passthrough")),
				("force_ac3", _("Convert to AC3")),
				("multichannel", _("Convert to multi-channel PCM")),
				("force_dts", _("Convert to DTS"))
			]
			default = "force_ac3"

		def setAC3plusTranscode(configElement):
			try:
				open("/proc/stb/audio/ac3plus", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/ac3plus failed!")
		if BoxInfo.getItem("CanProc"):
			with open("/proc/stb/audio/ac3plus_choices", "r") as ac3plus_choices:
				ac3plus_choices.read().split('\n', 1)[0]
				ac3plus_choices.close()
		config.av.transcodeac3plus = ConfigSelection(choices=choices, default=default)
		config.av.transcodeac3plus.addNotifier(setAC3plusTranscode)

	if BoxInfo.getItem("CanWMAPRO"):
		choices = [
			(pChoice("downmix")),
			(pChoice("passthrough")),
			(pChoice("multichannel")),
			(pChoice("hdmi_best"))
		]
		default = "downmix"

		def setWMAPRO(configElement):
			try:
				open("/proc/stb/audio/wmapro", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/audio/wmapro failed!")
		if isfile("/proc/stb/audio/wmapro_choices"):
			procfile = "/proc/stb/audio/wmapro_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.wmapro = ConfigSelection(choices=choices, default=default)
		config.av.wmapro.addNotifier(setWMAPRO)

	if BoxInfo.getItem("CanAudioDelay"):
		def setAudioDelay(configElement):
			try:
				open("/proc/stb/audio/audio_delay_pcm", "w").write(format(configElement.value * 90, "x"))
			except:
				open("/proc/stb/audio/audio_delay_bitstream", "w").write(format(configElement.value * 90, "x"))
		config.av.audiodelay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
		config.av.audiodelay.addNotifier(setAudioDelay)
	else:
		config.av.audiodelay = ConfigNothing()

	if BoxInfo.getItem("CanBTAudio"):
		choices = [
			(pChoice("off")),
			(pChoice("on"))
		]
		default = "off"

		def setBTAudio(configElement):
			try:
				open("/proc/stb/audio/btaudio", "w").write(configElement.value)
			except (IOError, OSError):
				print("[AVSwitch] Write to /proc/stb/audio/btaudio failed!")
		config.av.btaudio = ConfigSelection(choices=choices, default="off")
		config.av.btaudio.addNotifier(setBTAudio)
	else:
		config.av.btaudio = ConfigNothing()

	if BoxInfo.getItem("CanBTAudioDelay"):
		def setBTAudioDelay(configElement):
			try:
				open("/proc/stb/audio/btaudio_delay", "w").write(format(configElement.value * 90, "x"))
			except:
				open("/proc/stb/audio/btaudio_delay_pcm", "w").write(format(configElement.value * 90, "x"))
		config.av.btaudiodelay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
		config.av.btaudiodelay.addNotifier(setBTAudioDelay)
	else:
		config.av.btaudiodelay = ConfigNothing()

	if BoxInfo.getItem("Has3DSurround"):
		choices = [
			(pChoice("none")),
			(pChoice("hdmi")),
			(pChoice("spdif")),
			(pChoice("dac"))
		]
		default = "none"

		def set3DSurround(configElement):
			try:
				open("/proc/stb/audio/3d_surround", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/3d_surround failed!")
		if isfile("/proc/stb/audio/3d_surround_choices"):
			procfile = "/proc/stb/audio/3d_surround_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.surround_3d = ConfigSelection(choices=choices, default=default)
		config.av.surround_3d.addNotifier(set3DSurround)
	else:
		config.av.surround_3d = ConfigNothing()

	if BoxInfo.getItem("Has3DSpeaker"):
		choices = [
			(pChoice("center")),
			(pChoice("wide")),
			(pChoice("extrawide"))
		]
		default = "center"

		def set3DPosition(configElement):
			try:
				open("/proc/stb/audio/3d_surround_speaker_position", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/3d_surround_speaker_position failed!")
		if isfile("/proc/stb/audio/3d_surround_speaker_position_choices"):
			procfile = "/proc/stb/audio/3d_surround_speaker_position_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.speaker_3d = ConfigSelection(choices=choices, default=default)
		config.av.speaker_3d.addNotifier(set3DPosition)
	else:
		config.av.speaker_3d = ConfigNothing()

	if BoxInfo.getItem("Has3DSurroundSpeaker"):
		choices = [
			(pChoice("disabled")),
			(pChoice("center")),
			(pChoice("wide")),
			(pChoice("extrawide"))
		]
		default = "disabled"

		def set3DPositionDisable(configElement):
			try:
				open("/proc/stb/audio/3dsurround", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/3dsurround failed!")
		if isfile("/proc/stb/audio/3dsurround_choices"):
			procfile = "/proc/stb/audio/3dsurround_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.surround_3d_speaker = ConfigSelection(choices=choices, default=default)
		config.av.surround_3d_speaker.addNotifier(set3DPositionDisable)
	else:
		config.av.surround_3d_speaker = ConfigNothing()

	if BoxInfo.getItem("HasAutoVolume"):
		choices = [
			(pChoice("none")),
			(pChoice("hdmi")),
			(pChoice("spdif")),
			(pChoice("dac"))
		]
		default = "none"

		def setAutoVolume(configElement):
			try:
				open("/proc/stb/audio/avl", "w").write(configElement.value)
			except:
				print("[AVSwitch] Write to /proc/stb/audio/avl failed!")
		if isfile("/proc/stb/audio/avl_choices"):
			procfile = "/proc/stb/audio/avl_choices"
			(choices, default) = readChoices(procfile, choices, default)
		config.av.autovolume = ConfigSelection(choices=choices, default=default)
		config.av.autovolume.addNotifier(setAutoVolume)
	else:
		config.av.autovolume = ConfigNothing()

	if BoxInfo.getItem("HasAutoVolumeLevel"):
		def setAutoVolumeLevel(configElement):
			try:
				open("/proc/stb/audio/autovolumelevel_choices", "w").write("enabled" if configElement.value else "disabled")
			except:
				print("[AVSwitch] Write to /proc/stb/audio/autovolumelevel_choices failed!")
		config.av.autovolumelevel = ConfigYesNo(default=False)
		config.av.autovolumelevel.addNotifier(setAutoVolumeLevel)

	if BoxInfo.getItem("ScalerSharpness"):
		def setScaler_sharpness(config):
			myval = int(config.value)
			try:
				print("--> setting scaler_sharpness to: %0.8X" % myval)
				print("[AVSwitch] Write to /proc/stb/vmpeg/0/pep_scaler_sharpness")
				open("/proc/stb/vmpeg/0/pep_scaler_sharpness", "w").write("%0.8X" % myval)
				print("[AVSwitch] Write to /proc/stb/vmpeg/0/pep_apply")
				open("/proc/stb/vmpeg/0/pep_apply", "w").write("1")
			except IOError:
				print("[AVSwitch] Couldn't write pep_scaler_sharpness or pep_apply")
		config.av.scaler_sharpness = ConfigSlider(default=13, limits=(0, 26))
		config.av.scaler_sharpness.addNotifier(setScaler_sharpness)
	else:
		config.av.scaler_sharpness = NoSave(ConfigNothing())

	if BoxInfo.getItem("Has3DSurroundSoftLimiter"):
		def set3DSurroundSoftLimiter(configElement):
			try:
				open("/proc/stb/audio/3dsurround_softlimiter", "w").write(configElement.value and "enabled" or "disabled")
			except:
				print("[AVSwitch] Write to /proc/stb/audio/3dsurround_softlimiter failed!")
		config.av.surround_softlimiter_3d = ConfigYesNo(default=False)
		config.av.surround_softlimiter_3d.addNotifier(set3DSurroundSoftLimiter)

	config.av.force = ConfigSelection(default=None, choices=[
		(None, _("Do not force")),
		("50", _("Force 50Hz")),
		("60", _("Force 60Hz"))
	])

iAVSwitch = AVSwitch()
