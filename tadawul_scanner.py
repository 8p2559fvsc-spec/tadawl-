import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

import pandas as pd
import yfinance as yf

# الحد الأدنى للدرجة عشان يجيك تنبيه (الأعلى ممكن = 6)
ALERT_SCORE = 4

STOCKS = {
    "2222.SR": "أرامكو",
    "1120.SR": "الراجحي",
    "1180.SR": "الأهلي",
    "2010.SR": "سابك",
    "7010.SR": "stc",
    "1211.SR": "معادن",
    "2280.SR": "المراعي",
    "1150.SR": "الإنماء",
    "1010.SR": "بنك الرياض",
    "5110.SR": "السعودية للكهرباء",
    "2082.SR": "أكوا",
    "4013.SR": "سليمان الحبيب",
}


def rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)


def macd_hist(close):
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal


def analyze(df):
    close, volume = df["Close"], df["Volume"]
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    upper, lower = mid + 2 * std, mid - 2 * std
    high20 = close.shift(1).rolling(20).max()
    vol_avg = volume.rolling(20).mean()

    last = {
        "price": close.iloc[-1],
        "rsi": rsi(close).iloc[-1],
        "macd_hist": macd_hist(close).iloc[-1],
    }

    signals = {}
    signals["فوق متوسط 50"] = 1 if close.iloc[-1] > sma50.iloc[-1] else -1
    signals["متوسط 50 فوق 200"] = 1 if sma50.iloc[-1] > sma200.iloc[-1] else -1
    r = last["rsi"]
    signals["RSI"] = 1 if 50 <= r <= 70 else (-1 if r > 70 else 0)
    signals["MACD"] = 1 if last["macd_hist"] > 0 else -1
    if close.iloc[-1] < lower.iloc[-1]:
        signals["Bollinger"] = 1
    elif close.iloc[-1] > upper.iloc[-1]:
        signals["Bollinger"] = -1
    else:
        signals["Bollinger"] = 0
    breakout = close.iloc[-1] > high20.iloc[-1] and volume.iloc[-1] > 1.5 * vol_avg.iloc[-1]
    signals["اختراق"] = 1 if breakout else 0

    return last, signals


def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("تنبيه تيليجرام غير مفعّل")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=15)
    except Exception as e:
        print(f"فشل إرسال التنبيه: {e}")


def load_previous_scores():
    try:
        with open("results.json", encoding="utf-8") as f:
            old = json.load(f)
        return {r["ticker"]: r["score"] for r in old["results"]}
    except Exception:
        return {}


def send_alerts(results, previous):
    fresh = [
        r for r in results
        if r["score"] >= ALERT_SCORE and previous.get(r["ticker"], 0) < ALERT_SCORE
    ]
    if not fresh:
        return
    lines = ["📈 أسهم ظهرت عليها إشارات فنية إيجابية:\n"]
    for r in fresh:
        lines.append(f"• {r['name']} ({r['ticker']}) - السعر {r['price']} - الدرجة {r['score']}/6")
    lines.append("\n⚠️ مؤشرات فنية آلية، مو توصية ولا ضمان ارتفاع.")
    send_telegram("\n".join(lines))


def main():
    previous = load_previous_scores()
    results = []
    for ticker, name in STOCKS.items():
        try:
            df = yf.Ticker(ticker).history(period="2y", interval="1d")
            if len(df) < 210:
                print(f"بيانات غير كافية: {ticker}")
                continue
            last, signals = analyze(df)
            score = sum(signals.values())
            results.append({
                "ticker": ticker,
                "name": name,
                "price": round(float(last["price"]), 2),
                "rsi": round(float(last["rsi"]), 1),
                "score": score,
                "signals": signals,
            })
        except Exception as e:
            print(f"خطأ في {ticker}: {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    send_alerts(results, previous)

    out = {
        "updated": datetime.now().isoformat(timespec="minutes"),
        "disclaimer": "مؤشرات فنية آلية وليست توصية استثمارية",
        "results": results,
    }
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    table = pd.DataFrame(results)[["name", "ticker", "price", "rsi", "score"]]
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
