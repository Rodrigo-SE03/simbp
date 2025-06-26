import requests
import os

OW_API_KEY = os.getenv("OPEN_WEATHER_API_KEY")
URL_BASE = "https://api.openweathermap.org/data/2.5"


def get_rain(lat, lon):
    url = f"{URL_BASE}/weather?lat={lat}&lon={lon}&appid={OW_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return 0
    weather_data = response.json()
    if "rain" not in weather_data:
        return 0  # sem chuva

    rain_volume = weather_data["rain"].get("1h", 0)
    if rain_volume < 0.5:
        return 1  # chuva fraca
    elif rain_volume < 2:
        return 2  # chuva moderada
    else:
        return 3  # chuva forte
