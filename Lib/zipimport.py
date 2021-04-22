"zipimport provides support for importing Python modules from Zip archives.\n\nThis module exports three objects:\n- zipimporter: a class; its constructor takes a path to a Zip archive.\n- ZipImportError: exception raised by zipimporter objects. It's a\n  subclass of ImportError, so it can be caught as ImportError, too.\n- _zip_directory_cache: a dict, mapping archive paths to zip directory\n  info dicts, as used in zipimporter._files.\n\nIt is usually not needed to use the zipimport module explicitly; it is\nused by the builtin import mechanism for sys.path items that are paths\nto Zip archives.\n"
import _frozen_importlib_external as _bootstrap_external
from _frozen_importlib_external import _unpack_uint16, _unpack_uint32
import _frozen_importlib as _bootstrap
import _imp
import _io
import marshal
import sys
import time
import _warnings

__all__ = ["ZipImportError", "zipimporter"]
path_sep = _bootstrap_external.path_sep
alt_path_sep = _bootstrap_external.path_separators[1:]


class ZipImportError(ImportError):
    pass


_zip_directory_cache = {}
_module_type = type(sys)
END_CENTRAL_DIR_SIZE = 22
STRING_END_ARCHIVE = b"PK\x05\x06"
MAX_COMMENT_LEN = (1 << 16) - 1


