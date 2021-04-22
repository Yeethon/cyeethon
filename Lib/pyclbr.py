"Parse a Python module and describe its classes and functions.\n\nParse enough of a Python file to recognize imports and class and\nfunction definitions, and to find out the superclasses of a class.\n\nThe interface consists of a single function:\n    readmodule_ex(module, path=None)\nwhere module is the name of a Python module, and path is an optional\nlist of directories where the module is to be searched.  If present,\npath is prepended to the system search path sys.path.  The return value\nis a dictionary.  The keys of the dictionary are the names of the\nclasses and functions defined in the module (including classes that are\ndefined via the from XXX import YYY construct).  The values are\ninstances of classes Class and Function.  One special key/value pair is\npresent for packages: the key '__path__' has a list as its value which\ncontains the package search path.\n\nClasses and Functions have a common superclass: _Object.  Every instance\nhas the following attributes:\n    module  -- name of the module;\n    name    -- name of the object;\n    file    -- file in which the object is defined;\n    lineno  -- line in the file where the object's definition starts;\n    end_lineno -- line in the file where the object's definition ends;\n    parent  -- parent of this object, if any;\n    children -- nested objects contained in this object.\nThe 'children' attribute is a dictionary mapping names to objects.\n\nInstances of Function describe functions with the attributes from _Object,\nplus the following:\n    is_async -- if a function is defined with an 'async' prefix\n\nInstances of Class describe classes with the attributes from _Object,\nplus the following:\n    super   -- list of super classes (Class instances if possible);\n    methods -- mapping of method names to beginning line numbers.\nIf the name of a super class is not recognized, the corresponding\nentry in the list of super classes is not a class instance but a\nstring giving the name of the super class.  Since import statements\nare recognized and imported modules are scanned as well, this\nshouldn't happen often.\n"
import ast
import sys
import importlib.util

__all__ = ["readmodule", "readmodule_ex", "Class", "Function"]
_modules = {}


class _Object:
    "Information about Python class or function."

    def __init__(self, module, name, file, lineno, end_lineno, parent):
        self.module = module
        self.name = name
        self.file = file
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.parent = parent
        self.children = {}
        if parent is not None:
            parent.children[name] = self


class Function(_Object):
    "Information about a Python function, including methods."

    def __init__(
        self,
        module,
        name,
        file,
        lineno,
        parent=None,
        is_async=False,
        *,
        end_lineno=None,
    ):
        super().__init__(module, name, file, lineno, end_lineno, parent)
        self.is_async = is_async
        if isinstance(parent, Class):
            parent.methods[name] = lineno


class Class(_Object):
    "Information about a Python class."

    def __init__(
        self, module, name, super_, file, lineno, parent=None, *, end_lineno=None
    ):
        super().__init__(module, name, file, lineno, end_lineno, parent)
        self.super = super_ or []
        self.methods = {}


def _nest_function(ob, func_name, lineno, end_lineno, is_async=False):
    "Return a Function after nesting within ob."
    return Function(
        ob.module,
        func_name,
        ob.file,
        lineno,
        parent=ob,
        is_async=is_async,
        end_lineno=end_lineno,
    )


def _nest_class(ob, class_name, lineno, end_lineno, super=None):
    "Return a Class after nesting within ob."
    return Class(
        ob.module, class_name, super, ob.file, lineno, parent=ob, end_lineno=end_lineno
    )


def readmodule(module, path=None):
    "Return Class objects for the top-level classes in module.\n\n    This is the original interface, before Functions were added.\n    "
    res = {}
    for (key, value) in _readmodule(module, (path or [])).items():
        if isinstance(value, Class):
            res[key] = value
    return res


def readmodule_ex(module, path=None):
    "Return a dictionary with all functions and classes in module.\n\n    Search for module in PATH + sys.path.\n    If possible, include imported superclasses.\n    Do this by reading source, without importing (and executing) it.\n    "
    return _readmodule(module, (path or []))


