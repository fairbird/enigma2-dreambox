# -*- coding: utf-8 -*-
from os import listdir, remove
from os.path import basename, dirname, join
from re import match
from shutil import move, rmtree
from tempfile import mkdtemp
from threading import Thread, enumerate as tenumerate
from base64 import encodebytes
from json import loads
from time import sleep
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from json import loads
from Components.config import config
from Screens.MessageBox import MessageBox
from Tools.Notifications import AddNotificationWithID


class ImportChannels:

	def __init__(self):
		self.e2path = "/etc/enigma2"
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback.value and not "ChannelsImport" in [x.name for x in tenumerate()]:
			self.header = None
			if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback_import_url.value != "same" and config.usage.remote_fallback_import_url.value:
				self.url = config.usage.remote_fallback_import_url.value.rsplit(":", 1)[0]
			else:
				self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
			if config.usage.remote_fallback_openwebif_customize.value:
				self.url = f"{self.url}:{config.usage.remote_fallback_openwebif_port.value}"
				if config.usage.remote_fallback_openwebif_userid.value and config.usage.remote_fallback_openwebif_password.value:
					self.header = "Basic %s" % encodebytes(("%s:%s" % (config.usage.remote_fallback_openwebif_userid.value, config.usage.remote_fallback_openwebif_password.value)).encode("UTF-8")).strip().decode()
			self.remote_fallback_import = config.usage.remote_fallback_import.value
			self.thread = Thread(target=self.threaded_function, name="ChannelsImport")
			self.settings = {}
			self.thread.start()

	def getUrl(self, url, timeout=5):
		while True:
			request = Request(url)
			if self.header:
				request.add_header("Authorization", self.header)
			try:
				return urlopen(request, timeout=timeout).read()
			except URLError as e:
				if "[Errno -3]" in str(e.reason):
					print(f"[Import Channels] Network is not up yet while fetching {url} retry in 5 seconds")
					sleep(5)
				else:
					print(f"[Import Channels] URLError {e} while fetching {url}")
					return {}

	def getFallbackSettingsValue(self, url, e2settingname):
		if url not in self.settings:
			result = self.getUrl(f"{url}/api/settings")
			if result:
				self.settings['url'] = loads(result.decode('utf-8'))
		if 'url' in self.settings and 'result' in self.settings['url'] and self.settings['url']['result'] == True:
				for key, value in self.settings['url']['settings']:
					if key.endswith(e2settingname): #use the config key when the endpart but also the whole part matches
		return ""

	def getTerrestrialUrl(self):
		url = config.usage.remote_fallback_dvb_t.value
		return url[:url.rfind(":")] if url else self.url

	def getTerrestrialRegion(self):
		descr = self.getFallbackSettingsValue(self.getTerrestrialUrl(), ".terrestrial")
		description = ""
		if "Europe" in descr:
			description = "fallback DVB-T/T2 Europe"
		if "Australia" in descr:
			description = "fallback DVB-T/T2 Australia"
		config.usage.remote_fallback_dvbt_region.value = description

	"""
	Enumerate all the files that make up the bouquet system, either local or on a remote machine
	"""

	def ImportGetFilelist(self, remote=False, radio=False, *files):
		result = []
		for file in files:
			# read the contents of the file
			try:
				if remote:
					try:
						content = self.getUrl(f"{self.url}/file?file={self.e2path}/{quote(file)}").decode('utf-8', 'replace').split('\n')
					except Exception as e:
						print(f"[Import Channels] Exception: {str(e)}")
						continue
				else:
					with open(f"{self.e2path}/{file}", "r") as f:
						content = f.readlines()
			except Exception as e:
				# for the moment just log and ignore
				print(f"[Import Channels] {str(e)}")
				continue

			# check the contents for more bouquet files
			for line in content:
				print (f"[Import Channels] {line}")
				# check if it contains another bouquet reference, first tv type then radio type
				r = match('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "(.*)" ORDER BY bouquet', line) or match('#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "(.*)" ORDER BY bouquet', line)
				if r:
					# recurse
					result.extend(self.ImportGetFilelist(remote, r.group(1)))

			# add add the file itself
			result.append(file)

		# return the file list
		return result

	def threaded_function(self):
		self.tmp_dir = mkdtemp(prefix="ImportChannels_")

		if "channels" in self.remote_fallback_import:
			print("[Import Channels] Enumerate remote files")
			files = self.ImportGetFilelist(True, 'bouquets.tv', 'bouquets.radio')

			print("[Import Channels] Enumerate remote support files")
			for file in loads(self.getUrl(f"{self.url}/file?dir={self.e2path}"))["files"]:
				if os.path.basename(file).startswith(supportfiles):
					files.append(file.replace(self.e2path, ''))

			print("[Import Channels] Fetch remote files")
			for file in files:
