# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Sources.StreamService import StreamServiceList
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from enigma import eStreamServer, getDesktop
from ServiceReference import ServiceReference
import socket
try:
	from Plugins.Extensions.OpenWebif.controllers.stream import streamList
except:
	streamList = []

def getDesktopSize():
	s = getDesktop(0).size()
	return (s.width(), s.height())

def isHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] == 1280


class StreamingClientsInfo(Screen):
	if isHD():
		skin = '''
			<screen name="StreamingClientsInfo" position="center,center" size="540,490" title="Streaming clients info">
				<widget name="menu" font="Regular;20" position="10,60" size="530,320" zPosition="1" />
				<widget name="info" position="10,60" size="530,22" font="Regular;20" horizontalAlignment="center" transparent="1" zPosition="2"/>
				<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphaTest="on"/>
				<ePixmap pixmap="buttons/green.png" position="135,0" size="140,40" alphaTest="on"/>
				<ePixmap pixmap="buttons/yellow.png" position="270,0" size="140,40" alphaTest="on"/>
				<ePixmap pixmap="buttons/blue.png" position="405,0" size="140,40" alphaTest="on"/>
				<widget name="key_red" position="0,0" zPosition="1" size="135,40" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#9f1313" transparent="1"/>
				<widget name="key_green" position="135,0" zPosition="1" size="135,40" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#1f771f" transparent="1"/>
				<widget name="key_yellow" position="270,0" zPosition="1" size="135,40" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#18188b" transparent="1"/>
			</screen>
		'''
	else:
		skin = '''
			<screen name="StreamingClientsInfo" position="center,center" size="850,900" title="Streaming clients info">
				<widget name="menu" font="Regular;28" itemHeight="40" position="10,135" size="830,756" zPosition="1" />
				<widget name="info" position="10,70" size="838,50" font="Regular;28" horizontalAlignment="center" transparent="1" zPosition="2"/>
				<ePixmap pixmap="buttons/red.png" position="0,0" size="200,50" alphaTest="on"/>
				<ePixmap pixmap="buttons/green.png" position="210,0" size="200,50" alphaTest="on"/>
				<ePixmap pixmap="buttons/yellow.png" position="425,0" size="200,50" alphaTest="on"/>
				<ePixmap pixmap="buttons/blue.png" position="650,0" size="200,50" alphaTest="on"/>
				<widget name="key_red" position="0,0" zPosition="1" size="200,50" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#9f1313" transparent="1"/>
				<widget name="key_green" position="210,0" zPosition="1" size="200,50" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#1f771f" transparent="1"/>
				<widget name="key_yellow" position="425,0" zPosition="1" size="200,50" font="Regular;28" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#18188b" transparent="1"/>
			</screen>
		'''

	def __init__(self, session):
		Screen.__init__(self, session)
		self.streamServer = eStreamServer.getInstance()
		self.clients = []
		self["menu"] = MenuList(self.clients)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["info"] = Label()
		self.updateClients()
		self["actions"] = ActionMap(["ColorActions", "SetupActions"],
		{
			"cancel": self.close,
			"ok": self.stopCurrentStream,
			"red": self.close,
			"green": self.stopAllStreams,
			"yellow": self.stopCurrentStream
		})

	def updateClients(self):
		self["key_green"].setText("")
		self["key_yellow"].setText("")
		self.setTitle(_("Streaming clients info"))
		self.clients = []
		if self.streamServer:
			for x in self.streamServer.getConnectedClients():
				service_name = ServiceReference(x[1]).getServiceName() or "(unknown service)"
				ip = x[0]
				if int(x[2]) == 0:
					strtype = "S"
				else:
					strtype = "T"
				try:
					raw = socket.gethostbyaddr(ip)
					ip = raw[0]
				except:
					pass
				info = ("%s %-8s %s") % (strtype, ip, service_name)
				self.clients.append((info, (x[0], x[1])))
		if StreamServiceList and streamList:
			for x in StreamServiceList:
				ip = "ip n/a"
				service_name = "(unknown service)"
				for stream in streamList:
					if hasattr(stream, 'getService') and stream.getService() and stream.getService().__deref__() == x:
						service_name = ServiceReference(stream.ref.toString()).getServiceName()
						ip = stream.clientIP or ip
				info = ("T %s %s %s") % (ip, service_name, _("(VU+ type)"))
				self.clients.append((info, (-1, x)))
		self["menu"].setList(self.clients)
		if self.clients:
			self["info"].setText("")
			self["key_green"].setText(_("Stop all streams"))
			self["key_yellow"].setText(_("Stop current stream"))
		else:
			self["info"].setText(_("No stream clients"))

	def stopCurrentStream(self):
		self.updateClients()
		if self.clients:
			client = self["menu"].l.getCurrentSelection()
			if client:
				self.session.openWithCallback(self.stopCurrentStreamCallback, MessageBox, client[0] + " \n\n" + _("Stop current stream") + "?", MessageBox.TYPE_YESNO)

	def stopCurrentStreamCallback(self, answer):
		if answer:
			client = self["menu"].l.getCurrentSelection()
			if client and client[1][0] != -1 and self.streamServer:
				for x in self.streamServer.getConnectedClients():
					if client[1][0] == x[0] and client[1][1] == x[1]:
						if not self.streamServer.stopStreamClient(client[1][0], client[1][1]):
							self.session.open(MessageBox, client[0] + " \n\n" + _("Error stop stream!"), MessageBox.TYPE_WARNING)
				self.updateClients()

	def stopAllStreams(self):
		self.updateClients()
		if self.clients:
			self.session.openWithCallback(self.stopAllStreamsCallback, MessageBox, _("Stop all streams") + "?", MessageBox.TYPE_YESNO)

	def stopAllStreamsCallback(self, answer):
		if answer:
			if self.streamServer:
				for x in self.streamServer.getConnectedClients():
					self.streamServer.stopStream()
			self.updateClients()
			if not self.clients:
				self.close()
