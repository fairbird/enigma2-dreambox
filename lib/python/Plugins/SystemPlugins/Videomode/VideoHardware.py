# -*- coding: utf-8 -*-
from Components.config import config, ConfigSlider, ConfigSelection, ConfigSubDict, ConfigYesNo, ConfigEnableDisable, ConfigOnOff, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, NoSave  # storm - some config are required
from Components.SystemInfo import SystemInfo
from Tools.CList import CList
from Tools.HardwareInfo import HardwareInfo
from Components.About import about
from Tools.Directories import fileExists
from Components.Console import Console
from os.path import isfile
import os
from enigma import getDesktop

# The "VideoHardware" is the interface to /proc/stb/video.
# It generates hotplug events, and gives you the list of
# available and preferred modes, as well as handling the currently
# selected mode. No other strict checking is done.

config.av.edid_override = ConfigYesNo(default=True)
chipsetstring = about.getChipSetString()

Has24hz = SystemInfo["Has24hz"]

axis = {"480i": "0 0 719 479",
                "480p": "0 0 719 479",
                "576i": "0 0 719 575",
                "576p": "0 0 719 575",
                "720p": "0 0 1279 719",
                "1080i": "0 0 1919 1079",
                "1080p": "0 0 1919 1079",
                "2160p30": "0 0 3839 2159",
                "2160p": "0 0 3839 2159",
                "smpte": "0 0 4095 2159"}


