'\nLib/ctypes.util.find_library() support for AIX\nSimilar approach as done for Darwin support by using separate files\nbut unlike Darwin - no extension such as ctypes.macholib.*\n\ndlopen() is an interface to AIX initAndLoad() - primary documentation at:\nhttps://www.ibm.com/support/knowledgecenter/en/ssw_aix_61/com.ibm.aix.basetrf1/dlopen.htm\nhttps://www.ibm.com/support/knowledgecenter/en/ssw_aix_61/com.ibm.aix.basetrf1/load.htm\n\nAIX supports two styles for dlopen(): svr4 (System V Release 4) which is common on posix\nplatforms, but also a BSD style - aka SVR3.\n\nFrom AIX 5.3 Difference Addendum (December 2004)\n2.9 SVR4 linking affinity\nNowadays, there are two major object file formats used by the operating systems:\nXCOFF: The COFF enhanced by IBM and others. The original COFF (Common\nObject File Format) was the base of SVR3 and BSD 4.2 systems.\nELF:   Executable and Linking Format that was developed by AT&T and is a\nbase for SVR4 UNIX.\n\nWhile the shared library content is identical on AIX - one is located as a filepath name\n(svr4 style) and the other is located as a member of an archive (and the archive\nis located as a filepath name).\n\nThe key difference arises when supporting multiple abi formats (i.e., 32 and 64 bit).\nFor svr4 either only one ABI is supported, or there are two directories, or there\nare different file names. The most common solution for multiple ABI is multiple\ndirectories.\n\nFor the XCOFF (aka AIX) style - one directory (one archive file) is sufficient\nas multiple shared libraries can be in the archive - even sharing the same name.\nIn documentation the archive is also referred to as the "base" and the shared\nlibrary object is referred to as the "member".\n\nFor dlopen() on AIX (read initAndLoad()) the calls are similar.\nDefault activity occurs when no path information is provided. When path\ninformation is provided dlopen() does not search any other directories.\n\nFor SVR4 - the shared library name is the name of the file expected: libFOO.so\nFor AIX - the shared library is expressed as base(member). The search is for the\nbase (e.g., libFOO.a) and once the base is found the shared library - identified by\nmember (e.g., libFOO.so, or shr.o) is located and loaded.\n\nThe mode bit RTLD_MEMBER tells initAndLoad() that it needs to use the AIX (SVR3)\nnaming style.\n'
__author__ = "Michael Felt <aixtools@felt.demon.nl>"
import re
from os import environ, path
from sys import executable
from ctypes import c_void_p, sizeof
from subprocess import Popen, PIPE, DEVNULL

AIX_ABI = sizeof(c_void_p) * 8
from sys import maxsize


def _last_version(libnames, sep):
    def _num_version(libname):
        parts = libname.split(sep)
        nums = []
        try:
            while parts:
                nums.insert(0, int(parts.pop()))
        except ValueError:
            pass
        return nums or [maxsize]

    return max(reversed(libnames), key=_num_version)


def get_ld_header(p):
    ld_header = None
    for line in p.stdout:
        if line.startswith(("/", "./", "../")):
            ld_header = line
        elif "INDEX" in line:
            return ld_header.rstrip("\n")
    return None


def get_ld_header_info(p):
    info = []
    for line in p.stdout:
        if re.match("[0-9]", line):
            info.append(line)
        else:
            break
    return info


def get_ld_headers(file):
    "\n    Parse the header of the loader section of executable and archives\n    This function calls /usr/bin/dump -H as a subprocess\n    and returns a list of (ld_header, ld_header_info) tuples.\n    "
    ldr_headers = []
    p = Popen(
        ["/usr/bin/dump", f"-X{AIX_ABI}", "-H", file],
        universal_newlines=True,
        stdout=PIPE,
        stderr=DEVNULL,
    )
    while True:
        ld_header = get_ld_header(p)
        if ld_header:
            ldr_headers.append((ld_header, get_ld_header_info(p)))
        else:
            break
    p.stdout.close()
    p.wait()
    return ldr_headers


def get_shared(ld_headers):
    '\n    extract the shareable objects from ld_headers\n    character "[" is used to strip off the path information.\n    Note: the "[" and "]" characters that are part of dump -H output\n    are not removed here.\n    '
    shared = []
    for (line, _) in ld_headers:
        if "[" in line:
            shared.append(line[line.index("[") : (-1)])
    return shared


def get_one_match(expr, lines):
    '\n    Must be only one match, otherwise result is None.\n    When there is a match, strip leading "[" and trailing "]"\n    '
    expr = f"\[({expr})\]"
    matches = list(filter(None, (re.search(expr, line) for line in lines)))
    if len(matches) == 1:
        return matches[0].group(1)
    else:
        return None


