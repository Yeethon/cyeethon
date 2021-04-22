" This module tries to retrieve as much platform-identifying data as\n    possible. It makes this information available via function APIs.\n\n    If called from the command line, it prints the platform\n    information concatenated as single string to stdout. The output\n    format is useable as part of a filename.\n\n"
__copyright__ = "\n    Copyright (c) 1999-2000, Marc-Andre Lemburg; mailto:mal@lemburg.com\n    Copyright (c) 2000-2010, eGenix.com Software GmbH; mailto:info@egenix.com\n\n    Permission to use, copy, modify, and distribute this software and its\n    documentation for any purpose and without fee or royalty is hereby granted,\n    provided that the above copyright notice appear in all copies and that\n    both that copyright notice and this permission notice appear in\n    supporting documentation or portions thereof, including modifications,\n    that you make.\n\n    EGENIX.COM SOFTWARE GMBH DISCLAIMS ALL WARRANTIES WITH REGARD TO\n    THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND\n    FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL,\n    INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING\n    FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,\n    NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION\n    WITH THE USE OR PERFORMANCE OF THIS SOFTWARE !\n\n"
__version__ = "1.0.8"
import collections
import os
import re
import sys
import subprocess
import functools
import itertools

_ver_stages = {
    "dev": 10,
    "alpha": 20,
    "a": 20,
    "beta": 30,
    "b": 30,
    "c": 40,
    "RC": 50,
    "rc": 50,
    "pl": 200,
    "p": 200,
}
_component_re = re.compile("([0-9]+|[._+-])")


def _comparable_version(version):
    result = []
    for v in _component_re.split(version):
        if v not in "._+-":
            try:
                v = int(v, 10)
                t = 100
            except ValueError:
                t = _ver_stages.get(v, 0)
            result.extend((t, v))
    return result


_libc_search = re.compile(
    b"(__libc_init)|(GLIBC_([0-9.]+))|(libc(_\\w+)?\\.so(?:\\.(\\d[0-9.]*))?)", re.ASCII
)


def libc_ver(executable=None, lib="", version="", chunksize=16384):
    " Tries to determine the libc version that the file executable\n        (which defaults to the Python interpreter) is linked against.\n\n        Returns a tuple of strings (lib,version) which default to the\n        given parameters in case the lookup fails.\n\n        Note that the function has intimate knowledge of how different\n        libc versions add symbols to the executable and thus is probably\n        only useable for executables compiled using gcc.\n\n        The file is read and scanned in chunks of chunksize bytes.\n\n    "
    if not executable:
        try:
            ver = os.confstr("CS_GNU_LIBC_VERSION")
            parts = ver.split(maxsplit=1)
            if len(parts) == 2:
                return tuple(parts)
        except (AttributeError, ValueError, OSError):
            pass
        executable = sys.executable
    V = _comparable_version
    if hasattr(os.path, "realpath"):
        executable = os.path.realpath(executable)
    with open(executable, "rb") as f:
        binary = f.read(chunksize)
        pos = 0
        while pos < len(binary):
            if (b"libc" in binary) or (b"GLIBC" in binary):
                m = _libc_search.search(binary, pos)
            else:
                m = None
            if (not m) or (m.end() == len(binary)):
                chunk = f.read(chunksize)
                if chunk:
                    binary = binary[max(pos, (len(binary) - 1000)) :] + chunk
                    pos = 0
                    continue
                if not m:
                    break
            (libcinit, glibc, glibcversion, so, threads, soversion) = [
                (s.decode("latin1") if (s is not None) else s) for s in m.groups()
            ]
            if libcinit and (not lib):
                lib = "libc"
            elif glibc:
                if lib != "glibc":
                    lib = "glibc"
                    version = glibcversion
                elif V(glibcversion) > V(version):
                    version = glibcversion
            elif so:
                if lib != "glibc":
                    lib = "libc"
                    if soversion and ((not version) or (V(soversion) > V(version))):
                        version = soversion
                    if threads and (version[(-len(threads)) :] != threads):
                        version = version + threads
            pos = m.end()
    return (lib, version)


