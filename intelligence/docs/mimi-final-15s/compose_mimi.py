"""Local deterministic compositing of approved Mimi movement plates; no provider calls."""
from pathlib import Path
import cv2
import numpy as np
import subprocess
import math

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'mimi-sticky-first-frame'
W,H=540,960
S=W/360

def read_frames(path):
    cap=cv2.VideoCapture(str(path));out=[]
    while True:
        ok,f=cap.read()
        if not ok:break
        out.append(cv2.resize(f,(W,H),interpolation=cv2.INTER_CUBIC))
    cap.release();return out

# All coordinates below use the actual 360x640 inspection frame grid.
KEYS={
1:[
(0,(85,470,76,72,0),(273,455,59,66,-12)),
(.5,(85,472,76,72,0),(277,454,59,66,-12)),
(1,(60,535,55,60,-15),(324,400,42,65,0)),
(1.5,(60,540,55,60,-12),(327,408,42,65,0)),
(2,(65,550,55,60,-10),(329,465,42,65,0)),
(2.5,(65,550,55,60,-5),(329,475,42,65,0)),
(3,(75,550,57,62,-7),(327,490,45,65,0)),
(3.5,(75,515,64,67,-10),(282,490,56,64,6)),
(4,(65,500,64,67,-15),(278,470,58,65,10))],
2:[
(0,(65,500,64,67,-15),(278,470,58,65,10)),
(.5,(75,510,64,62,-10),(280,493,64,62,8)),
(1,(77,500,62,62,-8),(280,490,64,62,10)),
(1.5,(78,505,63,64,-10),(285,491,64,62,8)),
(2,(68,530,64,60,-25),(284,527,62,60,15)),
(2.5,(60,550,62,57,-25),(283,530,58,55,20)),
(3,(65,555,60,55,-35),(280,540,58,53,25)),
(4,(60,530,60,54,-35),(276,515,58,53,25))],
3:[
(0,(60,530,60,54,-35),(276,515,58,53,25)),
(.5,(70,540,62,60,-15),(280,510,60,60,15)),
(1,(80,520,66,64,-5),(280,500,64,63,10)),
(1.5,(80,520,66,64,-5),(282,505,64,63,10)),
(2,(80,530,65,64,-5),(285,525,64,62,12)),
(2.5,(80,550,64,62,-8),(285,540,63,61,12)),
(3,(90,570,63,60,-12),(282,565,62,60,15)),
(4,(88,570,63,60,-12),(280,565,62,60,15))],
4:[
(0,(88,570,63,60,-12),(280,565,62,60,15)),
(.5,(88,570,63,60,-12),(280,565,62,60,15)),
(1,(100,550,63,60,-10),(290,545,61,59,15)),
(1.5,(100,500,64,60,-10),(280,490,62,60,10)),
(2,(110,585,62,60,-8),(305,570,60,58,15)),
(2.5,(110,585,62,60,-8),(307,570,60,58,15)),
(3,(115,600,61,59,-5),(300,570,60,58,15)),
(4,(100,590,61,59,-5),(300,555,60,58,15))]}

def interp(k,t,side):
    arr=KEYS[k];times=[x[0] for x in arr]
    return np.array([np.interp(t,times,[x[side][i] for x in arr]) for i in range(5)],float)

# Rectify the actual approved original note's textured surface, not a flat color rectangle.
a=cv2.imread(str(OLD/'mimi-snap-state-a.png'))
src=np.float32([[137,1215],[342,1221],[353,1420],[136,1415]])
target=np.float32([[0,0],[255,0],[255,255],[0,255]])
TEX=cv2.warpPerspective(a,cv2.getPerspectiveTransform(src,target),(256,256))
# Small rendered border and contact shadow give a flush attachment on the real surface.
def quad(spec):
    x,y,w,h,angle=spec
    q=np.array([[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]],float)
    r=math.radians(angle);rot=np.array([[math.cos(r),-math.sin(r)],[math.sin(r),math.cos(r)]])
    return np.float32((q@rot.T+[x,y])*S)

