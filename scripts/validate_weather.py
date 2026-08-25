# -*- coding: utf-8 -*-
"""生成されたICSの機械検査。失敗したら非0で終了する（デプロイを止める）。"""
import re
import sys
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

ICS = Path(__file__).resolve().parent.parent / "public" / "kochi.ics"
UID_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-weather-kochi@weather-ics$")
JST = timezone(timedelta(hours=9))

errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


def main():
    raw = ICS.read_bytes()
    check(b"\r\n" in raw, "CRLF改行が使われていない")
    check(b"\n" not in raw.replace(b"\r\n", b""), "CRLFでない裸のLFが混入している")

    text = raw.decode("utf-8")
    physical = text.split("\r\n")
    check(all(len(l.encode("utf-8")) <= 75 for l in physical if l),
          "75オクテットを超える行がある")
    # 末尾の終端CRLF由来の空要素以外に、空行があってはならない（折り返し不良の検出）
    check(all(l for l in physical[:-1]), "カレンダー内に空行が混入している")

    # 折り返しを解除して論理行に戻す
    logical = []
    for line in physical:
        if line.startswith(" ") and logical:
            logical[-1] += line[1:]
        else:
            logical.append(line)

    check(logical[0] == "BEGIN:VCALENDAR", "先頭がBEGIN:VCALENDARでない")
    check("END:VCALENDAR" in logical, "END:VCALENDARがない")
    check(any(l.startswith("X-WR-CALNAME:") for l in logical), "X-WR-CALNAMEがない")

    n_begin = sum(1 for l in logical if l == "BEGIN:VEVENT")
    n_end = sum(1 for l in logical if l == "END:VEVENT")
    check(n_begin == n_end, f"VEVENTの対応が崩れている ({n_begin}/{n_end})")
    check(6 <= n_begin <= 8, f"イベント件数が異常: {n_begin}件（6〜8件のはず）")

    uids = [l[4:] for l in logical if l.startswith("UID:")]
    dates = []
    for uid in uids:
        m = UID_RE.match(uid)
        check(m is not None, f"UID形式が不正: {uid}")
        if m:
            dates.append(date.fromisoformat(m.group(1)))
    check(len(set(uids)) == len(uids), "UIDが重複している")

    dates.sort()
    for a, b in zip(dates, dates[1:]):
        check(b - a == timedelta(days=1), f"日付が連続していない: {a} → {b}")

    today = datetime.now(JST).date()
    check(today in dates, f"今日({today})のイベントがない")

    n_summary = sum(1 for l in logical if l.startswith("SUMMARY:"))
    n_desc = sum(1 for l in logical if l.startswith("DESCRIPTION:"))
    check(n_summary == n_begin, "SUMMARYのないイベントがある")
    check(n_desc == n_begin, "DESCRIPTIONのないイベントがある")
    check(all("出典: 気象庁" in l for l in logical if l.startswith("DESCRIPTION:")),
          "出典表記のないDESCRIPTIONがある")

    if errors:
        for e in errors:
            print(f"NG: {e}")
        sys.exit(1)
    print(f"OK: {ICS.name} 検査合格（{n_begin}件, {dates[0]}〜{dates[-1]}）")


if __name__ == "__main__":
    main()
