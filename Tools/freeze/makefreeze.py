import marshal
import bkfile

header = (
    '\n#include "Python.h"\n\nstatic struct _frozen _PyImport_FrozenModules[] = {\n'
)
trailer = "    {0, 0, 0} /* sentinel */\n};\n"
default_entry_point = (
    (
        "\nint\nmain(int argc, char **argv)\n{\n        extern int Py_FrozenMain(int, char **);\n"
        + (((not __debug__) and "\n        Py_OptimizeFlag++;\n") or "")
    )
    + "\n        PyImport_FrozenModules = _PyImport_FrozenModules;\n        return Py_FrozenMain(argc, argv);\n}\n\n"
)


def makefreeze(base, dict, debug=0, entry_point=None, fail_import=()):
    if entry_point is None:
        entry_point = default_entry_point
    done = []
    files = []
    mods = sorted(dict.keys())
    for mod in mods:
        m = dict[mod]
        mangled = "__".join(mod.split("."))
        if m.__code__:
            file = ("M_" + mangled) + ".c"
            with bkfile.open((base + file), "w") as outfp:
                files.append(file)
                if debug:
                    print("freezing", mod, "...")
                str = marshal.dumps(m.__code__)
                size = len(str)
                if m.__path__:
                    size = -size
                done.append((mod, mangled, size))
                writecode(outfp, mangled, str)
    if debug:
        print("generating table of frozen modules")
    with bkfile.open((base + "frozen.c"), "w") as outfp:
        for (mod, mangled, size) in done:
            outfp.write(("extern unsigned char M_%s[];\n" % mangled))
        outfp.write(header)
        for (mod, mangled, size) in done:
            outfp.write(('\t{"%s", M_%s, %d},\n' % (mod, mangled, size)))
        outfp.write("\n")
        for mod in fail_import:
            outfp.write(('\t{"%s", NULL, 0},\n' % (mod,)))
        outfp.write(trailer)
        outfp.write(entry_point)
    return files


def writecode(outfp, mod, str):
    outfp.write(("unsigned char M_%s[] = {" % mod))
    for i in range(0, len(str), 16):
        outfp.write("\n\t")
        for c in bytes(str[i : (i + 16)]):
            outfp.write(("%d," % c))
    outfp.write("\n};\n")
