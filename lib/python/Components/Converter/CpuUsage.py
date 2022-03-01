from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Tools.Directories import fileReadLines


class CpuUsage(Converter, object):
	CPU_ALL = -2
	CPU_TOTAL = -1

	def __init__(self, type):
		Converter.__init__(self, type)
		self.percentList = []
		self.pfmt = "%3d%%"
		if not type or type == "Total":
			self.type = self.CPU_TOTAL
			self.sfmt = "CPU: $0"
		elif len(type) == 1 and type[0].isdigit():
			self.type = int(type)
			self.sfmt = "$%d" % type
			self.pfmt = "%d"
		else:
			self.type = self.CPU_ALL
			self.sfmt = str(type)
			cpus = cpuUsageMonitor.getCpusCount()
			if cpus > -1:
				pos = 0
				while True:
					pos = self.sfmt.find("$", pos)
					if pos == -1:
						break
					if pos < len(self.sfmt) - 1 and \
						self.sfmt[pos + 1].isdigit() and \
						int(self.sfmt[pos + 1]) > cpus:
						self.sfmt = self.sfmt.replace("$%s" % self.sfmt[pos + 1], "N/A")
					pos += 1

	def doSuspend(self, suspended):
		if suspended:
			cpuUsageMonitor.disconnectCallback(self.gotPercentage)
		else:
			cpuUsageMonitor.connectCallback(self.gotPercentage)

	def gotPercentage(self, percentList):
		self.percentList = percentList
		self.changed((self.CHANGED_POLL,))

	@cached
	def getText(self):
		result = self.sfmt[:]
		if not self.percentList:
			self.percentList = [0] * 3
		for index in range(len(self.percentList)):
			result = result.replace("$%d" % index, self.pfmt % (self.percentList[index]))
		result = result.replace("$?", "%d" % (len(self.percentList) - 1))
		return result

	@cached
	def getValue(self):
		return self.percentList[self.type if self.type > 0 and self.type < len(self.percentList) else 0]

	text = property(getText)
	value = property(getValue)
	range = 100


class CpuUsageMonitor(Poll, object):

	def __init__(self):
		Poll.__init__(self)
		self.__callbacks = []
		self.__curr_info = self.getCpusInfo()
		self.poll_interval = 500  # Why update twice a second?  Users can't absorb the changes that fast.

	def getCpusCount(self):
		return len(self.__curr_info) - 1

	def getCpusInfo(self):
		results = []
		lines = fileReadLines("/proc/stat", [])
		for line in lines:
			if line.startswith("cpu"):
				# data = [cpu, usr, nic, sys, idle, iowait, irq, softirq, steal]
				data = line.split()
				total = 0
				for item in range(1, len(data)):
					data[item] = int(data[item])
					total += data[item]
				# busy = total - idle - iowait
				busy = total - data[4] - data[5]
				# append [cpu, total, busy]
				results.append([data[0], total, busy])
		return results

	def poll(self):
		prev_info, self.__curr_info = self.__curr_info, self.getCpusInfo()
		if len(self.__callbacks):
			info = []
			for index in range(len(self.__curr_info)):
				# xxx% = (cur_xxx - prev_xxx) / (cur_total - prev_total) * 100
				try:
					percentage = 100 * (self.__curr_info[index][2] - prev_info[index][2]) / (self.__curr_info[index][1] - prev_info[index][1])
				except ZeroDivisionError:
					percentage = 0
				info.append(percentage)
			for callback in self.__callbacks:
				callback(info)

	def connectCallback(self, func):
		if not func in self.__callbacks:
			self.__callbacks.append(func)
		if not self.poll_enabled:
			self.poll()
			self.poll_enabled = True

	def disconnectCallback(self, func):
		if func in self.__callbacks:
			self.__callbacks.remove(func)
		if not len(self.__callbacks) and self.poll_enabled:
			self.poll_enabled = False


cpuUsageMonitor = CpuUsageMonitor()
