import json
from unittest import mock

import pytest
from freezegun import freeze_time

from mealpy import cli
from mealpy import config
from mealpy import mealpy


class TestCLIListCities:

    @staticmethod
    @pytest.fixture(autouse=True)
    @pytest.mark.usefixtures('mock_fs')
    def setup_fakefs(mock_fs):
        """Setup up fake filesystem structure."""
        config.initialize_directories()

    @staticmethod
    @pytest.fixture(autouse=True)
    def pinned_time():
        """Time pinned to the test data.

        This makes tests deterministic.
        """
        with freeze_time('2019-05-09 20:00') as frozen_time:
            yield frozen_time

    @staticmethod
    @pytest.fixture
    def cities_json(mock_fs):
        contents = json.dumps({
            'run_date': '2019-05-09T20:00:00.000000-00:00',
            'result': [
                {'id': 'UID', 'name': 'San Francisco'},
            ],
        })

        mock_fs.create_file(
            config.CACHE_DIR / 'cities.json',
            contents=contents,
        )

    @staticmethod
    @pytest.fixture
    def mock_get_cities():
        with mock.patch.object(
                mealpy.MealPal,
                'get_cities',
                return_value=[
                    {
                        'name': 'city1',
                    },
                    {
                        'name': 'city2',
                    },
                ],
        ) as _mock:
            yield _mock

    @staticmethod
    @pytest.mark.usefixtures('mock_get_cities')
    def test_not_cached():
        result = cli.list_cities()

        assert result == ['city1', 'city2']
        assert (config.CACHE_DIR / 'cities.json').exists()

    @staticmethod
    @pytest.mark.usefixtures('cities_json')
    def test_use_cache(mock_get_cities):
        result = cli.list_cities()

        assert result == ['San Francisco']
        assert not mock_get_cities.called, 'Should not be called if using cache.'

    @staticmethod
    @pytest.mark.usefixtures('cities_json')
    def test_cache_invalidated(pinned_time, mock_get_cities):
        next_day = '2019-05-10T20:00:00.000000-00:00'
        pinned_time.move_to(next_day)

        result = cli.list_cities()

        assert result == ['city1', 'city2']
        assert mock_get_cities.called, "Cache should be ignored because it's stale."


class TestCLIListMenu:

    @staticmethod
    @pytest.fixture(autouse=True)
    @pytest.mark.usefixtures('mock_fs')
    def setup_fakefs(mock_fs):
        """Setup up fake filesystem structure."""
        config.initialize_directories()

    @staticmethod
    @pytest.fixture(autouse=True)
    def pinned_time():
        """Time pinned to the test data.

        This makes tests deterministic.
        """
        with freeze_time('2019-05-09 20:00') as frozen_time:
            yield frozen_time

    @staticmethod
    @pytest.fixture
    def menu_json(mock_fs):
        contents = json.dumps({
            'city2': {
                'run_date': '2019-05-09T20:00:00.000000-00:00',
                'result': 'CITY2 DATA',
            },
        })

        mock_fs.create_file(
            config.CACHE_DIR / 'menu.json',
            contents=contents,
        )

    @staticmethod
    def test_no_cache_file():
        """Cache file does not exist."""
        assert not (config.CACHE_DIR / 'menu.json').exists()

        with mock.patch.object(
                mealpy.MealPal,
                'get_schedules',
                return_value='DATA',
        ) as mock_get_schedules:
            cli.list_menu('city1')

            assert mock_get_schedules.called
        assert (config.CACHE_DIR / 'menu.json').exists()

    @staticmethod
    @pytest.mark.usefixtures('menu_json')
    def test_not_yet_cached():
        """Cache file exist but the selected city data is not in it yet."""
        assert (config.CACHE_DIR / 'menu.json').exists()

        with mock.patch.object(
                mealpy.MealPal,
                'get_schedules',
                return_value='DATA',
        ) as mock_get_schedules:
            cli.list_menu('city1')

            assert mock_get_schedules.called

    @staticmethod
    @pytest.mark.usefixtures('menu_json')
    def test_use_cache():
        """Cache file exist and city is in it. Use cache"""
        with mock.patch.object(
                mealpy.MealPal,
                'get_schedules',
        ) as mock_get_schedules:
            result = cli.list_menu('city2')

            assert result == 'CITY2 DATA'
            assert not mock_get_schedules.called, 'Should not be called if using cache.'

    @staticmethod
    @pytest.mark.usefixtures('menu_json')
    def test_cache_invalidated(pinned_time):
        next_day = '2019-05-10T20:00:00.000000-00:00'
        pinned_time.move_to(next_day)

        with mock.patch.object(
                mealpy.MealPal,
                'get_schedules',
                return_value='NOT CACHED DATA',
        ) as mock_get_schedules:
            result = cli.list_menu('city2')

            assert result == 'NOT CACHED DATA'
            assert mock_get_schedules.called, "Cache should be ignored because it's stale."
