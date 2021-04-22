'distutils.errors\n\nProvides exceptions used by the Distutils modules.  Note that Distutils\nmodules may raise standard exceptions; in particular, SystemExit is\nusually raised for errors that are obviously the end-user\'s fault\n(eg. bad command-line arguments).\n\nThis module is safe to use in "from ... import *" mode; it only exports\nsymbols whose names start with "Distutils" and end with "Error".'


class DistutilsError(Exception):
    "The root of all Distutils evil."
    pass


class DistutilsModuleError(DistutilsError):
    "Unable to load an expected module, or to find an expected class\n    within some module (in particular, command modules and classes)."
    pass


class DistutilsClassError(DistutilsError):
    'Some command class (or possibly distribution class, if anyone\n    feels a need to subclass Distribution) is found not to be holding\n    up its end of the bargain, ie. implementing some part of the\n    "command "interface.'
    pass


class DistutilsGetoptError(DistutilsError):
    "The option table provided to 'fancy_getopt()' is bogus."
    pass


class DistutilsArgError(DistutilsError):
    "Raised by fancy_getopt in response to getopt.error -- ie. an\n    error in the command line usage."
    pass


class DistutilsFileError(DistutilsError):
    "Any problems in the filesystem: expected file not found, etc.\n    Typically this is for problems that we detect before OSError\n    could be raised."
    pass


class DistutilsOptionError(DistutilsError):
    "Syntactic/semantic errors in command options, such as use of\n    mutually conflicting options, or inconsistent options,\n    badly-spelled values, etc.  No distinction is made between option\n    values originating in the setup script, the command line, config\n    files, or what-have-you -- but if we *know* something originated in\n    the setup script, we'll raise DistutilsSetupError instead."
    pass


class DistutilsSetupError(DistutilsError):
    "For errors that can be definitely blamed on the setup script,\n    such as invalid keyword arguments to 'setup()'."
    pass


class DistutilsPlatformError(DistutilsError):
    "We don't know how to do something on the current platform (but\n    we do know how to do it on some platform) -- eg. trying to compile\n    C files on a platform not supported by a CCompiler subclass."
    pass


class DistutilsExecError(DistutilsError):
    "Any problems executing an external program (such as the C\n    compiler, when compiling C files)."
    pass


class DistutilsInternalError(DistutilsError):
    "Internal inconsistencies or impossibilities (obviously, this\n    should never be seen if the code is working!)."
    pass


class DistutilsTemplateError(DistutilsError):
    "Syntax error in a file list template."


class DistutilsByteCompileError(DistutilsError):
    "Byte compile error."


class CCompilerError(Exception):
    "Some compile/link operation failed."


class PreprocessError(CCompilerError):
    "Failure to preprocess one or more C/C++ files."


class CompileError(CCompilerError):
    "Failure to compile one or more C/C++ source files."


class LibError(CCompilerError):
    "Failure to create a static library from one or more C/C++ object\n    files."


class LinkError(CCompilerError):
    "Failure to link one or more C/C++ object files into an executable\n    or shared library file."


class UnknownFileError(CCompilerError):
    "Attempt to process an unknown file type."
