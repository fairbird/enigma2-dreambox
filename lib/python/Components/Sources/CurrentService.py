# -*- coding: utf-8 -*-
from Components.PerServiceDisplay import PerServiceBase
from enigma import iPlayableService, iPlayableService, eServiceCenter
from Components.Sources.Source import Source
from Components.Element import cached
import NavigationInstance


class CurrentService(PerServiceBase, Source):
	def __init__(self, navcore):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evStart: self.serviceEvent,
				iPlayableService.evEnd: self.serviceEvent,
				# FIXME: we should check 'interesting_events'
				# which is not always provided.
				iPlayableService.evUpdatedInfo: self.serviceEvent,
				iPlayableService.evUpdatedEventInfo: self.serviceEvent,
				iPlayableService.evNewProgramInfo: self.serviceEvent,
				iPlayableService.evCuesheetChanged: self.serviceEvent,
				iPlayableService.evVideoSizeChanged: self.serviceEvent,
				iPlayableService.evVideoGammaChanged: self.serviceEvent,
				iPlayableService.evHBBTVInfo: self.serviceEvent
			}, with_event=True)
		self.navcore = navcore
		self.srv = None
		self.info = None
		self.ref = None
		self.onManualNewService = []

	def serviceEvent(self, event):
		self.srv = None
		self.info = None
		self.changed((self.CHANGED_SPECIFIC, event))

	@cached
	def getCurrentService(self):
		return self.srv or self.navcore.getCurrentService()

	def getCurrentServiceReference(self):
		return self.navcore.getCurrentlyPlayingServiceReference()

	service = property(getCurrentService)

	def getCurrentServiceWithFallback(self):
		return self.srv or self.navcore.getCurrentService()
	
	# this gets current service (set manually) with a fallback to the selected service from navigation.
	# Typically that is used in ServiceName convertor.
	servicealt = property(getCurrentServiceWithFallback)

	@cached
	def getCurrentServiceRef(self):
		if NavigationInstance.instance is not None:
			return self.srv or NavigationInstance.instance.getCurrentlyPlayingServiceOrGroup()
		return None

	# Setter added for iptv-m3u-reader plugin. For more info see:
	# https://github.com/DimitarCC/iptv-m3u-reader/commit/08d93986f0f00de6d0ff172abd0bb7b641921bda#diff-834f0679bc61d0427df924d74c20767d5b8fa62227d824361dd81555df6f6725R477-R482
	def setCurrentServiceRef(self, ref):
		self.ref = ref

	serviceref = property(getCurrentServiceRef, setCurrentServiceRef)

	def newService(self, ref):
		if ref and isinstance(ref, bool):
			self.srv = None
		elif ref:
			self.srv = ref
			self.info = eServiceCenter.getInstance().info(ref)
		else:
			self.srv = ref
			
		for x in self.onManualNewService:
			x()

		self.changed((self.CHANGED_SPECIFIC, iPlayableService.evStart))

	@cached
	def getCurrentBouquetName(self):
		if NavigationInstance.instance is not None:
			return NavigationInstance.instance.currentBouquetName
		return ""

	currentBouquetName = property(getCurrentBouquetName)

	def destroy(self):
		PerServiceBase.destroy(self)
		Source.destroy(self)
