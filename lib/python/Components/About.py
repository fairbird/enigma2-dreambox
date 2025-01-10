# -*- coding: utf-8 -*-
from array import array
from binascii import hexlify
from fcntl import ioctl
from glob import glob
from os import stat
from os.path import isfile
from platform import libc_ver
from re import search
from Tools.HardwareInfo import HardwareInfo
from Components.SystemInfo import BoxInfo
from sys import maxsize, modules, version_info, version as pyversion
from Tools.Directories import fileReadLine, fileReadLines
from subprocess import PIPE, Popen
from socket import AF_INET, SOCK_DGRAM, inet_ntoa, socket
from struct import pack, unpack
from time import localtime, strftime

MODULE_NAME = __name__.split(".")[-1]

socfamily = BoxInfo.getItem("socfamily")
MODEL = BoxInfo.getItem("model")


def _ifinfo(sock, addr, ifname):
	iface = pack('256s', bytes(ifname[:15], 'utf-8'))
	info = ioctl(sock.fileno(), addr, iface)
	if addr == 0x8927:
		return ''.join(['%02x:' % ord(chr(char)) for char in info[18:24]])[:-1].upper()
	else:
		return inet_ntoa(info[20:24])


def getIfConfig(ifname):
	ifreq = {"ifname": ifname}
	infos = {}
	sock = socket(AF_INET, SOCK_DGRAM)
	# Offsets defined in /usr/include/linux/sockios.h on linux 2.6.
	infos["addr"] = 0x8915  # SIOCGIFADDR
	infos["brdaddr"] = 0x8919  # SIOCGIFBRDADDR
	infos["hwaddr"] = 0x8927  # SIOCSIFHWADDR
	infos["netmask"] = 0x891b  # SIOCGIFNETMASK
	try:
		for k, v in infos.items():
			ifreq[k] = _ifinfo(sock, v, ifname)
	except Exception as ex:
		print("[About] getIfConfig Ex: %s" % str(ex))
		pass
	sock.close()
	return ifreq


def getIfTransferredData(ifname):
	lines = fileReadLines("/proc/net/dev", source=MODULE_NAME)
	if lines:
		for line in lines:
			if ifname in line:
				data = line.split("%s:" % ifname)[1].split()
				rx_bytes, tx_bytes = (data[0], data[8])
				return rx_bytes, tx_bytes


def getVersionString():
	return str(BoxInfo.getItem("imageversion"))


def getImageVersionString():
	return str(BoxInfo.getItem("imageversion"))

# WW -placeholder for BC purposes, commented out for the moment in the Screen


def getFlashDateString():
	try:
		tm = localtime(stat("/boot").st_ctime)
		if tm.tm_year >= 2011:
			return strftime(_("%Y-%m-%d"), tm)
		else:
			return _("Unknown")
	except:
		return _("Unknown")


def returndate(date):
	date = str(date)
	return "%s-%s-%s" % (date[:4], date[4:6], date[6:8])


def getBuildDateString():
	version = fileReadLine("/etc/version", source=MODULE_NAME)
	if version is None:
		return _("Unknown")
	return "%s-%s-%s" % (version[:4], version[4:6], version[6:8])


def getUpdateDateString():
	try:
		driver = [x.split("-")[-2] for x in open(glob("/var/lib/opkg/info/*-dvb-modules-*.control")[0], "r") if x.startswith("Version:")][0]
		if build.isdigit():
			return returndate(build)
	except:
		pass
	return _("unknown")


def getEnigmaVersionString():
	import enigma
	enigma_version = enigma.getEnigmaVersionString()
	if '-(no branch)' in enigma_version:
		enigma_version = enigma_version[:-12]
	return enigma_version


#maybe in future it is better to swig the branch string - for now I retrieve it from the VersionString
def getEnigmaBranchString():
	import enigma
	return enigma.getEnigmaVersionString()[11:]


def getGStreamerVersionString():
	try:
		gst = [x.split("Version: ") for x in open(glob("/var/lib/opkg/info/gstreamer[0-9].[0-9].control")[0], "r") if x.startswith("Version:")][0]
		return "%s" % gst[1].split("+")[0].split("-")[0].replace("\n", "")
	except:
		return _("Not Installed")


