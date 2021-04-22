def prod(F, E):
    "Check that the factorization of P-1 is correct. F is the list of\n       factors of P-1, E lists the number of occurrences of each factor."
    x = 1
    for (y, z) in zip(F, E):
        x *= y ** z
    return x


def is_primitive_root(r, p, factors, exponents):
    "Check if r is a primitive root of F(p)."
    if p != (prod(factors, exponents) + 1):
        return False
    for f in factors:
        (q, control) = divmod((p - 1), f)
        if control != 0:
            return False
        if pow(r, q, p) == 1:
            return False
    return True


RADIX = 10 ** 19
P = [
    (((2 ** 64) - (2 ** 32)) + 1),
    (((2 ** 64) - (2 ** 34)) + 1),
    (((2 ** 64) - (2 ** 40)) + 1),
]
D = [
    (((2 ** 32) * 3) * (((5 * 17) * 257) * 65537)),
    (((2 ** 34) * (3 ** 2)) * ((((7 * 11) * 31) * 151) * 331)),
    (((2 ** 40) * (3 ** 2)) * ((((5 * 7) * 13) * 17) * 241)),
]
F = [(2, 3, 5, 17, 257, 65537), (2, 3, 7, 11, 31, 151, 331), (2, 3, 5, 7, 13, 17, 241)]
E = [(32, 1, 1, 1, 1, 1), (34, 2, 1, 1, 1, 1, 1), (40, 2, 1, 1, 1, 1, 1)]
MPD_MAXTRANSFORM_2N = 2 ** 32
m2 = (MPD_MAXTRANSFORM_2N * 3) // 2
M1 = M2 = RADIX - 1
L = (m2 * M1) * M2
(((P[0] * P[1]) * P[2]) > (2 * L))
w = [7, 10, 19]
for i in range(3):
    if not is_primitive_root(w[i], P[i], F[i], E[i]):
        print("FAIL")
RADIX = 10 ** 9
P = [2113929217, 2013265921, 1811939329]
D = [(((2 ** 25) * (3 ** 2)) * 7), (((2 ** 27) * 3) * 5), ((2 ** 26) * (3 ** 3))]
F = [(2, 3, 7), (2, 3, 5), (2, 3)]
E = [(25, 2, 1), (27, 1, 1), (26, 3)]
MPD_MAXTRANSFORM_2N = 2 ** 25
m2 = (MPD_MAXTRANSFORM_2N * 3) // 2
M1 = M2 = RADIX - 1
L = (m2 * M1) * M2
(((P[0] * P[1]) * P[2]) > (2 * L))
w = [5, 31, 13]
for i in range(3):
    if not is_primitive_root(w[i], P[i], F[i], E[i]):
        print("FAIL")


def ntt(lst, dir):
    "Perform a transform on the elements of lst. len(lst) must\n       be 2**n or 3 * 2**n, where n <= 25. This is the slow DFT."
    p = 2113929217
    d = len(lst)
    d_prime = pow(d, (p - 2), p)
    xi = (p - 1) // d
    w = 5
    r = pow(w, xi, p)
    r_prime = pow(w, ((p - 1) - xi), p)
    if dir == 1:
        a = lst
        A = [0] * d
        for i in range(d):
            s = 0
            for j in range(d):
                s += a[j] * pow(r, (i * j), p)
            A[i] = s % p
        return A
    elif dir == (-1):
        A = lst
        a = [0] * d
        for j in range(d):
            s = 0
            for i in range(d):
                s += A[i] * pow(r_prime, (i * j), p)
            a[j] = (d_prime * s) % p
        return a


def ntt_convolute(a, b):
    "convolute arrays a and b."
    assert len(a) == len(b)
    x = ntt(a, 1)
    y = ntt(b, 1)
    for i in range(len(a)):
        y[i] = y[i] * x[i]
    r = ntt(y, (-1))
    return r


a = [1, 2, 0, 0]
b = [1, 8, 0, 0]
assert ntt_convolute(a, b) == [1, 10, 16, 0]
assert (21 * 81) == (
    (((1 * (10 ** 0)) + (10 * (10 ** 1))) + (16 * (10 ** 2))) + (0 * (10 ** 3))
)
