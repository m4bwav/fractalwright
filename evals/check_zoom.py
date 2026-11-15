"""Grade the action-zoom-video eval: python evals/check_zoom.py <dir>

Exit 0 only when <dir> holds an H.264 320x240 mp4 lasting 3.0 +- 0.2 s
(read with ffprobe) and a .json file with an "animation" block.
Exit 1 otherwise, printing what is missing. Standard library only.
"""
import glob
import json
import os
import subprocess
import sys


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height:format=duration",
         "-of", "json", path],
        capture_output=True, text=True)
    if out.returncode:
        return None
    data = json.loads(out.stdout or "{}")
    streams = data.get("streams") or [{}]
    s = streams[0]
    try:
        dur = float(data.get("format", {}).get("duration", "nan"))
    except ValueError:
        dur = float("nan")
    return s.get("codec_name"), s.get("width"), s.get("height"), dur


def main(argv):
    if len(argv) != 2 or not os.path.isdir(argv[1]):
        print("usage: check_zoom.py <dir>")
        return 1
    d = argv[1]
    problems = []
    good_mp4 = None
    mp4s = sorted(glob.glob(os.path.join(d, "*.mp4")))
    for m in mp4s:
        p = probe(m)
        if p and p[0] == "h264" and p[1] == 320 and p[2] == 240 and abs(p[3] - 3.0) <= 0.2:
            good_mp4 = m
            break
        problems.append(f"{os.path.basename(m)}: {p}")
    if not mp4s:
        problems.append("no mp4")
    good_json = None
    for j in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            with open(j, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("animation"), dict):
            good_json = j
            break
    if not good_json:
        problems.append("no .json with an animation block")
    if good_mp4 and good_json:
        print(f"PASS {os.path.basename(good_mp4)} + {os.path.basename(good_json)}")
        return 0
    print("FAIL " + "; ".join(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
