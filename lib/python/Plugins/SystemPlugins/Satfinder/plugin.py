# -*- coding: utf-8 -*-
from enigma import eDVBResourceManager, eDVBFrontendParametersSatellite, eDVBFrontendParametersTerrestrial, eTimer

from Screens.ScanSetup import ScanSetup, buildTerTransponder
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.Sources.FrontendStatus import FrontendStatus
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.config import config, ConfigSelection
from Components.SystemInfo import SystemInfo
from Components.TuneTest import Tuner
from Tools.Transponder import getChannelNumber, channel2frequency
from Tools.BoundFunction import boundFunction


class Satfinder(ScanSetup):
	"""Inherits StaticText [key_red] and [key_green] properties from ScanSetup"""

	def __init__(self, session):
		self.initcomplete = False
		service = session and session.nav.getCurrentService()
		feinfo = service and service.frontendInfo()
		self.frontendData = feinfo and feinfo.getAll(True)
		del feinfo
		del service

		self.typeOfTuningEntry = None
		self.systemEntry = None
		self.systemEntryATSC = None
		self.satfinderTunerEntry = None
		self.satEntry = None
		self.typeOfInputEntry = None
		self.DVB_TypeEntry = None
		self.systemEntryTerr = None
		self.preDefTransponderEntry = None
		self.preDefTransponderCableEntry = None
		self.preDefTransponderTerrEntry = None
		self.preDefTransponderAtscEntry = None
		self.frontend = None
		self.is_id_boolEntry = None
		self.t2mi_plp_id_boolEntry = None
		self.timer = eTimer()
		self.timer.callback.append(self.updateFrontendStatus)

		ScanSetup.__init__(self, session)
		self.setTitle(_("Signal finder"))
		self["Frontend"] = FrontendStatus(frontend_source=lambda: self.frontend, update_interval=100)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"save": self.keyGoScan,
			"ok": self.keyGoScan,
			"cancel": self.keyCancel,
		}, -3)

		self.initcomplete = True
		self.session.postScanService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.onClose.append(self.__onClose)
		self.onShow.append(self.prepareFrontend)

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
		return False

	def prepareFrontend(self):
		self.frontend = None
		if not self.openFrontend():
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					from Screens.InfoBar import InfoBar
					InfoBar.instance and hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()
					if not self.openFrontend():
						self.frontend = None # in normal case this should not happen
		self.tuner = Tuner(self.frontend)
		self.retune()

	def updateFrontendStatus(self):
		if self.frontend:
			dict = {}
			self.frontend.getFrontendStatus(dict)
			if dict["tuner_state"] == "FAILED" or dict["tuner_state"] == "LOSTLOCK":
				self.retune()
			else:
				self.timer.start(500, True)

	def __onClose(self):
		self.session.nav.playService(self.session.postScanService)

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur in (
					self.typeOfTuningEntry,
					self.systemEntry,
					self.typeOfInputEntry,
					self.systemEntryATSC,
					self.DVB_TypeEntry,
					self.systemEntryTerr,
					self.satEntry
					):  # update screen and retune
			self.createSetup()
			self.retune()

		elif cur == self.satfinderTunerEntry: # switching tuners, update screen, get frontend, and retune (in prepareFrontend())
			self.feid = int(self.satfinder_scan_nims.value)
			self.createSetup()
			self.prepareFrontend()
			if self.frontend is None:
				msg = _("Tuner not available.")
				if self.session.nav.RecordTimer.isRecording():
					msg += _("\nRecording in progress.")
				self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)

		elif cur in (self.preDefTransponderEntry, self.preDefTransponderCableEntry, self.preDefTransponderTerrEntry, self.preDefTransponderAtscEntry): # retune only
			self.retune()
		elif cur == self.is_id_boolEntry:
			if self.is_id_boolEntry[1].value:
				self.scan_sat.is_id.value = 0 if self.is_id_memory < 0 else self.is_id_memory
				self.scan_sat.pls_mode.value = self.pls_mode_memory
				self.scan_sat.pls_code.value = self.pls_code_memory
			else:
				self.is_id_memory = self.scan_sat.is_id.value
				self.pls_mode_memory = self.scan_sat.pls_mode.value
				self.pls_code_memory = self.scan_sat.pls_code.value
				self.scan_sat.is_id.value = eDVBFrontendParametersSatellite.No_Stream_Id_Filter
				self.scan_sat.pls_mode.value = eDVBFrontendParametersSatellite.PLS_Gold
				self.scan_sat.pls_code.value = eDVBFrontendParametersSatellite.PLS_Default_Gold_Code
			self.createSetup()
			self.retune()
		elif cur == self.t2mi_plp_id_boolEntry:
			if self.t2mi_plp_id_boolEntry[1].value:
				self.scan_sat.t2mi_plp_id.value = 0 if self.t2mi_plp_id_memory < 0 else self.t2mi_plp_id_memory
				self.scan_sat.t2mi_pid.value = self.t2mi_pid_memory
			else:
				self.t2mi_plp_id_memory = self.scan_sat.t2mi_plp_id.value
				self.t2mi_pid_memory = self.scan_sat.t2mi_pid.value
				self.scan_sat.t2mi_plp_id.value = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
				self.scan_sat.t2mi_pid.value = eDVBFrontendParametersSatellite.T2MI_Default_Pid
			self.createSetup()
			self.retune()

	def createSetup(self):
		self.list = []
		indent = "  "
		self.satfinderTunerEntry = (_("Tuner"), self.satfinder_scan_nims)
		self.list.append(self.satfinderTunerEntry)
		self.DVB_type = self.nim_type_dict[int(self.satfinder_scan_nims.value)]["selection"]
		self.DVB_TypeEntry = (_("DVB type"), self.DVB_type) # multitype?
		if len(self.nim_type_dict[int(self.satfinder_scan_nims.value)]["modes"]) > 1:
			self.list.append(self.DVB_TypeEntry)
		if self.DVB_type.value == "DVB-S":
			self.tuning_sat = self.scan_satselection[self.getSelectedSatIndex(self.feid)]
			self.satEntry = (_('Satellite'), self.tuning_sat)
			self.list.append(self.satEntry)
			self.typeOfTuningEntry = (_('Tune'), self.tuning_type)
			if len(nimmanager.getTransponders(int(self.tuning_sat.value), self.feid)) < 1: # Only offer 'predefined transponder' if some transponders exist
				self.tuning_type.value = "single_transponder"
			else:
				self.list.append(self.typeOfTuningEntry)

			nim = nimmanager.nim_slots[self.feid]

			if self.tuning_type.value == "single_transponder":
				if nim.canBeCompatible("DVB-S2"):
					self.systemEntry = (_('System'), self.scan_sat.system)
					self.list.append(self.systemEntry)
				else:
					# downgrade to dvb-s, in case a -s2 config was active
					self.scan_sat.system.value = eDVBFrontendParametersSatellite.System_DVB_S
				self.list.append((_('Frequency'), self.scan_sat.frequency))
				self.list.append((_('Polarization'), self.scan_sat.polarization))
				self.list.append((_('Symbol rate'), self.scan_sat.symbolrate))
				self.list.append((_('Inversion'), self.scan_sat.inversion))
				if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S:
					self.list.append((_("FEC"), self.scan_sat.fec))
				elif self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
					self.list.append((_("FEC"), self.scan_sat.fec_s2))
					self.modulationEntry = (_('Modulation'), self.scan_sat.modulation)
					self.list.append(self.modulationEntry)
					self.list.append((_('Roll-off'), self.scan_sat.rolloff))
					self.list.append((_('Pilot'), self.scan_sat.pilot))
					if nim.isMultistream():
						self.is_id_boolEntry = (_('Transport Stream Type'), self.scan_sat.is_id_bool)
						self.list.append(self.is_id_boolEntry)
						if self.scan_sat.is_id_bool.value:
							self.list.append(("%s%s" % (indent, _('Input Stream ID')), self.scan_sat.is_id))
							self.list.append(("%s%s" % (indent, _('PLS Mode')), self.scan_sat.pls_mode))
							self.list.append(("%s%s" % (indent, _('PLS Code')), self.scan_sat.pls_code))
					else:
						self.scan_sat.is_id.value = eDVBFrontendParametersSatellite.No_Stream_Id_Filter
						self.scan_sat.pls_mode.value = eDVBFrontendParametersSatellite.PLS_Gold
						self.scan_sat.pls_code.value = eDVBFrontendParametersSatellite.PLS_Default_Gold_Code
					if nim.isT2MI():
						self.t2mi_plp_id_boolEntry = (_('T2MI PLP'), self.scan_sat.t2mi_plp_id_bool)
						self.list.append(self.t2mi_plp_id_boolEntry)
						if self.scan_sat.t2mi_plp_id_bool.value:
							self.list.append(("%s%s" % (indent, _('T2MI PLP ID')), self.scan_sat.t2mi_plp_id))
							self.list.append(("%s%s" % (indent, _('T2MI PID')), self.scan_sat.t2mi_pid))
					else:
						self.scan_sat.t2mi_plp_id.value = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
						self.scan_sat.t2mi_pid.value = eDVBFrontendParametersSatellite.T2MI_Default_Pid
			elif self.tuning_type.value == "predefined_transponder":
				self.scan_nims.value = self.satfinder_scan_nims.value
				self.updatePreDefTransponders()
				self.preDefTransponderEntry = (_("Transponder"), self.preDefTransponders)
				self.list.append(self.preDefTransponderEntry)
		elif self.DVB_type.value == "DVB-C":
			self.typeOfTuningEntry = (_('Tune'), self.tuning_type)
			if config.Nims[self.feid].cable.scan_type.value != "provider" or len(nimmanager.getTranspondersCable(int(self.satfinder_scan_nims.value))) < 1: # only show 'predefined transponder' if in provider mode and transponders exist
				self.tuning_type.value = "single_transponder"
			else:
				self.list.append(self.typeOfTuningEntry)
			if self.tuning_type.value == "single_transponder":
				self.list.append((_("Frequency"), self.scan_cab.frequency))
				self.list.append((_("Inversion"), self.scan_cab.inversion))
				self.list.append((_("Symbol rate"), self.scan_cab.symbolrate))
				self.list.append((_("Modulation"), self.scan_cab.modulation))
				self.list.append((_("FEC"), self.scan_cab.fec))
			elif self.tuning_type.value == "predefined_transponder":
				self.scan_nims.value = self.satfinder_scan_nims.value
				self.predefinedCabTranspondersList()
				self.preDefTransponderCableEntry = (_("Transponder"), self.CableTransponders)
				self.list.append(self.preDefTransponderCableEntry)
		elif self.DVB_type.value == "DVB-T":
			self.typeOfTuningEntry = (_('Tune'), self.tuning_type)
			region = nimmanager.getTerrestrialDescription(int(self.satfinder_scan_nims.value))
			if len(nimmanager.getTranspondersTerrestrial(region)) < 1: # Only offer 'predefined transponder' if some transponders exist
				self.tuning_type.value = "single_transponder"
			else:
				self.list.append(self.typeOfTuningEntry)
			if self.tuning_type.value == "single_transponder":
				if nimmanager.nim_slots[int(self.satfinder_scan_nims.value)].canBeCompatible("DVB-T2"):
					self.systemEntryTerr = (_('System'), self.scan_ter.system)
					self.list.append(self.systemEntryTerr)
				else:
					self.scan_ter.system.value = eDVBFrontendParametersTerrestrial.System_DVB_T
				self.typeOfInputEntry = (_("Use frequency or channel"), self.scan_input_as)
				if self.ter_channel_input:
					self.list.append(self.typeOfInputEntry)
				else:
					self.scan_input_as.value = self.scan_input_as.choices[0]
				if self.ter_channel_input and self.scan_input_as.value == "channel":
					channel = getChannelNumber(self.scan_ter.frequency.floatint * 1000, self.ter_tnumber)
					if channel:
						self.scan_ter.channel.value = int(channel.replace("+", "").replace("-", ""))
					self.list.append((_("Channel"), self.scan_ter.channel))
				else:
					prev_val = self.scan_ter.frequency.floatint
					self.scan_ter.frequency.floatint = channel2frequency(self.scan_ter.channel.value, self.ter_tnumber) / 1000
					if self.scan_ter.frequency.floatint == 474000:
						self.scan_ter.frequency.floatint = prev_val
					self.list.append((_("Frequency"), self.scan_ter.frequency))
				self.list.append((_("Inversion"), self.scan_ter.inversion))
				self.list.append((_("Bandwidth"), self.scan_ter.bandwidth))
				self.list.append((_("Code rate HP"), self.scan_ter.fechigh))
				self.list.append((_("Code rate LP"), self.scan_ter.feclow))
				self.list.append((_("Modulation"), self.scan_ter.modulation))
				self.list.append((_("Transmission mode"), self.scan_ter.transmission))
				self.list.append((_("Guard interval"), self.scan_ter.guard))
				self.list.append((_("Hierarchy info"), self.scan_ter.hierarchy))
				if self.scan_ter.system.value == eDVBFrontendParametersTerrestrial.System_DVB_T2:
					self.list.append((_('PLP ID'), self.scan_ter.plp_id))
			elif self.tuning_type.value == "predefined_transponder":
				self.scan_nims.value = self.satfinder_scan_nims.value
				self.predefinedTerrTranspondersList()
				self.preDefTransponderTerrEntry = (_('Transponder'), self.TerrestrialTransponders)
				self.list.append(self.preDefTransponderTerrEntry)
		elif self.DVB_type.value == "ATSC":
			self.typeOfTuningEntry = (_('Tune'), self.tuning_type)
			if len(nimmanager.getTranspondersATSC(int(self.satfinder_scan_nims.value))) < 1: # only show 'predefined transponder' if transponders exist
				self.tuning_type.value = "single_transponder"
			else:
				self.list.append(self.typeOfTuningEntry)
			if self.tuning_type.value == "single_transponder":
				self.systemEntryATSC = (_("System"), self.scan_ats.system)
				self.list.append(self.systemEntryATSC)
				self.list.append((_("Frequency"), self.scan_ats.frequency))
				self.list.append((_("Inversion"), self.scan_ats.inversion))
				self.list.append((_("Modulation"), self.scan_ats.modulation))
			elif self.tuning_type.value == "predefined_transponder":
				#FIXME add region
				self.scan_nims.value = self.satfinder_scan_nims.value
				self.predefinedATSCTranspondersList()
				self.preDefTransponderAtscEntry = (_('Transponder'), self.ATSCTransponders)
				self.list.append(self.preDefTransponderAtscEntry)
		self["config"].list = self.list

	def createConfig(self, foo):
		self.tuning_type = ConfigSelection(default="predefined_transponder", choices=[("single_transponder", _("User defined transponder")), ("predefined_transponder", _("Predefined transponder"))])
		self.orbital_position = 192
		if self.frontendData and 'orbital_position' in self.frontendData:
			self.orbital_position = self.frontendData['orbital_position']
		ScanSetup.createConfig(self, self.frontendData)

		# The following are updated in self.newConfig(). Do not add here.
		# self.scan_sat.system, self.tuning_type, self.scan_input_as, self.scan_ats.system, self.DVB_type, self.scan_ter.system, self.satfinder_scan_nims, self.tuning_sat
		for x in (self.scan_sat.frequency,
			self.scan_sat.inversion, self.scan_sat.symbolrate,
			self.scan_sat.polarization, self.scan_sat.fec, self.scan_sat.pilot,
			self.scan_sat.fec_s2, self.scan_sat.fec, self.scan_sat.modulation,
			self.scan_sat.rolloff,
			self.scan_sat.is_id, self.scan_sat.pls_mode, self.scan_sat.pls_code,
			self.scan_sat.t2mi_plp_id, self.scan_sat.t2mi_pid,
			self.scan_ter.channel, self.scan_ter.frequency, self.scan_ter.inversion,
			self.scan_ter.bandwidth, self.scan_ter.fechigh, self.scan_ter.feclow,
			self.scan_ter.modulation, self.scan_ter.transmission,
			self.scan_ter.guard, self.scan_ter.hierarchy, self.scan_ter.plp_id,
			self.scan_cab.frequency, self.scan_cab.inversion, self.scan_cab.symbolrate,
			self.scan_cab.modulation, self.scan_cab.fec,
			self.scan_ats.frequency, self.scan_ats.modulation, self.scan_ats.inversion):
			x.addNotifier(self.retune, initial_call=False)

		satfinder_nim_list = []
		for n in nimmanager.nim_slots:
			if not any([n.isCompatible(x) for x in ("DVB-S", "DVB-T", "DVB-C", "ATSC")]):
				continue
			if n.config_mode in ("loopthrough", "satposdepends", "nothing"):
				continue
			if n.isCompatible("DVB-S") and n.config_mode in ("simple", "equal", "advanced") and len(nimmanager.getSatListForNim(n.slot)) < 1:
				continue
			satfinder_nim_list.append((str(n.slot), n.friendly_full_description))
		self.satfinder_scan_nims = ConfigSelection(choices=satfinder_nim_list)
		if self.frontendData is not None and len(satfinder_nim_list) > 0: # open the plugin with the currently active NIM as default
			self.satfinder_scan_nims.setValue(str(self.frontendData.get("tuner_number", satfinder_nim_list[0][0])))

		self.feid = int(self.satfinder_scan_nims.value)

		self.satList = []
		self.scan_satselection = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
				self.scan_satselection.append(getConfigSatlist(self.orbital_position, self.satList[slot.slot]))
			else:
				self.satList.append(None)

		if self.frontendData:
			ttype = self.frontendData.get("tuner_type", "UNKNOWN")
			if ttype == "DVB-S" and self.predefinedTranspondersList(self.getSelectedSatIndex(self.feid)) is None and len(nimmanager.getTransponders(self.getSelectedSatIndex(self.feid), self.feid)) > 0:
				self.tuning_type.value = "single_transponder"
			elif ttype == "DVB-T" and self.predefinedTerrTranspondersList() is None and len(nimmanager.getTranspondersTerrestrial(nimmanager.getTerrestrialDescription(self.feid))) > 0:
				self.tuning_type.value = "single_transponder"
			elif ttype == "DVB-C" and self.predefinedCabTranspondersList() is None and len(nimmanager.getTranspondersCable(self.feid)) > 0:
				self.tuning_type.value = "single_transponder"
			elif ttype == "ATSC" and self.predefinedATSCTranspondersList() is None and len(nimmanager.getTranspondersATSC(self.feid)) > 0:
				self.tuning_type.value = "single_transponder"

	def getSelectedSatIndex(self, v):
		index = 0
		none_cnt = 0
		for n in self.satList:
			if self.satList[index] is None:
				none_cnt += 1
			if index == int(v):
				return index - none_cnt
			index += 1
		return -1

	def updatePreDefTransponders(self):
		ScanSetup.predefinedTranspondersList(self, self.tuning_sat.orbital_position)

	def retuneCab(self):
		if not self.initcomplete:
			return
		if self.tuning_type.value == "single_transponder":
			transponder = (
				self.scan_cab.frequency.floatint,
				self.scan_cab.symbolrate.value * 1000,
				self.scan_cab.modulation.value,
				self.scan_cab.fec.value,
				self.scan_cab.inversion.value
			)
			self.tuner.tuneCab(transponder)
			self.transponder = transponder
		elif self.tuning_type.value == "predefined_transponder":
			tps = nimmanager.getTranspondersCable(int(self.satfinder_scan_nims.value))
			if len(tps) > self.CableTransponders.index:
				tp = tps[self.CableTransponders.index]
				# tp = 0 transponder type, 1 freq, 2 sym, 3 mod, 4 fec, 5 inv, 6 sys
				transponder = (tp[1], tp[2], tp[3], tp[4], tp[5])
				self.tuner.tuneCab(transponder)
				self.transponder = transponder

	def retuneTerr(self):
		if not self.initcomplete:
			return
		if self.scan_input_as.value == "channel":
			frequency = channel2frequency(self.scan_ter.channel.value, self.ter_tnumber)
		else:
			frequency = self.scan_ter.frequency.floatint * 1000
		if self.tuning_type.value == "single_transponder":
			transponder = [
				2, #TERRESTRIAL
				frequency,
				self.scan_ter.bandwidth.value,
				self.scan_ter.modulation.value,
				self.scan_ter.fechigh.value,
				self.scan_ter.feclow.value,
				self.scan_ter.guard.value,
				self.scan_ter.transmission.value,
				self.scan_ter.hierarchy.value,
				self.scan_ter.inversion.value,
				self.scan_ter.system.value,
				self.scan_ter.plp_id.value]
			self.tuner.tuneTerr(transponder[1], transponder[9], transponder[2], transponder[4], transponder[5], transponder[3], transponder[7], transponder[6], transponder[8], transponder[10], transponder[11])
			self.transponder = transponder
		elif self.tuning_type.value == "predefined_transponder":
			region = nimmanager.getTerrestrialDescription(int(self.satfinder_scan_nims.value))
			tps = nimmanager.getTranspondersTerrestrial(region)
			if len(tps) > self.TerrestrialTransponders.index:
				transponder = tps[self.TerrestrialTransponders.index]
				# frequency 1, inversion 9, bandwidth 2, fechigh 4, feclow 5, modulation 3, transmission 7, guard 6, hierarchy 8, system 10, plp_id 11
				self.tuner.tuneTerr(transponder[1], transponder[9], transponder[2], transponder[4], transponder[5], transponder[3], transponder[7], transponder[6], transponder[8], transponder[10], transponder[11])
				self.transponder = transponder

	def retuneATSC(self):
		if not self.initcomplete:
			return
		if self.tuning_type.value == "single_transponder":
			transponder = (
				self.scan_ats.frequency.floatint * 1000,
				self.scan_ats.modulation.value,
				self.scan_ats.inversion.value,
				self.scan_ats.system.value,
			)
			self.tuner.tuneATSC(transponder)
			self.transponder = transponder
		elif self.tuning_type.value == "predefined_transponder":
			tps = nimmanager.getTranspondersATSC(int(self.satfinder_scan_nims.value))
			if tps and len(tps) > self.ATSCTransponders.index:
				tp = tps[self.ATSCTransponders.index]
				transponder = (tp[1], tp[2], tp[3], tp[4])
				self.tuner.tuneATSC(transponder)
				self.transponder = transponder

	def retuneSat(self): #satellite
		if not self.tuning_sat.value:
			return
		satpos = int(self.tuning_sat.value)
		if self.tuning_type.value == "single_transponder":
			if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
				fec = self.scan_sat.fec_s2.value
			else:
				fec = self.scan_sat.fec.value
			transponder = (
				self.scan_sat.frequency.value,
				self.scan_sat.symbolrate.value,
				self.scan_sat.polarization.value,
				fec,
				self.scan_sat.inversion.value,
				satpos,
				self.scan_sat.system.value,
				self.scan_sat.modulation.value,
				self.scan_sat.rolloff.value,
				self.scan_sat.pilot.value,
				self.scan_sat.is_id.value,
				self.scan_sat.pls_mode.value,
				self.scan_sat.pls_code.value,
				self.scan_sat.t2mi_plp_id.value,
				self.scan_sat.t2mi_pid.value)
			if self.initcomplete:
				self.tuner.tune(transponder)
			self.transponder = transponder
		elif self.tuning_type.value == "predefined_transponder":
			tps = nimmanager.getTransponders(satpos, int(self.satfinder_scan_nims.value))
			if len(tps) > self.preDefTransponders.index:
				tp = tps[self.preDefTransponders.index]
				transponder = (tp[1] // 1000, tp[2] // 1000,
					tp[3], tp[4], 2, satpos, tp[5], tp[6], tp[8], tp[9], tp[10], tp[11], tp[12], tp[13], tp[14])
				if self.initcomplete:
					self.tuner.tune(transponder)
				self.transponder = transponder

	def retune(self, configElement=None):
		if self.DVB_type.value == "DVB-S":
			self.retuneSat()
		elif self.DVB_type.value == "DVB-T":
			self.retuneTerr()
		elif self.DVB_type.value == "DVB-C":
			self.retuneCab()
		elif self.DVB_type.value == "ATSC":
			self.retuneATSC()
		self.timer.start(500, True)

	def keyGoScan(self):
		self.frontend = None
		if self.raw_channel:
			del(self.raw_channel)
		tlist = []
		if self.DVB_type.value == "DVB-S":
			self.addSatTransponder(tlist,
				self.transponder[0], # frequency
				self.transponder[1], # sr
				self.transponder[2], # pol
				self.transponder[3], # fec
				self.transponder[4], # inversion
				self.tuning_sat.orbital_position,
				self.transponder[6], # system
				self.transponder[7], # modulation
				self.transponder[8], # rolloff
				self.transponder[9], # pilot
				self.transponder[10],# input stream id
				self.transponder[11],# pls mode
				self.transponder[12],# pls code
				self.transponder[13],# t2mi_plp_id
				self.transponder[14] # t2mi_pid
			)
		elif self.DVB_type.value == "DVB-T":
			parm = buildTerTransponder(
				self.transponder[1],  # frequency
				self.transponder[9],  # inversion
				self.transponder[2],  # bandwidth
				self.transponder[4],  # fechigh
				self.transponder[5],  # feclow
				self.transponder[3],  # modulation
				self.transponder[7],  # transmission
				self.transponder[6],  # guard
				self.transponder[8],  # hierarchy
				self.transponder[10], # system
				self.transponder[11]  # plp_id
			)
			tlist.append(parm)
		elif self.DVB_type.value == "DVB-C":
			self.addCabTransponder(tlist,
				self.transponder[0], # frequency
				self.transponder[1], # sr
				self.transponder[2], # modulation
				self.transponder[3], # fec_inner
				self.transponder[4]  # inversion
			)
		elif self.DVB_type.value == "ATSC":
			self.addATSCTransponder(tlist,
				self.transponder[0], # frequency
				self.transponder[1], # modulation
				self.transponder[2], # inversion
				self.transponder[3]  # system
			)
		self.startScan(tlist, self.feid)

	def startScan(self, tlist, feid):
		flags = 0
		networkid = 0
		self.session.openWithCallback(self.startScanCallback, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])

	def startScanCallback(self, answer=None):
		if answer:
			self.doCloseRecursive()

	def keyCancel(self):
		if self.session.postScanService and self.frontend:
			self.frontend = None
			del self.raw_channel
		self.close(False)

	def doCloseRecursive(self):
		if self.session.postScanService and self.frontend:
			self.frontend = None
			del self.raw_channel
		self.close(True)


