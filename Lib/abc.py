"Abstract Base Classes (ABCs) according to PEP 3119."


def abstractmethod(funcobj):
    "A decorator indicating abstract methods.\n\n    Requires that the metaclass is ABCMeta or derived from it.  A\n    class that has a metaclass derived from ABCMeta cannot be\n    instantiated unless all of its abstract methods are overridden.\n    The abstract methods can be called using any of the normal\n    'super' call mechanisms.  abstractmethod() may be used to declare\n    abstract methods for properties and descriptors.\n\n    Usage:\n\n        class C(metaclass=ABCMeta):\n            @abstractmethod\n            def my_abstract_method(self, ...):\n                ...\n    "
    funcobj.__isabstractmethod__ = True
    return funcobj


class abstractclassmethod(classmethod):
    "A decorator indicating abstract classmethods.\n\n    Deprecated, use 'classmethod' with 'abstractmethod' instead.\n    "
    __isabstractmethod__ = True

    def __init__(self, callable):
        callable.__isabstractmethod__ = True
        super().__init__(callable)


class abstractstaticmethod(staticmethod):
    "A decorator indicating abstract staticmethods.\n\n    Deprecated, use 'staticmethod' with 'abstractmethod' instead.\n    "
    __isabstractmethod__ = True

    def __init__(self, callable):
        callable.__isabstractmethod__ = True
        super().__init__(callable)


class abstractproperty(property):
    "A decorator indicating abstract properties.\n\n    Deprecated, use 'property' with 'abstractmethod' instead.\n    "
    __isabstractmethod__ = True


try:
    from _abc import (
        get_cache_token,
        _abc_init,
        _abc_register,
        _abc_instancecheck,
        _abc_subclasscheck,
        _get_dump,
        _reset_registry,
        _reset_caches,
    )
except ImportError:
    from _py_abc import ABCMeta, get_cache_token

    ABCMeta.__module__ = "abc"
else:

    class ABCMeta(type):
        "Metaclass for defining Abstract Base Classes (ABCs).\n\n        Use this metaclass to create an ABC.  An ABC can be subclassed\n        directly, and then acts as a mix-in class.  You can also register\n        unrelated concrete classes (even built-in classes) and unrelated\n        ABCs as 'virtual subclasses' -- these and their descendants will\n        be considered subclasses of the registering ABC by the built-in\n        issubclass() function, but the registering ABC won't show up in\n        their MRO (Method Resolution Order) nor will method\n        implementations defined by the registering ABC be callable (not\n        even via super()).\n        "

        def __new__(mcls, name, bases, namespace, **kwargs):
            cls = super().__new__(mcls, name, bases, namespace, **kwargs)
            _abc_init(cls)
            return cls

        def register(cls, subclass):
            "Register a virtual subclass of an ABC.\n\n            Returns the subclass, to allow usage as a class decorator.\n            "
            return _abc_register(cls, subclass)

        def __instancecheck__(cls, instance):
            "Override for isinstance(instance, cls)."
            return _abc_instancecheck(cls, instance)

        def __subclasscheck__(cls, subclass):
            "Override for issubclass(subclass, cls)."
            return _abc_subclasscheck(cls, subclass)

        def _dump_registry(cls, file=None):
            "Debug helper to print the ABC registry."
            print(f"Class: {cls.__module__}.{cls.__qualname__}", file=file)
            print(f"Inv. counter: {get_cache_token()}", file=file)
            (
                _abc_registry,
                _abc_cache,
                _abc_negative_cache,
                _abc_negative_cache_version,
            ) = _get_dump(cls)
            print(f"_abc_registry: {_abc_registry!r}", file=file)
            print(f"_abc_cache: {_abc_cache!r}", file=file)
            print(f"_abc_negative_cache: {_abc_negative_cache!r}", file=file)
            print(
                f"_abc_negative_cache_version: {_abc_negative_cache_version!r}",
                file=file,
            )

        def _abc_registry_clear(cls):
            "Clear the registry (for debugging or testing)."
            _reset_registry(cls)

        def _abc_caches_clear(cls):
            "Clear the caches (for debugging or testing)."
            _reset_caches(cls)


def update_abstractmethods(cls):
    "Recalculate the set of abstract methods of an abstract class.\n\n    If a class has had one of its abstract methods implemented after the\n    class was created, the method will not be considered implemented until\n    this function is called. Alternatively, if a new abstract method has been\n    added to the class, it will only be considered an abstract method of the\n    class after this function is called.\n\n    This function should be called before any use is made of the class,\n    usually in class decorators that add methods to the subject class.\n\n    Returns cls, to allow usage as a class decorator.\n\n    If cls is not an instance of ABCMeta, does nothing.\n    "
    if not hasattr(cls, "__abstractmethods__"):
        return cls
    abstracts = set()
    for scls in cls.__bases__:
        for name in getattr(scls, "__abstractmethods__", ()):
            value = getattr(cls, name, None)
            if getattr(value, "__isabstractmethod__", False):
                abstracts.add(name)
    for (name, value) in cls.__dict__.items():
        if getattr(value, "__isabstractmethod__", False):
            abstracts.add(name)
    cls.__abstractmethods__ = frozenset(abstracts)
    return cls


class ABC(metaclass=ABCMeta):
    "Helper class that provides a standard way to create an ABC using\n    inheritance.\n    "
    __slots__ = ()
