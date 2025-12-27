# -*- coding: utf-8 -*-
from os import W_OK, access, system
from time import sleep
from os.path import isfile
import os

from Components.config import config, ConfigSlider, ConfigSelection, ConfigYesNo, ConfigEnableDisable, ConfigOnOff, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, NoSave
from enigma import eAVSwitch, eAVControl, getDesktop
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileWriteLine, fileReadLine


iAVSwitch = None  # will be initialized later, allows to import name 'iAVSwitch' from 'Components.AVSwitch'

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
		if valstr in ("4_3_letterbox", "4_3_panscan"):  # 4:3
			return (4, 3)
		elif valstr == "16_9":  # auto ... 4:3 or 16:9
			if isfile("/proc/stb/vmpeg/0/aspect"):
				try:
					if "1" in open("/proc/stb/vmpeg/0/aspect", "r").read().split('\n', 1)[0]:  # 4:3
						return (4, 3)
				except IOError:
					print("[AVSwitch] Read /proc/stb/vmpeg/0/aspect failed!")
			elif isfile("/sys/class/video/screen_mode"):
				try:
					if "1" in open("/sys/class/video/screen_mode", "r").read().split('\n', 1)[0]:  # 4:3
						return (4, 3)
				except IOError:
					print("[AVSwitch] Read /sys/class/video/screen_mode failed!")
		elif valstr in ("16_9_always", "16_9_letterbox"):  # 16:9
			pass
		elif valstr in ("16_10_letterbox", "16_10_panscan"):  # 16:10
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
			value = 2  # auto(4:3_off)
		else:
			value = 1  # auto
		eAVSwitch.getInstance().setWSS(value)