def _norm_version(version, build=""):
    " Normalize the version and build strings and return a single\n        version string using the format major.minor.build (or patchlevel).\n    "
    l = version.split(".")
    if build:
        l.append(build)
    try:
        ints = map(int, l)
    except ValueError:
        strings = l
    else:
        strings = list(map(str, ints))
    version = ".".join(strings[:3])
    return version


_ver_output = re.compile("(?:([\\w ]+) ([\\w.]+) .*\\[.* ([\\d.]+)\\])")


def _syscmd_ver(
    system="", release="", version="", supported_platforms=("win32", "win16", "dos")
):
    ' Tries to figure out the OS version used and returns\n        a tuple (system, release, version).\n\n        It uses the "ver" shell command for this which is known\n        to exists on Windows, DOS. XXX Others too ?\n\n        In case this fails, the given parameters are used as\n        defaults.\n\n    '
    if sys.platform not in supported_platforms:
        return (system, release, version)
    import subprocess

    for cmd in ("ver", "command /c ver", "cmd /c ver"):
        try:
            info = subprocess.check_output(
                cmd, stderr=subprocess.DEVNULL, text=True, shell=True
            )
        except (OSError, subprocess.CalledProcessError) as why:
            continue
        else:
            break
    else:
        return (system, release, version)
    info = info.strip()
    m = _ver_output.match(info)
    if m is not None:
        (system, release, version) = m.groups()
        if release[(-1)] == ".":
            release = release[:(-1)]
        if version[(-1)] == ".":
            version = version[:(-1)]
        version = _norm_version(version)
    return (system, release, version)


_WIN32_CLIENT_RELEASES = {
    (5, 0): "2000",
    (5, 1): "XP",
    (5, 2): "2003Server",
    (5, None): "post2003",
    (6, 0): "Vista",
    (6, 1): "7",
    (6, 2): "8",
    (6, 3): "8.1",
    (6, None): "post8.1",
    (10, 0): "10",
    (10, None): "post10",
}
_WIN32_SERVER_RELEASES = {
    (5, 2): "2003Server",
    (6, 0): "2008Server",
    (6, 1): "2008ServerR2",
    (6, 2): "2012Server",
    (6, 3): "2012ServerR2",
    (6, None): "post2012ServerR2",
}


def win32_is_iot():
    return win32_edition() in (
        "IoTUAP",
        "NanoServer",
        "WindowsCoreHeadless",
        "IoTEdgeOS",
    )


def win32_edition():
    try:
        try:
            import winreg
        except ImportError:
            import _winreg as winreg
    except ImportError:
        pass
    else:
        try:
            cvkey = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion"
            with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, cvkey) as key:
                return winreg.QueryValueEx(key, "EditionId")[0]
        except OSError:
            pass
    return None


def win32_ver(release="", version="", csd="", ptype=""):
    try:
        from sys import getwindowsversion
    except ImportError:
        return (release, version, csd, ptype)
    winver = getwindowsversion()
    (maj, min, build) = winver.platform_version or winver[:3]
    version = "{0}.{1}.{2}".format(maj, min, build)
    release = (
        _WIN32_CLIENT_RELEASES.get((maj, min))
        or _WIN32_CLIENT_RELEASES.get((maj, None))
        or release
    )
    if winver[:2] == (maj, min):
        try:
            csd = "SP{}".format(winver.service_pack_major)
        except AttributeError:
            if csd[:13] == "Service Pack ":
                csd = "SP" + csd[13:]
    if getattr(winver, "product_type", None) == 3:
        release = (
            _WIN32_SERVER_RELEASES.get((maj, min))
            or _WIN32_SERVER_RELEASES.get((maj, None))
            or release
        )
    try:
        try:
            import winreg
        except ImportError:
            import _winreg as winreg
    except ImportError:
        pass
    else:
        try:
            cvkey = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion"
            with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, cvkey) as key:
                ptype = winreg.QueryValueEx(key, "CurrentType")[0]
        except OSError:
            pass
    return (release, version, csd, ptype)


