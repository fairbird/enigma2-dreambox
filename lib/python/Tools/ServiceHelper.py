# -*- coding: utf-8 -*-
from twisted.internet.reactor import callInThread
from enigma import eTimer

class ServiceHelper:
	def __init__(self, *args, **kwargs):
		self.callbackTimer = eTimer()
		self.callbackTimer_conn = self.callbackTimer.timeout.get().append(self._closeSocket)
		self.callback = None

	def _action(self, action):
		self._waitSocket()

	def restart(self, callback, timeout=5000):
		self.callback = callback
		self.timeout = timeout
		self._action("RESTART")

	def start(self, callback, timeout=5000):
		self.callback = callback
		self.timeout = timeout
		self._action("START")

	def stop(self, callback, timeout=5000):
		self.callback = callback
		self.timeout = timeout
		self._action("STOP")

	def _waitSocket(self):
		self.callbackTimer.start(self.timeout, True)
		callInThread(self._listenSocket)

	def _listenSocket(self):
		from Components.Network import iNetwork
		iNetwork.restartNetwork(self._onNetworkRestarted)

	def _onNetworkRestarted(self, data=None):
		self._closeSocket()

	def _closeSocket(self):
		self.callbackTimer.stop()
		if self.callback:
			callback = self.callback
			self.callback = None
			callback()
