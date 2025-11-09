import ee
import datetime
import pandas as pd
import numpy as np


class SmapFetcher:
    """Fetch and normalize SMAP L4 (NASA/SMAP/SPL4SMGP/008) surface soil moisture data."""

    def __init__(self, lat, lon, start_date, end_date,
                 project='bramhackstest', buffer_km=9):
        """
        Initialize the fetcher with coordinates, date range, and optional buffer size.

        Parameters
        ----------
        lat : float
            Latitude of point of interest.
        lon : float
            Longitude of point of interest.
        start_date : str or datetime-like
            Start date for the historical time series (e.g., '2022-02-01').
        end_date : str or datetime-like
            End date for the historical time series (e.g., '2024-02-15').
        project : str
            Earth Engine project ID.
        buffer_km : float
            Buffer radius around the point, in kilometers.
        """
        # Initialize Earth Engine
        try:
            ee.Initialize(project=project)
        except Exception:
            ee.Authenticate()
            ee.Initialize(project=project)

        self.lon = lon
        self.lat = lat
        # NOTE: Earth Engine expects [lon, lat]
        self.roi = ee.Geometry.Point([lon, lat]).buffer(buffer_km * 1000)

        self.start_date = pd.to_datetime(start_date).date()
        self.end_date = pd.to_datetime(end_date).date()
        self.collection = ee.ImageCollection("NASA/SMAP/SPL4SMGP/008")

        # Will hold the historical dataframe once fetched
        self.df: pd.DataFrame | None = None

    def _extract_feature(self, img):
        """Extract surface soil moisture from a single image as a Feature."""
        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=self.roi,
            scale=11000,
            maxPixels=1e9
        )
        date = ee.Date(img.get('system:time_start'))
        return ee.Feature(
            None,
            {
                "date": date.format("YYYY-MM-dd"),
                "sm_surface": stats.get("sm_surface"),
            }
        )

    def fetch_range(self):
        """Fetch soil moisture data for the initialized date range and cache in self.df."""
        end_plus_one = self.end_date + datetime.timedelta(days=1)

        filtered = (
            self.collection
            .filterDate(self.start_date.isoformat(), end_plus_one.isoformat())
            # keep one hour (e.g., 00–01) to avoid multiple samples per day
            .filter(ee.Filter.calendarRange(0, 1, "hour"))
            .select(["sm_surface"])
        )

        features = filtered.map(self._extract_feature).filter(
            ee.Filter.notNull(["sm_surface"])
        )

        fc_dict = features.getInfo()
        rows = [f["properties"] for f in fc_dict.get("features", [])]

        if not rows:
            # No data returned
            self.df = pd.DataFrame(columns=["date", "sm_surface"])
            return self.df

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df["sm_surface"] = pd.to_numeric(df["sm_surface"], errors="coerce")
        df = df.sort_values("date").reset_index(drop=True)

        self.df = df[["date", "sm_surface"]]
        return self.df

    def normalize(self, df, column="sm_surface"):
        """
        Apply custom normalization to soil moisture values.

        The mapping is piecewise and returns values in [0, 1] with NaNs preserved.
        """
        def map_value(x):
            if x is None or pd.isna(x):
                return np.nan
            if x < 0.14:
                return 0
            elif 0.14 <= x <= 0.17:
                return 0.5
            elif 0.18 <= x <= 0.20:
                return 0.7
            elif 0.21 <= x <= 0.41:
                return 1
            elif 0.42 <= x <= 0.54:
                return 0.6
            elif x > 0.54:
                return 0.4
            return 0

        df = df.copy()
        norm_col = f"{column}_normalized"
        df[norm_col] = df[column].apply(map_value)
        return df[["date", norm_col]]

    def predict_weighted(self, start_date, end_date):
        """
        Predict future soil moisture using weighted temporal lags:
        1-day, 2-day, 1-year, and 2-year lags.

        Returns
        -------
        pandas.DataFrame
            Columns: ['date', 'predicted_sm_surface']
        """
        if self.df is None or self.df.empty:
            raise ValueError("Run fetch_range() first to load historical data.")

        df = self.df.copy().set_index("date")

        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        preds = []
        current_day = start_date

        while current_day <= end_date:
            lags = {
                "1d": current_day - datetime.timedelta(days=1),
                "2d": current_day - datetime.timedelta(days=2),
                "1y": current_day - datetime.timedelta(days=365),
                "2y": current_day - datetime.timedelta(days=730),
            }

            def get_sm(date):
                # exact match if available
                if date in df.index:
                    return float(df.loc[date, "sm_surface"])
                # otherwise, use nearest date
                idx = df.index.get_indexer([date], method="nearest")[0]
                return float(df.iloc[idx]["sm_surface"])

            vals = {key: get_sm(val) for key, val in lags.items()}

            pred = (
                0.35 * vals["1d"] +
                0.15 * vals["2d"] +
                0.30 * vals["1y"] +
                0.20 * vals["2y"]
            )

            preds.append(
                {
                    "date": current_day.normalize(),
                    "predicted_sm_surface": float(pred),
                }
            )

            # allow future predictions to be used as lags for the next days
            df.loc[current_day.normalize()] = pred
            current_day += datetime.timedelta(days=1)

        preds_df = pd.DataFrame(preds).sort_values("date").reset_index(drop=True)
        return preds_df

    def normalized_prediction(self, start_date, end_date):
        """
        Predict and normalize future soil moisture for the given range.

        Returns
        -------
        pandas.Series
            Normalized predicted soil moisture values for each date
            in [start_date, end_date].
        """
        preds_df = self.predict_weighted(start_date, end_date)
        df_norm = self.normalize(preds_df, column="predicted_sm_surface")
        return df_norm["predicted_sm_surface_normalized"]

    def main(self):
        """
        Fetch and normalize historical data for the original [start_date, end_date].

        Returns
        -------
        pandas.Series
            Normalized historical soil moisture series.
        """
        df_hist = self.fetch_range()
        if df_hist.empty:
            return pd.Series(name="sm_surface_normalized", dtype=float)

        df_norm = self.normalize(df_hist, column="sm_surface")
        return df_norm["sm_surface_normalized"]


if __name__ == "__main__":
    # Simple sanity check
    hist_start = "2022-02-01"
    hist_end = "2024-02-15"
    lat, lon = 51.779472, -81.417514

    fetcher = SmapFetcher(
        lat=lat,
        lon=lon,
        start_date=hist_start,
        end_date=hist_end
    )

    hist_df = fetcher.fetch_range()
    print("Historical records:", len(hist_df))

    pred_start = "2026-02-01"
    pred_end = "2026-02-15"

    normalized_future = fetcher.normalized_prediction(pred_start, pred_end)
    print("\nNormalized predicted soil moisture:")
    print(normalized_future)