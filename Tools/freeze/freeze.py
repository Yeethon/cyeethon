"Freeze a Python script into a binary.\n\nusage: freeze [options...] script [module]...\n\nOptions:\n-p prefix:    This is the prefix used when you ran ``make install''\n              in the Python build directory.\n              (If you never ran this, freeze won't work.)\n              The default is whatever sys.prefix evaluates to.\n              It can also be the top directory of the Python source\n              tree; then -P must point to the build tree.\n\n-P exec_prefix: Like -p but this is the 'exec_prefix', used to\n                install objects etc.  The default is whatever sys.exec_prefix\n                evaluates to, or the -p argument if given.\n                If -p points to the Python source tree, -P must point\n                to the build tree, if different.\n\n-e extension: A directory containing additional .o files that\n              may be used to resolve modules.  This directory\n              should also have a Setup file describing the .o files.\n              On Windows, the name of a .INI file describing one\n              or more extensions is passed.\n              More than one -e option may be given.\n\n-o dir:       Directory where the output files are created; default '.'.\n\n-m:           Additional arguments are module names instead of filenames.\n\n-a package=dir: Additional directories to be added to the package's\n                __path__.  Used to simulate directories added by the\n                package at runtime (eg, by OpenGL and win32com).\n                More than one -a option may be given for each package.\n\n-l file:      Pass the file to the linker (windows only)\n\n-d:           Debugging mode for the module finder.\n\n-q:           Make the module finder totally quiet.\n\n-h:           Print this help message.\n\n-x module     Exclude the specified module. It will still be imported\n              by the frozen binary if it exists on the host system.\n\n-X module     Like -x, except the module can never be imported by\n              the frozen binary.\n\n-E:           Freeze will fail if any modules can't be found (that\n              were not excluded using -x or -X).\n\n-i filename:  Include a file with additional command line options.  Used\n              to prevent command lines growing beyond the capabilities of\n              the shell/OS.  All arguments specified in filename\n              are read and the -i option replaced with the parsed\n              params (note - quoting args in this file is NOT supported)\n\n-s subsystem: Specify the subsystem (For Windows only.);\n              'console' (default), 'windows', 'service' or 'com_dll'\n\n-w:           Toggle Windows (NT or 95) behavior.\n              (For debugging only -- on a win32 platform, win32 behavior\n              is automatic.)\n\n-r prefix=f:  Replace path prefix.\n              Replace prefix with f in the source path references\n              contained in the resulting binary.\n\nArguments:\n\nscript:       The Python script to be executed by the resulting binary.\n\nmodule ...:   Additional Python modules (referenced by pathname)\n              that will be included in the resulting binary.  These\n              may be .py or .pyc files.  If -m is specified, these are\n              module names that are search in the path instead.\n\nNOTES:\n\nIn order to use freeze successfully, you must have built Python and\ninstalled it (\"make install\").\n\nThe script should not use modules provided only as shared libraries;\nif it does, the resulting binary is not self-contained.\n"
import modulefinder
import getopt
import os
import sys
import sysconfig
import checkextensions
import makeconfig
import makefreeze
import makemakefile
import parsesetup
import bkfile


