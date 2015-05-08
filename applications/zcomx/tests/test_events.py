#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/events.py

"""
import datetime
import unittest
from gluon import *
from applications.zcomx.modules.events import \
    is_loggable, \
    log_download_click
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import entity_to_row


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    def test__is_loggable(self):
        now = request.now
        download_click_1 = self.add(db.download_click, dict(
            ip_address='111.111.111.111',
            auth_user_id=1,
            record_table='_table_1_',
            record_id=111,
            loggable=True,
            time_stamp=now,
        ))

        # Test: should not match itself.
        self.assertTrue(is_loggable(download_click_1))

        # Test: identical record should not be loggable.
        click_2 = dict(
            ip_address='111.111.111.111',
            auth_user_id=1,
            record_table='_table_1_',
            record_id=111,
            loggable=True,
            time_stamp=now,
        )

        download_click_2 = self.add(db.download_click, dict(click_2))
        self.assertFalse(is_loggable(download_click_2))

        # If first record is not loggable, then should be loggable.
        download_click_1.update_record(loggable=False)
        db.commit()
        self.assertTrue(is_loggable(download_click_2))

        # Reset
        download_click_1.update_record(loggable=True)
        db.commit()
        self.assertFalse(is_loggable(download_click_2))

        def test_mismatch(change):
            click_2_changed = dict(click_2)
            click_2_changed.update(change)
            download_click_2.update_record(**click_2_changed)
            db.commit()
            self.assertTrue(is_loggable(download_click_2))

        # Test mismatching each field in query
        test_mismatch(dict(ip_address='222.222.222.222'))
        test_mismatch(dict(auth_user_id=2))
        test_mismatch(dict(record_table='_table_2_'))
        test_mismatch(dict(record_id=222))

        # Reset
        download_click_2.update_record(**click_2)
        db.commit()
        self.assertFalse(is_loggable(download_click_2))

        # Test interval seconds.
        def set_time_stamp(increment_seconds):
            click_2_changed = dict(click_2)
            click_2_changed.update(dict(
                time_stamp=(
                    now + datetime.timedelta(seconds=increment_seconds))
            ))
            download_click_2.update_record(**click_2_changed)
            db.commit()

        set_time_stamp(1)
        self.assertFalse(is_loggable(download_click_2, interval_seconds=5))

        set_time_stamp(4)
        self.assertFalse(is_loggable(download_click_2, interval_seconds=5))

        set_time_stamp(5)
        self.assertTrue(is_loggable(download_click_2, interval_seconds=5))

        set_time_stamp(6)
        self.assertTrue(is_loggable(download_click_2, interval_seconds=5))

    def test__log_download_click(self):
        env = globals()
        request = env['request']
        auth = env['auth']
        test_ip = '000.111.111.333'
        request.client = test_ip

        query = (db.download_click.ip_address == test_ip)
        db(query).delete()
        db.commit()

        click_id = log_download_click('all', 0, queue_log_downloads=False)
        download_click = entity_to_row(db.download_click, click_id)
        self.assertTrue(download_click)
        self.assertEqual(download_click.ip_address, test_ip)
        self.assertEqual(download_click.loggable, is_loggable(download_click))
        self.assertEqual(download_click.completed, False)
        self._objects.append(download_click)

        click_id_2 = log_download_click('all', 0, queue_log_downloads=False)
        download_click_2 = entity_to_row(db.download_click, click_id_2)
        self.assertEqual(download_click_2.ip_address, test_ip)
        self.assertEqual(download_click_2.loggable, False)
        self.assertEqual(download_click_2.completed, True)
        self._objects.append(download_click_2)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
