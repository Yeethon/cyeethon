import pickle
import sqlite3
from collections import namedtuple

MemoRecord = namedtuple("MemoRecord", "key, task")


class DBPickler(pickle.Pickler):
    def persistent_id(self, obj):
        if isinstance(obj, MemoRecord):
            return ("MemoRecord", obj.key)
        else:
            return None


class DBUnpickler(pickle.Unpickler):
    def __init__(self, file, connection):
        super().__init__(file)
        self.connection = connection

    def persistent_load(self, pid):
        cursor = self.connection.cursor()
        (type_tag, key_id) = pid
        if type_tag == "MemoRecord":
            cursor.execute("SELECT * FROM memos WHERE key=?", (str(key_id),))
            (key, task) = cursor.fetchone()
            return MemoRecord(key, task)
        else:
            raise pickle.UnpicklingError("unsupported persistent object")


def main():
    import io
    import pprint

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE memos(key INTEGER PRIMARY KEY, task TEXT)")
    tasks = ("give food to fish", "prepare group meeting", "fight with a zebra")
    for task in tasks:
        cursor.execute("INSERT INTO memos VALUES(NULL, ?)", (task,))
    cursor.execute("SELECT * FROM memos")
    memos = [MemoRecord(key, task) for (key, task) in cursor]
    file = io.BytesIO()
    DBPickler(file).dump(memos)
    print("Pickled records:")
    pprint.pprint(memos)
    cursor.execute("UPDATE memos SET task='learn italian' WHERE key=1")
    file.seek(0)
    memos = DBUnpickler(file, conn).load()
    print("Unpickled records:")
    pprint.pprint(memos)


if __name__ == "__main__":
    main()
