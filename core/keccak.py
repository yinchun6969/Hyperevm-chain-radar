# Pure-Python Ethereum Keccak-256. No eth-utils/pydantic/Rust dependency.
_RC=[
0x0000000000000001,0x0000000000008082,0x800000000000808A,0x8000000080008000,
0x000000000000808B,0x0000000080000001,0x8000000080008081,0x8000000000008009,
0x000000000000008A,0x0000000000000088,0x0000000080008009,0x000000008000000A,
0x000000008000808B,0x800000000000008B,0x8000000000008089,0x8000000000008003,
0x8000000000008002,0x8000000000000080,0x000000000000800A,0x800000008000000A,
0x8000000080008081,0x8000000000008080,0x0000000080000001,0x8000000080008008]
_ROT=[[0,36,3,41,18],[1,44,10,45,2],[62,6,43,15,61],[28,55,25,21,56],[27,20,39,8,14]]
_M=(1<<64)-1
def _rol(v,n): return v&_M if not n else ((v<<n)|(v>>(64-n)))&_M
def _f(st):
    a=st[:]
    for rc in _RC:
        c=[a[x]^a[x+5]^a[x+10]^a[x+15]^a[x+20] for x in range(5)]
        d=[c[(x-1)%5]^_rol(c[(x+1)%5],1) for x in range(5)]
        for y in range(5):
            for x in range(5): a[x+5*y]^=d[x]
        b=[0]*25
        for y in range(5):
            for x in range(5): b[y+5*((2*x+3*y)%5)]=_rol(a[x+5*y],_ROT[x][y])
        for y in range(5):
            for x in range(5): a[x+5*y]=(b[x+5*y]^((~b[(x+1)%5+5*y])&b[(x+2)%5+5*y]))&_M
        a[0]^=rc
    return a
def keccak256(data:bytes)->bytes:
    rate=136; p=bytearray(data); p.append(0x01)
    while len(p)%rate!=rate-1:p.append(0)
    p.append(0x80); st=[0]*25
    for off in range(0,len(p),rate):
        block=p[off:off+rate]
        for i in range(rate//8): st[i]^=int.from_bytes(block[i*8:(i+1)*8],'little')
        st=_f(st)
    out=bytearray()
    while len(out)<32:
        for i in range(rate//8):
            out.extend(st[i].to_bytes(8,'little'))
            if len(out)>=32: break
        if len(out)<32: st=_f(st)
    return bytes(out[:32])
def topic(signature:str)->str: return '0x'+keccak256(signature.encode()).hex()
