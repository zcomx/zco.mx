"""
Source: https://github.com/mohanraj-r/torrentparse
Parses a torrent file and provides method to access the following attributes.
    . Tracker URL
    . Creation date
    . Client name, if any
    . For each file
        . name
        . length
        . checksum

Created on 2012-03-07

@author: mohanr

NOTES:
    The original is no longer developed. It's been converted to python3.
"""
from io import BytesIO
from datetime import datetime
from glob import glob
import os
import string
import sys


class ParsingError(Exception):
    """Error class representing errors that occur while parsing the torrent
    content.
    """
    def __init__(self, error_msg):
        Exception.__init__(self)
        self.error_msg = error_msg

    def __str__(self):
        return repr(self.error_msg)


class TorrentParser():
    """Parses a torrent file and returns various properties based on the
    content of the torrent file.
    """

    DICT_START = 'd'
    LIST_START = 'l'
    DICT_LIST_END = 'e'
    DICT_KEY_VALUE_SEP = ': '
    DICT_LIST_ITEM_SEP = ', '
    INT_START = 'i'

    class _TorrentStr():
        """ BytesIO wrapper over the torrent string.

            TODO:
                . Create unittests to cover this class.
                . Should this rather extend BytesIO class. Explore.
        """

        STR_LEN_VALUE_SEP = ':'
        INT_END = 'e'

        def __init__(self, torr_str):
            self.torr_str = BytesIO(torr_str)
            self.curr_char = None

        def next_char(self):
            """Return the next char"""
            # to provide 2 ways of accessing the current parsed char - 1. as
            # return value, 2. as self.curr_char (useful in some circumstances)
            self.curr_char = self.torr_str.read(1)
            return self.curr_char.decode('utf-8')

        def step_back(self, position=-1, mode=1):
            """Step back, by default, 1 position relative to the current
            position.
            """
            self.torr_str.seek(position, mode)

        def parse_str(self):
            """Parse and return a string from the torrent file content.
            Format <string length>:<string>

            Returns:
                Parsed string (from the current position).
            Raises:
                ParsingError, when expected string format is not encountered.

            TODO:
                . Explore using regex to accomplish the parsing.
            """
            str_len = self._parse_number(delimiter=self.STR_LEN_VALUE_SEP)

            if not str_len:
                raise ParsingError(
                    'Empty string length found while parsing at position %d' %
                    self.torr_str.pos
                )

            return self.torr_str.read(str_len)

        def parse_int(self):
            """ Parse and return an integer from the torrent file content.
            Format i[0-9]+e

            Returns:
                Parsed integer (from the current position).
            Raises:
                ParsingError, when expected integer format is not
                    encountered.

            TODO:
                . Explore using regex to accomplish the parsing.
                . Could re-purpose this function to parse str_length.
            """
            # just to make sure we are parsing the integer of correct format
            self.step_back()

            if self.next_char() != TorrentParser.INT_START:
                fmt = (
                    'Error while parsing for an integer. '
                    'Found %s at position %d while %s is expected.'
                )
                raise ParsingError(fmt % (
                    self.curr_char,
                    self.torr_str.pos,
                    TorrentParser.INT_START
                ))

            return self._parse_number(delimiter=self.INT_END)

        def _parse_number(self, delimiter):
            """ Parses a sequence of digits representing either an integer or
            string length and returns the number.
            """
            parsed_int = ''
            while True:
                parsed_int_char = self.next_char()
                if parsed_int_char not in string.digits:
                    if parsed_int_char != delimiter:
                        fmt = (
                            'Invalid character %s found after parsing '
                            'an integer (%s expected) at position %d.'
                        )
                        raise ParsingError(fmt % (
                            parsed_int_char,
                            delimiter,
                            self.torr_str.pos
                        ))
                    break

                parsed_int += parsed_int_char

            return int(parsed_int)

    def __init__(self, torrent_file_path):
        """
        Reads the torrent file and sets the content as an object attribute.

        Args:
            torrent_file_path - String containing path to the torrent file to
                be parsed
        Returns:
            None
        Raises:
            ValueError - when passed arg is not of string type
            IOError - when the string arg passed points to a non-existent file

        """
        if not isinstance(torrent_file_path, str):
            raise ValueError(
                'Path of the torrent file expected in string format.')

        if not os.path.exists(torrent_file_path):
            raise IOError("No file found at '%s'" % torrent_file_path)

        with open(torrent_file_path, 'rb') as torr_file:
            torrent_content = torr_file.read()
            self.torrent_str = self._TorrentStr(torrent_content)

        self.parsed_content = self._parse_torrent()

    def get_tracker_url(self):
        """ Returns the tracker URL from the parsed torrent file. """
        return self.parsed_content.get('announce')

    def get_creation_date(self, time_format='iso'):
        """Returns creation date of the torrent, if present, in ISO time_format
        from the parsed torrent file.

        Args:
            time_format - determines the time_format of the time value
                returned. Valid values 'iso' or 'datetime'. Defaults to 'iso'.
        """
        time_stamp = self.parsed_content.get('creation date')
        if time_stamp:
            time_stamp = datetime.utcfromtimestamp(time_stamp)

            if time_format == 'iso':
                return time_stamp.isoformat()
            return time_stamp

    def get_client_name(self):
        """Returns the name of the client that created the torrent if present,
        from the parsed torrent file.
        """
        return self.parsed_content.get('created by')

    def get_files_details(self):
        """Parses torrent file and returns details of the files contained in
        the torrent. Details include name, length and checksum for each file in
        the torrent.
        """
        parsed_files_info = []
        files_info = self.parsed_content.get('info')

        # 'info' should be present in all torrent files. Nevertheless..
        if files_info:
            multiple_files_info = files_info.get('files')
            if multiple_files_info:     # multiple-file torrent
                for file_info in multiple_files_info:
                    parsed_files_info.append((
                        os.path.sep.join(
                            [x.decode('utf-8') for x in file_info.get('path')]
                        ),
                        file_info.get('length'),
                    ))
            else:       # single file torrent
                parsed_files_info.append(
                    (files_info.get('name'), files_info.get('length'), ))

        return parsed_files_info

    def _parse_torrent(self):
        """ Parse the torrent content in bencode format into python data
        format.

        Returns:
            A dictionary containing info parsed from torrent file.

        """
        parsed_char = self.torrent_str.next_char()

        if not parsed_char:
            return     # EOF

        # Parsing logic
        if parsed_char == self.DICT_LIST_END:
            return

        if parsed_char == self.INT_START:
            return self.torrent_str.parse_int()

        if parsed_char in string.digits:    # string
            self.torrent_str.step_back()
            return self.torrent_str.parse_str()

        if parsed_char == self.DICT_START:
            parsed_dict = {}
            while True:
                dict_key = self._parse_torrent()
                if not dict_key:
                    break     # End of dict
                dict_value = self._parse_torrent()     # parse value
                parsed_dict.setdefault(dict_key.decode('utf-8'), dict_value)

            return parsed_dict

        if parsed_char == self.LIST_START:
            parsed_list = []
            while True:
                list_item = self._parse_torrent()
                if not list_item:
                    break     # End of list
                parsed_list.append(list_item)

            return parsed_list


if __name__ == '__main__':
    # Parse a torrent file if given or parse the test data files.
    if len(sys.argv) > 1:
        torrent_files = sys.argv[1:]
        for torrent_file in torrent_files:
            if os.path.exists(torrent_file):
                print('Parsing file {}'.format(torrent_file))
            else:
                sys.exit('Unable to find file {}'.format(torrent_file))
    else:
        # this is helpful when debugging
        print('Parsing test torrent files ..')
        # pylint: disable=invalid-name
        test_files_rel_path = '/../tests/test_data/'
        cwd = os.path.dirname(os.path.realpath(__file__))
        test_data_dir = os.path.normpath(cwd + test_files_rel_path)
        torrent_files = glob(os.path.join(test_data_dir, '*.torrent'))

    for torrent_file in torrent_files:
        tp = TorrentParser(torrent_file)
        print(torrent_file)
        print(
            tp.get_tracker_url(),
            tp.get_creation_date(),
            tp.get_client_name(),
            tp.get_files_details()
        )
        print('*' * 80)
