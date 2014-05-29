#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
encoding.py

Classes related to encoding.

"""
import codecs
import types

# This is more of visual translation also avoiding multiple char translation
# e.g. £ may be written as {pound}
LATIN_DICT = {
    u"¡": u"!",
    u"¢": u"c",
    u"£": u"L",
    u"¤": u"o",
    u"¥": u"Y",
    u"¦": u"|",
    u"§": u"S",
    u"¨": u"`",
    u"©": u"c",
    u"ª": u"a",
    u"«": u"<<",
    u"¬": u"-",
    u"­": u"-",
    u"®": u"R",
    u"¯": u"-",
    u"°": u"o",
    u"±": u"+-",
    u"²": u"2",
    u"³": u"3",
    u"´": u"'",
    u"µ": u"u",
    u"¶": u"P",
    u"·": u".",
    u"¸": u",",
    u"¹": u"1",
    u"º": u"o",
    u"»": u">>",
    u"¼": u"1/4",
    u"½": u"1/2",
    u"¾": u"3/4",
    u"¿": u"?",
    u"À": u"A",
    u"Á": u"A",
    u"Â": u"A",
    u"Ã": u"A",
    u"Ä": u"A",
    u"Å": u"A",
    u"Æ": u"Ae",
    u"Ç": u"C",
    u"È": u"E",
    u"É": u"E",
    u"Ê": u"E",
    u"Ë": u"E",
    u"Ì": u"I",
    u"Í": u"I",
    u"Î": u"I",
    u"Ï": u"I",
    u"Ð": u"D",
    u"Ñ": u"N",
    u"Ò": u"O",
    u"Ó": u"O",
    u"Ô": u"O",
    u"Õ": u"O",
    u"Ö": u"O",
    u"×": u"*",
    u"Ø": u"O",
    u"Ù": u"U",
    u"Ú": u"U",
    u"Û": u"U",
    u"Ü": u"U",
    u"Ý": u"Y",
    u"Þ": u"p",
    u"ß": u"b",
    u"à": u"a",
    u"á": u"a",
    u"â": u"a",
    u"ã": u"a",
    u"ä": u"a",
    u"å": u"a",
    u"æ": u"ae",
    u"ç": u"c",
    u"č": u"c",
    u"ć": u"c",
    u"è": u"e",
    u"é": u"e",
    u"ê": u"e",
    u"ë": u"e",
    u"ì": u"i",
    u"í": u"i",
    u"î": u"i",
    u"ï": u"i",
    u"ı": u"i",
    u"ð": u"d",
    u"ñ": u"n",
    u"ò": u"o",
    u"ó": u"o",
    u"ô": u"o",
    u"õ": u"o",
    u"ö": u"o",
    u"÷": u"/",
    u"ø": u"o",
    u"ù": u"u",
    u"ú": u"u",
    u"û": u"u",
    u"ü": u"u",
    u"ý": u"y",
    u"þ": u"p",
    u"ÿ": u"y",
    u"ž": u"z",
    u"’": u"'",
    u" ": u" ",         # \xa0
}


def latin2ascii(unicode_error):
    """
    Unicode encode error handler.

    # Adapted from
    # http://stackoverflow.com/questions/1382998/latin-1-to-ascii

    unicode_error is the portion of text from start to end, we just convert the
    first char, thus return unicode_error.start+1 instead of unicode_error.end
    """
    try:
        return (LATIN_DICT[unicode_error.object[unicode_error.start]],
                unicode_error.start + 1)
    except KeyError:
        # Uncomment next lines to see the offending character. This may not
        # work in contexts without a terminal.
        #import sys; print >> sys.stderr, "Nasty unicode char: {var}".format(
        #        var=unicode_error.object[unicode_error.start])
        return (u"?", unicode_error.start + 1)


class BaseLatin(object):
    """Base class representing an object in latin-1 encoding"""

    def __init__(self, value):
        """Constructor

        Args:
            value: string, the string value
        """
        self.value = value

    def as_ascii(self):
        """Return the string as ascii"""
        return self.value


class LatinDict(BaseLatin):
    """Class representing a dict in latin-1 encoding"""

    def __init__(self, value):
        """Constructor

        Args:
            value: dict
        """
        BaseLatin.__init__(self, value)

    def as_ascii(self):
        """Return the dict with values as ascii"""
        encoded = dict(self.value)
        for k, v in encoded.items():
            encoded[k] = latin_factory(v).as_ascii()
        return encoded


class LatinList(BaseLatin):
    """Class representing a list in latin-1 encoding"""

    def __init__(self, value):
        """Constructor

        Args:
            value: list
        """
        BaseLatin.__init__(self, value)

    def as_ascii(self):
        """Return the list with all items as ascii"""
        encoded = list(self.value)
        for k, v in enumerate(encoded):
            encoded[k] = latin_factory(v).as_ascii()
        return encoded


class LatinString(BaseLatin):
    """Class representing a string in latin-1 encoding"""

    def __init__(self, value):
        """Constructor

        Args:
            value: string, the string value
        """
        BaseLatin.__init__(self, value)

    def as_ascii(self):
        """Return the string as ascii"""
        codecs.register_error('latin2ascii', latin2ascii)
        return self.value.encode('ascii', 'latin2ascii')


def latin_factory(obj):
    """Factory for delegating obj to particular Latin class

    Args:
        obj: mixed, obj to handle with latin classes.

    Returns:
        BaseLatin instance or instance of subclass
    """
    if isinstance(obj, types.StringTypes):
        return LatinString(obj)
    if isinstance(obj, (types.ListType, types.TupleType)):
        return LatinList(obj)
    if isinstance(obj, types.DictType):
        return LatinDict(obj)
    return BaseLatin(obj)
