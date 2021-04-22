'\ngc.get_referrers() can be used to see objects before they are fully built.\n\nNote that this is only an example.  There are many ways to crash Python\nby using gc.get_referrers(), as well as many extension modules (even\nwhen they are using perfectly documented patterns to build objects).\n\nIdentifying and removing all places that expose to the GC a\npartially-built object is a long-term project.  A patch was proposed on\nSF specifically for this example but I consider fixing just this single\nexample a bit pointless (#1517042).\n\nA fix would include a whole-scale code review, possibly with an API\nchange to decouple object creation and GC registration, and according\nfixes to the documentation for extension module writers.  It\'s unlikely\nto happen, though.  So this is currently classified as\n"gc.get_referrers() is dangerous, use only for debugging".\n'
import gc


def g():
    marker = object()
    (yield marker)
    [tup] = [x for x in gc.get_referrers(marker) if (type(x) is tuple)]
    print(tup)
    print(tup[1])


tuple(g())
