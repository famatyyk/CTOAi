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


def rva_to_file(rva: int) -> int | None:
    for _, vaddr, vsize, raw_ptr, raw_size in sections:
        size = max(vsize, raw_size)
        if vaddr <= rva < vaddr + size:
            return raw_ptr + (rva - vaddr)
    return None


def file_to_rva(foff: int) -> int | None:
    for _, vaddr, _, raw_ptr, raw_size in sections:
        if raw_ptr <= foff < raw_ptr + raw_size:
            return vaddr + (foff - raw_ptr)
    return None


def va_to_file(va: int) -> int | None:
    return rva_to_file(va - image_base)


def in_text(va: int) -> bool:
    text = next((x for x in sections if x[0] == '.text'), None)
    if not text:
        return False
    _, vaddr, vsize, _, raw_size = text
    size = max(vsize, raw_size)
    rva = va - image_base
    return vaddr <= rva < vaddr + size

anchor_va = 0x005EC61D
anchor_foff = va_to_file(anchor_va)
if anchor_foff is None:
    raise SystemExit("anchor not mappable")

# Find likely function start by scanning backward for prologue and no RET in short window.
scan_start = max(0, anchor_foff - 0x1200)
region = b[scan_start:anchor_foff]
pro = b"\x55\x8B\xEC"
ret_ops = {0xC3, 0xC2, 0xCB, 0xCA}
best = None
for i in range(len(region) - 2):
    if region[i:i+3] == pro:
        cand = scan_start + i
        tail = b[cand:anchor_foff]
        if not any(x in ret_ops for x in tail[-64:]):
            best = cand

if best is None:
    best = region.rfind(pro)
    if best == -1:
        raise SystemExit("no prologue found")
    best = scan_start + best

func_start_foff = best
func_start_va = image_base + file_to_rva(func_start_foff)

# Disassemble forward until first RET after anchor + reasonable range
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

max_len = 0x1800
code = b[func_start_foff:func_start_foff + max_len]
ret_va = None
insns = []
for ins in md.disasm(code, func_start_va):
    insns.append(ins)
    if ins.address > anchor_va and ins.mnemonic == 'ret':
        ret_va = ins.address
        break

print(f"FUNC_START_VA=0x{func_start_va:08X}")
print(f"ANCHOR_VA=0x{anchor_va:08X}")
print(f"FUNC_END_VA={f'0x{ret_va:08X}' if ret_va else 'unknown'}")
print(f"INSN_COUNT={len(insns)}")

# Print window around anchor
print("\n=== WINDOW AROUND ANCHOR ===")
for ins in insns:
    if anchor_va - 0x50 <= ins.address <= anchor_va + 0x90:
        print(f"0x{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}")

# Collect direct calls in this window
calls = []
for ins in insns:
    if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
        try:
            dst = int(ins.op_str, 16)
        except ValueError:
            continue
        calls.append((ins.address, dst))

uniq = []
seen = set()
for a, d in calls:
    if d not in seen:
        seen.add(d)
        uniq.append((a, d))

print("\n=== UNIQUE DIRECT CALL TARGETS IN FUNCTION (first 40) ===")
for a, d in uniq[:40]:
    print(f"0x{a:08X} -> 0x{d:08X}")

# For targets of interest, show xref count from push/call search
targets = [0x00462E50, 0x004810D0, 0x00460F20]
print("\n=== TARGET XREF COUNTS (direct rel32 calls) ===")
for t in targets:
    # call rel32 encoding: E8 <rel32>
    # brute force by disasm over .text and counting exact dst
    text = next((x for x in sections if x[0] == '.text'), None)
    if not text:
        continue
    _, tvaddr, _, traw, traw_size = text
    tva = image_base + tvaddr
    tcode = b[traw:traw + traw_size]
    cnt = 0
    first = []
    for ins in md.disasm(tcode, tva):
        if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
            try:
                d = int(ins.op_str, 16)
            except ValueError:
                continue
            if d == t:
                cnt += 1
                if len(first) < 5:
                    first.append(ins.address)
    print(f"0x{t:08X}: count={cnt}, sample={', '.join(f'0x{x:08X}' for x in first)}")

# Try to locate nearby logging strings by scanning for immediate pushes of .rdata addresses near calls
print("\n=== POSSIBLE LOG STRING PUSHES NEAR TARGET CALLS IN WINDOW ===")
for ins in insns:
    if anchor_va - 0x80 <= ins.address <= anchor_va + 0xA0 and ins.mnemonic == 'push' and ins.op_str.startswith('0x'):
        try:
            v = int(ins.op_str, 16)
        except ValueError:
            continue
        if not in_text(v):
            f = va_to_file(v)
            if f is not None and 0 <= f < len(b):
                s = b[f:f+80].split(b'\x00', 1)[0]
                if len(s) >= 4 and all(32 <= c < 127 for c in s):
                    print(f"0x{ins.address:08X}: push 0x{v:08X} -> {s.decode('latin1', 'ignore')}")
