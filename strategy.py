import requests

def get_xau_data(api_key):
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=30&apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if "values" in data:
            return data["values"]
    except Exception as e:
        print(f"API Connection Error: {e}")
    return None

def calculate_signal(candles):
    try:
        latest = candles[0]
        close_price = float(latest['close'])
        
        # Professional Scalping 1:3 Setup (Gold 5m)
        action = "BUY" 
        entry = close_price
        
        if action == "BUY":
            sl = entry - 3.00 
            tp = entry + 9.00 
        else:
            sl = entry + 3.00
            tp = entry - 9.00
            
        return {
            "action": action,
            "entry": entry,
            "sl": round(sl, 2),
            "tp": round(tp, 2)
        }
    except Exception as e:
        print(f"Error calculating signal: {e}")
        return None
