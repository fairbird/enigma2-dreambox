# -*- coding: utf-8 -*-
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileReadLine

MODULE_NAME = __name__.split(".")[-1]
hw_info = None


class HardwareInfo:
	device_name = "Unavailable"
	device_version = ""
	device_revision = ""
	device_model = None
	device_brandname = None
	device_hdmi = True

	def __init__(self):
		global hw_info
		if hw_info:
			return
		hw_info = self

		# Version
		self.device_version = fileReadLine("/proc/stb/info/version", "", source=MODULE_NAME).strip()
		# Revision
		self.device_revision = fileReadLine("/proc/stb/info/board_revision", "", source=MODULE_NAME).strip()
		# Name ... bit odd, but history prevails
		self.device_name = fileReadLine("/proc/stb/info/model", "", source=MODULE_NAME).strip()

		# standard values
		self.machine_name = BoxInfo.getItem("machinebuild") # This contains the value where the image is buld from
		self.device_model = BoxInfo.getItem("model") # This may contain more information about the specific model
		self.device_brandname = BoxInfo.getItem("brand")
		self.device_hw = BoxInfo.getItem("displaymodel")

		if self.device_revision:
			self.device_string = "%s (%s-%s)" % (self.device_hw, self.device_revision, self.device_version)
		elif self.device_version:
			self.device_string = "%s (%s)" % (self.device_hw, self.device_version)
		else:
			self.device_string = self.device_hw
		if BoxInfo.getItem("DreamBoxDVI"):
			self.device_hdmi = False  # Only dm800 and dm8000 do not have HDMI hardware.
		print("[HardwareInfo] Detected: '%s'." % self.get_device_string())

	def get_device_name(self):
		return hw_info.device_name

	def get_device_model(self):
		return hw_info.device_model

	def get_device_version(self):
		return hw_info.device_version

	def get_device_revision(self):
		return hw_info.device_revision

	def get_device_string(self):
		return hw_info.device_string

	def get_machine_name(self):
		return hw_info.machine_name

	def has_hdmi(self):
		return hw_info.device_hdmi
