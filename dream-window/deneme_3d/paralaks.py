import sys, subprocess, numpy as np, cv2
D=sys.argv[1]; src=sys.argv[2]; ses=sys.argv[3]; out=sys.argv[4]
SURE=15; FPS=24; N=SURE*FPS
OW,OH=1080,1920
disp=np.load(f"{D}/d29.npy").astype(np.float32)
# kaynak 4K -> yükseklik 1920
SW=int(round(3840*OH/2160)); SH=OH
disp=cv2.resize(disp,(SW,SH),interpolation=cv2.INTER_CUBIC)
disp=cv2.GaussianBlur(disp,(0,0),2.0)
disp=np.clip(disp-np.percentile(disp,5),0,None); disp/=disp.max()
def ease(x): return 0.5-0.5*np.cos(np.pi*x)
cx0,cx1=0.40*SW,0.58*SW          # kadraj merkezi
T0,T1=-55.0,55.0                   # yakın nesnelerin ek kayması (px)
Z0,Z1=1.00,1.035                   # hafif yaklaşma (yakın nesneler daha çok büyür)
dec=subprocess.Popen(["ffmpeg","-v","error","-i",src,"-t",str(SURE),"-vf",f"scale={SW}:{SH}","-f","rawvideo","-pix_fmt","bgr24","-"],stdout=subprocess.PIPE)
enc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s",f"{OW}x{OH}","-r",str(FPS),"-i","-",
    "-ss","0","-t",str(SURE),"-i",ses,"-map","0:v","-map","1:a","-af",f"afade=t=in:d=1,afade=t=out:st={SURE-1.5}:d=1.5",
    "-c:v","libx264","-crf","19","-preset","slow","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",out],stdin=subprocess.PIPE)
u,v=np.meshgrid(np.arange(OW,dtype=np.float32),np.arange(OH,dtype=np.float32))
for i in range(N):
    f=np.frombuffer(dec.stdout.read(SW*SH*3),np.uint8)
    if f.size<SW*SH*3: break
    f=f.reshape(SH,SW,3)
    k=ease(i/(N-1))
    cx=cx0+(cx1-cx0)*k; T=T0+(T1-T0)*k; Z=Z0+(Z1-Z0)*k
    x0=cx-OW/2
    bx=(u+np.float32(x0)).astype(np.float32)
    d=cv2.remap(disp,bx,v,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    zz=1+(Z-1)*(0.3+0.7*d)          # uzak az, yakın çok büyür
    mx=(bx-cx)/zz+cx + T*d
    my=(v-SH*0.55)/zz+SH*0.55
    o=cv2.remap(f,mx.astype(np.float32),my.astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
    enc.stdin.write(o.tobytes())
enc.stdin.close(); enc.wait(); dec.wait()
print("bitti",out)