def _mac_ver_xml():
    fn = "/System/Library/CoreServices/SystemVersion.plist"
    if not os.path.exists(fn):
        return None
    try:
        import plistlib
    except ImportError:
        return None
    with open(fn, "rb") as f:
        pl = plistlib.load(f)
    release = pl["ProductVersion"]
    versioninfo = ("", "", "")
    machine = os.uname().machine
    if machine in ("ppc", "Power Macintosh"):
        machine = "PowerPC"
    return (release, versioninfo, machine)


def mac_ver(release="", versioninfo=("", "", ""), machine=""):
    " Get macOS version information and return it as tuple (release,\n        versioninfo, machine) with versioninfo being a tuple (version,\n        dev_stage, non_release_version).\n\n        Entries which cannot be determined are set to the parameter values\n        which default to ''. All tuple entries are strings.\n    "
    info = _mac_ver_xml()
    if info is not None:
        return info
    return (release, versioninfo, machine)


def _java_getprop(name, default):
    from java.lang import System

    try:
        value = System.getProperty(name)
        if value is None:
            return default
        return value
    except AttributeError:
        return default


def java_ver(release="", vendor="", vminfo=("", "", ""), osinfo=("", "", "")):
    " Version interface for Jython.\n\n        Returns a tuple (release, vendor, vminfo, osinfo) with vminfo being\n        a tuple (vm_name, vm_release, vm_vendor) and osinfo being a\n        tuple (os_name, os_version, os_arch).\n\n        Values which cannot be determined are set to the defaults\n        given as parameters (which all default to '').\n\n    "
    try:
        import java.lang
    except ImportError:
        return (release, vendor, vminfo, osinfo)
    vendor = _java_getprop("java.vendor", vendor)
    release = _java_getprop("java.version", release)
    (vm_name, vm_release, vm_vendor) = vminfo
    vm_name = _java_getprop("java.vm.name", vm_name)
    vm_vendor = _java_getprop("java.vm.vendor", vm_vendor)
    vm_release = _java_getprop("java.vm.version", vm_release)
    vminfo = (vm_name, vm_release, vm_vendor)
    (os_name, os_version, os_arch) = osinfo
    os_arch = _java_getprop("java.os.arch", os_arch)
    os_name = _java_getprop("java.os.name", os_name)
    os_version = _java_getprop("java.os.version", os_version)
    osinfo = (os_name, os_version, os_arch)
    return (release, vendor, vminfo, osinfo)


def system_alias(system, release, version):
    " Returns (system, release, version) aliased to common\n        marketing names used for some systems.\n\n        It also does some reordering of the information in some cases\n        where it would otherwise cause confusion.\n\n    "
    if system == "SunOS":
        if release < "5":
            return (system, release, version)
        l = release.split(".")
        if l:
            try:
                major = int(l[0])
            except ValueError:
                pass
            else:
                major = major - 3
                l[0] = str(major)
                release = ".".join(l)
        if release < "6":
            system = "Solaris"
        else:
            system = "Solaris"
    elif system in ("win32", "win16"):
        system = "Windows"
    return (system, release, version)


def _platform(*args):
    ' Helper to format the platform string in a filename\n        compatible format e.g. "system-version-machine".\n    '
    platform = "-".join((x.strip() for x in filter(len, args)))
    platform = platform.replace(" ", "_")
    platform = platform.replace("/", "-")
    platform = platform.replace("\\", "-")
    platform = platform.replace(":", "-")
    platform = platform.replace(";", "-")
    platform = platform.replace('"', "-")
    platform = platform.replace("(", "-")
    platform = platform.replace(")", "-")
    platform = platform.replace("unknown", "")
    while 1:
        cleaned = platform.replace("--", "-")
        if cleaned == platform:
            break
        platform = cleaned
    while platform[(-1)] == "-":
        platform = platform[:(-1)]
    return platform


def _node(default=""):
    " Helper to determine the node name of this machine.\n    "
    try:
        import socket
    except ImportError:
        return default
    try:
        return socket.gethostname()
    except OSError:
        return default


