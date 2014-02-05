#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from itertools import izip

import polib
from odslib import ODS
from c3po.conf import settings
from c3po.converters.po_csv import _get_all_po_filenames
from c3po.converters.unicode import UnicodeReader


def _escape_apostrophe(entry):
    return ("'" if entry.startswith("'") else "") + entry


def _prepare_ods_columns(ods, trans_title_row):
    """
    Prepare columns in new ods file, create new sheet for metadata,
    set columns color and width. Set formatting style info in your
    settings.py file in ~/.c3po/ folder.
    """
    ods.content.getSheet(0).setSheetName('Translations')
    ods.content.makeSheet('Meta options')
    ods.content.getColumn(0).setWidth('5.0in')
    ods.content.getCell(0, 0).stringValue('metadata')\
        .setCellColor(settings.TITLE_ROW_BG_COLOR) \
        .setBold(True).setFontColor(settings.TITLE_ROW_FONT_COLOR)

    ods.content.getSheet(0)
    ods.content.getColumn(0).setWidth('1.5in')
    ods.content.getCell(0, 0) \
        .setCellColor(settings.TITLE_ROW_BG_COLOR) \
        .setBold(True).setFontColor(settings.TITLE_ROW_FONT_COLOR)
    for i, title in enumerate(trans_title_row):
        ods.content.getColumn(i).setWidth(settings.MSGSTR_COLUMN_WIDTH)
        ods.content.getCell(i, 0).stringValue(title)\
            .setCellColor(settings.TITLE_ROW_BG_COLOR) \
            .setBold(True).setFontColor(settings.TITLE_ROW_FONT_COLOR)
    ods.content.getColumn(0).setWidth(settings.NOTES_COLUMN_WIDTH)


def _write_trans_into_ods(ods, languages, locale_root,
                          po_files_path, po_filename, start_row):
    """
    Write translations from po files into ods one file.
    Assumes a directory structure:
    <locale_root>/<lang>/<po_files_path>/<filename>.
    """
    ods.content.getSheet(0)
    for i, lang in enumerate(languages[1:]):
        lang_po_path = os.path.join(locale_root, lang,
                                    po_files_path, po_filename)
        if os.path.exists(lang_po_path):
            po_file = polib.pofile(lang_po_path)
            for j, entry in enumerate(po_file):
                # start from 4th column, 1st row
                row = j+start_row
                ods.content.getCell(i+4, row).stringValue(
                    _escape_apostrophe(entry.msgstr))
                if i % 2 == 1:
                    ods.content.getCell(i+4, row).setCellColor(
                        settings.ODD_COLUMN_BG_COLOR)
                else:
                    ods.content.getCell(i+4, row).setCellColor(
                        settings.EVEN_COLUMN_BG_COLOR)


def _write_row_into_ods(ods, sheet_no, row_no, row):
    """
    Write row with translations to ods file into specified sheet and row_no.
    """
    ods.content.getSheet(sheet_no)
    for j, col in enumerate(row):
        cell = ods.content.getCell(j, row_no+1)
        cell.stringValue(_escape_apostrophe(col))
        if j % 2 == 1:
            cell.setCellColor(settings.EVEN_COLUMN_BG_COLOR)
        else:
            cell.setCellColor(settings.ODD_COLUMN_BG_COLOR)


def po_to_ods(languages, locale_root, po_files_path, temp_file_path):
    """
    Converts po file to csv GDocs spreadsheet readable format.
    :param languages: list of language codes
    :param locale_root: path to locale root folder containing directories
                        with languages
    :param po_files_path: path from lang directory to po file
    :param temp_file_path: path where temporary files will be saved
    """
    title_row = ['file', 'comment', 'msgid']
    title_row += map(lambda s: s + ':msgstr', languages)

    ods = ODS()

    _prepare_ods_columns(ods, title_row)

    po_files = _get_all_po_filenames(locale_root, languages[0], po_files_path)

    i = 1
    for po_filename in po_files:
        po_file_path = os.path.join(locale_root, languages[0],
                                    po_files_path, po_filename)

        start_row = i

        po = polib.pofile(po_file_path)
        for entry in po:
            meta = dict(entry.__dict__)
            meta.pop('msgid', None)
            meta.pop('msgstr', None)
            meta.pop('tcomment', None)

            ods.content.getSheet(1)
            ods.content.getCell(0, i).stringValue(
                str(meta)).setCellColor(settings.EVEN_COLUMN_BG_COLOR)

            ods.content.getSheet(0)
            ods.content.getCell(0, i) \
                .stringValue(po_filename) \
                .setCellColor(settings.ODD_COLUMN_BG_COLOR)
            ods.content.getCell(1, i) \
                .stringValue(_escape_apostrophe(entry.tcomment)) \
                .setCellColor(settings.ODD_COLUMN_BG_COLOR)
            ods.content.getCell(2, i) \
                .stringValue(_escape_apostrophe(entry.msgid)) \
                .setCellColor(settings.EVEN_COLUMN_BG_COLOR)
            ods.content.getCell(3, i) \
                .stringValue(_escape_apostrophe(entry.msgstr))\
                .setCellColor(settings.ODD_COLUMN_BG_COLOR)

            i += 1

        _write_trans_into_ods(ods, languages, locale_root,
                              po_files_path, po_filename, start_row)

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
