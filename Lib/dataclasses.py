import re
import sys
import copy
import types
import inspect
import keyword
import builtins
import functools
import abc
import _thread
from types import FunctionType, GenericAlias

__all__ = [
    "dataclass",
    "field",
    "Field",
    "FrozenInstanceError",
    "InitVar",
    "MISSING",
    "fields",
    "asdict",
    "astuple",
    "make_dataclass",
    "replace",
    "is_dataclass",
]


class FrozenInstanceError(AttributeError):
    pass


class _HAS_DEFAULT_FACTORY_CLASS:
    def __repr__(self):
        return "<factory>"


_HAS_DEFAULT_FACTORY = _HAS_DEFAULT_FACTORY_CLASS()


class _MISSING_TYPE:
    pass


MISSING = _MISSING_TYPE()
_EMPTY_METADATA = types.MappingProxyType({})


class _FIELD_BASE:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


_FIELD = _FIELD_BASE("_FIELD")
_FIELD_CLASSVAR = _FIELD_BASE("_FIELD_CLASSVAR")
_FIELD_INITVAR = _FIELD_BASE("_FIELD_INITVAR")
_FIELDS = "__dataclass_fields__"
_PARAMS = "__dataclass_params__"
_POST_INIT_NAME = "__post_init__"
_MODULE_IDENTIFIER_RE = re.compile("^(?:\\s*(\\w+)\\s*\\.)?\\s*(\\w+)")


class InitVar:
    __slots__ = ("type",)

    def __init__(self, type):
        self.type = type

    def __repr__(self):
        if isinstance(self.type, type):
            type_name = self.type.__name__
        else:
            type_name = repr(self.type)
        return f"dataclasses.InitVar[{type_name}]"

    def __class_getitem__(cls, type):
        return InitVar(type)


class Field:
    __slots__ = (
        "name",
        "type",
        "default",
        "default_factory",
        "repr",
        "hash",
        "init",
        "compare",
        "metadata",
        "_field_type",
    )

    def __init__(self, default, default_factory, init, repr, hash, compare, metadata):
        self.name = None
        self.type = None
        self.default = default
        self.default_factory = default_factory
        self.init = init
        self.repr = repr
        self.hash = hash
        self.compare = compare
        self.metadata = (
            _EMPTY_METADATA if (metadata is None) else types.MappingProxyType(metadata)
        )
        self._field_type = None

    def __repr__(self):
        return f"Field(name={self.name!r},type={self.type!r},default={self.default!r},default_factory={self.default_factory!r},init={self.init!r},repr={self.repr!r},hash={self.hash!r},compare={self.compare!r},metadata={self.metadata!r},_field_type={self._field_type})"

    def __set_name__(self, owner, name):
        func = getattr(type(self.default), "__set_name__", None)
        if func:
            func(self.default, owner, name)

    __class_getitem__ = classmethod(GenericAlias)


class _DataclassParams:
    __slots__ = ("init", "repr", "eq", "order", "unsafe_hash", "frozen")

    def __init__(self, init, repr, eq, order, unsafe_hash, frozen):
        self.init = init
        self.repr = repr
        self.eq = eq
        self.order = order
        self.unsafe_hash = unsafe_hash
        self.frozen = frozen

    def __repr__(self):
        return f"_DataclassParams(init={self.init!r},repr={self.repr!r},eq={self.eq!r},order={self.order!r},unsafe_hash={self.unsafe_hash!r},frozen={self.frozen!r})"


def field(
    *,
    default=MISSING,
    default_factory=MISSING,
    init=True,
    repr=True,
    hash=None,
    compare=True,
    metadata=None,
):
    "Return an object to identify dataclass fields.\n\n    default is the default value of the field.  default_factory is a\n    0-argument function called to initialize a field's value.  If init\n    is True, the field will be a parameter to the class's __init__()\n    function.  If repr is True, the field will be included in the\n    object's repr().  If hash is True, the field will be included in\n    the object's hash().  If compare is True, the field will be used\n    in comparison functions.  metadata, if specified, must be a\n    mapping which is stored but not otherwise examined by dataclass.\n\n    It is an error to specify both default and default_factory.\n    "
    if (default is not MISSING) and (default_factory is not MISSING):
        raise ValueError("cannot specify both default and default_factory")
    return Field(default, default_factory, init, repr, hash, compare, metadata)


