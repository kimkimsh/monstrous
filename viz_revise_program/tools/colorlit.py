#!/usr/bin/env python3
"""CSS 변수 정의와 인쇄용 흑백 말고는 hex 가 나오면 안 된다.

주석 안의 hex 는 세지 않는다 — 왜 그 값인지 적어 둔 설명까지 위반으로 신고하면
검사가 주석을 쫓아낸다.

build.sh 안에 히어독으로 있던 것을 파일로 뺐다. 같은 규칙의 Perl 판이 colorlit.pl
에 있고 build.sh 가 되는 쪽을 고른다. 고칠 일이 생기면 양쪽을 같이 고친다.
"""
import re, sys

src = open(sys.argv[1], encoding="utf-8").read()
src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)          # 주석 제거
bad = []
for i, line in enumerate(src.split("\n"), 1):
    for m in re.finditer(r"#[0-9a-fA-F]{6}\b", line):
        if re.search(r"--[a-z0-9-]+\s*:\s*" + re.escape(m.group(0)), line): continue
        if m.group(0).upper() in ("#000000", "#FFFFFF", "#999999"): continue
        bad.append(f"{i}: {line.strip()[:90]}")
for b in bad[:10]:
    print(b, file=sys.stderr)
sys.exit(1 if bad else 0)
