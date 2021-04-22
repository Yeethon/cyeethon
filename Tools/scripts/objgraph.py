import sys
import os
import getopt
import re

definitions = "TRGDSBAEC"
externals = "UV"
ignore = "Nntrgdsbavuc"
matcher = re.compile("(.*):\t?........ (.) (.*)$")


def store(dict, key, item):
    if key in dict:
        dict[key].append(item)
    else:
        dict[key] = [item]


def flat(list):
    s = ""
    for item in list:
        s = (s + " ") + item
    return s[1:]


file2undef = {}
def2file = {}
file2def = {}
undef2file = {}


def readinput(fp):
    while 1:
        s = fp.readline()
        if not s:
            break
        if matcher.search(s) < 0:
            s
            continue
        ((ra, rb), (r1a, r1b), (r2a, r2b), (r3a, r3b)) = matcher.regs[:4]
        (fn, name, type) = (s[r1a:r1b], s[r3a:r3b], s[r2a:r2b])
        if type in definitions:
            store(def2file, name, fn)
            store(file2def, fn, name)
        elif type in externals:
            store(file2undef, fn, name)
            store(undef2file, name, fn)
        elif not (type in ignore):
            print(((((fn + ":") + name) + ": unknown type ") + type))


def printcallee():
    flist = sorted(file2undef.keys())
    for filename in flist:
        print((filename + ":"))
        elist = file2undef[filename]
        elist.sort()
        for ext in elist:
            if len(ext) >= 8:
                tabs = "\t"
            else:
                tabs = "\t\t"
            if ext not in def2file:
                print(((("\t" + ext) + tabs) + " *undefined"))
            else:
                print(((("\t" + ext) + tabs) + flat(def2file[ext])))


def printcaller():
    files = sorted(file2def.keys())
    for filename in files:
        callers = []
        for label in file2def[filename]:
            if label in undef2file:
                callers = callers + undef2file[label]
        if callers:
            callers.sort()
            print((filename + ":"))
            lastfn = ""
            for fn in callers:
                if fn != lastfn:
                    print(("\t" + fn))
                lastfn = fn
        else:
            print((filename + ": unused"))


def printundef():
    undefs = {}
    for filename in list(file2undef.keys()):
        for ext in file2undef[filename]:
            if ext not in def2file:
                store(undefs, ext, filename)
    elist = sorted(undefs.keys())
    for ext in elist:
        print((ext + ":"))
        flist = sorted(undefs[ext])
        for filename in flist:
            print(("\t" + filename))


def warndups():
    savestdout = sys.stdout
    sys.stdout = sys.stderr
    names = sorted(def2file.keys())
    for name in names:
        if len(def2file[name]) > 1:
            print("warning:", name, "multiply defined:", end=" ")
            print(flat(def2file[name]))
    sys.stdout = savestdout


def main():
    try:
        (optlist, args) = getopt.getopt(sys.argv[1:], "cdu")
    except getopt.error:
        sys.stdout = sys.stderr
        print("Usage:", os.path.basename(sys.argv[0]), end=" ")
        print("[-cdu] [file] ...")
        print("-c: print callers per objectfile")
        print("-d: print callees per objectfile")
        print("-u: print usage of undefined symbols")
        print("If none of -cdu is specified, all are assumed.")
        print('Use "nm -o" to generate the input')
        print("e.g.: nm -o /lib/libc.a | objgraph")
        return 1
    optu = optc = optd = 0
    for (opt, void) in optlist:
        if opt == "-u":
            optu = 1
        elif opt == "-c":
            optc = 1
        elif opt == "-d":
            optd = 1
    if optu == optc == optd == 0:
        optu = optc = optd = 1
    if not args:
        args = ["-"]
    for filename in args:
        if filename == "-":
            readinput(sys.stdin)
        else:
            with open(filename) as f:
                readinput(f)
    warndups()
    more = ((optu + optc) + optd) > 1
    if optd:
        if more:
            print("---------------All callees------------------")
        printcallee()
    if optu:
        if more:
            print("---------------Undefined callees------------")
        printundef()
    if optc:
        if more:
            print("---------------All Callers------------------")
        printcaller()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
