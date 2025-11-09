import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from twilio.rest import Client

lat, lon = 43.7315, -79.7624  # Brampton, Ontario

def fetch_year(year):
    start_date = f"{year}-01-01"
    end_date   = f"{year}-04-30"
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m",
        "timezone": "America/Toronto"
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    j = r.json()
    df = pd.DataFrame({
        "time": pd.to_datetime(j["hourly"]["time"]),
        "temp": j["hourly"]["temperature_2m"]
    })
    df["date"] = df["time"].dt.date
    daily = df.groupby("date").agg(tmin=("temp","min"), tmax=("temp","max")).reset_index()
    return daily

def compute_window(daily):
    # Updated criteria: min < 0, max > 7, max <= 10
    daily['freeze_thaw'] = (daily['tmin'] < 0) & (daily['tmax'] > 4) & (daily['tmax'] <= 10)
    daily['group'] = (daily['freeze_thaw'] != daily['freeze_thaw'].shift()).cumsum()
    streaks = daily.groupby('group')['freeze_thaw'].agg(['sum','size'])
    valid_groups = streaks[streaks['sum'] >= 3].index
    windows = daily[daily['group'].isin(valid_groups)]

    if not windows.empty:
        start = pd.to_datetime(windows['date'].iloc[0])
        end   = pd.to_datetime(windows['date'].iloc[-1])
        return start, end
    else:
        return None, None

def Predict():
    today = datetime.now()
    years = [today.year - 2, today.year - 1]  # last 2 years
    results = []

    for y in years:
        try:
            daily = fetch_year(y)
            start, end = compute_window(daily)
            results.append({"year": y, "start_dt": start, "end_dt": end})
        except Exception as e:
            print("Error fetching year", y, e)
        time.sleep(1)

    res_df = pd.DataFrame(results).dropna()

    res_df['start_doy'] = res_df['start_dt'].dt.dayofyear
    res_df['duration'] = (res_df['end_dt'] - res_df['start_dt']).dt.days

    median_start_doy = int(res_df['start_doy'].median())
    median_duration  = int(res_df['duration'].median())

    predict_year = today.year + 1 if today.month > 4 else today.year

    start_date = datetime(predict_year, 1, 1) + timedelta(days=median_start_doy - 1)
    end_date   = start_date + timedelta(days=median_duration - 1)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    #print(f"\n Predicted Freeze–Thaw Window for {predict_year}: {start_date:%Y-%m-%d} → {end_date:%Y-%m-%d}")
    return (start_str, end_str)
