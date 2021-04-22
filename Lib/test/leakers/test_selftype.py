import gc


def leak():
    class T(type):
        pass

    class U(type, metaclass=T):
        pass

    U.__class__ = U
    del U
    gc.collect()
    gc.collect()
    gc.collect()
