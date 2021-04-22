"Provide access to Python's configuration information.  The specific\nconfiguration variables available depend heavily on the platform and\nconfiguration.  The values may be retrieved using\nget_config_var(name), and the list of variables is available via\nget_config_vars().keys().  Additional convenience functions are also\navailable.\n\nWritten by:   Fred L. Drake, Jr.\nEmail:        <fdrake@acm.org>\n"
import _imp
import os
import re
import sys
from .errors import DistutilsPlatformError

PREFIX = os.path.normpath(sys.prefix)
EXEC_PREFIX = os.path.normpath(sys.exec_prefix)
BASE_PREFIX = os.path.normpath(sys.base_prefix)
BASE_EXEC_PREFIX = os.path.normpath(sys.base_exec_prefix)
if "_PYTHON_PROJECT_BASE" in os.environ:
    project_base = os.path.abspath(os.environ["_PYTHON_PROJECT_BASE"])
elif sys.executable:
    project_base = os.path.dirname(os.path.abspath(sys.executable))
else:
    project_base = os.getcwd()


def _is_python_source_dir(d):
    for fn in ("Setup", "Setup.local"):
        if os.path.isfile(os.path.join(d, "Modules", fn)):
            return True
    return False


_sys_home = getattr(sys, "_home", None)
if os.name == "nt":

    def _fix_pcbuild(d):
        if d and os.path.normcase(d).startswith(
            os.path.normcase(os.path.join(PREFIX, "PCbuild"))
        ):
            return PREFIX
        return d

    project_base = _fix_pcbuild(project_base)
    _sys_home = _fix_pcbuild(_sys_home)


def _python_build():
    if _sys_home:
        return _is_python_source_dir(_sys_home)
    return _is_python_source_dir(project_base)


python_build = _python_build()
build_flags = ""
try:
    if not python_build:
        build_flags = sys.abiflags
except AttributeError:
    pass


def get_python_version():
    "Return a string containing the major and minor Python version,\n    leaving off the patchlevel.  Sample return values could be '1.5'\n    or '2.2'.\n    "
    return "%d.%d" % sys.version_info[:2]


def get_python_inc(plat_specific=0, prefix=None):
    "Return the directory containing installed Python header files.\n\n    If 'plat_specific' is false (the default), this is the path to the\n    non-platform-specific header files, i.e. Python.h and so on;\n    otherwise, this is the path to platform-specific header files\n    (namely pyconfig.h).\n\n    If 'prefix' is supplied, use it instead of sys.base_prefix or\n    sys.base_exec_prefix -- i.e., ignore 'plat_specific'.\n    "
    if prefix is None:
        prefix = (plat_specific and BASE_EXEC_PREFIX) or BASE_PREFIX
    if os.name == "posix":
        if python_build:
            if plat_specific:
                return _sys_home or project_base
            else:
                incdir = os.path.join(get_config_var("srcdir"), "Include")
                return os.path.normpath(incdir)
        python_dir = ("python" + get_python_version()) + build_flags
        return os.path.join(prefix, "include", python_dir)
    elif os.name == "nt":
        if python_build:
            return (os.path.join(prefix, "include") + os.path.pathsep) + os.path.join(
                prefix, "PC"
            )
        return os.path.join(prefix, "include")
    else:
        raise DistutilsPlatformError(
            (
                "I don't know where Python installs its C header files on platform '%s'"
                % os.name
            )
        )


