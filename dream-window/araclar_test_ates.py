import sys, json, pathlib, cv2, numpy as np
a=sys.argv[1:]; ad,etiket,cx,cy=a[0],a[1],int(a[2]),int(a[3])
sys.argv=['uret.py']+(['--4k'] if '--4k' in a else [])
sys.path.insert(0,'/home/user/Deneme-2/dream-window')
import uret
uret.DONGU=96
s=uret.Sahne(pathlib.Path('/home/user/Deneme-2/dream-window')/ad)
if "--eski" in a: s.parlak_esik=None
K=uret.K; r=1920/1672; cx=int(cx*r); cy=int(cy*r)
for n in (200,700,1500):
    f=(np.clip(s.kare(n),0,1)*255).astype(np.uint8) if s.kare(n).dtype!=np.uint8 else s.kare(n)
    x0,y0=int((cx-160)*K),int((cy-100)*K)
    c=f[max(y0,0):y0+int(200*K), max(x0,0):x0+int(320*K)]
    cv2.imwrite(f'/tmp/claude-0/-home-user-Deneme-2/36d569d3-b977-5a25-ab51-fa4671bedd90/scratchpad/{etiket}_{n}.png',cv2.resize(c,None,fx=3/K,fy=3/K))
