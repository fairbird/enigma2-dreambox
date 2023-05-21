# -*- coding: utf-8 -*-
from Components.config import ConfigNumber, ConfigYesNo, ConfigSubsection, ConfigSelection, config


def InitRecordingConfig():
	config.recording = ConfigSubsection()
	# actually this is "recordings always have priority". "Yes" does mean: don't ask. The RecordTimer will ask when value is 0.
	config.recording.asktozap = ConfigYesNo(default=True)
	config.recording.margin_before = ConfigNumber(default=3)
	config.recording.margin_after = ConfigNumber(default=5)
	config.recording.debug = ConfigYesNo(default=False)
	config.recording.ascii_filenames = ConfigYesNo(default=False)
	config.recording.keep_timers = ConfigNumber(default=7)
	config.recording.filename_composition = ConfigSelection(default="standard", choices=[
		("standard", _("standard")),
		("event", _("Event name first")),
		("short", _("Short filenames")),
		("long", _("Long filenames"))])
	config.recording.always_ecm = ConfigYesNo(default=False)
	config.recording.never_decrypt = ConfigYesNo(default=False)
	config.recording.zap_record_service_in_standby = ConfigYesNo(default=False)
	config.recording.offline_decode_delay = ConfigNumber(default=1000)
	config.recording.timer_default_type = ConfigSelection(choices=[("zap", _("zap")), ("record", _("record")), ("zap+record", _("zap and record"))], default="record")
