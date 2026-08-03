from pathlib import Path
import heapq
import math
import numpy as np
from PIL import Image

WORK = Path(__file__).resolve().parent
G = 3.721
N = 0.0545
DX = 400.0
DT = 600.0
SOURCE = (105, 64)
NEI = ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1))


def minimax(z, source):
    h, w = z.shape
    src = source[0] * w + source[1]
    head = np.full(z.size, np.inf, np.float32)
    parent = np.full(z.size, -1, np.int32)
    head[src] = z[source]
    q = [(float(z[source]), src)]
    while q:
        lev, i = heapq.heappop(q)
        if lev > float(head[i]) + 1e-5:
            continue
        y, x = divmod(i, w)
        for oy, ox in NEI:
            yy, xx = y + oy, x + ox
            if 0 <= yy < h and 0 <= xx < w:
                j = yy * w + xx
                nl = max(lev, float(z[yy, xx]))
                if nl + 1e-5 < float(head[j]):
                    head[j] = nl
                    parent[j] = i
                    heapq.heappush(q, (nl, j))
    heads = head.reshape(z.shape)
    candidates = []
    for x in range(w):
        candidates.extend((x, (h-1)*w+x))
    for y in range(1,h-1):
        candidates.extend((y*w, y*w+w-1))
    end = min(candidates, key=lambda i: float(head[i]))
    route=[]
    i=end
    while i>=0:
        route.append(i)
        if i==src: break
        i=int(parent[i])
    route.reverse()
    return float(head[end]), np.array(route, np.int32), heads


def source_component(z, level, source):
    allowed = z < level - 0.05
    seen = np.zeros(z.shape, bool)
    stack=[source]
    seen[source]=True
    while stack:
        y,x=stack.pop()
        for oy,ox in NEI:
            yy,xx=y+oy,x+ox
            if 0<=yy<z.shape[0] and 0<=xx<z.shape[1] and allowed[yy,xx] and not seen[yy,xx]:
                seen[yy,xx]=True; stack.append((yy,xx))
    return seen


def route_setup(z):
    spill, route, _ = minimax(z, SOURCE)
    basin = source_component(z, spill, SOURCE)
    rz = z.ravel()[route]
    saddle = int(np.flatnonzero(rz >= rz.max()-0.05)[-1])
    # Start on the downstream side of the controlling crest.
    outlet_i = int(route[min(saddle+1, len(route)-1)])
    oy,ox=divmod(outlet_i,z.shape[1])
    yy,xx=np.mgrid[:z.shape[0],:z.shape[1]]
    inlet=(np.hypot(yy-oy,xx-ox)<=2.5)&(~basin)&(z<spill+12)
    if inlet.sum()<6:
        inlet=(np.hypot(yy-oy,xx-ox)<=2.5)&(~basin)
    return spill, route, basin, inlet, (oy,ox), saddle


