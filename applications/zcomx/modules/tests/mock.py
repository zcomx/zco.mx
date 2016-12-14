#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Unit test mock classes and functions.
"""
import datetime


class DateMock(object):
    """Class representing a DateMock (context manager)"""

    def __init__(self, value):
        """Initializer

        Args:
            value: datetime.date instance
        """
        self.value = value
        self.save_date = None

    def __enter__(self):
        """Context manager 'enter' method.

        Returns:
            self: DateMock instance
        """
        self.save_date = datetime.date
        datetime.date = self.mocked_class()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager 'exit' method.

        Args:
            exc_type: exception type
            exc_value: exception value
            traceback: exception traceback

        Returns:
            True if no exceptions raised

        """
        datetime.date = self.save_date
        return True

    def mocked_class(self):
        """Return datetime.date subclass with today overridden."""
        # pylint: disable=no-self-use
        mocked_value = self.value

        class MockDate(datetime.date):
            """Class representing mock date"""
            @classmethod
            def today(cls):
                """Function to override datatime.date.today()"""
                return mocked_value

        return MockDate


class DateTimeMock(object):
    """Class representing a DateTimeMock (context manager)"""

    def __init__(self, value):
        """Initializer

        Args:
            value: datetime.datetime instance
        """
        self.value = value
        self.save_datetime = None

    def __enter__(self):
        """Context manager 'enter' method.

        Returns:
            self: DateTimeMock instance
        """
        self.save_datetime = datetime.datetime
        datetime.datetime = self.mocked_class()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager 'exit' method.

        Args:
            exc_type: exception type
            exc_value: exception value
            traceback: exception traceback

        Returns:
            True if no exceptions raised

        """
        datetime.datetime = self.save_datetime
        return True

    def mocked_class(self):
        """Return datetime.datetime subclass with now overridden."""
        # pylint: disable=no-self-use
        mocked_value = self.value

        class MockDatetime(datetime.datetime):
            """Class representing mock datetime"""
            @classmethod
            def now(cls):
                """Function to override datatime.datetime.now()"""
                return mocked_value

        return MockDatetime