class zipimporter(_bootstrap_external._LoaderBasics):
    "zipimporter(archivepath) -> zipimporter object\n\n    Create a new zipimporter instance. 'archivepath' must be a path to\n    a zipfile, or to a specific path inside a zipfile. For example, it can be\n    '/tmp/myimport.zip', or '/tmp/myimport.zip/mydirectory', if mydirectory is a\n    valid directory inside the archive.\n\n    'ZipImportError is raised if 'archivepath' doesn't point to a valid Zip\n    archive.\n\n    The 'archive' attribute of zipimporter objects contains the name of the\n    zipfile targeted.\n    "

    def __init__(self, path):
        if not isinstance(path, str):
            import os

            path = os.fsdecode(path)
        if not path:
            raise ZipImportError("archive path is empty", path=path)
        if alt_path_sep:
            path = path.replace(alt_path_sep, path_sep)
        prefix = []
        while True:
            try:
                st = _bootstrap_external._path_stat(path)
            except (OSError, ValueError):
                (dirname, basename) = _bootstrap_external._path_split(path)
                if dirname == path:
                    raise ZipImportError("not a Zip file", path=path)
                path = dirname
                prefix.append(basename)
            else:
                if (st.st_mode & 61440) != 32768:
                    raise ZipImportError("not a Zip file", path=path)
                break
        try:
            files = _zip_directory_cache[path]
        except KeyError:
            files = _read_directory(path)
            _zip_directory_cache[path] = files
        self._files = files
        self.archive = path
        self.prefix = _bootstrap_external._path_join(*prefix[::(-1)])
        if self.prefix:
            self.prefix += path_sep

    def find_loader(self, fullname, path=None):
        "find_loader(fullname, path=None) -> self, str or None.\n\n        Search for a module specified by 'fullname'. 'fullname' must be the\n        fully qualified (dotted) module name. It returns the zipimporter\n        instance itself if the module was found, a string containing the\n        full path name if it's possibly a portion of a namespace package,\n        or None otherwise. The optional 'path' argument is ignored -- it's\n        there for compatibility with the importer protocol.\n\n        Deprecated since Python 3.10. Use find_spec() instead.\n        "
        _warnings.warn(
            "zipimporter.find_loader() is deprecated and slated for removal in Python 3.12; use find_spec() instead",
            DeprecationWarning,
        )
        mi = _get_module_info(self, fullname)
        if mi is not None:
            return (self, [])
        modpath = _get_module_path(self, fullname)
        if _is_dir(self, modpath):
            return (None, [f"{self.archive}{path_sep}{modpath}"])
        return (None, [])

    def find_module(self, fullname, path=None):
        "find_module(fullname, path=None) -> self or None.\n\n        Search for a module specified by 'fullname'. 'fullname' must be the\n        fully qualified (dotted) module name. It returns the zipimporter\n        instance itself if the module was found, or None if it wasn't.\n        The optional 'path' argument is ignored -- it's there for compatibility\n        with the importer protocol.\n\n        Deprecated since Python 3.10. Use find_spec() instead.\n        "
        _warnings.warn(
            "zipimporter.find_module() is deprecated and slated for removal in Python 3.12; use find_spec() instead",
            DeprecationWarning,
        )
        return self.find_loader(fullname, path)[0]

    def find_spec(self, fullname, target=None):
        "Create a ModuleSpec for the specified module.\n\n        Returns None if the module cannot be found.\n        "
        module_info = _get_module_info(self, fullname)
        if module_info is not None:
            return _bootstrap.spec_from_loader(fullname, self, is_package=module_info)
        else:
            modpath = _get_module_path(self, fullname)
            if _is_dir(self, modpath):
                path = f"{self.archive}{path_sep}{modpath}"
                spec = _bootstrap.ModuleSpec(
                    name=fullname, loader=None, is_package=True
                )
                spec.submodule_search_locations.append(path)
                return spec
            else:
                return None

    def get_code(self, fullname):
        "get_code(fullname) -> code object.\n\n        Return the code object for the specified module. Raise ZipImportError\n        if the module couldn't be imported.\n        "
        (code, ispackage, modpath) = _get_module_code(self, fullname)
        return code

    def get_data(self, pathname):
        "get_data(pathname) -> string with file data.\n\n        Return the data associated with 'pathname'. Raise OSError if\n        the file wasn't found.\n        "
        if alt_path_sep:
            pathname = pathname.replace(alt_path_sep, path_sep)
        key = pathname
        if pathname.startswith((self.archive + path_sep)):
            key = pathname[len((self.archive + path_sep)) :]
        try:
            toc_entry = self._files[key]
        except KeyError:
            raise OSError(0, "", key)
        return _get_data(self.archive, toc_entry)

    def get_filename(self, fullname):
        "get_filename(fullname) -> filename string.\n\n        Return the filename for the specified module or raise ZipImportError\n        if it couldn't be imported.\n        "
        (code, ispackage, modpath) = _get_module_code(self, fullname)
        return modpath

    def get_source(self, fullname):
        "get_source(fullname) -> source string.\n\n        Return the source code for the specified module. Raise ZipImportError\n        if the module couldn't be found, return None if the archive does\n        contain the module, but has no source for it.\n        "
        mi = _get_module_info(self, fullname)
        if mi is None:
            raise ZipImportError(f"can't find module {fullname!r}", name=fullname)
        path = _get_module_path(self, fullname)
        if mi:
            fullpath = _bootstrap_external._path_join(path, "__init__.py")
        else:
            fullpath = f"{path}.py"
        try:
            toc_entry = self._files[fullpath]
        except KeyError:
            return None
        return _get_data(self.archive, toc_entry).decode()

    def is_package(self, fullname):
        "is_package(fullname) -> bool.\n\n        Return True if the module specified by fullname is a package.\n        Raise ZipImportError if the module couldn't be found.\n        "
        mi = _get_module_info(self, fullname)
        if mi is None:
            raise ZipImportError(f"can't find module {fullname!r}", name=fullname)
        return mi

    def load_module(self, fullname):
        "load_module(fullname) -> module.\n\n        Load the module specified by 'fullname'. 'fullname' must be the\n        fully qualified (dotted) module name. It returns the imported\n        module, or raises ZipImportError if it could not be imported.\n\n        Deprecated since Python 3.10. Use exec_module() instead.\n        "
        msg = "zipimport.zipimporter.load_module() is deprecated and slated for removal in Python 3.12; use exec_module() instead"
        _warnings.warn(msg, DeprecationWarning)
        (code, ispackage, modpath) = _get_module_code(self, fullname)
        mod = sys.modules.get(fullname)
        if (mod is None) or (not isinstance(mod, _module_type)):
            mod = _module_type(fullname)
            sys.modules[fullname] = mod
        mod.__loader__ = self
        try:
            if ispackage:
                path = _get_module_path(self, fullname)
                fullpath = _bootstrap_external._path_join(self.archive, path)
                mod.__path__ = [fullpath]
            if not hasattr(mod, "__builtins__"):
                mod.__builtins__ = __builtins__
            _bootstrap_external._fix_up_module(mod.__dict__, fullname, modpath)
            exec(code, mod.__dict__)
        except:
            del sys.modules[fullname]
            raise
        try:
            mod = sys.modules[fullname]
        except KeyError:
            raise ImportError(f"Loaded module {fullname!r} not found in sys.modules")
        _bootstrap._verbose_message("import {} # loaded from Zip {}", fullname, modpath)
        return mod

    def get_resource_reader(self, fullname):
        "Return the ResourceReader for a package in a zip file.\n\n        If 'fullname' is a package within the zip file, return the\n        'ResourceReader' object for the package.  Otherwise return None.\n        "
        try:
            if not self.is_package(fullname):
                return None
        except ZipImportError:
            return None
        from importlib.readers import ZipReader

        return ZipReader(self, fullname)

    def invalidate_caches(self):
        "Reload the file data of the archive path."
        try:
            self._files = _read_directory(self.archive)
            _zip_directory_cache[self.archive] = self._files
        except ZipImportError:
            _zip_directory_cache.pop(self.archive, None)
            self._files = None

    def __repr__(self):
        return f'<zipimporter object "{self.archive}{path_sep}{self.prefix}">'


