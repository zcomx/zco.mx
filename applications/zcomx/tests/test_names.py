#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/names.py
"""
import unittest
from gluon import *
from applications.zcomx.modules.names import (
    BaseName,
    BookName,
    BookNumber,
    BookTitle,
    CreatorName,
    names,
)
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class MockBookName(BaseName):
    def for_file(self):
        return self.name + ' name for file!'

    def for_search(self):
        return self.name + ' name for search!'

    def for_url(self):
        return self.name + ' name for url!'


class MockBookNumber(BaseName):
    def for_file(self):
        return self.name + ' number for file!'

    def for_search(self):
        return self.name + ' number for search!'

    def for_url(self):
        return self.name + ' number for url!'


class MockBookNumberBlanks(BaseName):
    def for_file(self):
        return ''

    def for_search(self):
        return ''

    def for_url(self):
        return ''


class TestBaseName(LocalTestCase):

    def test____init__(self):
        name = BaseName('First Last')
        self.assertTrue(name)

    def test__for_file(self):
        name = BaseName('First Last')
        self.assertRaises(NotImplementedError, name.for_file)

    def test__for_search(self):
        # Test variations
        tests = [
            # (name, expect)
            (None, None),
            ('', ''),
            # creator names
            ('John Adams-Smith', 'john-adams-smith'),
            ("Joanne d'Arc", 'joanne-darc'),
            ("Jean-Luc de'Breu", 'jean-luc-debreu'),
            ('Don Al François de Sade', 'don-al-francois-de-sade'),
            ('Herbert von Locke', 'herbert-von-locke'),
            ('Edwin van der Sad', 'edwin-van-der-sad'),
            ("Slèzé d'Ruñez", 'sleze-drunez'),
            # book names
            ('Image Test Case', 'image-test-case'),
            ('__test__defaults__', 'test-defaults'),
        ]
        for t in tests:
            self.assertEqual(BaseName(t[0]).for_search(), t[1])

    def test__for_url(self):
        tests = [
            # (name, expect)
            (None, None),
            ('', ''),
            # creator names
            ('Prince', 'Prince'),
            ('First Last', 'FirstLast'),
            ('first last', 'FirstLast'),
            ('SørenMosdal', 'SørenMosdal'),
            ("Hélè d'Eñça", 'HélèDEñça'),
            # book names
            ('My Book', 'MyBook'),
            ('Tepid: Fall 2003', 'TepidFall2003'),
            ("My Book's Trials", 'MyBooksTrials'),
            ('    My    Book   ', 'MyBook'),
        ]

        for t in tests:
            self.assertEqual(BaseName(t[0]).for_url(), t[1])


class TestBookName(LocalTestCase):

    def test____init__(self):
        name = BookName('First Last')
        self.assertTrue(name)

    def test__for_file(self):
        tests = [
            # (name, expect)
            (None, None),
            ('', ''),
            ('My Book', 'My Book'),
            ('Tepid: Fall 2003', 'Tepid - Fall 2003'),
            ("Hélè d'Eñça", "Hélè d'Eñça"),
            ("My Book's Trials", "My Book's Trials"),
            ('    My    Book   ', 'My Book'),
        ]

        for t in tests:
            self.assertEqual(BookName(t[0]).for_file(), t[1])


class TestBookNumber(LocalTestCase):

    def test____init__(self):
        # Typical one-shot
        number = BookNumber('')
        self.assertTrue(number)

        # Typical ongoing
        number = BookNumber('001')
        self.assertTrue(number)

        # Typical mini-series
        number = BookNumber('01 (of 04)')
        self.assertTrue(number)

    def test__for_url(self):
        # Typical one-shot
        number = BookNumber('')
        self.assertEqual(number.for_url(), '')

        # Typical ongoing
        number = BookNumber('001')
        self.assertEqual(number.for_url(), '001')

        # Typical mini-series
        number = BookNumber('01 (of 04)')
        self.assertEqual(number.for_url(), '01of04')


class TestBookTitle(LocalTestCase):

    def test____init__(self):
        book_name = MockBookName('My Book')
        book_number = MockBookNumber('num 001')
        title = BookTitle(book_name, book_number)
        self.assertTrue(title)

    def test__for_file(self):
        book_name = MockBookName('My Book')
        book_number = MockBookNumber('num 001')
        title = BookTitle(book_name, book_number)
        self.assertEqual(
            title.for_file(),
            'My Book name for file! num 001 number for file!'
        )

        # Test strips trailing whitespace
        book_number = MockBookNumberBlanks('num 001')
        title = BookTitle(book_name, book_number)
        self.assertEqual(
            title.for_file(),
            'My Book name for file!'
        )

    def test__for_search(self):
        book_name = MockBookName('My Book')
        book_number = MockBookNumber('num 001')
        title = BookTitle(book_name, book_number)
        self.assertEqual(
            title.for_search(),
            'My Book name for search!-num 001 number for search!'
        )

        # Test strips trailing '-'
        book_number = MockBookNumberBlanks('num 001')
        title = BookTitle(book_name, book_number)
        self.assertEqual(
            title.for_search(),
            'My Book name for search!'
        )

    def test__for_url(self):
        book_name = MockBookName('My Book')
        book_number = MockBookNumber('num 001')
        title = BookTitle(book_name, book_number)
        self.assertEqual(
            title.for_url(),
            'My Book name for url!-num 001 number for url!'
        )

        # Test strips trailing '-'
        book_number = MockBookNumberBlanks('num 001')
        title = BookTitle(book_name, book_number)
        self.assertEqual(
            title.for_url(),
            'My Book name for url!'
        )


class TestCreatorName(LocalTestCase):

    def test____init__(self):
        name = CreatorName('First Last')
        self.assertTrue(name)

    def test__for_file(self):
        tests = [
            # (name, expect)
            (None, None),
            ('', ''),
            ('Fred Smith', 'FredSmith'),
            ("Sean O'Reilly", 'SeanOReilly'),
            ('John Adams-Smith', 'JohnAdamsSmith'),
            ('Willem deBoer', 'WillemDeBoer'),
            ("Joanne d'Arc", 'JoanneDArc'),
            ("Jean-Luc de'Breu", 'JeanLucDeBreu'),
            ('Herbert von Locke', 'HerbertVonLocke'),
            ('Sander van Dorn', 'SanderVanDorn'),
            ('Edwin van der Sad', 'EdwinVanDerSad'),
            ('J.P. Parise', 'JPParise'),
            ('J. P. Parise', 'JPParise'),

            # Unicode should be preserved in these.
            ('Sverre Årnes', 'SverreÅrnes'),
            ('Bjørn Eidsvåg', 'BjørnEidsvåg'),
            ('Frode Øverli', 'FrodeØverli'),
            ('Dražen Kovačević', 'DraženKovačević'),
            ('Yıldıray Çınar', 'YıldırayÇınar'),
            ('Alain Saint-Ogan', 'AlainSaintOgan'),
            ('José Muñoz', 'JoséMuñoz'),
            ('Ralf König', 'RalfKönig'),
            ('Ted Benoît', 'TedBenoît'),
            ('Gilbert G. Groud', 'GilbertGGroud'),
            ('Samuel (Mark) Clemens', 'SamuelMarkClemens'),
            ('Alfa _Rant_ Tamil', 'AlfaRantTamil'),
            ('Too     Close', 'TooClose'),

            # These names are scrubed
            ('Fred/ Smith', 'FredSmith'),
            (r'Fred\ Smith', 'FredSmith'),
            ('Fred? Smith', 'FredSmith'),
            ('Fred% Smith', 'FredSmith'),
            ('Fred* Smith', 'FredSmith'),
            ('Fred: Smith', 'FredSmith'),
            ('Fred| Smith', 'FredSmith'),
            ('Fred" Smith', 'FredSmith'),
            ('Fred< Smith', 'FredSmith'),
            ('Fred> Smith', 'FredSmith'),
            (' Fred Smith ', 'FredSmith'),
            ("Fred's Smith", "FredsSmith"),
            ('Kevin "Kev" Walker', 'KevinKevWalker'),
        ]

        for t in tests:
            self.assertEqual(CreatorName(t[0]).for_file(), t[1])


class TestFunctions(LocalTestCase):

    def test__names(self):
        name = MockBookName('hello')
        self.assertEqual(
            names(name),
            {
                'name_for_file': 'hello name for file!',
                'name_for_search': 'hello name for search!',
                'name_for_url': 'hello name for url!',
            }
        )

        fields = ['_fake_1', 'name_for_url', '_fake_2', 'name_for_search']
        self.assertEqual(
            names(name, fields=fields),
            {
                'name_for_search': 'hello name for search!',
                'name_for_url': 'hello name for url!',
            }
        )


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
