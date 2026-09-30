#!/usr/bin/env python3
"""usage: moj_grep.py KEY REGEX [maxchars]  -> print sentences (whitespace-normalised) of local opinion text matching REGEX"""
import sys,re,os,json
ROOT='/home/user/workspace/flb'
k=sys.argv[1]; p=f"{ROOT}/raw/moj/cap/{k[4:]}.txt" if k.startswith('cap:') else f"{ROOT}/raw/moj/text/{k[3:]}.txt"
t=re.sub(r'\s+',' ',open(p,errors='ignore').read())
for m in re.finditer(sys.argv[2],t,re.I):
    a=t.rfind('. ',0,m.start()); b=t.find('. ',m.end())
    print('>>',t[a+2:b+1][:int(sys.argv[3]) if len(sys.argv)>3 else 600])
