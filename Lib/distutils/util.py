"distutils.util\n\nMiscellaneous utility functions -- anything that doesn't fit into\none of the other *util.py modules.\n"
import os
import re
import importlib.util
import string
import sys
import distutils
from distutils.errors import DistutilsPlatformError
from distutils.dep_util import newer
from distutils.spawn import spawn
from distutils import log
from distutils.errors import DistutilsByteCompileError


def get_host_platform():
    "Return a string that identifies the current platform.  This is used mainly to\n    distinguish platform-specific build directories and platform-specific built\n    distributions.  Typically includes the OS name and version and the\n    architecture (as supplied by 'os.uname()'), although the exact information\n    included depends on the OS; eg. on Linux, the kernel version isn't\n    particularly important.\n\n    Examples of returned values:\n       linux-i586\n       linux-alpha (?)\n       solaris-2.6-sun4u\n\n    Windows will return one of:\n       win-amd64 (64bit Windows on AMD64 (aka x86_64, Intel64, EM64T, etc)\n       win32 (all others - specifically, sys.platform is returned)\n\n    For other non-POSIX platforms, currently just returns 'sys.platform'.\n\n    "
    if os.name == "nt":
        if "amd64" in sys.version.lower():
            return "win-amd64"
        if "(arm)" in sys.version.lower():
            return "win-arm32"
        if "(arm64)" in sys.version.lower():
            return "win-arm64"
        return sys.platform
    if "_PYTHON_HOST_PLATFORM" in os.environ:
        return os.environ["_PYTHON_HOST_PLATFORM"]
    if (os.name != "posix") or (not hasattr(os, "uname")):
        return sys.platform
    (osname, host, release, version, machine) = os.uname()
    osname = osname.lower().replace("/", "")
    machine = machine.replace(" ", "_")
    machine = machine.replace("/", "-")
    if osname[:5] == "linux":
        return "%s-%s" % (osname, machine)
    elif osname[:5] == "sunos":
        if release[0] >= "5":
            osname = "solaris"
            release = "%d.%s" % ((int(release[0]) - 3), release[2:])
            bitness = {2147483647: "32bit", 9223372036854775807: "64bit"}
            machine += ".%s" % bitness[sys.maxsize]
    elif osname[:3] == "aix":
        from _aix_support import aix_platform

        return aix_platform()
    elif osname[:6] == "cygwin":
        osname = "cygwin"
        rel_re = re.compile("[\\d.]+", re.ASCII)
        m = rel_re.match(release)
        if m:
            release = m.group()
    elif osname[:6] == "darwin":
        import _osx_support, distutils.sysconfig

        (osname, release, machine) = _osx_support.get_platform_osx(
            distutils.sysconfig.get_config_vars(), osname, release, machine
        )
    return "%s-%s-%s" % (osname, release, machine)


def get_platform():
    if os.name == "nt":
        TARGET_TO_PLAT = {"x86": "win32", "x64": "win-amd64", "arm": "win-arm32"}
        return (
            TARGET_TO_PLAT.get(os.environ.get("VSCMD_ARG_TGT_ARCH"))
            or get_host_platform()
        )
    else:
        return get_host_platform()


def convert_path(pathname):
    "Return 'pathname' as a name that will work on the native filesystem,\n    i.e. split it on '/' and put it back together again using the current\n    directory separator.  Needed because filenames in the setup script are\n    always supplied in Unix style, and have to be converted to the local\n    convention before we can actually use them in the filesystem.  Raises\n    ValueError on non-Unix-ish systems if 'pathname' either starts or\n    ends with a slash.\n    "
    if os.sep == "/":
        return pathname
    if not pathname:
        return pathname
    if pathname[0] == "/":
        raise ValueError(("path '%s' cannot be absolute" % pathname))
    if pathname[(-1)] == "/":
        raise ValueError(("path '%s' cannot end with '/'" % pathname))
    paths = pathname.split("/")
    while "." in paths:
        paths.remove(".")
    if not paths:
        return os.curdir
    return os.path.join(*paths)


