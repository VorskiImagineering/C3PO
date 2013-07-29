#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import os
import shutil
import unittest

import gdata.data
from c3po.converters.po_ods import csv_to_ods

from mod.communicator import Communicator


TESTS_URL = 'https://docs.google.com/spreadsheet/ccc?key=0AnVOHClWGpLZdGFpQmpVUUx2eUg4Z0NVMGVQX3NrNkE#gid=0'


PO_CONTENT_LOCAL = [r'''# test
msgid ""
msgstr ""
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: %s\n"

#: tpl/base_site.html:44
msgid "Translation1"
msgstr "Str1 local"

#: tpl/base_site.html:44
msgid "Translation2"
msgstr ""

''', r'''# test
msgid ""
msgstr ""
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: %s\n"

#: tpl/base_site.html:44
msgid "Custom1"
msgstr "Str1 local"

#: tpl/base_site.html:44
msgid "Custom2"
msgstr ""

''']

CSV_TRANS_GDOCS = [
    ['comment', 'msgid', 'en:msgstr', 'pl:msgstr', 'jp:msgstr'],
    ['', 'Translation1', 'Str1 gdocs', 'Str1 gdocs', 'Str1 gdocs'],
    ['', 'Translation3', 'Str3', 'Str3', 'Str3'],
    ['', 'Custom1', 'Str1 gdocs', 'Str1 gdocs', 'Str1 gdocs'],
    ['', 'Custom3', 'Str3', 'Str3', 'Str3'],
]

CSV_META_GDOCS = [
    ['file', 'metadata'],
    ['custom.po', "{'occurrences': [(u'tpl/base_site.html', u'44')]}"],
    ['custom.po', "{'occurrences': [(u'tpl/base_site.html', u'44')]}"],
    ['django.po', "{'occurrences': [(u'tpl/base_site.html', u'44')]}"],
    ['django.po', "{'occurrences': [(u'tpl/base_site.html', u'44')]}"],
]

PO_CONTENT_MERGED = [r'''# test
msgid ""
msgstr ""
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: %s\n"

#: tpl/base_site.html:44
msgid "Translation1"
msgstr "Str1 gdocs"

#: tpl/base_site.html:44
msgid "Translation3"
msgstr "Str3"

#: tpl/base_site.html:44
msgid "Translation2"
msgstr ""
''', r'''# test
msgid ""
msgstr ""
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: %s\n"

#: tpl/base_site.html:44
msgid "Custom1"
msgstr "Str1 gdocs"

#: tpl/base_site.html:44
msgid "Custom3"
msgstr "Str3"

#: tpl/base_site.html:44
msgid "Custom2"
msgstr ""
''']


class TestCommunicator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = 'temp-conf'
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.languages = ['en', 'pl', 'jp']
        self.po_filenames = ['custom.po', 'django.po']
        self.locale_root = os.path.join(self.temp_dir, 'locale')
        self.po_files_path = 'LC_MESSAGES'
        self.header = '# test\n'
        os.makedirs(self.locale_root)
        for lang in self.languages:
            lang_path = os.path.join(self.locale_root, lang, self.po_files_path)
            os.makedirs(lang_path)

            with open(os.path.join(lang_path, self.po_filenames[0]), 'wb') as po_file:
                po_file.write(PO_CONTENT_LOCAL[0] % lang)
            with open(os.path.join(lang_path, self.po_filenames[1]), 'wb') as po_file:
                po_file.write(PO_CONTENT_LOCAL[1] % lang)

        self.com = Communicator(url=TESTS_URL, languages=self.languages, locale_root=self.locale_root,
                                po_files_path=self.po_files_path, header=self.header)
        self.com.clear()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        self.com.clear()

    def test_multiple_files_sync(self):
        temp_trans_path = os.path.join(self.temp_dir, 'temp_trans.csv')
        temp_meta_path = os.path.join(self.temp_dir, 'temp_meta.csv')
        temp_ods_path = os.path.join(self.temp_dir, 'temp.ods')
        with open(temp_trans_path, 'wb') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(CSV_TRANS_GDOCS)
        with open(temp_meta_path, 'wb') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(CSV_META_GDOCS)

        csv_to_ods(temp_trans_path, temp_meta_path, temp_ods_path)

        entry = self.com.gd_client.GetResourceById(self.com.key)
        media = gdata.data.MediaSource(file_path=temp_ods_path,
                                       content_type='application/x-vnd.oasis.opendocument.spreadsheet')
        self.com.gd_client.UpdateResource(entry, media=media, update_metadata=False)

        self.com.synchronize()

        for lang in self.languages:
            lang_path = os.path.join(self.locale_root, lang, self.po_files_path)

            with open(os.path.join(lang_path, self.po_filenames[0]), 'rb') as po_file:
                self.assertEqual(po_file.read(), PO_CONTENT_MERGED[0] % lang)

            with open(os.path.join(lang_path, self.po_filenames[1]), 'rb') as po_file:
                self.assertEqual(po_file.read(), PO_CONTENT_MERGED[1] % lang)


if __name__ == '__main__':
    unittest.main()
