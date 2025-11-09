import ee
import datetime
import pandas as pd
import numpy as np


class SmapFetcher:
    """Fetch and predict SMAP L4 (NASA/SMAP/SPL4SMGP/008) surface soil moisture data."""

    def __init__(self, lat, lon, project='bramhackstest', buffer_km=9):
        """Initialize the fetcher with coordinates and optional buffer size."""
        try:
            ee.Initialize(project=project)
        except Exception:
            ee.Authenticate()
            ee.Initialize(project=project)

        self.lon = lon
        self.lat = lat
        self.roi = ee.Geometry.Point([lon, lat]).buffer(buffer_km * 1000)
        self.collection = ee.ImageCollection("NASA/SMAP/SPL4SMGP/008")

    def _extract_feature(self, img):
        """Helper to extract surface soil moisture from one image."""
        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=self.roi,
            scale=11000,
            maxPixels=1e9
        )
        date = ee.Date(img.get('system:time_start'))
        return ee.Feature(None, {
            'date': date.format('YYYY-MM-dd'),
            'sm_surface': stats.get('sm_surface')
        })

    def fetch_last_2years(self):
        """Fetch 13 UTC soil-moisture data for the past 2 years."""
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=2 * 365)

        filtered = (
            self.collection
            .filterDate(start_date.isoformat(), (end_date + datetime.timedelta(days=1)).isoformat())
            .filter(ee.Filter.calendarRange(13, 13, 'hour'))  # 13 UTC (~13:30)
            .select(['sm_surface'])
        )

        features = filtered.map(self._extract_feature)
        fc_dict = features.getInfo()
        rows = [f['properties'] for f in fc_dict['features']]

        df = pd.DataFrame(rows)
        df['date'] = pd.to_datetime(df['date'])
        df['sm_surface'] = pd.to_numeric(df['sm_surface'], errors='coerce')
        df = df.sort_values('date').reset_index(drop=True)
        return df[['date', 'sm_surface']]

    def normalize(self, df, column='sm_surface'):
        """Apply custom normalization to soil moisture values based on defined ranges."""
        def map_value(x):
            if x is None or pd.isna(x):
                return np.nan
            if x < 0.14:
                return 0
            elif 0.14 <= x <= 0.17:
                return 0.5
            elif 0.18 <= x <= .20:
                return 0.7
            elif 0.21 <= x <= 0.41:
                return 1
            elif 0.42 <= x <= 0.46:
                return 0.6
            elif x > 0.47:
                return 0
            else:
                return 0

        df = df.copy()
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame.")

        df[f'{column}_normalized'] = df[column].apply(map_value)
        return df[['date', f'{column}_normalized']]
    
    def main(self):
        df_hist = self.fetch_last_2years()
        df_norm = self.normalize(df_hist, column='sm_surface')
        return df_norm["sm_surface_normalized"]


if __name__ == "__main__":
    # Example usage
    lat = 52.067712
    lon = -81.296853
    fetcher = SmapFetcher(lat=lat, lon=lon)
    normalized = fetcher.main()
    print(normalized)
