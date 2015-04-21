#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/creators.py

"""
import os
import shutil
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.contrib.simplejson import loads
from gluon.storage import Storage
from applications.zcomx.modules.creators import \
    add_creator, \
    book_for_contributions, \
    can_receive_contributions, \
    contribute_link, \
    creator_name, \
    for_path, \
    formatted_name, \
    html_metadata, \
    image_as_json, \
    images, \
    on_change_name, \
    profile_onaccept, \
    queue_update_indicia, \
    short_url, \
    torrent_file_name, \
    torrent_link, \
    torrent_url, \
    tumblr_data, \
    url
from applications.zcomx.modules.images import store
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    _image_dir = '/tmp/image_for_creators'
    _image_original = os.path.join(_image_dir, 'original')
    _test_data_dir = None
    _uploadfolders = {}

    @classmethod
    def _prep_image(cls, img, working_directory=None, to_name=None):
        """Prepare an image for testing.
        Copy an image from private/test/data to a working directory.

        Args:
            img: string, name of source image, eg file.jpg
                must be in cls._test_data_dir
            working_directory: string, path of working directory to copy to.
                If None, uses cls._image_dir
            to_name: string, optional, name of image to copy file to.
                If None, img is used.
        """
        src_filename = os.path.join(
            os.path.abspath(cls._test_data_dir),
            img
        )

        if working_directory is None:
            working_directory = os.path.abspath(cls._image_dir)

        if to_name is None:
            to_name = img

        filename = os.path.join(working_directory, to_name)
        shutil.copy(src_filename, filename)
        return filename

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

        if not os.path.exists(cls._image_original):
            os.makedirs(cls._image_original)

        # Store images in tmp directory
        img_fields = [
            'image', 'indicia_image', 'indicia_portrait', 'indicia_landscape']

        for img_field in img_fields:
            cls._uploadfolders[img_field] = db.creator[img_field].uploadfolder
            db.creator[img_field].uploadfolder = cls._image_original

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)

    def test__add_creator(self):
        email = 'test__add_creator@example.com'

        def user_by_email(email):
            query = (db.auth_user.email == email)
            return db(query).select(db.auth_user.ALL).first()

        def creator_by_email(email):
            query = (db.creator.email == email)
            return db(query).select(db.creator.ALL).first()

        self.assertEqual(creator_by_email(email), None)
        self.assertEqual(user_by_email(email), None)

        # form has no email
        form = Storage({'vars': Storage()})
        add_creator(form)
        self.assertEqual(creator_by_email(email), None)

        # auth_user doesn't exist
        form.vars.email = email
        add_creator(form)
        self.assertEqual(creator_by_email(email), None)

        user = self.add(db.auth_user, dict(
            name='First Last',
            email=email,
        ))

        add_creator(form)
        creator = creator_by_email(email)
        self.assertTrue(creator)
        self._objects.append(creator)
        self.assertEqual(creator.email, email)
        self.assertEqual(creator.auth_user_id, user.id)
        self.assertEqual(creator.name_for_search, 'first-last')
        self.assertEqual(creator.name_for_url, 'FirstLast')
        query = (db.job.command.like(
            '%update_creator_indicia.py -o -r {i}'.format(i=creator.id)))
        jobs = db(query).select()
        self.assertEqual(len(jobs), 1)
        jobs[0].delete_record()
        db.commit()

        before = db(db.creator).count()
        add_creator(form)
        after = db(db.creator).count()
        self.assertEqual(before, after)

    def test__book_for_contributions(self):
        creator = self.add(db.creator, dict(
            email='test__book_for_contributions@email.com',
        ))

        # Has no books
        self.assertEqual(book_for_contributions(db, creator), None)

        book_1 = self.add(db.book, dict(
            creator_id=creator.id,
            contributions_remaining=100.00,
        ))

        got = book_for_contributions(db, creator)
        self.assertEqual(got, book_1)

        # With two books, the higher remaining should be returned.
        book_2 = self.add(db.book, dict(
            creator_id=creator.id,
            contributions_remaining=99.00,
        ))

        got = book_for_contributions(db, creator)
        self.assertEqual(got, book_1)

        # If contributions are applied to book so that its remaining is
        # lower, the higher book should be returned.
        book_1.update_record(contributions_remaining=98.00)
        db.commit()

        got = book_for_contributions(db, creator)
        self.assertEqual(got, book_2)

    def test__can_receive_contributions(self):
        creator = self.add(db.creator, dict(
            paypal_email='',
        ))

        self.assertFalse(can_receive_contributions(db, creator))

        tests = [
            # (paypal_email, expect)
            (None, False),
            ('', False),
            ('paypal@paypal.com', True),
        ]

        # With no book, all tests should return False
        for t in tests:
            creator.update_record(paypal_email=t[0])
            db.commit()
            self.assertFalse(can_receive_contributions(db, creator))

        self.add(db.book, dict(
            creator_id=creator.id,
            contributions_remaining=100.00,
        ))

        for t in tests:
            creator.update_record(paypal_email=t[0])
            db.commit()
            self.assertEqual(can_receive_contributions(db, creator), t[1])

    def test__contribute_link(self):
        empty = '<span></span>'

        creator = self.add(db.creator, dict(
            email='test__contribute_link@email.com',
        ))

        # As integer, creator_id
        link = contribute_link(db, creator.id)
        # Eg   <a href="/contributions/paypal?creator_id=3713" target="_blank">
        #       Contribute
        #      </a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?creator_id={i}'.format(i=creator.id)
        )

        # As Row, creator
        link = contribute_link(db, creator)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?creator_id={i}'.format(i=creator.id)
        )

        # Invalid id
        link = contribute_link(db, -1)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = contribute_link(db, creator, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = contribute_link(db, creator, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = contribute_link(db, creator, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__creator_name(self):
        auth_user = self.add(db.auth_user, dict(
            name='First Last'
        ))

        creator = self.add(db.creator, dict(
            auth_user_id=auth_user.id,
            name_for_search='first-last',
            name_for_url='FirstMiddleLast',
        ))

        tests = [
            # (use, expect)
            ('file', 'FirstLast'),
            ('search', 'first-last'),
            ('url', 'FirstMiddleLast'),
        ]

        for t in tests:
            self.assertEqual(creator_name(creator, use=t[0]), t[1])

    def test__for_path(self):

        tests = [
            # (name, expect)
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
            self.assertEqual(for_path(t[0]), t[1])

    def test__formatted_name(self):
        auth_user = self.add(db.auth_user, dict(
            name='Test Name'
        ))

        creator = self.add(db.creator, dict(
            email='test_name@example.com'
        ))

        # creator.auth_user_id not set
        self.assertEqual(formatted_name(creator), None)

        # Invalid auth_user.id
        creator.update_record(auth_user_id=-1)
        db.commit()
        self.assertEqual(formatted_name(creator), None)

        creator.update_record(auth_user_id=auth_user.id)
        db.commit()
        # By Row instance
        self.assertEqual(formatted_name(creator), 'Test Name')
        # By integer instance
        self.assertEqual(formatted_name(creator.id), 'Test Name')

    def test__html_metadata(self):

        self.assertEqual(html_metadata(None), {})

        auth_user = self.add(db.auth_user, dict(name='First Last'))
        creator = self.add(db.creator, dict(
            auth_user_id=auth_user.id,
            name_for_url='FirstLast',
            bio='First was born...',
            twitter='@firstlast',
        ))

        # Creator without image
        self.assertEqual(
            html_metadata(creator),
            {
                'description': 'First was born...',
                'image_url': None,
                'name': 'First Last',
                'twitter': '@firstlast',
                'type': 'profile',
                'url': 'http://127.0.0.1:8000/FirstLast'
            }
        )

        # Creator with image
        creator.image = 'file.jpg'
        img_url = 'http://127.0.0.1:8000/images/download/file.jpg?size=web'
        self.assertEqual(
            html_metadata(creator),
            {
                'description': 'First was born...',
                'image_url': img_url,
                'name': 'First Last',
                'twitter': '@firstlast',
                'type': 'profile',
                'url': 'http://127.0.0.1:8000/FirstLast'
            }
        )

    def test__image_as_json(self):
        db.creator.image.uploadfolder = self._uploadfolders['image']
        db.creator.indicia_image.uploadfolder = \
            self._uploadfolders['indicia_image']

        email = web.username
        user = db(db.auth_user.email == email).select().first()
        if not user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        query = (db.creator.auth_user_id == user.id)
        creator = db(query).select().first()
        if not creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

        for field in ['image', 'indicia_image']:
            if creator[field]:
                filename, fullname = db.creator[field].retrieve(
                    creator[field],
                    nameonly=True,
                )
            if not creator[field] or not os.path.exists(fullname):
                stored_filename = store(
                    db.creator[field],
                    self._prep_image('file.jpg'),
                )
                data = {field: stored_filename}
                creator.update_record(**data)
                db.commit()

        self.assertTrue(creator)

        def do_test(image, expect):
            self.assertTrue('files' in image.keys())
            self.assertEqual(len(image['files']), 1)
            self.assertEqual(
                image['files'][0],
                {
                    'name': expect.filename,
                    'size': expect.size,
                    'url': expect.down_url,
                    'thumbnailUrl': expect.thumb,
                    'deleteUrl': expect.delete_url,
                    'deleteType': 'DELETE',
                }
            )

        # Test creator.image
        for entity in [creator.id, creator]:
            image_json = image_as_json(db, entity)
            expect = Storage({})
            filename, fullname = db.creator.image.retrieve(
                creator.image,
                nameonly=True,
            )

            expect.filename = filename
            expect.size = os.stat(fullname).st_size
            expect.down_url = '/images/download/{img}'.format(
                img=creator.image)
            expect.thumb = '/images/download/{img}?size=web'.format(
                img=creator.image)
            expect.delete_url = '/login/creator_img_handler/image'

            do_test(loads(image_json), expect)

        # Test creator.indicia_image
        for entity in [creator.id, creator]:
            image_json = image_as_json(db, entity, field='indicia_image')
            expect = Storage({})
            filename, fullname = db.creator.indicia_image.retrieve(
                creator.indicia_image,
                nameonly=True,
            )
            expect.filename = filename
            expect.size = os.stat(fullname).st_size
            expect.down_url = '/images/download/{img}'.format(
                img=creator.indicia_image)
            expect.thumb = '/images/download/{img}?size=web'.format(
                img=creator.indicia_image)
            expect.delete_url = '/login/creator_img_handler/indicia_image'

            do_test(loads(image_json), expect)

        db.creator.image.uploadfolder = self._image_original
        db.creator.indicia_image.uploadfolder = self._image_original

    def test__images(self):
        creator = self.add(db.creator, dict(
            email='test__images@example.com'
        ))

        self.assertEqual(images(creator), [])

        data = {
            'image': None,
            'indicia_image': 'b.2.jpg',
            'indicia_landscape': None,
            'indicia_portrait': None,
        }

        creator.update_record(**data)
        db.commit()
        self.assertEqual(images(creator), ['b.2.jpg'])

        data = {
            'image': 'a.1.jpg',
            'indicia_image': 'b.2.jpg',
            'indicia_landscape': 'c.3.jpg',
            'indicia_portrait': 'd.4.jpg',
        }

        creator.update_record(**data)
        db.commit()

        self.assertEqual(
            sorted(images(creator)),
            [
                'a.1.jpg',
                'b.2.jpg',
                'c.3.jpg',
                'd.4.jpg',
            ]
        )

    def test__on_change_name(self):
        auth_user = self.add(db.auth_user, dict(
            name='Test On Change Name'
        ))

        creator = self.add(db.creator, dict(
            email='test_on_change_name@example.com'
        ))

        self.assertEqual(creator.name_for_search, None)
        self.assertEqual(creator.name_for_url, None)
        on_change_name(creator)
        # creator.auth_user_id not set
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.name_for_search, None)
        self.assertEqual(creator.name_for_url, None)

        creator.update_record(auth_user_id=auth_user.id)
        db.commit()
        on_change_name(creator)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.name_for_search, 'test-on-change-name')
        self.assertEqual(creator.name_for_url, 'TestOnChangeName')

        # Test with creator.id
        # Reset
        creator.update_record(name_for_search=None, name_for_url=None)
        db.commit()
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.name_for_search, None)
        self.assertEqual(creator.name_for_url, None)
        on_change_name(creator.id)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.name_for_search, 'test-on-change-name')
        self.assertEqual(creator.name_for_url, 'TestOnChangeName')

    def test__profile_onaccept(self):
        auth_user = self.add(db.auth_user, dict(
            name='Test Profile Onaccept'
        ))

        creator = self.add(db.creator, dict(
            email='test_profile_onaccept@example.com',
        ))

        self.assertEqual(creator.name_for_search, None)
        self.assertEqual(creator.name_for_url, None)

        # form has no email
        form = Storage({'vars': Storage()})
        profile_onaccept(form)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.name_for_search, None)
        self.assertEqual(creator.name_for_url, None)

        # creator.auth_user_id not set
        form.vars.id = auth_user.id
        profile_onaccept(form)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.name_for_search, None)
        self.assertEqual(creator.name_for_url, None)

        creator.update_record(auth_user_id=auth_user.id)
        db.commit()
        profile_onaccept(form)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.name_for_search, 'test-profile-onaccept')
        self.assertEqual(creator.name_for_url, 'TestProfileOnaccept')

    def test__queue_update_indicia(self):
        self.assertRaises(NotFoundError, queue_update_indicia, -1)

        creator = self.add(db.creator, dict(
            email='test__queue_update_indicia@example.com',
        ))

        job = queue_update_indicia(creator)
        self.assertTrue(job)
        expect = 'update_creator_indicia.py -o -r {i}'.format(i=creator.id)
        self.assertTrue(expect in job.command)
        self._objects.append(job)

    def test__short_url(self):
        tests = [
            # (creator_id, expect)
            (None, None),
            (-1, None),
            (98, 'http://98.zco.mx'),
            (101, 'http://101.zco.mx'),
        ]
        for t in tests:
            self.assertEqual(short_url(t[0]), t[1])

    def test__torrent_file_name(self):
        auth_user = self.add(db.auth_user, dict(name='First Last'))
        creator = self.add(db.creator, dict(auth_user_id=auth_user.id))
        self.assertEqual(
            torrent_file_name(creator),
            'FirstLast ({i}.zco.mx).torrent'.format(i=creator.id)
        )

        # Test scrubbed character.
        auth_user.update_record(
            name='First <Middle> Last',
        )
        db.commit()

        self.assertEqual(
            torrent_file_name(creator),
            'FirstMiddleLast ({i}.zco.mx).torrent'.format(i=creator.id)
        )

    def test__torrent_link(self):
        auth_user = self.add(db.auth_user, dict(name='First Last'))
        creator = self.add(db.creator, dict(
            auth_user_id=auth_user.id,
            torrent='app/zco/pri/var/tor/F/FirstLast.torrent',
            name_for_url='FirstLast',
        ))

        # As integer, creator.id
        link = torrent_link(creator.id)
        # Eg <a class="log_download_link"
        #   data-record_id="8979" data-record_table="book"
        #   href="/First_Last_(101.zco.mx).torrent">first_last.torrent</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'FirstLast.torrent')
        self.assertEqual(
            anchor['href'],
            '/FirstLast_({i}.zco.mx).torrent'.format(i=creator.id)
        )
        self.assertEqual(anchor['class'], 'log_download_link')
        self.assertEqual(anchor['data-record_table'], 'creator')
        self.assertEqual(anchor['data-record_id'], str(creator.id))

        # As Row, creator
        link = torrent_link(creator)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'FirstLast.torrent')
        self.assertEqual(
            anchor['href'],
            '/FirstLast_({i}.zco.mx).torrent'.format(i=creator.id)
        )
        self.assertEqual(anchor['class'], 'log_download_link')
        self.assertEqual(anchor['data-record_table'], 'creator')
        self.assertEqual(anchor['data-record_id'], str(creator.id))

        # Invalid id
        self.assertRaises(NotFoundError, torrent_link, -1)

        # Test components param
        components = ['aaa', 'bbb']
        link = torrent_link(creator, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = torrent_link(creator, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = torrent_link(creator, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'FirstLast.torrent')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__torrent_url(self):
        self.assertRaises(NotFoundError, torrent_url, None)

        auth_user = self.add(db.auth_user, dict(name='First Last'))
        creator = self.add(db.creator, dict(auth_user_id=auth_user.id))

        self.assertEqual(
            torrent_url(creator),
            '/FirstLast_({i}.zco.mx).torrent'.format(i=creator.id)
        )

        # Test scrubbed character.
        auth_user.update_record(name='First <Middle> Last')
        db.commit()

        self.assertEqual(
            torrent_url(creator),
            '/FirstMiddleLast_({i}.zco.mx).torrent'.format(i=creator.id)
        )

    def test__tumblr_data(self):

        self.assertEqual(tumblr_data(None), {})

        auth_user = self.add(db.auth_user, dict(name='First Last'))
        creator = self.add(db.creator, dict(
            auth_user_id=auth_user.id,
            name_for_search='first-last',
            name_for_url='FirstLast',
            website='http://website.com',
            twitter='@firstlast',
            shop=None,
            tumblr='http://tumblr.com/firstlast',
            facebook='htt://facebook.com/firstlast',
        ))

        self.assertEqual(
            tumblr_data(creator),
            {
                'name': 'First Last',
                'name_for_search': 'first-last',
                'name_for_url': 'FirstLast',
                'social_media': [
                    ('website', 'http://website.com'),
                    ('twitter', 'https://twitter.com/firstlast'),
                    ('tumblr', 'http://tumblr.com/firstlast'),
                    ('facebook', 'htt://facebook.com/firstlast'),
                ],
                'twitter': '@firstlast',
                'url': 'http://zco.mx/FirstLast',
            }
        )

    def test__url(self):
        creator = self.add(db.creator, dict(email='test__url@example.com'))

        tests = [
            # (name_for_url, expect)
            (None, None),
            ('Prince', '/Prince'),
            ('FirstLast', '/FirstLast'),
            ('firstlast', '/firstlast'),
            ("HélèDEñça", '/H%C3%A9l%C3%A8DE%C3%B1%C3%A7a'),
        ]

        for t in tests:
            creator.update_record(name_for_url=t[0])
            db.commit()
            self.assertEqual(url(creator), t[1])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
