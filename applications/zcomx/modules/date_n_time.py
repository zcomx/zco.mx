#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
date_n_time.py

Classes and functions related to dates and times.
"""
import datetime
import pytz

from applications.zcomx.modules.my.constants import (
    SECONDS_PER_MINUTE,
    SECONDS_PER_HOUR,
    SECONDS_PER_DAY,
    DAYS_PER_YEAR,
)


def age(timestamp, units='years', rounded=True, today=None):
    """Return the age of a date.

    Args:
        timestamp: The following formats are supported:
            datetime.date instance
            datetime.datetime instance
            datetime string 'yyyy-mm-dd hh:mm:ss'
            date string 'yyyy-mm-dd'
        units: one of 'years', 'days', 'seconds'
        rounded: If true, an integer is returned.
        today: datetime.date instance representing today. Useful for testing.
            Defaults to datetime.date.today()

    Returns
        float or integer, age of timestamp.

    Notes
        * If timestamp is in the future, a negative age is returned.
        * If timestamp is a date, the age is taken as of midnight that day,
            ie hh:mm:ss = 00:00:00
    """
    if not timestamp:
        return 0
    if units not in ['years', 'days', 'seconds']:
        raise SyntaxError('Invalid units')

    # Convert the timestamp to a datetime.datetime instance
    datetime_stamp = None
    if hasattr(timestamp, 'now'):
        datetime_stamp = timestamp
    else:
        if hasattr(timestamp, 'today'):
            # We have a datetime.date
            datetime_stamp = datetime.datetime.combine(
                timestamp, datetime.time(0, 0, 0))
        elif timestamp is not None:
            # Assume we have a string
            datetime_stamp = str_to_datetime(str(timestamp))
            if not datetime_stamp:
                try:
                    datetime_stamp = datetime.datetime.combine(
                        str_to_date(str(timestamp)),
                        datetime.time(0, 0, 0))
                except TypeError:
                    # Invalid timestamp
                    pass

    if not datetime_stamp:
        raise SyntaxError('Unsupported timestamp')

    # Convert today to datetime.datetime.
    datetime_today = None
    if not today:
        datetime_today = datetime.datetime.now()
    else:
        if hasattr(today, 'now'):
            datetime_today = today
        elif not hasattr(today, 'now'):
            if hasattr(today, 'today'):
                datetime_today = datetime.datetime.combine(
                    today, datetime.time(0, 0, 0))
            elif today is not None:
                # Assume we have a string
                datetime_today = str_to_datetime(str(today))
                if not datetime_today:
                    try:
                        datetime_today = datetime.datetime.combine(
                            str_to_date(str(today)),
                            datetime.time(0, 0, 0))
                    except TypeError:
                        # Invalid timestamp
                        pass

    if not datetime_today:
        raise SyntaxError('Unsupported timestamp')

    delta = (datetime_today - datetime_stamp)
    if units == 'seconds':
        age_in_units = delta.total_seconds()
    else:
        age_in_units = delta.days
        if units == 'years':
            age_in_units = age_in_units / DAYS_PER_YEAR

    return int(age_in_units) if rounded else age_in_units


def english_delta(datetime1, datetime2, zeros=True, max_attributes=0):
    """Return the difference of two datetimes in english

    Args
        datetime1: datetime instance
        datetime2: datetime instance
        max_attributes: integer, Maximum number of date attributes. If 0, there
            is no maximum. Of the non-zero attributes, starting from the
            smallest attribute, seconds, and up, truncate until
            number of attributes <= max_attributes
        zeros: if True, include all attributes even if zero.

    Examples:
        datetime1               datetime2   max_attributes  result
        2011-01-01 12:30:00 2011-01-01 13:31:30 0 1 hour, 1 minute, 30 seconds
        2011-01-01 12:30:00 2011-01-01 13:31:30 2 1 hour, 1 minute
        2011-01-01 12:30:00 2011-01-01 13:31:30 1 1 hour
    """
    # 1 minute(s)  2 minutes
    diff = datetime1 - datetime2
    return english_seconds(
        int(diff.total_seconds()),
        zeros=zeros,
        max_attributes=max_attributes
    )


def english_seconds(seconds, zeros=True, max_attributes=0):
    """Convert seconds to a time value in english

    Args
        seconds: integer, number of seconds
        max_attributes: integer, Maximum number of date attributes. If 0, there
            is no maximum. Of the non-zero attributes, starting from the
            smallest attribute, seconds, and up, truncate until
            number of attributes <= max_attributes
        zeros: if True, include all attributes even if zero.

    Examples:
        seconds    max_attributes  result
        3690         0             1 hour, 1 minute, 30 seconds
        3690         2             1 hour, 1 minute
        3690         1             1 hour
    """
    # 1 minute(s)  2 minutes
    raw_units = ['day', 'hour', 'minute', 'second']

    def _pluralize(count, word):
        """Make a work plural if applicable."""
        if count == 1:
            return word
        return ''.join([word, 's'])

    days, remainder = divmod(seconds, SECONDS_PER_DAY)
    hours, remainder = divmod(remainder, SECONDS_PER_HOUR)
    minutes, seconds = divmod(remainder, SECONDS_PER_MINUTE)

    attributes = [days, hours, minutes, seconds]
    units = [_pluralize(attributes[c], w) for c, w in enumerate(raw_units)]

    results = [
        ' '.join([str(w), units[c]])
        for c, w in enumerate(attributes)
    ]
    if not zeros:
        new_results = []
        if days != 0:
            new_results.append(results[0])
        if hours != 0:
            new_results.append(results[1])
        if minutes != 0:
            new_results.append(results[2])
        if seconds != 0 or not new_results:
            new_results.append(results[3])
        results = new_results
    if max_attributes:
        if len(results) > max_attributes:
            results = results[: max_attributes - len(results)]
    return ', '.join(results)


def enumerate_month_dates(start_date, end_date):
    """Generator of (start date, end date) tuples of months between to dates.

    Args:
        start_date: datetime.date instance
        end_date: datetime.date instance
    """
    current = start_date
    while current <= end_date:
        if current.month >= 12:
            next_current = datetime.date(current.year + 1, 1, 1)
        else:
            next_current = datetime.date(current.year, current.month + 1, 1)
        last = min(next_current - datetime.timedelta(1), end_date)
        yield current, last
        current = next_current


def enumerate_year_dates(start_date, end_date):
    """Generator of (start date, end date) tuples of years between to dates.

    Args:
        start_date: datetime.date instance
        end_date: datetime.date instance
    """
    current = start_date
    while current <= end_date:
        next_current = datetime.date(current.year + 1, 1, 1)
        last = min(next_current - datetime.timedelta(1), end_date)
        yield current, last
        current = next_current


def is_day_of_week(date, day_of_week):
    """Determine if a date is a specific day of the week.

    Args:
        date: datetime.date instance
        day_of_week: str, either full day of the week name or abbr
            Eg 'Mon', 'Monday'

    Returns:
        True if the date matches the weekday.
    """
    fmt = '%A' if len(day_of_week) > 3 else '%a'
    return date.strftime(fmt) == day_of_week


def month_first_last(any_date):
    """Return the first day and last day of the month any_date is in.

    Args:
        any_date: datetime.date instance, if None, datetime.date.today() is
            used

    Returns:
        tuple, (datetime.date, datetime.date): (first day, last day)
    """
    first_of_month = any_date.replace(day=1)
    next_month = any_date.replace(day=28) + datetime.timedelta(days=4)
    last_of_month = next_month - datetime.timedelta(days=next_month.day)
    return (first_of_month, last_of_month)


def str_to_date(date_as_str):
    """Convert a string yyyy-mm-dd to a datetime.date() instance"""
    try:
        return datetime.datetime.strptime(date_as_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def str_to_datetime(datetime_as_str):
    """Convert a string 'yyyy-mm-dd hh:mm:ss' to a datetime.datetime()
    instance"""
    try:
        return datetime.datetime.strptime(datetime_as_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def utc_to_localtime(date_time, zone='America/Toronto'):
    """Convert a UTC time to localtime.

    Args:
        date_time: datetime.datetime instance
        zone: str, the localtime zone

    Returns:
        datetime instance in localtime
    """
    time_zone = pytz.timezone(zone)
    utc_dt = datetime.datetime(
        date_time.year,
        date_time.month,
        date_time.day,
        date_time.hour,
        date_time.minute,
        date_time.second,
        tzinfo=pytz.utc
    )
    loc_dt = utc_dt.astimezone(time_zone)
    # Convert loc_dt to a standard datetime.datetime
    return datetime.datetime(
        loc_dt.year,
        loc_dt.month,
        loc_dt.day,
        loc_dt.hour,
        loc_dt.minute,
        loc_dt.second,
    )