def getffmpegVersionString():
	try:
		ffmpeg = [x.split("Version: ") for x in open(glob("/var/lib/opkg/info/ffmpeg.control")[0], "r") if x.startswith("Version:")][0]
		return "%s" % ffmpeg[1].split("+")[0].replace("\n", "")
	except:
		return _("Not Installed")


def getKernelVersionString():
	return BoxInfo.getItem("kernel")


def getHardwareTypeString():
	return HardwareInfo().get_device_string()


def getImageTypeString():
	return "%s %s" % (BoxInfo.getItem("displaydistro"), BoxInfo.getItem("imageversion").title())


def getOEVersionString():
	return BoxInfo.getItem("oe").title()


def getCPUSerial():
	lines = fileReadLines("/proc/cpuinfo", source=MODULE_NAME)
	if lines:
		for line in lines:
			if line[0:6] == "Serial":
				return line[10:26]
	return _("Undefined")


def getCPUInfoString():
	try:
		cpu_count = 0
		cpu_speed = 0
		processor = ""
		for line in open("/proc/cpuinfo").readlines():
			line = [x.strip() for x in line.strip().split(":")]
			if not processor and line[0] in ("system type", "model name", "Processor"):
				processor = line[1].split()[0]
			elif not cpu_speed and line[0] == "cpu MHz":
				cpu_speed = "%1.0f" % float(line[1])
			elif line[0] == "processor":
				cpu_count += 1

		if processor.startswith("ARM") and isfile("/proc/stb/info/chipset"):
			processor = "%s (%s)" % (open("/proc/stb/info/chipset").readline().strip().upper(), processor)

		if not cpu_speed:
			try:
				cpu_speed = int(open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").read()) // 1000
			except:
				try:
					import binascii
					cpu_speed = int(int(binascii.hexlify(open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb').read()), 16) // 100000000) * 100
				except:
					cpu_speed = "-"

		temperature = None
		freq = _("MHz")
		if isfile('/proc/stb/fp/temp_sensor_avs'):
			temperature = open("/proc/stb/fp/temp_sensor_avs").readline().replace('\n', '')
		elif isfile('/proc/stb/power/avs'):
			temperature = open("/proc/stb/power/avs").readline().replace('\n', '')
		elif isfile('/proc/stb/fp/temp_sensor'):
			temperature = open("/proc/stb/fp/temp_sensor").readline().replace('\n', '')
		elif isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
			try:
				temperature = int(open("/sys/devices/virtual/thermal/thermal_zone0/temp").read().strip()) // 1000
			except:
				pass
		elif isfile("/proc/hisi/msp/pm_cpu"):
			try:
				temperature = search('temperature = (\d+) degree', open("/proc/hisi/msp/pm_cpu").read()).group(1)
			except:
				pass
		if temperature:
			return "%s %s %s (%s) %s\xb0C" % (processor, cpu_speed, freq, ngettext("%d core", "%d cores", cpu_count) % cpu_count, temperature)
		return "%s %s %s (%s)" % (processor, cpu_speed, freq, ngettext("%d core", "%d cores", cpu_count) % cpu_count)
	except:
		return _("undefined")


def getSystemTemperature():
	temperature = ""
	if isfile("/proc/stb/sensors/temp0/value"):
		temperature = fileReadLine("/proc/stb/sensors/temp0/value", source=MODULE_NAME)
	elif isfile("/proc/stb/sensors/temp/value"):
		temperature = fileReadLine("/proc/stb/sensors/temp/value", source=MODULE_NAME)
	elif isfile("/proc/stb/fp/temp_sensor"):
		temperature = fileReadLine("/proc/stb/fp/temp_sensor", source=MODULE_NAME)
	if temperature:
		return "%s%s C" % (temperature, "\u00B0")
	return temperature


def getChipSetString():
	if MODEL in ('dm7080', 'dm820'):
		return "7435"
	elif MODEL in ('dm520', 'dm525'):
		return "73625"
	elif MODEL in ('dm900', 'dm920', 'et13000', 'sf5008'):
		return "7252S"
	elif MODEL in ('hd51', 'vs1500', 'h7'):
		return "7251S"
	elif MODEL in ('alien5',):
		return "S905D"
	else:
		chipset = fileReadLine("/proc/stb/info/chipset", source=MODULE_NAME)
		if chipset is None:
			return _("Undefined")
		return str(chipset.lower().replace('\n', '').replace('bcm', '').replace('brcm', '').replace('sti', ''))


def getCPUBrand():
	if BoxInfo.getItem("AmlogicFamily"):
		return _("Amlogic")
	elif BoxInfo.getItem("HiSilicon"):
		return _("HiSilicon")
	elif socfamily.startswith("smp"):
		return _("Sigma Designs")
	elif socfamily.startswith("bcm") or BoxInfo.getItem("brand") == "rpi":
		return _("Broadcom")
	print("[About] No CPU brand?")
	return _("Undefined")


def getCPUArch():
	if BoxInfo.getItem("ArchIsARM64"):
		return _("ARM64")
	elif BoxInfo.getItem("ArchIsARM"):
		return _("ARM")
	return _("Mipsel")


def getDVBAPI():
	if BoxInfo.getItem("OLDE2API"):
		return _("Old") 
	else:
		return _("New")


def getDriverInstalledDate():

	def extractDate(value):
		match = search('[0-9]{8}', value)
		if match:
			return match[0]
		else:
			return value

	filenames = glob("/var/lib/opkg/info/*dvb-modules*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					return extractDate(line)
	filenames = glob("/var/lib/opkg/info/*dvb-proxy*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					return extractDate(line)
	filenames = glob("/var/lib/opkg/info/*platform-util*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					return extractDate(line)
	return _("Unknown")


def getPythonVersionString():
	return "%s.%s.%s" % (version_info.major, version_info.minor, version_info.micro)


def getOpenSSLVersion():
	process = Popen(("/usr/bin/openssl", "version"), stdout=PIPE, stderr=PIPE, universal_newlines=True)
	stdout, stderr = process.communicate()
	if process.returncode == 0:
		data = stdout.strip().split()
		if len(data) > 1 and data[0] == "OpenSSL":
			return data[1]
	print("[About] Get OpenSSL version failed.")
	return _("Unknown")


def GetIPsFromNetworkInterfaces():
	structSize = 40 if maxsize > 2 ** 32 else 32
	sock = socket(AF_INET, SOCK_DGRAM)
	maxPossible = 8  # Initial value.
	while True:
		_bytes = maxPossible * structSize
		names = array("B")
		for index in range(_bytes):
			names.append(0)
		outbytes = unpack("iL", ioctl(sock.fileno(), 0x8912, pack("iL", _bytes, names.buffer_info()[0])))[0]  # 0x8912 = SIOCGIFCONF
		if outbytes == _bytes:
			maxPossible *= 2
		else:
			break
	ifaces = []
	for index in range(0, outbytes, structSize):
		ifaceName = names.tobytes()[index:index + 16].decode().split("\0", 1)[0]
		if ifaceName != "lo":
			ifaces.append((ifaceName, inet_ntoa(names[index + 20:index + 24])))
	return ifaces


def getBoxUptime():
	upTime = fileReadLine("/proc/uptime", source=MODULE_NAME)
	if upTime is None:
		return "-"
	secs = int(upTime.split(".")[0])
	times = []
	if secs > 86400:
		days = secs // 86400
		secs = secs % 86400
		times.append(ngettext("%d Day", "%d Days", days) % days)
	h = secs // 3600
	m = (secs % 3600) // 60
	times.append(ngettext("%d Hour", "%d Hours", h) % h)
	times.append(ngettext("%d Minute", "%d Minutes", m) % m)
	return " ".join(times)


def getGlibcVersion():
	try:
		return libc_ver()[1]
	except:
		print("[About] Get glibc version failed.")
	return _("Unknown")


def getGccVersion():
	try:
		return pyversion.split("[GCC ")[1].replace("]", "")
	except:
		print("[About] Get gcc version failed.")
	return _("Unknown")


# For modules that do "from About import about"
about = modules[__name__]