def get_python_lib(plat_specific=0, standard_lib=0, prefix=None):
    "Return the directory containing the Python library (standard or\n    site additions).\n\n    If 'plat_specific' is true, return the directory containing\n    platform-specific modules, i.e. any module from a non-pure-Python\n    module distribution; otherwise, return the platform-shared library\n    directory.  If 'standard_lib' is true, return the directory\n    containing standard Python library modules; otherwise, return the\n    directory for site-specific modules.\n\n    If 'prefix' is supplied, use it instead of sys.base_prefix or\n    sys.base_exec_prefix -- i.e., ignore 'plat_specific'.\n    "
    if prefix is None:
        if standard_lib:
            prefix = (plat_specific and BASE_EXEC_PREFIX) or BASE_PREFIX
        else:
            prefix = (plat_specific and EXEC_PREFIX) or PREFIX
    if os.name == "posix":
        if plat_specific or standard_lib:
            libdir = sys.platlibdir
        else:
            libdir = "lib"
        libpython = os.path.join(prefix, libdir, ("python" + get_python_version()))
        if standard_lib:
            return libpython
        else:
            return os.path.join(libpython, "site-packages")
    elif os.name == "nt":
        if standard_lib:
            return os.path.join(prefix, "Lib")
        else:
            return os.path.join(prefix, "Lib", "site-packages")
    else:
        raise DistutilsPlatformError(
            (
                "I don't know where Python installs its library on platform '%s'"
                % os.name
            )
        )


def customize_compiler(compiler):
    "Do any platform-specific customization of a CCompiler instance.\n\n    Mainly needed on Unix, so we can plug in the information that\n    varies across Unices and is stored in Python's Makefile.\n    "
    if compiler.compiler_type == "unix":
        if sys.platform == "darwin":
            global _config_vars
            if not get_config_var("CUSTOMIZED_OSX_COMPILER"):
                import _osx_support

                _osx_support.customize_compiler(_config_vars)
                _config_vars["CUSTOMIZED_OSX_COMPILER"] = "True"
        (
            cc,
            cxx,
            cflags,
            ccshared,
            ldshared,
            shlib_suffix,
            ar,
            ar_flags,
        ) = get_config_vars(
            "CC",
            "CXX",
            "CFLAGS",
            "CCSHARED",
            "LDSHARED",
            "SHLIB_SUFFIX",
            "AR",
            "ARFLAGS",
        )
        if "CC" in os.environ:
            newcc = os.environ["CC"]
            if (
                (sys.platform == "darwin")
                and ("LDSHARED" not in os.environ)
                and ldshared.startswith(cc)
            ):
                ldshared = newcc + ldshared[len(cc) :]
            cc = newcc
        if "CXX" in os.environ:
            cxx = os.environ["CXX"]
        if "LDSHARED" in os.environ:
            ldshared = os.environ["LDSHARED"]
        if "CPP" in os.environ:
            cpp = os.environ["CPP"]
        else:
            cpp = cc + " -E"
        if "LDFLAGS" in os.environ:
            ldshared = (ldshared + " ") + os.environ["LDFLAGS"]
        if "CFLAGS" in os.environ:
            cflags = (cflags + " ") + os.environ["CFLAGS"]
            ldshared = (ldshared + " ") + os.environ["CFLAGS"]
        if "CPPFLAGS" in os.environ:
            cpp = (cpp + " ") + os.environ["CPPFLAGS"]
            cflags = (cflags + " ") + os.environ["CPPFLAGS"]
            ldshared = (ldshared + " ") + os.environ["CPPFLAGS"]
        if "AR" in os.environ:
            ar = os.environ["AR"]
        if "ARFLAGS" in os.environ:
            archiver = (ar + " ") + os.environ["ARFLAGS"]
        else:
            archiver = (ar + " ") + ar_flags
        cc_cmd = (cc + " ") + cflags
        compiler.set_executables(
            preprocessor=cpp,
            compiler=cc_cmd,
            compiler_so=((cc_cmd + " ") + ccshared),
            compiler_cxx=cxx,
            linker_so=ldshared,
            linker_exe=cc,
            archiver=archiver,
        )
        compiler.shared_lib_extension = shlib_suffix


def get_config_h_filename():
    "Return full pathname of installed pyconfig.h file."
    if python_build:
        if os.name == "nt":
            inc_dir = os.path.join((_sys_home or project_base), "PC")
        else:
            inc_dir = _sys_home or project_base
    else:
        inc_dir = get_python_inc(plat_specific=1)
    return os.path.join(inc_dir, "pyconfig.h")


