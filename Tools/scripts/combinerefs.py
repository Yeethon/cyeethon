'\ncombinerefs path\n\nA helper for analyzing PYTHONDUMPREFS output.\n\nWhen the PYTHONDUMPREFS envar is set in a debug build, at Python shutdown\ntime Py_FinalizeEx() prints the list of all live objects twice:  first it\nprints the repr() of each object while the interpreter is still fully intact.\nAfter cleaning up everything it can, it prints all remaining live objects\nagain, but the second time just prints their addresses, refcounts, and type\nnames (because the interpreter has been torn down, calling repr methods at\nthis point can get into infinite loops or blow up).\n\nSave all this output into a file, then run this script passing the path to\nthat file.  The script finds both output chunks, combines them, then prints\na line of output for each object still alive at the end:\n\n    address refcnt typename repr\n\naddress is the address of the object, in whatever format the platform C\nproduces for a %p format code.\n\nrefcnt is of the form\n\n    "[" ref "]"\n\nwhen the object\'s refcount is the same in both PYTHONDUMPREFS output blocks,\nor\n\n    "[" ref_before "->" ref_after "]"\n\nif the refcount changed.\n\ntypename is Py_TYPE(object)->tp_name, extracted from the second PYTHONDUMPREFS\noutput block.\n\nrepr is repr(object), extracted from the first PYTHONDUMPREFS output block.\nCAUTION:  If object is a container type, it may not actually contain all the\nobjects shown in the repr:  the repr was captured from the first output block,\nand some of the containees may have been released since then.  For example,\nit\'s common for the line showing the dict of interned strings to display\nstrings that no longer exist at the end of Py_FinalizeEx; this can be recognized\n(albeit painfully) because such containees don\'t have a line of their own.\n\nThe objects are listed in allocation order, with most-recently allocated\nprinted first, and the first object allocated printed last.\n\n\nSimple examples:\n\n    00857060 [14] str \'__len__\'\n\nThe str object \'__len__\' is alive at shutdown time, and both PYTHONDUMPREFS\noutput blocks said there were 14 references to it.  This is probably due to\nC modules that intern the string "__len__" and keep a reference to it in a\nfile static.\n\n    00857038 [46->5] tuple ()\n\n46-5 = 41 references to the empty tuple were removed by the cleanup actions\nbetween the times PYTHONDUMPREFS produced output.\n\n    00858028 [1025->1456] str \'<dummy key>\'\n\nThe string \'<dummy key>\', which is used in dictobject.c to overwrite a real\nkey that gets deleted, grew several hundred references during cleanup.  It\nsuggests that stuff did get removed from dicts by cleanup, but that the dicts\nthemselves are staying alive for some reason. '
import re
import sys


def read(fileiter, pat, whilematch):
    for line in fileiter:
        if bool(pat.match(line)) == whilematch:
            (yield line)
        else:
            break


def combinefile(f):
    fi = iter(f)
    for line in read(fi, re.compile("^Remaining objects:$"), False):
        pass
    crack = re.compile("([a-zA-Z\\d]+) \\[(\\d+)\\] (.*)")
    addr2rc = {}
    addr2guts = {}
    before = 0
    for line in read(fi, re.compile("^Remaining object addresses:$"), False):
        m = crack.match(line)
        if m:
            (addr, addr2rc[addr], addr2guts[addr]) = m.groups()
            before += 1
        else:
            print("??? skipped:", line)
    after = 0
    for line in read(fi, crack, True):
        after += 1
        m = crack.match(line)
        assert m
        (addr, rc, guts) = m.groups()
        if addr not in addr2rc:
            print("??? new object created while tearing down:", line.rstrip())
            continue
        print(addr, end=" ")
        if rc == addr2rc[addr]:
            print(("[%s]" % rc), end=" ")
        else:
            print(("[%s->%s]" % (addr2rc[addr], rc)), end=" ")
        print(guts, addr2guts[addr])
    print(("%d objects before, %d after" % (before, after)))


def combine(fname):
    with open(fname) as f:
        combinefile(f)


if __name__ == "__main__":
    combine(sys.argv[1])
