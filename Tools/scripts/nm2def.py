"nm2def.py\n\nHelpers to extract symbols from Unix libs and auto-generate\nWindows definition files from them. Depends on nm(1). Tested\non Linux and Solaris only (-p option to nm is for Solaris only).\n\nBy Marc-Andre Lemburg, Aug 1998.\n\nAdditional notes: the output of nm is supposed to look like this:\n\nacceler.o:\n000001fd T PyGrammar_AddAccelerators\n         U PyGrammar_FindDFA\n00000237 T PyGrammar_RemoveAccelerators\n         U _IO_stderr_\n         U exit\n         U fprintf\n         U free\n         U malloc\n         U printf\n\ngrammar1.o:\n00000000 T PyGrammar_FindDFA\n00000034 T PyGrammar_LabelRepr\n         U _PyParser_TokenNames\n         U abort\n         U printf\n         U sprintf\n\n...\n\nEven if this isn't the default output of your nm, there is generally an\noption to produce this format (since it is the original v7 Unix format).\n\n"
import os, sys

PYTHONLIB = "libpython%d.%d.a" % sys.version_info[:2]
PC_PYTHONLIB = "Python%d%d.dll" % sys.version_info[:2]
NM = "nm -p -g %s"


def symbols(lib=PYTHONLIB, types=("T", "C", "D")):
    with os.popen((NM % lib)) as pipe:
        lines = pipe.readlines()
    lines = [s.strip() for s in lines]
    symbols = {}
    for line in lines:
        if (len(line) == 0) or (":" in line):
            continue
        items = line.split()
        if len(items) != 3:
            continue
        (address, type, name) = items
        if type not in types:
            continue
        symbols[name] = (address, type)
    return symbols


def export_list(symbols):
    data = []
    code = []
    for (name, (addr, type)) in symbols.items():
        if type in ("C", "D"):
            data.append(("\t" + name))
        else:
            code.append(("\t" + name))
    data.sort()
    data.append("")
    code.sort()
    return (" DATA\n".join(data) + "\n") + "\n".join(code)


DEF_TEMPLATE = "EXPORTS\n%s\n"
SPECIALS = ()


def filter_Python(symbols, specials=SPECIALS):
    for name in list(symbols.keys()):
        if (name[:2] == "Py") or (name[:3] == "_Py"):
            pass
        elif name not in specials:
            del symbols[name]


def main():
    s = symbols(PYTHONLIB)
    filter_Python(s)
    exports = export_list(s)
    f = sys.stdout
    f.write((DEF_TEMPLATE % exports))


if __name__ == "__main__":
    main()
