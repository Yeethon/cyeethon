'Manage shelves of pickled objects.\n\nA "shelf" is a persistent, dictionary-like object.  The difference\nwith dbm databases is that the values (not the keys!) in a shelf can\nbe essentially arbitrary Python objects -- anything that the "pickle"\nmodule can handle.  This includes most class instances, recursive data\ntypes, and objects containing lots of shared sub-objects.  The keys\nare ordinary strings.\n\nTo summarize the interface (key is a string, data is an arbitrary\nobject):\n\n        import shelve\n        d = shelve.open(filename) # open, with (g)dbm filename -- no suffix\n\n        d[key] = data   # store data at key (overwrites old data if\n                        # using an existing key)\n        data = d[key]   # retrieve a COPY of the data at key (raise\n                        # KeyError if no such key) -- NOTE that this\n                        # access returns a *copy* of the entry!\n        del d[key]      # delete data stored at key (raises KeyError\n                        # if no such key)\n        flag = key in d # true if the key exists\n        list = d.keys() # a list of all existing keys (slow!)\n\n        d.close()       # close it\n\nDependent on the implementation, closing a persistent dictionary may\nor may not be necessary to flush changes to disk.\n\nNormally, d[key] returns a COPY of the entry.  This needs care when\nmutable entries are mutated: for example, if d[key] is a list,\n        d[key].append(anitem)\ndoes NOT modify the entry d[key] itself, as stored in the persistent\nmapping -- it only modifies the copy, which is then immediately\ndiscarded, so that the append has NO effect whatsoever.  To append an\nitem to d[key] in a way that will affect the persistent mapping, use:\n        data = d[key]\n        data.append(anitem)\n        d[key] = data\n\nTo avoid the problem with mutable entries, you may pass the keyword\nargument writeback=True in the call to shelve.open.  When you use:\n        d = shelve.open(filename, writeback=True)\nthen d keeps a cache of all entries you access, and writes them all back\nto the persistent mapping when you call d.close().  This ensures that\nsuch usage as d[key].append(anitem) works as intended.\n\nHowever, using keyword argument writeback=True may consume vast amount\nof memory for the cache, and it may make d.close() very slow, if you\naccess many of d\'s entries after opening it in this way: d has no way to\ncheck which of the entries you access are mutable and/or which ones you\nactually mutate, so it must cache, and write back at close, all of the\nentries that you access.  You can call d.sync() to write back all the\nentries in the cache, and empty the cache (d.sync() also synchronizes\nthe persistent dictionary on disk, if feasible).\n'
from pickle import DEFAULT_PROTOCOL, Pickler, Unpickler
from io import BytesIO
import collections.abc

__all__ = ["Shelf", "BsdDbShelf", "DbfilenameShelf", "open"]


class _ClosedDict(collections.abc.MutableMapping):
    "Marker for a closed dict.  Access attempts raise a ValueError."

    def closed(self, *args):
        raise ValueError("invalid operation on closed shelf")

    __iter__ = __len__ = __getitem__ = __setitem__ = __delitem__ = keys = closed

    def __repr__(self):
        return "<Closed Dictionary>"


class Shelf(collections.abc.MutableMapping):
    "Base class for shelf implementations.\n\n    This is initialized with a dictionary-like object.\n    See the module's __doc__ string for an overview of the interface.\n    "

    def __init__(self, dict, protocol=None, writeback=False, keyencoding="utf-8"):
        self.dict = dict
        if protocol is None:
            protocol = DEFAULT_PROTOCOL
        self._protocol = protocol
        self.writeback = writeback
        self.cache = {}
        self.keyencoding = keyencoding

    def __iter__(self):
        for k in self.dict.keys():
            (yield k.decode(self.keyencoding))

    def __len__(self):
        return len(self.dict)

    def __contains__(self, key):
        return key.encode(self.keyencoding) in self.dict

    def get(self, key, default=None):
        if key.encode(self.keyencoding) in self.dict:
            return self[key]
        return default

    def __getitem__(self, key):
        try:
            value = self.cache[key]
        except KeyError:
            f = BytesIO(self.dict[key.encode(self.keyencoding)])
            value = Unpickler(f).load()
            if self.writeback:
                self.cache[key] = value
        return value

    def __setitem__(self, key, value):
        if self.writeback:
            self.cache[key] = value
        f = BytesIO()
        p = Pickler(f, self._protocol)
        p.dump(value)
        self.dict[key.encode(self.keyencoding)] = f.getvalue()

    def __delitem__(self, key):
        del self.dict[key.encode(self.keyencoding)]
        try:
            del self.cache[key]
        except KeyError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        if self.dict is None:
            return
        try:
            self.sync()
            try:
                self.dict.close()
            except AttributeError:
                pass
        finally:
            try:
                self.dict = _ClosedDict()
            except:
                self.dict = None

    def __del__(self):
        if not hasattr(self, "writeback"):
            return
        self.close()

    def sync(self):
        if self.writeback and self.cache:
            self.writeback = False
            for (key, entry) in self.cache.items():
                self[key] = entry
            self.writeback = True
            self.cache = {}
        if hasattr(self.dict, "sync"):
            self.dict.sync()


class BsdDbShelf(Shelf):
    'Shelf implementation using the "BSD" db interface.\n\n    This adds methods first(), next(), previous(), last() and\n    set_location() that have no counterpart in [g]dbm databases.\n\n    The actual database must be opened using one of the "bsddb"\n    modules "open" routines (i.e. bsddb.hashopen, bsddb.btopen or\n    bsddb.rnopen) and passed to the constructor.\n\n    See the module\'s __doc__ string for an overview of the interface.\n    '

    def __init__(self, dict, protocol=None, writeback=False, keyencoding="utf-8"):
        Shelf.__init__(self, dict, protocol, writeback, keyencoding)

    def set_location(self, key):
        (key, value) = self.dict.set_location(key)
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())

    def next(self):
        (key, value) = next(self.dict)
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())

    def previous(self):
        (key, value) = self.dict.previous()
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())

    def first(self):
        (key, value) = self.dict.first()
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())

    def last(self):
        (key, value) = self.dict.last()
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())


class DbfilenameShelf(Shelf):
    'Shelf implementation using the "dbm" generic dbm interface.\n\n    This is initialized with the filename for the dbm database.\n    See the module\'s __doc__ string for an overview of the interface.\n    '

    def __init__(self, filename, flag="c", protocol=None, writeback=False):
        import dbm

        Shelf.__init__(self, dbm.open(filename, flag), protocol, writeback)


def open(filename, flag="c", protocol=None, writeback=False):
    "Open a persistent dictionary for reading and writing.\n\n    The filename parameter is the base filename for the underlying\n    database.  As a side-effect, an extension may be added to the\n    filename and more than one file may be created.  The optional flag\n    parameter has the same interpretation as the flag parameter of\n    dbm.open(). The optional protocol parameter specifies the\n    version of the pickle protocol.\n\n    See the module's __doc__ string for an overview of the interface.\n    "
    return DbfilenameShelf(filename, flag, protocol, writeback)