def _readmodule(module, path, inpackage=None):
    "Do the hard work for readmodule[_ex].\n\n    If inpackage is given, it must be the dotted name of the package in\n    which we are searching for a submodule, and then PATH must be the\n    package search path; otherwise, we are searching for a top-level\n    module, and path is combined with sys.path.\n    "
    if inpackage is not None:
        fullmodule = "%s.%s" % (inpackage, module)
    else:
        fullmodule = module
    if fullmodule in _modules:
        return _modules[fullmodule]
    tree = {}
    if (module in sys.builtin_module_names) and (inpackage is None):
        _modules[module] = tree
        return tree
    i = module.rfind(".")
    if i >= 0:
        package = module[:i]
        submodule = module[(i + 1) :]
        parent = _readmodule(package, path, inpackage)
        if inpackage is not None:
            package = "%s.%s" % (inpackage, package)
        if not ("__path__" in parent):
            raise ImportError("No package named {}".format(package))
        return _readmodule(submodule, parent["__path__"], package)
    f = None
    if inpackage is not None:
        search_path = path
    else:
        search_path = path + sys.path
    spec = importlib.util._find_spec_from_path(fullmodule, search_path)
    if spec is None:
        raise ModuleNotFoundError(f"no module named {fullmodule!r}", name=fullmodule)
    _modules[fullmodule] = tree
    if spec.submodule_search_locations is not None:
        tree["__path__"] = spec.submodule_search_locations
    try:
        source = spec.loader.get_source(fullmodule)
    except (AttributeError, ImportError):
        return tree
    else:
        if source is None:
            return tree
    fname = spec.loader.get_filename(fullmodule)
    return _create_tree(fullmodule, path, fname, source, tree, inpackage)


class _ModuleBrowser(ast.NodeVisitor):
    def __init__(self, module, path, file, tree, inpackage):
        self.path = path
        self.tree = tree
        self.file = file
        self.module = module
        self.inpackage = inpackage
        self.stack = []

    def visit_ClassDef(self, node):
        bases = []
        for base in node.bases:
            name = ast.unparse(base)
            if name in self.tree:
                bases.append(self.tree[name])
            elif len((names := name.split("."))) > 1:
                (*_, module, class_) = names
                if module in _modules:
                    bases.append(_modules[module].get(class_, name))
            else:
                bases.append(name)
        parent = self.stack[(-1)] if self.stack else None
        class_ = Class(
            self.module,
            node.name,
            bases,
            self.file,
            node.lineno,
            parent=parent,
            end_lineno=node.end_lineno,
        )
        if parent is None:
            self.tree[node.name] = class_
        self.stack.append(class_)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node, *, is_async=False):
        parent = self.stack[(-1)] if self.stack else None
        function = Function(
            self.module,
            node.name,
            self.file,
            node.lineno,
            parent,
            is_async,
            end_lineno=node.end_lineno,
        )
        if parent is None:
            self.tree[node.name] = function
        self.stack.append(function)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node, is_async=True)

    def visit_Import(self, node):
        if node.col_offset != 0:
            return
        for module in node.names:
            try:
                try:
                    _readmodule(module.name, self.path, self.inpackage)
                except ImportError:
                    _readmodule(module.name, [])
            except (ImportError, SyntaxError):
                continue

    def visit_ImportFrom(self, node):
        if node.col_offset != 0:
            return
        try:
            module = "." * node.level
            if node.module:
                module += node.module
            module = _readmodule(module, self.path, self.inpackage)
        except (ImportError, SyntaxError):
            return
        for name in node.names:
            if name.name in module:
                self.tree[(name.asname or name.name)] = module[name.name]
            elif name.name == "*":
                for (import_name, import_value) in module.items():
                    if import_name.startswith("_"):
                        continue
                    self.tree[import_name] = import_value


def _create_tree(fullmodule, path, fname, source, tree, inpackage):
    mbrowser = _ModuleBrowser(fullmodule, path, fname, tree, inpackage)
    mbrowser.visit(ast.parse(source))
    return mbrowser.tree


def _main():
    "Print module output (default this file) for quick visual check."
    import os

    try:
        mod = sys.argv[1]
    except:
        mod = __file__
    if os.path.exists(mod):
        path = [os.path.dirname(mod)]
        mod = os.path.basename(mod)
        if mod.lower().endswith(".py"):
            mod = mod[:(-3)]
    else:
        path = []
    tree = readmodule_ex(mod, path)
    lineno_key = lambda a: getattr(a, "lineno", 0)
    objs = sorted(tree.values(), key=lineno_key, reverse=True)
    indent_level = 2
    while objs:
        obj = objs.pop()
        if isinstance(obj, list):
            continue
        if not hasattr(obj, "indent"):
            obj.indent = 0
        if isinstance(obj, _Object):
            new_objs = sorted(obj.children.values(), key=lineno_key, reverse=True)
            for ob in new_objs:
                ob.indent = obj.indent + indent_level
            objs.extend(new_objs)
        if isinstance(obj, Class):
            print(
                "{}class {} {} {}".format(
                    (" " * obj.indent), obj.name, obj.super, obj.lineno
                )
            )
        elif isinstance(obj, Function):
            print("{}def {} {}".format((" " * obj.indent), obj.name, obj.lineno))


if __name__ == "__main__":
    _main()