_zip_searchorder = (
    ((path_sep + "__init__.pyc"), True, True),
    ((path_sep + "__init__.py"), False, True),
    (".pyc", True, False),
    (".py", False, False),
)


def _get_module_path(self, fullname):
    return self.prefix + fullname.rpartition(".")[2]


def _is_dir(self, path):
    dirpath = path + path_sep
    return dirpath in self._files


def _get_module_info(self, fullname):
    path = _get_module_path(self, fullname)
    for (suffix, isbytecode, ispackage) in _zip_searchorder:
        fullpath = path + suffix
        if fullpath in self._files:
            return ispackage
    return None


def _read_directory(archive):
    try:
        fp = _io.open_code(archive)
    except OSError:
        raise ZipImportError(f"can't open Zip file: {archive!r}", path=archive)
    with fp:
        try:
            fp.seek((-END_CENTRAL_DIR_SIZE), 2)
            header_position = fp.tell()
            buffer = fp.read(END_CENTRAL_DIR_SIZE)
        except OSError:
            raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
        if len(buffer) != END_CENTRAL_DIR_SIZE:
            raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
        if buffer[:4] != STRING_END_ARCHIVE:
            try:
                fp.seek(0, 2)
                file_size = fp.tell()
            except OSError:
                raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
            max_comment_start = max(
                ((file_size - MAX_COMMENT_LEN) - END_CENTRAL_DIR_SIZE), 0
            )
            try:
                fp.seek(max_comment_start)
                data = fp.read()
            except OSError:
                raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
            pos = data.rfind(STRING_END_ARCHIVE)
            if pos < 0:
                raise ZipImportError(f"not a Zip file: {archive!r}", path=archive)
            buffer = data[pos : (pos + END_CENTRAL_DIR_SIZE)]
            if len(buffer) != END_CENTRAL_DIR_SIZE:
                raise ZipImportError(f"corrupt Zip file: {archive!r}", path=archive)
            header_position = (file_size - len(data)) + pos
        header_size = _unpack_uint32(buffer[12:16])
        header_offset = _unpack_uint32(buffer[16:20])
        if header_position < header_size:
            raise ZipImportError(
                f"bad central directory size: {archive!r}", path=archive
            )
        if header_position < header_offset:
            raise ZipImportError(
                f"bad central directory offset: {archive!r}", path=archive
            )
        header_position -= header_size
        arc_offset = header_position - header_offset
        if arc_offset < 0:
            raise ZipImportError(
                f"bad central directory size or offset: {archive!r}", path=archive
            )
        files = {}
        count = 0
        try:
            fp.seek(header_position)
        except OSError:
            raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
        while True:
            buffer = fp.read(46)
            if len(buffer) < 4:
                raise EOFError("EOF read where not expected")
            if buffer[:4] != b"PK\x01\x02":
                break
            if len(buffer) != 46:
                raise EOFError("EOF read where not expected")
            flags = _unpack_uint16(buffer[8:10])
            compress = _unpack_uint16(buffer[10:12])
            time = _unpack_uint16(buffer[12:14])
            date = _unpack_uint16(buffer[14:16])
            crc = _unpack_uint32(buffer[16:20])
            data_size = _unpack_uint32(buffer[20:24])
            file_size = _unpack_uint32(buffer[24:28])
            name_size = _unpack_uint16(buffer[28:30])
            extra_size = _unpack_uint16(buffer[30:32])
            comment_size = _unpack_uint16(buffer[32:34])
            file_offset = _unpack_uint32(buffer[42:46])
            header_size = (name_size + extra_size) + comment_size
            if file_offset > header_offset:
                raise ZipImportError(
                    f"bad local header offset: {archive!r}", path=archive
                )
            file_offset += arc_offset
            try:
                name = fp.read(name_size)
            except OSError:
                raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
            if len(name) != name_size:
                raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
            try:
                if len(fp.read((header_size - name_size))) != (header_size - name_size):
                    raise ZipImportError(
                        f"can't read Zip file: {archive!r}", path=archive
                    )
            except OSError:
                raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
            if flags & 2048:
                name = name.decode()
            else:
                try:
                    name = name.decode("ascii")
                except UnicodeDecodeError:
                    name = name.decode("latin1").translate(cp437_table)
            name = name.replace("/", path_sep)
            path = _bootstrap_external._path_join(archive, name)
            t = (path, compress, data_size, file_size, file_offset, time, date, crc)
            files[name] = t
            count += 1
    _bootstrap._verbose_message("zipimport: found {} names in {!r}", count, archive)
    return files


