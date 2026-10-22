import struct, sys, zlib

class TC:
    def __init__(s, b, p=0): s.b=b; s.p=p
    def byte(s): v=s.b[s.p]; s.p+=1; return v
    def varint(s):
        r=0; sh=0
        while True:
            c=s.byte(); r|=(c&0x7f)<<sh; sh+=7
            if not c&0x80: return r
    def zz(s):
        n=s.varint(); return (n>>1)^-(n&1)
    def val(s,t):
        if t in (1,2): return t==1
        if t==3: v=s.byte(); return v-256 if v>127 else v
        if t in (4,5,6): return s.zz()
        if t==7: v=struct.unpack('<d',s.b[s.p:s.p+8])[0]; s.p+=8; return v
        if t==8: n=s.varint(); v=bytes(s.b[s.p:s.p+n]); s.p+=n; return v
        if t in (9,10):
            h=s.byte(); n=h>>4; et=h&0xf
            if n==15: n=s.varint()
            return [s.val(et) for _ in range(n)]
        if t==11:
            n=s.varint()
            if n==0: return {}
            kv=s.byte(); return {s.val(kv>>4): s.val(kv&0xf) for _ in range(n)}
        if t==12: return s.struct()
        raise ValueError(t)
    def struct(s):
        d={}; last=0
        while True:
            h=s.byte()
            if h==0: return d
            t=h&0xf; delta=h>>4
            fid = last+delta if delta else s.zz()
            last=fid
            d[fid]=s.val(t)

def snappy(b):
    p=0; n=0; sh=0
    while True:
        c=b[p]; p+=1; n|=(c&0x7f)<<sh; sh+=7
        if not c&0x80: break
    out=bytearray()
    while p<len(b):
        tag=b[p]; p+=1; t=tag&3
        if t==0:
            ln=tag>>2
            if ln>=60:
                k=ln-59; ln=int.from_bytes(b[p:p+k],'little'); p+=k
            ln+=1; out+=b[p:p+ln]; p+=ln; continue
        if t==1: ln=((tag>>2)&7)+4; off=((tag>>5)<<8)|b[p]; p+=1
        elif t==2: ln=(tag>>2)+1; off=int.from_bytes(b[p:p+2],'little'); p+=2
        else: ln=(tag>>2)+1; off=int.from_bytes(b[p:p+4],'little'); p+=4
        st=len(out)-off
        if off>=ln: out+=out[st:st+ln]
        else:
            for i in range(ln): out.append(out[st+i])
    return bytes(out)

def decomp(codec, data, usize):
    if codec==0: return data
    if codec==1: return snappy(data)
    if codec==2: return zlib.decompress(data, 31)
    raise NotImplementedError('codec %d'%codec)

def rle_bp(buf, bw, count):
    # RLE/bit-packed hybrid, returns list
    s=TC(buf); out=[]
    bytew=(bw+7)//8
    while len(out)<count and s.p<len(buf):
        h=s.varint()
        if h&1:
            g=h>>1; nb=g*bw; raw=buf[s.p:s.p+nb]; s.p+=nb
            v=int.from_bytes(raw,'little'); m=(1<<bw)-1
            for i in range(g*8): out.append((v>>(i*bw))&m)
        else:
            n=h>>1; v=int.from_bytes(buf[s.p:s.p+bytew],'little'); s.p+=bytew
            out.extend([v]*n)
    return out[:count]

def read(path):
    b=open(path,'rb').read()
    assert b[:4]==b'PAR1' and b[-4:]==b'PAR1'
    fl=struct.unpack('<i',b[-8:-4])[0]
    meta=TC(b, len(b)-8-fl).struct()
    schema=meta[2]; rgs=meta[4]
    leaves=[e for e in schema[1:]]
    names=[e[4].decode() for e in leaves]
    cols={n:[] for n in names}
    for rg in rgs:
        for cc in rg[1]:
            md=cc[3]
            ptype=md[1]; path_=[x.decode() for x in md[3]]; codec=md[4]
            name=path_[-1]
            leaf=[e for e in leaves if e[4].decode()==name][0]
            optional = leaf.get(3,0)==1
            start=md.get(11, md[9]) if md.get(11) else md[9]
            end=start+md[7]
            pos=start; dictv=None; vals=[]
            nv_total=md[5]
            while pos<end and len(vals)<nv_total:
                t=TC(b,pos); ph=t.struct(); hdr_end=t.p
                csize=ph[3]; usize=ph[2]; ptype_=ph[1]
                raw=b[hdr_end:hdr_end+csize]; pos=hdr_end+csize
                if ptype_==2:  # dict page
                    data=decomp(codec,raw,usize); n=ph[7][1]
                    dictv=plain(data,ptype,n)
                    continue
                if ptype_==0:
                    dh=ph[5]; n=dh[1]; enc=dh[2]
                    data=decomp(codec,raw,usize); q=0
                    if optional:
                        L=struct.unpack('<i',data[:4])[0]
                        defs=rle_bp(data[4:4+L],1,n); q=4+L
                    else: defs=[1]*n
                elif ptype_==3:
                    dh=ph[8]; n=dh[1]; enc=dh[4]; dl=dh[5]; rl=dh[6]
                    comp=dh.get(7,True)
                    lv=raw[:rl+dl]; body=raw[rl+dl:]
                    if comp and codec: body=decomp(codec,body,usize-rl-dl)
                    defs=rle_bp(lv[rl:rl+dl],1,n) if optional and dl else [1]*n
                    data=body; q=0
                else: continue
                nn=sum(defs)
                if enc in (2,8):
                    bw=data[q]; idx=rle_bp(data[q+1:],bw,nn); present=[dictv[i] for i in idx]
                else:
                    present=plain(data[q:],ptype,nn)
                it=iter(present)
                vals.extend(next(it) if d else None for d in defs)
            cols[name].extend(vals)
    return cols

def plain(data,ptype,n):
    out=[]; p=0
    if ptype==6:
        for _ in range(n):
            L=struct.unpack('<i',data[p:p+4])[0]; p+=4
            out.append(data[p:p+L].decode('utf-8')); p+=L
    elif ptype==1:
        out=list(struct.unpack('<%di'%n,data[:4*n]))
    elif ptype==2:
        out=list(struct.unpack('<%dq'%n,data[:8*n]))
    else: raise NotImplementedError(ptype)
    return out

if __name__=='__main__':
    b=open(sys.argv[1],'rb').read()
    fl=struct.unpack('<i',b[-8:-4])[0]
    meta=TC(b,len(b)-8-fl).struct()
    print('rows',meta[3]); print('schema',[(e.get(4),e.get(1),e.get(3)) for e in meta[2]])
    for rg in meta[4]:
        print('rg rows',rg[3],[ (c[3][3],c[3][1],c[3][4],c[3][2]) for c in rg[1]])