def get_legacy(members):
    "\n    This routine provides historical aka legacy naming schemes started\n    in AIX4 shared library support for library members names.\n    e.g., in /usr/lib/libc.a the member name shr.o for 32-bit binary and\n    shr_64.o for 64-bit binary.\n    "
    if AIX_ABI == 64:
        expr = "shr4?_?64\\.o"
        member = get_one_match(expr, members)
        if member:
            return member
    else:
        for name in ["shr.o", "shr4.o"]:
            member = get_one_match(re.escape(name), members)
            if member:
                return member
    return None


def get_version(name, members):
    '\n    Sort list of members and return highest numbered version - if it exists.\n    This function is called when an unversioned libFOO.a(libFOO.so) has\n    not been found.\n\n    Versioning for the member name is expected to follow\n    GNU LIBTOOL conventions: the highest version (x, then X.y, then X.Y.z)\n     * find [libFoo.so.X]\n     * find [libFoo.so.X.Y]\n     * find [libFoo.so.X.Y.Z]\n\n    Before the GNU convention became the standard scheme regardless of\n    binary size AIX packagers used GNU convention "as-is" for 32-bit\n    archive members but used an "distinguishing" name for 64-bit members.\n    This scheme inserted either 64 or _64 between libFOO and .so\n    - generally libFOO_64.so, but occasionally libFOO64.so\n    '
    exprs = [f"lib{name}\.so\.[0-9]+[0-9.]*", f"lib{name}_?64\.so\.[0-9]+[0-9.]*"]
    for expr in exprs:
        versions = []
        for line in members:
            m = re.search(expr, line)
            if m:
                versions.append(m.group(0))
        if versions:
            return _last_version(versions, ".")
    return None


def get_member(name, members):
    "\n    Return an archive member matching the request in name.\n    Name is the library name without any prefix like lib, suffix like .so,\n    or version number.\n    Given a list of members find and return the most appropriate result\n    Priority is given to generic libXXX.so, then a versioned libXXX.so.a.b.c\n    and finally, legacy AIX naming scheme.\n    "
    expr = f"lib{name}\.so"
    member = get_one_match(expr, members)
    if member:
        return member
    elif AIX_ABI == 64:
        expr = f"lib{name}64\.so"
        member = get_one_match(expr, members)
    if member:
        return member
    member = get_version(name, members)
    if member:
        return member
    else:
        return get_legacy(members)


def get_libpaths():
    '\n    On AIX, the buildtime searchpath is stored in the executable.\n    as "loader header information".\n    The command /usr/bin/dump -H extracts this info.\n    Prefix searched libraries with LD_LIBRARY_PATH (preferred),\n    or LIBPATH if defined. These paths are appended to the paths\n    to libraries the python executable is linked with.\n    This mimics AIX dlopen() behavior.\n    '
    libpaths = environ.get("LD_LIBRARY_PATH")
    if libpaths is None:
        libpaths = environ.get("LIBPATH")
    if libpaths is None:
        libpaths = []
    else:
        libpaths = libpaths.split(":")
    objects = get_ld_headers(executable)
    for (_, lines) in objects:
        for line in lines:
            path = line.split()[1]
            if "/" in path:
                libpaths.extend(path.split(":"))
    return libpaths


def find_shared(paths, name):
    '\n    paths is a list of directories to search for an archive.\n    name is the abbreviated name given to find_library().\n    Process: search "paths" for archive, and if an archive is found\n    return the result of get_member().\n    If an archive is not found then return None\n    '
    for dir in paths:
        if dir == "/lib":
            continue
        base = f"lib{name}.a"
        archive = path.join(dir, base)
        if path.exists(archive):
            members = get_shared(get_ld_headers(archive))
            member = get_member(re.escape(name), members)
            if member != None:
                return (base, member)
            else:
                return (None, None)
    return (None, None)


def find_library(name):
    "AIX implementation of ctypes.util.find_library()\n    Find an archive member that will dlopen(). If not available,\n    also search for a file (or link) with a .so suffix.\n\n    AIX supports two types of schemes that can be used with dlopen().\n    The so-called SystemV Release4 (svr4) format is commonly suffixed\n    with .so while the (default) AIX scheme has the library (archive)\n    ending with the suffix .a\n    As an archive has multiple members (e.g., 32-bit and 64-bit) in one file\n    the argument passed to dlopen must include both the library and\n    the member names in a single string.\n\n    find_library() looks first for an archive (.a) with a suitable member.\n    If no archive+member pair is found, look for a .so file.\n    "
    libpaths = get_libpaths()
    (base, member) = find_shared(libpaths, name)
    if base != None:
        return f"{base}({member})"
    soname = f"lib{name}.so"
    for dir in libpaths:
        if dir == "/lib":
            continue
        shlib = path.join(dir, soname)
        if path.exists(shlib):
            return soname
    return None
