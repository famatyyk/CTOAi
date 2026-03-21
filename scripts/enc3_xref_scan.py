import pathlib
import struct

p = pathlib.Path(r"C:\Users\zycie\AppData\Roaming\MKLauncher\althea\Althea_dx.exe")
b = p.read_bytes()
needle = b"unable to decrypt file: %s"
off = b.find(needle)
print("needle off:", hex(off) if off != -1 else off)
if off == -1:
    raise SystemExit(0)

pe_off = struct.unpack_from("<I", b, 0x3C)[0]
opt_off = pe_off + 24
magic = struct.unpack_from("<H", b, opt_off)[0]
if magic != 0x10B:
    print("Unexpected PE magic", hex(magic))
image_base = struct.unpack_from("<I", b, opt_off + 28)[0]
str_va = image_base + off
print("image_base:", hex(image_base), "str_va:", hex(str_va))

ptr = str_va.to_bytes(4, "little")
hits = []
start = 0
while True:
    i = b.find(ptr, start)
    if i == -1:
        break
    hits.append(i)
    start = i + 1

print("raw pointer hits:", len(hits))
for h in hits[:100]:
    print(hex(h))

base = max(0, off - 180)
chunk = b[base:off + 260]
print("\nContext around decrypt string:")
print(chunk.decode("latin1", "ignore"))
