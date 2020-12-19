import json
import pytz
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from datetime import datetime
from flask import render_template, request, redirect, url_for
from application import app, babel, api_key
from application.forms import AddressForm

lon, lat = None, None


@babel.localeselector
def get_locale():
    '''Get locale of user'''

    return request.accept_languages.best_match(['en', 'de', 'fr', 'es'])


def get_user_location():
    '''Get the user's current location'''

    if 'X-Forwarded-For' in request.headers:
        ip_address = request.headers['X-Forwarded-For']
    else:
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

    if ip_address == '127.0.0.1':
        ip_address = requests.get('http://ipecho.net/plain').text

    url = f'http://ip-api.com/json/{ip_address}'
    response = requests.get(url)
    text = response.json()

    if text['status'] == 'success':
        lat = text['lat']
        lon = text['lon']
        region_name = text['regionName']
        city = text['city']
        country = text['country']
        return lat, lon, region_name, city, country
    else:
        return None


def find_location(addr):
    '''Get latitude and longitude'''
    try:
        geolocator = Nominatim(user_agent='yourweather.cc', timeout=3)
        return geolocator.geocode(addr)
    except (GeocoderTimedOut, GeocoderServiceError):
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    '''Index route'''

    form = AddressForm()
    lat, lon, city, region_name, country = get_user_location()
    url = requests.get(f'https://api.openweathermap.org/data/2.5/onecall?'
                       f'lat={lat}&lon={lon}&appid={api_key}&units=imperial')
    if url.status_code == 200:
        report = url.text
        data = json.loads(report)
        json.dumps(data, ensure_ascii=False)
        icon_id = data['current']['weather'][0]['id']
        current_temp = data['current']['temp']
        current_forecast = data['current']['weather'][0]['description']
        current_low = data['daily'][0]['temp']['min']
        current_high = data['daily'][0]['temp']['max']
        current_weather = {
                'icon_id': icon_id,
                'current_temp': current_temp,
                'current_forecast': current_forecast,
                'current_low': current_low,
                'current_high': current_high,
                'city': city,
                'region_name': region_name,
                'country': country
                }
    if form.validate_on_submit():
        return redirect(url_for('get_weather_report'))
    return render_template('index.html', form=form, **current_weather)


@app.route('/weather', methods=['GET', 'POST'])
def get_weather_report():
    '''Display local weather report based on geolocation'''

    content = {}
    form = AddressForm()
    addr = request.form.get('address')
    location = find_location(addr)

    if location is None:
        return render_template('index.html', form=form,
                               message="Location Not Found")
    else:
        lat = location.latitude
        lon = location.longitude
        local_address = location.address
        url = requests.get(f'https://api.openweathermap.org/data/2.5/onecall?'
                           f'lat={lat}&lon={lon}&appid={api_key}&'
                           f'units=imperial')

        if url.status_code == 200:
            report = url.text
            data = json.loads(report)
            json.dumps(data, ensure_ascii=False)
            icon_id = data['current']['weather'][0]['id']
            temps = []
            hours = []
            forecast = []
            humidity = []
            wind_speed = []
            visibility = []
            pressure = []
            daily_high = []
            daily_low = []
            daily_datetime = []

            current_temp = data['current']['temp']
            current_forecast = data['current']['weather'][0]['description']
            tzone = data['timezone']
            current_low = data['daily'][0]['temp']['min']
            current_high = data['daily'][0]['temp']['max']
            sunrise = datetime.fromtimestamp(data['daily'][0]['sunrise'],
                                             tz=pytz.timezone(
                                             tzone)).strftime('%Hh:%Mm')
            sunset = datetime.fromtimestamp(data['daily'][0]['sunset'],
                                            tz=pytz.timezone(
                                            tzone)).strftime('%Hh:%Mm')

            for txt in data['hourly']:
                hours.append(datetime.fromtimestamp(txt['dt']).strftime("%H"))
                temps.append(txt['temp'])
                forecast.append(txt['weather'][0]['description'])
                humidity.append(txt['humidity'])
                wind_speed.append(txt['wind_speed'])
                visibility.append(txt['visibility'])
                pressure.append(txt['pressure'])

            for i in range(7):
                daily_high.append(data['daily'][i]['temp']['max'])
                daily_low.append(data['daily'][i]['temp']['min'])
                daily_datetime.append(datetime.fromtimestamp(
                                      data['daily'][i]['dt']).strftime(
                                      '%a %b %d'))

                content = {
                    'lat': lat,
                    'lon': lon,
                    'local_address': local_address,
                    'icon_id': icon_id,
                    'daily_high': daily_high,
                    'daily_low': daily_low,
                    'daily_datetime': daily_datetime,
                    'sunrise': sunrise,
                    'sunset': sunset,
                    'local_address': local_address,
                    'current_temp': current_temp,
                    'current_forecast': current_forecast,
                    'timezone': tzone,
                    'current_low': current_low,
                    'current_high': current_high,
                    'hours': hours,
                    'temps': temps,
                    'forecast': forecast,
                    'humidity': humidity,
                    'wind_speed': wind_speed,
                    'visibility': visibility,
                    'pressure': pressure
                    }
    return render_template('weather.html', form=form, **content)


@app.errorhandler(404)
def page_not_found(error):
    '''404 page not found route'''

    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    '''500 page not found route'''

    return render_template('500.html'), 500
