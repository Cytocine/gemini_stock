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

WATCHLIST = ["AA","AAL","AAPL","ABBV","ABT","ACB","ACGL","ACN","ADBE","ADI","ADP","ADSK","AEM","AFL","AFRM","AGNC","AIG","ALHC","AMAT","AMD","AMGN","AMP","AMT","AMZN","ANET","APA","APH","APO","APP","ARM","ASML","ASPI","ASTS","AVDL","AVGO","AXP","AXON","AZN","BA","BAC","BABA","BAM","BE","BKR","BKNG","BLK","BMY","BSX","BULL","BX","C","CARR","CAT","CAVA","CC","CCJ","CCL","CDNS","CEG","CELH","CHTR","CHWY","CI","CL","CLMT","CLOV","CLSK","CMCSA","CME","CMG","CMI","CNQ","COF","COIN","COP","CORZ","COST","COTY","CPNG","CPRT","CRM","CRML","CRWD","CRWV","CSX","CTAS","CVNA","CVS","CVX","D","DASH","DAR","DBX","DD","DDOG","DE","DELL","DFS","DG","DHI","DIS","DJT","DKNG","DLR","DLTR","DOV","DOW","DRI","DUK","EAT","EBAY","ECL","ED","EMR","ENPH","ENR","EOG","EPAM","EQIX","EQX","ETN","ETR","EW","EXC","EXE","F","FANG","FAST","FCX","FDX","FI","FIS","FITB","FSLR","FTNT","GD","GE","GEV","GILD","GILT","GIS","GLW","GM","GME","GNRC","GOOG","GOOGL","GPN","GS","HAL","HD","HEI","HIG","HIMS","HON","HOOD","HPE","HPQ","HST","HUM","HUT","IBM","ICE","IDXX","ILMN","INTC","INTU","IQ","IREN","ISRG","ITW","IWM","J","JBHT","JBLU","JCI","JD","JMIA","JNJ","JPM","K","KHC","KMB","KMI","KO","KR","KSS","L","LEN","LHX","LIN","LLY","LOW","LULU","LUV","LVS","LYFT","LYV","MA","MAR","MARA","MAS","MBLY","MBOT","MCD","MCHP","MCK","MDT","META","MET","MGM","MHK","MKC","MKL","MLM","MMC","MMM","MNDY","MNST","MO","MRA","MRK","MRO","MRVL","MS","MSFT","MSI","MSTR","MTB","MTD","MU","NEE","NEM","NET","NEXT","NFLX","NIO","NKE","NOC","NSC","NTRS","NU","NUE","NVDA","ONDS","OPEN","ORCL","OTIS","OWL","OXY","PANW","PATH","PAYX","PBR","PCG","PDD","PEP","PFE","PG","PGEN","PGR","PH","PINS","PKG","PLD","PLTR","PM","PNC","PNR","POOL","PPG","PRU","PSA","PSKY","PWR","PXD","QBTS","QCOM","QD","QQQ","QS","RCL","REGN","RELY","RGTI","RIOT","RIVN","RKT","RMD","ROK","ROKU","ROL","ROP","ROST","RSG","RTX","RVMD","SATS","SBUX","SCHW","SERV","SHW","SJM","SLB","SLV","SMC","SMCI","SNAP","SNOW","SNPS","SO","SOFI","SOUN","SPGI","SPY","SQ","STZ","SYK","SYY","T","TAP","TCOM","TDOC","TEVA","TFC","TFX","TGT","TIGR","TJX","TMDX","TMO","TMUS","TNA","TRMD","TSCO","TSLA","TSM","TT","TTD","TXN","U","UAL","UBER","UNH","UNP","UPS","UPST","URI","USB","V","VALE","VLO","VMC","VRTX","VZ","VST","WDC","WFC","WMB","WMT","WTW","WULF","WYNN","XLE","XLF","XOM","XPEV","XYL","YUM","Z","ZTS"]

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
