import json
import math
import zlib
from pathlib import Path

INP = Path('artifacts/enc3/kingsvale-io-dense-assembled-by-time.bin')
OUT_DIR = Path('artifacts/enc3/depack')
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / 'depack-io-dense-assembled-focused.json'
OUT_MD = OUT_DIR / 'depack-io-dense-assembled-focused.md'


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    c=[0]*256
    for b in data: c[b]+=1
    n=float(len(data)); h=0.0
    for x in c:
        if x:
            p=x/n; h-=p*math.log2(p)
    return h


def magic(data: bytes):
    out=[]
    for n,s in [('MZ',b'MZ'),('PK',b'PK\x03\x04'),('ENC3',b'ENC3')]:
        p=data.find(s)
        if p!=-1: out.append({'name':n,'offset':p})
    return out


def score(data: bytes):
    h=entropy(data)
    s=0
    if magic(data[:65536]): s+=35
    if 4.5<=h<=7.8: s+=20
    elif h>7.8: s+=10
    if len(data)>2048: s+=10
    return s, round(h,4)

if not INP.exists():
    raise SystemExit('missing input stream')

data = INP.read_bytes()

# Focus on discovered signatures and nearby neighborhoods
base = {0}
for sig in (b'\x78\x01', b'\x78\x9c', b'\x78\xda', b'MZ', b'PK\x03\x04'):
    pos = data.find(sig)
    if pos != -1:
        for d in (-256,-128,-64,-32,-16,-8,0,8,16,32,64,128,256):
            o = pos + d
            if 0 <= o < len(data)-8:
                base.add(o)

offsets = sorted(base)
transforms = [('id',0),('xor_ff',0xFF),('xor_20',0x20)]

hits=[]
for off in offsets:
    src = data[off:]
    for tname,k in transforms:
        payload = src if k==0 else bytes(b ^ k for b in src)
        for method,w in [('zlib',None),('zlib_raw',-15),('zlib_gzip',31)]:
            try:
                dec = zlib.decompress(payload) if w is None else zlib.decompress(payload,wbits=w)
            except zlib.error:
                continue
            if not dec:
                continue
            sc, ent = score(dec)
            fp = OUT_DIR / f"io-assembled-focused-off{off:06d}-{tname}-{method}.bin"
            fp.write_bytes(dec)
            hits.append({'offset':off,'transform':tname,'method':method,'out_size':len(dec),'score':sc,'entropy':ent,'magic':magic(dec[:65536]),'file':str(fp).replace('\\','/')})

hits.sort(key=lambda x:(x['score'],x['out_size']), reverse=True)
summary = {
    'input': str(INP).replace('\\','/'),
    'input_size': len(data),
    'offset_count': len(offsets),
    'transform_count': len(transforms),
    'hits': len(hits),
    'top': hits[:20],
}
OUT_JSON.write_text(json.dumps(summary, indent=2), encoding='utf-8')

md=['# Assembled Focused Depack','',f"- Input: {summary['input']}",f"- Input size: {summary['input_size']}",f"- Offsets: {summary['offset_count']}",f"- Hits: {summary['hits']}",'','## Top']
for h in summary['top'][:10]:
    mg=', '.join(f"{m['name']}@{m['offset']}" for m in h.get('magic',[])) or 'none'
    md.append(f"- score={h['score']} size={h['out_size']} off={h['offset']} tr={h['transform']} m={h['method']} ent={h['entropy']} magic={mg} -> {h['file']}")
OUT_MD.write_text('\n'.join(md), encoding='utf-8')

print(json.dumps({'json':str(OUT_JSON).replace('\\','/'),'md':str(OUT_MD).replace('\\','/'),'hits':summary['hits'],'top1':summary['top'][0] if summary['top'] else None}, indent=2))
