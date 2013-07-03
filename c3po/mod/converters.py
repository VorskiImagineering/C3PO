#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ast
import codecs
import cStringIO
import csv
import shutil
import os
import polib
from itertools import izip
from odslib import ODS

from c3po.conf import settings


class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, file, encoding):
        self.reader = codecs.getreader(encoding)(file)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, file_path, dialect=csv.excel, encoding="utf-8", **kwargs):
        self.file = open(file_path, 'rb')
        recorder = UTF8Recoder(self.file, encoding)
        self.reader = csv.reader(recorder, dialect=dialect, **kwargs)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

    def close(self):
        self.file.close()


class UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, file_path, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = open(file_path, 'wb')
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

    def close(self):
        self.stream.close()


def _get_new_csv_writers(trans_title, meta_title, trans_csv_path, meta_csv_path):
    # Prepare new csv writers, write title rows and return them
    trans_writer = UnicodeWriter(trans_csv_path)
    trans_writer.writerow(trans_title)

    meta_writer = UnicodeWriter(meta_csv_path)
    meta_writer.writerow(meta_title)

    return trans_writer, meta_writer


def _get_all_po_filenames(locale_root, lang, po_files_path):
    # get all po files from lang folder
    all_files = os.listdir(os.path.join(locale_root, lang, po_files_path))
    return filter(lambda s: s.endswith('.po'), all_files)


def _write_header(po_path, lang, header):
    po_file = open(po_path, 'w')
    po_file.write(header + '\n')
    po_file.write('msgid ""' +
    '\nmsgstr ""' +
    '\n"MIME-Version: ' + settings.METADATA['MIME-Version'] + r'\n"'
    '\n"Content-Type: ' + settings.METADATA['Content-Type'] + r'\n"'
    '\n"Content-Transfer-Encoding: ' + settings.METADATA['Content-Transfer-Encoding'] + r'\n"'
    '\n"Language: ' + lang + r'\n"' + '\n')
    po_file.close()


def _prepare_locale_dirs(languages, locale_root):
    trans_languages = []
    for i, t in enumerate(languages):
        lang = t.split(':')[0]
        trans_languages.append(lang)
        lang_path = os.path.join(locale_root, lang)
        if not os.path.exists(lang_path):
            os.makedirs(lang_path)
    return trans_languages


def _write_entries(po_files, languages, msgid, msgstrs, metadata, comment):
    # write msgstr for every language
    for i, lang in enumerate(languages):
        meta = ast.literal_eval(metadata)
        entry = polib.POEntry(**meta)
        entry.tcomment = comment
        entry.msgid = msgid
        entry.msgstr = unicode(msgstrs[i])
        po_files[lang].append(entry)
        po_files[lang].save()


def _prepare_polib_files(files_dict, filename, languages, locale_root, po_files_path, header):
    files_dict[filename] = {}
    for lang in languages:
        file_path = os.path.join(locale_root, lang, po_files_path)
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        if header is not None:
            _write_header(os.path.join(file_path, filename), lang, header)

        files_dict[filename][lang] = polib.pofile(os.path.join(file_path, filename), encoding="UTF-8")


def _write_trans_into_ods(ods, languages, locale_root, po_files_path, po_filename):
    ods.content.getSheet(0)
    for i, lang in enumerate(languages[1:]):
        lang_po_path = os.path.join(locale_root, lang, po_files_path, po_filename)
        if os.path.exists(lang_po_path):
            po_file = polib.pofile(lang_po_path)
            for j, entry in enumerate(po_file):
                # start from 3 column, 1 row
                ods.content.getCell(i+3, j+1).stringValue(entry.msgstr)
                if i % 2 == 1:
                    ods.content.getCell(j, i+1).setCellColor('#f9f9f9')


def _prepare_ods_columns(ods, trans_title_row):
    ods.content.getSheet(0).setSheetName('Translations')
    ods.content.makeSheet('Meta options')
    ods.content.getColumn(0).setWidth('1.5in')
    ods.content.getColumn(1).setWidth('5.0in')
    ods.content.getCell(0, 0).stringValue('file').setCellColor('#d9edf7').setBold(True).setFontColor('#3a87ad')
    ods.content.getCell(1, 0).stringValue('metadata').setCellColor('#d9edf7').setBold(True).setFontColor('#3a87ad')

    ods.content.getSheet(0)
    for i, title in enumerate(trans_title_row):
        ods.content.getColumn(i).setWidth('2.5in')
        ods.content.getCell(i, 0).stringValue(title).setCellColor('#d9edf7').setBold(True).setFontColor('#3a87ad')
    ods.content.getColumn(0).setWidth('1.5in')


def _write_row_into_ods(ods, sheet_no, row_no, row):
    ods.content.getSheet(sheet_no)
    for j, col in enumerate(row):
        ods.content.getCell(j, row_no+1).stringValue(col)
        if j % 2 == 1:
            ods.content.getCell(j, row_no+1).setCellColor('#f9f9f9')


def _write_new_messages(po_file_path, trans_writer, meta_writer, msgids, languages_num):
    po_filename = os.path.basename(po_file_path)
    po_file = polib.pofile(po_file_path)

    new_trans = 0
    for entry in po_file:
        if entry.msgid not in msgids:
            new_trans += 1
            trans = [entry.tcomment, entry.msgid, entry.msgstr]
            trans += [''] * languages_num

            meta = dict(entry.__dict__)
            meta.pop('msgid', None)
            meta.pop('msgstr', None)
            meta.pop('tcomment', None)

            trans_writer.writerow(trans)
            meta_writer.writerow([po_filename, str(meta)])

    return new_trans