def change_root(new_root, pathname):
    "Return 'pathname' with 'new_root' prepended.  If 'pathname' is\n    relative, this is equivalent to \"os.path.join(new_root,pathname)\".\n    Otherwise, it requires making 'pathname' relative and then joining the\n    two, which is tricky on DOS/Windows and Mac OS.\n    "
    if os.name == "posix":
        if not os.path.isabs(pathname):
            return os.path.join(new_root, pathname)
        else:
            return os.path.join(new_root, pathname[1:])
    elif os.name == "nt":
        (drive, path) = os.path.splitdrive(pathname)
        if path[0] == "\\":
            path = path[1:]
        return os.path.join(new_root, path)
    else:
        raise DistutilsPlatformError(("nothing known about platform '%s'" % os.name))


_environ_checked = 0


def check_environ():
    "Ensure that 'os.environ' has all the environment variables we\n    guarantee that users can use in config files, command-line options,\n    etc.  Currently this includes:\n      HOME - user's home directory (Unix only)\n      PLAT - description of the current platform, including hardware\n             and OS (see 'get_platform()')\n    "
    global _environ_checked
    if _environ_checked:
        return
    if (os.name == "posix") and ("HOME" not in os.environ):
        try:
            import pwd

            os.environ["HOME"] = pwd.getpwuid(os.getuid())[5]
        except (ImportError, KeyError):
            pass
    if "PLAT" not in os.environ:
        os.environ["PLAT"] = get_platform()
    _environ_checked = 1


def subst_vars(s, local_vars):
    "Perform shell/Perl-style variable substitution on 'string'.  Every\n    occurrence of '$' followed by a name is considered a variable, and\n    variable is substituted by the value found in the 'local_vars'\n    dictionary, or in 'os.environ' if it's not in 'local_vars'.\n    'os.environ' is first checked/augmented to guarantee that it contains\n    certain values: see 'check_environ()'.  Raise ValueError for any\n    variables not found in either 'local_vars' or 'os.environ'.\n    "
    check_environ()

    def _subst(match, local_vars=local_vars):
        var_name = match.group(1)
        if var_name in local_vars:
            return str(local_vars[var_name])
        else:
            return os.environ[var_name]

    try:
        return re.sub("\\$([a-zA-Z_][a-zA-Z_0-9]*)", _subst, s)
    except KeyError as var:
        raise ValueError(("invalid variable '$%s'" % var))


def grok_environment_error(exc, prefix="error: "):
    return prefix + str(exc)


_wordchars_re = _squote_re = _dquote_re = None


def _init_regex():
    global _wordchars_re, _squote_re, _dquote_re
    _wordchars_re = re.compile(("[^\\\\\\'\\\"%s ]*" % string.whitespace))
    _squote_re = re.compile("'(?:[^'\\\\]|\\\\.)*'")
    _dquote_re = re.compile('"(?:[^"\\\\]|\\\\.)*"')


def split_quoted(s):
    "Split a string up according to Unix shell-like rules for quotes and\n    backslashes.  In short: words are delimited by spaces, as long as those\n    spaces are not escaped by a backslash, or inside a quoted string.\n    Single and double quotes are equivalent, and the quote characters can\n    be backslash-escaped.  The backslash is stripped from any two-character\n    escape sequence, leaving only the escaped character.  The quote\n    characters are stripped from any quoted string.  Returns a list of\n    words.\n    "
    if _wordchars_re is None:
        _init_regex()
    s = s.strip()
    words = []
    pos = 0
    while s:
        m = _wordchars_re.match(s, pos)
        end = m.end()
        if end == len(s):
            words.append(s[:end])
            break
        if s[end] in string.whitespace:
            words.append(s[:end])
            s = s[end:].lstrip()
            pos = 0
        elif s[end] == "\\":
            s = s[:end] + s[(end + 1) :]
            pos = end + 1
        else:
            if s[end] == "'":
                m = _squote_re.match(s, end)
            elif s[end] == '"':
                m = _dquote_re.match(s, end)
            else:
                raise RuntimeError(("this can't happen (bad char '%c')" % s[end]))
            if m is None:
                raise ValueError(("bad string (mismatched %s quotes?)" % s[end]))
            (beg, end) = m.span()
            s = (s[:beg] + s[(beg + 1) : (end - 1)]) + s[end:]
            pos = m.end() - 2
        if pos >= len(s):
            words.append(s)
            break
    return words