cp437_table = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7fÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■\xa0"
_importing_zlib = False


def _get_decompress_func():
    global _importing_zlib
    if _importing_zlib:
        _bootstrap._verbose_message("zipimport: zlib UNAVAILABLE")
        raise ZipImportError("can't decompress data; zlib not available")
    _importing_zlib = True
    try:
        from zlib import decompress
    except Exception:
        _bootstrap._verbose_message("zipimport: zlib UNAVAILABLE")
        raise ZipImportError("can't decompress data; zlib not available")
    finally:
        _importing_zlib = False
    _bootstrap._verbose_message("zipimport: zlib available")
    return decompress


def _get_data(archive, toc_entry):
    (datapath, compress, data_size, file_size, file_offset, time, date, crc) = toc_entry
    if data_size < 0:
        raise ZipImportError("negative data size")
    with _io.open_code(archive) as fp:
        try:
            fp.seek(file_offset)
        except OSError:
            raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
        buffer = fp.read(30)
        if len(buffer) != 30:
            raise EOFError("EOF read where not expected")
        if buffer[:4] != b"PK\x03\x04":
            raise ZipImportError(f"bad local file header: {archive!r}", path=archive)
        name_size = _unpack_uint16(buffer[26:28])
        extra_size = _unpack_uint16(buffer[28:30])
        header_size = (30 + name_size) + extra_size
        file_offset += header_size
        try:
            fp.seek(file_offset)
        except OSError:
            raise ZipImportError(f"can't read Zip file: {archive!r}", path=archive)
        raw_data = fp.read(data_size)
        if len(raw_data) != data_size:
            raise OSError("zipimport: can't read data")
    if compress == 0:
        return raw_data
    try:
        decompress = _get_decompress_func()
    except Exception:
        raise ZipImportError("can't decompress data; zlib not available")
    return decompress(raw_data, (-15))


