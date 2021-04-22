"Shared AIX support functions."
import sys
import sysconfig

try:
    import subprocess
except ImportError:
    import _bootsubprocess as subprocess


def _aix_tag(vrtl, bd):
    _sz = 32 if (sys.maxsize == ((2 ** 31) - 1)) else 64
    return "aix-{:1x}{:1d}{:02d}-{:04d}-{}".format(vrtl[0], vrtl[1], vrtl[2], bd, _sz)


def _aix_vrtl(vrmf):
    (v, r, tl) = vrmf.split(".")[:3]
    return [int(v[(-1)]), int(r), int(tl)]


def _aix_bosmp64():
    "\n    Return a Tuple[str, int] e.g., ['7.1.4.34', 1806]\n    The fileset bos.mp64 is the AIX kernel. It's VRMF and builddate\n    reflect the current ABI levels of the runtime environment.\n    "
    out = subprocess.check_output(["/usr/bin/lslpp", "-Lqc", "bos.mp64"])
    out = out.decode("utf-8")
    out = out.strip().split(":")
    return (str(out[2]), int(out[(-1)]))


def aix_platform():
    '\n    AIX filesets are identified by four decimal values: V.R.M.F.\n    V (version) and R (release) can be retreived using ``uname``\n    Since 2007, starting with AIX 5.3 TL7, the M value has been\n    included with the fileset bos.mp64 and represents the Technology\n    Level (TL) of AIX. The F (Fix) value also increases, but is not\n    relevant for comparing releases and binary compatibility.\n    For binary compatibility the so-called builddate is needed.\n    Again, the builddate of an AIX release is associated with bos.mp64.\n    AIX ABI compatibility is described  as guaranteed at: https://www.ibm.com/    support/knowledgecenter/en/ssw_aix_72/install/binary_compatability.html\n\n    For pep425 purposes the AIX platform tag becomes:\n    "aix-{:1x}{:1d}{:02d}-{:04d}-{}".format(v, r, tl, builddate, bitsize)\n    e.g., "aix-6107-1415-32" for AIX 6.1 TL7 bd 1415, 32-bit\n    and, "aix-6107-1415-64" for AIX 6.1 TL7 bd 1415, 64-bit\n    '
    (vrmf, bd) = _aix_bosmp64()
    return _aix_tag(_aix_vrtl(vrmf), bd)


def _aix_bgt():
    gnu_type = sysconfig.get_config_var("BUILD_GNU_TYPE")
    if not gnu_type:
        raise ValueError("BUILD_GNU_TYPE is not defined")
    return _aix_vrtl(vrmf=gnu_type)


def aix_buildtag():
    "\n    Return the platform_tag of the system Python was built on.\n    "
    build_date = sysconfig.get_config_var("AIX_BUILDDATE")
    try:
        build_date = int(build_date)
    except (ValueError, TypeError):
        raise ValueError(f"AIX_BUILDDATE is not defined or invalid: {build_date!r}")
    return _aix_tag(_aix_bgt(), build_date)
