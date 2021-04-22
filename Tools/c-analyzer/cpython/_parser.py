import os.path
import re
from c_parser.preprocessor import get_preprocessor as _get_preprocessor
from c_parser import parse_file as _parse_file, parse_files as _parse_files
from . import REPO_ROOT

GLOB_ALL = "**/*"


def clean_lines(text):
    "Clear out comments, blank lines, and leading/trailing whitespace."
    lines = (line.strip() for line in text.splitlines())
    lines = (
        line.partition("#")[0].rstrip()
        for line in lines
        if (line and (not line.startswith("#")))
    )
    glob_all = f"{GLOB_ALL} "
    lines = (re.sub("^[*] ", glob_all, line) for line in lines)
    lines = (os.path.join(REPO_ROOT, line) for line in lines)
    return list(lines)


"\n@begin=sh@\n./python ../c-parser/cpython.py\n    --exclude '+../c-parser/EXCLUDED'\n    --macros '+../c-parser/MACROS'\n    --incldirs '+../c-parser/INCL_DIRS'\n    --same './Include/cpython/'\n    Include/*.h\n    Include/internal/*.h\n    Modules/**/*.c\n    Objects/**/*.c\n    Parser/**/*.c\n    Python/**/*.c\n@end=sh@\n"
EXCLUDED = clean_lines(
    "\n# @begin=conf@\n\n# Rather than fixing for this one, we manually make sure it's okay.\nModules/_sha3/kcp/KeccakP-1600-opt64.c\n\n# OSX\n#Modules/_ctypes/darwin/*.c\n#Modules/_ctypes/libffi_osx/*.c\nModules/_scproxy.c                # SystemConfiguration/SystemConfiguration.h\n\n# Windows\nModules/_winapi.c               # windows.h\nModules/overlapped.c            # winsock.h\nPython/dynload_win.c            # windows.h\nModules/expat/winconfig.h\nPython/thread_nt.h\n\n# other OS-dependent\nPython/dynload_dl.c             # dl.h\nPython/dynload_hpux.c           # dl.h\nPython/dynload_aix.c            # sys/ldr.h\nPython/thread_pthread.h\n\n# only huge constants (safe but parsing is slow)\nModules/_ssl_data.h\nModules/unicodedata_db.h\nModules/unicodename_db.h\nModules/cjkcodecs/mappings_*.h\nObjects/unicodetype_db.h\nPython/importlib.h\nPython/importlib_external.h\nPython/importlib_zipimport.h\n\n# @end=conf@\n"
)
EXCLUDED += clean_lines(
    "\n# The tool should be able to parse these...\n\nModules/hashlib.h\nObjects/stringlib/codecs.h\nObjects/stringlib/count.h\nObjects/stringlib/ctype.h\nObjects/stringlib/fastsearch.h\nObjects/stringlib/find.h\nObjects/stringlib/find_max_char.h\nObjects/stringlib/partition.h\nObjects/stringlib/replace.h\nObjects/stringlib/split.h\n\nModules/_dbmmodule.c\nModules/cjkcodecs/_codecs_*.c\nModules/expat/xmlrole.c\nModules/expat/xmlparse.c\nPython/initconfig.c\n"
)
INCL_DIRS = clean_lines(
    "\n# @begin=tsv@\n\nglob\tdirname\n*\t.\n*\t./Include\n*\t./Include/internal\n\nModules/_tkinter.c\t/usr/include/tcl8.6\nModules/tkappinit.c\t/usr/include/tcl\nModules/_decimal/**/*.c\tModules/_decimal/libmpdec\n\n# @end=tsv@\n"
)[1:]
MACROS = clean_lines(
    "\n# @begin=tsv@\n\nglob\tname\tvalue\n\nInclude/internal/*.h\tPy_BUILD_CORE\t1\nPython/**/*.c\tPy_BUILD_CORE\t1\nParser/**/*.c\tPy_BUILD_CORE\t1\nObjects/**/*.c\tPy_BUILD_CORE\t1\n\nModules/faulthandler.c\tPy_BUILD_CORE\t1\nModules/_functoolsmodule.c\tPy_BUILD_CORE\t1\nModules/gcmodule.c\tPy_BUILD_CORE\t1\nModules/getpath.c\tPy_BUILD_CORE\t1\nModules/_io/*.c\tPy_BUILD_CORE\t1\nModules/itertoolsmodule.c\tPy_BUILD_CORE\t1\nModules/_localemodule.c\tPy_BUILD_CORE\t1\nModules/main.c\tPy_BUILD_CORE\t1\nModules/posixmodule.c\tPy_BUILD_CORE\t1\nModules/signalmodule.c\tPy_BUILD_CORE\t1\nModules/_threadmodule.c\tPy_BUILD_CORE\t1\nModules/_tracemalloc.c\tPy_BUILD_CORE\t1\nModules/_asynciomodule.c\tPy_BUILD_CORE\t1\nModules/mathmodule.c\tPy_BUILD_CORE\t1\nModules/cmathmodule.c\tPy_BUILD_CORE\t1\nModules/_weakref.c\tPy_BUILD_CORE\t1\nModules/sha256module.c\tPy_BUILD_CORE\t1\nModules/sha512module.c\tPy_BUILD_CORE\t1\nModules/_datetimemodule.c\tPy_BUILD_CORE\t1\nModules/_ctypes/cfield.c\tPy_BUILD_CORE\t1\nModules/_heapqmodule.c\tPy_BUILD_CORE\t1\nModules/_posixsubprocess.c\tPy_BUILD_CORE\t1\nModules/_sre.c\tPy_BUILD_CORE\t1\nModules/_collectionsmodule.c\tPy_BUILD_CORE\t1\nModules/_zoneinfo.c\tPy_BUILD_CORE\t1\nModules/unicodedata.c\tPy_BUILD_CORE\t1\nModules/_cursesmodule.c\tPy_BUILD_CORE\t1\nModules/_ctypes/_ctypes.c\tPy_BUILD_CORE\t1\nObjects/stringlib/codecs.h\tPy_BUILD_CORE\t1\nPython/ceval_gil.h\tPy_BUILD_CORE\t1\nPython/condvar.h\tPy_BUILD_CORE\t1\n\nModules/_json.c\tPy_BUILD_CORE_BUILTIN\t1\nModules/_pickle.c\tPy_BUILD_CORE_BUILTIN\t1\nModules/_testinternalcapi.c\tPy_BUILD_CORE_BUILTIN\t1\n\nInclude/cpython/abstract.h\tPy_CPYTHON_ABSTRACTOBJECT_H\t1\nInclude/cpython/bytearrayobject.h\tPy_CPYTHON_BYTEARRAYOBJECT_H\t1\nInclude/cpython/bytesobject.h\tPy_CPYTHON_BYTESOBJECT_H\t1\nInclude/cpython/ceval.h\tPy_CPYTHON_CEVAL_H\t1\nInclude/cpython/code.h\tPy_CPYTHON_CODE_H\t1\nInclude/cpython/dictobject.h\tPy_CPYTHON_DICTOBJECT_H\t1\nInclude/cpython/fileobject.h\tPy_CPYTHON_FILEOBJECT_H\t1\nInclude/cpython/fileutils.h\tPy_CPYTHON_FILEUTILS_H\t1\nInclude/cpython/frameobject.h\tPy_CPYTHON_FRAMEOBJECT_H\t1\nInclude/cpython/import.h\tPy_CPYTHON_IMPORT_H\t1\nInclude/cpython/interpreteridobject.h\tPy_CPYTHON_INTERPRETERIDOBJECT_H\t1\nInclude/cpython/listobject.h\tPy_CPYTHON_LISTOBJECT_H\t1\nInclude/cpython/methodobject.h\tPy_CPYTHON_METHODOBJECT_H\t1\nInclude/cpython/object.h\tPy_CPYTHON_OBJECT_H\t1\nInclude/cpython/objimpl.h\tPy_CPYTHON_OBJIMPL_H\t1\nInclude/cpython/pyerrors.h\tPy_CPYTHON_ERRORS_H\t1\nInclude/cpython/pylifecycle.h\tPy_CPYTHON_PYLIFECYCLE_H\t1\nInclude/cpython/pymem.h\tPy_CPYTHON_PYMEM_H\t1\nInclude/cpython/pystate.h\tPy_CPYTHON_PYSTATE_H\t1\nInclude/cpython/sysmodule.h\tPy_CPYTHON_SYSMODULE_H\t1\nInclude/cpython/traceback.h\tPy_CPYTHON_TRACEBACK_H\t1\nInclude/cpython/tupleobject.h\tPy_CPYTHON_TUPLEOBJECT_H\t1\nInclude/cpython/unicodeobject.h\tPy_CPYTHON_UNICODEOBJECT_H\t1\n\n# implied include of pyport.h\nInclude/**/*.h\tPyAPI_DATA(RTYPE)\textern RTYPE\nInclude/**/*.h\tPyAPI_FUNC(RTYPE)\tRTYPE\nInclude/**/*.h\tPy_DEPRECATED(VER)\t/* */\nInclude/**/*.h\t_Py_NO_RETURN\t/* */\nInclude/**/*.h\tPYLONG_BITS_IN_DIGIT\t30\nModules/**/*.c\tPyMODINIT_FUNC\tPyObject*\nObjects/unicodeobject.c\tPyMODINIT_FUNC\tPyObject*\nPython/marshal.c\tPyMODINIT_FUNC\tPyObject*\nPython/_warnings.c\tPyMODINIT_FUNC\tPyObject*\nPython/Python-ast.c\tPyMODINIT_FUNC\tPyObject*\nPython/import.c\tPyMODINIT_FUNC\tPyObject*\nModules/_testcapimodule.c\tPyAPI_FUNC(RTYPE)\tRTYPE\nPython/getargs.c\tPyAPI_FUNC(RTYPE)\tRTYPE\nObjects/stringlib/unicode_format.h\tPy_LOCAL_INLINE(type)\tstatic inline type\n\n# implied include of pymacro.h\n*/clinic/*.c.h\tPyDoc_VAR(name)\tstatic const char name[]\n*/clinic/*.c.h\tPyDoc_STR(str)\tstr\n*/clinic/*.c.h\tPyDoc_STRVAR(name,str)\tPyDoc_VAR(name) = PyDoc_STR(str)\n\n# implied include of exports.h\n#Modules/_io/bytesio.c\tPy_EXPORTED_SYMBOL\t/* */\n\n# implied include of object.h\nInclude/**/*.h\tPyObject_HEAD\tPyObject ob_base;\nInclude/**/*.h\tPyObject_VAR_HEAD\tPyVarObject ob_base;\n\n# implied include of pyconfig.h\nInclude/**/*.h\tSIZEOF_WCHAR_T\t4\n\n# implied include of <unistd.h>\nInclude/**/*.h\t_POSIX_THREADS\t1\n\n# from Makefile\nModules/getpath.c\tPYTHONPATH\t1\nModules/getpath.c\tPREFIX\t...\nModules/getpath.c\tEXEC_PREFIX\t...\nModules/getpath.c\tVERSION\t...\nModules/getpath.c\tVPATH\t...\n\n# from Modules/_sha3/sha3module.c\nModules/_sha3/kcp/KeccakP-1600-inplace32BI.c\tPLATFORM_BYTE_ORDER\t4321  # force big-endian\nModules/_sha3/kcp/*.c\tKeccakOpt\t64\nModules/_sha3/kcp/*.c\tKeccakP200_excluded\t1\nModules/_sha3/kcp/*.c\tKeccakP400_excluded\t1\nModules/_sha3/kcp/*.c\tKeccakP800_excluded\t1\n\n# See: setup.py\nModules/_decimal/**/*.c\tCONFIG_64\t1\nModules/_decimal/**/*.c\tASM\t1\nModules/expat/xmlparse.c\tHAVE_EXPAT_CONFIG_H\t1\nModules/expat/xmlparse.c\tXML_POOR_ENTROPY\t1\nModules/_dbmmodule.c\tHAVE_GDBM_DASH_NDBM_H\t1\n\n# others\nModules/sre_lib.h\tLOCAL(type)\tstatic inline type\nModules/sre_lib.h\tSRE(F)\tsre_ucs2_##F\nObjects/stringlib/codecs.h\tSTRINGLIB_IS_UNICODE\t1\n\n# @end=tsv@\n"
)[1:]
SAME = ["./Include/cpython/"]


def get_preprocessor(*, file_macros=None, file_incldirs=None, file_same=None, **kwargs):
    macros = tuple(MACROS)
    if file_macros:
        macros += tuple(file_macros)
    incldirs = tuple(INCL_DIRS)
    if file_incldirs:
        incldirs += tuple(file_incldirs)
    return _get_preprocessor(
        file_macros=macros, file_incldirs=incldirs, file_same=file_same, **kwargs
    )


def parse_file(filename, *, match_kind=None, ignore_exc=None, log_err=None):
    get_file_preprocessor = get_preprocessor(ignore_exc=ignore_exc, log_err=log_err)
    (
        yield from _parse_file(
            filename, match_kind=match_kind, get_file_preprocessor=get_file_preprocessor
        )
    )


def parse_files(
    filenames=None,
    *,
    match_kind=None,
    ignore_exc=None,
    log_err=None,
    get_file_preprocessor=None,
    **file_kwargs,
):
    if get_file_preprocessor is None:
        get_file_preprocessor = get_preprocessor(ignore_exc=ignore_exc, log_err=log_err)
    (
        yield from _parse_files(
            filenames,
            match_kind=match_kind,
            get_file_preprocessor=get_file_preprocessor,
            **file_kwargs,
        )
    )