def get_makefile_filename():
    "Return full pathname of installed Makefile from the Python build."
    if python_build:
        return os.path.join((_sys_home or project_base), "Makefile")
    lib_dir = get_python_lib(plat_specific=0, standard_lib=1)
    config_file = "config-{}{}".format(get_python_version(), build_flags)
    if hasattr(sys.implementation, "_multiarch"):
        config_file += "-%s" % sys.implementation._multiarch
    return os.path.join(lib_dir, config_file, "Makefile")


def parse_config_h(fp, g=None):
    "Parse a config.h-style file.\n\n    A dictionary containing name/value pairs is returned.  If an\n    optional dictionary is passed in as the second argument, it is\n    used instead of a new dictionary.\n    "
    if g is None:
        g = {}
    define_rx = re.compile("#define ([A-Z][A-Za-z0-9_]+) (.*)\n")
    undef_rx = re.compile("/[*] #undef ([A-Z][A-Za-z0-9_]+) [*]/\n")
    while True:
        line = fp.readline()
        if not line:
            break
        m = define_rx.match(line)
        if m:
            (n, v) = m.group(1, 2)
            try:
                v = int(v)
            except ValueError:
                pass
            g[n] = v
        else:
            m = undef_rx.match(line)
            if m:
                g[m.group(1)] = 0
    return g


_variable_rx = re.compile("([a-zA-Z][a-zA-Z0-9_]+)\\s*=\\s*(.*)")
_findvar1_rx = re.compile("\\$\\(([A-Za-z][A-Za-z0-9_]*)\\)")
_findvar2_rx = re.compile("\\${([A-Za-z][A-Za-z0-9_]*)}")


def parse_makefile(fn, g=None):
    "Parse a Makefile-style file.\n\n    A dictionary containing name/value pairs is returned.  If an\n    optional dictionary is passed in as the second argument, it is\n    used instead of a new dictionary.\n    "
    from distutils.text_file import TextFile

    fp = TextFile(
        fn, strip_comments=1, skip_blanks=1, join_lines=1, errors="surrogateescape"
    )
    if g is None:
        g = {}
    done = {}
    notdone = {}
    while True:
        line = fp.readline()
        if line is None:
            break
        m = _variable_rx.match(line)
        if m:
            (n, v) = m.group(1, 2)
            v = v.strip()
            tmpv = v.replace("$$", "")
            if "$" in tmpv:
                notdone[n] = v
            else:
                try:
                    v = int(v)
                except ValueError:
                    done[n] = v.replace("$$", "$")
                else:
                    done[n] = v
    renamed_variables = ("CFLAGS", "LDFLAGS", "CPPFLAGS")
    while notdone:
        for name in list(notdone):
            value = notdone[name]
            m = _findvar1_rx.search(value) or _findvar2_rx.search(value)
            if m:
                n = m.group(1)
                found = True
                if n in done:
                    item = str(done[n])
                elif n in notdone:
                    found = False
                elif n in os.environ:
                    item = os.environ[n]
                elif n in renamed_variables:
                    if name.startswith("PY_") and (name[3:] in renamed_variables):
                        item = ""
                    elif ("PY_" + n) in notdone:
                        found = False
                    else:
                        item = str(done[("PY_" + n)])
                else:
                    done[n] = item = ""
                if found:
                    after = value[m.end() :]
                    value = (value[: m.start()] + item) + after
                    if "$" in after:
                        notdone[name] = value
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            done[name] = value.strip()
                        else:
                            done[name] = value
                        del notdone[name]
                        if name.startswith("PY_") and (name[3:] in renamed_variables):
                            name = name[3:]
                            if name not in done:
                                done[name] = value
            else:
                del notdone[name]
    fp.close()
    for (k, v) in done.items():
        if isinstance(v, str):
            done[k] = v.strip()
    g.update(done)
    return g


