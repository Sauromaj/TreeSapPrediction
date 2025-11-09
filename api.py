from fastapi import FastAPI, Form, Query
from fastapi.responses import JSONResponse
from twilio.rest import Client
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os

from lst_data import ret_normalized_land_temperature
from SoilMoistureData import SmapFetcher
from PressureData import PressureDataFetcher
from SeasonalPlanningAlerts import Predict

from utils import get_coordinates

app = FastAPI(title="Freeze-Thaw, LST & Soil Moisture API")

# --------------------------------------------------
# 🧊 Freeze–Thaw Endpoint
# --------------------------------------------------
@app.get("/freeze-thaw")
def get_freeze_thaw_data(address: str = Query(..., description="Full address to fetch coordinates for")):
    
    lat, lon = get_coordinates(address)

    start_date, end_date = Predict(lat, lon)

    LST_data_normalized = get_lst_data(start_date, end_date, lat, lon)
    Soil_data_normalized = get_soil_moisture_data(start_date, end_date, lat, lon)
    Pressure_data_normalized = get_pressure_data(lat, lon, start_date, end_date)




    # print(LST_data_normalized)
    # print(Soil_data_normalized)
    # print(Pressure_data_normalized)
    normalized_data = calculate_index(LST_data_normalized,Pressure_data_normalized, Soil_data_normalized)


    # Calculate index value to adjust start_date
    # print(normalized_data)
    index_value = normalized_data["combined_index"].idxmax(skipna=True)
    start_date = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=int(index_value))
    pick_date = start_date.strftime('%Y-%m-%d')


    data = {
        "start_date_freeze_thaw": [start_date],
        "pick_date": [pick_date],
        "end_date_freeze_thaw": [end_date],
    }

    modis_df_final = pd.DataFrame(data)
    print(modis_df_final.head(10))
    return JSONResponse(content=modis_df_final.to_dict(orient="records"))

# --------------------------------------------------
# 📱 SMS Endpoint
# --------------------------------------------------
@app.post("/send-sms")
def send_sms(
    to: str = Form(...),
    message: str = Form(...)
):
    """
    Send an SMS via Twilio.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        return JSONResponse(
            content={"error": "Twilio credentials not configured"},
            status_code=500
        )

    try:
        client = Client(account_sid, auth_token)
        msg = client.messages.create(body=message, from_=from_number, to=to)
        return {"status": "success", "sid": msg.sid}
    except Exception as e:
        return JSONResponse(content={"status": "failed", "error": str(e)}, status_code=400)


# --------------------------------------------------
# 🌡️ Land Surface Temperature Data Endpoint
# --------------------------------------------------

def get_lst_data(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    lat: float = Query(..., description="Latitude in decimal degrees"),
    long: float = Query(..., description="Longitude in decimal degrees"),
):
    """
    Retrieve normalized Land Surface Temperature (LST) data
    for a given location and time range.
    """

    print(start_date)
    print(end_date)
    print(lat)
    print(long)

    land_surface_data = ret_normalized_land_temperature(start_date, end_date, lat, long)

    return land_surface_data



# --------------------------------------------------
# 🌱 Soil Moisture Data Endpoint
# --------------------------------------------------
def get_soil_moisture_data(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    lat: float = Query(..., description="Latitude in decimal degrees"),
    long: float = Query(..., description="Longitude in decimal degrees"),
):
    """
    Retrieve normalized soil moisture data
    for a given location and time range.
    """

    # 1️⃣ Convert start_date to datetime
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")

    # 2️⃣ Subtract 2 years
    start_date_2yrs_ago = start_date_dt.replace(year=start_date_dt.year - 2)

    new_start_date = start_date_2yrs_ago.strftime('%Y-%m-%d')

    end_date = datetime.today().strftime("%Y-%m-%d")
    hist_start = new_start_date
    hist_end = end_date

    soil_fetch = SmapFetcher(lat, long, hist_start, hist_end)

    hist_df = soil_fetch.fetch_range()

    normalized_future = soil_fetch.normalized_prediction(start_date, end_date)

    soil_data = soil_fetch.main()
 

    return soil_data

def calculate_index(
    LST_day_normalized: list[float] = Form(...),
    Pressure_day_normalized: list[float] = Form(...),
    soil_moisture_normalized: list[float] = Form(...)
):
    """
    Calculate a combined environmental index using the
    normalized LST, pressure, and soil moisture data.
    """

    # Convert lists to pandas DataFrame for vector operations
    LST_day_normalized.fillna(0)
    Pressure_day_normalized.fillna(0)
    soil_moisture_normalized.fillna(0)

    df = pd.DataFrame({
        "LST_day_normalized": LST_day_normalized,
        "Pressure_day_normalized": Pressure_day_normalized,
        "soil_moisture_normalized": soil_moisture_normalized
    })


    # Example: simple weighted average index
    df["combined_index"] = (
        0.4 * df["LST_day_normalized"] +
        0.3 * df["Pressure_day_normalized"] +
        0.3 * df["soil_moisture_normalized"]
    )

    # # Optional normalization (0–1)
    # df["combined_index_normalized"] = (
    #     (df["combined_index"] - df["combined_index"].min()) /
    #     (df["combined_index"].max() - df["combined_index"].min())
    # )

    print(df.head())
    return df


def get_pressure_data(
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD")
):
    """
    Fetch normalized pressure data for a given location and date range.
    """

    # 1️⃣ Initialize the fetcher
    fetcher = PressureDataFetcher(lat, lon)

    fetcher.get_past_5years()

    # 2️⃣ Fetch normalized pressure values
    pressure_values = fetcher.normalizedPrediction(start_date, end_date)

    return pressure_values


if __name__ == "__main__":
    print(get_freeze_thaw_data(address= 'Brampton, Canada'))