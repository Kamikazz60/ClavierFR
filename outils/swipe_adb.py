"""Génère une commande adb shell qui trace un mot en polyligne sur le clavier AZERTY du Pixel (1080x2400). Usage : python swipe_adb.py vent"""
import sys
K={}
for i,c in enumerate("azertyuiop"): K[c]=(58+107*i,1705)
for i,c in enumerate("qsdfghjklm"): K[c]=(58+107*i,1862)
for i,c in enumerate("wxcvbn"): K[c]=(218+107*i,2020)
w=sys.argv[1]; pts=[K[w[0]]]
for a,b in zip(w,w[1:]):
    if a==b: continue
    (x0,y0),(x1,y1)=K[a],K[b]
    for k in range(1,7): pts.append((x0+(x1-x0)*k//6,y0+(y1-y0)*k//6))
cmd=[f"input motionevent DOWN {pts[0][0]} {pts[0][1]}"]
cmd+=[f"input motionevent MOVE {x} {y}" for x,y in pts[1:]]
cmd.append(f"input motionevent UP {pts[-1][0]} {pts[-1][1]}")
print("; ".join(cmd))