def main():
    prefix = None
    exec_prefix = None
    extensions = []
    exclude = []
    addn_link = []
    path = sys.path[:]
    modargs = 0
    debug = 1
    odir = ""
    win = sys.platform[:3] == "win"
    replace_paths = []
    error_if_any_missing = 0
    if win:
        exclude = exclude + ["dos", "dospath", "mac", "macfs", "MACFS", "posix"]
    fail_import = exclude[:]
    frozen_c = "frozen.c"
    config_c = "config.c"
    target = "a.out"
    makefile = "Makefile"
    subsystem = "console"
    pos = 1
    while pos < (len(sys.argv) - 1):
        if sys.argv[pos] == "-i":
            try:
                with open(sys.argv[(pos + 1)]) as infp:
                    options = infp.read().split()
            except IOError as why:
                usage(
                    (
                        "File name '%s' specified with the -i option can not be read - %s"
                        % (sys.argv[(pos + 1)], why)
                    )
                )
            sys.argv[pos : (pos + 2)] = options
            pos = (pos + len(options)) - 1
        pos = pos + 1
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "r:a:dEe:hmo:p:P:qs:wX:x:l:")
    except getopt.error as msg:
        usage(("getopt error: " + str(msg)))
    for (o, a) in opts:
        if o == "-h":
            print(__doc__)
            return
        if o == "-d":
            debug = debug + 1
        if o == "-e":
            extensions.append(a)
        if o == "-m":
            modargs = 1
        if o == "-o":
            odir = a
        if o == "-p":
            prefix = a
        if o == "-P":
            exec_prefix = a
        if o == "-q":
            debug = 0
        if o == "-w":
            win = not win
        if o == "-s":
            if not win:
                usage("-s subsystem option only on Windows")
            subsystem = a
        if o == "-x":
            exclude.append(a)
        if o == "-X":
            exclude.append(a)
            fail_import.append(a)
        if o == "-E":
            error_if_any_missing = 1
        if o == "-l":
            addn_link.append(a)
        if o == "-a":
            modulefinder.AddPackagePath(*a.split("=", 2))
        if o == "-r":
            (f, r) = a.split("=", 2)
            replace_paths.append((f, r))
    implicits = []
    for module in ("site", "warnings", "encodings.utf_8", "encodings.latin_1"):
        if module not in exclude:
            implicits.append(module)
    if not exec_prefix:
        if prefix:
            exec_prefix = prefix
        else:
            exec_prefix = sys.exec_prefix
    if not prefix:
        prefix = sys.prefix
    ishome = os.path.exists(os.path.join(prefix, "Python", "ceval.c"))
    version = "%d.%d" % sys.version_info[:2]
    if hasattr(sys, "abiflags"):
        flagged_version = version + sys.abiflags
    else:
        flagged_version = version
    if win:
        extensions_c = "frozen_extensions.c"
    if ishome:
        print("(Using Python source directory)")
        configdir = exec_prefix
        incldir = os.path.join(prefix, "Include")
        config_h_dir = exec_prefix
        config_c_in = os.path.join(prefix, "Modules", "config.c.in")
        frozenmain_c = os.path.join(prefix, "Python", "frozenmain.c")
        makefile_in = os.path.join(exec_prefix, "Makefile")
        if win:
            frozendllmain_c = os.path.join(exec_prefix, "Pc\\frozen_dllmain.c")
    else:
        configdir = sysconfig.get_config_var("LIBPL")
        incldir = os.path.join(prefix, "include", ("python%s" % flagged_version))
        config_h_dir = os.path.join(
            exec_prefix, "include", ("python%s" % flagged_version)
        )
        config_c_in = os.path.join(configdir, "config.c.in")
        frozenmain_c = os.path.join(configdir, "frozenmain.c")
        makefile_in = os.path.join(configdir, "Makefile")
        frozendllmain_c = os.path.join(configdir, "frozen_dllmain.c")
    libdir = sysconfig.get_config_var("LIBDIR")
    supp_sources = []
    defines = []
    includes = [("-I" + incldir), ("-I" + config_h_dir)]
    check_dirs = [prefix, exec_prefix, configdir, incldir]
    if not win:
        check_dirs = check_dirs + extensions
    for dir in check_dirs:
        if not os.path.exists(dir):
            usage(("needed directory %s not found" % dir))
        if not os.path.isdir(dir):
            usage(("%s: not a directory" % dir))
    if win:
        files = supp_sources + extensions
    else:
        files = [config_c_in, makefile_in] + supp_sources
    for file in supp_sources:
        if not os.path.exists(file):
            usage(("needed file %s not found" % file))
        if not os.path.isfile(file):
            usage(("%s: not a plain file" % file))
    if not win:
        for dir in extensions:
            setup = os.path.join(dir, "Setup")
            if not os.path.exists(setup):
                usage(("needed file %s not found" % setup))
            if not os.path.isfile(setup):
                usage(("%s: not a plain file" % setup))
    if not args:
        usage("at least one filename argument required")
    for arg in args:
        if arg == "-m":
            break
        if modargs:
            break
        if not os.path.exists(arg):
            usage(("argument %s not found" % arg))
        if not os.path.isfile(arg):
            usage(("%s: not a plain file" % arg))
    scriptfile = args[0]
    modules = args[1:]
    base = os.path.basename(scriptfile)
    (base, ext) = os.path.splitext(base)
    if base:
        if base != scriptfile:
            target = base
        else:
            target = base + ".bin"
    base_frozen_c = frozen_c
    base_config_c = config_c
    base_target = target
    if odir and (not os.path.isdir(odir)):
        try:
            os.mkdir(odir)
            print("Created output directory", odir)
        except OSError as msg:
            usage(("%s: mkdir failed (%s)" % (odir, str(msg))))
    base = ""
    if odir:
        base = os.path.join(odir, "")
        frozen_c = os.path.join(odir, frozen_c)
        config_c = os.path.join(odir, config_c)
        target = os.path.join(odir, target)
        makefile = os.path.join(odir, makefile)
        if win:
            extensions_c = os.path.join(odir, extensions_c)
    custom_entry_point = None
    python_entry_is_main = 1
    if win:
        import winmakemakefile

        try:
            (
                custom_entry_point,
                python_entry_is_main,
            ) = winmakemakefile.get_custom_entry_point(subsystem)
        except ValueError as why:
            usage(why)
    dir = os.path.dirname(scriptfile)
    path[0] = dir
    mf = modulefinder.ModuleFinder(path, debug, exclude, replace_paths)
    if win and (subsystem == "service"):
        mod = mf.add_module("servicemanager")
        mod.__file__ = "dummy.pyd"
    for mod in implicits:
        mf.import_hook(mod)
    for mod in modules:
        if mod == "-m":
            modargs = 1
            continue
        if modargs:
            if mod[(-2):] == ".*":
                mf.import_hook(mod[:(-2)], None, ["*"])
            else:
                mf.import_hook(mod)
        else:
            mf.load_file(mod)
    mf.modules["_frozen_importlib"] = mf.modules["importlib._bootstrap"]
    mf.modules["_frozen_importlib_external"] = mf.modules[
        "importlib._bootstrap_external"
    ]
    if python_entry_is_main:
        mf.run_script(scriptfile)
    else:
        mf.load_file(scriptfile)
    if debug > 0:
        mf.report()
        print()
    dict = mf.modules
    if error_if_any_missing:
        missing = mf.any_missing()
        if missing:
            sys.exit(("There are some missing modules: %r" % missing))
    files = makefreeze.makefreeze(base, dict, debug, custom_entry_point, fail_import)
    builtins = []
    unknown = []
    mods = sorted(dict.keys())
    for mod in mods:
        if dict[mod].__code__:
            continue
        if not dict[mod].__file__:
            builtins.append(mod)
        else:
            unknown.append(mod)
    addfiles = []
    frozen_extensions = []
    if unknown or ((not win) and builtins):
        if not win:
            (addfiles, addmods) = checkextensions.checkextensions(
                (unknown + builtins), extensions
            )
            for mod in addmods:
                if mod in unknown:
                    unknown.remove(mod)
                    builtins.append(mod)
        else:
            import checkextensions_win32

            frozen_extensions = checkextensions_win32.checkextensions(
                unknown, extensions, prefix
            )
            for mod in frozen_extensions:
                unknown.remove(mod.name)
    if unknown:
        sys.stderr.write(("Warning: unknown modules remain: %s\n" % " ".join(unknown)))
    if win:
        import winmakemakefile, checkextensions_win32

        checkextensions_win32.write_extension_table(extensions_c, frozen_extensions)
        xtras = [
            frozenmain_c,
            os.path.basename(frozen_c),
            frozendllmain_c,
            os.path.basename(extensions_c),
        ] + files
        maindefn = checkextensions_win32.CExtension("__main__", xtras)
        frozen_extensions.append(maindefn)
        with open(makefile, "w") as outfp:
            winmakemakefile.makemakefile(
                outfp, locals(), frozen_extensions, os.path.basename(target)
            )
        return
    builtins.sort()
    with open(config_c_in) as infp, bkfile.open(config_c, "w") as outfp:
        makeconfig.makeconfig(infp, outfp, builtins)
    cflags = ["$(OPT)"]
    cppflags = defines + includes
    libs = [os.path.join(libdir, "$(LDLIBRARY)")]
    somevars = {}
    if os.path.exists(makefile_in):
        makevars = parsesetup.getmakevars(makefile_in)
        for key in makevars:
            somevars[key] = makevars[key]
    somevars["CFLAGS"] = " ".join(cflags)
    somevars["CPPFLAGS"] = " ".join(cppflags)
    files = (
        ((([base_config_c, base_frozen_c] + files) + supp_sources) + addfiles) + libs
    ) + ["$(MODLIBS)", "$(LIBS)", "$(SYSLIBS)"]
    with bkfile.open(makefile, "w") as outfp:
        makemakefile.makemakefile(outfp, somevars, files, base_target)
    if odir:
        print('Now run "make" in', odir, end=" ")
        print("to build the target:", base_target)
    else:
        print('Now run "make" to build the target:', base_target)


def usage(msg):
    sys.stdout = sys.stderr
    print("Error:", msg)
    print(("Use ``%s -h'' for help" % sys.argv[0]))
    sys.exit(2)


main()
