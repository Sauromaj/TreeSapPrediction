import ee
import pandas as pd
from datetime import datetime, timedelta

class PressureDataFetcher:

    def __init__(self, lat, lon, project='bramhackstest'):
        """Initialize the Earth Engine connection and location."""
        try:
            ee.Initialize(project=project)
        except Exception:
            ee.Authenticate()
            ee.Initialize(project=project)

        self.lat = lat
        self.lon = lon
        self.point = ee.Geometry.Point(lon, lat)
        self.dataset = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").select("surface_pressure")
        self.scale = 9000  # default ERA5-Land resolution

    def get_past_5years(self):
        """Fetches daily pressure (hPa) for the past 5 years up to today."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=5 * 365)

        #print(f"Fetching daily pressure data {start_date} → {end_date}")

        # Filter dataset by date
        collection = self.dataset.filterDate(str(start_date), str(end_date))

        # Reduce to point values (convert Pa → hPa)
        def extract(image):
            val = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=self.point,
                scale=self.scale
            ).get("surface_pressure")
            return ee.Feature(None, {
                "datetime": image.date().format("YYYY-MM-dd"),
                "pressure_hPa": ee.Number(val).divide(100)
            })

        features = collection.map(extract).filter(ee.Filter.notNull(["pressure_hPa"]))

        #print("Downloading from Earth Engine")

        # Aggregate values into arrays
        times = features.aggregate_array("datetime").getInfo()
        pressures = features.aggregate_array("pressure_hPa").getInfo()

        # Convert to DataFrame
        self.df = pd.DataFrame({
            "datetime": pd.to_datetime(times),
            "pressure_hPa": pressures
        }).sort_values("datetime").reset_index(drop=True)

        #print(f"Retrieved {len(self.df)} daily records.")
        return self.df

    def predict_weighted(self, start_date, end_date):
        if self.df is None:
            raise ValueError("Historical data not loaded. Run get_past_5years() first.")

        df = self.df.copy()
        df = df.set_index("datetime")

        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        preds = []
        current_day = start_date

        #print(f" Predicting {start_date.date()} → {end_date.date()} using weighted temporal lags...")

        while current_day <= end_date:
            # Collect lagged dates
            lags = {
                "1d": current_day - timedelta(days=1),
                "2d": current_day - timedelta(days=2),
                "1y": current_day - timedelta(days=365),
                "2y": current_day - timedelta(days=730),
                "3y": current_day - timedelta(days=1095),
                "4y": current_day - timedelta(days=1460),
                "5y": current_day - timedelta(days=1825),
            }

            def get_pressure(date):
                # Try to fetch exact or nearest date in df
                if date in df.index:
                    return df.loc[date, "pressure_hPa"]
                else:
                    nearest = df.index.get_indexer([date], method="nearest")
                    return df.iloc[nearest]["pressure_hPa"].values[0]

            # Retrieve lag values
            vals = {key: get_pressure(val) for key, val in lags.items()}

            # Apply weights
            pred = (
                    0.25 * vals["1d"] +
                    0.10 * vals["2d"] +
                    0.20 * vals["1y"] +
                    0.15 * vals["2y"] +
                    0.10 * vals["3y"] +
                    0.10 * vals["4y"] +
                    0.10 * vals["5y"]
            )

            preds.append({
                "date": current_day.date(),
                "predicted_pressure_hPa": round(pred, 2)
            })

            # Add new prediction to dataset so it can be used for subsequent lags
            df.loc[current_day] = pred
            current_day += timedelta(days=1)

        result = pd.DataFrame(preds)
        #print(f"✅ Generated {len(result)} predicted days.")
        return result

    def normalize_pressure(self, p):
        """Convert pressure to 0–1 sap flow potential."""
        if p < 990:
            return 1.0
        elif 990 <= p < 995:
            return 1.0 - ((p - 990) / 5) * 0.1
        elif 995 <= p < 1005:
            return 0.9 - ((p - 995) / 10) * 0.2
        elif 1005 <= p < 1013:
            return 0.7 - ((p - 1005) / 8) * 0.2
        elif 1013 <= p <= 1015:
            return 0.5 - ((p - 1013) / 2) * 0.25
        else:
            return 0.0

    def normalizedPrediction(self, start_date, end_date):
        preds = self.predict_weighted(start_date, end_date)
        preds["normalized_flow_score"] = preds["predicted_pressure_hPa"].apply(self.normalize_pressure)
        #print(f" Added normalized sap flow scores for {len(preds)} days.")
        return preds['normalized_flow_score']

if __name__ == "__main__":
    fetcher = PressureDataFetcher(lat=43.6532, lon=-79.3832)

    # Step 1 — Fetch historical data (faster with DAILY_AGGR)
    fetcher.get_past_5years()

    # Step 2 — Predict next month using weighted model
    results = fetcher.normalizedPrediction(start_date="2026-03-04", end_date="2026-03-30")

    print("\nPredicted Barometric Pressures:")
    print(results.head())
