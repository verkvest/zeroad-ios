# Cuts App Store preview videos from the appstore-shots run.mp4 recordings (SIM_VIDEO=1): speeds segments up,
# rotates to landscape, hides the iPhone Dynamic Island strip, burns in captions, adds a silent AAC stereo track.
# Usage (in the downloaded artifact dir): python3 make-preview-video.py iphone|ipad
import subprocess, sys
FONT='/tmp/as4/LinBiolinum_RBah.ttf'
def build(dev, src, segs, W, H, out):
    # segs: (start_s, end_s, out_dur, caption, kind)
    args=['ffmpeg','-v','error','-y']
    for st,en,d,cap,kind in segs: args+=['-ss',str(st),'-to',str(en),'-i',src]
    args+=['-f','lavfi','-t',str(sum(s[2] for s in segs)),'-i','anullsrc=channel_layout=stereo:sample_rate=48000']
    fc=[]
    for i,(st,en,d,cap,kind) in enumerate(segs):
        k=(en-st)/d
        ch=f'[{i}:v]setpts=(PTS-STARTPTS)/{k:.4f},fps=30,transpose=2'
        if dev=='iphone':
            if kind=='menu':
                ch+=',crop=2708:1246:160:0'
                fc.append(ch+f',scale={W}:{H}:flags=lanczos,setsar=1[c{i}]')
            else:
                fc.append(ch+f',split[a{i}][b{i}];[b{i}]crop=136:410:166:455,hflip[s{i}];[a{i}][s{i}]overlay=30:455,scale={W}:{H}:flags=lanczos,setsar=1[c{i}]')
        else:
            fc.append(ch+f',scale={W}:{H}:flags=lanczos,setsar=1[c{i}]')
        last=f'c{i}'
        if cap:
            fs=int(H*(0.072 if dev=='iphone' else 0.052)); CY=0.115 if dev=='iphone' else 0.085; X0,XW=(0.5,0.48) if dev=='iphone' else (0.40,0.58)
            alpha=f"if(lt(t,0.4),t/0.4,if(gt(t,{d}-0.4),max(0,({d}-t)/0.4),1))"
            fc.append(f"[{last}]trim=duration={d},setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text='{cap}':fontsize={fs}:fontcolor=0xFFDE96:borderw=4:bordercolor=black@0.85:shadowx=3:shadowy=3:shadowcolor=black@0.6:x=w*{X0}+(w*{XW}-tw)/2:y=h*{CY}:alpha='{alpha}'[d{i}]")
        else:
            fc.append(f"[{last}]trim=duration={d},setpts=PTS-STARTPTS[d{i}]")
    fc.append(''.join(f'[d{i}]' for i in range(len(segs)))+f'concat=n={len(segs)}:v=1:a=0,fps=30,format=yuv420p[v]')
    args+=['-filter_complex',';'.join(fc),'-map','[v]','-map',f'{len(segs)}:a',
           '-c:v','libx264','-profile:v','high','-level','4.0','-preset','slow','-b:v','11M','-maxrate','12M','-bufsize','24M','-r','30',
           '-c:a','aac','-b:a','256k','-ar','48000','-ac','2','-shortest','-movflags','+faststart',out]
    subprocess.run(args,check=True)
dev=sys.argv[1]
if dev=='iphone':
    segs=[(5,25,3,'',  'menu'),(90,180,5,'Build your city','g'),(180,280,4,'Raise your legions','g'),(290,550,12,'Command epic battles','g'),(560,720,4,'Ancient RTS for iPhone and iPad','g')]
    build('iphone','appstore-shots-iphone/iphone/run.mp4',segs,1920,886,'/workspace/zeroad-ios/shots/appstore/preview-iphone69.mp4')
else:
    segs=[(10,50,3,'','menu'),(120,280,6,'Build your city','g'),(280,410,4,'Raise your legions','g'),(420,800,11,'Command epic battles','g'),(815,852,3,'Ancient RTS for iPhone and iPad','g')]
    build('ipad','appstore-shots-ipad/ipad/run.mp4',segs,1600,1200,'/workspace/zeroad-ios/shots/appstore/preview-ipad13.mp4')
