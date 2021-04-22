"distutils.ccompiler\n\nContains CCompiler, an abstract base class that defines the interface\nfor the Distutils compiler abstraction model."
import sys, os, re
from distutils.errors import *
from distutils.spawn import spawn
from distutils.file_util import move_file
from distutils.dir_util import mkpath
from distutils.dep_util import newer_group
from distutils.util import split_quoted, execute
from distutils import log


class CCompiler:
    "Abstract base class to define the interface that must be implemented\n    by real compiler classes.  Also has some utility methods used by\n    several compiler classes.\n\n    The basic idea behind a compiler abstraction class is that each\n    instance can be used for all the compile/link steps in building a\n    single project.  Thus, attributes common to all of those compile and\n    link steps -- include directories, macros to define, libraries to link\n    against, etc. -- are attributes of the compiler instance.  To allow for\n    variability in how individual files are treated, most of those\n    attributes may be varied on a per-compilation or per-link basis.\n    "
    compiler_type = None
    src_extensions = None
    obj_extension = None
    static_lib_extension = None
    shared_lib_extension = None
    static_lib_format = None
    shared_lib_format = None
    exe_extension = None
    language_map = {".c": "c", ".cc": "c++", ".cpp": "c++", ".cxx": "c++", ".m": "objc"}
    language_order = ["c++", "objc", "c"]

    def __init__(self, verbose=0, dry_run=0, force=0):
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose
        self.output_dir = None
        self.macros = []
        self.include_dirs = []
        self.libraries = []
        self.library_dirs = []
        self.runtime_library_dirs = []
        self.objects = []
        for key in self.executables.keys():
            self.set_executable(key, self.executables[key])

    def set_executables(self, **kwargs):
        "Define the executables (and options for them) that will be run\n        to perform the various stages of compilation.  The exact set of\n        executables that may be specified here depends on the compiler\n        class (via the 'executables' class attribute), but most will have:\n          compiler      the C/C++ compiler\n          linker_so     linker used to create shared objects and libraries\n          linker_exe    linker used to create binary executables\n          archiver      static library creator\n\n        On platforms with a command-line (Unix, DOS/Windows), each of these\n        is a string that will be split into executable name and (optional)\n        list of arguments.  (Splitting the string is done similarly to how\n        Unix shells operate: words are delimited by spaces, but quotes and\n        backslashes can override this.  See\n        'distutils.util.split_quoted()'.)\n        "
        for key in kwargs:
            if key not in self.executables:
                raise ValueError(
                    (
                        "unknown executable '%s' for class %s"
                        % (key, self.__class__.__name__)
                    )
                )
            self.set_executable(key, kwargs[key])

    def set_executable(self, key, value):
        if isinstance(value, str):
            setattr(self, key, split_quoted(value))
        else:
            setattr(self, key, value)

    def _find_macro(self, name):
        i = 0
        for defn in self.macros:
            if defn[0] == name:
                return i
            i += 1
        return None

    def _check_macro_definitions(self, definitions):
        "Ensures that every element of 'definitions' is a valid macro\n        definition, ie. either (name,value) 2-tuple or a (name,) tuple.  Do\n        nothing if all definitions are OK, raise TypeError otherwise.\n        "
        for defn in definitions:
            if not (
                isinstance(defn, tuple)
                and (
                    (len(defn) in (1, 2))
                    and (isinstance(defn[1], str) or (defn[1] is None))
                )
                and isinstance(defn[0], str)
            ):
                raise TypeError(
                    (
                        (
                            ("invalid macro definition '%s': " % defn)
                            + "must be tuple (string,), (string, string), or "
                        )
                        + "(string, None)"
                    )
                )

    def define_macro(self, name, value=None):
        "Define a preprocessor macro for all compilations driven by this\n        compiler object.  The optional parameter 'value' should be a\n        string; if it is not supplied, then the macro will be defined\n        without an explicit value and the exact outcome depends on the\n        compiler used (XXX true? does ANSI say anything about this?)\n        "
        i = self._find_macro(name)
        if i is not None:
            del self.macros[i]
        self.macros.append((name, value))

    def undefine_macro(self, name):
        "Undefine a preprocessor macro for all compilations driven by\n        this compiler object.  If the same macro is defined by\n        'define_macro()' and undefined by 'undefine_macro()' the last call\n        takes precedence (including multiple redefinitions or\n        undefinitions).  If the macro is redefined/undefined on a\n        per-compilation basis (ie. in the call to 'compile()'), then that\n        takes precedence.\n        "
        i = self._find_macro(name)
        if i is not None:
            del self.macros[i]
        undefn = (name,)
        self.macros.append(undefn)

    def add_include_dir(self, dir):
        "Add 'dir' to the list of directories that will be searched for\n        header files.  The compiler is instructed to search directories in\n        the order in which they are supplied by successive calls to\n        'add_include_dir()'.\n        "
        self.include_dirs.append(dir)

    def set_include_dirs(self, dirs):
        "Set the list of directories that will be searched to 'dirs' (a\n        list of strings).  Overrides any preceding calls to\n        'add_include_dir()'; subsequence calls to 'add_include_dir()' add\n        to the list passed to 'set_include_dirs()'.  This does not affect\n        any list of standard include directories that the compiler may\n        search by default.\n        "
        self.include_dirs = dirs[:]

    def add_library(self, libname):
        "Add 'libname' to the list of libraries that will be included in\n        all links driven by this compiler object.  Note that 'libname'\n        should *not* be the name of a file containing a library, but the\n        name of the library itself: the actual filename will be inferred by\n        the linker, the compiler, or the compiler class (depending on the\n        platform).\n\n        The linker will be instructed to link against libraries in the\n        order they were supplied to 'add_library()' and/or\n        'set_libraries()'.  It is perfectly valid to duplicate library\n        names; the linker will be instructed to link against libraries as\n        many times as they are mentioned.\n        "
        self.libraries.append(libname)

    def set_libraries(self, libnames):
        "Set the list of libraries to be included in all links driven by\n        this compiler object to 'libnames' (a list of strings).  This does\n        not affect any standard system libraries that the linker may\n        include by default.\n        "
        self.libraries = libnames[:]

    def add_library_dir(self, dir):
        "Add 'dir' to the list of directories that will be searched for\n        libraries specified to 'add_library()' and 'set_libraries()'.  The\n        linker will be instructed to search for libraries in the order they\n        are supplied to 'add_library_dir()' and/or 'set_library_dirs()'.\n        "
        self.library_dirs.append(dir)

    def set_library_dirs(self, dirs):
        "Set the list of library search directories to 'dirs' (a list of\n        strings).  This does not affect any standard library search path\n        that the linker may search by default.\n        "
        self.library_dirs = dirs[:]

    def add_runtime_library_dir(self, dir):
        "Add 'dir' to the list of directories that will be searched for\n        shared libraries at runtime.\n        "
        self.runtime_library_dirs.append(dir)

    def set_runtime_library_dirs(self, dirs):
        "Set the list of directories to search for shared libraries at\n        runtime to 'dirs' (a list of strings).  This does not affect any\n        standard search path that the runtime linker may search by\n        default.\n        "
        self.runtime_library_dirs = dirs[:]

    def add_link_object(self, object):
        "Add 'object' to the list of object files (or analogues, such as\n        explicitly named library files or the output of \"resource\n        compilers\") to be included in every link driven by this compiler\n        object.\n        "
        self.objects.append(object)

    def set_link_objects(self, objects):
        "Set the list of object files (or analogues) to be included in\n        every link to 'objects'.  This does not affect any standard object\n        files that the linker may include by default (such as system\n        libraries).\n        "
        self.objects = objects[:]

    def _setup_compile(self, outdir, macros, incdirs, sources, depends, extra):
        "Process arguments and decide which source files to compile."
        if outdir is None:
            outdir = self.output_dir
        elif not isinstance(outdir, str):
            raise TypeError("'output_dir' must be a string or None")
        if macros is None:
            macros = self.macros
        elif isinstance(macros, list):
            macros = macros + (self.macros or [])
        else:
            raise TypeError("'macros' (if supplied) must be a list of tuples")
        if incdirs is None:
            incdirs = self.include_dirs
        elif isinstance(incdirs, (list, tuple)):
            incdirs = list(incdirs) + (self.include_dirs or [])
        else:
            raise TypeError("'include_dirs' (if supplied) must be a list of strings")
        if extra is None:
            extra = []
        objects = self.object_filenames(sources, strip_dir=0, output_dir=outdir)
        assert len(objects) == len(sources)
        pp_opts = gen_preprocess_options(macros, incdirs)
        build = {}
        for i in range(len(sources)):
            src = sources[i]
            obj = objects[i]
            ext = os.path.splitext(src)[1]
            self.mkpath(os.path.dirname(obj))
            build[obj] = (src, ext)
        return (macros, objects, extra, pp_opts, build)

    def _get_cc_args(self, pp_opts, debug, before):
        cc_args = pp_opts + ["-c"]
        if debug:
            cc_args[:0] = ["-g"]
        if before:
            cc_args[:0] = before
        return cc_args

    def _fix_compile_args(self, output_dir, macros, include_dirs):
        "Typecheck and fix-up some of the arguments to the 'compile()'\n        method, and return fixed-up values.  Specifically: if 'output_dir'\n        is None, replaces it with 'self.output_dir'; ensures that 'macros'\n        is a list, and augments it with 'self.macros'; ensures that\n        'include_dirs' is a list, and augments it with 'self.include_dirs'.\n        Guarantees that the returned values are of the correct type,\n        i.e. for 'output_dir' either string or None, and for 'macros' and\n        'include_dirs' either list or None.\n        "
        if output_dir is None:
            output_dir = self.output_dir
        elif not isinstance(output_dir, str):
            raise TypeError("'output_dir' must be a string or None")
        if macros is None:
            macros = self.macros
        elif isinstance(macros, list):
            macros = macros + (self.macros or [])
        else:
            raise TypeError("'macros' (if supplied) must be a list of tuples")
        if include_dirs is None:
            include_dirs = self.include_dirs
        elif isinstance(include_dirs, (list, tuple)):
            include_dirs = list(include_dirs) + (self.include_dirs or [])
        else:
            raise TypeError("'include_dirs' (if supplied) must be a list of strings")
        return (output_dir, macros, include_dirs)

    def _prep_compile(self, sources, output_dir, depends=None):
        "Decide which souce files must be recompiled.\n\n        Determine the list of object files corresponding to 'sources',\n        and figure out which ones really need to be recompiled.\n        Return a list of all object files and a dictionary telling\n        which source files can be skipped.\n        "
        objects = self.object_filenames(sources, output_dir=output_dir)
        assert len(objects) == len(sources)
        return (objects, {})

    def _fix_object_args(self, objects, output_dir):
        "Typecheck and fix up some arguments supplied to various methods.\n        Specifically: ensure that 'objects' is a list; if output_dir is\n        None, replace with self.output_dir.  Return fixed versions of\n        'objects' and 'output_dir'.\n        "
        if not isinstance(objects, (list, tuple)):
            raise TypeError("'objects' must be a list or tuple of strings")
        objects = list(objects)
        if output_dir is None:
            output_dir = self.output_dir
        elif not isinstance(output_dir, str):
            raise TypeError("'output_dir' must be a string or None")
        return (objects, output_dir)

    def _fix_lib_args(self, libraries, library_dirs, runtime_library_dirs):
        "Typecheck and fix up some of the arguments supplied to the\n        'link_*' methods.  Specifically: ensure that all arguments are\n        lists, and augment them with their permanent versions\n        (eg. 'self.libraries' augments 'libraries').  Return a tuple with\n        fixed versions of all arguments.\n        "
        if libraries is None:
            libraries = self.libraries
        elif isinstance(libraries, (list, tuple)):
            libraries = list(libraries) + (self.libraries or [])
        else:
            raise TypeError("'libraries' (if supplied) must be a list of strings")
        if library_dirs is None:
            library_dirs = self.library_dirs
        elif isinstance(library_dirs, (list, tuple)):
            library_dirs = list(library_dirs) + (self.library_dirs or [])
        else:
            raise TypeError("'library_dirs' (if supplied) must be a list of strings")
        if runtime_library_dirs is None:
            runtime_library_dirs = self.runtime_library_dirs
        elif isinstance(runtime_library_dirs, (list, tuple)):
            runtime_library_dirs = list(runtime_library_dirs) + (
                self.runtime_library_dirs or []
            )
        else:
            raise TypeError(
                "'runtime_library_dirs' (if supplied) must be a list of strings"
            )
        return (libraries, library_dirs, runtime_library_dirs)

    def _need_link(self, objects, output_file):
        "Return true if we need to relink the files listed in 'objects'\n        to recreate 'output_file'.\n        "
        if self.force:
            return True
        else:
            if self.dry_run:
                newer = newer_group(objects, output_file, missing="newer")
            else:
                newer = newer_group(objects, output_file)
            return newer

    def detect_language(self, sources):
        "Detect the language of a given file, or list of files. Uses\n        language_map, and language_order to do the job.\n        "
        if not isinstance(sources, list):
            sources = [sources]
        lang = None
        index = len(self.language_order)
        for source in sources:
            (base, ext) = os.path.splitext(source)
            extlang = self.language_map.get(ext)
            try:
                extindex = self.language_order.index(extlang)
                if extindex < index:
                    lang = extlang
                    index = extindex
            except ValueError:
                pass
        return lang

    def preprocess(
        self,
        source,
        output_file=None,
        macros=None,
        include_dirs=None,
        extra_preargs=None,
        extra_postargs=None,
    ):
        "Preprocess a single C/C++ source file, named in 'source'.\n        Output will be written to file named 'output_file', or stdout if\n        'output_file' not supplied.  'macros' is a list of macro\n        definitions as for 'compile()', which will augment the macros set\n        with 'define_macro()' and 'undefine_macro()'.  'include_dirs' is a\n        list of directory names that will be added to the default list.\n\n        Raises PreprocessError on failure.\n        "
        pass

    def compile(
        self,
        sources,
        output_dir=None,
        macros=None,
        include_dirs=None,
        debug=0,
        extra_preargs=None,
        extra_postargs=None,
        depends=None,
    ):
        "Compile one or more source files.\n\n        'sources' must be a list of filenames, most likely C/C++\n        files, but in reality anything that can be handled by a\n        particular compiler and compiler class (eg. MSVCCompiler can\n        handle resource files in 'sources').  Return a list of object\n        filenames, one per source filename in 'sources'.  Depending on\n        the implementation, not all source files will necessarily be\n        compiled, but all corresponding object filenames will be\n        returned.\n\n        If 'output_dir' is given, object files will be put under it, while\n        retaining their original path component.  That is, \"foo/bar.c\"\n        normally compiles to \"foo/bar.o\" (for a Unix implementation); if\n        'output_dir' is \"build\", then it would compile to\n        \"build/foo/bar.o\".\n\n        'macros', if given, must be a list of macro definitions.  A macro\n        definition is either a (name, value) 2-tuple or a (name,) 1-tuple.\n        The former defines a macro; if the value is None, the macro is\n        defined without an explicit value.  The 1-tuple case undefines a\n        macro.  Later definitions/redefinitions/ undefinitions take\n        precedence.\n\n        'include_dirs', if given, must be a list of strings, the\n        directories to add to the default include file search path for this\n        compilation only.\n\n        'debug' is a boolean; if true, the compiler will be instructed to\n        output debug symbols in (or alongside) the object file(s).\n\n        'extra_preargs' and 'extra_postargs' are implementation- dependent.\n        On platforms that have the notion of a command-line (e.g. Unix,\n        DOS/Windows), they are most likely lists of strings: extra\n        command-line arguments to prepend/append to the compiler command\n        line.  On other platforms, consult the implementation class\n        documentation.  In any event, they are intended as an escape hatch\n        for those occasions when the abstract compiler framework doesn't\n        cut the mustard.\n\n        'depends', if given, is a list of filenames that all targets\n        depend on.  If a source file is older than any file in\n        depends, then the source file will be recompiled.  This\n        supports dependency tracking, but only at a coarse\n        granularity.\n\n        Raises CompileError on failure.\n        "
        (macros, objects, extra_postargs, pp_opts, build) = self._setup_compile(
            output_dir, macros, include_dirs, sources, depends, extra_postargs
        )
        cc_args = self._get_cc_args(pp_opts, debug, extra_preargs)
        for obj in objects:
            try:
                (src, ext) = build[obj]
            except KeyError:
                continue
            self._compile(obj, src, ext, cc_args, extra_postargs, pp_opts)
        return objects

    def _compile(self, obj, src, ext, cc_args, extra_postargs, pp_opts):
        "Compile 'src' to product 'obj'."
        pass

    def create_static_lib(
        self, objects, output_libname, output_dir=None, debug=0, target_lang=None
    ):
        "Link a bunch of stuff together to create a static library file.\n        The \"bunch of stuff\" consists of the list of object files supplied\n        as 'objects', the extra object files supplied to\n        'add_link_object()' and/or 'set_link_objects()', the libraries\n        supplied to 'add_library()' and/or 'set_libraries()', and the\n        libraries supplied as 'libraries' (if any).\n\n        'output_libname' should be a library name, not a filename; the\n        filename will be inferred from the library name.  'output_dir' is\n        the directory where the library file will be put.\n\n        'debug' is a boolean; if true, debugging information will be\n        included in the library (note that on most platforms, it is the\n        compile step where this matters: the 'debug' flag is included here\n        just for consistency).\n\n        'target_lang' is the target language for which the given objects\n        are being compiled. This allows specific linkage time treatment of\n        certain languages.\n\n        Raises LibError on failure.\n        "
        pass

    SHARED_OBJECT = "shared_object"
    SHARED_LIBRARY = "shared_library"
    EXECUTABLE = "executable"

    def link(
        self,
        target_desc,
        objects,
        output_filename,
        output_dir=None,
        libraries=None,
        library_dirs=None,
        runtime_library_dirs=None,
        export_symbols=None,
        debug=0,
        extra_preargs=None,
        extra_postargs=None,
        build_temp=None,
        target_lang=None,
    ):
        "Link a bunch of stuff together to create an executable or\n        shared library file.\n\n        The \"bunch of stuff\" consists of the list of object files supplied\n        as 'objects'.  'output_filename' should be a filename.  If\n        'output_dir' is supplied, 'output_filename' is relative to it\n        (i.e. 'output_filename' can provide directory components if\n        needed).\n\n        'libraries' is a list of libraries to link against.  These are\n        library names, not filenames, since they're translated into\n        filenames in a platform-specific way (eg. \"foo\" becomes \"libfoo.a\"\n        on Unix and \"foo.lib\" on DOS/Windows).  However, they can include a\n        directory component, which means the linker will look in that\n        specific directory rather than searching all the normal locations.\n\n        'library_dirs', if supplied, should be a list of directories to\n        search for libraries that were specified as bare library names\n        (ie. no directory component).  These are on top of the system\n        default and those supplied to 'add_library_dir()' and/or\n        'set_library_dirs()'.  'runtime_library_dirs' is a list of\n        directories that will be embedded into the shared library and used\n        to search for other shared libraries that *it* depends on at\n        run-time.  (This may only be relevant on Unix.)\n\n        'export_symbols' is a list of symbols that the shared library will\n        export.  (This appears to be relevant only on Windows.)\n\n        'debug' is as for 'compile()' and 'create_static_lib()', with the\n        slight distinction that it actually matters on most platforms (as\n        opposed to 'create_static_lib()', which includes a 'debug' flag\n        mostly for form's sake).\n\n        'extra_preargs' and 'extra_postargs' are as for 'compile()' (except\n        of course that they supply command-line arguments for the\n        particular linker being used).\n\n        'target_lang' is the target language for which the given objects\n        are being compiled. This allows specific linkage time treatment of\n        certain languages.\n\n        Raises LinkError on failure.\n        "
        raise NotImplementedError

    def link_shared_lib(
        self,
        objects,
        output_libname,
        output_dir=None,
        libraries=None,
        library_dirs=None,
        runtime_library_dirs=None,
        export_symbols=None,
        debug=0,
        extra_preargs=None,
        extra_postargs=None,
        build_temp=None,
        target_lang=None,
    ):
        self.link(
            CCompiler.SHARED_LIBRARY,
            objects,
            self.library_filename(output_libname, lib_type="shared"),
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            export_symbols,
            debug,
            extra_preargs,
            extra_postargs,
            build_temp,
            target_lang,
        )

    def link_shared_object(
        self,
        objects,
        output_filename,
        output_dir=None,
        libraries=None,
        library_dirs=None,
        runtime_library_dirs=None,
        export_symbols=None,
        debug=0,
        extra_preargs=None,
        extra_postargs=None,
        build_temp=None,
        target_lang=None,
    ):
        self.link(
            CCompiler.SHARED_OBJECT,
            objects,
            output_filename,
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            export_symbols,
            debug,
            extra_preargs,
            extra_postargs,
            build_temp,
            target_lang,
        )

    def link_executable(
        self,
        objects,
        output_progname,
        output_dir=None,
        libraries=None,
        library_dirs=None,
        runtime_library_dirs=None,
        debug=0,
        extra_preargs=None,
        extra_postargs=None,
        target_lang=None,
    ):
        self.link(
            CCompiler.EXECUTABLE,
            objects,
            self.executable_filename(output_progname),
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            None,
            debug,
            extra_preargs,
            extra_postargs,
            None,
            target_lang,
        )

    def library_dir_option(self, dir):
        "Return the compiler option to add 'dir' to the list of\n        directories searched for libraries.\n        "
        raise NotImplementedError

    def runtime_library_dir_option(self, dir):
        "Return the compiler option to add 'dir' to the list of\n        directories searched for runtime libraries.\n        "
        raise NotImplementedError

    def library_option(self, lib):
        "Return the compiler option to add 'lib' to the list of libraries\n        linked into the shared library or executable.\n        "
        raise NotImplementedError

    def has_function(
        self,
        funcname,
        includes=None,
        include_dirs=None,
        libraries=None,
        library_dirs=None,
    ):
        "Return a boolean indicating whether funcname is supported on\n        the current platform.  The optional arguments can be used to\n        augment the compilation environment.\n        "
        import tempfile

        if includes is None:
            includes = []
        if include_dirs is None:
            include_dirs = []
        if libraries is None:
            libraries = []
        if library_dirs is None:
            library_dirs = []
        (fd, fname) = tempfile.mkstemp(".c", funcname, text=True)
        f = os.fdopen(fd, "w")
        try:
            for incl in includes:
                f.write(('#include "%s"\n' % incl))
            f.write(
                (
                    "int main (int argc, char **argv) {\n    %s();\n    return 0;\n}\n"
                    % funcname
                )
            )
        finally:
            f.close()
        try:
            objects = self.compile([fname], include_dirs=include_dirs)
        except CompileError:
            return False
        try:
            self.link_executable(
                objects, "a.out", libraries=libraries, library_dirs=library_dirs
            )
        except (LinkError, TypeError):
            return False
        return True

    def find_library_file(self, dirs, lib, debug=0):
        "Search the specified list of directories for a static or shared\n        library file 'lib' and return the full path to that file.  If\n        'debug' true, look for a debugging version (if that makes sense on\n        the current platform).  Return None if 'lib' wasn't found in any of\n        the specified directories.\n        "
        raise NotImplementedError

    def object_filenames(self, source_filenames, strip_dir=0, output_dir=""):
        if output_dir is None:
            output_dir = ""
        obj_names = []
        for src_name in source_filenames:
            (base, ext) = os.path.splitext(src_name)
            base = os.path.splitdrive(base)[1]
            base = base[os.path.isabs(base) :]
            if ext not in self.src_extensions:
                raise UnknownFileError(
                    ("unknown file type '%s' (from '%s')" % (ext, src_name))
                )
            if strip_dir:
                base = os.path.basename(base)
            obj_names.append(os.path.join(output_dir, (base + self.obj_extension)))
        return obj_names

    def shared_object_filename(self, basename, strip_dir=0, output_dir=""):
        assert output_dir is not None
        if strip_dir:
            basename = os.path.basename(basename)
        return os.path.join(output_dir, (basename + self.shared_lib_extension))

    def executable_filename(self, basename, strip_dir=0, output_dir=""):
        assert output_dir is not None
        if strip_dir:
            basename = os.path.basename(basename)
        return os.path.join(output_dir, (basename + (self.exe_extension or "")))

    def library_filename(self, libname, lib_type="static", strip_dir=0, output_dir=""):
        assert output_dir is not None
        if lib_type not in ("static", "shared", "dylib", "xcode_stub"):
            raise ValueError(
                '\'lib_type\' must be "static", "shared", "dylib", or "xcode_stub"'
            )
        fmt = getattr(self, (lib_type + "_lib_format"))
        ext = getattr(self, (lib_type + "_lib_extension"))
        (dir, base) = os.path.split(libname)
        filename = fmt % (base, ext)
        if strip_dir:
            dir = ""
        return os.path.join(output_dir, dir, filename)

    def announce(self, msg, level=1):
        log.debug(msg)

    def debug_print(self, msg):
        from distutils.debug import DEBUG

        if DEBUG:
            print(msg)

    def warn(self, msg):
        sys.stderr.write(("warning: %s\n" % msg))

    def execute(self, func, args, msg=None, level=1):
        execute(func, args, msg, self.dry_run)

    def spawn(self, cmd):
        spawn(cmd, dry_run=self.dry_run)

    def move_file(self, src, dst):
        return move_file(src, dst, dry_run=self.dry_run)

    def mkpath(self, name, mode=511):
        mkpath(name, mode, dry_run=self.dry_run)


