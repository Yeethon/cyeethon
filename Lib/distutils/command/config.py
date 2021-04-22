'distutils.command.config\n\nImplements the Distutils \'config\' command, a (mostly) empty command class\nthat exists mainly to be sub-classed by specific module distributions and\napplications.  The idea is that while every "config" command is different,\nat least they\'re all named the same, and users always see "config" in the\nlist of standard commands.  Also, this is a good place to put common\nconfigure-like tasks: "try to compile this C code", or "figure out where\nthis header file lives".\n'
import os, re
from distutils.core import Command
from distutils.errors import DistutilsExecError
from distutils.sysconfig import customize_compiler
from distutils import log

LANG_EXT = {"c": ".c", "c++": ".cxx"}


class config(Command):
    description = "prepare to build"
    user_options = [
        ("compiler=", None, "specify the compiler type"),
        ("cc=", None, "specify the compiler executable"),
        ("include-dirs=", "I", "list of directories to search for header files"),
        ("define=", "D", "C preprocessor macros to define"),
        ("undef=", "U", "C preprocessor macros to undefine"),
        ("libraries=", "l", "external C libraries to link with"),
        ("library-dirs=", "L", "directories to search for external C libraries"),
        ("noisy", None, "show every action (compile, link, run, ...) taken"),
        (
            "dump-source",
            None,
            "dump generated source files before attempting to compile them",
        ),
    ]

    def initialize_options(self):
        self.compiler = None
        self.cc = None
        self.include_dirs = None
        self.libraries = None
        self.library_dirs = None
        self.noisy = 1
        self.dump_source = 1
        self.temp_files = []

    def finalize_options(self):
        if self.include_dirs is None:
            self.include_dirs = self.distribution.include_dirs or []
        elif isinstance(self.include_dirs, str):
            self.include_dirs = self.include_dirs.split(os.pathsep)
        if self.libraries is None:
            self.libraries = []
        elif isinstance(self.libraries, str):
            self.libraries = [self.libraries]
        if self.library_dirs is None:
            self.library_dirs = []
        elif isinstance(self.library_dirs, str):
            self.library_dirs = self.library_dirs.split(os.pathsep)

    def run(self):
        pass

    def _check_compiler(self):
        "Check that 'self.compiler' really is a CCompiler object;\n        if not, make it one.\n        "
        from distutils.ccompiler import CCompiler, new_compiler

        if not isinstance(self.compiler, CCompiler):
            self.compiler = new_compiler(
                compiler=self.compiler, dry_run=self.dry_run, force=1
            )
            customize_compiler(self.compiler)
            if self.include_dirs:
                self.compiler.set_include_dirs(self.include_dirs)
            if self.libraries:
                self.compiler.set_libraries(self.libraries)
            if self.library_dirs:
                self.compiler.set_library_dirs(self.library_dirs)

    def _gen_temp_sourcefile(self, body, headers, lang):
        filename = "_configtest" + LANG_EXT[lang]
        with open(filename, "w") as file:
            if headers:
                for header in headers:
                    file.write(("#include <%s>\n" % header))
                file.write("\n")
            file.write(body)
            if body[(-1)] != "\n":
                file.write("\n")
        return filename

    def _preprocess(self, body, headers, include_dirs, lang):
        src = self._gen_temp_sourcefile(body, headers, lang)
        out = "_configtest.i"
        self.temp_files.extend([src, out])
        self.compiler.preprocess(src, out, include_dirs=include_dirs)
        return (src, out)

    def _compile(self, body, headers, include_dirs, lang):
        src = self._gen_temp_sourcefile(body, headers, lang)
        if self.dump_source:
            dump_file(src, ("compiling '%s':" % src))
        (obj,) = self.compiler.object_filenames([src])
        self.temp_files.extend([src, obj])
        self.compiler.compile([src], include_dirs=include_dirs)
        return (src, obj)

    def _link(self, body, headers, include_dirs, libraries, library_dirs, lang):
        (src, obj) = self._compile(body, headers, include_dirs, lang)
        prog = os.path.splitext(os.path.basename(src))[0]
        self.compiler.link_executable(
            [obj],
            prog,
            libraries=libraries,
            library_dirs=library_dirs,
            target_lang=lang,
        )
        if self.compiler.exe_extension is not None:
            prog = prog + self.compiler.exe_extension
        self.temp_files.append(prog)
        return (src, obj, prog)

    def _clean(self, *filenames):
        if not filenames:
            filenames = self.temp_files
            self.temp_files = []
        log.info("removing: %s", " ".join(filenames))
        for filename in filenames:
            try:
                os.remove(filename)
            except OSError:
                pass

    def try_cpp(self, body=None, headers=None, include_dirs=None, lang="c"):
        "Construct a source file from 'body' (a string containing lines\n        of C/C++ code) and 'headers' (a list of header files to include)\n        and run it through the preprocessor.  Return true if the\n        preprocessor succeeded, false if there were any errors.\n        ('body' probably isn't of much use, but what the heck.)\n        "
        from distutils.ccompiler import CompileError

        self._check_compiler()
        ok = True
        try:
            self._preprocess(body, headers, include_dirs, lang)
        except CompileError:
            ok = False
        self._clean()
        return ok

    def search_cpp(self, pattern, body=None, headers=None, include_dirs=None, lang="c"):
        "Construct a source file (just like 'try_cpp()'), run it through\n        the preprocessor, and return true if any line of the output matches\n        'pattern'.  'pattern' should either be a compiled regex object or a\n        string containing a regex.  If both 'body' and 'headers' are None,\n        preprocesses an empty file -- which can be useful to determine the\n        symbols the preprocessor and compiler set by default.\n        "
        self._check_compiler()
        (src, out) = self._preprocess(body, headers, include_dirs, lang)
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        with open(out) as file:
            match = False
            while True:
                line = file.readline()
                if line == "":
                    break
                if pattern.search(line):
                    match = True
                    break
        self._clean()
        return match

    def try_compile(self, body, headers=None, include_dirs=None, lang="c"):
        "Try to compile a source file built from 'body' and 'headers'.\n        Return true on success, false otherwise.\n        "
        from distutils.ccompiler import CompileError

        self._check_compiler()
        try:
            self._compile(body, headers, include_dirs, lang)
            ok = True
        except CompileError:
            ok = False
        log.info(((ok and "success!") or "failure."))
        self._clean()
        return ok

    def try_link(
        self,
        body,
        headers=None,
        include_dirs=None,
        libraries=None,
        library_dirs=None,
        lang="c",
    ):
        "Try to compile and link a source file, built from 'body' and\n        'headers', to executable form.  Return true on success, false\n        otherwise.\n        "
        from distutils.ccompiler import CompileError, LinkError

        self._check_compiler()
        try:
            self._link(body, headers, include_dirs, libraries, library_dirs, lang)
            ok = True
        except (CompileError, LinkError):
            ok = False
        log.info(((ok and "success!") or "failure."))
        self._clean()
        return ok

    def try_run(
        self,
        body,
        headers=None,
        include_dirs=None,
        libraries=None,
        library_dirs=None,
        lang="c",
    ):
        "Try to compile, link to an executable, and run a program\n        built from 'body' and 'headers'.  Return true on success, false\n        otherwise.\n        "
        from distutils.ccompiler import CompileError, LinkError

        self._check_compiler()
        try:
            (src, obj, exe) = self._link(
                body, headers, include_dirs, libraries, library_dirs, lang
            )
            self.spawn([exe])
            ok = True
        except (CompileError, LinkError, DistutilsExecError):
            ok = False
        log.info(((ok and "success!") or "failure."))
        self._clean()
        return ok

    def check_func(
        self,
        func,
        headers=None,
        include_dirs=None,
        libraries=None,
        library_dirs=None,
        decl=0,
        call=0,
    ):
        "Determine if function 'func' is available by constructing a\n        source file that refers to 'func', and compiles and links it.\n        If everything succeeds, returns true; otherwise returns false.\n\n        The constructed source file starts out by including the header\n        files listed in 'headers'.  If 'decl' is true, it then declares\n        'func' (as \"int func()\"); you probably shouldn't supply 'headers'\n        and set 'decl' true in the same call, or you might get errors about\n        a conflicting declarations for 'func'.  Finally, the constructed\n        'main()' function either references 'func' or (if 'call' is true)\n        calls it.  'libraries' and 'library_dirs' are used when\n        linking.\n        "
        self._check_compiler()
        body = []
        if decl:
            body.append(("int %s ();" % func))
        body.append("int main () {")
        if call:
            body.append(("  %s();" % func))
        else:
            body.append(("  %s;" % func))
        body.append("}")
        body = "\n".join(body) + "\n"
        return self.try_link(body, headers, include_dirs, libraries, library_dirs)

    def check_lib(
        self,
        library,
        library_dirs=None,
        headers=None,
        include_dirs=None,
        other_libraries=[],
    ):
        "Determine if 'library' is available to be linked against,\n        without actually checking that any particular symbols are provided\n        by it.  'headers' will be used in constructing the source file to\n        be compiled, but the only effect of this is to check if all the\n        header files listed are available.  Any libraries listed in\n        'other_libraries' will be included in the link, in case 'library'\n        has symbols that depend on other libraries.\n        "
        self._check_compiler()
        return self.try_link(
            "int main (void) { }",
            headers,
            include_dirs,
            ([library] + other_libraries),
            library_dirs,
        )

    def check_header(self, header, include_dirs=None, library_dirs=None, lang="c"):
        "Determine if the system header file named by 'header_file'\n        exists and can be found by the preprocessor; return true if so,\n        false otherwise.\n        "
        return self.try_cpp(
            body="/* No body */", headers=[header], include_dirs=include_dirs
        )


def dump_file(filename, head=None):
    "Dumps a file content into log.info.\n\n    If head is not None, will be dumped before the file content.\n    "
    if head is None:
        log.info("%s", filename)
    else:
        log.info(head)
    file = open(filename)
    try:
        log.info(file.read())
    finally:
        file.close()
