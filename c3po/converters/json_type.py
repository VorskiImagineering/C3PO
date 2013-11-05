#!/usr/bin/env python
#-*- coding: utf-8 -*-
#vim: set ts=4 sw=4 et fdm=marker : */
import json
import os
import shutil
from odslib import ODS
from collections import OrderedDict
from c3po.conf import settings
from c3po.converters.po_ods import _prepare_ods_columns
from c3po.converters.unicode import UnicodeReader


def _json_file_path(locale_root, lang):
    prefix = settings.SOURCE_FILE_PREFIX
    suffix = settings.SOURCE_FILE_SUFFIX
    return os.path.join(locale_root, '{0}{1}{2}'.format(prefix, lang, suffix))


def json_to_ods(languages, locale_root, temp_file_path):
    """
    Converts po file to csv GDocs spreadsheet readable format.
    :param languages: list of language codes
    :param locale_root: path to locale root folder containing directories with languages
    :param po_files_path: path from lang directory to po file
    :param temp_file_path: path where temporary files will be saved
    """
    title_row = ['comment', 'msgid']
    title_row += languages

    ods = ODS()
    ods.content.getSheet(0)
    _prepare_ods_columns(ods, title_row)

    trans_dict = OrderedDict()

    for lang in languages:
        with open(_json_file_path(locale_root, lang)) as fp:
            trans_dict[lang] = json.load(fp)

    i = 1
    for msgid, msgstr in trans_dict.values()[0].items():
        ods.content.getCell(1, i).stringValue(msgid).setCellColor(settings.EVEN_COLUMN_BG_COLOR)
        ods.content.getCell(2, i).stringValue(msgstr).setCellColor(settings.ODD_COLUMN_BG_COLOR)

        for j, langs_trans in enumerate(trans_dict.values()[1:]):
            bg_color = j % 2 and settings.ODD_COLUMN_BG_COLOR or settings.EVEN_COLUMN_BG_COLOR
            trans = langs_trans.get(msgid, '')
            ods.content.getCell(3 + j, i).stringValue(trans).setCellColor(bg_color)

        i += 1

    ods.save(temp_file_path)


def csv_to_json(trans_csv_path, locale_root):
    shutil.rmtree(locale_root)

    trans_reader = UnicodeReader(trans_csv_path)

    try:
        title_row = trans_reader.next()
    except StopIteration:
        # empty file
        return

    languages = title_row[2:]
    trans_dict = {}
    for lang in languages:
        trans_dict[lang] = {}

    for trans_line in trans_reader:
        msgid = trans_line[1]
        for i, trans in enumerate(trans_line[2:]):
            trans_dict[languages[i]][msgid] = trans

    os.makedirs(locale_root)

    for lang, lang_dict in trans_dict.items():
        with open(_json_file_path(locale_root, lang), 'w') as fp:
            json.dump(lang_dict, fp, indent=4)

    trans_reader.close()


def json_to_csv_merge(languages, locale_root, gdocs_trans_csv):
    """
    Converts po file to csv GDocs spreadsheet readable format. Merges them if some msgid aren't in the spreadsheet.
    """

    trans_dict = {}

    for lang in languages:
        with open(_json_file_path(locale_root, lang)) as fp:
            trans_dict[lang] = json.load(fp)

    trans_reader = UnicodeReader(gdocs_trans_csv)

    try:
        trans_reader.next()
    except StopIteration:
        # empty file
        pass

    for trans_line in trans_reader:
        msgid = trans_line[1]
        for i, trans in enumerate(trans_line[2:]):
            trans_dict[languages[i]][msgid] = trans

    for lang, lang_dict in trans_dict.items():
        with open(_json_file_path(locale_root, lang), 'w') as fp:
            json.dump(lang_dict, fp, indent=4)

    return True