def _tuple_str(obj_name, fields):
    if not fields:
        return "()"
    return f"({','.join([f'{obj_name}.{f.name}' for f in fields])},)"


def _recursive_repr(user_function):
    repr_running = set()

    @functools.wraps(user_function)
    def wrapper(self):
        key = (id(self), _thread.get_ident())
        if key in repr_running:
            return "..."
        repr_running.add(key)
        try:
            result = user_function(self)
        finally:
            repr_running.discard(key)
        return result

    return wrapper


def _create_fn(name, args, body, *, globals=None, locals=None, return_type=MISSING):
    if locals is None:
        locals = {}
    if "BUILTINS" not in locals:
        locals["BUILTINS"] = builtins
    return_annotation = ""
    if return_type is not MISSING:
        locals["_return_type"] = return_type
        return_annotation = "->_return_type"
    args = ",".join(args)
    body = "\n".join((f"  {b}" for b in body))
    txt = f""" def {name}({args}){return_annotation}:
{body}"""
    local_vars = ", ".join(locals.keys())
    txt = f"""def __create_fn__({local_vars}):
{txt}
 return {name}"""
    ns = {}
    exec(txt, globals, ns)
    return ns["__create_fn__"](**locals)


def _field_assign(frozen, name, value, self_name):
    if frozen:
        return f"BUILTINS.object.__setattr__({self_name},{name!r},{value})"
    return f"{self_name}.{name}={value}"


def _field_init(f, frozen, globals, self_name):
    default_name = f"_dflt_{f.name}"
    if f.default_factory is not MISSING:
        if f.init:
            globals[default_name] = f.default_factory
            value = (
                f"{default_name}() if {f.name} is _HAS_DEFAULT_FACTORY else {f.name}"
            )
        else:
            globals[default_name] = f.default_factory
            value = f"{default_name}()"
    elif f.init:
        if f.default is MISSING:
            value = f.name
        elif f.default is not MISSING:
            globals[default_name] = f.default
            value = f.name
    else:
        return None
    if f._field_type is _FIELD_INITVAR:
        return None
    return _field_assign(frozen, f.name, value, self_name)


def _init_param(f):
    if (f.default is MISSING) and (f.default_factory is MISSING):
        default = ""
    elif f.default is not MISSING:
        default = f"=_dflt_{f.name}"
    elif f.default_factory is not MISSING:
        default = "=_HAS_DEFAULT_FACTORY"
    return f"{f.name}:_type_{f.name}{default}"


def _init_fn(fields, frozen, has_post_init, self_name, globals):
    seen_default = False
    for f in fields:
        if f.init:
            if not ((f.default is MISSING) and (f.default_factory is MISSING)):
                seen_default = True
            elif seen_default:
                raise TypeError(
                    f"non-default argument {f.name!r} follows default argument"
                )
    locals = {f"_type_{f.name}": f.type for f in fields}
    locals.update({"MISSING": MISSING, "_HAS_DEFAULT_FACTORY": _HAS_DEFAULT_FACTORY})
    body_lines = []
    for f in fields:
        line = _field_init(f, frozen, locals, self_name)
        if line:
            body_lines.append(line)
    if has_post_init:
        params_str = ",".join(
            (f.name for f in fields if (f._field_type is _FIELD_INITVAR))
        )
        body_lines.append(f"{self_name}.{_POST_INIT_NAME}({params_str})")
    if not body_lines:
        body_lines = ["pass"]
    return _create_fn(
        "__init__",
        ([self_name] + [_init_param(f) for f in fields if f.init]),
        body_lines,
        locals=locals,
        globals=globals,
        return_type=None,
    )


def _repr_fn(fields, globals):
    fn = _create_fn(
        "__repr__",
        ("self",),
        [
            (
                (
                    'return self.__class__.__qualname__ + f"('
                    + ", ".join([f"{f.name}={{self.{f.name}!r}}" for f in fields])
                )
                + ')"'
            )
        ],
        globals=globals,
    )
    return _recursive_repr(fn)


