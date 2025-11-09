import ee
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime


def ret_normalized_land_temperature(start_date, end_date, lat, long, project = 'bramhackstest'):
    ee.Authenticate()
    ee.Initialize(project = project)

    # Example: Quebec maple forest area
    area = ee.Geometry.Point([lat, long]).buffer(5000)  # 5 km buffer

    # 1️⃣ MODIS Land Surface Temperature (MOD11A1)
    # LST values are scaled by 0.02 and originally in Kelvin

    # 1️⃣ Convert start_date to datetime
    start_date_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")

    # 2️⃣ Subtract 2 years
    start_date_2yrs_ago = start_date_dt.replace(year=start_date_dt.year - 2)

    new_start_date = start_date_2yrs_ago.strftime('%Y-%m-%d')

    end_date = datetime.datetime.today().strftime("%Y-%m-%d")

    modis = (
        ee.ImageCollection('MODIS/061/MOD11A1')
        .filterBounds(area)
        .filterDate(new_start_date, end_date)
        .select(['LST_Day_1km', 'LST_Night_1km'])
        .map(lambda img: img.multiply(0.02).subtract(273.15)  # Convert K → °C
            .copyProperties(img, ['system:time_start']))
    )

    # 2️⃣ SMAP Soil & Temperature Data
    # SMAP surface_temp and rootzone_temp are already in Kelvin (convert too)
    smap = (
        ee.ImageCollection('NASA/SMAP/SPL4SMGP/008')
        .filterBounds(area)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.listContains('system:band_names', 'rootzone_temp'))
        .select(['surface_temp', 'rootzone_temp', 
                'surface_soil_moisture', 'rootzone_soil_moisture'])
        .map(lambda img: img.addBands(
            img.select(['surface_temp', 'rootzone_temp']).subtract(273.15),  # Convert K → °C
            overwrite=True
        ))
    )

    # Extract mean values for each image
    modis_fc = modis.map(lambda img: ee.Feature(None, {
        'time': img.date().format('YYYY-MM-dd'),
        'LST_Day': img.select('LST_Day_1km').reduceRegion(
            ee.Reducer.mean(), area, 1000
        ).get('LST_Day_1km'),
        'LST_Night': img.select('LST_Night_1km').reduceRegion(
            ee.Reducer.mean(), area, 1000
        ).get('LST_Night_1km'),
    }))

    # Convert to DataFrames

    print(modis_fc)

    modis_list = modis_fc.getInfo()['features']

    modis_df = pd.DataFrame([f['properties'] for f in modis_list])

    print(modis_df)


    # --- Assume modis_df is your dataframe with ['time', 'LST_Day', 'LST_Night'] ---
    modis_df = modis_df.dropna(subset=['LST_Day', 'LST_Night']).copy()
    modis_df['time'] = pd.to_datetime(modis_df['time'])
    modis_df = modis_df.sort_values('time').reset_index(drop=True)

    # === Compute 5-year rolling daily climatology ===
    predictions = []

    start_date = pd.Timestamp('2026-02-01')
    end_date = pd.Timestamp('2026-04-01')

    # Create a list of all dates to fill
    all_dates = pd.date_range(start=start_date, end=end_date)

    predictions = []

    for current_date in all_dates:
        past_start = current_date - pd.DateOffset(years=2)
        past_end = current_date - pd.DateOffset(years=1)  # Up to last year
        
        past_data = modis_df[(modis_df['time'] >= past_start) & (modis_df['time'] <= past_end)]
        
        doy = current_date.dayofyear
        past_same_doy = past_data[past_data['time'].dt.dayofyear == doy]
        
        if len(past_same_doy) > 0:
            mean_day = past_same_doy['LST_Day'].mean()
            mean_night = past_same_doy['LST_Night'].mean()
        else:
            mean_day = np.nan
            mean_night = np.nan
        
        predictions.append({
            'date': current_date,
            'LST_Day_predicted': mean_day,
            'LST_Night_predicted': mean_night
        })

    # Create prediction DataFrame
    pred_df = pd.DataFrame(predictions)

    # Interpolate NaNs linearly
    pred_df['LST_Day_predicted'] = pred_df['LST_Day_predicted'].interpolate(method='linear')
    # pred_df['LST_Night_predicted'] = pred_df['LST_Night_predicted'].interpolate(method='linear')

    # Normalize between 0 and 1
    pred_df['LST_Day_normalized'] = (pred_df['LST_Day_predicted'] - pred_df['LST_Day_predicted'].min()) / \
                                    (pred_df['LST_Day_predicted'].max() - pred_df['LST_Day_predicted'].min())


    modis_df_final = pd.merge(modis_df, pred_df, left_on='time', right_on='date', how='right')
    print(modis_df_final.columns)
    modis_df_final = modis_df_final.rename(columns={'time': 'original_time'})
    modis_df_final = modis_df_final.loc[: ,['LST_Day_normalized', 'date', 'LST_Day_predicted']]


    print(modis_df_final.head(10))

    return modis_df_final['LST_Day_normalized']

# modis_df_final.to_csv('sap_temperature_timeseries_celsius_predicted.csv', index=False)


if __name__ == "__main__":
     # Sap flow season
    start_date = '2026-03-04'
    end_date   = '2026-03-30'
    lat, long = [-79.7599366, 43.685832]

    print(ret_normalized_land_temperature(start_date,end_date, lat, long, project = 'bramhackstest'))