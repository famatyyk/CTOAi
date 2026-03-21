import re
import pathlib

p = pathlib.Path(r"C:\Users\zycie\AppData\Roaming\MKLauncher\althea\Althea_dx.exe")
b = p.read_bytes()

ascii_runs = re.findall(rb"[ -~]{20,}", b)
print(f"ASCII runs: {len(ascii_runs)}")

patterns = [
    b"BEGIN PUBLIC KEY",
    b"BEGIN RSA PUBLIC KEY",
    b"RSA PUBLIC KEY",
    b"-----BEGIN",
    b"setRSA",
    b"RSA",
]

for pat in patterns:
    hits = [s for s in ascii_runs if pat in s]
    if hits:
        print(f"\nPATTERN {pat.decode('latin1')} hits {len(hits)}")
        for h in hits[:10]:
            print(h[:220].decode("latin1", "ignore"))

hex_runs = []
for s in ascii_runs:
    ds = s.decode("latin1", "ignore")
    if re.fullmatch(r"[0-9A-Fa-f]{128,}", ds):
        hex_runs.append(ds)

print(f"\nLong pure-hex runs (>=128): {len(hex_runs)}")
for h in hex_runs[:20]:
    print(f"len={len(h)} prefix={h[:64]}")
