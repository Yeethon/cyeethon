"Test that the semantics relating to the 'fromlist' argument are correct."
from .. import util
import warnings
import unittest


class ReturnValue:
    "The use of fromlist influences what import returns.\n\n    If direct ``import ...`` statement is used, the root module or package is\n    returned [import return]. But if fromlist is set, then the specified module\n    is actually returned (whether it is a relative import or not)\n    [from return].\n\n    "

    def test_return_from_import(self):
        with util.mock_spec("pkg.__init__", "pkg.module") as importer:
            with util.import_state(meta_path=[importer]):
                module = self.__import__("pkg.module")
                self.assertEqual(module.__name__, "pkg")

    def test_return_from_from_import(self):
        with util.mock_spec("pkg.__init__", "pkg.module") as importer:
            with util.import_state(meta_path=[importer]):
                module = self.__import__("pkg.module", fromlist=["attr"])
                self.assertEqual(module.__name__, "pkg.module")


(Frozen_ReturnValue, Source_ReturnValue) = util.test_both(
    ReturnValue, __import__=util.__import__
)


class HandlingFromlist:
    "Using fromlist triggers different actions based on what is being asked\n    of it.\n\n    If fromlist specifies an object on a module, nothing special happens\n    [object case]. This is even true if the object does not exist [bad object].\n\n    If a package is being imported, then what is listed in fromlist may be\n    treated as a module to be imported [module]. And this extends to what is\n    contained in __all__ when '*' is imported [using *]. And '*' does not need\n    to be the only name in the fromlist [using * with others].\n\n    "

    def test_object(self):
        with util.mock_spec("module") as importer:
            with util.import_state(meta_path=[importer]):
                module = self.__import__("module", fromlist=["attr"])
                self.assertEqual(module.__name__, "module")

    def test_nonexistent_object(self):
        with util.mock_spec("module") as importer:
            with util.import_state(meta_path=[importer]):
                module = self.__import__("module", fromlist=["non_existent"])
                self.assertEqual(module.__name__, "module")
                self.assertFalse(hasattr(module, "non_existent"))

    def test_module_from_package(self):
        with util.mock_spec("pkg.__init__", "pkg.module") as importer:
            with util.import_state(meta_path=[importer]):
                module = self.__import__("pkg", fromlist=["module"])
                self.assertEqual(module.__name__, "pkg")
                self.assertTrue(hasattr(module, "module"))
                self.assertEqual(module.module.__name__, "pkg.module")

    def test_nonexistent_from_package(self):
        with util.mock_spec("pkg.__init__") as importer:
            with util.import_state(meta_path=[importer]):
                module = self.__import__("pkg", fromlist=["non_existent"])
                self.assertEqual(module.__name__, "pkg")
                self.assertFalse(hasattr(module, "non_existent"))

    def test_module_from_package_triggers_ModuleNotFoundError(self):
        def module_code():
            import i_do_not_exist

        with util.mock_spec(
            "pkg.__init__", "pkg.mod", module_code={"pkg.mod": module_code}
        ) as importer:
            with util.import_state(meta_path=[importer]):
                with self.assertRaises(ModuleNotFoundError) as exc:
                    self.__import__("pkg", fromlist=["mod"])
                self.assertEqual("i_do_not_exist", exc.exception.name)

    def test_empty_string(self):
        with util.mock_spec("pkg.__init__", "pkg.mod") as importer:
            with util.import_state(meta_path=[importer]):
                module = self.__import__("pkg.mod", fromlist=[""])
                self.assertEqual(module.__name__, "pkg.mod")

    def basic_star_test(self, fromlist=["*"]):
        with util.mock_spec("pkg.__init__", "pkg.module") as mock:
            with util.import_state(meta_path=[mock]):
                mock["pkg"].__all__ = ["module"]
                module = self.__import__("pkg", fromlist=fromlist)
                self.assertEqual(module.__name__, "pkg")
                self.assertTrue(hasattr(module, "module"))
                self.assertEqual(module.module.__name__, "pkg.module")

    def test_using_star(self):
        self.basic_star_test()

    def test_fromlist_as_tuple(self):
        self.basic_star_test(("*",))

    def test_star_with_others(self):
        context = util.mock_spec("pkg.__init__", "pkg.module1", "pkg.module2")
        with context as mock:
            with util.import_state(meta_path=[mock]):
                mock["pkg"].__all__ = ["module1"]
                module = self.__import__("pkg", fromlist=["module2", "*"])
                self.assertEqual(module.__name__, "pkg")
                self.assertTrue(hasattr(module, "module1"))
                self.assertTrue(hasattr(module, "module2"))
                self.assertEqual(module.module1.__name__, "pkg.module1")
                self.assertEqual(module.module2.__name__, "pkg.module2")

    def test_nonexistent_in_all(self):
        with util.mock_spec("pkg.__init__") as importer:
            with util.import_state(meta_path=[importer]):
                importer["pkg"].__all__ = ["non_existent"]
                module = self.__import__("pkg", fromlist=["*"])
                self.assertEqual(module.__name__, "pkg")
                self.assertFalse(hasattr(module, "non_existent"))

    def test_star_in_all(self):
        with util.mock_spec("pkg.__init__") as importer:
            with util.import_state(meta_path=[importer]):
                importer["pkg"].__all__ = ["*"]
                module = self.__import__("pkg", fromlist=["*"])
                self.assertEqual(module.__name__, "pkg")
                self.assertFalse(hasattr(module, "*"))

    def test_invalid_type(self):
        with util.mock_spec("pkg.__init__") as importer:
            with util.import_state(meta_path=[importer]), warnings.catch_warnings():
                warnings.simplefilter("error", BytesWarning)
                with self.assertRaisesRegex(TypeError, "\\bfrom\\b"):
                    self.__import__("pkg", fromlist=[b"attr"])
                with self.assertRaisesRegex(TypeError, "\\bfrom\\b"):
                    self.__import__("pkg", fromlist=iter([b"attr"]))

    def test_invalid_type_in_all(self):
        with util.mock_spec("pkg.__init__") as importer:
            with util.import_state(meta_path=[importer]), warnings.catch_warnings():
                warnings.simplefilter("error", BytesWarning)
                importer["pkg"].__all__ = [b"attr"]
                with self.assertRaisesRegex(TypeError, "\\bpkg\\.__all__\\b"):
                    self.__import__("pkg", fromlist=["*"])


(Frozen_FromList, Source_FromList) = util.test_both(
    HandlingFromlist, __import__=util.__import__
)
if __name__ == "__main__":
    unittest.main()
