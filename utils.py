import ssl
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError

def get_coordinates(address):
    geolocator = Nominatim(user_agent="geoapi", timeout=10)
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            return None
    except GeocoderServiceError as e:
        print(f"Geocoding error: {e}")
        return None

if __name__ == "__main__":
    address = '2 Wellington St W, Brampton, ON L6Y 4R2'
    print(get_coordinates(address))