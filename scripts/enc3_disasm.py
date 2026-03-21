import pathlib
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = pathlib.Path(r"C:\Users\zycie\AppData\Roaming\MKLauncher\althea\Althea_dx.exe")
b = EXE.read_bytes()

pe_off = struct.unpack_from("<I", b, 0x3C)[0]
coff = pe_off + 4
num_sections = struct.unpack_from("<H", b, coff + 2)[0]
size_opt = struct.unpack_from("<H", b, coff + 16)[0]
opt_off = coff + 20
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


def file_to_rva(foff: int) -> int | None:
    for _, vaddr, _, raw_ptr, raw_size in sections:
        if raw_ptr <= foff < raw_ptr + raw_size:
            return vaddr + (foff - raw_ptr)
    return None


def rva_to_file(rva: int) -> int | None:
    for _, vaddr, vsize, raw_ptr, raw_size in sections:
        size = max(vsize, raw_size)
        if vaddr <= rva < vaddr + size:
            return raw_ptr + (rva - vaddr)
    return None

needle = b"unable to decrypt file: %s"
needle_foff = b.find(needle)
if needle_foff == -1:
    print("decrypt string not found")
    raise SystemExit(1)
needle_rva = file_to_rva(needle_foff)
needle_va = image_base + needle_rva
print(f"decrypt_str file=0x{needle_foff:X} rva=0x{needle_rva:X} va=0x{needle_va:X}")

# find direct push imm32 references
imm = needle_va.to_bytes(4, "little")
pat = b"\x68" + imm
push_hits = []
start = 0
while True:
    i = b.find(pat, start)
    if i == -1:
        break
    push_hits.append(i)
    start = i + 1

print(f"push refs: {len(push_hits)}")
if not push_hits:
    raise SystemExit(0)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

for idx, hit in enumerate(push_hits[:10], 1):
    hit_rva = file_to_rva(hit)
    hit_va = image_base + hit_rva
    print(f"\n=== ref {idx}: file=0x{hit:X} rva=0x{hit_rva:X} va=0x{hit_va:X} ===")

    # Disassemble around the reference for context
    win = 0x90
    s = max(0, hit - win)
    e = min(len(b), hit + win)
    code = b[s:e]
    code_va = image_base + file_to_rva(s)

    for ins in md.disasm(code, code_va):
        if hit_va - 0x40 <= ins.address <= hit_va + 0x60:
            print(f"0x{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}")

    # find nearest previous function prologue pattern in .text region
    text = next((x for x in sections if x[0] == '.text'), None)
    if text:
        _, tvaddr, _, traw, traw_size = text
        lo = max(traw, hit - 0x300)
        chunk = b[lo:hit]
        prolog = b"\x55\x8B\xEC"
        p = chunk.rfind(prolog)
        if p != -1:
            foff = lo + p
            frva = file_to_rva(foff)
            fva = image_base + frva
            print(f"candidate function start: file=0x{foff:X} rva=0x{frva:X} va=0x{fva:X}")
