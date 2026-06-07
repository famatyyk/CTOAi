import json
import math
import zlib
from pathlib import Path

D = Path('artifacts/enc3/io_dense_dumps')
OUT_JSON = Path('artifacts/enc3/kingsvale-io-dense-triage.json')
OUT_MD = Path('artifacts/enc3/kingsvale-io-dense-triage.md')


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    cnt=[0]*256
    for b in data: cnt[b]+=1
    n=float(len(data)); h=0.0
    for c in cnt:
        if c:
            p=c/n; h-=p*math.log2(p)
    return h


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    p=sum(1 for b in data if 32<=b<=126 or b in (9,10,13))
    return p/len(data)


def magics(data: bytes):
    sig=[('MZ',b'MZ'),('PK',b'PK\x03\x04'),('ENC3',b'ENC3'),('GZIP',b'\x1f\x8b\x08'),('ZLIB_78',b'\x78')]
    out=[]
    for n,s in sig:
        p=data.find(s)
        if p!=-1: out.append({'name':n,'offset':p})
    return out


def decomp_hints(data: bytes):
    res=[]
    for m,w in [('zlib',None),('zlib_raw',-15),('zlib_gzip',31)]:
        try:
            d = zlib.decompress(data) if w is None else zlib.decompress(data,wbits=w)
            res.append({'method':m,'ok':True,'out_len':len(d),'out_magic':magics(d[:65536])})
        except Exception:
            pass
    return res

rows=[]
for p in sorted(D.glob('*.bin')):
    b=p.read_bytes()
    m=magics(b[:65536])
    h=entropy(b)
    pr=printable_ratio(b)
    hints=decomp_hints(b)
    score=0
    if m: score+=35
    if 4.5<=h<=7.8: score+=20
    elif h>7.8: score+=10
    if pr>0.05: score+=10
    if len(b)>2048: score+=10
    if hints: score+=20
    rows.append({
        'file':str(p).replace('\\','/'),
        'size':len(b),
        'entropy':round(h,4),
        'printable_ratio':round(pr,4),
        'magic':m,
        'decomp_hits':hints,
        'score':score,
    })

rows.sort(key=lambda x:(x['score'],x['size']), reverse=True)
out={'count':len(rows),'top':rows[:20],'all':rows}
OUT_JSON.write_text(json.dumps(out,indent=2),encoding='utf-8')

md=['# IO Dense Triage','',f"- Count: {len(rows)}",'', '## Top 10']
for r in rows[:10]:
    mg=', '.join(f"{m['name']}@{m['offset']}" for m in r['magic']) or 'none'
    dh='; '.join(f"{d['method']}:{d['out_len']}" for d in r['decomp_hits']) or 'none'
    md.append(f"- score={r['score']} size={r['size']} ent={r['entropy']} magic={mg} decomp={dh} -> {r['file']}")
OUT_MD.write_text('\n'.join(md),encoding='utf-8')
print(json.dumps({'count':len(rows),'json':str(OUT_JSON).replace('\\','/'),'md':str(OUT_MD).replace('\\','/'),'top':rows[:5]},indent=2))