def _frozen_get_del_attr(cls, fields, globals):
    locals = {"cls": cls, "FrozenInstanceError": FrozenInstanceError}
    if fields:
        fields_str = ("(" + ",".join((repr(f.name) for f in fields))) + ",)"
    else:
        fields_str = "()"
    return (
        _create_fn(
            "__setattr__",
            ("self", "name", "value"),
            (
                f"if type(self) is cls or name in {fields_str}:",
                ' raise FrozenInstanceError(f"cannot assign to field {name!r}")',
                f"super(cls, self).__setattr__(name, value)",
            ),
            locals=locals,
            globals=globals,
        ),
        _create_fn(
            "__delattr__",
            ("self", "name"),
            (
                f"if type(self) is cls or name in {fields_str}:",
                ' raise FrozenInstanceError(f"cannot delete field {name!r}")',
                f"super(cls, self).__delattr__(name)",
            ),
            locals=locals,
            globals=globals,
        ),
    )


def _cmp_fn(name, op, self_tuple, other_tuple, globals):
    return _create_fn(
        name,
        ("self", "other"),
        [
            "if other.__class__ is self.__class__:",
            f" return {self_tuple}{op}{other_tuple}",
            "return NotImplemented",
        ],
        globals=globals,
    )


def _hash_fn(fields, globals):
    self_tuple = _tuple_str("self", fields)
    return _create_fn(
        "__hash__", ("self",), [f"return hash({self_tuple})"], globals=globals
    )


def _is_classvar(a_type, typing):
    return (a_type is typing.ClassVar) or (
        (type(a_type) is typing._GenericAlias)
        and (a_type.__origin__ is typing.ClassVar)
    )


def _is_initvar(a_type, dataclasses):
    return (a_type is dataclasses.InitVar) or (type(a_type) is dataclasses.InitVar)


def _is_type(annotation, cls, a_module, a_type, is_type_predicate):
    match = _MODULE_IDENTIFIER_RE.match(annotation)
    if match:
        ns = None
        module_name = match.group(1)
        if not module_name:
            ns = sys.modules.get(cls.__module__).__dict__
        else:
            module = sys.modules.get(cls.__module__)
            if module and (module.__dict__.get(module_name) is a_module):
                ns = sys.modules.get(a_type.__module__).__dict__
        if ns and is_type_predicate(ns.get(match.group(2)), a_module):
            return True
    return False


def _get_field(cls, a_name, a_type):
    default = getattr(cls, a_name, MISSING)
    if isinstance(default, Field):
        f = default
    else:
        if isinstance(default, types.MemberDescriptorType):
            default = MISSING
        f = field(default=default)
    f.name = a_name
    f.type = a_type
    f._field_type = _FIELD
    typing = sys.modules.get("typing")
    if typing:
        if _is_classvar(a_type, typing) or (
            isinstance(f.type, str)
            and _is_type(f.type, cls, typing, typing.ClassVar, _is_classvar)
        ):
            f._field_type = _FIELD_CLASSVAR
    if f._field_type is _FIELD:
        dataclasses = sys.modules[__name__]
        if _is_initvar(a_type, dataclasses) or (
            isinstance(f.type, str)
            and _is_type(f.type, cls, dataclasses, dataclasses.InitVar, _is_initvar)
        ):
            f._field_type = _FIELD_INITVAR
    if f._field_type in (_FIELD_CLASSVAR, _FIELD_INITVAR):
        if f.default_factory is not MISSING:
            raise TypeError(f"field {f.name} cannot have a default factory")
    if (f._field_type is _FIELD) and isinstance(f.default, (list, dict, set)):
        raise ValueError(
            f"mutable default {type(f.default)} for field {f.name} is not allowed: use default_factory"
        )
    return f


def _set_qualname(cls, value):
    if isinstance(value, FunctionType):
        value.__qualname__ = f"{cls.__qualname__}.{value.__name__}"
    return value


def _set_new_attribute(cls, name, value):
    if name in cls.__dict__:
        return True
    _set_qualname(cls, value)
    setattr(cls, name, value)
    return False


def _hash_set_none(cls, fields, globals):
    return None


