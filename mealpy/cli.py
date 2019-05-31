import getpass
import json
import time
from http.cookiejar import MozillaCookieJar

import click
import pendulum
import requests
import xdg

from mealpy import config
from mealpy.mealpy import MealPal

CACHE_HOME = xdg.XDG_CACHE_HOME / 'mealpy'
COOKIES_FILENAME = 'cookies.txt'


@click.group()
def cli():  # pragma: no cover
    config.initialize_directories()


@cli.command('reserve', short_help='Reserve a meal on MealPal.')
@click.argument('restaurant')
@click.argument('reservation_time')
@click.argument('city')
def reserve(restaurant, reservation_time, city):  # pragma: no cover
    execute_reserve_meal(restaurant, reservation_time, city)


def execute_reserve_meal(restaurant, reservation_time, city):
    mealpal = initialize_mealpal()

    while True:
        try:
            status_code = mealpal.reserve_meal(
                reservation_time,
                restaurant_name=restaurant,
                city_name=city,
            )
            if status_code == 200:
                print('Reservation success!')
                # print('Leave this script running to reschedule again the next day!')
                break
            else:
                print('Reservation error, retrying!')
        except IndexError:
            print('Retrying...')
            time.sleep(0.05)


@cli.group(name='list')
def cli_list():  # pragma: no cover
    pass


@cli_list.command('cities', short_help='List available cities.')
def cli_list_cities():  # pragma: no cover
    print('\n'.join(list_cities()))


def list_cities():
    cities_file = CACHE_HOME / 'cities.json'

    cities = []

    if cities_file.exists():
        cities_data = json.load(cities_file.open())
        cache_expire_date = pendulum.parse(cities_data['run_date']).add(hours=1)
        if pendulum.now() < cache_expire_date:
            cities = [i['name'] for i in cities_data['result']]

    if not cities:
        cities_data = MealPal.get_cities()
        json.dump({'run_date': str(pendulum.now()), 'result': cities_data}, cities_file.open('w'))

        cities = [i['name'] for i in cities_data]

    return cities


@cli_list.command('restaurants', short_help='List available restaurants.')
@click.argument('city')
def cli_list_restaurants(city):  # pragma: no cover
    restaurants = [i['restaurant']['name'] for i in list_menu(city)]
    print('\n'.join(restaurants))


@cli_list.command('meals', short_help='List meal choices.')
@click.argument('city')
def cli_list_meals(city):  # pragma: no cover
    restaurants = [i['meal']['name'] for i in list_menu(city)]
    print('\n'.join(restaurants))


def list_menu(city):
    """Return menu for the city.

    If there is cached data available, it will be used. Data is cached separately per-city and has a TTL of 1 hour.
    """
    menu_file = CACHE_HOME / 'menu.json'

    cached_data = {}
    result = []

    if menu_file.exists():
        cached_data = json.load(menu_file.open())

        city_data = cached_data.get(city)

        if city_data:
            cache_expire_date = pendulum.parse(city_data['run_date']).add(hours=1)

            if pendulum.now() < cache_expire_date:
                result = city_data['result']

    if not result:
        result = MealPal.get_schedules(city)
        cached_data[city] = {
            'run_date': str(pendulum.now()),
            'result': result,
        }
        json.dump(cached_data, menu_file.open('w'))

    return result


def get_mealpal_credentials():
    email = config.get_config()['email_address']
    password = getpass.getpass('Enter password: ')
    return email, password


def initialize_mealpal():
    cookies_path = CACHE_HOME / COOKIES_FILENAME
    mealpal = MealPal()
    mealpal.session.cookies = MozillaCookieJar()

    if cookies_path.exists():
        try:
            mealpal.session.cookies.load(cookies_path, ignore_expires=True, ignore_discard=True)
        except UnicodeDecodeError:
            pass
        else:
            # hacky way of validating cookies
            sleep_duration = 1
            for _ in range(5):
                try:
                    MealPal.get_schedules('San Francisco')
                except requests.HTTPError:
                    # Possible fluke, retry validation
                    print(f'Login using cookies failed, retrying after {sleep_duration} second(s).')
                    time.sleep(sleep_duration)
                    sleep_duration *= 2
                else:
                    print('Login using cookies successful!')
                    return mealpal

        print('Existing cookies are invalid, please re-enter your login credentials.')

    while True:
        email, password = get_mealpal_credentials()

        try:
            mealpal.login(email, password)
        except requests.HTTPError:
            print('Invalid login credentials, please try again!')
        else:
            break

    # save latest cookies
    print(f'Login successful! Saving cookies as {cookies_path}.')
    mealpal.session.cookies.save(cookies_path, ignore_discard=True, ignore_expires=True)

    return mealpal
