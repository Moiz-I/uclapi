import json
import os
from binascii import hexlify

import redis
from django.conf import settings
from django.test import TestCase

from .occupeye.api import OccupEyeApi
from .occupeye.cache import OccupeyeCache
from .occupeye.constants import OccupEyeConstants
from .occupeye.exceptions import BadOccupEyeRequest
from .occupeye.token import (
    get_bearer_token,
    token_valid
)


class OccupEyeTokenTestCase(TestCase):
    def setUp(self):
        self.r = redis.Redis(
            host=settings.REDIS_UCLAPI_HOST,
            charset="utf-8",
            decode_responses=True
        )
        self._consts = OccupEyeConstants()

        # Ensure we have no tokens in Redis yet
        self.r.delete(
            self._consts.ACCESS_TOKEN_KEY
        )
        self.r.delete(
            self._consts.ACCESS_TOKEN_EXPIRY_KEY
        )

        # Instantiate the OccupEye API in test mode
        self.api = OccupEyeApi()

    def test_tokens_empty(self):
        # The Redis get functions should return None values
        self.assertEqual(
            self.r.get(self._consts.ACCESS_TOKEN_KEY),
            None
        )
        self.assertEqual(
            self.r.get(self._consts.ACCESS_TOKEN_EXPIRY_KEY),
            None
        )

    def test_token_expiry(self):
        access_token = "blahblah"
        access_token_expiry = 1
        self.assertFalse(
            token_valid(access_token, access_token_expiry)
        )
        # 1st January 2100. I"d be honoured if this code is still
        # being run 83 years from now!
        access_token_expiry = 4102444800
        self.assertTrue(
            token_valid(access_token, access_token_expiry)
        )

    def test_bearer_token_generator(self):
        # Generate a random token then check that the bearer string
        # is properly formed
        random_data = hexlify(os.urandom(30)).decode()
        access_token = random_data
        access_token_expiry = 4102444800
        self.assertEqual(
            get_bearer_token(
                access_token,
                access_token_expiry,
                self._consts
            ),
            "Bearer " + random_data
        )