_default_compilers = (("cygwin.*", "unix"), ("posix", "unix"), ("nt", "msvc"))


def get_default_compiler(osname=None, platform=None):
    "Determine the default compiler to use for the given platform.\n\n       osname should be one of the standard Python OS names (i.e. the\n       ones returned by os.name) and platform the common value\n       returned by sys.platform for the platform in question.\n\n       The default values are os.name and sys.platform in case the\n       parameters are not given.\n    "
    if osname is None:
        osname = os.name
    if platform is None:
        platform = sys.platform
    for (pattern, compiler) in _default_compilers:
        if (re.match(pattern, platform) is not None) or (
            re.match(pattern, osname) is not None
        ):
            return compiler
    return "unix"


compiler_class = {
    "unix": ("unixccompiler", "UnixCCompiler", "standard UNIX-style compiler"),
    "msvc": ("_msvccompiler", "MSVCCompiler", "Microsoft Visual C++"),
    "cygwin": (
        "cygwinccompiler",
        "CygwinCCompiler",
        "Cygwin port of GNU C Compiler for Win32",
    ),
    "mingw32": (
        "cygwinccompiler",
        "Mingw32CCompiler",
        "Mingw32 port of GNU C Compiler for Win32",
    ),
    "bcpp": ("bcppcompiler", "BCPPCompiler", "Borland C++ Compiler"),
}


