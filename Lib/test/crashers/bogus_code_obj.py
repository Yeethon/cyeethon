'\nBroken bytecode objects can easily crash the interpreter.\n\nThis is not going to be fixed.  It is generally agreed that there is no\npoint in writing a bytecode verifier and putting it in CPython just for\nthis.  Moreover, a verifier is bound to accept only a subset of all safe\nbytecodes, so it could lead to unnecessary breakage.\n\nFor security purposes, "restricted" interpreters are not going to let\nthe user build or load random bytecodes anyway.  Otherwise, this is a\n"won\'t fix" case.\n\n'
import types

co = types.CodeType(0, 0, 0, 0, 0, 0, b"\x04\x00q\x00", (), (), (), "", "", 1, b"")
exec(co)