def _hash_add(cls, fields, globals):
    flds = [f for f in fields if (f.compare if (f.hash is None) else f.hash)]
    return _set_qualname(cls, _hash_fn(flds, globals))


def _hash_exception(cls, fields, globals):
    raise TypeError(f"Cannot overwrite attribute __hash__ in class {cls.__name__}")


_hash_action = {
    (False, False, False, False): None,
    (False, False, False, True): None,
    (False, False, True, False): None,
    (False, False, True, True): None,
    (False, True, False, False): _hash_set_none,
    (False, True, False, True): None,
    (False, True, True, False): _hash_add,
    (False, True, True, True): None,
    (True, False, False, False): _hash_add,
    (True, False, False, True): _hash_exception,
    (True, False, True, False): _hash_add,
    (True, False, True, True): _hash_exception,
    (True, True, False, False): _hash_add,
    (True, True, False, True): _hash_exception,
    (True, True, True, False): _hash_add,
    (True, True, True, True): _hash_exception,
}


def _process_class(cls, init, repr, eq, order, unsafe_hash, frozen, match_args):
    fields = {}
    if cls.__module__ in sys.modules:
        globals = sys.modules[cls.__module__].__dict__
    else:
        globals = {}
    setattr(cls, _PARAMS, _DataclassParams(init, repr, eq, order, unsafe_hash, frozen))
    any_frozen_base = False
    has_dataclass_bases = False
    for b in cls.__mro__[(-1):0:(-1)]:
        base_fields = getattr(b, _FIELDS, None)
        if base_fields is not None:
            has_dataclass_bases = True
            for f in base_fields.values():
                fields[f.name] = f
            if getattr(b, _PARAMS).frozen:
                any_frozen_base = True
    cls_annotations = cls.__dict__.get("__annotations__", {})
    cls_fields = [
        _get_field(cls, name, type) for (name, type) in cls_annotations.items()
    ]
    for f in cls_fields:
        fields[f.name] = f
        if isinstance(getattr(cls, f.name, None), Field):
            if f.default is MISSING:
                delattr(cls, f.name)
            else:
                setattr(cls, f.name, f.default)
    for (name, value) in cls.__dict__.items():
        if isinstance(value, Field) and (not (name in cls_annotations)):
            raise TypeError(f"{name!r} is a field but has no type annotation")
    if has_dataclass_bases:
        if any_frozen_base and (not frozen):
            raise TypeError("cannot inherit non-frozen dataclass from a frozen one")
        if (not any_frozen_base) and frozen:
            raise TypeError("cannot inherit frozen dataclass from a non-frozen one")
    setattr(cls, _FIELDS, fields)
    class_hash = cls.__dict__.get("__hash__", MISSING)
    has_explicit_hash = not (
        (class_hash is MISSING) or ((class_hash is None) and ("__eq__" in cls.__dict__))
    )
    if order and (not eq):
        raise ValueError("eq must be true if order is true")
    if init:
        has_post_init = hasattr(cls, _POST_INIT_NAME)
        flds = [
            f for f in fields.values() if (f._field_type in (_FIELD, _FIELD_INITVAR))
        ]
        _set_new_attribute(
            cls,
            "__init__",
            _init_fn(
                flds,
                frozen,
                has_post_init,
                ("__dataclass_self__" if ("self" in fields) else "self"),
                globals,
            ),
        )
    field_list = [f for f in fields.values() if (f._field_type is _FIELD)]
    if repr:
        flds = [f for f in field_list if f.repr]
        _set_new_attribute(cls, "__repr__", _repr_fn(flds, globals))
    if eq:
        flds = [f for f in field_list if f.compare]
        self_tuple = _tuple_str("self", flds)
        other_tuple = _tuple_str("other", flds)
        _set_new_attribute(
            cls,
            "__eq__",
            _cmp_fn("__eq__", "==", self_tuple, other_tuple, globals=globals),
        )
    if order:
        flds = [f for f in field_list if f.compare]
        self_tuple = _tuple_str("self", flds)
        other_tuple = _tuple_str("other", flds)
        for (name, op) in [
            ("__lt__", "<"),
            ("__le__", "<="),
            ("__gt__", ">"),
            ("__ge__", ">="),
        ]:
            if _set_new_attribute(
                cls, name, _cmp_fn(name, op, self_tuple, other_tuple, globals=globals)
            ):
                raise TypeError(
                    f"Cannot overwrite attribute {name} in class {cls.__name__}. Consider using functools.total_ordering"
                )
    if frozen:
        for fn in _frozen_get_del_attr(cls, field_list, globals):
            if _set_new_attribute(cls, fn.__name__, fn):
                raise TypeError(
                    f"Cannot overwrite attribute {fn.__name__} in class {cls.__name__}"
                )
    hash_action = _hash_action[
        (bool(unsafe_hash), bool(eq), bool(frozen), has_explicit_hash)
    ]
    if hash_action:
        cls.__hash__ = hash_action(cls, field_list, globals)
    if not getattr(cls, "__doc__"):
        cls.__doc__ = cls.__name__ + str(inspect.signature(cls)).replace(" -> None", "")
    if match_args:
        _set_new_attribute(
            cls, "__match_args__", tuple((f.name for f in field_list if f.init))
        )
    abc.update_abstractmethods(cls)
    return cls