def execute(func, args, msg=None, verbose=0, dry_run=0):
    "Perform some action that affects the outside world (eg.  by\n    writing to the filesystem).  Such actions are special because they\n    are disabled by the 'dry_run' flag.  This method takes care of all\n    that bureaucracy for you; all you have to do is supply the\n    function to call and an argument tuple for it (to embody the\n    \"external action\" being performed), and an optional message to\n    print.\n    "
    if msg is None:
        msg = "%s%r" % (func.__name__, args)
        if msg[(-2):] == ",)":
            msg = msg[0:(-2)] + ")"
    log.info(msg)
    if not dry_run:
        func(*args)


def strtobool(val):
    "Convert a string representation of truth to true (1) or false (0).\n\n    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values\n    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if\n    'val' is anything else.\n    "
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError(("invalid truth value %r" % (val,)))


def byte_compile(
    py_files,
    optimize=0,
    force=0,
    prefix=None,
    base_dir=None,
    verbose=1,
    dry_run=0,
    direct=None,
):
    "Byte-compile a collection of Python source files to .pyc\n    files in a __pycache__ subdirectory.  'py_files' is a list\n    of files to compile; any files that don't end in \".py\" are silently\n    skipped.  'optimize' must be one of the following:\n      0 - don't optimize\n      1 - normal optimization (like \"python -O\")\n      2 - extra optimization (like \"python -OO\")\n    If 'force' is true, all files are recompiled regardless of\n    timestamps.\n\n    The source filename encoded in each bytecode file defaults to the\n    filenames listed in 'py_files'; you can modify these with 'prefix' and\n    'basedir'.  'prefix' is a string that will be stripped off of each\n    source filename, and 'base_dir' is a directory name that will be\n    prepended (after 'prefix' is stripped).  You can supply either or both\n    (or neither) of 'prefix' and 'base_dir', as you wish.\n\n    If 'dry_run' is true, doesn't actually do anything that would\n    affect the filesystem.\n\n    Byte-compilation is either done directly in this interpreter process\n    with the standard py_compile module, or indirectly by writing a\n    temporary script and executing it.  Normally, you should let\n    'byte_compile()' figure out to use direct compilation or not (see\n    the source for details).  The 'direct' flag is used by the script\n    generated in indirect mode; unless you know what you're doing, leave\n    it set to None.\n    "
    import subprocess

    if sys.dont_write_bytecode:
        raise DistutilsByteCompileError("byte-compiling is disabled.")
    if direct is None:
        direct = __debug__ and (optimize == 0)
    if not direct:
        try:
            from tempfile import mkstemp

            (script_fd, script_name) = mkstemp(".py")
        except ImportError:
            from tempfile import mktemp

            (script_fd, script_name) = (None, mktemp(".py"))
        log.info("writing byte-compilation script '%s'", script_name)
        if not dry_run:
            if script_fd is not None:
                script = os.fdopen(script_fd, "w")
            else:
                script = open(script_name, "w")
            with script:
                script.write("from distutils.util import byte_compile\nfiles = [\n")
                script.write((",\n".join(map(repr, py_files)) + "]\n"))
                script.write(
                    (
                        "\nbyte_compile(files, optimize=%r, force=%r,\n             prefix=%r, base_dir=%r,\n             verbose=%r, dry_run=0,\n             direct=1)\n"
                        % (optimize, force, prefix, base_dir, verbose)
                    )
                )
        msg = distutils._DEPRECATION_MESSAGE
        cmd = [sys.executable]
        cmd.extend(subprocess._optim_args_from_interpreter_flags())
        cmd.append(f"-Wignore:{msg}:DeprecationWarning")
        cmd.append(script_name)
        spawn(cmd, dry_run=dry_run)
        execute(
            os.remove, (script_name,), ("removing %s" % script_name), dry_run=dry_run
        )
    else:
        from py_compile import compile

        for file in py_files:
            if file[(-3):] != ".py":
                continue
            if optimize >= 0:
                opt = "" if (optimize == 0) else optimize
                cfile = importlib.util.cache_from_source(file, optimization=opt)
            else:
                cfile = importlib.util.cache_from_source(file)
            dfile = file
            if prefix:
                if file[: len(prefix)] != prefix:
                    raise ValueError(
                        (
                            "invalid prefix: filename %r doesn't start with %r"
                            % (file, prefix)
                        )
                    )
                dfile = dfile[len(prefix) :]
            if base_dir:
                dfile = os.path.join(base_dir, dfile)
            cfile_base = os.path.basename(cfile)
            if direct:
                if force or newer(file, cfile):
                    log.info("byte-compiling %s to %s", file, cfile_base)
                    if not dry_run:
                        compile(file, cfile, dfile)
                else:
                    log.debug("skipping byte-compilation of %s to %s", file, cfile_base)


