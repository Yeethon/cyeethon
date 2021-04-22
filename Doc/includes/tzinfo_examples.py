from datetime import tzinfo, timedelta, datetime

ZERO = timedelta(0)
HOUR = timedelta(hours=1)
SECOND = timedelta(seconds=1)
import time as _time

STDOFFSET = timedelta(seconds=(-_time.timezone))
if _time.daylight:
    DSTOFFSET = timedelta(seconds=(-_time.altzone))
else:
    DSTOFFSET = STDOFFSET
DSTDIFF = DSTOFFSET - STDOFFSET


class LocalTimezone(tzinfo):
    def fromutc(self, dt):
        assert dt.tzinfo is self
        stamp = (dt - datetime(1970, 1, 1, tzinfo=self)) // SECOND
        args = _time.localtime(stamp)[:6]
        dst_diff = DSTDIFF // SECOND
        fold = args == _time.localtime((stamp - dst_diff))
        return datetime(*args, microsecond=dt.microsecond, tzinfo=self, fold=fold)

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.weekday(),
            0,
            0,
        )
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0


Local = LocalTimezone()


def first_sunday_on_or_after(dt):
    days_to_go = 6 - dt.weekday()
    if days_to_go:
        dt += timedelta(days_to_go)
    return dt


DSTSTART_2007 = datetime(1, 3, 8, 2)
DSTEND_2007 = datetime(1, 11, 1, 2)
DSTSTART_1987_2006 = datetime(1, 4, 1, 2)
DSTEND_1987_2006 = datetime(1, 10, 25, 2)
DSTSTART_1967_1986 = datetime(1, 4, 24, 2)
DSTEND_1967_1986 = DSTEND_1987_2006


def us_dst_range(year):
    if 2006 < year:
        (dststart, dstend) = (DSTSTART_2007, DSTEND_2007)
    elif 1986 < year < 2007:
        (dststart, dstend) = (DSTSTART_1987_2006, DSTEND_1987_2006)
    elif 1966 < year < 1987:
        (dststart, dstend) = (DSTSTART_1967_1986, DSTEND_1967_1986)
    else:
        return (datetime(year, 1, 1),) * 2
    start = first_sunday_on_or_after(dststart.replace(year=year))
    end = first_sunday_on_or_after(dstend.replace(year=year))
    return (start, end)


class USTimeZone(tzinfo):
    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if (dt is None) or (dt.tzinfo is None):
            return ZERO
        assert dt.tzinfo is self
        (start, end) = us_dst_range(dt.year)
        dt = dt.replace(tzinfo=None)
        if (start + HOUR) <= dt < (end - HOUR):
            return HOUR
        if (end - HOUR) <= dt < end:
            return ZERO if dt.fold else HOUR
        if start <= dt < (start + HOUR):
            return HOUR if dt.fold else ZERO
        return ZERO

    def fromutc(self, dt):
        assert dt.tzinfo is self
        (start, end) = us_dst_range(dt.year)
        start = start.replace(tzinfo=self)
        end = end.replace(tzinfo=self)
        std_time = dt + self.stdoffset
        dst_time = std_time + HOUR
        if end <= dst_time < (end + HOUR):
            return std_time.replace(fold=1)
        if (std_time < start) or (dst_time >= end):
            return std_time
        if start <= std_time < (end - HOUR):
            return dst_time


Eastern = USTimeZone((-5), "Eastern", "EST", "EDT")
Central = USTimeZone((-6), "Central", "CST", "CDT")
Mountain = USTimeZone((-7), "Mountain", "MST", "MDT")
Pacific = USTimeZone((-8), "Pacific", "PST", "PDT")
