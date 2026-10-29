# Generates ../smp_toolbox_tests.nv from toolbox_tests.nv.in.
# Run with `python3 -I gen_toolbox.py`, then `novo fmt ../smp_toolbox_tests.nv`.
#
# The oracle is the Python `cryptography` package (OpenSSL): AES-128 in
# ECB mode and AES-CMAC.  The formulas are transcribed from Core
# Vol 3 Part H section 2.2 and anchored by the specification's own
# Appendix D vectors, which this script asserts before it writes a
# single random row, so a transcription error cannot hide in the table.
import os, random
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import cmac

def e(k, b):
    c = Cipher(algorithms.AES(k), modes.ECB()).encryptor()
    return c.update(b) + c.finalize()
def aes_cmac(k, m):
    c = cmac.CMAC(algorithms.AES(k)); c.update(m); return c.finalize()
xor = lambda a, b: bytes(x ^ y for x, y in zip(a, b))
H = bytes.fromhex

def c1(k, r, p1, p2): return e(k, xor(e(k, xor(r, p1)), p2))
def s1(k, r1, r2): return e(k, r1[8:] + r2[8:])
def ah(irk, r): return e(irk, bytes(13) + r)[13:]
def f4(u, v, x, z): return aes_cmac(x, u + v + bytes([z]))
SALT = H("6C888391AAF5A53860370BDB5A6083BE")
def f5(w, n1, n2, a1, a2):
    t = aes_cmac(SALT, w)
    tail = H("62746c65")
    mac = aes_cmac(t, b"\x00" + tail + n1 + n2 + a1 + a2 + b"\x01\x00")
    ltk = aes_cmac(t, b"\x01" + tail + n1 + n2 + a1 + a2 + b"\x01\x00")
    return mac, ltk
def f6(w, n1, n2, r, io, a1, a2): return aes_cmac(w, n1 + n2 + r + io + a1 + a2)
def g2(u, v, x, y): return int.from_bytes(aes_cmac(x, u + v + y)[12:], 'big') % 10**6
def h6(w, kid): return aes_cmac(w, kid)
def h7(salt, w): return aes_cmac(salt, w)
def p1(pres, preq, rat, iat): return pres[::-1] + preq[::-1] + bytes([rat & 1, iat & 1])
def p2(ia, ra): return bytes(4) + ia[::-1] + ra[::-1]

# ---- Core Vol 3 Part H appendix D vectors, and 2.2.3 / 2.2.4 samples
U = H("20b003d2f297be2c5e2c83a7e9f9a5b9eff49111acf4fddbcc0301480e359de6")
V = H("55188b3d32f6bb9a900afcfbeed4e72a59cb9ac2f19d7cfb6b4fdd49f47fc5fd")
N1 = H("d5cb8454d177733effffb2ec712baeab"); N2 = H("a6e8e7cc25a75f6e216583f7ff3dc4cf")
A1 = H("0056123737bfce"); A2 = H("00a713702dcfc1")
IRK = H("ec0234a357c8ad05341010a60a397d9b")
assert f4(U, V, N1, 0) == H("f2c916f107a9bd1cf1eda1bea974872d")
W = IRK + H("99796b13b4f866f1868d34f373bfa698")
mac, ltk = f5(W, N1, N2, A1, A2)
assert aes_cmac(SALT, W) == H("3c128f20de88328897624bdb8dac6989")
assert mac == H("2965f176a1084a02fd3f6a20ce636e20") and ltk == H("6986791169d7cd23980522b594750a38")
assert f6(mac, N1, N2, H("12a3343bb453bb5408da42d20c2d0fc8"), H("010102"), A1, A2) == H("e3c473989cd0e8c5d26c0b09da958f61")
assert aes_cmac(N1, U + V + N2) == H("1536d18de3d20df99b7044c12f9ed5ba") and g2(U, V, N1, N2) == 938554
assert h6(IRK, H("6c656272")) == H("2d9ae102e76dc91ce8d3a9e280b16399")
assert h7(bytes(12) + H("746d7031"), IRK) == H("fb173597c6a3c0ecd2998c2a75a57011")
assert ah(IRK, H("708194")) == H("0dfbaa")
preq = H("01010000100707"); pres = H("02030000080005")
assert p1(pres, preq, 0, 1) == H("05000800000302070710000001010001")
assert p2(H("A6A5A4A3A2A1"), H("B6B5B4B3B2B1")) == H("00000000A1A2A3A4A5A6B1B2B3B4B5B6")
Z16 = bytes(16)
assert c1(Z16, H("5783D52156AD6F0E6388274EC6702EE0"), p1(pres, preq, 0, 1), p2(H("A6A5A4A3A2A1"), H("B6B5B4B3B2B1"))) == H("1E1E3FEF878988EAD2A74DC5BEF13B86")
assert s1(Z16, H("000F0E0D0C0B0A091122334455667788"), H("010203040506070899AABBCCDDEEFF00")) == H("9A1FE1F0E8B0F49B5B4216AE796DA062")

