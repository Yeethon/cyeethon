import struct


def load_tzdata(key):
    import importlib.resources

    components = key.split("/")
    package_name = ".".join((["tzdata.zoneinfo"] + components[:(-1)]))
    resource_name = components[(-1)]
    try:
        return importlib.resources.open_binary(package_name, resource_name)
    except (ImportError, FileNotFoundError, UnicodeEncodeError):
        raise ZoneInfoNotFoundError(f"No time zone found with key {key}")


def load_data(fobj):
    header = _TZifHeader.from_file(fobj)
    if header.version == 1:
        time_size = 4
        time_type = "l"
    else:
        time_size = 8
        time_type = "q"
        skip_bytes = (
            (
                (((header.timecnt * 5) + (header.typecnt * 6)) + header.charcnt)
                + (header.leapcnt * 8)
            )
            + header.isstdcnt
        ) + header.isutcnt
        fobj.seek(skip_bytes, 1)
        header = _TZifHeader.from_file(fobj)
    typecnt = header.typecnt
    timecnt = header.timecnt
    charcnt = header.charcnt
    if timecnt:
        trans_list_utc = struct.unpack(
            f">{timecnt}{time_type}", fobj.read((timecnt * time_size))
        )
        trans_idx = struct.unpack(f">{timecnt}B", fobj.read(timecnt))
    else:
        trans_list_utc = ()
        trans_idx = ()
    if typecnt:
        (utcoff, isdst, abbrind) = zip(
            *(struct.unpack(">lbb", fobj.read(6)) for i in range(typecnt))
        )
    else:
        utcoff = ()
        isdst = ()
        abbrind = ()
    abbr_vals = {}
    abbr_chars = fobj.read(charcnt)

    def get_abbr(idx):
        if idx not in abbr_vals:
            span_end = abbr_chars.find(b"\x00", idx)
            abbr_vals[idx] = abbr_chars[idx:span_end].decode()
        return abbr_vals[idx]

    abbr = tuple((get_abbr(idx) for idx in abbrind))
    if header.version >= 2:
        skip_bytes = (header.isutcnt + header.isstdcnt) + (header.leapcnt * 12)
        fobj.seek(skip_bytes, 1)
        c = fobj.read(1)
        assert c == b"\n", c
        tz_bytes = b""
        while (c := fobj.read(1)) != b"\n":
            tz_bytes += c
        tz_str = tz_bytes
    else:
        tz_str = None
    return (trans_idx, trans_list_utc, utcoff, isdst, abbr, tz_str)


class _TZifHeader:
    __slots__ = [
        "version",
        "isutcnt",
        "isstdcnt",
        "leapcnt",
        "timecnt",
        "typecnt",
        "charcnt",
    ]

    def __init__(self, *args):
        for (attr, val) in zip(self.__slots__, args, strict=True):
            setattr(self, attr, val)

    @classmethod
    def from_file(cls, stream):
        if stream.read(4) != b"TZif":
            raise ValueError("Invalid TZif file: magic not found")
        _version = stream.read(1)
        if _version == b"\x00":
            version = 1
        else:
            version = int(_version)
        stream.read(15)
        args = (version,)
        args = args + struct.unpack(">6l", stream.read(24))
        return cls(*args)


class ZoneInfoNotFoundError(KeyError):
    "Exception raised when a ZoneInfo key is not found."
