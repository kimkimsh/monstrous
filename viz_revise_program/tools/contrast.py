#!/usr/bin/env python3
"""CSS 변수 블록에서 색을 뽑아 텍스트 토큰 x 배경 토큰 명암비를 검사한다.

첫 초안에는 조용한 구멍이 둘 있었다.
  1) 색 정규식이 6자리 hex 만 받아서 `--bg:#000` 을 못 읽었다. 그러면 고대비 블록에
     `--bg` 가 없는 것으로 보이고 continue 로 건너뛴다 — 7:1 하한이 한 번도
     검사되지 않는다. 3자리를 받아 6자리로 펴서 해결했다.
  2) 블록이 PAIRS 에 필요한 토큰을 빠뜨려도 그냥 지나갔다. 이제는 그것 자체를
     실패로 본다. 고대비 블록이 --ink 를 선언하지 않던 상태가 여기 걸린다.

한계: 같은 블록 안에 함께 정의된 변수만 본다. 상속을 따라가지 않는다. 그래서 각 테마
블록이 PAIRS 에 필요한 토큰을 전부 다시 선언해야 하고, 안 하면 그것을 실패로 보고한다.
"""
import re, sys

PAIRS = [("--fg","--bg"),("--fg","--panel"),("--fg","--panel-2"),
         ("--fg-dim","--bg"),("--fg-dim","--panel"),("--fg-dim","--panel-2"),
         ("--fg-faint","--bg"),("--fg-faint","--panel"),("--fg-faint","--panel-2"),
         ("--ember","--bg"),("--gold","--bg"),("--lime","--bg"),
         ("--coral","--bg"),("--magenta","--bg"),("--plum","--bg"),
         ("--ember","--panel-2"),("--gold","--panel-2"),("--lime","--panel-2"),
         ("--coral","--panel-2"),("--magenta","--panel-2"),("--plum","--panel-2"),
         ("--ink","--ember"),("--ink","--gold"),("--ink","--lime"),
         ("--ink","--coral"),("--ink","--magenta"),("--ink","--plum"),
         ("--ink","--fg-faint")]          # 판정 보류 도장 = --v-hold 배경 위의 잉크
MIN = 4.5
HEX = re.compile(r"(--[\w-]+)\s*:\s*#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")

def norm(h):
    return "".join(c*2 for c in h) if len(h) == 3 else h

def lin(c):
    c /= 255
    return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4

def lum(h):
    h = norm(h)
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126*lin(r) + 0.7152*lin(g) + 0.0722*lin(b)

def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi+0.05) / (lo+0.05)

src = open(sys.argv[1], encoding="utf-8").read()
bad = 0
seen = 0
for m in re.finditer(r"(:root|html\[[^\]]+\](?:\[[^\]]+\])?)[^{]*\{([^}]*)\}", src):
    scope, body = m.group(1), m.group(2)
    vals = dict(HEX.findall(body))
    if "--bg" not in vals:
        continue                       # 색을 정의하지 않는 블록 (레이아웃 규칙 등)
    seen += 1
    floor = 7.0 if "contrast" in scope else MIN
    need = {k for pair in PAIRS for k in pair}
    missing = sorted(need - set(vals))
    if missing:
        print(f"{scope}: 토큰 누락 {missing} — 이 블록에서 다시 선언할 것")
        bad += len(missing)
    for fg, bgk in PAIRS:
        if fg in vals and bgk in vals:
            r = ratio(vals[fg], vals[bgk])
            if r < floor:
                print(f"{scope}: {fg} on {bgk} = {r:.2f} (< {floor})")
                bad += 1
if seen == 0:
    print("색 블록을 하나도 못 찾았다 — 정규식이나 토큰 블록을 확인할 것")
    sys.exit(1)
print(f"검사한 블록 {seen}개, 위반 {bad}건")
sys.exit(1 if bad else 0)