def po_to_csv_merge(languages, locale_root, po_files_path,
                    local_trans_csv, local_meta_csv, gdocs_trans_csv, gdocs_meta_csv):
    """
    Converts po file to csv GDocs spreadsheet readable format. Merges them if some msgid aren't in the spreadsheet.
    :param languages: list of language codes
    :param locale_root: path to locale root folder containing directories with languages
    :param po_files_path: path from lang directory to po file
    :param local_trans_csv: path where local csv with translations will be created
    :param local_meta_csv: path where local csv with metadata will be created
    :param gdocs_trans_csv: path to gdoc csv with translations
    """
    msgids = []

    trans_reader = UnicodeReader(gdocs_trans_csv)
    meta_reader = UnicodeReader(gdocs_meta_csv)

    try:
        trans_title = trans_reader.next()
        meta_title = meta_reader.next()
    except StopIteration:
        trans_title = ['comment', 'msgid']
        trans_title += map(lambda s: s + ':msgstr', languages)
        meta_title = ['file', 'metadata']

    trans_writer, meta_writer = _get_new_csv_writers(trans_title, meta_title, local_trans_csv, local_meta_csv)

    for trans_row, meta_row in izip(trans_reader, meta_reader):
        msgids.append(trans_row[1].rstrip())
        trans_writer.writerow(trans_row)
        meta_writer.writerow(meta_row)

    trans_reader.close()
    meta_reader.close()

    po_files = _get_all_po_filenames(locale_root, languages[0], po_files_path)

    new_trans = False
    for po_filename in po_files:
        po_file_path = os.path.join(locale_root, languages[0], po_files_path, po_filename)
        ret = _write_new_messages(po_file_path, trans_writer, meta_writer, msgids, len(languages)-1)
        if ret > 0:
            new_trans = True

    trans_writer.close()
    meta_writer.close()

    return new_trans


def csv_to_po(trans_csv_path, meta_csv_path, locale_root, po_files_path, header=None):
    """
    Converts GDocs spreadsheet generated csv file into po file.
    :param trans_csv_path: path to temporary file with translations
    :param meta_csv_path: path to temporary file with meta information
    :param locale_root: path to locale root folder containing directories with languages
    :param po_files_path: path from lang directory to po file
    """
    shutil.rmtree(locale_root)

    # read title row and prepare descriptors for po files in each lang
    trans_reader = UnicodeReader(trans_csv_path)
    meta_reader = UnicodeReader(meta_csv_path)
    try:
        title_row = trans_reader.next()
    except StopIteration:
        # empty file
        return

    trans_languages = _prepare_locale_dirs(title_row[2:], locale_root)

    po_files = {}

    meta_reader.next()
    # go through every row in downloaded csv file
    for trans_row, meta_row in izip(trans_reader, meta_reader):
        filename = meta_row[0].rstrip()
        metadata = meta_row[1].rstrip()
        comment = trans_row[0].rstrip()
        msgid = trans_row[1].rstrip()

        if filename not in po_files:
            _prepare_polib_files(po_files, filename, trans_languages, locale_root, po_files_path, header)

        _write_entries(po_files[filename], trans_languages, msgid, trans_row[2:], metadata, comment)

    trans_reader.close()
    meta_reader.close()


def po_to_ods(languages, locale_root, po_files_path, temp_file_path):
    """
    Converts po file to csv GDocs spreadsheet readable format.
    :param languages: list of language codes
    :param locale_root: path to locale root folder containing directories with languages
    :param po_files_path: path from lang directory to po file
    :param temp_file_path: path where temporary files will be saved
    """
    title_row = ['comment', 'msgid']
    title_row += map(lambda s: s + ':msgstr', languages)

    ods = ODS()

    _prepare_ods_columns(ods, title_row)

    po_files = _get_all_po_filenames(locale_root, languages[0], po_files_path)

    for po_filename in po_files:
        po_file_path = os.path.join(locale_root, languages[0], po_files_path, po_filename)

        po = polib.pofile(po_file_path)
        for i, entry in enumerate(po):
            meta = dict(entry.__dict__)
            meta.pop('msgid', None)
            meta.pop('msgstr', None)
            meta.pop('tcomment', None)

            ods.content.getSheet(1)
            ods.content.getCell(0, i+1).stringValue(po_filename)
            ods.content.getCell(1, i+1).stringValue(str(meta)).setCellColor('#f9f9f9')

            ods.content.getSheet(0)
            ods.content.getCell(0, i+1).stringValue(entry.tcomment)
            ods.content.getCell(1, i+1).stringValue(entry.msgid).setCellColor('#f9f9f9')
            ods.content.getCell(2, i+1).stringValue(entry.msgstr)

        _write_trans_into_ods(ods, languages, locale_root, po_files_path, po_filename)

    ods.save(temp_file_path)


def csv_to_ods(trans_csv, meta_csv, local_ods):
    """
    Converts csv files to one ods file
    :param trans_csv: path to csv file with translations
    :param meta_csv: path to csv file with metadata
    :param local_ods: path to new ods file
    """
    trans_reader = UnicodeReader(trans_csv)
    meta_reader = UnicodeReader(meta_csv)

    ods = ODS()

    trans_title = trans_reader.next()
    meta_reader.next()

    _prepare_ods_columns(ods, trans_title)

    for i, (trans_row, meta_row) in enumerate(izip(trans_reader, meta_reader)):
        _write_row_into_ods(ods, 0, i, trans_row)
        _write_row_into_ods(ods, 1, i, meta_row)

    trans_reader.close()
    meta_reader.close()

    ods.save(local_ods)