#				print(f"[Import Channels] Downloading {file}...")
				try:
					open(os.path.join(self.tmp_dir, os.path.basename(file)), "wb").write(self.getUrl(f"{self.url}/file?file={self.e2path}/{quote(file)}"))
				except Exception as e:
					print(f"[Import Channels] Exception: {str(e}")

			print("[Import Channels] Enumerate local files")
			files = self.ImportGetFilelist(False, 'bouquets.tv', 'bouquets.radio')

			print("[Import Channels] Removing old local files...")
			for file in files:
#				print("- Removing %s..." % file)
				try:
					os.remove(os.path.join(self.e2path, file))
				except OSError:
					print(f"[Import Channels] File {file} did not exist")

			print("[Import Channels] Updating files...")
			files = [x for x in os.listdir(self.tmp_dir)]
			for file in files:
#				print("- Moving %s..." % file)
				shutil.move(os.path.join(self.tmp_dir, file), os.path.join(self.e2path, file))

		if "epg" in self.remote_fallback_import:
			print("[Import Channels] Writing epg.dat file on server box")
			try:
				result = loads(self.getUrl(f"{self.url}/api/saveepg", timeout=30).decode("utf-8"))
				if "result" not in result and result["result"] == False:
					self.ImportChannelsDone(False, _("Error when writing epg.dat on the fallback receiver"))
			except Exception as e:
				print(f"[Import Channels] Exception: {str(e)}")
				self.ImportChannelsDone(False, _("Error when writing epg.dat on the fallback receiver"))
				return
			print("[Import Channels] Get EPG Location")
			try:
				epgdatfile = self.getFallbackSettingsValue(self.url, "config.misc.epgcache_filename") or "/media/hdd/epg.dat"
				try:
					files = [file for file in loads(self.getUrl(f"{self.url}/file?dir={dirname(epgdatfile)}"))["files"] if basename(file).startswith(basename(epgdatfile))]
				except:
					files = [file for file in loads(self.getUrl(f"{self.url}/file?dir=/"))["files"] if basename(file).startswith("epg.dat")]
				epg_location = files[0] if files else None
			except Exception as e:
				print(f"[Import Channels] Exception: {str(e)}")
				self.ImportChannelsDone(False, _("Error while retrieving location of epg.dat on the fallback receiver"))
				return
			if epg_location:
				print("[Import Channels] Copy EPG file...")
				try:
					open(join(self.tmp_dir, "epg.dat"), "wb").write(self.getUrl(f"{self.url}/file?file={epg_location}"))
				except Exception as e:
					print(f"[Import Channels] Exception: {str(e)}")
					self.ImportChannelsDone(False, _("Error while retrieving epg.dat from the fallback receiver"))
					return
				try:
					move(join(self.tmp_dir, "epg.dat"), config.misc.epgcache_filename.value)
				except:
					# follow same logic as in epgcache.cpp
					try:
						move(join(self.tmp_dir, "epg.dat"), "/epg.dat")
					except OSError as e:
						print(f"[Import Channels] Exception: {str(e)}")
						self.ImportChannelsDone(False, _("Error while moving epg.dat to its destination"))
						return
			else:
				self.ImportChannelsDone(False, _("No epg.dat file found on the fallback receiver"))

		self.getTerrestrialRegion()
		self.ImportChannelsDone(True, {"channels": _("Channels"), "epg": _("EPG"), "channels_epg": _("Channels and EPG")}[self.remote_fallback_import])

	def ImportChannelsDone(self, flag, message=None):
		rmtree(self.tmp_dir, True)
		if flag:
			AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s imported from fallback tuner") % message, type=MessageBox.TYPE_INFO, timeout=5)
		else:
			AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Import from fallback tuner failed, %s") % message, type=MessageBox.TYPE_ERROR, timeout=5)