def _follow_symlinks(filepath):
    " In case filepath is a symlink, follow it until a\n        real file is reached.\n    "
    filepath = os.path.abspath(filepath)
    while os.path.islink(filepath):
        filepath = os.path.normpath(
            os.path.join(os.path.dirname(filepath), os.readlink(filepath))
        )
    return filepath


def _syscmd_file(target, default=""):
    " Interface to the system's file command.\n\n        The function uses the -b option of the file command to have it\n        omit the filename in its output. Follow the symlinks. It returns\n        default in case the command should fail.\n\n    "
    if sys.platform in ("dos", "win32", "win16"):
        return default
    import subprocess

    target = _follow_symlinks(target)
    env = dict(os.environ, LC_ALL="C")
    try:
        output = subprocess.check_output(
            ["file", "-b", target], stderr=subprocess.DEVNULL, env=env
        )
    except (OSError, subprocess.CalledProcessError):
        return default
    if not output:
        return default
    return output.decode("latin-1")


_default_architecture = {
    "win32": ("", "WindowsPE"),
    "win16": ("", "Windows"),
    "dos": ("", "MSDOS"),
}


def architecture(executable=sys.executable, bits="", linkage=""):
    ' Queries the given executable (defaults to the Python interpreter\n        binary) for various architecture information.\n\n        Returns a tuple (bits, linkage) which contains information about\n        the bit architecture and the linkage format used for the\n        executable. Both values are returned as strings.\n\n        Values that cannot be determined are returned as given by the\n        parameter presets. If bits is given as \'\', the sizeof(pointer)\n        (or sizeof(long) on Python version < 1.5.2) is used as\n        indicator for the supported pointer size.\n\n        The function relies on the system\'s "file" command to do the\n        actual work. This is available on most if not all Unix\n        platforms. On some non-Unix platforms where the "file" command\n        does not exist and the executable is set to the Python interpreter\n        binary defaults from _default_architecture are used.\n\n    '
    if not bits:
        import struct

        size = struct.calcsize("P")
        bits = str((size * 8)) + "bit"
    if executable:
        fileout = _syscmd_file(executable, "")
    else:
        fileout = ""
    if (not fileout) and (executable == sys.executable):
        if sys.platform in _default_architecture:
            (b, l) = _default_architecture[sys.platform]
            if b:
                bits = b
            if l:
                linkage = l
        return (bits, linkage)
    if ("executable" not in fileout) and ("shared object" not in fileout):
        return (bits, linkage)
    if "32-bit" in fileout:
        bits = "32bit"
    elif "64-bit" in fileout:
        bits = "64bit"
    if "ELF" in fileout:
        linkage = "ELF"
    elif "PE" in fileout:
        if "Windows" in fileout:
            linkage = "WindowsPE"
        else:
            linkage = "PE"
    elif "COFF" in fileout:
        linkage = "COFF"
    elif "MS-DOS" in fileout:
        linkage = "MSDOS"
    else:
        pass
    return (bits, linkage)


def _get_machine_win32():
    return os.environ.get("PROCESSOR_ARCHITEW6432", "") or os.environ.get(
        "PROCESSOR_ARCHITECTURE", ""
    )


