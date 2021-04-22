"Simple class to read IFF chunks.\n\nAn IFF chunk (used in formats such as AIFF, TIFF, RMFF (RealMedia File\nFormat)) has the following structure:\n\n+----------------+\n| ID (4 bytes)   |\n+----------------+\n| size (4 bytes) |\n+----------------+\n| data           |\n| ...            |\n+----------------+\n\nThe ID is a 4-byte string which identifies the type of chunk.\n\nThe size field (a 32-bit value, encoded using big-endian byte order)\ngives the size of the whole chunk, including the 8-byte header.\n\nUsually an IFF-type file consists of one or more chunks.  The proposed\nusage of the Chunk class defined here is to instantiate an instance at\nthe start of each chunk and read from the instance until it reaches\nthe end, after which a new instance can be instantiated.  At the end\nof the file, creating a new instance will fail with an EOFError\nexception.\n\nUsage:\nwhile True:\n    try:\n        chunk = Chunk(file)\n    except EOFError:\n        break\n    chunktype = chunk.getname()\n    while True:\n        data = chunk.read(nbytes)\n        if not data:\n            pass\n        # do something with data\n\nThe interface is file-like.  The implemented methods are:\nread, close, seek, tell, isatty.\nExtra methods are: skip() (called by close, skips to the end of the chunk),\ngetname() (returns the name (ID) of the chunk)\n\nThe __init__ method has one required argument, a file-like object\n(including a chunk instance), and one optional argument, a flag which\nspecifies whether or not chunks are aligned on 2-byte boundaries.  The\ndefault is 1, i.e. aligned.\n"


class Chunk:
    def __init__(self, file, align=True, bigendian=True, inclheader=False):
        import struct

        self.closed = False
        self.align = align
        if bigendian:
            strflag = ">"
        else:
            strflag = "<"
        self.file = file
        self.chunkname = file.read(4)
        if len(self.chunkname) < 4:
            raise EOFError
        try:
            self.chunksize = struct.unpack_from((strflag + "L"), file.read(4))[0]
        except struct.error:
            raise EOFError from None
        if inclheader:
            self.chunksize = self.chunksize - 8
        self.size_read = 0
        try:
            self.offset = self.file.tell()
        except (AttributeError, OSError):
            self.seekable = False
        else:
            self.seekable = True

    def getname(self):
        "Return the name (ID) of the current chunk."
        return self.chunkname

    def getsize(self):
        "Return the size of the current chunk."
        return self.chunksize

    def close(self):
        if not self.closed:
            try:
                self.skip()
            finally:
                self.closed = True

    def isatty(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return False

    def seek(self, pos, whence=0):
        "Seek to specified position into the chunk.\n        Default position is 0 (start of chunk).\n        If the file is not seekable, this will result in an error.\n        "
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if not self.seekable:
            raise OSError("cannot seek")
        if whence == 1:
            pos = pos + self.size_read
        elif whence == 2:
            pos = pos + self.chunksize
        if (pos < 0) or (pos > self.chunksize):
            raise RuntimeError
        self.file.seek((self.offset + pos), 0)
        self.size_read = pos

    def tell(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return self.size_read

    def read(self, size=(-1)):
        "Read at most size bytes from the chunk.\n        If size is omitted or negative, read until the end\n        of the chunk.\n        "
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if self.size_read >= self.chunksize:
            return b""
        if size < 0:
            size = self.chunksize - self.size_read
        if size > (self.chunksize - self.size_read):
            size = self.chunksize - self.size_read
        data = self.file.read(size)
        self.size_read = self.size_read + len(data)
        if (self.size_read == self.chunksize) and self.align and (self.chunksize & 1):
            dummy = self.file.read(1)
            self.size_read = self.size_read + len(dummy)
        return data

    def skip(self):
        "Skip the rest of the chunk.\n        If you are not interested in the contents of the chunk,\n        this method should be called so that the file points to\n        the start of the next chunk.\n        "
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if self.seekable:
            try:
                n = self.chunksize - self.size_read
                if self.align and (self.chunksize & 1):
                    n = n + 1
                self.file.seek(n, 1)
                self.size_read = self.size_read + n
                return
            except OSError:
                pass
        while self.size_read < self.chunksize:
            n = min(8192, (self.chunksize - self.size_read))
            dummy = self.read(n)
            if not dummy:
                raise EOFError
