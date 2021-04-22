import _winapi
import math
import msvcrt
import os
import subprocess
import uuid
import winreg
from test.support import os_helper
from test.libregrtest.utils import print_warning

BUFSIZE = 8192
SAMPLING_INTERVAL = 1
LOAD_FACTOR_1 = 1 / math.exp((SAMPLING_INTERVAL / 60))
NVALUE = 5
COUNTER_REGISTRY_KEY = (
    "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Perflib\\CurrentLanguage"
)


class WindowsLoadTracker:
    "\n    This class asynchronously interacts with the `typeperf` command to read\n    the system load on Windows. Multiprocessing and threads can't be used\n    here because they interfere with the test suite's cases for those\n    modules.\n    "

    def __init__(self):
        self._values = []
        self._load = None
        self._buffer = ""
        self._popen = None
        self.start()

    def start(self):
        pipe_name = "\\\\.\\pipe\\typeperf_output_" + str(uuid.uuid4())
        open_mode = _winapi.PIPE_ACCESS_INBOUND
        open_mode |= _winapi.FILE_FLAG_FIRST_PIPE_INSTANCE
        open_mode |= _winapi.FILE_FLAG_OVERLAPPED
        self.pipe = _winapi.CreateNamedPipe(
            pipe_name,
            open_mode,
            _winapi.PIPE_WAIT,
            1,
            BUFSIZE,
            BUFSIZE,
            _winapi.NMPWAIT_WAIT_FOREVER,
            _winapi.NULL,
        )
        pipe_write_end = _winapi.CreateFile(
            pipe_name,
            _winapi.GENERIC_WRITE,
            0,
            _winapi.NULL,
            _winapi.OPEN_EXISTING,
            0,
            _winapi.NULL,
        )
        command_stdout = msvcrt.open_osfhandle(pipe_write_end, 0)
        overlap = _winapi.ConnectNamedPipe(self.pipe, overlapped=True)
        overlap.GetOverlappedResult(True)
        counter_name = self._get_counter_name()
        command = ["typeperf", counter_name, "-si", str(SAMPLING_INTERVAL)]
        self._popen = subprocess.Popen(
            " ".join(command), stdout=command_stdout, cwd=os_helper.SAVEDCWD
        )
        os.close(command_stdout)

    def _get_counter_name(self):
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, COUNTER_REGISTRY_KEY) as perfkey:
            counters = winreg.QueryValueEx(perfkey, "Counter")[0]
        counters = iter(counters)
        counters_dict = dict(zip(counters, counters))
        system = counters_dict["2"]
        process_queue_length = counters_dict["44"]
        return f'"\{system}\{process_queue_length}"'

    def close(self, kill=True):
        if self._popen is None:
            return
        self._load = None
        if kill:
            self._popen.kill()
        self._popen.wait()
        self._popen = None

    def __del__(self):
        self.close()

    def _parse_line(self, line):
        tokens = line.split(",")
        if len(tokens) != 2:
            raise ValueError
        value = tokens[1]
        if (not value.startswith('"')) or (not value.endswith('"')):
            raise ValueError
        value = value[1:(-1)]
        return float(value)

    def _read_lines(self):
        (overlapped, _) = _winapi.ReadFile(self.pipe, BUFSIZE, True)
        (bytes_read, res) = overlapped.GetOverlappedResult(False)
        if res != 0:
            return ()
        output = overlapped.getbuffer()
        output = output.decode("oem", "replace")
        output = self._buffer + output
        lines = output.splitlines(True)
        try:
            self._parse_line(lines[(-1)])
        except ValueError:
            self._buffer = lines.pop((-1))
        else:
            self._buffer = ""
        return lines

    def getloadavg(self):
        if self._popen is None:
            return None
        returncode = self._popen.poll()
        if returncode is not None:
            self.close(kill=False)
            return None
        try:
            lines = self._read_lines()
        except BrokenPipeError:
            self.close()
            return None
        for line in lines:
            line = line.rstrip()
            if "PDH-CSV" in line:
                continue
            if not line:
                continue
            try:
                processor_queue_length = self._parse_line(line)
            except ValueError:
                print_warning(("Failed to parse typeperf output: %a" % line))
                continue
            if self._load is not None:
                self._load = (self._load * LOAD_FACTOR_1) + (
                    processor_queue_length * (1.0 - LOAD_FACTOR_1)
                )
            elif len(self._values) < NVALUE:
                self._values.append(processor_queue_length)
            else:
                self._load = sum(self._values) / len(self._values)
        return self._load
