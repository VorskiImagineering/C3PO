#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ast
import os
import re
from itertools import izip_longest

import polib

from c3po.conf import settings
from c3po.converters.unicode import UnicodeWriter, UnicodeReader


METADATA_EMPTY = "{'comment': '', 'previous_msgctxt': None, " + \
                 "'encoding': 'utf-8', 'obsolete': 0, 'msgid_plural': '', " + \
                 "'msgstr_plural': {}, 'occurrences': [], 'msgctxt': None, " + \
                 "'flags': [], 'previous_msgid': None, " + \
                 "'previous_msgid_plural': None}"


def _get_all_po_filenames(locale_root, lang, po_files_path):
    """
    Get all po filenames from locale folder and return list of them.
    Assumes a directory structure:
    <locale_root>/<lang>/<po_files_path>/<filename>.
    """
    all_files = os.listdir(os.path.join(locale_root, lang, po_files_path))
    return filter(lambda s: s.endswith('.po'), all_files)


def _get_new_csv_writers(trans_title, meta_title,
                         trans_csv_path, meta_csv_path):
    """
    Prepare new csv writers, write title rows and return them.
    """
    trans_writer = UnicodeWriter(trans_csv_path)
    trans_writer.writerow(trans_title)

    meta_writer = UnicodeWriter(meta_csv_path)
    meta_writer.writerow(meta_title)

    return trans_writer, meta_writer


def _prepare_locale_dirs(languages, locale_root):
    """
    Prepare locale dirs for writing po files.
    Create new directories if they doesn't exist.
    """
    trans_languages = []
    for i, t in enumerate(languages):
        lang = t.split(':')[0]
        trans_languages.append(lang)
        lang_path = os.path.join(locale_root, lang)
        if not os.path.exists(lang_path):
            os.makedirs(lang_path)
    return trans_languages


def _prepare_polib_files(files_dict, filename, languages,
                         locale_root, po_files_path, header):
    """
    Prepare polib file object for writing/reading from them.
    Create directories and write header if needed. For each language,
    ensure there's a translation file named "filename" in the correct place.
    Assumes (and creates) a directory structure:
    <locale_root>/<lang>/<po_files_path>/<filename>.
    """
    files_dict[filename] = {}
    for lang in languages:
        file_path = os.path.join(locale_root, lang, po_files_path)
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        if header is not None:
            _write_header(os.path.join(file_path, filename), lang, header)

        files_dict[filename][lang] = polib.pofile(
            os.path.join(file_path, filename), encoding="UTF-8")


def _write_entries(po_files, languages, msgid, msgstrs, metadata, comment):
    """
    Write msgstr for every language with all needed metadata and comment.
    Metadata are parser from string into dict, so read them only from gdocs.
    """
    start = re.compile(r'^[\s]+')
    end = re.compile(r'[\s]+$')
    for i, lang in enumerate(languages):
        meta = ast.literal_eval(metadata)
        entry = polib.POEntry(**meta)
        entry.tcomment = comment
        entry.msgid = msgid
        if msgstrs[i]:
            start_ws = start.search(msgid)
            end_ws = end.search(msgid)
            entry.msgstr = str(start_ws.group() if start_ws else '') + \
                unicode(msgstrs[i].strip()) + \
                str(end_ws.group() if end_ws else '')
        else:
            entry.msgstr = ''
        po_files[lang].append(entry)


def _write_header(po_path, lang, header):
    """
    Write header into po file for specific lang.
    Metadata are read from settings file.
    """
    po_file = open(po_path, 'w')
    po_file.write(header + '\n')
    po_file.write(
        'msgid ""' +
        '\nmsgstr ""' +
        '\n"MIME-Version: ' + settings.METADATA['MIME-Version'] + r'\n"'
        '\n"Content-Type: ' + settings.METADATA['Content-Type'] + r'\n"'
        '\n"Content-Transfer-Encoding: ' +
        settings.METADATA['Content-Transfer-Encoding'] + r'\n"'
        '\n"Language: ' + lang + r'\n"' + '\n')
    po_file.close()


