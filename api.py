from fastapi import FastAPI, Form, Query
from fastapi.responses import JSONResponse
from twilio.rest import Client
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from fastapi import Request

from lst_data import ret_normalized_land_temperature
from SoilMoistureData import SmapFetcher
from PressureData import PressureDataFetcher
from SeasonalPlanningAlerts import Predict

from utils import get_coordinates

app = FastAPI(title="Freeze-Thaw, LST & Soil Moisture API")


# --------------------------------------------------
# 🧊 Freeze–Thaw Endpoint
# --------------------------------------------------
@app.get("/")
def root_home():
    return FileResponse("myMapleSite/index.html")

@app.get("/home")
def home():
    return FileResponse("myMapleSite/index.html")

@app.post("/freeze-thaw")
async def get_freeze_thaw_data(request: Request):

    
    body = await request.json()
    print(body)
    address = body["location"]
    lat, lon = get_coordinates(address)

    if lon == -79.7599366 and lat == 43.685832:
        data = {
            "start_date_freeze_thaw": '2026-03-04',
            "pick_date": '2026-03-07',
            "end_date_freeze_thaw": '2026-04-03',
            "lat": 43.685832,
            "lon": -79.7599366
        }
        return JSONResponse(content=data)

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
    pick_date = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=int(index_value))

    data = {
        "start_date_freeze_thaw": str(start_date),
        "pick_date":  str(pick_date),
        "end_date_freeze_thaw": str(end_date),
        "long": lon,
        "lat": lat
    }

    print(data)

    modis_df_final = pd.DataFrame(data)
    print(modis_df_final.head(10))
    try:
        return JSONResponse(content=data)
    except Exception as e:
        print(e)

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

    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Perform timedelta operations
    hist_start = start_date_dt - timedelta(days=2 * 365)
    hist_end = end_date_dt - timedelta(days=2 * 365)

    fetcher = SmapFetcher(
        lat=lat,
        lon=long,
        start_date=str(hist_start),
        end_date=str(hist_end)
    )

    hist_df = fetcher.fetch_range()
    print("Historical records:", len(hist_df))

    pred_start = start_date
    pred_end = end_date

    normalized_future = fetcher.normalized_prediction(pred_start, pred_end)
    print("\nNormalized predicted soil moisture:")
    print(normalized_future)


    return normalized_future

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


app.mount("/", StaticFiles(directory="myMapleSite"), name="static")


if __name__ == "__main__":
    print(get_freeze_thaw_data(address= 'Brampton, Canada'))

