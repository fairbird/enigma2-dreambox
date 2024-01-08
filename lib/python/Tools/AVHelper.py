# -*- coding: utf-8 -*-

def pChoice(node):
	return node, pnD.get(node, node)


# dictionary ... "proc_node_name" : _("human translatable texts"),
pnD = {
	"ac3": _("AC3"),
	"auto": _("Auto"),
	"auto(EDID)": _("Controlled by HDMI"),
	"center": _("Center"),
	"dac": _("DAC"),
	"dolby": _("Dolby"),
	"dts": _("DTS"),
	"downmix": _("Downmix"),
	"disabled": _("Off"),
	"Edid(Auto)": _("Auto"),
	"enabled": _("On"),
	"extrawide": _("Extra Wide"),
	"force_ac3": _("Convert to AC3"),
	"force_ddp": _("Convert to AC3+"),
	"force_dts": _("Convert to DTS"),
	"hdmi": _("HDMI"),
	"hdmi_best": _("Use best / Controlled by HDMI"),
	"Hdmi_Rgb": _("RGB"),
	"hdr10": _("HDR10"),
	"hlg": _("HLG"),
	"multichannel": _("Convert to multi-channel PCM"),
	"none": _("Off"),
	"off": _("Off"),
	"on": _("On"),
	"passthrough": _("Passthrough"),
	"pcm": _("PCM"),
	"rgb": _("RGB"),
	"spdif": _("SPDIF"),
	"use_hdmi_cacenter": _("Use HDMI cacenter"),
	"use_hdmi_caps": _("Controlled by HDMI"),
	"wide": _("Wide"),
}


def readChoices(procx, choices, default):
	try:
		with open(procx, "r") as myfile:
			procChoices = myfile.read().strip()
	except:
		procChoices = ""
	if procChoices:
		choiceslist = procChoices.split(" ")
		choices = [(pChoice(item)) for item in choiceslist]
		default = choiceslist[0]
	return (choices, default)
