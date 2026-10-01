"""Terrarium 고도 타일 -> 경기만 범위의 음영기복 배경 이미지 + 육지 마스크.
출력: relief.jpg (위경도 선형 격자), mask.b64 (NX x NY 비트, 1=육지), preview.png
"""
import math, glob, base64, json, sys
import numpy as np
from PIL import Image, ImageFilter

LON0,LON1,LAT0,LAT1=125.95,126.95,37.10,37.92
Z=12; X0,X1,Y0,Y1=3481,3492,1581,1592
N=2**Z
# 모자이크 (웹 메르카토르 픽셀 격자)
rows=[]
for y in range(Y0,Y1+1):
    r=[]
    for x in range(X0,X1+1):
        a=np.asarray(Image.open(f'tiles/t_{Z}_{x}_{y}.png').convert('RGB')).astype(np.float32)
        r.append(a[...,0]*256+a[...,1]+a[...,2]/256-32768)
    rows.append(np.hstack(r))
H=np.vstack(rows)                    # (12*256, 12*256)
def merc_px(lon,lat):
    px=(lon+180)/360*N*256 - X0*256
    la=math.radians(lat)
    py=(1-math.log(math.tan(la)+1/math.cos(la))/math.pi)/2*N*256 - Y0*256
    return px,py
# 위경도 선형 출력 격자
KX=111.32*math.cos(math.radians((LAT0+LAT1)/2)); KY=111.32
Wkm=(LON1-LON0)*KX; Hkm=(LAT1-LAT0)*KY
OW=int(sys.argv[1]) if len(sys.argv)>1 else 1600
OH=int(round(OW*Hkm/Wkm))
lons=LON0+(np.arange(OW)+0.5)/OW*(LON1-LON0)
lats=LAT1-(np.arange(OH)+0.5)/OH*(LAT1-LAT0)
pxs=np.array([merc_px(l,LAT0)[0] for l in lons]); pys=np.array([merc_px(LON0,l)[1] for l in lats])
# 쌍선형 보간
xi=np.clip(pxs,0,H.shape[1]-1.001); yi=np.clip(pys,0,H.shape[0]-1.001)
x0=np.floor(xi).astype(int); y0=np.floor(yi).astype(int); fx=xi-x0; fy=yi-y0
E=(H[np.ix_(y0,x0)]*(1-fy)[:,None]*(1-fx)[None,:]+H[np.ix_(y0,x0+1)]*(1-fy)[:,None]*fx[None,:]
   +H[np.ix_(y0+1,x0)]*fy[:,None]*(1-fx)[None,:]+H[np.ix_(y0+1,x0+1)]*fy[:,None]*fx[None,:])
print('E shape',E.shape,'min',E.min(),'max',E.max())
sea=E<=0.5
print('sea frac',sea.mean(),'sea depth pct',np.percentile(E[sea],[1,5,25,50,75,95]))
np.save('E.npy',E)
