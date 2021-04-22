" Standard \"encodings\" Package\n\n    Standard Python encoding modules are stored in this package\n    directory.\n\n    Codec modules must have names corresponding to normalized encoding\n    names as defined in the normalize_encoding() function below, e.g.\n    'utf-8' must be implemented by the module 'utf_8.py'.\n\n    Each codec module must export the following interface:\n\n    * getregentry() -> codecs.CodecInfo object\n    The getregentry() API must return a CodecInfo object with encoder, decoder,\n    incrementalencoder, incrementaldecoder, streamwriter and streamreader\n    attributes which adhere to the Python Codec Interface Standard.\n\n    In addition, a module may optionally also define the following\n    APIs which are then used by the package's codec search function:\n\n    * getaliases() -> sequence of encoding name strings to use as aliases\n\n    Alias names returned by getaliases() must be normalized encoding\n    names as defined by normalize_encoding().\n\nWritten by Marc-Andre Lemburg (mal@lemburg.com).\n\n(c) Copyright CNRI, All Rights Reserved. NO WARRANTY.\n\n"
import codecs
import sys
from . import aliases

_cache = {}
_unknown = "--unknown--"
_import_tail = ["*"]
_aliases = aliases.aliases


class CodecRegistryError(LookupError, SystemError):
    pass


def normalize_encoding(encoding):
    " Normalize an encoding name.\n\n        Normalization works as follows: all non-alphanumeric\n        characters except the dot used for Python package names are\n        collapsed and replaced with a single underscore, e.g. '  -;#'\n        becomes '_'. Leading and trailing underscores are removed.\n\n        Note that encoding names should be ASCII only.\n\n    "
    if isinstance(encoding, bytes):
        encoding = str(encoding, "ascii")
    chars = []
    punct = False
    for c in encoding:
        if c.isalnum() or (c == "."):
            if punct and chars:
                chars.append("_")
            if c.isascii():
                chars.append(c)
            punct = False
        else:
            punct = True
    return "".join(chars)


def search_function(encoding):
    entry = _cache.get(encoding, _unknown)
    if entry is not _unknown:
        return entry
    norm_encoding = normalize_encoding(encoding)
    aliased_encoding = _aliases.get(norm_encoding) or _aliases.get(
        norm_encoding.replace(".", "_")
    )
    if aliased_encoding is not None:
        modnames = [aliased_encoding, norm_encoding]
    else:
        modnames = [norm_encoding]
    for modname in modnames:
        if (not modname) or ("." in modname):
            continue
        try:
            mod = __import__(("encodings." + modname), fromlist=_import_tail, level=0)
        except ImportError:
            pass
        else:
            break
    else:
        mod = None
    try:
        getregentry = mod.getregentry
    except AttributeError:
        mod = None
    if mod is None:
        _cache[encoding] = None
        return None
    entry = getregentry()
    if not isinstance(entry, codecs.CodecInfo):
        if not (4 <= len(entry) <= 7):
            raise CodecRegistryError(
                ('module "%s" (%s) failed to register' % (mod.__name__, mod.__file__))
            )
        if (
            (not callable(entry[0]))
            or (not callable(entry[1]))
            or ((entry[2] is not None) and (not callable(entry[2])))
            or ((entry[3] is not None) and (not callable(entry[3])))
            or (
                (len(entry) > 4) and (entry[4] is not None) and (not callable(entry[4]))
            )
            or (
                (len(entry) > 5) and (entry[5] is not None) and (not callable(entry[5]))
            )
        ):
            raise CodecRegistryError(
                (
                    'incompatible codecs in module "%s" (%s)'
                    % (mod.__name__, mod.__file__)
                )
            )
        if (len(entry) < 7) or (entry[6] is None):
            entry += ((None,) * (6 - len(entry))) + (mod.__name__.split(".", 1)[1],)
        entry = codecs.CodecInfo(*entry)
    _cache[encoding] = entry
    try:
        codecaliases = mod.getaliases()
    except AttributeError:
        pass
    else:
        for alias in codecaliases:
            if alias not in _aliases:
                _aliases[alias] = modname
    return entry


codecs.register(search_function)
if sys.platform == "win32":

    def _alias_mbcs(encoding):
        try:
            import _winapi

            ansi_code_page = "cp%s" % _winapi.GetACP()
            if encoding == ansi_code_page:
                import encodings.mbcs

                return encodings.mbcs.getregentry()
        except ImportError:
            pass

    codecs.register(_alias_mbcs)
