"Mock classes that imitate idlelib modules or classes.\n\nAttributes and methods will be added as needed for tests.\n"
from idlelib.idle_test.mock_tk import Text


class Func:
    "Record call, capture args, return/raise result set by test.\n\n    When mock function is called, set or use attributes:\n    self.called - increment call number even if no args, kwds passed.\n    self.args - capture positional arguments.\n    self.kwds - capture keyword arguments.\n    self.result - return or raise value set in __init__.\n    self.return_self - return self instead, to mock query class return.\n\n    Most common use will probably be to mock instance methods.\n    Given class instance, can set and delete as instance attribute.\n    Mock_tk.Var and Mbox_func are special variants of this.\n    "

    def __init__(self, result=None, return_self=False):
        self.called = 0
        self.result = result
        self.return_self = return_self
        self.args = None
        self.kwds = None

    def __call__(self, *args, **kwds):
        self.called += 1
        self.args = args
        self.kwds = kwds
        if isinstance(self.result, BaseException):
            raise self.result
        elif self.return_self:
            return self
        else:
            return self.result


class Editor:
    "Minimally imitate editor.EditorWindow class.\n    "

    def __init__(self, flist=None, filename=None, key=None, root=None, text=None):
        self.text = text or Text()
        self.undo = UndoDelegator()

    def get_selection_indices(self):
        first = self.text.index("1.0")
        last = self.text.index("end")
        return (first, last)


class UndoDelegator:
    "Minimally imitate undo.UndoDelegator class.\n    "

    def undo_block_start(*args):
        pass

    def undo_block_stop(*args):
        pass