def InitAVSwitch():
	config.av = ConfigSubsection()
	config.av.yuvenabled = ConfigBoolean(default=True)
	colorformat_choices = {"cvbs": "CVBS"}

	delayChoices = [(i, _("%d ms") % i) for i in list(range(0, 3000, 100))]  # noqa: F821
	config.av.passthrough_fix_long = ConfigSelection(choices=delayChoices, default=1200)
	config.av.passthrough_fix_short = ConfigSelection(choices=delayChoices, default=100)

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

	iAVSwitch.setInput("encoder")  # init on startup

	BoxInfo.setItem("ScartSwitch", eAVControl.getInstance().hasScartSwitch())

	if BoxInfo.getItem("HasBypassEdidChecking"):
		def setEDIDBypass(configElement):
			if configElement.value:
				value = "00000001" if configElement.value else "00000000"
				fileWriteLine("/proc/stb/hdmi/bypass_edid_checking", value, source=MODULE_NAME)

		config.av.bypass_edid_checking = ConfigYesNo(default=True)
		config.av.bypass_edid_checking.addNotifier(setEDIDBypass)
	else:
		config.av.bypass_edid_checking = ConfigNothing()

	if BoxInfo.getItem("HasColorspace"):
		def setHDMIColorspace(configElement):
			fileWriteLine("/proc/stb/video/hdmi_colorspace", configElement.value, source=MODULE_NAME)

		if model in ("dm900", "dm920"):
			default = "Edid(Auto)"
			choiceList = [
				("Edid(Auto)", _("Auto")),
				("Hdmi_Rgb", "RGB"),
				("Itu_R_BT_709", "BT.709"),
				("DVI_Full_Range_RGB", _("Full Range RGB")),
				("FCC", "FCC 1953"),
				("Itu_R_BT_470_2_BG", "BT.470 BG"),
				("Smpte_170M", "SMPTE 170M"),
				("Smpte_240M", "SMPTE 240M"),
				("Itu_R_BT_2020_NCL", "BT.2020 NCL"),
				("Itu_R_BT_2020_CL", "BT.2020 CL"),
				("XvYCC_709", "BT.709 XvYCC"),
				("XvYCC_601", "BT.601 XvYCC")
			]
		else:
			default = "auto"
			choiceList = [
				("auto", _("Auto")),
				("rgb", "RGB"),
				("420", "YCbCr 420"),
				("422", "YCbCr 422"),
				("444", "YCbCr 444")
			]
		config.av.hdmicolorspace = ConfigSelection(default=default, choices=choiceList)
		config.av.hdmicolorspace.addNotifier(setHDMIColorspace)
	else:
		config.av.hdmicolorspace = ConfigNothing()

	if BoxInfo.getItem("HasColorimetry"):
		def setHDMIColorimetry(configElement):
			sleep(0.1)
			fileWriteLine("/proc/stb/video/hdmi_colorimetry", configElement.value, source=MODULE_NAME)

		config.av.hdmicolorimetry = ConfigSelection(default="auto", choices=[
			("auto", _("Auto")),
			("bt2020ncl", "BT.2020 NCL"),
			("bt2020cl", "BT.2020 CL"),
			("bt709", "BT.709")
		])
		config.av.hdmicolorimetry.addNotifier(setHDMIColorimetry)
	else:
		config.av.hdmicolorimetry = ConfigNothing()

	if BoxInfo.getItem("HasColordepth"):
		def setColorDepth(configElement):
			fileWriteLine("/proc/stb/video/hdmi_colordepth", configElement.value, source=MODULE_NAME)

		config.av.hdmicolordepth = ConfigSelection(default="auto", choices=[
			("auto", _("Auto")),
			("8bit", _("8bit")),
			("10bit", _("10bit")),
			("12bit", _("12bit"))
		])
		config.av.hdmicolordepth.addNotifier(setColorDepth)
	else:
		config.av.hdmicolordepth = ConfigNothing()

	if BoxInfo.getItem("AmlHDRSupport"):
		def setAMLHDR10(configElement):
			fileWriteLine("/sys/class/amhdmitx/amhdmitx0/config", configElement.value, source=MODULE_NAME)

		def setAMLHLG(configElement):
			fileWriteLine("/sys/class/amhdmitx/amhdmitx0/config", configElement.value, source=MODULE_NAME)

		config.av.amlhdr10_support = ConfigSelection(default="hdr10-2", choices=[
			("hdr10-0", _("Force enabled")),
			("hdr10-1", _("Force disabled")),
			("hdr10-2", _("Controlled by HDMI"))
		])
		config.av.amlhdr10_support.addNotifier(setAMLHDR10)
		config.av.amlhlg_support = ConfigSelection(default="hlg-2", choices=[
			("hlg-0", _("Force enabled")),
			("hlg-1", _("Force disabled")),
			("hlg-2", _("Controlled by HDMI"))
		])
		config.av.amlhlg_support.addNotifier(setAMLHLG)
	else:
		config.av.amlhdr10_support = ConfigNothing()
		config.av.amlhlg_support = ConfigNothing()

	if BoxInfo.getItem("HasHdrType"):
		def setHDRType(configElement):
			fileWriteLine("/proc/stb/video/hdmi_hdrtype", configElement.value, source=MODULE_NAME)

		config.av.hdmihdrtype = ConfigSelection(default="auto", choices=[
			("auto", _("Auto")),
			("dolby", "Dolby Vision"),
			("none", "SDR"),
			("hdr10", "HDR10"),
			# ("hdr10+", "HDR10+"),
			("hlg", "HLG")
		])
		config.av.hdmihdrtype.addNotifier(setHDRType)
	else:
		config.av.hdmihdrtype = ConfigNothing()

	if BoxInfo.getItem("HasHDMIpreemphasis"):
		def setHDMIpreemphasis(configElement):
			fileWriteLine("/proc/stb/hdmi/preemphasis", "on" if configElement.value else "off", source=MODULE_NAME)
		config.av.hdmipreemphasis = ConfigYesNo(default=False)
		config.av.hdmipreemphasis.addNotifier(setHDMIpreemphasis)

	if BoxInfo.getItem("HDRSupport"):
		def setHlgSupport(configElement):
			fileWriteLine("/proc/stb/hdmi/hlg_support", configElement.value, source=MODULE_NAME)

		def setHdr10Support(configElement):
			fileWriteLine("/proc/stb/hdmi/hdr10_support", configElement.value, source=MODULE_NAME)

		def setDisable12Bit(configElement):
			fileWriteLine("/proc/stb/video/disable_12bit", "1" if configElement.value else "0", source=MODULE_NAME)

		def setDisable10Bit(configElement):
			fileWriteLine("/proc/stb/video/disable_10bit", "1" if configElement.value else "0", source=MODULE_NAME)

		config.av.hlg_support = ConfigSelection(default="auto(EDID)", choices=[
			("auto(EDID)", _("Controlled by HDMI")),
			("yes", _("Force enabled")),
			("no", _("Force disabled"))
		])
		config.av.hlg_support.addNotifier(setHlgSupport)
		config.av.hdr10_support = ConfigSelection(default="auto(EDID)", choices=[
			("auto(EDID)", _("Controlled by HDMI")),
			("yes", _("Force enabled")),
			("no", _("Force disabled"))
		])
		config.av.hdr10_support.addNotifier(setHdr10Support)
		config.av.allow_12bit = ConfigYesNo(default=False)
		config.av.allow_12bit.addNotifier(setDisable12Bit)
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
				("pcm", _("PCM")),
				("spdif", _("SPDIF"))
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
		def setSyncMode(configElement):
			fileWriteLine("/proc/stb/video/sync_mode", configElement.value, source=MODULE_NAME)

		config.av.sync_mode = ConfigSelection(default="slow", choices=[
			("slow", _("Slow Motion")),
			("hold", _("Hold First Frame")),
			("black", _("Black Screen")),
		])
		config.av.sync_mode.addNotifier(setSyncMode)
	else:
		config.av.sync_mode = ConfigNothing()

	multiChannel = access("/proc/stb/audio/multichannel_pcm", W_OK)
	if BoxInfo.getItem("HasMultichannelPCM"):
		def setPCMMultichannel(configElement):
			fileWriteLine("/proc/stb/audio/multichannel_pcm", configElement.value and "enable" or "disable", source=MODULE_NAME)

		config.av.pcm_multichannel = ConfigYesNo(default=False)
		config.av.pcm_multichannel.addNotifier(setPCMMultichannel)

	if BoxInfo.getItem("AmlogicFamily"):
		downmixAC3 = True
		BoxInfo.setItem("CanPcmMultichannel", True)
	else:
		downmixAC3 = fileReadLine("/proc/stb/audio/ac3_choices", default=None, source=MODULE_NAME)
		if downmixAC3:
			downmixAC3 = "downmix" in downmixAC3
		else:
			downmixAC3 = False
			BoxInfo.setItem("CanPcmMultichannel", False)
	if BoxInfo.getItem("CanDownmixAC3"):
		def setAC3Downmix(configElement):
			if BoxInfo.getItem("AmlogicFamily"):
				fileWriteLine("/sys/class/audiodsp/digital_raw", configElement.value, source=MODULE_NAME)
			else:
				value = configElement.value and "downmix" or "passthrough"
				if model in ("dm900", "dm920", "dm7080", "dm820", "dm520"):
					value = configElement.value
				fileWriteLine("/proc/stb/audio/ac3", value, source=MODULE_NAME)

			if BoxInfo.getItem("supportPcmMultichannel", False) and not configElement.value:
				BoxInfo.setItem("CanPcmMultichannel", True)
			else:
				BoxInfo.setItem("CanPcmMultichannel", False)
				if multiChannel:
					config.av.pcm_multichannel.setValue(False)

		if model in ("dm900", "dm920", "dm7080", "dm820", "dm520"):
			config.av.downmix_ac3 = ConfigSelection(default="downmix", choices=[
				("downmix", _("Downmix")),
				("passthrough", _("Pass-through")),
				("multichannel", _("Convert to multi-channel PCM")),
				("hdmi_best", _("Use best / Controlled by HDMI"))
			])
		elif model in ("dreamone", "dreamtwo"):
			config.av.downmix_ac3 = ConfigSelection(default="0", choices=[
				("0", _("Downmix")),
				("1", _("Pass-through")),
				("2", _("Use best / Controlled by HDMI"))
			])
		else:
			config.av.downmix_ac3 = ConfigYesNo(default=True)
		config.av.downmix_ac3.addNotifier(setAC3Downmix)
	else:
		config.av.downmix_ac3 = ConfigNothing()

	if BoxInfo.getItem("CanDownmixAAC"):
		def setAACDownmix(configElement):
			value = configElement.value if model in ("dm900", "dm920", "dm7080", "dm820", "dm520", "gbquad4k", "gbquad4kpro", "gbue4k", "gbx34k") else configElement.value and "downmix" or "passthrough"
			fileWriteLine("/proc/stb/audio/aac", value, source=MODULE_NAME)

		if model in ("dm900", "dm920", "dm7080", "dm820", "dm520"):
			config.av.downmix_aac = ConfigSelection(default="downmix", choices=[
				("downmix", _("Downmix")),
				("passthrough", _("Pass-through")),
				("multichannel", _("Convert to multi-channel PCM")),
				("hdmi_best", _("Use best / Controlled by HDMI"))
			])
		elif model in ("gbquad4k", "gbquad4kpro", "gbue4k", "gbx34k"):
			config.av.downmix_aac = ConfigSelection(default="downmix", choices=[
				("downmix", _("Downmix")),
				("passthrough", _("Pass-through")),
				("multichannel", _("Convert to multi-channel PCM")),
				("force_ac3", _("Convert to AC3")),
				("force_dts", _("Convert to DTS")),
				("use_hdmi_caps", _("Use best / Controlled by HDMI"))
			])
		else:
			config.av.downmix_aac = ConfigYesNo(default=True)
		config.av.downmix_aac.addNotifier(setAACDownmix)

	if BoxInfo.getItem("CanDownmixAACPlus"):
		def setAACDownmixPlus(configElement):
			fileWriteLine("/proc/stb/audio/aacplus", configElement.value, source=MODULE_NAME)

		config.av.downmix_aacplus = ConfigSelection(default="downmix", choices=[
			("downmix", _("Downmix")),
			("passthrough", _("Pass-through")),
			("multichannel", _("Convert to multi-channel PCM")),
			("force_ac3", _("Convert to AC3")),
			("force_dts", _("Convert to DTS"))
		])
		config.av.downmix_aacplus.addNotifier(setAACDownmixPlus)

	if BoxInfo.getItem("CanDownmixDTS"):
		def setDTSDownmix(configElement):
			fileWriteLine("/proc/stb/audio/dts", configElement.value and "downmix" or "passthrough", source=MODULE_NAME)

		config.av.downmix_dts = ConfigYesNo(default=True)
		config.av.downmix_dts.addNotifier(setDTSDownmix)

	if BoxInfo.getItem("CanDTSHD"):
		def setDTSHD(configElement):
			fileWriteLine("/proc/stb/audio/dtshd", configElement.value, source=MODULE_NAME)

		if model in ("dm7080", "dm820"):
			default = "use_hdmi_caps"
			choiceList = [
				("use_hdmi_caps", _("Controlled by HDMI")),
				("force_dts", _("Convert to DTS"))
			]
		else:
			default = "downmix"
			choiceList = [
				("downmix", _("Downmix")),
				("force_dts", _("Convert to DTS")),
				("use_hdmi_caps", _("Controlled by HDMI")),
				("multichannel", _("Convert to multi-channel PCM")),
				("hdmi_best", _("Use best / Controlled by HDMI"))
			]
		config.av.dtshd = ConfigSelection(default=default, choices=choiceList)
		config.av.dtshd.addNotifier(setDTSHD)

	if BoxInfo.getItem("CanAACTranscode"):
		def setAACTranscode(configElement):
			fileWriteLine("/proc/stb/audio/aac_transcode", configElement.value, source=MODULE_NAME)

		config.av.transcodeaac = ConfigSelection(default=default, choices=aacTranscode)
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
			fileWriteLine("/proc/stb/audio/ac3plus", configElement.value, source=MODULE_NAME)
		if BoxInfo.getItem("CanProc"):
			with open("/proc/stb/audio/ac3plus_choices", "r") as ac3plus_choices:
				ac3plus_choices.read().split('\n', 1)[0]
				ac3plus_choices.close()
		config.av.transcodeac3plus = ConfigSelection(choices=choices, default=default)
		config.av.transcodeac3plus.addNotifier(setAC3plusTranscode)

	if BoxInfo.getItem("CanWMAPRO"):
		def setWMAPro(configElement):
			fileWriteLine("/proc/stb/audio/wmapro", configElement.value, source=MODULE_NAME)

		config.av.wmapro = ConfigSelection(default="downmix", choices=[
			("downmix", _("Downmix")),
			("passthrough", _("Pass-through")),
			("multichannel", _("Convert to multi-channel PCM")),
			("hdmi_best", _("Use best / Controlled by HDMI"))
		])
		config.av.wmapro.addNotifier(setWMAPro)

	if BoxInfo.getItem("CanAudioDelay"):
		def setAudioDelay(configElement):
			try:
				fileWriteLine("/proc/stb/audio/audio_delay_pcm", format(configElement.value * 90, "x"), source=MODULE_NAME)
			except:
				fileWriteLine("/proc/stb/audio/audio_delay_bitstream", format(configElement.value * 90, "x"), source=MODULE_NAME)
		config.av.audiodelay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
		config.av.audiodelay.addNotifier(setAudioDelay)
	else:
		config.av.audiodelay = ConfigNothing()

	if BoxInfo.getItem("CanBTAudio"):
		def setBTAudio(configElement):
			fileWriteLine("/proc/stb/audio/btaudio", "on" if configElement.value else "off", source=MODULE_NAME)

		config.av.btaudio = ConfigOnOff(default=False)
		config.av.btaudio.addNotifier(setBTAudio)
	else:
		config.av.btaudio = ConfigNothing()

	if BoxInfo.getItem("CanBTAudioDelay"):
		def setBTAudioDelay(configElement):
			fileWriteLine("/proc/stb/audio/btaudio_delay", format(configElement.value * 90, "x"), source=MODULE_NAME)

		config.av.btaudiodelay = ConfigSelectionNumber(min=-1000, max=1000, stepwidth=5, default=0)
		config.av.btaudiodelay.addNotifier(setBTAudioDelay)
	else:
		config.av.btaudiodelay = ConfigNothing()

	if BoxInfo.getItem("Has3DSurround"):
		def set3DSurround(configElement):
			fileWriteLine("/proc/stb/audio/3d_surround", configElement.value, source=MODULE_NAME)

		config.av.surround_3d = ConfigSelection(default="none", choices=[
			("none", _("Off")),
			("hdmi", "HDMI"),
			("spdif", "S/PDIF"),
			("dac", "DAC")
		])
		config.av.surround_3d.addNotifier(set3DSurround)
	else:
		config.av.surround_3d = ConfigNothing()

	if BoxInfo.getItem("Has3DSpeaker"):
		def set3DSurroundSpeaker(configElement):
			fileWriteLine("/proc/stb/audio/3d_surround_speaker_position", configElement.value, source=MODULE_NAME)

		config.av.surround_3d_speaker = ConfigSelection(default="center", choices=[
			("center", _("Center")),
			("wide", _("Wide")),
			("extrawide", _("Extra wide"))
		])
		config.av.surround_3d_speaker.addNotifier(set3DSurroundSpeaker)
	else:
		config.av.surround_3d_speaker = ConfigNothing()

	if BoxInfo.getItem("Has3DSurroundSpeaker"):
		def set3DSurroundSpeaker(configElement):
			fileWriteLine("/proc/stb/audio/3d_surround_speaker_position", configElement.value, source=MODULE_NAME)

		config.av.surround_3d_speaker = ConfigSelection(default="center", choices=[
			("center", _("Center")),
			("wide", _("Wide")),
			("extrawide", _("Extra wide"))
		])
		config.av.surround_3d_speaker.addNotifier(set3DSurroundSpeaker)
	else:
		config.av.surround_3d_speaker = ConfigNothing()

	if BoxInfo.getItem("HasAutoVolume"):
		def setAutoVolume(configElement):
			fileWriteLine("/proc/stb/audio/avl", configElement.value, source=MODULE_NAME)

		config.av.autovolume = ConfigSelection(default="none", choices=[
			("none", _("Off")),
			("hdmi", "HDMI"),
			("spdif", "S/PDIF"),
			("dac", "DAC")
		])
		config.av.autovolume.addNotifier(setAutoVolume)
	else:
		config.av.autovolume = ConfigNothing()

	if BoxInfo.getItem("HasAutoVolumeLevel"):
		def setAutoVolumeLevel(configElement):
			fileWriteLine("/proc/stb/audio/autovolumelevel_choices", "enabled" if configElement.value else "disabled", source=MODULE_NAME)
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