def SatfinderCallback(close, answer):
	if close and answer:
		close(True)


def SatfinderMain(session, close=None, **kwargs):
	nims = nimmanager.nim_slots
	nimList = []
	for n in nims:
		if not any([n.isCompatible(x) for x in ("DVB-S", "DVB-T", "DVB-C", "ATSC")]):
			continue
		if n.config_mode in ("loopthrough", "satposdepends", "nothing"):
			continue
		if n.isCompatible("DVB-S") and n.config_mode in ("advanced", "simple") and len(nimmanager.getSatListForNim(n.slot)) < 1 and len(n.getTunerTypesEnabled()) < 2:
			continue
		nimList.append(n)

	if len(nimList) == 0:
		session.open(MessageBox, _("No satellite, terrestrial or cable tuner is configured. Please check your tuner setup."), MessageBox.TYPE_ERROR)
	else:
		session.openWithCallback(boundFunction(SatfinderCallback, close), Satfinder)


def SatfinderStart(menuid, **kwargs):
	if menuid == "scan" and nimmanager.somethingConnected():
		return [(_("Signal finder"), SatfinderMain, "satfinder", None)]
	else:
		return []


def Plugins(**kwargs):
	if any([nimmanager.hasNimType(x) for x in ("DVB-S", "DVB-T", "DVB-C", "ATSC")]):
		return PluginDescriptor(name=_("Signal finder"), description=_("Helps setting up your antenna"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=SatfinderStart)
	else:
		return []
