from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import pandas as pd
from twilio.rest import Client
import os

app = FastAPI(title="Freeze-Thaw Cycle API")

# --- Your Freeze-Thaw Endpoint ---
@app.get("/freeze-thaw")
def get_freeze_thaw_data():
    # Replace this with your real computed DataFrame
    data = {
        "start_date_freeze_thaw": ["2025-02-01", "2025-02-03", "2025-02-05"],
        "end_date_freeze_thaw": ["2025-02-02", "2025-02-04", "2025-02-06"],
        "LST_day_normalized": [0.76, 0.81, 0.68],
        "Pressure_day_normalized": [0.45, 0.53, 0.47],
        "soil_moisture_normalized": [0.62, 0.59, 0.64],
    }

    modis_df_final = pd.DataFrame(data)
    print(modis_df_final.head(10))

    result_json = modis_df_final.to_dict(orient="records")
    return JSONResponse(content=result_json)


# --- New SMS Endpoint ---
@app.post("/send-sms")
def send_sms(
    to: str = Form(...),
    message: str = Form(...)
):
    """
    Send an SMS to a user via Twilio.
    Example form body:
    {
        "to": "+15551234567",
        "message": "Freeze-thaw cycle detected!"
    }
    """

    # 🔒 Load Twilio credentials (set these as environment variables)
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
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to
        )
        return {"status": "success", "sid": msg.sid}
    except Exception as e:
        return JSONResponse(
            content={"status": "failed", "error": str(e)},
            status_code=400
        )
