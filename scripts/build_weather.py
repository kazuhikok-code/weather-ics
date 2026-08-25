# -*- coding: utf-8 -*-
"""気象庁の予報JSONから天気予報ICS（購読カレンダー）を生成する。

データ源: https://www.jma.go.jp/bosai/forecast/data/forecast/{PREF_CODE}.json
出典: 気象庁（公共データ利用規約 第1.0版 準拠）

使い方:
    python scripts/build_weather.py            # 気象庁から取得して生成
    python scripts/build_weather.py input.json # ローカルJSONから生成（テスト用）
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

# ===== 地域設定（全国版に拡張するときはここを地域ごとに差し替える）=====
PREF_CODE = "390000"        # 高知県
CLASS10_CODE = "390010"     # 高知県中部（高知市が属する予報区）
TEMP_STATION_CODE = "74182" # 気温の代表地点「高知」
CAL_NAME = "高知の天気"
UID_AREA = "weather-kochi"  # UIDの一部。変更するとカレンダー側で別イベント扱いになるため変更禁止
OUTPUT = Path(__file__).resolve().parent.parent / "public" / "kochi.ics"
# =====================================================================

JST = timezone(timedelta(hours=9))
FORECAST_URL = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{PREF_CODE}.json"

# 気象庁の天気コード→日本語（週間予報で使われる主要コード）。
# 未知のコードは百の位でフォールバックする。
WEATHER_CODE_TEXT = {
    "100": "晴れ", "101": "晴れ時々くもり", "102": "晴れ一時雨", "103": "晴れ時々雨",
    "104": "晴れ一時雪", "105": "晴れ時々雪", "106": "晴れ一時雨か雪", "107": "晴れ時々雨か雪",
    "108": "晴れ一時雨か雷雨", "110": "晴れ後時々くもり", "111": "晴れ後くもり",
    "112": "晴れ後一時雨", "113": "晴れ後時々雨", "114": "晴れ後雨", "115": "晴れ後一時雪",
    "116": "晴れ後時々雪", "117": "晴れ後雪", "118": "晴れ後雨か雪", "119": "晴れ後雨か雷雨",
    "120": "晴れ朝夕一時雨", "121": "晴れ朝の内一時雨", "122": "晴れ夕方一時雨",
    "123": "晴れ山沿い雷雨", "124": "晴れ山沿い雪", "125": "晴れ午後は雷雨",
    "126": "晴れ昼頃から雨", "127": "晴れ夕方から雨", "128": "晴れ夜は雨",
    "130": "朝の内霧後晴れ", "131": "晴れ明け方霧", "132": "晴れ朝夕くもり",
    "140": "晴れ時々雨で雷を伴う", "160": "晴れ一時雪か雨", "170": "晴れ時々雪か雨",
    "181": "晴れ後雪か雨",
    "200": "くもり", "201": "くもり時々晴れ", "202": "くもり一時雨", "203": "くもり時々雨",
    "204": "くもり一時雪", "205": "くもり時々雪", "206": "くもり一時雨か雪",
    "207": "くもり時々雨か雪", "208": "くもり一時雨か雷雨", "209": "霧",
    "210": "くもり後時々晴れ", "211": "くもり後晴れ", "212": "くもり後一時雨",
    "213": "くもり後時々雨", "214": "くもり後雨", "215": "くもり後一時雪",
    "216": "くもり後時々雪", "217": "くもり後雪", "218": "くもり後雨か雪",
    "219": "くもり後雨か雷雨", "220": "くもり朝夕一時雨", "221": "くもり朝の内一時雨",
    "222": "くもり夕方一時雨", "223": "くもり日中時々晴れ", "224": "くもり昼頃から雨",
    "225": "くもり夕方から雨", "226": "くもり夜は雨", "228": "くもり昼頃から雪",
    "229": "くもり夕方から雪", "230": "くもり夜は雪", "231": "くもり海上海岸は霧か霧雨",
    "240": "くもり時々雨で雷を伴う", "250": "くもり時々雪で雷を伴う",
    "260": "くもり一時雪か雨", "270": "くもり時々雪か雨", "281": "くもり後雪か雨",
    "300": "雨", "301": "雨時々晴れ", "302": "雨時々止む", "303": "雨時々雪", "304": "雨か雪",
    "306": "大雨", "308": "雨で暴風を伴う", "309": "雨一時雪", "311": "雨後晴れ",
    "313": "雨後くもり", "314": "雨後時々雪", "315": "雨後雪", "316": "雨か雪後晴れ",
    "317": "雨か雪後くもり", "320": "朝の内雨後晴れ", "321": "朝の内雨後くもり",
    "322": "雨朝晩一時雪", "323": "雨昼頃から晴れ", "324": "雨夕方から晴れ",
    "325": "雨夜は晴れ", "326": "雨夕方から雪", "327": "雨夜は雪", "328": "雨一時強く降る",
    "329": "雨一時みぞれ", "340": "雪か雨", "350": "雨で雷を伴う", "361": "雪か雨後晴れ",
    "371": "雪か雨後くもり",
    "400": "雪", "401": "雪時々晴れ", "402": "雪時々止む", "403": "雪時々雨", "405": "大雪",
    "406": "風雪強い", "407": "暴風雪", "409": "雪一時雨", "411": "雪後晴れ",
    "413": "雪後くもり", "414": "雪後雨", "420": "朝の内雪後晴れ", "421": "朝の内雪後くもり",
    "422": "雪昼頃から雨", "423": "雪夕方から雨", "425": "雪一時強く降る",
    "426": "雪後みぞれ", "427": "雪一時みぞれ", "450": "雪で雷を伴う",
}
CODE_FALLBACK = {"1": "晴れ", "2": "くもり", "3": "雨", "4": "雪"}


def code_to_text(code):
    if code in WEATHER_CODE_TEXT:
        return WEATHER_CODE_TEXT[code]
    return CODE_FALLBACK.get(str(code)[:1], "予報")


def pick_emoji(text):
    """天気文からカレンダー表示用の絵文字を1つ選ぶ。"""
    if "雪" in text or "みぞれ" in text:
        return "⛄"
    if "雷" in text:
        return "⛈"
    has_rain = "雨" in text
    has_sun = "晴" in text
    has_cloud = ("くもり" in text) or ("曇" in text)
    if has_rain and has_sun:
        return "🌦"
    if has_rain:
        return "🌧"
    if "霧" in text:
        return "🌫"
    if has_sun and has_cloud:
        return "⛅"
    if has_sun:
        return "☀"
    if has_cloud:
        return "☁"
    return "🌤"


def normalize_weather(w):
    """気象庁の天気文「くもり　後　一時　雨」を「くもり後一時雨」に整える。
    「所により〜」の補足節の前にだけ区切りを残す。"""
    t = re.sub(r"\s+", "", w.strip())
    return t.replace("所により", "　所により")


def fetch_forecast(path=None):
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    req = urllib.request.Request(FORECAST_URL, headers={"User-Agent": "weather-ics/1.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def valid_num(v):
    return v not in (None, "", "-")


def parse_days(data, today):
    """気象庁JSONを日付ごとの辞書 {date: {text, pop, tmin, tmax}} に統合する。"""
    short, weekly = data[0], data[1]
    days = {}

    def day(d):
        return days.setdefault(d, {"text": None, "pop": None, "tmin": None, "tmax": None})

    # --- 短期（今日〜明後日）: 天気文・6時間区分の降水確率・地点気温 ---
    for ts in short.get("timeSeries", []):
        times = [datetime.fromisoformat(t) for t in ts["timeDefines"]]
        for area in ts["areas"]:
            code = area["area"]["code"]
            if code == CLASS10_CODE and "weathers" in area:
                for t, w in zip(times, area["weathers"]):
                    day(t.date())["text"] = normalize_weather(w)
            if code == CLASS10_CODE and "pops" in area:
                for t, p in zip(times, area["pops"]):
                    if valid_num(p):
                        d = day(t.date())
                        d["pop"] = max(d["pop"] or 0, int(p))
            if code == TEMP_STATION_CODE and "temps" in area:
                # timeDefinesの時刻で意味が決まる: 00:00=最低気温 / 09:00=日中の最高気温
                for t, v in zip(times, area["temps"]):
                    if not valid_num(v):
                        continue
                    d = day(t.date())
                    if t.hour == 0:
                        d["tmin"] = int(v)
                    elif t.hour == 9:
                        d["tmax"] = int(v)

    # 11時・17時発表では当日の最低気温欄に最高気温が重複格納される（気象庁の仕様）。
    # 当日で最低=最高なら最低は欠損として扱う。
    t = days.get(today)
    if t and t["tmin"] is not None and t["tmin"] == t["tmax"]:
        t["tmin"] = None

    # --- 週間（明日〜7日先）: 足りない項目だけ補完する ---
    for ts in weekly.get("timeSeries", []):
        times = [datetime.fromisoformat(t) for t in ts["timeDefines"]]
        for area in ts["areas"]:
            code = area["area"]["code"]
            if code == PREF_CODE and "weatherCodes" in area:
                for t, wc, p in zip(times, area["weatherCodes"], area.get("pops", [])):
                    d = day(t.date())
                    if d["text"] is None and valid_num(wc):
                        d["text"] = code_to_text(wc)
                    if d["pop"] is None and valid_num(p):
                        d["pop"] = int(p)
            if code == TEMP_STATION_CODE and "tempsMin" in area:
                for t, lo, hi in zip(times, area["tempsMin"], area["tempsMax"]):
                    d = day(t.date())
                    if d["tmin"] is None and valid_num(lo):
                        d["tmin"] = int(lo)
                    if d["tmax"] is None and valid_num(hi):
                        d["tmax"] = int(hi)

    return days


def build_event_text(info):
    """SUMMARYとDESCRIPTION本文（出典行を除く）を組み立てる。"""
    text = info["text"] or "予報"
    # 「所により〜」の補足節は要約と絵文字選定から外し、主文だけで判断する
    short_text = text.split("　")[0]
    emoji = pick_emoji(short_text)

    if info["tmax"] is not None and info["tmin"] is not None:
        temp_label = f"{info['tmax']}/{info['tmin']}℃"
    elif info["tmax"] is not None:
        temp_label = f"最高{info['tmax']}℃"
    elif info["tmin"] is not None:
        temp_label = f"最低{info['tmin']}℃"
    else:
        temp_label = ""
    summary = f"{emoji} {short_text}" + (f" {temp_label}" if temp_label else "")

    parts = []
    if info["tmax"] is not None:
        parts.append(f"最高{info['tmax']}℃")
    if info["tmin"] is not None:
        parts.append(f"最低{info['tmin']}℃")
    if info["pop"] is not None:
        parts.append(f"降水確率{info['pop']}％")
    desc = f"{text}。"
    if parts:
        desc += "、".join(parts) + "の予報です。"
    return summary, desc


def esc(s):
    return (s.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    """RFC 5545: 1行75オクテット以内にUTF-8境界を保って折り返す。"""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return [line]
    out, cur, cur_len, limit = [], "", 0, 75
    for ch in line:
        b = len(ch.encode("utf-8"))
        if cur_len + b > limit:
            out.append(cur)
            cur, cur_len, limit = " ", 1, 75
        cur += ch
        cur_len += b
    if cur.strip("\x20"):
        out.append(cur)
    return out


def build_ics(days, report_dt, today):
    dtstamp = report_dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    issued = f"{report_dt.month}月{report_dt.day}日{report_dt.hour}時発表"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//weather-ics//JP",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{CAL_NAME}",
        "X-WR-TIMEZONE:Asia/Tokyo",
        "X-WR-CALDESC:気象庁の天気予報データをもとに1日3回自動更新されます",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    for d in sorted(days):
        if d < today or d > today + timedelta(days=7):
            continue
        info = days[d]
        if info["text"] is None:
            continue
        summary, desc = build_event_text(info)
        desc += f"\n出典: 気象庁（{issued}）"
        # UIDは安定運用（変更禁止）。変更すると購読側で別イベントになる。
        uid = f"{d.isoformat()}-{UID_AREA}@weather-ics"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{esc(summary)}",
            f"DESCRIPTION:{esc(desc)}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")

    folded = []
    for line in lines:
        folded.extend(fold(line))
    return "\r\n".join(folded) + "\r\n"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    data = fetch_forecast(src)
    report_dt = datetime.fromisoformat(data[0]["reportDatetime"])
    today = datetime.now(JST).date()
    days = parse_days(data, today)
    ics = build_ics(days, report_dt, today)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(ics.encode("utf-8"))
    n = ics.count("BEGIN:VEVENT")
    print(f"OK: {OUTPUT} ({n} events, 発表: {report_dt.isoformat()})")


if __name__ == "__main__":
    main()
