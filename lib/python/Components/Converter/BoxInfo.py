# -*- coding: utf-8 -*-
# BoxInfo
# Copyright (c) Tikhon 2019
# v.1.0
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

#<widget source="session.CurrentService" render="Label" position="1356,284" size="488,34" zPosition="2" font="Regular;30" horizontalAlignment="center" foregroundColor="red" backgroundColor="transpBlack" transparent="1">
#	<convert type="BoxInfo">Boxtype</convert>
#</widget>

from Components.Converter.Poll import Poll
from Components.Converter.Converter import Converter
from Components.config import config
from Components.Element import cached
from Components.Language import language
from Tools.Directories import fileExists
from os import path, popen
import re
import os

class BoxInfo(Poll, Converter, object):
	Boxtype = 0
	CpuInfo = 1	
	HddTemp = 2
	TempInfo = 3
	FanInfo = 4
	Upinfo = 5
	CpuLoad = 6
	CpuSpeed = 7
	SkinInfo = 8
	TimeInfo = 9
	TimeInfo2 = 10
	TimeInfo3 = 11
	TimeInfo4 = 12

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.poll_interval = 1000
		self.poll_enabled = True
		self.type = {'Boxtype': self.Boxtype,
		'CpuInfo': self.CpuInfo,
		'HddTemp': self.HddTemp,
		'TempInfo': self.TempInfo,
		'FanInfo': self.FanInfo,
		'Upinfo': self.Upinfo,
		'CpuLoad': self.CpuLoad,
		'CpuSpeed': self.CpuSpeed,
		'SkinInfo': self.SkinInfo,
		'TimeInfo': self.TimeInfo,
		'TimeInfo2': self.TimeInfo2,
		'TimeInfo3': self.TimeInfo3,
		'TimeInfo4': self.TimeInfo4}[type]		

	def imageinfo(self):
		imageinfo = ''
		if os.path.isfile('/usr/lib/opkg/status'):
			imageinfo = '/usr/lib/opkg/status'
		elif os.path.isfile('/usr/lib/ipkg/status'):
			imageinfo = '/usr/lib/ipkg/status'
		elif os.path.isfile('/var/lib/opkg/status'):
			imageinfo = '/var/lib/opkg/status'
		elif os.path.isfile('/var/opkg/status'):
			imageinfo = '/var/opkg/status'
		return imageinfo

	@cached	
	def getText(self):
		if self.type == self.Boxtype:
			box = software = ''
			if os.path.isfile('/proc/version'):
				enigma = open('/proc/version').read().split()[2]
			if os.path.isfile('/proc/stb/info/boxtype'):
				box = open('/proc/stb/info/boxtype').read().strip().upper()
				if box.startswith('HD51'):
					box = 'AX 4K-BOX HD51'
				elif box.startswith('SF8008'):
					box = 'Octagon SF8008'
				elif box.startswith('h9combo'):
					box = 'Zgemma h9combo'
			elif os.path.isfile('/proc/stb/info/vumodel'):
				box = 'Vu+ ' + open('/proc/stb/info/vumodel').read().strip().capitalize()
			elif os.path.isfile('/proc/stb/info/model'):
				box = open('/proc/stb/info/model').read().strip().upper()
			if os.path.isfile('/etc/issue'):
				for line in open('/etc/issue'):
					software += line.capitalize().replace('Open vision enigma2 image for', '').replace('More information : https://openvision.tech', '').replace('%d, %t - (%s %r %m)', '').replace('release', 'r').replace('Welcome to openatv', '').replace('Welcome to opendroid', '').replace('\n', '').replace('\l', '').replace('\\', '').strip()[:-1].capitalize()
				software = ' : %s ' % software.strip()
			if os.path.isfile('/etc/vtiversion.info'):
				software = ''
				for line in open('/etc/vtiversion.info'):
					software += line.split()[0].split('-')[0] + ' ' + line.split()[-1].replace('\n', '')
				software = ' : %s ' % software.strip()
			return '%s%s' % (box, software)

		elif self.type == self.CpuInfo:
			cpu_count = 0
			info = cpu_speed = cpu_info = core = ''
			core = _('core')
			cores = _('cores')
			if os.path.isfile('/proc/cpuinfo'):
				for line in open('/proc/cpuinfo'):
					if 'system type' in line:
						info = line.split(':')[-1].split()[0].strip().strip('\n')
					elif 'cpu MHz' in line:
						cpu_speed =  line.split(':')[-1].strip().strip('\n')
					elif 'cpu type' in line:
						info = line.split(':')[-1].strip().strip('\n')
					elif 'model name' in line or 'Processor' in line:
						info = line.split(':')[-1].strip().strip('\n').replace('Processor ', '')
					elif line.startswith('processor'):
						cpu_count += 1
				if info.startswith('ARM') and os.path.isfile('/proc/stb/info/chipset'):
					for line in open('/proc/cpuinfo'):
						if 'model name' in line or 'Processor' in line:
							info = line.split(':')[-1].split()[0].strip().strip('\n')
							info = '%s (%s)' % (open('/proc/stb/info/chipset').readline().strip().lower().replace('hi3798mv200', 'Hi3798MV200').replace('bcm', 'BCM').replace('brcm', 'BCM').replace('7444', 'BCM7444').replace('7278', 'BCM7278'), info)
				if not cpu_speed:
					try:
						cpu_speed = int(open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq').read()) / 1000
					except:
						try:
							import binascii
							f = open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb')
							clockfrequency = f.read()
							f.close()
							cpu_speed = "%s" % str(int(binascii.hexlify(clockfrequency), 16)/1000000)
						except:
							cpu_speed = '-'
				if cpu_info == '': 
					return _('%s, %s MHz (%d %s)') % (info, cpu_speed, cpu_count, cpu_count > 1 and cores or core)
			else:
				return _('No info')

		elif self.type == self.HddTemp:
			textvalue = 'No info'
			info = 'N/A'
			try:
				out_line = popen('hddtemp -n -q /dev/sda').readline()
				info = 'HDD: Temp:' + out_line[:2] + str('\xb0') + 'C'
				textvalue = info
			except:
				pass
			return textvalue

		elif self.type == self.TempInfo:
			info = 'N/A'
			try:
				if os.path.exists('/proc/stb/sensors/temp0/value') and os.path.exists('/proc/stb/sensors/temp0/unit'):
					info = '%s%s%s' % (open('/proc/stb/sensors/temp0/value').read().strip('\n'), str('\xb0'), open('/proc/stb/sensors/temp0/unit').read().strip('\n'))
				elif os.path.exists('/proc/stb/fp/temp_sensor_avs'):
					info = '%s%sC' % (open('/proc/stb/fp/temp_sensor_avs').read().strip('\n'), str('\xb0'))
				elif os.path.exists('/proc/stb/fp/temp_sensor'):
					info = '%s%sC' % (open('/proc/stb/fp/temp_sensor').read().strip('\n'), str('\xb0'))
				elif os.path.exists('/sys/devices/virtual/thermal/thermal_zone0/temp'):
					info = '%s%sC' % (open('/sys/devices/virtual/thermal/thermal_zone0/temp').read()[:2].strip('\n'), str('\xb0'))
				elif os.path.exists('/proc/hisi/msp/pm_cpu'):
					try:
						info = '%s%sC' % (re.search('temperature = (\d+) degree', open('/proc/hisi/msp/pm_cpu').read()).group(1), str('\xb0'))
					except:
						pass
			except:
				info = 'N/A'
			if self.type == self.TempInfo:
				info = (_('CPU: Temp:') + info)
			return info

		elif self.type == self.FanInfo:
			info = 'N/A'
			try:
				if os.path.exists('/proc/stb/fp/fan_speed'):
					info = open('/proc/stb/fp/fan_speed').read().strip('\n')
				elif os.path.exists('/proc/stb/fp/fan_pwm'):
					info = open('/proc/stb/fp/fan_pwm').read().strip('\n')
			except:
				info = 'N/A'
			if self.type == self.FanInfo:
				info = 'Fan: ' + info
			return info

		elif self.type == self.Upinfo:
			try:
				with open('/proc/uptime', 'r') as file:
					uptime_info = file.read().split()
			except:
				return ' '
				uptime_info = None
			if uptime_info != None:
				total_seconds = float(uptime_info[0])
				MINUTE = 60
				HOUR = MINUTE * 60
				DAY = HOUR * 24
				days = int( total_seconds / DAY )
				hours = int( ( total_seconds % DAY ) / HOUR )
				minutes = int( ( total_seconds % HOUR ) / MINUTE )
				seconds = int( total_seconds % MINUTE )
				uptime = ''
				if days > 0:
					uptime += str(days) + ' ' + (days == 1 and _('day') or _('days') ) + ' '
				if len(uptime) > 0 or hours > 0:
					uptime += str(hours) + ' ' + (hours == 1 and _('hour') or _('hours') ) + ' '
				if len(uptime) > 0 or minutes > 0:
					uptime += str(minutes) + ' ' + (minutes == 1 and _('minute') or _('minutes') )
				return _('Time working: %s') % uptime
	
		elif self.type == self.CpuLoad:
			info = ''
			try:
				if os.path.exists('/proc/loadavg'):
					l = open('/proc/loadavg', 'r')
					load = l.readline(4)
					l.close()
			except:
				load = ''
			info = load.replace('\n', '').replace(' ', '')
			return _('CPU Load: %s') % info

		elif self.type == self.CpuSpeed:
			info = 0
			try:
				for line in open('/proc/cpuinfo').readlines():
					line = [ x.strip() for x in line.strip().split(':') ]
					if line[0] == 'cpu MHz':
						info = '%1.0f' % float(line[1])
				if not info:
					try:
						info = int(open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq').read()) / 1000
					except:
						try:
							import binascii
							info = int(int(binascii.hexlify(open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb').read()), 16) / 100000000) * 100
						except:
							info = '-'
				return _('CPU Speed: %s MHz') % info
			except:
				return ''

		elif self.type == self.SkinInfo:			
			if fileExists('/etc/enigma2/settings'):
				try:
					for line in open('/etc/enigma2/settings'):
						if 'config.skin.primary_skin' in line:
							return (_('Skin: ')) + line.replace('/skin.xml', ' ').split('=')[1]
				except:
					return				

		elif self.type == self.TimeInfo:
			if not config.timezone.val.value.startswith('(GMT)'):
				return config.timezone.val.value[4:7]
			else:
				return '+0'

		elif self.type == self.TimeInfo2:
			if not config.timezone.val.value.startswith('(GMT)'):
				return (_('Timezone: ')) + config.timezone.val.value[0:10]
			else:
				return (_('Timezone: ')) + 'GMT+00:00'

		elif self.type == self.TimeInfo3:
			if not config.timezone.val.value.startswith('(GMT)'):
				return (_('Timezone:')) + config.timezone.val.value[0:20]
			else:
				return '+0'

		elif self.type == self.TimeInfo4:
			if not config.timezone.area.value.startswith('(GMT)'):
				return (_('Part~of~the~light: ')) + config.timezone.area.value[0:12]
			else:
				return '+0'
				
	text = property(getText)
