# -*- coding: utf-8 -*-
# ===========================================================================
# ServiceAction - direct Console-based implementation (no daemon dependency).
#
# OpenPLI does not ship OpenATV's eServiceActionClient/socketdaemon, so
# instead of talking to /var/run/daemon.socket we spawn the same shell
# commands directly through Components.Console (async, non-blocking, uses
# the existing Twisted reactor already running in Enigma2).
#
# callback(exitCode: int) is called exactly once. exitCode == 0 -> success.
# ===========================================================================
from os.path import isfile

from Components.Console import Console

ifupBin = "/sbin/ifup"
ifdownBin = "/sbin/ifdown"


def _netrestarterPath() -> str:
    # Prefer /usr/sbin/netrestarter (correct install path); fall back to
    # /etc/init.d/netrestarter for images built before the Makefile.am fix.
    return "/usr/sbin/netrestarter" if isfile("/usr/sbin/netrestarter") else "/etc/init.d/netrestarter"


class ServiceAction:
    """Console-based replacement for the old eServiceActionClient wrapper.

    Same public API as before (restart/start/stop + the ifup/ifdown/...
    class-method factories) so callers need no changes.
    """

    def __init__(self, serviceName: str):
        self.serviceName = serviceName
        self.console = None  # kept alive by the caller holding this instance

    def _run(self, cmd: str, callback, timeout: int = 15000) -> None:
        self.console = Console()

        def _done(result, retval, extra_args=None):
            if callback and callable(callback):
                callback(retval)

        self.console.ePopen(cmd, _done)

    # ---- instance methods ------------------------------------------------

    def restart(self, callback, timeout: int = 15000) -> None:
        self._run(f"/etc/init.d/{self.serviceName} restart", callback, timeout)

    def start(self, callback, timeout: int = 15000) -> None:
        self._run(f"/etc/init.d/{self.serviceName} start", callback, timeout)

    def stop(self, callback, timeout: int = 15000) -> None:
        self._run(f"/etc/init.d/{self.serviceName} stop", callback, timeout)

    # ---- class-method factories -------------------------------------------

    @classmethod
    def netrestart(cls, callback, iface: str = "", timeout: int = 15000) -> "ServiceAction":
        data = iface if (iface and iface != "all") else ""
        obj = cls(data)
        obj._run(f"{_netrestarterPath()} restart {data}".strip(), callback, timeout)
        return obj

    @classmethod
    def ifup(cls, iface: str, callback, timeout: int = 15000) -> "ServiceAction":
        obj = cls(iface)
        obj._run(f"{ifupBin} {iface}", callback, timeout)
        return obj

    @classmethod
    def ifdown(cls, ifaces: "str | list[str]", callback, timeout: int = 15000) -> "ServiceAction":
        data = " ".join(ifaces) if isinstance(ifaces, list) else ifaces
        obj = cls(data)
        obj._run(f"{ifdownBin} {data}", callback, timeout)
        return obj

    @classmethod
    def wlanActivate(cls, iface: str, callback, networkId: "int | None" = None, timeout: int = 30000) -> "ServiceAction":
        obj = cls(iface)
        args = f"{iface} {networkId}" if networkId is not None else iface
        obj._run(f"/etc/init.d/wlanactivator start {args}", callback, timeout)
        return obj

    @classmethod
    def wlanDeactivate(cls, iface: str, callback, timeout: int = 15000) -> "ServiceAction":
        obj = cls(iface)
        obj._run(f"/etc/init.d/wlanactivator stop {iface}", callback, timeout)
        return obj

    @classmethod
    def switchSoftcam(cls, camName: str, callback, timeout: int = 15000) -> "ServiceAction":
        obj = cls(camName)
        obj._run(f"/etc/init.d/softcam.{camName} restart", callback, timeout)
        return obj

    @classmethod
    def switchCardserver(cls, serverName: str, callback, timeout: int = 15000) -> "ServiceAction":
        obj = cls(serverName)
        obj._run(f"/etc/init.d/cardserver.{serverName} restart", callback, timeout)
        return obj

    @classmethod
    def ping(cls, iface: str, host: str, callback, timeout: int = 3000) -> "ServiceAction":
        obj = cls(host)
        secs = max(1, timeout // 1000)
        obj._run(f"/bin/ping -I {iface} -c 1 -W {secs} {host}", callback, timeout)
        return obj

    @classmethod
    def resolve(cls, host: str, callback, timeout: int = 3000) -> "ServiceAction":
        obj = cls(host)
        obj._run(f'python3 -c "import socket,sys;socket.gethostbyname(sys.argv[1])" {host}', callback, timeout)
        return obj

    @classmethod
    def netscan(cls, cidr: str, ports: "list[int]", callback, timeout: int = 10000) -> "ServiceAction":
        obj = cls(cidr)
        portArgs = " ".join(str(p) for p in ports)
        obj._run(f"/usr/sbin/netscan {cidr} {portArgs}", callback, timeout)
        return obj
