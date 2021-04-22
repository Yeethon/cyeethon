"Test debugger_r, coverage 30%."
from idlelib import debugger_r
import unittest
from test.support import requires
from tkinter import Tk


class Test(unittest.TestCase):
    def test_init(self):
        self.assertTrue(True)


class IdbAdapterTest(unittest.TestCase):
    def test_dict_item_noattr(self):
        class BinData:
            def __repr__(self):
                return self.length

        debugger_r.dicttable[0] = {"BinData": BinData()}
        idb = debugger_r.IdbAdapter(None)
        self.assertTrue(idb.dict_item(0, "BinData"))
        debugger_r.dicttable.clear()


if __name__ == "__main__":
    unittest.main(verbosity=2)