class _Processor:
    @classmethod
    def get(cls):
        func = getattr(cls, f"get_{sys.platform}", cls.from_subprocess)
        return func() or ""

    def get_win32():
        return os.environ.get("PROCESSOR_IDENTIFIER", _get_machine_win32())

    def get_OpenVMS():
        try:
            import vms_lib
        except ImportError:
            pass
        else:
            (csid, cpu_number) = vms_lib.getsyi("SYI$_CPU", 0)
            return "Alpha" if (cpu_number >= 128) else "VAX"

    def from_subprocess():
        "\n        Fall back to `uname -p`\n        "
        try:
            return subprocess.check_output(
                ["uname", "-p"], stderr=subprocess.DEVNULL, text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            pass


def _unknown_as_blank(val):
    return "" if (val == "unknown") else val


class uname_result(
    collections.namedtuple("uname_result_base", "system node release version machine")
):
    "\n    A uname_result that's largely compatible with a\n    simple namedtuple except that 'processor' is\n    resolved late and cached to avoid calling \"uname\"\n    except when needed.\n    "

    @functools.cached_property
    def processor(self):
        return _unknown_as_blank(_Processor.get())

    def __iter__(self):
        return itertools.chain(super().__iter__(), (self.processor,))

    @classmethod
    def _make(cls, iterable):
        num_fields = len(cls._fields)
        result = cls.__new__(cls, *iterable)
        if len(result) != (num_fields + 1):
            msg = f"Expected {num_fields} arguments, got {len(result)}"
            raise TypeError(msg)
        return result

    def __getitem__(self, key):
        return tuple(self)[key]

    def __len__(self):
        return len(tuple(iter(self)))

    def __reduce__(self):
        return (uname_result, tuple(self)[: len(self._fields)])


_uname_cache = None


def uname():
    " Fairly portable uname interface. Returns a tuple\n        of strings (system, node, release, version, machine, processor)\n        identifying the underlying platform.\n\n        Note that unlike the os.uname function this also returns\n        possible processor information as an additional tuple entry.\n\n        Entries which cannot be determined are set to ''.\n\n    "
    global _uname_cache
    if _uname_cache is not None:
        return _uname_cache
    try:
        (system, node, release, version, machine) = infos = os.uname()
    except AttributeError:
        system = sys.platform
        node = _node()
        release = version = machine = ""
        infos = ()
    if not any(infos):
        if system == "win32":
            (release, version, csd, ptype) = win32_ver()
            machine = machine or _get_machine_win32()
        if not (release and version):
            (system, release, version) = _syscmd_ver(system)
            if system == "Microsoft Windows":
                system = "Windows"
            elif (system == "Microsoft") and (release == "Windows"):
                system = "Windows"
                if "6.0" == version[:3]:
                    release = "Vista"
                else:
                    release = ""
        if system in ("win32", "win16"):
            if not version:
                if system == "win32":
                    version = "32bit"
                else:
                    version = "16bit"
            system = "Windows"
        elif system[:4] == "java":
            (release, vendor, vminfo, osinfo) = java_ver()
            system = "Java"
            version = ", ".join(vminfo)
            if not version:
                version = vendor
    if system == "OpenVMS":
        if (not release) or (release == "0"):
            release = version
            version = ""
    if (system == "Microsoft") and (release == "Windows"):
        system = "Windows"
        release = "Vista"
    vals = (system, node, release, version, machine)
    _uname_cache = uname_result(*map(_unknown_as_blank, vals))
    return _uname_cache


def system():
    " Returns the system/OS name, e.g. 'Linux', 'Windows' or 'Java'.\n\n        An empty string is returned if the value cannot be determined.\n\n    "
    return uname().system


def node():
    " Returns the computer's network name (which may not be fully\n        qualified)\n\n        An empty string is returned if the value cannot be determined.\n\n    "
    return uname().node


def release():
    " Returns the system's release, e.g. '2.2.0' or 'NT'\n\n        An empty string is returned if the value cannot be determined.\n\n    "
    return uname().release


def version():
    " Returns the system's release version, e.g. '#3 on degas'\n\n        An empty string is returned if the value cannot be determined.\n\n    "
    return uname().version


def machine():
    " Returns the machine type, e.g. 'i386'\n\n        An empty string is returned if the value cannot be determined.\n\n    "
    return uname().machine


def processor():
    " Returns the (true) processor name, e.g. 'amdk6'\n\n        An empty string is returned if the value cannot be\n        determined. Note that many platforms do not provide this\n        information or simply return the same value as for machine(),\n        e.g.  NetBSD does this.\n\n    "
    return uname().processor


_sys_version_parser = re.compile(
    "([\\w.+]+)\\s*\\(#?([^,]+)(?:,\\s*([\\w ]*)(?:,\\s*([\\w :]*))?)?\\)\\s*\\[([^\\]]+)\\]?",
    re.ASCII,
)
_ironpython_sys_version_parser = re.compile(
    "IronPython\\s*([\\d\\.]+)(?: \\(([\\d\\.]+)\\))? on (.NET [\\d\\.]+)", re.ASCII
)
_ironpython26_sys_version_parser = re.compile(
    "([\\d.]+)\\s*\\(IronPython\\s*[\\d.]+\\s*\\(([\\d.]+)\\) on ([\\w.]+ [\\d.]+(?: \\(\\d+-bit\\))?)\\)"
)
_pypy_sys_version_parser = re.compile(
    "([\\w.+]+)\\s*\\(#?([^,]+),\\s*([\\w ]+),\\s*([\\w :]+)\\)\\s*\\[PyPy [^\\]]+\\]?"
)
_sys_version_cache = {}


def _sys_version(sys_version=None):
    " Returns a parsed version of Python's sys.version as tuple\n        (name, version, branch, revision, buildno, builddate, compiler)\n        referring to the Python implementation name, version, branch,\n        revision, build number, build date/time as string and the compiler\n        identification string.\n\n        Note that unlike the Python sys.version, the returned value\n        for the Python version will always include the patchlevel (it\n        defaults to '.0').\n\n        The function returns empty strings for tuple entries that\n        cannot be determined.\n\n        sys_version may be given to parse an alternative version\n        string, e.g. if the version was read from a different Python\n        interpreter.\n\n    "
    if sys_version is None:
        sys_version = sys.version
    result = _sys_version_cache.get(sys_version, None)
    if result is not None:
        return result
    if "IronPython" in sys_version:
        name = "IronPython"
        if sys_version.startswith("IronPython"):
            match = _ironpython_sys_version_parser.match(sys_version)
        else:
            match = _ironpython26_sys_version_parser.match(sys_version)
        if match is None:
            raise ValueError(
                ("failed to parse IronPython sys.version: %s" % repr(sys_version))
            )
        (version, alt_version, compiler) = match.groups()
        buildno = ""
        builddate = ""
    elif sys.platform.startswith("java"):
        name = "Jython"
        match = _sys_version_parser.match(sys_version)
        if match is None:
            raise ValueError(
                ("failed to parse Jython sys.version: %s" % repr(sys_version))
            )
        (version, buildno, builddate, buildtime, _) = match.groups()
        if builddate is None:
            builddate = ""
        compiler = sys.platform
    elif "PyPy" in sys_version:
        name = "PyPy"
        match = _pypy_sys_version_parser.match(sys_version)
        if match is None:
            raise ValueError(
                ("failed to parse PyPy sys.version: %s" % repr(sys_version))
            )
        (version, buildno, builddate, buildtime) = match.groups()
        compiler = ""
    else:
        match = _sys_version_parser.match(sys_version)
        if match is None:
            raise ValueError(
                ("failed to parse CPython sys.version: %s" % repr(sys_version))
            )
        (version, buildno, builddate, buildtime, compiler) = match.groups()
        name = "CPython"
        if builddate is None:
            builddate = ""
        elif buildtime:
            builddate = (builddate + " ") + buildtime
    if hasattr(sys, "_git"):
        (_, branch, revision) = sys._git
    elif hasattr(sys, "_mercurial"):
        (_, branch, revision) = sys._mercurial
    else:
        branch = ""
        revision = ""
    l = version.split(".")
    if len(l) == 2:
        l.append("0")
        version = ".".join(l)
    result = (name, version, branch, revision, buildno, builddate, compiler)
    _sys_version_cache[sys_version] = result
    return result


def python_implementation():
    " Returns a string identifying the Python implementation.\n\n        Currently, the following implementations are identified:\n          'CPython' (C implementation of Python),\n          'IronPython' (.NET implementation of Python),\n          'Jython' (Java implementation of Python),\n          'PyPy' (Python implementation of Python).\n\n    "
    return _sys_version()[0]


def python_version():
    " Returns the Python version as string 'major.minor.patchlevel'\n\n        Note that unlike the Python sys.version, the returned value\n        will always include the patchlevel (it defaults to 0).\n\n    "
    return _sys_version()[1]


def python_version_tuple():
    " Returns the Python version as tuple (major, minor, patchlevel)\n        of strings.\n\n        Note that unlike the Python sys.version, the returned value\n        will always include the patchlevel (it defaults to 0).\n\n    "
    return tuple(_sys_version()[1].split("."))


def python_branch():
    " Returns a string identifying the Python implementation\n        branch.\n\n        For CPython this is the SCM branch from which the\n        Python binary was built.\n\n        If not available, an empty string is returned.\n\n    "
    return _sys_version()[2]


def python_revision():
    " Returns a string identifying the Python implementation\n        revision.\n\n        For CPython this is the SCM revision from which the\n        Python binary was built.\n\n        If not available, an empty string is returned.\n\n    "
    return _sys_version()[3]


def python_build():
    " Returns a tuple (buildno, builddate) stating the Python\n        build number and date as strings.\n\n    "
    return _sys_version()[4:6]


def python_compiler():
    " Returns a string identifying the compiler used for compiling\n        Python.\n\n    "
    return _sys_version()[6]


_platform_cache = {}


def platform(aliased=0, terse=0):
    ' Returns a single string identifying the underlying platform\n        with as much useful information as possible (but no more :).\n\n        The output is intended to be human readable rather than\n        machine parseable. It may look different on different\n        platforms and this is intended.\n\n        If "aliased" is true, the function will use aliases for\n        various platforms that report system names which differ from\n        their common names, e.g. SunOS will be reported as\n        Solaris. The system_alias() function is used to implement\n        this.\n\n        Setting terse to true causes the function to return only the\n        absolute minimum information needed to identify the platform.\n\n    '
    result = _platform_cache.get((aliased, terse), None)
    if result is not None:
        return result
    (system, node, release, version, machine, processor) = uname()
    if machine == processor:
        processor = ""
    if aliased:
        (system, release, version) = system_alias(system, release, version)
    if system == "Darwin":
        macos_release = mac_ver()[0]
        if macos_release:
            system = "macOS"
            release = macos_release
    if system == "Windows":
        (rel, vers, csd, ptype) = win32_ver(version)
        if terse:
            platform = _platform(system, release)
        else:
            platform = _platform(system, release, version, csd)
    elif system in ("Linux",):
        (libcname, libcversion) = libc_ver()
        platform = _platform(
            system, release, machine, processor, "with", (libcname + libcversion)
        )
    elif system == "Java":
        (r, v, vminfo, (os_name, os_version, os_arch)) = java_ver()
        if terse or (not os_name):
            platform = _platform(system, release, version)
        else:
            platform = _platform(
                system, release, version, "on", os_name, os_version, os_arch
            )
    elif terse:
        platform = _platform(system, release)
    else:
        (bits, linkage) = architecture(sys.executable)
        platform = _platform(system, release, machine, processor, bits, linkage)
    _platform_cache[(aliased, terse)] = platform
    return platform


_os_release_line = re.compile(
    "^(?P<name>[a-zA-Z0-9_]+)=(?P<quote>[\"']?)(?P<value>.*)(?P=quote)$"
)
_os_release_unescape = re.compile("\\\\([\\\\\\$\\\"\\'`])")
_os_release_candidates = ("/etc/os-release", "/usr/lib/os-release")
_os_release_cache = None


def _parse_os_release(lines):
    info = {"NAME": "Linux", "ID": "linux", "PRETTY_NAME": "Linux"}
    for line in lines:
        mo = _os_release_line.match(line)
        if mo is not None:
            info[mo.group("name")] = _os_release_unescape.sub("\\1", mo.group("value"))
    return info


def freedesktop_os_release():
    "Return operation system identification from freedesktop.org os-release\n    "
    global _os_release_cache
    if _os_release_cache is None:
        errno = None
        for candidate in _os_release_candidates:
            try:
                with open(candidate, encoding="utf-8") as f:
                    _os_release_cache = _parse_os_release(f)
                break
            except OSError as e:
                errno = e.errno
        else:
            raise OSError(
                errno, f"Unable to read files {', '.join(_os_release_candidates)}"
            )
    return _os_release_cache.copy()


if __name__ == "__main__":
    terse = ("terse" in sys.argv) or ("--terse" in sys.argv)
    aliased = (not ("nonaliased" in sys.argv)) and (not ("--nonaliased" in sys.argv))
    print(platform(aliased, terse))
    sys.exit(0)