class OccupEyeApiTestCase(TestCase):
    def setUp(self):
        self.r = redis.Redis(
            host=settings.REDIS_UCLAPI_HOST,
            charset="utf-8",
            decode_responses=True
        )
        self._consts = OccupEyeConstants()
        self.api = OccupEyeApi()
        self.cache = OccupeyeCache()

        # Create some sample data
        data_lpush = {
            self._consts.SURVEYS_LIST_KEY: [9991, 9992, 9993],
            self._consts.SURVEY_SENSORS_LIST_KEY.format(9991): [6666661],
            self._consts.SURVEY_MAPS_LIST_KEY.format(9991): [3331],
            self._consts.SURVEY_MAP_SENSORS_LIST_KEY.format(9991, 3331): [
                6666661],
        }
        data_set = {
            self._consts.SURVEY_DATA_KEY.format(9991): {
                "id": 9991,
                "active": str(True),
                "name": "test survey 1",
                "start_time": "10:00",
                "end_time": "12:00",
                "staff_survey": str(False),
                "lat": "3.14159",
                "long": "-0.500100",
                "address1": "some building",
                "address2": "some street",
                "address3": "some city",
                "address4": "postcode please"
            },
            self._consts.SURVEY_DATA_KEY.format(9992): {
                "id": 9992,
                "active": str(False),
                "name": "test survey 2",
                "start_time": "09:00",
                "end_time": "17:00",
                "staff_survey": str(True),
                "lat": "2.14159",
                "long": "-1.500100",
                "address1": "some building2",
                "address2": "some street2",
                "address3": "some city2",
                "address4": "postcode please2"
            },
            self._consts.SURVEY_DATA_KEY.format(9993): {
                "id": 9993,
                "active": str(True),
                "name": "test survey 3",
                "start_time": "12:00",
                "end_time": "14:00",
                "staff_survey": str(False),
                "lat": "1.14159",
                "long": "-2.500100",
                "address1": "some building3",
                "address2": "some street3",
                "address3": "some city3",
                "address4": "postcode please3"
            },
            self._consts.IMAGE_BASE64_KEY.format(
                9991): "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQV"
                       "R42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
            self._consts.IMAGE_CONTENT_TYPE_KEY.format(9991): "image/png",
            self._consts.SURVEY_MAP_DATA_KEY.format(9991, 3331): {
                "id": "3331", "name": "E&ET", "image_id": "1115"
            },
            self._consts.SURVEY_MAP_SENSOR_PROPERTIES_KEY.format(9991, 3331,
                                                                 6666661): {
                "hardware_id": "6666661", "x_pos": "123.0", "y_pos": "321.0"
            },
            self._consts.SURVEY_SENSOR_DATA_KEY.format(9991, 6666661): {
                "survey_id": "9991", "hardware_id": "6666661",
                "survey_device_id": "3331",
                "host_address": "123", "pir_address": "8",
                "device_type": "Desk", "location": "",
                "description_1": "Teaching", "description_2": "",
                "description_3": "TT", "room_id": "275",
                "room_name": "B1.07", "share_id": "None", "floor": "-1",
                "room_type": "Room",
                "building_name": "The Testing", "room_description": ""
            },
            self._consts.SURVEY_SENSOR_STATUS_KEY.format(9991, 6666661): {
                "occupied": "False", "hardware_id": "6666661",
                "last_trigger_type": "Absent",
                "last_trigger_timestamp": "2020-10-16T09:38:22+01:00"
            },
            self._consts.SURVEY_MAX_TIMESTAMP_KEY.format(
                9991): "2020-11-12T00:55:16",
            self._consts.TIMEAVERAGE_KEY.format(9991,
                                                1): json.dumps(
                {"{}:{}:00".format(str(h).zfill(2), str(m).zfill(2)):
                 {"sensors_absent": m + (24 - h),
                  "sensors_occupied": h + (60 - m),
                  "sensors_total": 74} for h in range(0, 24, 1) for m in
                 range(0, 60, 10)}),
            self._consts.SURVEY_MAP_VMAX_X_KEY.format(9991, 3331): 123,
            self._consts.SURVEY_MAP_VMAX_Y_KEY.format(9991, 3331): 321,
            self._consts.SURVEY_MAP_VIEWBOX_KEY.format(9991,
                                                       3331): '0 0 1234 4321'
        }

        pipeline = self.r.pipeline()
        for key in list(data_lpush.keys()) + list(data_set.keys()):
            pipeline.delete(key)

        for key, value in data_lpush.items():
            for v in value:
                pipeline.lpush(key, v)
            # pipeline.expire(key, 20)

        for key, value in data_set.items():
            if type(value) is dict:
                pipeline.hmset(key, value)
            else:
                pipeline.set(key, value)

            # pipeline.expire(key, 20)
        pipeline.execute()
        self.cache.cache_common_summaries()

    def assert_nested(self, a, b):
        self.assertTrue(
            type(a) is type(b) or issubclass(type(a), type(b)) or issubclass(
                type(b), type(a)))
        if type(a) is list:
            self.assertEqual(len(a), len(b))
            for a_i, b_i in zip(a, b):
                self.assert_nested(a_i, b_i)
        elif type(b) is dict:
            self.assertListEqual(list(a.keys()), list(b.keys()))
            for key in a.keys():
                self.assert_nested(a[key], b[key])
        else:
            self.assertEqual(a, b)

    def test_check_survey_exists(self):
        self.assertTrue(self.api.check_survey_exists("9991"))
        self.assertFalse(self.api.check_survey_exists("9990"))

    def test_check_map_exists(self):
        self.assertTrue(self.api.check_map_exists("9991", "3331"))
        self.assertFalse(self.api.check_map_exists("9991", "3330"))
        self.assertFalse(self.api.check_map_exists("9990", "3331"))

    def test_get_surveys(self):
        surveys = self.api.get_surveys("all")
        # When the data comes from the actual API it is backwards
        surveys.reverse()
        self.assert_nested(surveys,
                           [{"id": 9991, "name": "test survey 1", "active": 1,
                             "start_time": "10:00",
                             "end_time": "12:00", "staff_survey": 0,
                             "location": {"coordinates": {"lat": "3.14159",
                                                          "lng": "-0.500100"},
                                          "address": ["some building",
                                                      "some street",
                                                      "some city",
                                                      "postcode please"]},
                             "maps": [{"id": 3331, "name": "E&ET",
                                       "image_id": 1115}]},
                            {"id": 9992, "name": "test survey 2", "active": 0,
                             "start_time": "09:00",
                             "end_time": "17:00", "staff_survey": 1,
                             "location": {"coordinates": {"lat": "2.14159",
                                                          "lng": "-1.500100"},
                                          "address": ["some building2",
                                                      "some street2",
                                                      "some city2",
                                                      "postcode please2"]},
                             "maps": []},
                            {"id": 9993, "name": "test survey 3", "active": 1,
                             "start_time": "12:00",
                             "end_time": "14:00", "staff_survey": 0,
                             "location": {"coordinates": {"lat": "1.14159",
                                                          "lng": "-2.500100"},
                                          "address": ["some building3",
                                                      "some street3",
                                                      "some city3",
                                                      "postcode please3"]},
                             "maps": []}])

    def test_get_image(self):
        self.assertRaises(BadOccupEyeRequest, self.api.get_image,
                          "hello_world")
        self.assertRaises(BadOccupEyeRequest, self.api.get_image,
                          "99999999999")
        image = self.api.get_image("9991")
        self.assertTupleEqual(image, (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABC"
            "AYAAAAfFcSJAAAADUlEQVR42mP8z8BQDw"
            "AEhQGAhKmMIQAAAABJRU5ErkJggg==",
            "image/png"))

    def test_get_survey_sensors(self):
        self.assertRaises(BadOccupEyeRequest, self.api.get_survey_sensors,
                          "hello_world")
        sensors = self.api.get_survey_sensors("9991")
        self.assert_nested(sensors,
                           {"maps": [{"id": "3331", "name": "E&ET",
                                      "image_id": "1115", "sensors": {
                                          "6666661":
                                          {
                                              "hardware_id": "6666661",
                                              "x_pos": "123.0",
                                              "y_pos": "321.0",
                                              "survey_id": "9991",
                                              "survey_device_id": "3331",
                                              "host_address": "123",
                                              "pir_address": "8",
                                              "device_type": "Desk",
                                              "location": "",
                                              "description_1": "Teaching",
                                              "description_2": "",
                                              "description_3": "TT",
                                              "room_id": "275",
                                              "room_name": "B1.07",
                                              "share_id": "None",
                                              "floor": "-1",
                                              "room_type": "Room",
                                              "building_name": "The Testing",
                                              "room_description": "",
                                              "last_trigger_timestamp":
                                              "2020-10-16T09:38:22+01:00",
                                              "last_trigger_type": "Absent",
                                              "occupied": False}}}],
                            "survey_id": "9991",
                            "survey_name": "test survey 1",
                            "most_recent_timestamp": "2020-11-12T00:55:16"})

    def test_get_max_survey_timestamp(self):
        self.assertRaises(BadOccupEyeRequest,
                          self.api.get_max_survey_timestamp,
                          "hello_world")
        self.assertRaises(BadOccupEyeRequest,
                          self.api.get_max_survey_timestamp,
                          "9990")
        self.assertTupleEqual(self.api.get_max_survey_timestamp("9991"),
                              (9991, "2020-11-12T00:55:16"))

    def test_get_survey_sensors_summary(self):
        self.assertRaises(BadOccupEyeRequest,
                          self.api.get_survey_sensors_summary, "hello_world",
                          "student")
        self.assertRaises(BadOccupEyeRequest,
                          self.api.get_survey_sensors_summary, "9991,9992",
                          "student")
        self.assertRaises(BadOccupEyeRequest,
                          self.api.get_survey_sensors_summary, "9991,9992",
                          "staff")
        self.assertRaises(BadOccupEyeRequest,
                          self.api.get_survey_sensors_summary, "9991", "staff")
        self.assertRaises(BadOccupEyeRequest,
                          self.api.get_survey_sensors_summary, "9992",
                          "student")
        summary_student = self.api.get_survey_sensors_summary("9991",
                                                              "student")
        self.assert_nested(summary_student,
                           [{"id": 9991, "name": "test survey 1", "maps": [
                               {"id": 3331, "name": "E&ET",
                                "sensors_absent": 1,
                                "sensors_occupied": 0, "sensors_other": 0}],
                             "staff_survey": 0, "sensors_absent": 1,
                             "sensors_occupied": 0,
                             "sensors_other": 0}])

        summary_all_student = self.api.get_survey_sensors_summary("9991,9993",
                                                                  "student")
        self.assert_nested(summary_all_student, [
            {"id": 9993, "name": "test survey 3", "maps": [],
             "staff_survey": 0,
             "sensors_absent": 0,
             "sensors_occupied": 0, "sensors_other": 0},
            {"id": 9991, "name": "test survey 1", "maps": [
                {"id": 3331, "name": "E&ET", "sensors_absent": 1,
                 "sensors_occupied": 0, "sensors_other": 0}],
             "staff_survey": 0, "sensors_absent": 1, "sensors_occupied": 0,
             "sensors_other": 0}])

        summary_staff = self.api.get_survey_sensors_summary("9992", "staff")
        self.assert_nested(summary_staff, [
            {"id": 9992, "name": "test survey 2", "maps": [],
             "staff_survey": 1,
             "sensors_absent": 0,
             "sensors_occupied": 0, "sensors_other": 0}])

    def test_get_historical_time_usage_data(self):
        historical = self.api.get_historical_time_usage_data("9991", 1,
                                                             "student")
        self.assert_nested(historical,
                           [{'survey_id': 9991, 'name': 'test survey 1',
                             'averages': {"{}:{}:00".format(str(h).zfill(2),
                                                            str(m).zfill(2)):
                                          {"sensors_absent": m + (24 - h),
                                           "sensors_occupied": h + (
                                              60 - m),
                                           "sensors_total": 74} for h in
                                          range(0, 24, 1) for m
                                          in range(0, 60, 10)}}])

    def test_get_survey_image_map_data(self):
        map_data = self.api.get_survey_image_map_data("9991", "3331")
        self.assert_nested(map_data, {'VMaxX': '123', 'VMaxY': '321',
                                      'ViewBox': '0 0 1234 4321'})
