import argparse
import importlib._bootstrap
import importlib.machinery
import importlib.util
import os
import re
import sys
import sysconfig
import warnings
from glob import glob, escape
import _osx_support

try:
    import subprocess

    del subprocess
    SUBPROCESS_BOOTSTRAP = False
except ImportError:
    import _bootsubprocess

    sys.modules["subprocess"] = _bootsubprocess
    del _bootsubprocess
    SUBPROCESS_BOOTSTRAP = True
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore", "The distutils package is deprecated", DeprecationWarning
    )
    from distutils import log
    from distutils.command.build_ext import build_ext
    from distutils.command.build_scripts import build_scripts
    from distutils.command.install import install
    from distutils.command.install_lib import install_lib
    from distutils.core import Extension, setup
    from distutils.errors import CCompilerError, DistutilsError
    from distutils.spawn import find_executable
TEST_EXTENSIONS = sysconfig.get_config_var("TEST_MODULES") == "yes"
DISABLED_MODULE_LIST = []
LIST_MODULE_NAMES = False


def get_platform():
    if "_PYTHON_HOST_PLATFORM" in os.environ:
        return os.environ["_PYTHON_HOST_PLATFORM"]
    if sys.platform.startswith("osf1"):
        return "osf1"
    return sys.platform


CROSS_COMPILING = "_PYTHON_HOST_PLATFORM" in os.environ
HOST_PLATFORM = get_platform()
MS_WINDOWS = HOST_PLATFORM == "win32"
CYGWIN = HOST_PLATFORM == "cygwin"
MACOS = HOST_PLATFORM == "darwin"
AIX = HOST_PLATFORM.startswith("aix")
VXWORKS = "vxworks" in HOST_PLATFORM
SUMMARY = "\nPython is an interpreted, interactive, object-oriented programming\nlanguage. It is often compared to Tcl, Perl, Scheme or Java.\n\nPython combines remarkable power with very clear syntax. It has\nmodules, classes, exceptions, very high level dynamic data types, and\ndynamic typing. There are interfaces to many system calls and\nlibraries, as well as to various windowing systems (X11, Motif, Tk,\nMac, MFC). New built-in modules are easily written in C or C++. Python\nis also usable as an extension language for applications that need a\nprogrammable interface.\n\nThe Python implementation is portable: it runs on many brands of UNIX,\non Windows, DOS, Mac, Amiga... If your favorite system isn't\nlisted here, it may still be supported, if there's a C compiler for\nit. Ask around on comp.lang.python -- or just try compiling Python\nyourself.\n"
CLASSIFIERS = "\nDevelopment Status :: 6 - Mature\nLicense :: OSI Approved :: Python Software Foundation License\nNatural Language :: English\nProgramming Language :: C\nProgramming Language :: Python\nTopic :: Software Development\n"


def run_command(cmd):
    status = os.system(cmd)
    return os.waitstatus_to_exitcode(status)


def set_compiler_flags(compiler_flags, compiler_py_flags_nodist):
    flags = sysconfig.get_config_var(compiler_flags)
    py_flags_nodist = sysconfig.get_config_var(compiler_py_flags_nodist)
    sysconfig.get_config_vars()[compiler_flags] = (flags + " ") + py_flags_nodist


def add_dir_to_list(dirlist, dir):
    "Add the directory 'dir' to the list 'dirlist' (after any relative\n    directories) if:\n\n    1) 'dir' is not already in 'dirlist'\n    2) 'dir' actually exists, and is a directory.\n    "
    if (dir is None) or (not os.path.isdir(dir)) or (dir in dirlist):
        return
    for (i, path) in enumerate(dirlist):
        if not os.path.isabs(path):
            dirlist.insert((i + 1), dir)
            return
    dirlist.insert(0, dir)


def sysroot_paths(make_vars, subdirs):
    "Get the paths of sysroot sub-directories.\n\n    * make_vars: a sequence of names of variables of the Makefile where\n      sysroot may be set.\n    * subdirs: a sequence of names of subdirectories used as the location for\n      headers or libraries.\n    "
    dirs = []
    for var_name in make_vars:
        var = sysconfig.get_config_var(var_name)
        if var is not None:
            m = re.search('--sysroot=([^"]\\S*|"[^"]+")', var)
            if m is not None:
                sysroot = m.group(1).strip('"')
                for subdir in subdirs:
                    if os.path.isabs(subdir):
                        subdir = subdir[1:]
                    path = os.path.join(sysroot, subdir)
                    if os.path.isdir(path):
                        dirs.append(path)
                break
    return dirs


MACOS_SDK_ROOT = None
MACOS_SDK_SPECIFIED = None


def macosx_sdk_root():
    "Return the directory of the current macOS SDK.\n\n    If no SDK was explicitly configured, call the compiler to find which\n    include files paths are being searched by default.  Use '/' if the\n    compiler is searching /usr/include (meaning system header files are\n    installed) or use the root of an SDK if that is being searched.\n    (The SDK may be supplied via Xcode or via the Command Line Tools).\n    The SDK paths used by Apple-supplied tool chains depend on the\n    setting of various variables; see the xcrun man page for more info.\n    Also sets MACOS_SDK_SPECIFIED for use by macosx_sdk_specified().\n    "
    global MACOS_SDK_ROOT, MACOS_SDK_SPECIFIED
    if MACOS_SDK_ROOT:
        return MACOS_SDK_ROOT
    cflags = sysconfig.get_config_var("CFLAGS")
    m = re.search("-isysroot\\s*(\\S+)", cflags)
    if m is not None:
        MACOS_SDK_ROOT = m.group(1)
        MACOS_SDK_SPECIFIED = MACOS_SDK_ROOT != "/"
    else:
        MACOS_SDK_ROOT = _osx_support._default_sysroot(sysconfig.get_config_var("CC"))
        MACOS_SDK_SPECIFIED = False
    return MACOS_SDK_ROOT


def macosx_sdk_specified():
    "Returns true if an SDK was explicitly configured.\n\n    True if an SDK was selected at configure time, either by specifying\n    --enable-universalsdk=(something other than no or /) or by adding a\n    -isysroot option to CFLAGS.  In some cases, like when making\n    decisions about macOS Tk framework paths, we need to be able to\n    know whether the user explicitly asked to build with an SDK versus\n    the implicit use of an SDK when header files are no longer\n    installed on a running system by the Command Line Tools.\n    "
    global MACOS_SDK_SPECIFIED
    if MACOS_SDK_SPECIFIED:
        return MACOS_SDK_SPECIFIED
    macosx_sdk_root()
    return MACOS_SDK_SPECIFIED


def is_macosx_sdk_path(path):
    "\n    Returns True if 'path' can be located in an OSX SDK\n    "
    return (
        (path.startswith("/usr/") and (not path.startswith("/usr/local")))
        or path.startswith("/System/")
        or path.startswith("/Library/")
    )


def grep_headers_for(function, headers):
    for header in headers:
        with open(header, "r", errors="surrogateescape") as f:
            if function in f.read():
                return True
    return False


def find_file(filename, std_dirs, paths):
    "Searches for the directory where a given file is located,\n    and returns a possibly-empty list of additional directories, or None\n    if the file couldn't be found at all.\n\n    'filename' is the name of a file, such as readline.h or libcrypto.a.\n    'std_dirs' is the list of standard system directories; if the\n        file is found in one of them, no additional directives are needed.\n    'paths' is a list of additional locations to check; if the file is\n        found in one of them, the resulting list will contain the directory.\n    "
    if MACOS:
        sysroot = macosx_sdk_root()
    for dir in std_dirs:
        f = os.path.join(dir, filename)
        if MACOS and is_macosx_sdk_path(dir):
            f = os.path.join(sysroot, dir[1:], filename)
        if os.path.exists(f):
            return []
    for dir in paths:
        f = os.path.join(dir, filename)
        if MACOS and is_macosx_sdk_path(dir):
            f = os.path.join(sysroot, dir[1:], filename)
        if os.path.exists(f):
            return [dir]
    return None


def find_library_file(compiler, libname, std_dirs, paths):
    result = compiler.find_library_file((std_dirs + paths), libname)
    if result is None:
        return None
    if MACOS:
        sysroot = macosx_sdk_root()
    dirname = os.path.dirname(result)
    for p in std_dirs:
        p = p.rstrip(os.sep)
        if MACOS and is_macosx_sdk_path(p):
            if os.path.join(sysroot, p[1:]) == dirname:
                return []
        if p == dirname:
            return []
    for p in paths:
        p = p.rstrip(os.sep)
        if MACOS and is_macosx_sdk_path(p):
            if os.path.join(sysroot, p[1:]) == dirname:
                return [p]
        if p == dirname:
            return [p]
    else:
        assert False, "Internal error: Path not found in std_dirs or paths"


def validate_tzpath():
    base_tzpath = sysconfig.get_config_var("TZPATH")
    if not base_tzpath:
        return
    tzpaths = base_tzpath.split(os.pathsep)
    bad_paths = [tzpath for tzpath in tzpaths if (not os.path.isabs(tzpath))]
    if bad_paths:
        raise ValueError(
            (
                (
                    "TZPATH must contain only absolute paths, "
                    + f"""found:
{tzpaths!r}
with invalid paths:
"""
                )
                + f"{bad_paths!r}"
            )
        )


def find_module_file(module, dirlist):
    "Find a module in a set of possible folders. If it is not found\n    return the unadorned filename"
    list = find_file(module, [], dirlist)
    if not list:
        return module
    if len(list) > 1:
        log.info("WARNING: multiple copies of %s found", module)
    return os.path.join(list[0], module)


