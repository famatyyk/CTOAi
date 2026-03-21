"""Static analysis of Althea_dx.exe - ENC3 / OTCv8 signatures."""
import re, struct, sys, os

EXE = os.path.expandvars(r"%APPDATA%\MKLauncher\althea\Althea_dx.exe")

with open(EXE, "rb") as f:
    b = f.read()

def show_context(offset, before=128, after=256, label=""):
    chunk = b[max(0, offset - before): offset + after]
    out = []
    for byte in chunk:
        if 0x20 <= byte <= 0x7E:
            out.append(chr(byte))
        elif byte == 0:
            out.append("|")
        else:
            out.append(".")
    print(f"\n{'='*60}")
    print(f"  {label}  (file offset 0x{offset:08X})")
    print(f"{'='*60}")
    print("".join(out))

def null_strings(region_bytes):
    return [s.decode("ascii", "replace")
            for s in re.findall(rb"[ -~]{4,}", region_bytes)]

# ── 1. ENC3 exact hits ────────────────────────────────────────
print("\n### ENC3 HITS IN BINARY ###")
for pattern in [b"ENC3", b"enc3", b"ENC_3", b"ENCV3"]:
    hits = [i for i in range(len(b) - len(pattern))
            if b[i:i+len(pattern)] == pattern]
    if hits:
        print(f"  {pattern}: {len(hits)} hit(s) -> offsets: {[hex(h) for h in hits[:10]]}")
    else:
        print(f"  {pattern}: NOT FOUND")

# full context for ENC3
enc3_offs = [i for i in range(len(b) - 4) if b[i:i+4] == b"ENC3"]
for off in enc3_offs[:3]:
    show_context(off, label=f"ENC3")

# ── 2. Strings surrounding ENC3 region 0x905400 - 0x9059FF ──
print("\n### NULL-DELIM STRINGS @ ENC3 REGION (0x905400 - 0x905AFF) ###")
region = b[0x905400:0x905B00]
for s in null_strings(region):
    print(f"  {s}")

# ── 3. OTCv8 / otclient hits ─────────────────────────────────
print("\n### OTClient version strings ###")
for m in re.finditer(rb"[Oo][Tt][Cc]lient[^\x00]{0,60}", b):
    print(f"  0x{m.start():08X}: {m.group()[:90]}")

# full context for OTClientV8
for m in re.finditer(rb"OTClientV8", b):
    show_context(m.start(), 64, 128, label="OTClientV8")

# ── 4. File extension / format strings ───────────────────────
print("\n### FORMAT / EXTENSION STRINGS ###")
exts = [b".spr", b".dat", b".otb", b".otbm", b".otmm", b".enc",
        b"things", b"Tibia.dat", b"Tibia.spr",
        b"proto_", b"xtea", b"XTEA", b"RSA_", b"rsa_",
        b"ENC_", b"CRYPT", b"crypt"]
for pat in exts:
    hits = []
    for m in re.finditer(re.escape(pat), b, re.IGNORECASE):
        ctx = b[max(0,m.start()-30):m.start()+60]
        txt = "".join(chr(c) if 0x20<=c<=0x7E else "|" if c==0 else "." for c in ctx)
        hits.append(f"  0x{m.start():08X}: {txt}")
    if hits:
        print(f"\n[{pat}]")
        for h in hits[:5]:
            print(h)

# ── 5. Import table DLLs (quick scan for Import Directory) ───
print("\n### IMPORTED DLL NAMES (from IAT string scan) ###")
dll_hits = set()
for m in re.finditer(rb"[a-zA-Z0-9_]{2,30}\.dll", b):
    dll_hits.add(m.group().decode("ascii", "replace").lower())
for dll in sorted(dll_hits):
    print(f"  {dll}")

# ── 6. Build info / version resource ─────────────────────────
print("\n### BUILD / VERSION STRINGS ###")
for kw in [b"FileVersion", b"ProductVersion", b"CompanyName",
           b"LegalCopyright", b"OriginalFilename"]:
    for m in re.finditer(kw, b):
        ctx = b[m.start():m.start()+80]
        txt = "".join(chr(c) if 0x20<=c<=0x7E else "|" if c==0 else "." for c in ctx)
        print(f"  0x{m.start():08X}: {txt}")
        break  # first hit only per keyword

# ── 7. Source paths ──────────────────────────────────────────
print("\n### SOURCE PATHS (C:\\...\\src\\...) ###")
seen = set()
for m in re.finditer(rb"[Cc]:\\[a-zA-Z0-9_.\\/ -]{8,120}", b):
    s = m.group().decode("ascii", "replace")
    if ("althea" in s.lower() or "otc" in s.lower() or ".cpp" in s or
            ".h" in s or ".c" in s) and s not in seen:
        seen.add(s)
        print(f"  0x{m.start():08X}: {s[:130]}")

print("\n[done]")
