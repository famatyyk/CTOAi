"""Analyze ENC3 header structure across multiple files."""
import os, struct, re

base = os.path.expandvars(r"%APPDATA%\MKLauncher\althea")
samples = []

for root, dirs, files in os.walk(base):
    for fn in files:
        path = os.path.join(root, fn)
        try:
            with open(path, "rb") as f:
                b = f.read()
            if b[:4] == b"ENC3":
                samples.append((os.path.relpath(path, base), len(b), b[:32]))
        except:
            pass
    if len(samples) >= 20:
        break

print("=== ENC3 HEADER DUMP (first 20 files) ===")
print(f"{'File':<55} {'[4:8]':<10} {'[8:12]':<10} {'[12:16]LE':<12} {'[16:20]LE':<12} {'[20:24]':<10} {'TotalSz'}")
for name, sz, h in samples:
    def hex4(off): return h[off:off+4].hex()
    def u32(off): return struct.unpack_from("<I", h, off)[0]
    print(f"{name:<55} {hex4(4):<10} {hex4(8):<10} {u32(12):<12} {u32(16):<12} {hex4(20):<10} {sz}")

# Hypothesis 1: header=24, field[12:16] = payload length = filesize - 24
print()
print("=== HYPOTHESIS: 24-byte header, field[12:16] == filesize - 24 ===")
ok = sum(1 for name, sz, h in samples if struct.unpack_from("<I", h, 12)[0] == sz - 24)
print(f"Match: {ok}/{len(samples)}")

# Hypothesis 2: header=16, field[12:16] = payload length = filesize - 16
ok2 = sum(1 for name, sz, h in samples if struct.unpack_from("<I", h, 12)[0] == sz - 16)
print(f"Match (16-byte header): {ok2}/{len(samples)}")

# Hypothesis 3: field[12:16] is original unencrypted size
# Check if field[8:12] == field[20:24] (repeated CRC?)
print()
print("=== field[8:12] == field[20:24] (repeated checksum?) ===")
match_crc = sum(1 for name, sz, h in samples if h[8:12] == h[20:24])
print(f"Repeated: {match_crc}/{len(samples)}")

# Check alignment of (filesize - header) for XTEA (8-byte blocks)
print()
print("=== XTEA block check: (filesize - headerN) % 8 ===")
for hdr_sz in [4, 8, 12, 16, 20, 24]:
    aligned = sum(1 for name, sz, h in samples if (sz - hdr_sz) % 8 == 0)
    print(f"  header={hdr_sz}: {aligned}/{len(samples)} payload divisible by 8")