random.seed(2026)
rb = lambda n: bytes(random.randrange(256) for _ in range(n))
rows = {k: [] for k in ["cmac", "aes", "c1", "s1", "ah", "f4", "f5", "f6", "g2", "h6", "h7", "p1", "p2"]}
for _ in range(25):
    k, r, a, b = rb(16), rb(16), rb(16), rb(16)
    rows["c1"].append((k, r, a, b, c1(k, r, a, b)))
    rows["s1"].append((k, r, a, s1(k, r, a)))
    r3 = rb(3); rows["ah"].append((k, r3, ah(k, r3)))
    u, v, x, y, z = rb(32), rb(32), rb(16), rb(16), random.choice([0, 0x80, 0x81])
    rows["f4"].append((u, v, x, bytes([z]), f4(u, v, x, z)))
    w, a1, a2 = rb(32), rb(7), rb(7)
    m, l = f5(w, x, y, a1, a2)
    rows["f5"].append((w, x, y, a1, a2, m, l))
    rr, io = rb(16), rb(3)
    rows["f6"].append((k, x, y, rr, io, a1, a2, f6(k, x, y, rr, io, a1, a2)))
    g = g2(u, v, x, y); rows["g2"].append((u, v, x, y, g.to_bytes(4, 'big')))
    kid = rb(4); rows["h6"].append((k, kid, h6(k, kid)))
    rows["h7"].append((rb(16), k, None))
    rows["h7"][-1] = (rows["h7"][-1][0], k, h7(rows["h7"][-1][0], k))
    pq, ps = rb(7), rb(7); rat, iat = random.randrange(2), random.randrange(2)
    rows["p1"].append((ps, pq, bytes([rat]), bytes([iat]), p1(ps, pq, rat, iat)))
    ia, ra = rb(6), rb(6); rows["p2"].append((ia, ra, p2(ia, ra)))

# AES-CMAC at every length around the block boundaries, and AES-128 itself
RK = H("2b7e151628aed2a6abf7158809cf4f3c")
assert aes_cmac(RK, b"") == H("bb1d6929e95937287fa37d129b756746")
assert aes_cmac(RK, H("6bc1bee22e409f96e93d7e117393172a")) == H("070a16b46b4d4144f79bdd9dd04a287c")
assert e(RK, H("3243f6a8885a308d313198a2e0370734")) == H("3925841d02dc09fbdc118597196a0b32")
assert e(bytes(range(16)), H("00112233445566778899aabbccddeeff")) == H("69c4e0d86a7b0430d8cdb78070b4c55a")
for n in list(range(0, 50)) + [63, 64, 65, 100, 127, 128, 129]:
    k, m = rb(16), rb(n)
    rows["cmac"].append((k, m, aes_cmac(k, m)))
for _ in range(25):
    k, m = rb(16), rb(16)
    rows["aes"].append((k, m, e(k, m)))

def table(name, rs):
    lines = ["fn %s_table() -> [Str]" % name, "    ["]
    for r in rs:
        lines.append("        " + ", ".join('"%s"' % c.hex() for c in r) + ",")
    lines += ["    ]", ""]
    return "\n".join(lines)
here = os.path.dirname(os.path.abspath(__file__))
body = open(os.path.join(here, 'toolbox_tests.nv.in')).read()
for k, v in rows.items():
    body += "\n" + table(k, v)
open(os.path.join(here, '..', 'smp_toolbox_tests.nv'), 'w').write(body)
print({k: len(v) for k, v in rows.items()})
