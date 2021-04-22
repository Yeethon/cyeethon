import abc


class FinderTests(metaclass=abc.ABCMeta):
    "Basic tests for a finder to pass."

    @abc.abstractmethod
    def test_module(self):
        pass

    @abc.abstractmethod
    def test_package(self):
        pass

    @abc.abstractmethod
    def test_module_in_package(self):
        pass

    @abc.abstractmethod
    def test_package_in_package(self):
        pass

    @abc.abstractmethod
    def test_package_over_module(self):
        pass

    @abc.abstractmethod
    def test_failure(self):
        pass


class LoaderTests(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def test_module(self):
        "A module should load without issue.\n\n        After the loader returns the module should be in sys.modules.\n\n        Attributes to verify:\n\n            * __file__\n            * __loader__\n            * __name__\n            * No __path__\n\n        "
        pass

    @abc.abstractmethod
    def test_package(self):
        "Loading a package should work.\n\n        After the loader returns the module should be in sys.modules.\n\n        Attributes to verify:\n\n            * __name__\n            * __file__\n            * __package__\n            * __path__\n            * __loader__\n\n        "
        pass

    @abc.abstractmethod
    def test_lacking_parent(self):
        "A loader should not be dependent on it's parent package being\n        imported."
        pass

    @abc.abstractmethod
    def test_state_after_failure(self):
        "If a module is already in sys.modules and a reload fails\n        (e.g. a SyntaxError), the module should be in the state it was before\n        the reload began."
        pass

    @abc.abstractmethod
    def test_unloadable(self):
        "Test ImportError is raised when the loader is asked to load a module\n        it can't."
        pass