class VideoHardware:
        rates = {} # high-level, use selectable modes.

        modes = {}  # a list of (high-level) modes for a certain port.

        rates["PAL"] = {"50Hz": {50: "pal"},
                "60Hz": {60: "pal60"},
                "multi": {50: "pal", 60: "pal60"}}

        rates["NTSC"] = {"60Hz": {60: "ntsc"}}

        rates["Multi"] = {"multi": {50: "pal", 60: "ntsc"}}

        rates["480i"] = {"60Hz": {60: "480i"}}

        rates["576i"] = {"50Hz": {50: "576i"}}

        rates["480p"] = {"60Hz": {60: "480p"}}

        rates["576p"] = {"50Hz": {50: "576p"}}

        rates["720p"] = {"50Hz": {50: "720p50"},
                "60Hz": {60: "720p"},
                "multi": {50: "720p50", 60: "720p"},
                "auto": {50: "720p50", 60: "720p", 24: "720p24"}}

        rates["1080i"] = {"50Hz": {50: "1080i50"},
                "60Hz": {60: "1080i"},
                "multi": {50: "1080i50", 60: "1080i"},
                "auto": {50: "1080i50", 60: "1080i", 24: "1080p24"}}

        rates["1080p"] = {"50Hz": {50: "1080p50"},
                "60Hz": {60: "1080p"},
                "multi": {50: "1080p50", 60: "1080p"},
                "auto": {50: "1080p50", 60: "1080p", 24: "1080p24"}}

        rates["2160p30"] = {"25Hz": {50: "2160p25"},
                "30Hz": {60: "2160p30"},
                "multi": {50: "2160p25", 60: "2160p30"},
                "auto": {50: "2160p25", 60: "2160p30", 24: "2160p24"}}

        rates["2160p"] = {"50Hz": {50: "2160p50"},
                "60Hz": {60: "2160p60"},
                "multi": {50: "2160p50", 60: "2160p60"},
                "auto": {50: "2160p50", 60: "2160p60", 24: "2160p24"}}

        if HardwareInfo().get_device_name() in ("dm900", "dm920"):
                rates["2160p"] = {"50Hz": {50: "2160p50"},
                	"60Hz": {60: "2160p60"},
                	"multi": {50: "2160p50", 60: "2160p60"}, 
                	"auto": {50: "2160p50", 60: "2160p60", 24: "2160p24"}}
        else:
                rates["2160p"] = {"50Hz": {50:
                	"2160p50"}, "60Hz": {60:
                	"2160p"}, "multi": {50: "2160p50", 60: "2160p"},
                	"auto": {50: "2160p50", 60: "2160p", 24: "2160p24"}}

        rates["smpte"] = {"50Hz": {50: "smpte50hz"},
                "60Hz": {60: "smpte60hz"},
                "30Hz": {30: "smpte30hz"},
                "25Hz": {25: "smpte25hz"},
                "24Hz": {24: "smpte24hz"},
                "auto": {60: "smpte60hz"}}

        rates["PC"] = {
                "1024x768": {60: "1024x768"}, # not possible on DM7025
                "800x600": {60: "800x600"},  # also not possible
                "720x480": {60: "720x480"},
                "720x576": {60: "720x576"},
                "1280x720": {60: "1280x720"},
                "1280x720 multi": {50: "1280x720_50", 60: "1280x720"},
                "1920x1080": {60: "1920x1080"},
                "1920x1080 multi": {50: "1920x1080", 60: "1920x1080_50"},
                "1280x1024": {60: "1280x1024"},
                "1366x768": {60: "1366x768"},
                "1366x768 multi": {50: "1366x768", 60: "1366x768_50"},
                "1280x768": {60: "1280x768"},
                "640x480": {60: "640x480"}
        }

        if HardwareInfo().get_device_name() in ("one", "two"):
                rates["480i"] = {"60hz": {60: "480i60hz"}}

                rates["576i"] = {"50hz": {50: "576i50hz"}}

                rates["480p"] = {"60hz": {60: "480p60hz"}}

                rates["576p"] = {"50hz": {50: "576p50hz"}}

                rates["720p"] = {"50hz": {50: "720p50hz"},
			"60hz": {60: "720p60hz"},
			"auto": {60: "720p60hz"}}

                rates["1080i"] = {"50hz": {50: "1080i50hz"},
			"60hz": {60: "1080i60hz"},
			"auto": {60: "1080i60hz"}}

                rates["1080p"] = {"50hz": {50: "1080p50hz"},
			"60hz": {60: "1080p60hz"},
			"30hz": {30: "1080p30hz"},
			"25hz": {25: "1080p25hz"},
			"24hz": {24: "1080p24hz"},
			"auto": {60: "1080p60hz"}}

                rates["2160p"] = {"50hz": {50: "2160p50hz"},
			"60hz": {60: "2160p60hz"},
			"30hz": {30: "2160p30hz"},
			"25hz": {25: "2160p25hz"},
			"24hz": {24: "2160p24hz"},
			"auto": {60: "2160p60hz"}}

                rates["2160p30"] = {"25hz": {50: "2160p25hz"},
			"30hz": {60: "2160p30hz"},
			"auto": {60: "2160p30hz"}}

        if SystemInfo["HasScart"]:
                modes["Scart"] = ["PAL", "NTSC", "Multi"]
        if SystemInfo["HasComposite"] and HardwareInfo().get_device_name() in ("dm7020hd", "dm7020hdv2", "dm8000"):
                modes["RCA"] = ["576i", "PAL", "NTSC", "Multi"]
        if SystemInfo["HasYPbPr"]:
                modes["YPbPr"] = ["720p", "1080i", "576p", "480p", "576i", "480i"]
        if SystemInfo["Has2160p"]:
                modes["DVI"] = ["720p", "1080p", "2160p", "1080i", "576p", "480p", "576i", "480i"]
        if HardwareInfo().get_device_name() in ("one", "two"):
                modes["HDMI"] = ["720p", "1080p", "smpte", "2160p30", "2160p", "1080i", "576p", "576i", "480p", "480i"]
                widescreen_modes = {"720p", "1080p", "1080i", "2160p", "smpte"}
        else:
                modes["DVI"] = ["720p", "1080p", "2160p", "2160p30", "1080i", "576p", "480p", "576i", "480i"]

        def getOutputAspect(self):
                ret = (16, 9)
                port = config.av.videoport.value
                if port not in config.av.videomode:
                        print("[VideoHardware] current port not available in getOutputAspect!!! force 16:9")
                else:
                        mode = config.av.videomode[port].value
                        force_widescreen = self.isWidescreenMode(port, mode)
                        is_widescreen = force_widescreen or config.av.aspect.value in ("16_9", "16_10")
                        is_auto = config.av.aspect.value == "auto"
                        if is_widescreen:
                                if force_widescreen:
                                        pass
                                else:
                                        aspect = {"16_9": "16:9", "16_10": "16:10"}[config.av.aspect.value]
                                        if aspect == "16:10":
                                                ret = (16, 10)
                        elif is_auto:
                                if isfile("/proc/stb/vmpeg/0/aspect"):
                                        try:
                                                aspect_str = open("/proc/stb/vmpeg/0/aspect", "r").read()
                                        except IOError:
                                                print("[Videomode] Read /proc/stb/vmpeg/0/aspect failed!")
                                elif isfile("/sys/class/video/screen_mode"):
                                        try:
                                                aspect_str = open("/sys/class/video/screen_mode", "r").read()
                                        except IOError:
                                                print("[Videomode] Read /sys/class/video/screen_mode failed!")
                                if aspect_str == "1": # 4:3
                                        ret = (4, 3)
                        else:  # 4:3
                                ret = (4, 3)
                return ret

        def __init__(self):
                self.last_modes_preferred = []
                self.on_hotplug = CList()
                self.current_mode = None
                self.current_port = None

                self.readAvailableModes()
                self.readPreferredModes()
                self.widescreen_modes = set(["720p", "1080i", "1080p", "2160p", "2160p30"]).intersection(*[self.modes_available])

                if "DVI-PC" in self.modes and not self.getModeList("DVI-PC"):
                        print("[VideoHardware] remove DVI-PC because of not existing modes")
                        del self.modes["DVI-PC"]
                if "Scart" in self.modes and not self.getModeList("Scart"):
                        print("[VideoHardware] remove Scart because of not existing modes")
                        del self.modes["Scart"]

                self.createConfig()

                # take over old AVSwitch component :)
                from Components.AVSwitch import AVSwitch
                config.av.aspectratio.notifiers = []
                config.av.tvsystem.notifiers = []
                config.av.wss.notifiers = []
                AVSwitch.getOutputAspect = self.getOutputAspect

                config.av.aspect.addNotifier(self.updateAspect)
                config.av.wss.addNotifier(self.updateAspect)
                config.av.policy_169.addNotifier(self.updateAspect)
                config.av.policy_43.addNotifier(self.updateAspect)

        def readAvailableModes(self):
                if isfile("/sys/class/amhdmitx/amhdmitx0/disp_cap"):
                        print("[Videomode] Read /sys/class/amhdmitx/amhdmitx0/disp_cap")
                        modes = open("/sys/class/amhdmitx/amhdmitx0/disp_cap").read()[:-1].replace('*', '')
                        self.modes_available = modes.splitlines()
                        return self.modes_available
                else:
                        try:
                                modes = open("/proc/stb/video/videomode_choices").read()[:-1]
                        except (IOError, OSError):
                                print("[Videomode] Read /proc/stb/video/videomode_choices failed!")
                                self.modes_available = []
                                return
                        self.modes_available = modes.split(' ')

        def readPreferredModes(self):
                if config.av.edid_override.value == False:
                        if isfile("/sys/class/amhdmitx/amhdmitx0/disp_cap"):
                                modes = open("/sys/class/amhdmitx/amhdmitx0/disp_cap").read()[:-1].replace('*', '')
                                self.modes_preferred = modes.splitlines()
                                print("[Videomode] VideoHardware reading disp_cap modes: ", self.modes_preferred)
                        else:
                                try:
                                        modes = open("/proc/stb/video/videomode_edid").read()[:-1]
                                        self.modes_preferred = modes.split(' ')
                                        print("[Videomode] VideoHardware reading edid modes: ", self.modes_preferred)
                                except (IOError, OSError):
                                        print("[Videomode] Read /proc/stb/video/videomode_edid failed!")
                                        try:
                                                modes = open("/proc/stb/video/videomode_preferred").read()[:-1]
                                                self.modes_preferred = modes.split(' ')
                                        except IOError:
                                                print("[Videomode] Read /proc/stb/video/videomode_preferred failed!")
                                                self.modes_preferred = self.modes_available

                        if len(self.modes_preferred) <= 1:
                                self.modes_preferred = self.modes_available
                                print("[Videomode] VideoHardware reading preferred modes is empty, using all video modes")
                else:
                        self.modes_preferred = self.modes_available
                        print("[Videomode] VideoHardware reading preferred modes override, using all video modes")

                self.last_modes_preferred = self.modes_preferred

        # check if a high-level mode with a given rate is available.
        def isModeAvailable(self, port, mode, rate):
                rate = self.rates[mode][rate]
                for mode in rate.values():
                        if port == "DVI":
                                if mode not in self.modes_preferred:
                                        return False
                        else:
                                if mode not in self.modes_available:
                                        return False
                return True

        def isWidescreenMode(self, port, mode):
                return mode in self.widescreen_modes

        def setMode(self, port, mode, rate, force=None):
                print("[VideoHardware] setMode - port:", port, "mode:", mode, "rate:", rate)
                # we can ignore "port"
                self.current_mode = mode
                self.current_port = port
                modes = self.rates[mode][rate]

                mode_50 = modes.get(50)
                mode_60 = modes.get(60)
                mode_30 = modes.get(30)
                mode_25 = modes.get(25)
                mode_24 = modes.get(24)

                if mode_50 is None or force == 60:
                        mode_50 = mode_60
                if mode_60 is None or force == 50:
                        mode_60 = mode_50

                if mode_30 is None or force:
                        mode_30 = mode_60
                        if force == 50:
                                mode_30 = mode_50
                if mode_25 is None or force:
                        mode_25 = mode_60
                        if force == 50:
                                mode_25 = mode_50

                if mode_24 is None or force:
                        mode_24 = mode_60
                        if force == 50:
                                mode_24 = mode_50

                if HardwareInfo().get_device_name() in ("one", "two"): # storm - this part should be here
                        amlmode = list(modes.values())[0]
                        oldamlmode = self.getAMLMode()
                        f = open("/sys/class/display/mode", "w")
                        f.write(amlmode)
                        f.close()
                        print("[AVSwitch] Amlogic setting videomode to mode: %s" % amlmode)
                        f = open("/etc/u-boot.scr.d/000_hdmimode.scr", "w")
                        f.write("setenv hdmimode %s" % amlmode)
                        f.close()
                        f = open("/etc/u-boot.scr.d/000_outputmode.scr", "w")
                        f.write("setenv outputmode %s" % amlmode)
                        f.close()
                        os.system("update-autoexec")
                        f = open("/sys/class/ppmgr/ppscaler", "w")
                        f.write("1")
                        f.close()
                        f = open("/sys/class/ppmgr/ppscaler", "w")
                        f.write("0")
                        f.close()
                        f = open("/sys/class/video/axis", "w")
                        f.write(axis[mode])
                        f.close()
                        f = open("/sys/class/graphics/fb0/stride", "r")
                        stride = f.read().strip()
                        f.close()
                        limits = [int(x) for x in axis[mode].split()]
                        config.osd.dst_left = ConfigSelectionNumber(default=limits[0], stepwidth=1, min=limits[0] - 255, max=limits[0] + 255, wraparound=False)
                        config.osd.dst_top = ConfigSelectionNumber(default=limits[1], stepwidth=1, min=limits[1] - 255, max=limits[1] + 255, wraparound=False)
                        config.osd.dst_width = ConfigSelectionNumber(default=limits[2], stepwidth=1, min=limits[2] - 255, max=limits[2] + 255, wraparound=False)
                        config.osd.dst_height = ConfigSelectionNumber(default=limits[3], stepwidth=1, min=limits[3] - 255, max=limits[3] + 255, wraparound=False)

                        if oldamlmode != amlmode:
                                config.osd.dst_width.setValue(limits[0])
                                config.osd.dst_height.setValue(limits[1])
                                config.osd.dst_left.setValue(limits[2])
                                config.osd.dst_top.setValue(limits[3])
                                config.osd.dst_left.save()
                                config.osd.dst_width.save()
                                config.osd.dst_top.save()
                                config.osd.dst_height.save()
                        print("[AVSwitch] Framebuffer mode:%s  stride:%s axis:%s" % (getDesktop(0).size().width(), stride, axis[mode]))
                        return

                try:
                        print("[Videomode] Write to /proc/stb/video/videomode_50hz")
                        open("/proc/stb/video/videomode_50hz", "w").write(mode_50)
                        print("[Videomode] Write to /proc/stb/video/videomode_60hz")
                        open("/proc/stb/video/videomode_60hz", "w").write(mode_60)
                except IOError:
                        print("[Videomode] Write to /proc/stb/video/videomode_50hz failed.")
                        print("[Videomode] Write to /proc/stb/video/videomode_60hz failed.")
                        if isfile("/proc/stb/video/videomode"):
                                try:
                                        # fallback if no possibility to setup 50 hz mode
                                        open("/proc/stb/video/videomode", "w").write(mode_50)
                                except IOError:
                                        print("[Videomode] Write to /proc/stb/video/videomode failed!")
                        elif isfile("/sys/class/display/mode"):
                                try:
                                        # fallback if no possibility to setup 50 hz mode
                                        open("/sys/class/display/mode", "w").write(mode_50)
                                except IOError:
                                        print("[Videomode] Write to /sys/class/display/mode failed!")

                try:
                        open("/etc/videomode", "w").write(mode_50) # use 50Hz mode (if available) for booting
                except IOError:
                        print("[VideoHardware] writing initial videomode to /etc/videomode failed.")

                if SystemInfo["Has24hz"]:
                        try:
                                print("[Videomode] Write to /proc/stb/video/videomode_24hz")
                                open("/proc/stb/video/videomode_24hz", "w").write(mode_24)
                        except IOError:
                                print("[Videomode] Write to /proc/stb/video/videomode_24hz failed.")

                self.updateAspect(None)

        def saveMode(self, port, mode, rate):
                print("[VideoHardware] saveMode", port, mode, rate)
                config.av.videoport.value = port
                config.av.videoport.save()
                if port in config.av.videomode:
                        config.av.videomode[port].value = mode
                        config.av.videomode[port].save()
                if mode in config.av.videorate:
                        config.av.videorate[mode].value = rate
                        config.av.videorate[mode].save()

        def getAMLMode(self):
                f = open("/sys/class/display/mode", "r")
                currentmode = f.read().strip()
                f.close()
                return currentmode[:-4]

        def isPortAvailable(self, port):
                # fixme
                return True

        def isPortUsed(self, port):
                if port == "DVI":
                        self.readPreferredModes()
                        return len(self.modes_preferred) != 0
                else:
                        return True

        def getPortList(self):
                return [port for port in self.modes if self.isPortAvailable(port)]

        # get a list with all modes, with all rates, for a given port.
        def getModeList(self, port):
                print("[Videomode] VideoHardware getModeList for port", port)
                res = []
                if HardwareInfo().get_device_name() not in ("one", "two"):
                        for mode in self.modes[port]:
                                # list all rates which are completely valid
                                rates = [rate for rate in self.rates[mode] if self.isModeAvailable(port, mode, rate)]

                                # if at least one rate is ok, add this mode
                                if len(rates):
                                        res.append((mode, rates))
                else:
                        res = [('1080p', ['50hz', '60hz', '30hz', '24hz', '25hz']),
                        ('2160p', ['50hz', '60hz', '30hz', '24hz', '25hz']),
                        ('720p', ['50hz', '60hz']), ('1080i', ['50hz', '60hz']),
                        ('576p', ['50hz']), ('576i', ['50hz']), ('480p', ['60hz']), ('480i', ['60hz'])]
                return res

        def createConfig(self, *args):
                has_hdmi = HardwareInfo().has_hdmi()
                lst = []

                config.av.videomode = ConfigSubDict()
                config.av.videorate = ConfigSubDict()

                # create list of output ports
                portlist = self.getPortList()
                for port in portlist:
                        descr = port
                        if descr == "DVI" and has_hdmi:
                                descr = "HDMI"
                        elif descr == "DVI-PC" and has_hdmi:
                                descr = "HDMI-PC"
                        if "HDMI" in descr:
                                lst.insert(0, (port, descr))
                        else:
                                lst.append((port, descr))

                        # create list of available modes
                        modes = self.getModeList(port)
                        if len(modes):
                                config.av.videomode[port] = ConfigSelection(choices=[mode for (mode, rates) in modes])
                        for (mode, rates) in modes:
                                ratelist = []
                                for rate in rates:
                                        if rate == "auto" and not Has24hz:
                                                continue
                                        ratelist.append((rate, rate))
                                config.av.videorate[mode] = ConfigSelection(choices=ratelist)
                config.av.videoport = ConfigSelection(choices=lst)

        def setConfiguredMode(self):
                port = config.av.videoport.value
                if port not in config.av.videomode:
                        print("[Videomode] VideoHardware current port not available, not setting videomode")
                        return

                mode = config.av.videomode[port].value

                if mode not in config.av.videorate:
                        print("[Videomode] VideoHardware current mode not available, not setting videomode")
                        return

                if HardwareInfo().get_device_name() in ("one", "two") and (mode.find("0p30") != -1 or mode.find("0p24") != -1 or mode.find("0p25") != -1):
                        match = re.search(r"(\d*?[ip])(\d*?)$", mode)
                        mode = match.group(1)
                        rate = match.group(2) + "Hz"
                else:
                        rate = config.av.videorate[mode].value
                self.setMode(port, mode, rate)

        def updateAspect(self, cfgelement):
                # determine aspect = {any,4:3,16:9,16:10}
                # determine policy = {bestfit,letterbox,panscan,nonlinear}

                # based on;
                #   config.av.videoport.value: current video output device
                #     Scart:
                #   config.av.aspect:
                #     4_3:            use policy_169
                #     16_9,16_10:     use policy_43
                #     auto            always "bestfit"
                #   config.av.policy_169
                #     letterbox       use letterbox
                #     panscan         use panscan
                #     scale           use bestfit
                #   config.av.policy_43
                #     pillarbox       use panscan
                #     panscan         use letterbox  ("panscan" is just a bad term, it's inverse-panscan)
                #     nonlinear       use nonlinear
                #     scale           use bestfit

                port = config.av.videoport.value
                if port not in config.av.videomode:
                        print("[Videomode] VideoHardware current port not available, not setting videomode")
                        return
                mode = config.av.videomode[port].value

                force_widescreen = self.isWidescreenMode(port, mode)

                is_widescreen = force_widescreen or config.av.aspect.value in ("16_9", "16_10")
                is_auto = config.av.aspect.value == "auto"
                policy2 = "policy" # use main policy

                if is_widescreen:
                        if force_widescreen:
                                aspect = "16:9"
                        else:
                                aspect = {"16_9": "16:9", "16_10": "16:10"}[config.av.aspect.value]
                        policy_choices = {"pillarbox": "panscan", "panscan": "letterbox", "nonlinear": "nonlinear", "scale": "bestfit", "full": "full", "auto": "auto"}
                        policy = policy_choices[config.av.policy_43.value]
                        policy2_choices = {"letterbox": "letterbox", "panscan": "panscan", "scale": "bestfit", "full": "full", "auto": "auto"}
                        policy2 = policy2_choices[config.av.policy_169.value]
                elif is_auto:
                        aspect = "any"
                        if "auto" in config.av.policy_43.choices:
                                policy = "auto"
                        else:
                                policy = "bestfit"
                else:
                        aspect = "4:3"
                        policy = {"letterbox": "letterbox", "panscan": "panscan", "scale": "bestfit", "full": "full", "auto": "auto"}[config.av.policy_169.value]

                if not config.av.wss.value:
                        wss = "auto(4:3_off)"
                else:
                        wss = "auto"

                print("[Videomode] VideoHardware -> setting aspect, policy, policy2, wss", aspect, policy, policy2, wss)
                if chipsetstring.startswith("meson-6") and HardwareInfo().get_device_name() not in ("one", "two"):
                        arw = "0"
                        if config.av.policy_43.value == "bestfit":
                                arw = "10"
                        if config.av.policy_43.value == "panscan":
                                arw = "11"
                        if config.av.policy_43.value == "letterbox":
                                arw = "12"
                        try:
                                open("/sys/class/video/screen_mode", "w").write(arw)
                        except IOError:
                                print("[Videomode] Write to /sys/class/video/screen_mode failed.")
                elif HardwareInfo().get_device_name() in ("one", "two"):
                        arw = "0"
                        if config.av.policy_43.value == "bestfit":
                                arw = "10"
                        if config.av.policy_43.value == "letterbox":
                                arw = "11"
                        if config.av.policy_43.value == "panscan":
                                arw = "12"
                        try:
                                open("/sys/class/video/screen_mode", "w").write(arw)
                        except IOError:
                                print("[Videomode] Write to /sys/class/video/screen_mode failed.")

                try:
                        open("/proc/stb/video/aspect", "w").write(aspect)
                except IOError:
                        print("[Videomode] Write to /proc/stb/video/aspect failed.")
                try:
                        open("/proc/stb/video/policy", "w").write(policy)
                except IOError:
                        print("[Videomode] Write to /proc/stb/video/policy failed.")
                try:
                        open("/proc/stb/denc/0/wss", "w").write(wss)
                except IOError:
                        print("[Videomode] Write to /proc/stb/denc/0/wss failed.")
                try:
                        open("/proc/stb/video/policy2", "w").write(policy2)
                except IOError:
                        print("[Videomode] Write to /proc/stb/video/policy2 failed.")


video_hw = VideoHardware()
video_hw.setConfiguredMode()