def _eq_mtime(t1, t2):
    return abs((t1 - t2)) <= 1


def _unmarshal_code(self, pathname, fullpath, fullname, data):
    exc_details = {"name": fullname, "path": fullpath}
    flags = _bootstrap_external._classify_pyc(data, fullname, exc_details)
    hash_based = (flags & 1) != 0
    if hash_based:
        check_source = (flags & 2) != 0
        if (_imp.check_hash_based_pycs != "never") and (
            check_source or (_imp.check_hash_based_pycs == "always")
        ):
            source_bytes = _get_pyc_source(self, fullpath)
            if source_bytes is not None:
                source_hash = _imp.source_hash(
                    _bootstrap_external._RAW_MAGIC_NUMBER, source_bytes
                )
                _bootstrap_external._validate_hash_pyc(
                    data, source_hash, fullname, exc_details
                )
    else:
        (source_mtime, source_size) = _get_mtime_and_size_of_source(self, fullpath)
        if source_mtime:
            if (not _eq_mtime(_unpack_uint32(data[8:12]), source_mtime)) or (
                _unpack_uint32(data[12:16]) != source_size
            ):
                _bootstrap._verbose_message(f"bytecode is stale for {fullname!r}")
                return None
    code = marshal.loads(data[16:])
    if not isinstance(code, _code_type):
        raise TypeError(f"compiled module {pathname!r} is not a code object")
    return code


_code_type = type(_unmarshal_code.__code__)


def _normalize_line_endings(source):
    source = source.replace(b"\r\n", b"\n")
    source = source.replace(b"\r", b"\n")
    return source


def _compile_source(pathname, source):
    source = _normalize_line_endings(source)
    return compile(source, pathname, "exec", dont_inherit=True)


def _parse_dostime(d, t):
    return time.mktime(
        (
            ((d >> 9) + 1980),
            ((d >> 5) & 15),
            (d & 31),
            (t >> 11),
            ((t >> 5) & 63),
            ((t & 31) * 2),
            (-1),
            (-1),
            (-1),
        )
    )


def _get_mtime_and_size_of_source(self, path):
    try:
        assert path[(-1):] in ("c", "o")
        path = path[:(-1)]
        toc_entry = self._files[path]
        time = toc_entry[5]
        date = toc_entry[6]
        uncompressed_size = toc_entry[3]
        return (_parse_dostime(date, time), uncompressed_size)
    except (KeyError, IndexError, TypeError):
        return (0, 0)


def _get_pyc_source(self, path):
    assert path[(-1):] in ("c", "o")
    path = path[:(-1)]
    try:
        toc_entry = self._files[path]
    except KeyError:
        return None
    else:
        return _get_data(self.archive, toc_entry)


def _get_module_code(self, fullname):
    path = _get_module_path(self, fullname)
    import_error = None
    for (suffix, isbytecode, ispackage) in _zip_searchorder:
        fullpath = path + suffix
        _bootstrap._verbose_message(
            "trying {}{}{}", self.archive, path_sep, fullpath, verbosity=2
        )
        try:
            toc_entry = self._files[fullpath]
        except KeyError:
            pass
        else:
            modpath = toc_entry[0]
            data = _get_data(self.archive, toc_entry)
            code = None
            if isbytecode:
                try:
                    code = _unmarshal_code(self, modpath, fullpath, fullname, data)
                except ImportError as exc:
                    import_error = exc
            else:
                code = _compile_source(modpath, data)
            if code is None:
                continue
            modpath = toc_entry[0]
            return (code, ispackage, modpath)
    else:
        if import_error:
            msg = f"module load failed: {import_error}"
            raise ZipImportError(msg, name=fullname) from import_error
        else:
            raise ZipImportError(f"can't find module {fullname!r}", name=fullname)