def show_compilers():
    'Print list of available compilers (used by the "--help-compiler"\n    options to "build", "build_ext", "build_clib").\n    '
    from distutils.fancy_getopt import FancyGetopt

    compilers = []
    for compiler in compiler_class.keys():
        compilers.append((("compiler=" + compiler), None, compiler_class[compiler][2]))
    compilers.sort()
    pretty_printer = FancyGetopt(compilers)
    pretty_printer.print_help("List of available compilers:")


def new_compiler(plat=None, compiler=None, verbose=0, dry_run=0, force=0):
    "Generate an instance of some CCompiler subclass for the supplied\n    platform/compiler combination.  'plat' defaults to 'os.name'\n    (eg. 'posix', 'nt'), and 'compiler' defaults to the default compiler\n    for that platform.  Currently only 'posix' and 'nt' are supported, and\n    the default compilers are \"traditional Unix interface\" (UnixCCompiler\n    class) and Visual C++ (MSVCCompiler class).  Note that it's perfectly\n    possible to ask for a Unix compiler object under Windows, and a\n    Microsoft compiler object under Unix -- if you supply a value for\n    'compiler', 'plat' is ignored.\n    "
    if plat is None:
        plat = os.name
    try:
        if compiler is None:
            compiler = get_default_compiler(plat)
        (module_name, class_name, long_description) = compiler_class[compiler]
    except KeyError:
        msg = "don't know how to compile C/C++ code on platform '%s'" % plat
        if compiler is not None:
            msg = msg + (" with '%s' compiler" % compiler)
        raise DistutilsPlatformError(msg)
    try:
        module_name = "distutils." + module_name
        __import__(module_name)
        module = sys.modules[module_name]
        klass = vars(module)[class_name]
    except ImportError:
        raise DistutilsModuleError(
            ("can't compile C/C++ code: unable to load module '%s'" % module_name)
        )
    except KeyError:
        raise DistutilsModuleError(
            (
                "can't compile C/C++ code: unable to find class '%s' in module '%s'"
                % (class_name, module_name)
            )
        )
    return klass(None, dry_run, force)


