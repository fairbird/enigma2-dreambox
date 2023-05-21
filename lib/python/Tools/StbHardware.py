# -*- coding: utf-8 -*-
from os import path
from fcntl import ioctl
from struct import pack, unpack
from time import localtime, time, timezone
from Tools.HardwareInfo import HardwareInfo

def getFPVersion():
	ret = None
	try:
		if HardwareInfo().get_device_model() in ('dm7080', 'dm820', 'dm520', 'dm525', 'dm900', 'dm920'):
			ret = open("/proc/stb/fp/version", "r").read()
		elif HardwareInfo().get_device_model() in ('one', 'two'):
			ret = open("/proc/stb/fp/fp_version", "r").read()
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ret = ioctl(fp.fileno(), 0)
			fp.close()
		except IOError:
			try:
				ret = open("/sys/firmware/devicetree/base/bolt/tag", "r").read().rstrip("\0")
			except:
				print("getFPVersion failed!")
	return ret


def setFPWakeuptime(wutime):
	try:
		open("/proc/stb/fp/wakeup_time", "w").write(str(wutime))
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 6, pack('L', wutime)) # set wake up
			fp.close()
		except IOError:
			print("setFPWakeupTime failed!")


def setRTCoffset(forsleep=None):
	forsleep = 7200 + timezone if localtime().tm_isdst == 0 else 3600 - timezone
	# t_local = localtime(int(time()))  # This line does nothing!
	# Set RTC OFFSET (diff. between UTC and Local Time)
	try:
		open("/proc/stb/fp/rtc_offset", "w").write(str(forsleep))
		print("[RTC] set RTC offset to %s sec." % (forsleep))
	except IOError:
		print("setRTCoffset failed!")


def setRTCtime(wutime):
	if path.exists("/proc/stb/fp/rtc_offset"):
		setRTCoffset()
	try:
		open("/proc/stb/fp/rtc", "w").write(str(wutime))
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 0x101, pack('L', wutime)) # set wake up
			fp.close()
		except IOError:
			print("setRTCtime failed!")


def getFPWakeuptime():
	ret = 0
	try:
		ret = open("/proc/stb/fp/wakeup_time", "r").read()
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ret = unpack('L', ioctl(fp.fileno(), 5, '    '))[0] # get wakeuptime
			fp.close()
		except IOError:
			print("getFPWakeupTime failed!")
	return ret


wasTimerWakeup = None


def getFPWasTimerWakeup():
	global wasTimerWakeup
	if wasTimerWakeup is not None:
		return wasTimerWakeup
	wasTimerWakeup = False
	try:
		wasTimerWakeup = int(open("/proc/stb/fp/was_timer_wakeup", "r").read()) and True or False
	except:
		try:
			fp = open("/dev/dbox/fp0")
			wasTimerWakeup = unpack('B', ioctl(fp.fileno(), 9, ' '))[0] and True or False
			fp.close()
		except IOError:
			print("wasTimerWakeup failed!")
	if wasTimerWakeup:
		# clear hardware status
		clearFPWasTimerWakeup()
	return wasTimerWakeup


def clearFPWasTimerWakeup():
	try:
		open("/proc/stb/fp/was_timer_wakeup", "w").write('0')
	except:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 10)
			fp.close()
		except IOError:
			print("clearFPWasTimerWakeup failed!")