class PyBuildExt(build_ext):
    def __init__(self, dist):
        build_ext.__init__(self, dist)
        self.srcdir = None
        self.lib_dirs = None
        self.inc_dirs = None
        self.config_h_vars = None
        self.failed = []
        self.failed_on_import = []
        self.missing = []
        self.disabled_configure = []
        if "-j" in os.environ.get("MAKEFLAGS", ""):
            self.parallel = True

    def add(self, ext):
        self.extensions.append(ext)

    def set_srcdir(self):
        self.srcdir = sysconfig.get_config_var("srcdir")
        if not self.srcdir:
            raise ValueError("No source directory; cannot proceed.")
        self.srcdir = os.path.abspath(self.srcdir)

    def remove_disabled(self):
        extensions = [
            ext for ext in self.extensions if (ext.name not in DISABLED_MODULE_LIST)
        ]
        ext_map = dict(((ext.name, i) for (i, ext) in enumerate(extensions)))
        if "_ctypes" in ext_map:
            ctypes = extensions.pop(ext_map["_ctypes"])
            extensions.append(ctypes)
        self.extensions = extensions

    def update_sources_depends(self):
        moddirlist = [os.path.join(self.srcdir, "Modules")]
        self.distribution.scripts = [
            os.path.join(self.srcdir, filename)
            for filename in self.distribution.scripts
        ]
        headers = [sysconfig.get_config_h_filename()]
        headers += glob(os.path.join(escape(sysconfig.get_path("include")), "*.h"))
        for ext in self.extensions:
            ext.sources = [
                find_module_file(filename, moddirlist) for filename in ext.sources
            ]
            if ext.depends is not None:
                ext.depends = [
                    find_module_file(filename, moddirlist) for filename in ext.depends
                ]
            else:
                ext.depends = []
            ext.depends.extend(headers)

    def remove_configured_extensions(self):
        sysconf_built = sysconfig.get_config_var("MODBUILT_NAMES").split()
        sysconf_dis = sysconfig.get_config_var("MODDISABLED_NAMES").split()
        mods_built = []
        mods_disabled = []
        for ext in self.extensions:
            if ext.name in sysconf_built:
                mods_built.append(ext)
            if ext.name in sysconf_dis:
                mods_disabled.append(ext)
        mods_configured = mods_built + mods_disabled
        if mods_configured:
            self.extensions = [x for x in self.extensions if (x not in mods_configured)]
            for ext in mods_configured:
                fullpath = self.get_ext_fullpath(ext.name)
                if os.path.exists(fullpath):
                    os.unlink(fullpath)
        return (mods_built, mods_disabled)

    def set_compiler_executables(self):
        compiler = os.environ.get("CC")
        args = {}
        if compiler is not None:
            (ccshared, cflags) = sysconfig.get_config_vars("CCSHARED", "CFLAGS")
            args["compiler_so"] = (((compiler + " ") + ccshared) + " ") + cflags
        self.compiler.set_executables(**args)

    def build_extensions(self):
        self.set_srcdir()
        self.detect_modules()
        if not LIST_MODULE_NAMES:
            self.remove_disabled()
        self.update_sources_depends()
        (mods_built, mods_disabled) = self.remove_configured_extensions()
        self.set_compiler_executables()
        if LIST_MODULE_NAMES:
            for ext in self.extensions:
                print(ext.name)
            for name in self.missing:
                print(name)
            return
        build_ext.build_extensions(self)
        if SUBPROCESS_BOOTSTRAP:
            del sys.modules["subprocess"]
        for ext in self.extensions:
            self.check_extension_import(ext)
        self.summary(mods_built, mods_disabled)

    def summary(self, mods_built, mods_disabled):
        longest = max([len(e.name) for e in self.extensions], default=0)
        if self.failed or self.failed_on_import:
            all_failed = self.failed + self.failed_on_import
            longest = max(longest, max([len(name) for name in all_failed]))

        def print_three_column(lst):
            lst.sort(key=str.lower)
            while len(lst) % 3:
                lst.append("")
            for (e, f, g) in zip(lst[::3], lst[1::3], lst[2::3]):
                print(("%-*s   %-*s   %-*s" % (longest, e, longest, f, longest, g)))

        if self.missing:
            print()
            print("Python build finished successfully!")
            print("The necessary bits to build these optional modules were not found:")
            print_three_column(self.missing)
            print(
                "To find the necessary bits, look in setup.py in detect_modules() for the module's name."
            )
            print()
        if mods_built:
            print()
            print(
                "The following modules found by detect_modules() in setup.py, have been"
            )
            print("built by the Makefile instead, as configured by the Setup files:")
            print_three_column([ext.name for ext in mods_built])
            print()
        if mods_disabled:
            print()
            print(
                "The following modules found by detect_modules() in setup.py have not"
            )
            print("been built, they are *disabled* in the Setup files:")
            print_three_column([ext.name for ext in mods_disabled])
            print()
        if self.disabled_configure:
            print()
            print(
                "The following modules found by detect_modules() in setup.py have not"
            )
            print("been built, they are *disabled* by configure:")
            print_three_column(self.disabled_configure)
            print()
        if self.failed:
            failed = self.failed[:]
            print()
            print("Failed to build these modules:")
            print_three_column(failed)
            print()
        if self.failed_on_import:
            failed = self.failed_on_import[:]
            print()
            print(
                "Following modules built successfully but were removed because they could not be imported:"
            )
            print_three_column(failed)
            print()
        if any(
            (("_ssl" in l) for l in (self.missing, self.failed, self.failed_on_import))
        ):
            print()
            print("Could not build the ssl module!")
            print("Python requires a OpenSSL 1.1.1 or newer")
            if sysconfig.get_config_var("OPENSSL_LDFLAGS"):
                print("Custom linker flags may require --with-openssl-rpath=auto")
            print()

    def build_extension(self, ext):
        if ext.name == "_ctypes":
            if not self.configure_ctypes(ext):
                self.failed.append(ext.name)
                return
        try:
            build_ext.build_extension(self, ext)
        except (CCompilerError, DistutilsError) as why:
            self.announce(
                ('WARNING: building of extension "%s" failed: %s' % (ext.name, why))
            )
            self.failed.append(ext.name)
            return

    def check_extension_import(self, ext):
        if ext.name in self.failed:
            self.announce(
                ('WARNING: skipping import check for failed build "%s"' % ext.name),
                level=1,
            )
            return
        if "Carbon" in ext.extra_link_args:
            self.announce(
                ('WARNING: skipping import check for Carbon-based "%s"' % ext.name)
            )
            return
        if MACOS and ((sys.maxsize > (2 ** 32)) and ("-arch" in ext.extra_link_args)):
            self.announce(('WARNING: skipping import check for "%s"' % ext.name))
            return
        if CYGWIN:
            self.announce(
                ('WARNING: skipping import check for Cygwin-based "%s"' % ext.name)
            )
            return
        ext_filename = os.path.join(
            self.build_lib, self.get_ext_filename(self.get_ext_fullname(ext.name))
        )
        sys.path_importer_cache.clear()
        if CROSS_COMPILING:
            return
        loader = importlib.machinery.ExtensionFileLoader(ext.name, ext_filename)
        spec = importlib.util.spec_from_file_location(
            ext.name, ext_filename, loader=loader
        )
        try:
            importlib._bootstrap._load(spec)
        except ImportError as why:
            self.failed_on_import.append(ext.name)
            self.announce(
                (
                    '*** WARNING: renaming "%s" since importing it failed: %s'
                    % (ext.name, why)
                ),
                level=3,
            )
            assert not self.inplace
            (basename, tail) = os.path.splitext(ext_filename)
            newname = (basename + "_failed") + tail
            if os.path.exists(newname):
                os.remove(newname)
            os.rename(ext_filename, newname)
        except:
            (exc_type, why, tb) = sys.exc_info()
            self.announce(
                (
                    '*** WARNING: importing extension "%s" failed with %s: %s'
                    % (ext.name, exc_type, why)
                ),
                level=3,
            )
            self.failed.append(ext.name)

    def add_multiarch_paths(self):
        cc = sysconfig.get_config_var("CC")
        tmpfile = os.path.join(self.build_temp, "multiarch")
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        ret = run_command(("%s -print-multiarch > %s 2> /dev/null" % (cc, tmpfile)))
        multiarch_path_component = ""
        try:
            if ret == 0:
                with open(tmpfile) as fp:
                    multiarch_path_component = fp.readline().strip()
        finally:
            os.unlink(tmpfile)
        if multiarch_path_component != "":
            add_dir_to_list(
                self.compiler.library_dirs, ("/usr/lib/" + multiarch_path_component)
            )
            add_dir_to_list(
                self.compiler.include_dirs, ("/usr/include/" + multiarch_path_component)
            )
            return
        if not find_executable("dpkg-architecture"):
            return
        opt = ""
        if CROSS_COMPILING:
            opt = "-t" + sysconfig.get_config_var("HOST_GNU_TYPE")
        tmpfile = os.path.join(self.build_temp, "multiarch")
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        ret = run_command(
            (
                "dpkg-architecture %s -qDEB_HOST_MULTIARCH > %s 2> /dev/null"
                % (opt, tmpfile)
            )
        )
        try:
            if ret == 0:
                with open(tmpfile) as fp:
                    multiarch_path_component = fp.readline().strip()
                add_dir_to_list(
                    self.compiler.library_dirs, ("/usr/lib/" + multiarch_path_component)
                )
                add_dir_to_list(
                    self.compiler.include_dirs,
                    ("/usr/include/" + multiarch_path_component),
                )
        finally:
            os.unlink(tmpfile)

    def add_wrcc_search_dirs(self):
        def convert_mixed_path(path):
            drive = path[0].lower()
            left = path[2:].replace("\\", "/")
            return ("/" + drive) + left

        def add_search_path(line):
            pathsep = ";" if (sys.platform == "msys") else ":"
            for d in line.strip().split("=")[1].split(pathsep):
                d = d.strip()
                if sys.platform == "msys":
                    d = convert_mixed_path(d)
                d = os.path.normpath(d)
                add_dir_to_list(self.compiler.library_dirs, d)

        cc = sysconfig.get_config_var("CC")
        tmpfile = os.path.join(self.build_temp, "wrccpaths")
        os.makedirs(self.build_temp, exist_ok=True)
        try:
            ret = run_command(("%s --print-search-dirs >%s" % (cc, tmpfile)))
            if ret:
                return
            with open(tmpfile) as fp:
                for line in fp:
                    if not line.startswith("libraries"):
                        continue
                    add_search_path(line)
        finally:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass

    def add_cross_compiling_paths(self):
        cc = sysconfig.get_config_var("CC")
        tmpfile = os.path.join(self.build_temp, "ccpaths")
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        ret = run_command(("%s -E -v - </dev/null 2>%s 1>/dev/null" % (cc, tmpfile)))
        is_gcc = False
        is_clang = False
        in_incdirs = False
        try:
            if ret == 0:
                with open(tmpfile) as fp:
                    for line in fp.readlines():
                        if line.startswith("gcc version"):
                            is_gcc = True
                        elif line.startswith("clang version"):
                            is_clang = True
                        elif line.startswith("#include <...>"):
                            in_incdirs = True
                        elif line.startswith("End of search list"):
                            in_incdirs = False
                        elif (is_gcc or is_clang) and line.startswith("LIBRARY_PATH"):
                            for d in line.strip().split("=")[1].split(":"):
                                d = os.path.normpath(d)
                                if "/gcc/" not in d:
                                    add_dir_to_list(self.compiler.library_dirs, d)
                        elif (
                            (is_gcc or is_clang)
                            and in_incdirs
                            and ("/gcc/" not in line)
                            and ("/clang/" not in line)
                        ):
                            add_dir_to_list(self.compiler.include_dirs, line.strip())
        finally:
            os.unlink(tmpfile)
        if VXWORKS:
            self.add_wrcc_search_dirs()

    def add_ldflags_cppflags(self):
        for (env_var, arg_name, dir_list) in (
            ("LDFLAGS", "-R", self.compiler.runtime_library_dirs),
            ("LDFLAGS", "-L", self.compiler.library_dirs),
            ("CPPFLAGS", "-I", self.compiler.include_dirs),
        ):
            env_val = sysconfig.get_config_var(env_var)
            if env_val:
                parser = argparse.ArgumentParser()
                parser.add_argument(arg_name, dest="dirs", action="append")
                (options, _) = parser.parse_known_args(env_val.split())
                if options.dirs:
                    for directory in reversed(options.dirs):
                        add_dir_to_list(dir_list, directory)

    def configure_compiler(self):
        if not CROSS_COMPILING:
            add_dir_to_list(self.compiler.library_dirs, "/usr/local/lib")
            add_dir_to_list(self.compiler.include_dirs, "/usr/local/include")
        if CROSS_COMPILING:
            self.add_cross_compiling_paths()
        self.add_multiarch_paths()
        self.add_ldflags_cppflags()

    def init_inc_lib_dirs(self):
        if (
            (not CROSS_COMPILING)
            and (os.path.normpath(sys.base_prefix) != "/usr")
            and (not sysconfig.get_config_var("PYTHONFRAMEWORK"))
        ):
            add_dir_to_list(
                self.compiler.library_dirs, sysconfig.get_config_var("LIBDIR")
            )
            add_dir_to_list(
                self.compiler.include_dirs, sysconfig.get_config_var("INCLUDEDIR")
            )
        system_lib_dirs = ["/lib64", "/usr/lib64", "/lib", "/usr/lib"]
        system_include_dirs = ["/usr/include"]
        if not CROSS_COMPILING:
            self.lib_dirs = self.compiler.library_dirs + system_lib_dirs
            self.inc_dirs = self.compiler.include_dirs + system_include_dirs
        else:
            self.lib_dirs = self.compiler.library_dirs + sysroot_paths(
                ("LDFLAGS", "CC"), system_lib_dirs
            )
            self.inc_dirs = self.compiler.include_dirs + sysroot_paths(
                ("CPPFLAGS", "CFLAGS", "CC"), system_include_dirs
            )
        config_h = sysconfig.get_config_h_filename()
        with open(config_h) as file:
            self.config_h_vars = sysconfig.parse_config_h(file)
        if HOST_PLATFORM in ["osf1", "unixware7", "openunix8"]:
            self.lib_dirs += ["/usr/ccs/lib"]
        if HOST_PLATFORM == "hp-ux11":
            self.lib_dirs += ["/usr/lib/hpux64", "/usr/lib/hpux32"]
        if MACOS:
            (cflags, ldflags) = sysconfig.get_config_vars("CFLAGS", "LDFLAGS")
            for item in cflags.split():
                if item.startswith("-I"):
                    self.inc_dirs.append(item[2:])
            for item in ldflags.split():
                if item.startswith("-L"):
                    self.lib_dirs.append(item[2:])

    def detect_simple_extensions(self):
        self.add(
            Extension(
                "array",
                ["arraymodule.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(Extension("_contextvars", ["_contextvarsmodule.c"]))
        shared_math = "Modules/_math.o"
        self.add(
            Extension(
                "math",
                ["mathmodule.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
                extra_objects=[shared_math],
                depends=["_math.h", shared_math],
                libraries=["m"],
            )
        )
        self.add(
            Extension(
                "cmath",
                ["cmathmodule.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
                extra_objects=[shared_math],
                depends=["_math.h", shared_math],
                libraries=["m"],
            )
        )
        time_libs = []
        lib = sysconfig.get_config_var("TIMEMODULE_LIB")
        if lib:
            time_libs.append(lib)
        self.add(Extension("time", ["timemodule.c"], libraries=time_libs))
        self.add(
            Extension(
                "_datetime",
                ["_datetimemodule.c"],
                libraries=["m"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(
            Extension(
                "_zoneinfo",
                ["_zoneinfo.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(
            Extension(
                "_random",
                ["_randommodule.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(Extension("_bisect", ["_bisectmodule.c"]))
        self.add(
            Extension(
                "_heapq",
                ["_heapqmodule.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(
            Extension(
                "_pickle", ["_pickle.c"], extra_compile_args=["-DPy_BUILD_CORE_MODULE"]
            )
        )
        self.add(
            Extension(
                "_json", ["_json.c"], extra_compile_args=["-DPy_BUILD_CORE_MODULE"]
            )
        )
        self.add(Extension("_lsprof", ["_lsprof.c", "rotatingtree.c"]))
        self.add(
            Extension(
                "unicodedata",
                ["unicodedata.c"],
                depends=["unicodedata_db.h", "unicodename_db.h"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(Extension("_opcode", ["_opcode.c"]))
        self.add(
            Extension(
                "_asyncio",
                ["_asynciomodule.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(
            Extension("_abc", ["_abc.c"], extra_compile_args=["-DPy_BUILD_CORE_MODULE"])
        )
        self.add(
            Extension(
                "_queue",
                ["_queuemodule.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(Extension("_statistics", ["_statisticsmodule.c"]))
        libs = []
        if self.config_h_vars.get("FLOCK_NEEDS_LIBBSD", False):
            libs = ["bsd"]
        self.add(Extension("fcntl", ["fcntlmodule.c"], libraries=libs))
        self.add(Extension("pwd", ["pwdmodule.c"]))
        if not VXWORKS:
            self.add(Extension("grp", ["grpmodule.c"]))
        if self.config_h_vars.get("HAVE_GETSPNAM", False) or self.config_h_vars.get(
            "HAVE_GETSPENT", False
        ):
            self.add(Extension("spwd", ["spwdmodule.c"]))
        elif not AIX:
            self.missing.append("spwd")
        self.add(Extension("select", ["selectmodule.c"]))
        self.add(Extension("mmap", ["mmapmodule.c"]))
        self.add(Extension("syslog", ["syslogmodule.c"]))
        self.add(Extension("_xxsubinterpreters", ["_xxsubinterpretersmodule.c"]))
        self.add(Extension("audioop", ["audioop.c"], libraries=["m"]))
        self.add(Extension("_csv", ["_csv.c"]))
        self.add(
            Extension(
                "_posixsubprocess",
                ["_posixsubprocess.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )

    def detect_test_extensions(self):
        self.add(
            Extension("_testcapi", ["_testcapimodule.c"], depends=["testcapi_long.h"])
        )
        self.add(
            Extension(
                "_testinternalcapi",
                ["_testinternalcapi.c"],
                extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
            )
        )
        self.add(Extension("_testbuffer", ["_testbuffer.c"]))
        self.add(Extension("_testimportmultiple", ["_testimportmultiple.c"]))
        self.add(Extension("_testmultiphase", ["_testmultiphase.c"]))
        self.add(
            Extension(
                "_xxtestfuzz", ["_xxtestfuzz/_xxtestfuzz.c", "_xxtestfuzz/fuzzer.c"]
            )
        )

    def detect_readline_curses(self):
        readline_termcap_library = ""
        curses_library = ""
        tmpfile = os.path.join(self.build_temp, "readline_termcap_lib")
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        if sysconfig.get_config_var("HAVE_LIBREADLINE"):
            if sysconfig.get_config_var("WITH_EDITLINE"):
                readline_lib = "edit"
            else:
                readline_lib = "readline"
            do_readline = self.compiler.find_library_file(self.lib_dirs, readline_lib)
            if CROSS_COMPILING:
                ret = run_command(
                    (
                        "%s -d %s | grep '(NEEDED)' > %s"
                        % (sysconfig.get_config_var("READELF"), do_readline, tmpfile)
                    )
                )
            elif find_executable("ldd"):
                ret = run_command(("ldd %s > %s" % (do_readline, tmpfile)))
            else:
                ret = 1
            if ret == 0:
                with open(tmpfile) as fp:
                    for ln in fp:
                        if "curses" in ln:
                            readline_termcap_library = re.sub(
                                ".*lib(n?cursesw?)\\.so.*", "\\1", ln
                            ).rstrip()
                            break
                        if "tinfo" in ln:
                            readline_termcap_library = "tinfo"
                            break
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)
        else:
            do_readline = False
        if "curses" in readline_termcap_library:
            curses_library = readline_termcap_library
        elif self.compiler.find_library_file(self.lib_dirs, "ncursesw"):
            curses_library = "ncursesw"
        elif AIX and self.compiler.find_library_file(self.lib_dirs, "curses"):
            curses_library = "curses"
        elif self.compiler.find_library_file(self.lib_dirs, "ncurses"):
            curses_library = "ncurses"
        elif self.compiler.find_library_file(self.lib_dirs, "curses"):
            curses_library = "curses"
        if MACOS:
            os_release = int(os.uname()[2].split(".")[0])
            dep_target = sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET")
            if dep_target and (
                tuple((int(n) for n in dep_target.split(".")[0:2])) < (10, 5)
            ):
                os_release = 8
            if os_release < 9:
                if find_file("readline/rlconf.h", self.inc_dirs, []) is None:
                    do_readline = False
        if do_readline:
            if MACOS and (os_release < 9):
                readline_extra_link_args = ("-Wl,-search_paths_first",)
            else:
                readline_extra_link_args = ()
            readline_libs = [readline_lib]
            if readline_termcap_library:
                pass
            elif curses_library:
                readline_libs.append(curses_library)
            elif self.compiler.find_library_file(
                (self.lib_dirs + ["/usr/lib/termcap"]), "termcap"
            ):
                readline_libs.append("termcap")
            self.add(
                Extension(
                    "readline",
                    ["readline.c"],
                    library_dirs=["/usr/lib/termcap"],
                    extra_link_args=readline_extra_link_args,
                    libraries=readline_libs,
                )
            )
        else:
            self.missing.append("readline")
        curses_defines = []
        curses_includes = []
        panel_library = "panel"
        if curses_library == "ncursesw":
            curses_defines.append(("HAVE_NCURSESW", "1"))
            if not CROSS_COMPILING:
                curses_includes.append("/usr/include/ncursesw")
            panel_library = "panelw"
            if MACOS:
                curses_defines.append(("_XOPEN_SOURCE_EXTENDED", "1"))
        elif MACOS and (curses_library == "ncurses"):
            curses_defines.append(("HAVE_NCURSESW", "1"))
            curses_defines.append(("_XOPEN_SOURCE_EXTENDED", "1"))
        curses_enabled = True
        if curses_library.startswith("ncurses"):
            curses_libs = [curses_library]
            self.add(
                Extension(
                    "_curses",
                    ["_cursesmodule.c"],
                    extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
                    include_dirs=curses_includes,
                    define_macros=curses_defines,
                    libraries=curses_libs,
                )
            )
        elif (curses_library == "curses") and (not MACOS):
            if self.compiler.find_library_file(self.lib_dirs, "terminfo"):
                curses_libs = ["curses", "terminfo"]
            elif self.compiler.find_library_file(self.lib_dirs, "termcap"):
                curses_libs = ["curses", "termcap"]
            else:
                curses_libs = ["curses"]
            self.add(
                Extension(
                    "_curses",
                    ["_cursesmodule.c"],
                    extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
                    define_macros=curses_defines,
                    libraries=curses_libs,
                )
            )
        else:
            curses_enabled = False
            self.missing.append("_curses")
        skip_curses_panel = True if AIX else False
        if (
            curses_enabled
            and (not skip_curses_panel)
            and self.compiler.find_library_file(self.lib_dirs, panel_library)
        ):
            self.add(
                Extension(
                    "_curses_panel",
                    ["_curses_panel.c"],
                    include_dirs=curses_includes,
                    define_macros=curses_defines,
                    libraries=[panel_library, *curses_libs],
                )
            )
        elif not skip_curses_panel:
            self.missing.append("_curses_panel")

    def detect_crypt(self):
        if VXWORKS:
            self.missing.append("_crypt")
            return
        if self.compiler.find_library_file(self.lib_dirs, "crypt"):
            libs = ["crypt"]
        else:
            libs = []
        self.add(Extension("_crypt", ["_cryptmodule.c"], libraries=libs))

    def detect_socket(self):
        kwargs = {"depends": ["socketmodule.h"]}
        if MACOS:
            kwargs["extra_compile_args"] = ["-D__APPLE_USE_RFC_3542"]
        self.add(Extension("_socket", ["socketmodule.c"], **kwargs))

    def detect_dbm_gdbm(self):
        max_db_ver = (5, 3)
        min_db_ver = (3, 3)
        db_setup_debug = False

        def allow_db_ver(db_ver):
            "Returns a boolean if the given BerkeleyDB version is acceptable.\n\n            Args:\n              db_ver: A tuple of the version to verify.\n            "
            if not (min_db_ver <= db_ver <= max_db_ver):
                return False
            return True

        def gen_db_minor_ver_nums(major):
            if major == 4:
                for x in range((max_db_ver[1] + 1)):
                    if allow_db_ver((4, x)):
                        (yield x)
            elif major == 3:
                for x in (3,):
                    if allow_db_ver((3, x)):
                        (yield x)
            else:
                raise ValueError("unknown major BerkeleyDB version", major)

        db_inc_paths = [
            "/usr/include/db4",
            "/usr/local/include/db4",
            "/opt/sfw/include/db4",
            "/usr/include/db3",
            "/usr/local/include/db3",
            "/opt/sfw/include/db3",
            "/sw/include/db4",
            "/sw/include/db3",
        ]
        for x in gen_db_minor_ver_nums(4):
            db_inc_paths.append(("/usr/include/db4%d" % x))
            db_inc_paths.append(("/usr/include/db4.%d" % x))
            db_inc_paths.append(("/usr/local/BerkeleyDB.4.%d/include" % x))
            db_inc_paths.append(("/usr/local/include/db4%d" % x))
            db_inc_paths.append(("/pkg/db-4.%d/include" % x))
            db_inc_paths.append(("/opt/db-4.%d/include" % x))
            db_inc_paths.append(("/opt/local/include/db4%d" % x))
        for x in gen_db_minor_ver_nums(3):
            db_inc_paths.append(("/usr/include/db3%d" % x))
            db_inc_paths.append(("/usr/local/BerkeleyDB.3.%d/include" % x))
            db_inc_paths.append(("/usr/local/include/db3%d" % x))
            db_inc_paths.append(("/pkg/db-3.%d/include" % x))
            db_inc_paths.append(("/opt/db-3.%d/include" % x))
        if CROSS_COMPILING:
            db_inc_paths = []
        std_variants = []
        for dn in self.inc_dirs:
            std_variants.append(os.path.join(dn, "db3"))
            std_variants.append(os.path.join(dn, "db4"))
            for x in gen_db_minor_ver_nums(4):
                std_variants.append(os.path.join(dn, ("db4%d" % x)))
                std_variants.append(os.path.join(dn, ("db4.%d" % x)))
            for x in gen_db_minor_ver_nums(3):
                std_variants.append(os.path.join(dn, ("db3%d" % x)))
                std_variants.append(os.path.join(dn, ("db3.%d" % x)))
        db_inc_paths = std_variants + db_inc_paths
        db_inc_paths = [p for p in db_inc_paths if os.path.exists(p)]
        db_ver_inc_map = {}
        if MACOS:
            sysroot = macosx_sdk_root()

        class db_found(Exception):
            pass

        try:
            for d in self.inc_dirs + db_inc_paths:
                f = os.path.join(d, "db.h")
                if MACOS and is_macosx_sdk_path(d):
                    f = os.path.join(sysroot, d[1:], "db.h")
                if db_setup_debug:
                    print("db: looking for db.h in", f)
                if os.path.exists(f):
                    with open(f, "rb") as file:
                        f = file.read()
                    m = re.search(b"#define\\WDB_VERSION_MAJOR\\W(\\d+)", f)
                    if m:
                        db_major = int(m.group(1))
                        m = re.search(b"#define\\WDB_VERSION_MINOR\\W(\\d+)", f)
                        db_minor = int(m.group(1))
                        db_ver = (db_major, db_minor)
                        if db_ver == (4, 6):
                            m = re.search(b"#define\\WDB_VERSION_PATCH\\W(\\d+)", f)
                            db_patch = int(m.group(1))
                            if db_patch < 21:
                                print(
                                    "db.h:",
                                    db_ver,
                                    "patch",
                                    db_patch,
                                    "being ignored (4.6.x must be >= 4.6.21)",
                                )
                                continue
                        if (db_ver not in db_ver_inc_map) and allow_db_ver(db_ver):
                            db_ver_inc_map[db_ver] = d
                            if db_setup_debug:
                                print("db.h: found", db_ver, "in", d)
                        elif db_setup_debug:
                            print("db.h: ignoring", d)
                    elif db_setup_debug:
                        print("db.h: no version number version in", d)
            db_found_vers = list(db_ver_inc_map.keys())
            db_found_vers.sort()
            while db_found_vers:
                db_ver = db_found_vers.pop()
                db_incdir = db_ver_inc_map[db_ver]
                db_dirs_to_check = [
                    db_incdir.replace("include", "lib64"),
                    db_incdir.replace("include", "lib"),
                ]
                if not MACOS:
                    db_dirs_to_check = list(filter(os.path.isdir, db_dirs_to_check))
                else:
                    tmp = []
                    for dn in db_dirs_to_check:
                        if is_macosx_sdk_path(dn):
                            if os.path.isdir(os.path.join(sysroot, dn[1:])):
                                tmp.append(dn)
                        elif os.path.isdir(dn):
                            tmp.append(dn)
                    db_dirs_to_check = tmp
                    db_dirs_to_check = tmp
                for dblib in (
                    ("db-%d.%d" % db_ver),
                    ("db%d%d" % db_ver),
                    ("db%d" % db_ver[0]),
                ):
                    dblib_file = self.compiler.find_library_file(
                        (db_dirs_to_check + self.lib_dirs), dblib
                    )
                    if dblib_file:
                        dblib_dir = [os.path.abspath(os.path.dirname(dblib_file))]
                        raise db_found
                    elif db_setup_debug:
                        print("db lib: ", dblib, "not found")
        except db_found:
            if db_setup_debug:
                print("bsddb using BerkeleyDB lib:", db_ver, dblib)
                print("bsddb lib dir:", dblib_dir, " inc dir:", db_incdir)
            dblibs = [dblib]
            if db_incdir in self.inc_dirs:
                db_incs = None
            else:
                db_incs = [db_incdir]
            if dblib_dir[0] in self.lib_dirs:
                dblib_dir = None
        else:
            if db_setup_debug:
                print("db: no appropriate library found")
            db_incs = None
            dblibs = []
            dblib_dir = None
        dbm_setup_debug = False
        dbm_order = ["gdbm"]
        if not CYGWIN:
            config_args = [
                arg.strip("'")
                for arg in sysconfig.get_config_var("CONFIG_ARGS").split()
            ]
            dbm_args = [
                arg for arg in config_args if arg.startswith("--with-dbmliborder=")
            ]
            if dbm_args:
                dbm_order = [arg.split("=")[(-1)] for arg in dbm_args][(-1)].split(":")
            else:
                dbm_order = "ndbm:gdbm:bdb".split(":")
            dbmext = None
            for cand in dbm_order:
                if cand == "ndbm":
                    if find_file("ndbm.h", self.inc_dirs, []) is not None:
                        if self.compiler.find_library_file(self.lib_dirs, "ndbm"):
                            ndbm_libs = ["ndbm"]
                        elif self.compiler.find_library_file(
                            self.lib_dirs, "gdbm_compat"
                        ):
                            ndbm_libs = ["gdbm_compat"]
                        else:
                            ndbm_libs = []
                        if dbm_setup_debug:
                            print("building dbm using ndbm")
                        dbmext = Extension(
                            "_dbm",
                            ["_dbmmodule.c"],
                            define_macros=[("HAVE_NDBM_H", None)],
                            libraries=ndbm_libs,
                        )
                        break
                elif cand == "gdbm":
                    if self.compiler.find_library_file(self.lib_dirs, "gdbm"):
                        gdbm_libs = ["gdbm"]
                        if self.compiler.find_library_file(
                            self.lib_dirs, "gdbm_compat"
                        ):
                            gdbm_libs.append("gdbm_compat")
                        if find_file("gdbm/ndbm.h", self.inc_dirs, []) is not None:
                            if dbm_setup_debug:
                                print("building dbm using gdbm")
                            dbmext = Extension(
                                "_dbm",
                                ["_dbmmodule.c"],
                                define_macros=[("HAVE_GDBM_NDBM_H", None)],
                                libraries=gdbm_libs,
                            )
                            break
                        if find_file("gdbm-ndbm.h", self.inc_dirs, []) is not None:
                            if dbm_setup_debug:
                                print("building dbm using gdbm")
                            dbmext = Extension(
                                "_dbm",
                                ["_dbmmodule.c"],
                                define_macros=[("HAVE_GDBM_DASH_NDBM_H", None)],
                                libraries=gdbm_libs,
                            )
                            break
                elif cand == "bdb":
                    if dblibs:
                        if dbm_setup_debug:
                            print("building dbm using bdb")
                        dbmext = Extension(
                            "_dbm",
                            ["_dbmmodule.c"],
                            library_dirs=dblib_dir,
                            runtime_library_dirs=dblib_dir,
                            include_dirs=db_incs,
                            define_macros=[
                                ("HAVE_BERKDB_H", None),
                                ("DB_DBM_HSEARCH", None),
                            ],
                            libraries=dblibs,
                        )
                        break
            if dbmext is not None:
                self.add(dbmext)
            else:
                self.missing.append("_dbm")
        if ("gdbm" in dbm_order) and self.compiler.find_library_file(
            self.lib_dirs, "gdbm"
        ):
            self.add(Extension("_gdbm", ["_gdbmmodule.c"], libraries=["gdbm"]))
        else:
            self.missing.append("_gdbm")

    def detect_sqlite(self):
        sqlite_setup_debug = False
        sqlite_incdir = sqlite_libdir = None
        sqlite_inc_paths = [
            "/usr/include",
            "/usr/include/sqlite",
            "/usr/include/sqlite3",
            "/usr/local/include",
            "/usr/local/include/sqlite",
            "/usr/local/include/sqlite3",
        ]
        if CROSS_COMPILING:
            sqlite_inc_paths = []
        MIN_SQLITE_VERSION_NUMBER = (3, 7, 15)
        MIN_SQLITE_VERSION = ".".join([str(x) for x in MIN_SQLITE_VERSION_NUMBER])
        if MACOS:
            sysroot = macosx_sdk_root()
        for d_ in self.inc_dirs + sqlite_inc_paths:
            d = d_
            if MACOS and is_macosx_sdk_path(d):
                d = os.path.join(sysroot, d[1:])
            f = os.path.join(d, "sqlite3.h")
            if os.path.exists(f):
                if sqlite_setup_debug:
                    print(("sqlite: found %s" % f))
                with open(f) as file:
                    incf = file.read()
                m = re.search(
                    '\\s*.*#\\s*.*define\\s.*SQLITE_VERSION\\W*"([\\d\\.]*)"', incf
                )
                if m:
                    sqlite_version = m.group(1)
                    sqlite_version_tuple = tuple(
                        [int(x) for x in sqlite_version.split(".")]
                    )
                    if sqlite_version_tuple >= MIN_SQLITE_VERSION_NUMBER:
                        if sqlite_setup_debug:
                            print(("%s/sqlite3.h: version %s" % (d, sqlite_version)))
                        sqlite_incdir = d
                        break
                    elif sqlite_setup_debug:
                        print(
                            (
                                "%s: version %s is too old, need >= %s"
                                % (d, sqlite_version, MIN_SQLITE_VERSION)
                            )
                        )
                elif sqlite_setup_debug:
                    print(("sqlite: %s had no SQLITE_VERSION" % (f,)))
        if sqlite_incdir:
            sqlite_dirs_to_check = [
                os.path.join(sqlite_incdir, "..", "lib64"),
                os.path.join(sqlite_incdir, "..", "lib"),
                os.path.join(sqlite_incdir, "..", "..", "lib64"),
                os.path.join(sqlite_incdir, "..", "..", "lib"),
            ]
            sqlite_libfile = self.compiler.find_library_file(
                (sqlite_dirs_to_check + self.lib_dirs), "sqlite3"
            )
            if sqlite_libfile:
                sqlite_libdir = [os.path.abspath(os.path.dirname(sqlite_libfile))]
        if sqlite_incdir and sqlite_libdir:
            sqlite_srcs = [
                "_sqlite/cache.c",
                "_sqlite/connection.c",
                "_sqlite/cursor.c",
                "_sqlite/microprotocols.c",
                "_sqlite/module.c",
                "_sqlite/prepare_protocol.c",
                "_sqlite/row.c",
                "_sqlite/statement.c",
                "_sqlite/util.c",
            ]
            sqlite_defines = []
            if "--enable-loadable-sqlite-extensions" not in sysconfig.get_config_var(
                "CONFIG_ARGS"
            ):
                sqlite_defines.append(("SQLITE_OMIT_LOAD_EXTENSION", "1"))
            if MACOS:
                sqlite_extra_link_args = ("-Wl,-search_paths_first",)
            else:
                sqlite_extra_link_args = ()
            include_dirs = ["Modules/_sqlite"]
            if sqlite_incdir not in self.compiler.include_dirs:
                include_dirs.append(sqlite_incdir)
            if sqlite_libdir and (sqlite_libdir[0] in self.lib_dirs):
                sqlite_libdir = None
            self.add(
                Extension(
                    "_sqlite3",
                    sqlite_srcs,
                    define_macros=sqlite_defines,
                    include_dirs=include_dirs,
                    library_dirs=sqlite_libdir,
                    extra_link_args=sqlite_extra_link_args,
                    libraries=["sqlite3"],
                )
            )
        else:
            self.missing.append("_sqlite3")

    def detect_platform_specific_exts(self):
        if not MS_WINDOWS:
            if not VXWORKS:
                self.add(Extension("termios", ["termios.c"]))
            self.add(Extension("resource", ["resource.c"]))
        else:
            self.missing.extend(["resource", "termios"])
        if HOST_PLATFORM.startswith(("linux", "freebsd", "gnukfreebsd")):
            self.add(Extension("ossaudiodev", ["ossaudiodev.c"]))
        elif not AIX:
            self.missing.append("ossaudiodev")
        if MACOS:
            self.add(
                Extension(
                    "_scproxy",
                    ["_scproxy.c"],
                    extra_link_args=[
                        "-framework",
                        "SystemConfiguration",
                        "-framework",
                        "CoreFoundation",
                    ],
                )
            )

    def detect_compress_exts(self):
        zlib_inc = find_file("zlib.h", [], self.inc_dirs)
        have_zlib = False
        if zlib_inc is not None:
            zlib_h = zlib_inc[0] + "/zlib.h"
            version = '"0.0.0"'
            version_req = '"1.1.3"'
            if MACOS and is_macosx_sdk_path(zlib_h):
                zlib_h = os.path.join(macosx_sdk_root(), zlib_h[1:])
            with open(zlib_h) as fp:
                while 1:
                    line = fp.readline()
                    if not line:
                        break
                    if line.startswith("#define ZLIB_VERSION"):
                        version = line.split()[2]
                        break
            if version >= version_req:
                if self.compiler.find_library_file(self.lib_dirs, "z"):
                    if MACOS:
                        zlib_extra_link_args = ("-Wl,-search_paths_first",)
                    else:
                        zlib_extra_link_args = ()
                    self.add(
                        Extension(
                            "zlib",
                            ["zlibmodule.c"],
                            libraries=["z"],
                            extra_link_args=zlib_extra_link_args,
                        )
                    )
                    have_zlib = True
                else:
                    self.missing.append("zlib")
            else:
                self.missing.append("zlib")
        else:
            self.missing.append("zlib")
        if have_zlib:
            extra_compile_args = ["-DUSE_ZLIB_CRC32"]
            libraries = ["z"]
            extra_link_args = zlib_extra_link_args
        else:
            extra_compile_args = []
            libraries = []
            extra_link_args = []
        self.add(
            Extension(
                "binascii",
                ["binascii.c"],
                extra_compile_args=extra_compile_args,
                libraries=libraries,
                extra_link_args=extra_link_args,
            )
        )
        if self.compiler.find_library_file(self.lib_dirs, "bz2"):
            if MACOS:
                bz2_extra_link_args = ("-Wl,-search_paths_first",)
            else:
                bz2_extra_link_args = ()
            self.add(
                Extension(
                    "_bz2",
                    ["_bz2module.c"],
                    libraries=["bz2"],
                    extra_link_args=bz2_extra_link_args,
                )
            )
        else:
            self.missing.append("_bz2")
        if self.compiler.find_library_file(self.lib_dirs, "lzma"):
            self.add(Extension("_lzma", ["_lzmamodule.c"], libraries=["lzma"]))
        else:
            self.missing.append("_lzma")

    def detect_expat_elementtree(self):
        if "--with-system-expat" in sysconfig.get_config_var("CONFIG_ARGS"):
            expat_inc = []
            define_macros = []
            extra_compile_args = []
            expat_lib = ["expat"]
            expat_sources = []
            expat_depends = []
        else:
            expat_inc = [os.path.join(self.srcdir, "Modules", "expat")]
            define_macros = [("HAVE_EXPAT_CONFIG_H", "1"), ("XML_POOR_ENTROPY", "1")]
            extra_compile_args = []
            expat_lib = []
            expat_sources = ["expat/xmlparse.c", "expat/xmlrole.c", "expat/xmltok.c"]
            expat_depends = [
                "expat/ascii.h",
                "expat/asciitab.h",
                "expat/expat.h",
                "expat/expat_config.h",
                "expat/expat_external.h",
                "expat/internal.h",
                "expat/latin1tab.h",
                "expat/utf8tab.h",
                "expat/xmlrole.h",
                "expat/xmltok.h",
                "expat/xmltok_impl.h",
            ]
            cc = sysconfig.get_config_var("CC").split()[0]
            ret = run_command(
                (
                    '"%s" -Werror -Wno-unreachable-code -E -xc /dev/null >/dev/null 2>&1'
                    % cc
                )
            )
            if ret == 0:
                extra_compile_args.append("-Wno-unreachable-code")
        self.add(
            Extension(
                "pyexpat",
                define_macros=define_macros,
                extra_compile_args=extra_compile_args,
                include_dirs=expat_inc,
                libraries=expat_lib,
                sources=(["pyexpat.c"] + expat_sources),
                depends=expat_depends,
            )
        )
        if os.path.isfile(os.path.join(self.srcdir, "Modules", "_elementtree.c")):
            define_macros.append(("USE_PYEXPAT_CAPI", None))
            self.add(
                Extension(
                    "_elementtree",
                    define_macros=define_macros,
                    include_dirs=expat_inc,
                    libraries=expat_lib,
                    sources=["_elementtree.c"],
                    depends=["pyexpat.c", *expat_sources, *expat_depends],
                )
            )
        else:
            self.missing.append("_elementtree")

    def detect_multibytecodecs(self):
        self.add(Extension("_multibytecodec", ["cjkcodecs/multibytecodec.c"]))
        for loc in ("kr", "jp", "cn", "tw", "hk", "iso2022"):
            self.add(
                Extension(("_codecs_%s" % loc), [("cjkcodecs/_codecs_%s.c" % loc)])
            )

    def detect_multiprocessing(self):
        if MS_WINDOWS:
            multiprocessing_srcs = [
                "_multiprocessing/multiprocessing.c",
                "_multiprocessing/semaphore.c",
            ]
        else:
            multiprocessing_srcs = ["_multiprocessing/multiprocessing.c"]
            if sysconfig.get_config_var("HAVE_SEM_OPEN") and (
                not sysconfig.get_config_var("POSIX_SEMAPHORES_NOT_ENABLED")
            ):
                multiprocessing_srcs.append("_multiprocessing/semaphore.c")
        self.add(
            Extension(
                "_multiprocessing",
                multiprocessing_srcs,
                include_dirs=["Modules/_multiprocessing"],
            )
        )
        if (
            (not MS_WINDOWS)
            and sysconfig.get_config_var("HAVE_SHM_OPEN")
            and sysconfig.get_config_var("HAVE_SHM_UNLINK")
        ):
            posixshmem_srcs = ["_multiprocessing/posixshmem.c"]
            libs = []
            if sysconfig.get_config_var("SHM_NEEDS_LIBRT"):
                libs.append("rt")
            self.add(
                Extension(
                    "_posixshmem",
                    posixshmem_srcs,
                    define_macros={},
                    libraries=libs,
                    include_dirs=["Modules/_multiprocessing"],
                )
            )
        else:
            self.missing.append("_posixshmem")

    def detect_uuid(self):
        uuid_incs = find_file("uuid.h", self.inc_dirs, ["/usr/include/uuid"])
        if uuid_incs is not None:
            if self.compiler.find_library_file(self.lib_dirs, "uuid"):
                uuid_libs = ["uuid"]
            else:
                uuid_libs = []
            self.add(
                Extension(
                    "_uuid",
                    ["_uuidmodule.c"],
                    libraries=uuid_libs,
                    include_dirs=uuid_incs,
                )
            )
        else:
            self.missing.append("_uuid")

    def detect_modules(self):
        self.configure_compiler()
        self.init_inc_lib_dirs()
        self.detect_simple_extensions()
        if TEST_EXTENSIONS:
            self.detect_test_extensions()
        self.detect_readline_curses()
        self.detect_crypt()
        self.detect_socket()
        self.detect_openssl_hashlib()
        self.detect_hash_builtins()
        self.detect_dbm_gdbm()
        self.detect_sqlite()
        self.detect_platform_specific_exts()
        self.detect_nis()
        self.detect_compress_exts()
        self.detect_expat_elementtree()
        self.detect_multibytecodecs()
        self.detect_decimal()
        self.detect_ctypes()
        self.detect_multiprocessing()
        if not self.detect_tkinter():
            self.missing.append("_tkinter")
        self.detect_uuid()
        if not sysconfig.get_config_var("Py_TRACE_REFS"):
            self.add(Extension("xxlimited", ["xxlimited.c"]))
            self.add(Extension("xxlimited_35", ["xxlimited_35.c"]))

    def detect_tkinter_fromenv(self):
        tcltk_includes = os.environ.get("_TCLTK_INCLUDES")
        tcltk_libs = os.environ.get("_TCLTK_LIBS")
        if not (tcltk_includes and tcltk_libs):
            return False
        extra_compile_args = tcltk_includes.split()
        extra_link_args = tcltk_libs.split()
        self.add(
            Extension(
                "_tkinter",
                ["_tkinter.c", "tkappinit.c"],
                define_macros=[("WITH_APPINIT", 1)],
                extra_compile_args=extra_compile_args,
                extra_link_args=extra_link_args,
            )
        )
        return True

    def detect_tkinter_darwin(self):
        from os.path import join, exists

        sysroot = macosx_sdk_root()
        if macosx_sdk_specified():
            framework_dirs = [
                join(sysroot, "Library", "Frameworks"),
                join(sysroot, "System", "Library", "Frameworks"),
            ]
        else:
            framework_dirs = [
                join("/", "Library", "Frameworks"),
                join(sysroot, "System", "Library", "Frameworks"),
            ]
        for F in framework_dirs:
            for fw in ("Tcl", "Tk"):
                if not exists(join(F, (fw + ".framework"))):
                    break
            else:
                break
        else:
            return False
        include_dirs = [
            join(F, (fw + ".framework"), H)
            for fw in ("Tcl", "Tk")
            for H in ("Headers",)
        ]
        compile_args = ["-F", F]
        cflags = sysconfig.get_config_vars("CFLAGS")[0]
        archs = re.findall("-arch\\s+(\\w+)", cflags)
        tmpfile = os.path.join(self.build_temp, "tk.arch")
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        run_command(
            "file {}/Tk.framework/Tk | grep 'for architecture' > {}".format(F, tmpfile)
        )
        with open(tmpfile) as fp:
            detected_archs = []
            for ln in fp:
                a = ln.split()[(-1)]
                if a in archs:
                    detected_archs.append(ln.split()[(-1)])
        os.unlink(tmpfile)
        arch_args = []
        for a in detected_archs:
            arch_args.append("-arch")
            arch_args.append(a)
        compile_args += arch_args
        link_args = [
            ",".join(["-Wl", "-F", F, "-framework", "Tcl", "-framework", "Tk"]),
            *arch_args,
        ]
        if "-Wstrict-prototypes" in cflags.split():
            compile_args.append("-Wno-strict-prototypes")
        self.add(
            Extension(
                "_tkinter",
                ["_tkinter.c", "tkappinit.c"],
                define_macros=[("WITH_APPINIT", 1)],
                include_dirs=include_dirs,
                libraries=[],
                extra_compile_args=compile_args,
                extra_link_args=link_args,
            )
        )
        return True

    def detect_tkinter(self):
        if self.detect_tkinter_fromenv():
            return True
        if MACOS and self.detect_tkinter_darwin():
            return True
        tcllib = tklib = tcl_includes = tk_includes = None
        for version in [
            "8.6",
            "86",
            "8.5",
            "85",
            "8.4",
            "84",
            "8.3",
            "83",
            "8.2",
            "82",
            "8.1",
            "81",
            "8.0",
            "80",
        ]:
            tklib = self.compiler.find_library_file(self.lib_dirs, ("tk" + version))
            tcllib = self.compiler.find_library_file(self.lib_dirs, ("tcl" + version))
            if tklib and tcllib:
                break
        if tklib and tcllib:
            dotversion = version
            if ("." not in dotversion) and ("bsd" in HOST_PLATFORM.lower()):
                dotversion = (dotversion[:(-1)] + ".") + dotversion[(-1)]
            tcl_include_sub = []
            tk_include_sub = []
            for dir in self.inc_dirs:
                tcl_include_sub += [(((dir + os.sep) + "tcl") + dotversion)]
                tk_include_sub += [(((dir + os.sep) + "tk") + dotversion)]
            tk_include_sub += tcl_include_sub
            tcl_includes = find_file("tcl.h", self.inc_dirs, tcl_include_sub)
            tk_includes = find_file("tk.h", self.inc_dirs, tk_include_sub)
        if (
            (tcllib is None)
            or (tklib is None)
            or (tcl_includes is None)
            or (tk_includes is None)
        ):
            self.announce("INFO: Can't locate Tcl/Tk libs and/or headers", 2)
            return False
        include_dirs = []
        libs = []
        defs = []
        added_lib_dirs = []
        for dir in tcl_includes + tk_includes:
            if dir not in include_dirs:
                include_dirs.append(dir)
        if HOST_PLATFORM == "sunos5":
            include_dirs.append("/usr/openwin/include")
            added_lib_dirs.append("/usr/openwin/lib")
        elif os.path.exists("/usr/X11R6/include"):
            include_dirs.append("/usr/X11R6/include")
            added_lib_dirs.append("/usr/X11R6/lib64")
            added_lib_dirs.append("/usr/X11R6/lib")
        elif os.path.exists("/usr/X11R5/include"):
            include_dirs.append("/usr/X11R5/include")
            added_lib_dirs.append("/usr/X11R5/lib")
        else:
            include_dirs.append("/usr/X11/include")
            added_lib_dirs.append("/usr/X11/lib")
        if CYGWIN:
            x11_inc = find_file("X11/Xlib.h", [], include_dirs)
            if x11_inc is None:
                return False
        if self.compiler.find_library_file((self.lib_dirs + added_lib_dirs), "BLT8.0"):
            defs.append(("WITH_BLT", 1))
            libs.append("BLT8.0")
        elif self.compiler.find_library_file((self.lib_dirs + added_lib_dirs), "BLT"):
            defs.append(("WITH_BLT", 1))
            libs.append("BLT")
        libs.append(("tk" + version))
        libs.append(("tcl" + version))
        if not CYGWIN:
            libs.append("X11")
        self.add(
            Extension(
                "_tkinter",
                ["_tkinter.c", "tkappinit.c"],
                define_macros=([("WITH_APPINIT", 1)] + defs),
                include_dirs=include_dirs,
                libraries=libs,
                library_dirs=added_lib_dirs,
            )
        )
        return True

    def configure_ctypes(self, ext):
        return True

    def detect_ctypes(self):
        if (not sysconfig.get_config_var("LIBFFI_INCLUDEDIR")) and MACOS:
            self.use_system_libffi = True
        else:
            self.use_system_libffi = "--with-system-ffi" in sysconfig.get_config_var(
                "CONFIG_ARGS"
            )
        include_dirs = []
        extra_compile_args = ["-DPy_BUILD_CORE_MODULE"]
        extra_link_args = []
        sources = [
            "_ctypes/_ctypes.c",
            "_ctypes/callbacks.c",
            "_ctypes/callproc.c",
            "_ctypes/stgdict.c",
            "_ctypes/cfield.c",
        ]
        depends = ["_ctypes/ctypes.h"]
        if MACOS:
            sources.append("_ctypes/malloc_closure.c")
            extra_compile_args.append("-DUSING_MALLOC_CLOSURE_DOT_C=1")
            extra_compile_args.append("-DMACOSX")
            include_dirs.append("_ctypes/darwin")
        elif HOST_PLATFORM == "sunos5":
            extra_link_args.append("-mimpure-text")
        elif HOST_PLATFORM.startswith("hp-ux"):
            extra_link_args.append("-fPIC")
        ext = Extension(
            "_ctypes",
            include_dirs=include_dirs,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            libraries=[],
            sources=sources,
            depends=depends,
        )
        self.add(ext)
        if TEST_EXTENSIONS:
            self.add(
                Extension(
                    "_ctypes_test", sources=["_ctypes/_ctypes_test.c"], libraries=["m"]
                )
            )
        ffi_inc = sysconfig.get_config_var("LIBFFI_INCLUDEDIR")
        ffi_lib = None
        ffi_inc_dirs = self.inc_dirs.copy()
        if MACOS:
            ffi_in_sdk = os.path.join(macosx_sdk_root(), "usr/include/ffi")
            if not ffi_inc:
                if os.path.exists(ffi_in_sdk):
                    ext.extra_compile_args.append("-DUSING_APPLE_OS_LIBFFI=1")
                    ffi_inc = ffi_in_sdk
                    ffi_lib = "ffi"
                else:
                    ffi_inc_dirs.append("/usr/include/ffi")
        if not ffi_inc:
            found = find_file("ffi.h", [], ffi_inc_dirs)
            if found:
                ffi_inc = found[0]
        if ffi_inc:
            ffi_h = ffi_inc + "/ffi.h"
            if not os.path.exists(ffi_h):
                ffi_inc = None
                print("Header file {} does not exist".format(ffi_h))
        if (ffi_lib is None) and ffi_inc:
            for lib_name in ("ffi", "ffi_pic"):
                if self.compiler.find_library_file(self.lib_dirs, lib_name):
                    ffi_lib = lib_name
                    break
        if ffi_inc and ffi_lib:
            ffi_headers = glob(os.path.join(ffi_inc, "*.h"))
            if grep_headers_for("ffi_prep_cif_var", ffi_headers):
                ext.extra_compile_args.append("-DHAVE_FFI_PREP_CIF_VAR=1")
            if grep_headers_for("ffi_prep_closure_loc", ffi_headers):
                ext.extra_compile_args.append("-DHAVE_FFI_PREP_CLOSURE_LOC=1")
            if grep_headers_for("ffi_closure_alloc", ffi_headers):
                ext.extra_compile_args.append("-DHAVE_FFI_CLOSURE_ALLOC=1")
            ext.include_dirs.append(ffi_inc)
            ext.libraries.append(ffi_lib)
            self.use_system_libffi = True
        if sysconfig.get_config_var("HAVE_LIBDL"):
            ext.libraries.append("dl")

    def detect_decimal(self):
        extra_compile_args = []
        undef_macros = []
        if "--with-system-libmpdec" in sysconfig.get_config_var("CONFIG_ARGS"):
            include_dirs = []
            libraries = ["mpdec"]
            sources = ["_decimal/_decimal.c"]
            depends = ["_decimal/docstrings.h"]
        else:
            include_dirs = [
                os.path.abspath(
                    os.path.join(self.srcdir, "Modules", "_decimal", "libmpdec")
                )
            ]
            libraries = ["m"]
            sources = [
                "_decimal/_decimal.c",
                "_decimal/libmpdec/basearith.c",
                "_decimal/libmpdec/constants.c",
                "_decimal/libmpdec/context.c",
                "_decimal/libmpdec/convolute.c",
                "_decimal/libmpdec/crt.c",
                "_decimal/libmpdec/difradix2.c",
                "_decimal/libmpdec/fnt.c",
                "_decimal/libmpdec/fourstep.c",
                "_decimal/libmpdec/io.c",
                "_decimal/libmpdec/mpalloc.c",
                "_decimal/libmpdec/mpdecimal.c",
                "_decimal/libmpdec/numbertheory.c",
                "_decimal/libmpdec/sixstep.c",
                "_decimal/libmpdec/transpose.c",
            ]
            depends = [
                "_decimal/docstrings.h",
                "_decimal/libmpdec/basearith.h",
                "_decimal/libmpdec/bits.h",
                "_decimal/libmpdec/constants.h",
                "_decimal/libmpdec/convolute.h",
                "_decimal/libmpdec/crt.h",
                "_decimal/libmpdec/difradix2.h",
                "_decimal/libmpdec/fnt.h",
                "_decimal/libmpdec/fourstep.h",
                "_decimal/libmpdec/io.h",
                "_decimal/libmpdec/mpalloc.h",
                "_decimal/libmpdec/mpdecimal.h",
                "_decimal/libmpdec/numbertheory.h",
                "_decimal/libmpdec/sixstep.h",
                "_decimal/libmpdec/transpose.h",
                "_decimal/libmpdec/typearith.h",
                "_decimal/libmpdec/umodarith.h",
            ]
        config = {
            "x64": [("CONFIG_64", "1"), ("ASM", "1")],
            "uint128": [("CONFIG_64", "1"), ("ANSI", "1"), ("HAVE_UINT128_T", "1")],
            "ansi64": [("CONFIG_64", "1"), ("ANSI", "1")],
            "ppro": [("CONFIG_32", "1"), ("PPRO", "1"), ("ASM", "1")],
            "ansi32": [("CONFIG_32", "1"), ("ANSI", "1")],
            "ansi-legacy": [
                ("CONFIG_32", "1"),
                ("ANSI", "1"),
                ("LEGACY_COMPILER", "1"),
            ],
            "universal": [("UNIVERSAL", "1")],
        }
        cc = sysconfig.get_config_var("CC")
        sizeof_size_t = sysconfig.get_config_var("SIZEOF_SIZE_T")
        machine = os.environ.get("PYTHON_DECIMAL_WITH_MACHINE")
        if machine:
            define_macros = config[machine]
        elif MACOS:
            define_macros = config["universal"]
        elif sizeof_size_t == 8:
            if sysconfig.get_config_var("HAVE_GCC_ASM_FOR_X64"):
                define_macros = config["x64"]
            elif sysconfig.get_config_var("HAVE_GCC_UINT128_T"):
                define_macros = config["uint128"]
            else:
                define_macros = config["ansi64"]
        elif sizeof_size_t == 4:
            ppro = sysconfig.get_config_var("HAVE_GCC_ASM_FOR_X87")
            if (
                ppro
                and (("gcc" in cc) or ("clang" in cc))
                and (not ("sunos" in HOST_PLATFORM))
            ):
                define_macros = config["ppro"]
                extra_compile_args.append("-Wno-unknown-pragmas")
            else:
                define_macros = config["ansi32"]
        else:
            raise DistutilsError("_decimal: unsupported architecture")
        if sysconfig.get_config_var("HAVE_IPA_PURE_CONST_BUG"):
            extra_compile_args.append("-fno-ipa-pure-const")
        if sysconfig.get_config_var("HAVE_GLIBC_MEMMOVE_BUG"):
            undef_macros.append("_FORTIFY_SOURCE")
        self.add(
            Extension(
                "_decimal",
                include_dirs=include_dirs,
                libraries=libraries,
                define_macros=define_macros,
                undef_macros=undef_macros,
                extra_compile_args=extra_compile_args,
                sources=sources,
                depends=depends,
            )
        )

    def detect_openssl_hashlib(self):
        config_vars = sysconfig.get_config_vars()

        def split_var(name, sep):
            value = config_vars.get(name)
            if not value:
                return ()
            value = " " + value
            sep = " " + sep
            return [v.strip() for v in value.split(sep) if v.strip()]

        openssl_includes = split_var("OPENSSL_INCLUDES", "-I")
        openssl_libdirs = split_var("OPENSSL_LDFLAGS", "-L")
        openssl_libs = split_var("OPENSSL_LIBS", "-l")
        openssl_rpath = config_vars.get("OPENSSL_RPATH")
        if not openssl_libs:
            self.missing.extend(["_ssl", "_hashlib"])
            return (None, None)
        ssl_incs = find_file("openssl/ssl.h", self.inc_dirs, openssl_includes)
        if ssl_incs is None:
            self.missing.extend(["_ssl", "_hashlib"])
            return (None, None)
        if openssl_rpath == "auto":
            runtime_library_dirs = openssl_libdirs[:]
        elif not openssl_rpath:
            runtime_library_dirs = []
        else:
            runtime_library_dirs = [openssl_rpath]
        openssl_extension_kwargs = dict(
            include_dirs=openssl_includes,
            library_dirs=openssl_libdirs,
            libraries=openssl_libs,
            runtime_library_dirs=runtime_library_dirs,
        )
        if os.environ.get("PY_UNSUPPORTED_OPENSSL_BUILD") == "static":
            extra_linker_args = []
            for lib in openssl_extension_kwargs["libraries"]:
                extra_linker_args.append(f"-l:lib{lib}.a")
                extra_linker_args.append(f"-Wl,--exclude-libs,lib{lib}.a")
            openssl_extension_kwargs["extra_link_args"] = extra_linker_args
            openssl_extension_kwargs["libraries"] = []
        self.add(
            Extension(
                "_ssl",
                ["_ssl.c"],
                depends=["socketmodule.h", "_ssl/debughelpers.c", "_ssl.h"],
                **openssl_extension_kwargs,
            )
        )
        self.add(
            Extension(
                "_hashlib",
                ["_hashopenssl.c"],
                depends=["hashlib.h"],
                **openssl_extension_kwargs,
            )
        )

    def detect_hash_builtins(self):
        supported = {"md5", "sha1", "sha256", "sha512", "sha3", "blake2"}
        configured = sysconfig.get_config_var("PY_BUILTIN_HASHLIB_HASHES")
        configured = configured.strip('"').lower()
        configured = {m.strip() for m in configured.split(",")}
        self.disabled_configure.extend(sorted(supported.difference(configured)))
        if "sha256" in configured:
            self.add(
                Extension(
                    "_sha256",
                    ["sha256module.c"],
                    extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
                    depends=["hashlib.h"],
                )
            )
        if "sha512" in configured:
            self.add(
                Extension(
                    "_sha512",
                    ["sha512module.c"],
                    extra_compile_args=["-DPy_BUILD_CORE_MODULE"],
                    depends=["hashlib.h"],
                )
            )
        if "md5" in configured:
            self.add(Extension("_md5", ["md5module.c"], depends=["hashlib.h"]))
        if "sha1" in configured:
            self.add(Extension("_sha1", ["sha1module.c"], depends=["hashlib.h"]))
        if "blake2" in configured:
            blake2_deps = glob(
                os.path.join(escape(self.srcdir), "Modules/_blake2/impl/*")
            )
            blake2_deps.append("hashlib.h")
            self.add(
                Extension(
                    "_blake2",
                    [
                        "_blake2/blake2module.c",
                        "_blake2/blake2b_impl.c",
                        "_blake2/blake2s_impl.c",
                    ],
                    depends=blake2_deps,
                )
            )
        if "sha3" in configured:
            sha3_deps = glob(os.path.join(escape(self.srcdir), "Modules/_sha3/kcp/*"))
            sha3_deps.append("hashlib.h")
            self.add(Extension("_sha3", ["_sha3/sha3module.c"], depends=sha3_deps))

    def detect_nis(self):
        if MS_WINDOWS or CYGWIN or (HOST_PLATFORM == "qnx6"):
            self.missing.append("nis")
            return
        libs = []
        library_dirs = []
        includes_dirs = []
        rpcsvc_inc = find_file(
            "rpcsvc/yp_prot.h",
            self.inc_dirs,
            [os.path.join(inc_dir, "nsl") for inc_dir in self.inc_dirs],
        )
        rpc_inc = find_file(
            "rpc/rpc.h",
            self.inc_dirs,
            [os.path.join(inc_dir, "tirpc") for inc_dir in self.inc_dirs],
        )
        if (rpcsvc_inc is None) or (rpc_inc is None):
            self.missing.append("nis")
            return
        includes_dirs.extend(rpcsvc_inc)
        includes_dirs.extend(rpc_inc)
        if self.compiler.find_library_file(self.lib_dirs, "nsl"):
            libs.append("nsl")
        else:
            nsl_dirs = [os.path.join(lib_dir, "nsl") for lib_dir in self.lib_dirs]
            libnsl = self.compiler.find_library_file(nsl_dirs, "nsl")
            if libnsl is not None:
                library_dirs.append(os.path.dirname(libnsl))
                libs.append("nsl")
        if self.compiler.find_library_file(self.lib_dirs, "tirpc"):
            libs.append("tirpc")
        self.add(
            Extension(
                "nis",
                ["nismodule.c"],
                libraries=libs,
                library_dirs=library_dirs,
                include_dirs=includes_dirs,
            )
        )


class PyBuildInstall(install):
    def initialize_options(self):
        install.initialize_options(self)
        self.warn_dir = 0

    sub_commands = [
        ("install_lib", install.has_lib),
        ("install_headers", install.has_headers),
        ("install_scripts", install.has_scripts),
        ("install_data", install.has_data),
    ]


class PyBuildInstallLib(install_lib):
    shlib_suffix = sysconfig.get_config_var("SHLIB_SUFFIX")

    def install(self):
        outfiles = install_lib.install(self)
        self.set_file_modes(outfiles, 420, 493)
        self.set_dir_modes(self.install_dir, 493)
        return outfiles

    def set_file_modes(self, files, defaultMode, sharedLibMode):
        if not files:
            return
        for filename in files:
            if os.path.islink(filename):
                continue
            mode = defaultMode
            if filename.endswith(self.shlib_suffix):
                mode = sharedLibMode
            log.info("changing mode of %s to %o", filename, mode)
            if not self.dry_run:
                os.chmod(filename, mode)

    def set_dir_modes(self, dirname, mode):
        for (dirpath, dirnames, fnames) in os.walk(dirname):
            if os.path.islink(dirpath):
                continue
            log.info("changing mode of %s to %o", dirpath, mode)
            if not self.dry_run:
                os.chmod(dirpath, mode)


class PyBuildScripts(build_scripts):
    def copy_scripts(self):
        (outfiles, updated_files) = build_scripts.copy_scripts(self)
        fullversion = "-{0[0]}.{0[1]}".format(sys.version_info)
        minoronly = ".{0[1]}".format(sys.version_info)
        newoutfiles = []
        newupdated_files = []
        for filename in outfiles:
            if filename.endswith("2to3"):
                newfilename = filename + fullversion
            else:
                newfilename = filename + minoronly
            log.info("renaming %s to %s", filename, newfilename)
            os.rename(filename, newfilename)
            newoutfiles.append(newfilename)
            if filename in updated_files:
                newupdated_files.append(newfilename)
        return (newoutfiles, newupdated_files)


def main():
    global LIST_MODULE_NAMES
    if "--list-module-names" in sys.argv:
        LIST_MODULE_NAMES = True
        sys.argv.remove("--list-module-names")
    set_compiler_flags("CFLAGS", "PY_CFLAGS_NODIST")
    set_compiler_flags("LDFLAGS", "PY_LDFLAGS_NODIST")

    class DummyProcess:
        "Hack for parallel build"
        ProcessPoolExecutor = None

    sys.modules["concurrent.futures.process"] = DummyProcess
    validate_tzpath()
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    setup(
        name="Python",
        version=sys.version.split()[0],
        url=("http://www.python.org/%d.%d" % sys.version_info[:2]),
        maintainer="Guido van Rossum and the Python community",
        maintainer_email="python-dev@python.org",
        description="A high-level object-oriented programming language",
        long_description=SUMMARY.strip(),
        license="PSF license",
        classifiers=[x for x in CLASSIFIERS.split("\n") if x],
        platforms=["Many"],
        cmdclass={
            "build_ext": PyBuildExt,
            "build_scripts": PyBuildScripts,
            "install": PyBuildInstall,
            "install_lib": PyBuildInstallLib,
        },
        ext_modules=[
            Extension(
                "_struct", ["_struct.c"], extra_compile_args=["-DPy_BUILD_CORE_MODULE"]
            )
        ],
        scripts=["Tools/scripts/pydoc3", "Tools/scripts/idle3", "Tools/scripts/2to3"],
    )


if __name__ == "__main__":
    main()
