#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to services.
"""
from gluon.contrib.simplejson import dumps


class ServiceErrorHandler(object):
    """Class representing a handler for service errors."""

    def __init__(self, message='', return_data=None, json=False):
        """Constructor

        Args:
            message: string, the default error message
            return_data: dict, __call__ returns a dict
                {'error': 'error message'}.
                It will be updated to include this data. For example,
                the 'success' value can be set or cleared.
            json: If True, result data is json encoded.
        """
        self.message = message
        self.return_data = return_data
        self.json = json
        self.error_messages = []
        if self.message:
            self.error_messages.append(self.message)

    def __call__(self, message):
        """Format the return data including the error.

        Args:
            message: string, message appended to error messages.
                Multiple calls can be made to accumulate messages.
        """
        self.error_messages.append(message)
        error_msg = ' '.join(self.error_messages)
        result = {}
        if self.return_data:
            result.update(self.return_data)
        result.update(error=error_msg)
        return dumps(result) if self.json else result