def rfc822_escape(header):
    "Return a version of the string escaped for inclusion in an\n    RFC-822 header, by ensuring there are 8 spaces space after each newline.\n    "
    lines = header.split("\n")
    sep = "\n" + (8 * " ")
    return sep.join(lines)


def run_2to3(files, fixer_names=None, options=None, explicit=None):
    "Invoke 2to3 on a list of Python files.\n    The files should all come from the build area, as the\n    modification is done in-place. To reduce the build time,\n    only files modified since the last invocation of this\n    function should be passed in the files argument."
    if not files:
        return
    from lib2to3.refactor import RefactoringTool, get_fixers_from_package

    class DistutilsRefactoringTool(RefactoringTool):
        def log_error(self, msg, *args, **kw):
            log.error(msg, *args)

        def log_message(self, msg, *args):
            log.info(msg, *args)

        def log_debug(self, msg, *args):
            log.debug(msg, *args)

    if fixer_names is None:
        fixer_names = get_fixers_from_package("lib2to3.fixes")
    r = DistutilsRefactoringTool(fixer_names, options=options)
    r.refactor(files, write=True)


def copydir_run_2to3(
    src, dest, template=None, fixer_names=None, options=None, explicit=None
):
    "Recursively copy a directory, only copying new and changed files,\n    running run_2to3 over all newly copied Python modules afterward.\n\n    If you give a template string, it's parsed like a MANIFEST.in.\n    "
    from distutils.dir_util import mkpath
    from distutils.file_util import copy_file
    from distutils.filelist import FileList

    filelist = FileList()
    curdir = os.getcwd()
    os.chdir(src)
    try:
        filelist.findall()
    finally:
        os.chdir(curdir)
    filelist.files[:] = filelist.allfiles
    if template:
        for line in template.splitlines():
            line = line.strip()
            if not line:
                continue
            filelist.process_template_line(line)
    copied = []
    for filename in filelist.files:
        outname = os.path.join(dest, filename)
        mkpath(os.path.dirname(outname))
        res = copy_file(os.path.join(src, filename), outname, update=1)
        if res[1]:
            copied.append(outname)
    run_2to3(
        [fn for fn in copied if fn.lower().endswith(".py")],
        fixer_names=fixer_names,
        options=options,
        explicit=explicit,
    )
    return copied


class Mixin2to3:
    "Mixin class for commands that run 2to3.\n    To configure 2to3, setup scripts may either change\n    the class variables, or inherit from individual commands\n    to override how 2to3 is invoked."
    fixer_names = None
    options = None
    explicit = None

    def run_2to3(self, files):
        return run_2to3(files, self.fixer_names, self.options, self.explicit)