def gen_preprocess_options(macros, include_dirs):
    "Generate C pre-processor options (-D, -U, -I) as used by at least\n    two types of compilers: the typical Unix compiler and Visual C++.\n    'macros' is the usual thing, a list of 1- or 2-tuples, where (name,)\n    means undefine (-U) macro 'name', and (name,value) means define (-D)\n    macro 'name' to 'value'.  'include_dirs' is just a list of directory\n    names to be added to the header file search path (-I).  Returns a list\n    of command-line options suitable for either Unix compilers or Visual\n    C++.\n    "
    pp_opts = []
    for macro in macros:
        if not (isinstance(macro, tuple) and (1 <= len(macro) <= 2)):
            raise TypeError(
                (
                    "bad macro definition '%s': each element of 'macros' list must be a 1- or 2-tuple"
                    % macro
                )
            )
        if len(macro) == 1:
            pp_opts.append(("-U%s" % macro[0]))
        elif len(macro) == 2:
            if macro[1] is None:
                pp_opts.append(("-D%s" % macro[0]))
            else:
                pp_opts.append(("-D%s=%s" % macro))
    for dir in include_dirs:
        pp_opts.append(("-I%s" % dir))
    return pp_opts


def gen_lib_options(compiler, library_dirs, runtime_library_dirs, libraries):
    "Generate linker options for searching library directories and\n    linking with specific libraries.  'libraries' and 'library_dirs' are,\n    respectively, lists of library names (not filenames!) and search\n    directories.  Returns a list of command-line options suitable for use\n    with some compiler (depending on the two format strings passed in).\n    "
    lib_opts = []
    for dir in library_dirs:
        lib_opts.append(compiler.library_dir_option(dir))
    for dir in runtime_library_dirs:
        opt = compiler.runtime_library_dir_option(dir)
        if isinstance(opt, list):
            lib_opts = lib_opts + opt
        else:
            lib_opts.append(opt)
    for lib in libraries:
        (lib_dir, lib_name) = os.path.split(lib)
        if lib_dir:
            lib_file = compiler.find_library_file([lib_dir], lib_name)
            if lib_file:
                lib_opts.append(lib_file)
            else:
                compiler.warn(
                    ("no library file corresponding to '%s' found (skipping)" % lib)
                )
        else:
            lib_opts.append(compiler.library_option(lib))
    return lib_opts
