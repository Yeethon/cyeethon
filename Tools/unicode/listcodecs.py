" List all available codec modules.\n\n(c) Copyright 2005, Marc-Andre Lemburg (mal@lemburg.com).\n\n    Licensed to PSF under a Contributor Agreement.\n\n"
import os, codecs, encodings

_debug = 0


def listcodecs(dir):
    names = []
    for filename in os.listdir(dir):
        if filename[(-3):] != ".py":
            continue
        name = filename[:(-3)]
        try:
            codecs.lookup(name)
        except LookupError:
            continue
        except Exception as reason:
            if _debug:
                print(("* problem importing codec %r: %s" % (name, reason)))
        names.append(name)
    return names


if __name__ == "__main__":
    names = listcodecs(encodings.__path__[0])
    names.sort()
    print("all_codecs = [")
    for name in names:
        print(("    %r," % name))
    print("]")
