import numpy as np, math, base64, json
from PIL import Image
from scipy import ndimage
E=np.load('E.npy'); OH,OW=E.shape
E=np.where(E<-50,0,E)                 # 데이터 구멍 제거
land=E>0.5
# 작은 노이즈 섬/구멍 정리
land=ndimage.binary_opening(land,iterations=1); land=ndimage.binary_closing(land,iterations=1)
# 육지로부터의 거리(픽셀) -> 가상 수심
KX=111.32*math.cos(math.radians(37.51)); Wkm=1.0*KX; kmpp=Wkm/OW
dist=ndimage.distance_transform_edt(~land)*kmpp     # km
rng=np.random.default_rng(3)
noise=ndimage.gaussian_filter(rng.standard_normal(E.shape),6)*6
depth=np.clip(2+dist*1.8+noise,0.5,45)              # 해안 2 m -> 외해 ~45 m
# 조명: 북서쪽에서
def hillshade(z,scale,az=315,alt=45):
    gy,gx=np.gradient(z*scale)
    slope=np.arctan(np.hypot(gx,gy)); aspect=np.arctan2(-gx,gy)
    azr=math.radians(az); altr=math.radians(alt)
    hs=np.sin(altr)*np.cos(slope)+np.cos(altr)*np.sin(slope)*np.cos(azr-aspect)
    return np.clip(hs,0,1)
hs_land=hillshade(ndimage.gaussian_filter(E,1.0),1/(kmpp*1000)*1.6)
hs_sea=hillshade(-depth,1/(kmpp*1000)*25)
# 육지 색: 고도별 (갯벌·저지대 모래/농지 -> 숲 -> 암석)
e=np.clip(E,0,700)
lo=np.array([150,158,110]); mid=np.array([62,96,58]); hi=np.array([112,106,92]); top=np.array([160,152,140])
t1=np.clip(e/60,0,1)[...,None]; t2=np.clip((e-60)/300,0,1)[...,None]; t3=np.clip((e-360)/340,0,1)[...,None]
col=lo*(1-t1)+mid*t1; col=col*(1-t2)+hi*t2; col=col*(1-t3)+top*t3
tex=ndimage.gaussian_filter(rng.standard_normal(E.shape),1.2)*10      # 식생 질감
landc=np.clip(col*(0.45+0.75*hs_land[...,None])+tex[...,None],0,255)
# 바다 색: 얕은 곳 탁한 청록 -> 깊은 곳 짙은 남색 (경기만은 부유사가 많아 탁함)
d=np.clip(depth/45,0,1)[...,None]
shallow=np.array([96,146,150]); deep=np.array([18,46,82])
seac=shallow*(1-d)**1.3+deep*(1-(1-d)**1.3)
seac=np.clip(seac*(0.8+0.35*hs_sea[...,None])+ndimage.gaussian_filter(rng.standard_normal(E.shape),2.5)[...,None]*4,0,255)
# 해안선 부근 밝은 갯벌/파도 띠
shore=np.clip(1-dist/0.9,0,1)[...,None]
seac=seac*(1-shore*0.35)+np.array([150,165,150])*shore*0.35
img=np.where(land[...,None],landc,seac).astype(np.uint8)
Image.fromarray(img).save('relief.jpg',quality=82,optimize=True)
Image.fromarray(img).resize((800,int(800*OH/OW))).save('preview.png')
# 시뮬레이션 격자 마스크 (NX x NY), 1=육지
NX=400; NY=int(round(NX*OH/OW))
lm=np.asarray(Image.fromarray((land*255).astype(np.uint8)).resize((NX,NY),Image.BOX))>127
lm=lm[::-1]   # 아래(남)에서 위(북)으로, 페이지 격자(j=0이 남쪽)와 맞춤
bits=np.packbits(lm.ravel())
open('mask.json','w').write(json.dumps({'NX':NX,'NY':NY,'b64':base64.b64encode(bits.tobytes()).decode()}))
import os; print('relief.jpg',os.path.getsize('relief.jpg'),'mask',NX,NY,'land frac',lm.mean())
