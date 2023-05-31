#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
test_ConfigParser_improved.py

Test suite for modules/ConfigParser_improved.py
"""
import unittest
import io
from applications.zcomx.modules.ConfigParser_improved import \
    ConfigParserImproved
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring


class TestConfigParserImproved(LocalTestCase):

    def test__items_scrubbed(self):
        text = \
            """
[section]
s01_true = True
s02_false = False
s03_int = 123
s04_float = 123.45
s05_str1 = my setting value
s06_str2 = 'This is my setting value'
s07_str_true = 'True'
s08_str_int = '123'
s09_str_float = '123.45'

[strings]
str1 = my setting value
str2 = 'This is my setting value'

"""
        f = io.StringIO(text)
        config = ConfigParserImproved()
        config.read_file(f)
        self.assertEqual(
            config.items('strings'),
            config.items_scrubbed('strings')
        )

        self.assertEqual(
            sorted(config.items_scrubbed('section')),
            [
                ('s01_true', True),
                ('s02_false', False),
                ('s03_int', 123),
                ('s04_float', 123.45),
                ('s05_str1', 'my setting value'),
                ('s06_str2', "'This is my setting value'"),
                ('s07_str_true', 'True'),
                ('s08_str_int', '123'),
                ('s09_str_float', '123.45'),
            ]
        )


def _config_file_from_text(filename, text):
    """Create a config file with the provided text."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)


if __name__ == '__main__':
    unittest.main()
