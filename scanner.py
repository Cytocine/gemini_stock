import os
import json
import requests
from datetime import datetime, timedelta
from pytz import timezone

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from google import genai
from google.genai import types

# Read from GitHub Secrets
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

WATCHLIST = ["NVDA","TSLA","AAPL","AMZN","MSFT","META","AMD","PLTR","INTC","MU","GOOGL","NFLX","SOFI","ORCL","COIN","BABA","MARA","AVGO","DIS","F","SPY","IWM","QQQ","HOOD","JPM","C","BAC","XOM","OXY","UBER","ENPH","COST","NKE","LLY","MRK"
]

alpaca_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def send_discord_alert(ticker, confidence, analysis, entry, stop, target):
    embed = {
        "title": f"🚨 GEMINI SCANNER ALERT: {ticker}",
        "color": 3066993,
        "fields": [
            {"name": "Confidence Score", "value": f"**{confidence}%**", "inline": True},
            {"name": "Suggested Entry", "value": f"${entry}", "inline": True},
            {"name": "Stop Loss", "value": f"${stop}", "inline": True},
            {"name": "Target Price", "value": f"${target}", "inline": True},
            {"name": "Analysis & Reasoning", "value": analysis, "inline": False}
        ],
        "footer": {"text": "GitHub Actions Daily Scan • 3:45 PM ET"},
        "timestamp": datetime.utcnow().isoformat()
    }
    requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})

def get_stock_data(symbol):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)

    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date
    )
    bars = alpaca_client.get_stock_bars(request_params)
    df = bars.df.loc[symbol]

    latest_bar = df.iloc[-1]
    prev_bar = df.iloc[-2]

    return {
        "ticker": symbol,
        "latest_close": round(latest_bar['close'], 2),
        "latest_volume": int(latest_bar['volume']),
        "prev_close": round(prev_bar['close'], 2),
        "recent_closes": df['close'].tail(10).round(2).tolist(),
        "recent_highs": df['high'].tail(10).round(2).tolist(),
        "recent_lows": df['low'].tail(10).round(2).tolist()
    }

def run_daily_scan():
    print(f"[{datetime.now()}] Triggering 3:45 PM ET Scan...")
    
    for symbol in WATCHLIST:
        try:
            market_data = get_stock_data(symbol)
            prompt = f"Analyze market data for {symbol}:\n{market_data}"

            response = gemini_client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="""
                    Evaluate technical setup. Set alert_triggered = True ONLY if stock shows 
                    a strong momentum/pullback setup before market close.
                    """,
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "alert_triggered": {"type": "BOOLEAN"},
                            "ticker": {"type": "STRING"},
                            "confidence_score": {"type": "INTEGER"},
                            "analysis": {"type": "STRING"},
                            "trade_plan": {
                                "type": "OBJECT",
                                "properties": {
                                    "suggested_entry": {"type": "NUMBER"},
                                    "stop_loss": {"type": "NUMBER"},
                                    "target_price": {"type": "NUMBER"}
                                }
                            }
                        },
                        "required": ["alert_triggered", "analysis"]
                    }
                )
            )

            result = json.loads(response.text)
            if result.get("alert_triggered"):
                tp = result.get("trade_plan", {})
                send_discord_alert(
                    ticker=result['ticker'],
                    confidence=result.get('confidence_score', 'N/A'),
                    analysis=result['analysis'],
                    entry=tp.get('suggested_entry', 'N/A'),
                    stop=tp.get('stop_loss', 'N/A'),
                    target=tp.get('target_price', 'N/A')
                )
                print(f"Alert sent to Discord for {symbol}")
            else:
                print(f"No setup for {symbol}")
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

if __name__ == "__main__":
    run_daily_scan()