def _write_new_messages(po_file_path, trans_writer, meta_writer,
                        msgids, msgstrs, languages):
    """
    Write new msgids which appeared in po files with empty msgstrs values
    and metadata. Look for all new msgids which are diffed with msgids list
    provided as an argument.
    """
    po_filename = os.path.basename(po_file_path)
    po_file = polib.pofile(po_file_path)

    new_trans = 0
    for entry in po_file:
        if entry.msgid not in msgids:
            new_trans += 1
            trans = [po_filename, entry.tcomment, entry.msgid, entry.msgstr]
            for lang in languages[1:]:
                trans.append(msgstrs[lang].get(entry.msgid, ''))

            meta = dict(entry.__dict__)
            meta.pop('msgid', None)
            meta.pop('msgstr', None)
            meta.pop('tcomment', None)

            trans_writer.writerow(trans)
            meta_writer.writerow([str(meta)])

    return new_trans


def _get_new_msgstrs(po_file_path, msgids):
    """
    Write new msgids which appeared in po files with empty msgstrs values
    and metadata. Look for all new msgids which are diffed with msgids list
    provided as an argument.
    """
    po_file = polib.pofile(po_file_path)

    msgstrs = {}

    for entry in po_file:
        if entry.msgid not in msgids:
            msgstrs[entry.msgid] = entry.msgstr

    return msgstrs


def po_to_csv_merge(languages, locale_root, po_files_path,
                    local_trans_csv, local_meta_csv,
                    gdocs_trans_csv, gdocs_meta_csv):
    """
    Converts po file to csv GDocs spreadsheet readable format.
    Merges them if some msgid aren't in the spreadsheet.
    :param languages: list of language codes
    :param locale_root: path to locale root folder containing directories
                        with languages
    :param po_files_path: path from lang directory to po file
    :param local_trans_csv: path where local csv with translations
                            will be created
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
        trans_title = ['file', 'comment', 'msgid']
        trans_title += map(lambda s: s + ':msgstr', languages)
        meta_title = ['metadata']

    trans_writer, meta_writer = _get_new_csv_writers(
        trans_title, meta_title, local_trans_csv, local_meta_csv)

    for trans_row, meta_row in izip_longest(trans_reader, meta_reader):
        msgids.append(trans_row[2])
        trans_writer.writerow(trans_row)
        meta_writer.writerow(meta_row if meta_row else [METADATA_EMPTY])

    trans_reader.close()
    meta_reader.close()

    po_files = _get_all_po_filenames(locale_root, languages[0], po_files_path)

    new_trans = False
    for po_filename in po_files:
        new_msgstrs = {}
        for lang in languages[1:]:
            po_file_path = os.path.join(locale_root, lang,
                                        po_files_path, po_filename)
            if not os.path.exists(po_file_path):
                open(po_file_path, 'a').close()
            new_msgstrs[lang] = _get_new_msgstrs(po_file_path, msgids)

        if len(new_msgstrs[languages[1]].keys()) > 0:
            new_trans = True
            po_file_path = os.path.join(locale_root, languages[0],
                                        po_files_path, po_filename)
            _write_new_messages(po_file_path, trans_writer, meta_writer,
                                msgids, new_msgstrs, languages)

    trans_writer.close()
    meta_writer.close()

    return new_trans


def csv_to_po(trans_csv_path, meta_csv_path, locale_root,
              po_files_path, header=None):
    """
    Converts GDocs spreadsheet generated csv file into po file.
    :param trans_csv_path: path to temporary file with translations
    :param meta_csv_path: path to temporary file with meta information
    :param locale_root: path to locale root folder containing directories
                        with languages
    :param po_files_path: path from lang directory to po file
    """
    pattern = "^\w+.*po$"
    for root, dirs, files in os.walk(locale_root):
        for f in filter(lambda x: re.match(pattern, x), files):
            os.remove(os.path.join(root, f))

    # read title row and prepare descriptors for po files in each lang
    trans_reader = UnicodeReader(trans_csv_path)
    meta_reader = UnicodeReader(meta_csv_path)
    try:
        title_row = trans_reader.next()
    except StopIteration:
        # empty file
        return

    trans_languages = _prepare_locale_dirs(title_row[3:], locale_root)

    po_files = {}

    meta_reader.next()
    # go through every row in downloaded csv file
    for trans_row, meta_row in izip_longest(trans_reader, meta_reader):
        filename = trans_row[0].rstrip()
        metadata = meta_row[0].rstrip() if meta_row else METADATA_EMPTY
        comment = trans_row[1]
        msgid = trans_row[2]

        if filename not in po_files:
            _prepare_polib_files(po_files, filename, trans_languages,
                                 locale_root, po_files_path, header)

        _write_entries(po_files[filename], trans_languages, msgid,
                       trans_row[3:], metadata, comment)
    for filename in po_files:
        for lang in po_files[filename]:
            po_files[filename][lang].save()

    trans_reader.close()
    meta_reader.close()
