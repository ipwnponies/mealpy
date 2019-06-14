import requests


BASE_DOMAIN = 'secure.mealpal.com'
BASE_URL = f'https://{BASE_DOMAIN}'
LOGIN_URL = f'{BASE_URL}/1/login'
CITIES_URL = f'{BASE_URL}/1/functions/getCitiesWithNeighborhoods'
MENU_URL = f'{BASE_URL}/api/v1/cities/{{}}/product_offerings/lunch/menu'
RESERVATION_URL = f'{BASE_URL}/api/v2/reservations'
KITCHEN_URL = f'{BASE_URL}/1/functions/checkKitchen3'


class MealPal:

    def __init__(self):
        self.session = requests.Session()

    def login(self, user, password):
        data = {
            'username': user,
            'password': password,
        }

        headers = {
            'Host': BASE_DOMAIN,
            'Origin': BASE_URL,
            'Referer': f'{BASE_URL}/login',
            'Content-Type': 'application/json',
        }

        request = self.session.post(
            LOGIN_URL,
            json=data,
            headers=headers,
        )

        request.raise_for_status()

    @staticmethod
    def get_cities():
        response = requests.post(CITIES_URL)
        response.raise_for_status()

        result = response.json()['result']

        return result

    @staticmethod
    def get_schedules(city_name):
        city_id = next((i['objectId'] for i in MealPal.get_cities() if i['name'] == city_name), None)
        request = requests.get(MENU_URL.format(city_id))
        request.raise_for_status()
        return request.json()['schedules']

    @staticmethod
    def get_schedule_by_restaurant_name(restaurant_name, city_name):
        restaurant = next(
            i
            for i in MealPal.get_schedules(city_name)
            if i['restaurant']['name'] == restaurant_name
        )
        return restaurant

    @staticmethod
    def get_schedule_by_meal_name(meal_name, city_name):
        return next(i for i in MealPal.get_schedules(city_name) if i['meal']['name'] == meal_name)

    def reserve_meal(
            self,
            timing,
            city_name,
            restaurant_name=None,
            meal_name=None,
            cancel_current_meal=False,
    ):  # pylint: disable=too-many-arguments
        assert restaurant_name or meal_name
        if cancel_current_meal:
            self.cancel_current_meal()

        if meal_name:
            schedule_id = MealPal.get_schedule_by_meal_name(meal_name, city_name)['id']
        else:
            schedule_id = MealPal.get_schedule_by_restaurant_name(restaurant_name, city_name)['id']

        reserve_data = {
            'quantity': 1,
            'schedule_id': schedule_id,
            'pickup_time': timing,
            'source': 'Web',
        }

        request = self.session.post(RESERVATION_URL, json=reserve_data)
        return request.status_code

    def get_current_meal(self):
        request = self.session.post(KITCHEN_URL)
        return request.json()

    def cancel_current_meal(self):
        raise NotImplementedError()