def expand_makefile_vars(s, vars):
    "Expand Makefile-style variables -- \"${foo}\" or \"$(foo)\" -- in\n    'string' according to 'vars' (a dictionary mapping variable names to\n    values).  Variables not present in 'vars' are silently expanded to the\n    empty string.  The variable values in 'vars' should not contain further\n    variable expansions; if 'vars' is the output of 'parse_makefile()',\n    you're fine.  Returns a variable-expanded version of 's'.\n    "
    while True:
        m = _findvar1_rx.search(s) or _findvar2_rx.search(s)
        if m:
            (beg, end) = m.span()
            s = (s[0:beg] + vars.get(m.group(1))) + s[end:]
        else:
            break
    return s


_config_vars = None


def _init_posix():
    "Initialize the module as appropriate for POSIX systems."
    name = os.environ.get(
        "_PYTHON_SYSCONFIGDATA_NAME",
        "_sysconfigdata_{abi}_{platform}_{multiarch}".format(
            abi=sys.abiflags,
            platform=sys.platform,
            multiarch=getattr(sys.implementation, "_multiarch", ""),
        ),
    )
    _temp = __import__(name, globals(), locals(), ["build_time_vars"], 0)
    build_time_vars = _temp.build_time_vars
    global _config_vars
    _config_vars = {}
    _config_vars.update(build_time_vars)


def _init_nt():
    "Initialize the module as appropriate for NT"
    g = {}
    g["LIBDEST"] = get_python_lib(plat_specific=0, standard_lib=1)
    g["BINLIBDEST"] = get_python_lib(plat_specific=1, standard_lib=1)
    g["INCLUDEPY"] = get_python_inc(plat_specific=0)
    g["EXT_SUFFIX"] = _imp.extension_suffixes()[0]
    g["EXE"] = ".exe"
    g["VERSION"] = get_python_version().replace(".", "")
    g["BINDIR"] = os.path.dirname(os.path.abspath(sys.executable))
    global _config_vars
    _config_vars = g


def get_config_vars(*args):
    "With no arguments, return a dictionary of all configuration\n    variables relevant for the current platform.  Generally this includes\n    everything needed to build extensions and install both pure modules and\n    extensions.  On Unix, this means every variable defined in Python's\n    installed Makefile; on Windows it's a much smaller set.\n\n    With arguments, return a list of values that result from looking up\n    each argument in the configuration variable dictionary.\n    "
    global _config_vars
    if _config_vars is None:
        func = globals().get(("_init_" + os.name))
        if func:
            func()
        else:
            _config_vars = {}
        _config_vars["prefix"] = PREFIX
        _config_vars["exec_prefix"] = EXEC_PREFIX
        SO = _config_vars.get("EXT_SUFFIX")
        if SO is not None:
            _config_vars["SO"] = SO
        srcdir = _config_vars.get("srcdir", project_base)
        if os.name == "posix":
            if python_build:
                base = os.path.dirname(get_makefile_filename())
                srcdir = os.path.join(base, srcdir)
            else:
                srcdir = os.path.dirname(get_makefile_filename())
        _config_vars["srcdir"] = os.path.abspath(os.path.normpath(srcdir))
        if python_build and (os.name == "posix"):
            base = project_base
            if (not os.path.isabs(_config_vars["srcdir"])) and (base != os.getcwd()):
                srcdir = os.path.join(base, _config_vars["srcdir"])
                _config_vars["srcdir"] = os.path.normpath(srcdir)
        if sys.platform == "darwin":
            import _osx_support

            _osx_support.customize_config_vars(_config_vars)
    if args:
        vals = []
        for name in args:
            vals.append(_config_vars.get(name))
        return vals
    else:
        return _config_vars


def get_config_var(name):
    "Return the value of a single variable using the dictionary\n    returned by 'get_config_vars()'.  Equivalent to\n    get_config_vars().get(name)\n    "
    if name == "SO":
        import warnings

        warnings.warn("SO is deprecated, use EXT_SUFFIX", DeprecationWarning, 2)
    return get_config_vars().get(name)
