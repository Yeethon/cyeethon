"Module for testing the behavior of generics across different modules."
import sys
from textwrap import dedent
from typing import TypeVar, Generic, Optional

if sys.version_info[:2] >= (3, 6):
    exec(
        dedent(
            "\n    default_a: Optional['A'] = None\n    default_b: Optional['B'] = None\n\n    T = TypeVar('T')\n\n\n    class A(Generic[T]):\n        some_b: 'B'\n\n\n    class B(Generic[T]):\n        class A(Generic[T]):\n            pass\n\n        my_inner_a1: 'B.A'\n        my_inner_a2: A\n        my_outer_a: 'A'  # unless somebody calls get_type_hints with localns=B.__dict__\n    "
        )
    )
else:
    __annotations__ = dict(default_a=Optional["A"], default_b=Optional["B"])
    default_a = None
    default_b = None
    T = TypeVar("T")

    class A(Generic[T]):
        __annotations__ = dict(some_b="B")

    class B(Generic[T]):
        class A(Generic[T]):
            pass

        __annotations__ = dict(my_inner_a1="B.A", my_inner_a2=A, my_outer_a="A")
