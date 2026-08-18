#!/usr/bin/env python3
"""소리만 듣기용 HLS 주소를 갱신합니다.

CHZZK 다시보기의 HLS 주소에는 서명 토큰이 붙어 약 17시간 뒤 만료됩니다.
서버를 두지 않는 대신 이 스크립트를 12시간마다 돌립니다.

페이지 전체를 다시 굽지 않고 **주소만 담은 artifacts/hls.json 하나**를 새로 씁니다.
폰트도 썸네일도 건드리지 않으므로 GitHub Actions 러너에서 몇 초면 끝나고,
로컬 폰트가 없는 환경에서도 돌아갑니다. 페이지는 이 파일을 먼저 읽고,
없거나 실패하면 빌드 시점에 박혀 있던 주소로 되돌아갑니다.

  python scripts/refresh_hls.py --check    남은 시간만 확인
  python scripts/refresh_hls.py            필요할 때만 갱신
  python scripts/refresh_hls.py --force    무조건 갱신
"""

import argparse
import json
import pathlib
import re
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE.parent
# 작업 폴더에서는 workspace/data → artifacts/hls.json 이지만,
# 배포 저장소는 평평하다(data/sessions.json → hls.json). --data/--out 으로 맞춘다.
DATA = WORKSPACE / "data"
OUT = WORKSPACE.parent / "artifacts" / "hls.json"

# 남은 시간이 이보다 적으면 갱신합니다. 12시간 주기에서 한 번 걸러도
# 만료(약 17시간) 전에 다음 기회가 오도록 잡았습니다.
RENEW_BELOW_HOURS = 13.0


def expires_at(url):
    stamps = [int(x) for x in re.findall(r"exp=(\d+)", url or "")]
    return min(stamps) if stamps else 0


def describe(url, now=None):
    now = now or time.time()
    exp = expires_at(url)
    if not exp:
        return ("아직 받은 적 없음" if not url else "만료 시각을 읽을 수 없음"), 0.0
    left = (exp - now) / 3600
    stamp = time.strftime("%m-%d %H:%M", time.localtime(exp))
    return ("만료 %s (남음 %.1f시간)" % (stamp, left)) if left > 0 else ("만료됨 %s" % stamp), left


def chzzk_hls(video_id):
    """로그인 없이 받는 다시보기 HLS 주소.

    돌려주는 값은 (주소, 상태) 입니다. 상태는 셋 중 하나입니다.
      ""      받았다
      "gone"  영상이 치지직에서 사라졌다(404) — 다시 시도해도 소용없다
      "fail"  일시적 실패 — 다음 주기에 다시 받으면 된다

    둘을 구분하는 이유: 사라진 영상은 링크를 눌러도 죽은 페이지로 간다.
    화면에서 미리 밝혀 두려면 "못 받았다"와 "없어졌다"를 나눠야 한다.
    """
    import urllib.request
    import urllib.error

    url = "https://api.chzzk.naver.com/service/v3/videos/%s" % video_id
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Referer": "https://chzzk.naver.com/"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content = json.loads(response.read().decode("utf-8")).get("content") or {}
        raw = content.get("liveRewindPlaybackJson")
        if not raw:
            return "", "fail"
        for media in (json.loads(raw).get("media") or []):
            if media.get("protocol") == "HLS" and media.get("path"):
                return media["path"], ""
        return "", "fail"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("  ! %s 영상이 치지직에 없습니다 (404)" % video_id)
            return "", "gone"
        print("  ! %s 주소를 못 받았습니다: HTTP %d" % (video_id, exc.code))
    except Exception as exc:
        print("  ! %s 주소를 못 받았습니다: %s" % (video_id, exc))
    return "", "fail"


def chzzk_sessions():
    path = DATA / "sessions.json"
    if not path.exists():
        raise SystemExit("sessions.json 이 없습니다: %s" % path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    # 작업본은 배열, 배포본은 {"sessions": [...]} 다. 둘 다 받는다.
    rows = raw.get("sessions", []) if isinstance(raw, dict) else raw
    return [s for s in rows if s.get("platform") == "chzzk"]


def load_current():
    if not OUT.exists():
        return {}
    try:
        return json.loads(OUT.read_text(encoding="utf-8")).get("sessions", {})
    except (json.JSONDecodeError, OSError):
        return {}


def main():
    parser = argparse.ArgumentParser(description="HLS 주소만 갱신합니다.")
    parser.add_argument("--check", action="store_true", help="남은 시간만 확인합니다")
    parser.add_argument("--force", action="store_true", help="남은 시간과 무관하게 갱신합니다")
    parser.add_argument("--data", help="sessions.json 이 있는 폴더")
    parser.add_argument("--out", help="쓸 hls.json 경로")
    args = parser.parse_args()

    global DATA, OUT
    if args.data: DATA = pathlib.Path(args.data)
    if args.out:  OUT = pathlib.Path(args.out)

    sessions = chzzk_sessions()
    current = load_current()

    print("현재 상태 (치지직 %d개 방송)" % len(sessions))
    worst = 99.0
    for s in sessions:
        entry = current.get(s["date"]) or {}
        text, left = describe(entry.get("url"))
        worst = min(worst, left)
        print("  %s  %s" % (s["date"], text))

    if args.check:
        return
    if worst > RENEW_BELOW_HOURS and not args.force:
        print("\n아직 %.1f시간 남아 갱신하지 않았습니다 (기준 %.0f시간)." % (worst, RENEW_BELOW_HOURS))
        return

    print("\n주소를 다시 받는 중…")
    fresh, failed, gone = {}, 0, []
    for s in sessions:
        url, why = chzzk_hls(s["video_id"])
        if not url:
            if why == "gone":
                # 사라진 영상은 기존 주소를 남겨 둘 이유가 없다 — 눌러도 죽은 페이지다.
                gone.append({"date": s["date"], "video_id": s["video_id"]})
                continue
            failed += 1
            keep = current.get(s["date"])
            if keep:
                fresh[s["date"]] = keep       # 일시적 실패면 기존 값을 지우지 않는다
            continue
        fresh[s["date"]] = {"url": url, "exp": expires_at(url)}
        text, _ = describe(url)
        print("  %s  %s" % (s["date"], text))

    if not fresh:
        raise SystemExit("한 건도 받지 못했습니다. 기존 파일을 그대로 둡니다.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"generated_at": int(time.time()), "sessions": fresh, "gone": gone},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    left = min((describe(v["url"])[1] for v in fresh.values()), default=0.0)
    print("\n%s 갱신 · %d개 방송%s" % (OUT.name, len(fresh),
                                    (" · 실패 %d개" % failed) if failed else ""))
    print("만료까지 %.0f시간 — 12시간 주기면 %.0f시간 여유입니다." % (left, max(0.0, left - 12)))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