def dataclass(
    cls=None,
    /,
    *,
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=False,
    match_args=True,
):
    "Returns the same class as was passed in, with dunder methods\n    added based on the fields defined in the class.\n\n    Examines PEP 526 __annotations__ to determine fields.\n\n    If init is true, an __init__() method is added to the class. If\n    repr is true, a __repr__() method is added. If order is true, rich\n    comparison dunder methods are added. If unsafe_hash is true, a\n    __hash__() method function is added. If frozen is true, fields may\n    not be assigned to after instance creation. If match_args is true,\n    the __match_args__ tuple is added.\n    "

    def wrap(cls):
        return _process_class(
            cls, init, repr, eq, order, unsafe_hash, frozen, match_args
        )

    if cls is None:
        return wrap
    return wrap(cls)


def fields(class_or_instance):
    "Return a tuple describing the fields of this dataclass.\n\n    Accepts a dataclass or an instance of one. Tuple elements are of\n    type Field.\n    "
    try:
        fields = getattr(class_or_instance, _FIELDS)
    except AttributeError:
        raise TypeError("must be called with a dataclass type or instance")
    return tuple((f for f in fields.values() if (f._field_type is _FIELD)))


def _is_dataclass_instance(obj):
    "Returns True if obj is an instance of a dataclass."
    return hasattr(type(obj), _FIELDS)


def is_dataclass(obj):
    "Returns True if obj is a dataclass or an instance of a\n    dataclass."
    cls = obj if isinstance(obj, type) else type(obj)
    return hasattr(cls, _FIELDS)


def asdict(obj, *, dict_factory=dict):
    "Return the fields of a dataclass instance as a new dictionary mapping\n    field names to field values.\n\n    Example usage:\n\n      @dataclass\n      class C:\n          x: int\n          y: int\n\n      c = C(1, 2)\n      assert asdict(c) == {'x': 1, 'y': 2}\n\n    If given, 'dict_factory' will be used instead of built-in dict.\n    The function applies recursively to field values that are\n    dataclass instances. This will also look into built-in containers:\n    tuples, lists, and dicts.\n    "
    if not _is_dataclass_instance(obj):
        raise TypeError("asdict() should be called on dataclass instances")
    return _asdict_inner(obj, dict_factory)


def _asdict_inner(obj, dict_factory):
    if _is_dataclass_instance(obj):
        result = []
        for f in fields(obj):
            value = _asdict_inner(getattr(obj, f.name), dict_factory)
            result.append((f.name, value))
        return dict_factory(result)
    elif isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)((_asdict_inner(v, dict_factory) for v in obj))
    elif isinstance(obj, dict):
        return type(obj)(
            (
                (_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory))
                for (k, v) in obj.items()
            )
        )
    else:
        return copy.deepcopy(obj)