def simulate(z, basin, inlet, q_source=100000.0, days=60, capture_days=None):
    h=np.zeros_like(z,np.float32)
    arrival=np.full(z.shape,np.inf,np.float32)
    area=DX*DX
    weights=np.where(inlet,1.0,0.0).astype(np.float32)
    weights/=weights.sum()
    active=~basin
    pairs=((0,1,DX,DX),(1,0,DX,DX),(1,1,DX*math.sqrt(2),DX/math.sqrt(2)),(1,-1,DX*math.sqrt(2),DX/math.sqrt(2)))
    frames={0:h.copy()}
    stats={0:(0.0,0.0,0.0)}
    if capture_days is None:
        capture_days=[.5,1,2,4,7,10,14,21,30,45,60]
    captures={round(d*86400/DT):d for d in capture_days}
    out_total=0.0
    steps=round(days*86400/DT)
    for step in range(1,steps+1):
        h += weights*(q_source*DT/area)
        eta=z+h
        links=[]
        outgoing=np.zeros_like(h,np.float32)
        for dy,dx,dist,width in pairs:
            if dx>=0:
                a=(slice(0,z.shape[0]-dy or None),slice(0,z.shape[1]-dx or None))
                b=(slice(dy,None),slice(dx,None))
            else:
                a=(slice(0,z.shape[0]-dy),slice(-dx,None))
                b=(slice(dy,None),slice(0,z.shape[1]+dx))
            valid=active[a]&active[b]
            de=eta[a]-eta[b]
            hf=np.maximum(np.maximum(eta[a],eta[b])-np.maximum(z[a],z[b]),0)
            slope=np.abs(de)/dist
            unit=np.where((hf>.003)&valid,(hf**(5/3))*np.sqrt(slope)/N,0)
            unit=np.minimum(unit,hf*np.sqrt(G*hf))
            rate=np.sign(de)*unit*width
            # A face may not exchange enough volume to reverse the two-cell
            # water-surface gradient within one explicit step.
            equalize=np.abs(de)*area/(2*DT)
            rate=np.sign(rate)*np.minimum(np.abs(rate),equalize)
            links.append((a,b,rate))
            outgoing[a]+=np.maximum(rate,0)
            outgoing[b]+=np.maximum(-rate,0)
        # Positivity limiter for the simultaneous eight-neighbour update.
        factor=np.minimum(1.0,np.divide(h*area*.48,DT*outgoing,out=np.ones_like(h),where=outgoing>0)).astype(np.float32)
        for a,b,rate in links:
            rate=np.where(rate>=0,rate*factor[a],rate*factor[b])
            dv=rate*DT/area
            h[a]-=dv; h[b]+=dv
        np.maximum(h,0,out=h)
        # Open boundary; removed volume is explicitly accumulated.
        edge=np.zeros_like(h,bool);edge[0]=edge[-1]=True;edge[:,0]=edge[:,-1]=True
        ev=float(h[edge].sum(dtype=np.float64)*area)
        out_total+=ev;h[edge]=0
        new_wet=(h>.015)&~np.isfinite(arrival)
        arrival[new_wet]=step*DT/86400
        if step in captures:
            day=captures[step]
            frames[day]=h.copy()
            supplied=q_source*step*DT
            stored=float(h.sum(dtype=np.float64)*area)
            stats[day]=(stored,out_total,(supplied-stored-out_total)/supplied)
        if step%720==0 or step==steps:
            supplied=q_source*step*DT; stored=float(h.sum(dtype=np.float64)*area)
            err=(supplied-stored-out_total)/supplied
            print(f'{step*DT/86400:6.1f} d max={h.max():7.2f} wet={(h>.05).sum():6d} stored={stored/1e9:7.2f} out={out_total/1e9:7.2f} err={err:.3g}')
    return frames,stats,arrival


if __name__ == '__main__':
    z=np.load(WORK/'test-2d.npz')['z']
    spill,route,basin,inlet,outlet,saddle=route_setup(z)
    print('spill',spill,'basin cells',basin.sum(),'storage km3',np.maximum(spill-z[basin],0).sum()*DX*DX/1e9)
    print('route cells',len(route),'saddle route index',saddle,'outlet',outlet,'inlet cells',inlet.sum())
    frames,stats,arrival=simulate(z,basin,inlet)
    h=frames[60]
    scale=max(1,float(np.percentile(h[h>.02],99.5)))
    q=np.where(h>.02,np.clip(np.rint(np.log1p(h)/math.log1p(scale)*255),1,255),0).astype(np.uint8)
    rgb=np.zeros((*q.shape,3),np.uint8);rgb[...,2]=q;rgb[...,1]=q//2
    rgb[basin]=(80,80,80);rgb[inlet]=(255,120,0)
    Image.fromarray(rgb).resize((1368,1100),Image.Resampling.NEAREST).save(WORK/'downstream-test.png')
    np.savez_compressed(WORK/'downstream-test.npz',z=z,basin=basin,inlet=inlet,route=route,**{f'h{str(k).replace(".","p")}':v for k,v in frames.items()})