def paper(frame,spec,occlusion=None,shadow=True):
    q=quad(spec)
    M=cv2.getPerspectiveTransform(target,q)
    art=cv2.warpPerspective(TEX,M,(W,H),flags=cv2.INTER_CUBIC)
    alpha=cv2.warpPerspective(np.full((256,256),255,np.uint8),M,(W,H)).astype(float)/255
    if occlusion is not None:alpha*=1-occlusion
    if shadow:
        sh=cv2.GaussianBlur(alpha,(0,0),1.2*S)
        sh=cv2.warpAffine(sh,np.float32([[1,0,1.5*S],[0,1,2*S]]),(W,H))*.27
        frame=frame.astype(float)*(1-sh[...,None])
    return np.uint8(np.clip(frame*(1-alpha[...,None])+art*alpha[...,None],0,255))

# Fixed wooden-panel notes; they remain attached while Mimi moves in front.
CAB=[(329,105,57,60,-6),(330,242,56,59,7),(330,385,57,59,-8),(330,535,57,59,8)]
SHIRT=[(142,589,58,60,-9),(226,590,58,60,8)]
FINAL=[(329+(i%2)*2,62+i*75,54,57,[-8,11,-12,15,-4,9,-10,5][i]) for i in range(8)]

clips={i:read_frames(ROOT/f'movement-{i}.mp4') for i in range(1,5)}
proof=read_frames(OLD/'mimi-snap-proof.mp4')
assert len(proof)==60

# Strong skin occlusion uses only actual clean movement pixels, never generated paper masks.
def skin(frame):
    b,g,r=cv2.split(frame.astype(float))
    m=np.uint8(((b-r)>22)&((b-g)>3))*255
    return cv2.GaussianBlur(m,(3,3),0).astype(float)/255

output=ROOT/'mimi-final-15s.mp4'
enc=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r','30','-i','pipe:0','-an','-c:v','libx264','-crf','16','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
for n in range(450):
    t=n/30
    if n<60:
        frame=proof[n]
    else:
        k=1 if t<5 else 2 if t<8 else 3 if t<11 else 4
        base={1:2,2:5,3:8,4:11}[k];dur=3 if k<4 else 4
        local=(t-base)*4/dur
        source=clips[k];idx=min(len(source)-1,round(local/4*(len(source)-1)))
        frame=source[idx].copy();occ=skin(frame)
        R=interp(k,local,1);L=interp(k,local,2)
        count=2 if t<3.1 else 4 if t<6 else 8
        # Stable IDs: original two paws, then two cabinet notes; four new whole sheets at 6s.
        notes=[R,L]+CAB[:2]
        if count==8:notes=[R,L]+CAB[:2]+SHIRT+CAB[2:]
        else:notes=notes[:count]
        launch=13.05
        if t>=launch:
            # Track each existing note ID along one deterministic flight, with no duplication.
            u=min(1,(t-launch)/.85)
            if not hasattr(paper,'launch_notes'):
                paper.launch_notes=[x.copy() if hasattr(x,'copy') else x for x in notes]
            for j,start in enumerate(paper.launch_notes):
                dest=np.array(FINAL[j],float);start=np.array(start,float)
                ease=u*u*(3-2*u);spec=start*(1-ease)+dest*ease
                spec[1]-=(45+8*j)*math.sin(math.pi*u)
                spec[0]+=(-1 if j%2==0 else 1)*(12+j*2)*math.sin(math.pi*u)
                spec[4]+=(-1 if j%2==0 else 1)*(15+j*3)*math.sin(math.pi*u)
                frame=paper(frame,spec,occlusion=occ if u>=.98 else None,shadow=u>=.98)
        else:
            # Cabinet/shirt layers sit behind real foreground fur; palm sheets sit on the paws.
            for j,spec in enumerate(notes):
                if j>=2:frame=paper(frame,spec,occlusion=occ)
            frame=paper(frame,R);frame=paper(frame,L)
    enc.stdin.write(frame.tobytes())
enc.stdin.close();assert enc.wait()==0
print(output)