def astuple(obj, *, tuple_factory=tuple):
    "Return the fields of a dataclass instance as a new tuple of field values.\n\n    Example usage::\n\n      @dataclass\n      class C:\n          x: int\n          y: int\n\n    c = C(1, 2)\n    assert astuple(c) == (1, 2)\n\n    If given, 'tuple_factory' will be used instead of built-in tuple.\n    The function applies recursively to field values that are\n    dataclass instances. This will also look into built-in containers:\n    tuples, lists, and dicts.\n    "
    if not _is_dataclass_instance(obj):
        raise TypeError("astuple() should be called on dataclass instances")
    return _astuple_inner(obj, tuple_factory)


def _astuple_inner(obj, tuple_factory):
    if _is_dataclass_instance(obj):
        result = []
        for f in fields(obj):
            value = _astuple_inner(getattr(obj, f.name), tuple_factory)
            result.append(value)
        return tuple_factory(result)
    elif isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return type(obj)(*[_astuple_inner(v, tuple_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)((_astuple_inner(v, tuple_factory) for v in obj))
    elif isinstance(obj, dict):
        return type(obj)(
            (
                (_astuple_inner(k, tuple_factory), _astuple_inner(v, tuple_factory))
                for (k, v) in obj.items()
            )
        )
    else:
        return copy.deepcopy(obj)


def make_dataclass(
    cls_name,
    fields,
    *,
    bases=(),
    namespace=None,
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=False,
    match_args=True,
):
    "Return a new dynamically created dataclass.\n\n    The dataclass name will be 'cls_name'.  'fields' is an iterable\n    of either (name), (name, type) or (name, type, Field) objects. If type is\n    omitted, use the string 'typing.Any'.  Field objects are created by\n    the equivalent of calling 'field(name, type [, Field-info])'.\n\n      C = make_dataclass('C', ['x', ('y', int), ('z', int, field(init=False))], bases=(Base,))\n\n    is equivalent to:\n\n      @dataclass\n      class C(Base):\n          x: 'typing.Any'\n          y: int\n          z: int = field(init=False)\n\n    For the bases and namespace parameters, see the builtin type() function.\n\n    The parameters init, repr, eq, order, unsafe_hash, and frozen are passed to\n    dataclass().\n    "
    if namespace is None:
        namespace = {}
    seen = set()
    annotations = {}
    defaults = {}
    for item in fields:
        if isinstance(item, str):
            name = item
            tp = "typing.Any"
        elif len(item) == 2:
            (name, tp) = item
        elif len(item) == 3:
            (name, tp, spec) = item
            defaults[name] = spec
        else:
            raise TypeError(f"Invalid field: {item!r}")
        if (not isinstance(name, str)) or (not name.isidentifier()):
            raise TypeError(f"Field names must be valid identifiers: {name!r}")
        if keyword.iskeyword(name):
            raise TypeError(f"Field names must not be keywords: {name!r}")
        if name in seen:
            raise TypeError(f"Field name duplicated: {name!r}")
        seen.add(name)
        annotations[name] = tp

    def exec_body_callback(ns):
        ns.update(namespace)
        ns.update(defaults)
        ns["__annotations__"] = annotations

    cls = types.new_class(cls_name, bases, {}, exec_body_callback)
    return dataclass(
        cls,
        init=init,
        repr=repr,
        eq=eq,
        order=order,
        unsafe_hash=unsafe_hash,
        frozen=frozen,
        match_args=match_args,
    )


def replace(obj, /, **changes):
    "Return a new object replacing specified fields with new values.\n\n    This is especially useful for frozen classes.  Example usage:\n\n      @dataclass(frozen=True)\n      class C:\n          x: int\n          y: int\n\n      c = C(1, 2)\n      c1 = replace(c, x=3)\n      assert c1.x == 3 and c1.y == 2\n      "
    if not _is_dataclass_instance(obj):
        raise TypeError("replace() should be called on dataclass instances")
    for f in getattr(obj, _FIELDS).values():
        if f._field_type is _FIELD_CLASSVAR:
            continue
        if not f.init:
            if f.name in changes:
                raise ValueError(
                    f"field {f.name} is declared with init=False, it cannot be specified with replace()"
                )
            continue
        if f.name not in changes:
            if (f._field_type is _FIELD_INITVAR) and (f.default is MISSING):
                raise ValueError(f"InitVar {f.name!r} must be specified with replace()")
            changes[f.name] = getattr(obj, f.name)
    return obj.__class__(**changes)
