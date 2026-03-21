import pathlib
import struct

p = pathlib.Path(r"C:\Users\zycie\AppData\Roaming\MKLauncher\althea\Althea_dx.exe")
b = p.read_bytes()

needle = b"unable to decrypt file: %s"
foff = b.find(needle)
print("file_offset:", hex(foff) if foff != -1 else foff)
if foff == -1:
    raise SystemExit(0)

pe_off = struct.unpack_from("<I", b, 0x3C)[0]
coff = pe_off + 4
num_sections = struct.unpack_from("<H", b, coff + 2)[0]
size_opt = struct.unpack_from("<H", b, coff + 16)[0]
opt_off = coff + 20
magic = struct.unpack_from("<H", b, opt_off)[0]
if magic != 0x10B:
    print("Unexpected PE magic", hex(magic))
image_base = struct.unpack_from("<I", b, opt_off + 28)[0]
sec_off = opt_off + size_opt

sections = []
for i in range(num_sections):
    o = sec_off + i * 40
    name = b[o:o+8].split(b"\x00", 1)[0].decode("latin1", "ignore")
    vsize = struct.unpack_from("<I", b, o + 8)[0]
    vaddr = struct.unpack_from("<I", b, o + 12)[0]
    raw_size = struct.unpack_from("<I", b, o + 16)[0]
    raw_ptr = struct.unpack_from("<I", b, o + 20)[0]
    sections.append((name, vaddr, vsize, raw_ptr, raw_size))

rva = None
for name, vaddr, vsize, raw_ptr, raw_size in sections:
    if raw_ptr <= foff < raw_ptr + raw_size:
        rva = vaddr + (foff - raw_ptr)
        print(f"string in section {name}: raw=0x{raw_ptr:X} vaddr=0x{vaddr:X}")
        break

if rva is None:
    print("Failed to map file offset to RVA")
    raise SystemExit(1)

va = image_base + rva
print("image_base:", hex(image_base), "rva:", hex(rva), "va:", hex(va))

# Search push imm32 and mov reg,imm32 immediate refs
imm = va.to_bytes(4, "little")
patterns = {
    b"\x68" + imm: "push imm32",
    b"\xB8" + imm: "mov eax,imm32",
    b"\xB9" + imm: "mov ecx,imm32",
    b"\xBA" + imm: "mov edx,imm32",
    b"\xBB" + imm: "mov ebx,imm32",
    b"\xBE" + imm: "mov esi,imm32",
    b"\xBF" + imm: "mov edi,imm32",
}

hits = []
for pat, desc in patterns.items():
    start = 0
    while True:
        i = b.find(pat, start)
        if i == -1:
            break
        hits.append((i, desc))
        start = i + 1

hits.sort(key=lambda x: x[0])
print("candidate immediate refs:", len(hits))
for i, desc in hits[:80]:
    print(hex(i), desc)

# Print nearby bytes for first few hits
for i, desc in hits[:8]:
    s = max(0, i - 24)
    e = min(len(b), i + 40)
    print(f"\n-- {desc} at {hex(i)} --")
    print(b[s:e].hex())
