#!/usr/bin/env python
# -*- coding: utf-8 -*

import gdata.spreadsheet.service
import gdata.docs.client
import gdata.docs.data
import gdata.data
import gdata.docs.service
from gdata.client import RequestError

import os
import urlparse
from subprocess import Popen, PIPE

from c3po.conf import settings
from converters import csv_to_po, po_to_csv_merge, po_to_ods, csv_to_ods

LOCAL_ODS = 'local.ods'
GDOCS_TRANS_CSV = 'c3po_gdocs_trans.csv'
GDOCS_META_CSV = 'c3po_gdocs_meta.csv'
LOCAL_TRANS_CSV = 'c3po_local_trans.csv'
LOCAL_META_CSV = 'c3po_local_meta.csv'


class PODocsError(Exception):
    pass


class Communicator(object):
    """
    Client for communicating with GDocs. Providing log in on object creation and methods for synchronizing,
    uploading, downloading files and clearing GDoc.

    Needs to specify:
        locale_root, po_files_path
    For example in Django, where 'en' is language code:
        conf/locale/en/LC_MESSAGES/django.po
        conf/locale/en/LC_MESSAGES/custom.po
    locale_root='conf/locale/'
    po_files_path='LC_MESSAGES'
    """

    email = None
    password = None
    url = None
    source = None
    temp_path = None

    def __init__(self, email=None, password=None, url=None, source=None, temp_path=None):
        """
        Initialize object with all necessary client information and log in
        :param email: user gmail account address
        :param password: password to gmail account
        :param url: url to spreadsheet where translations are or will be placed
        :param temp_path: path where temporary files will be saved
        :param source: source information to show on web
        """
        construct_vars = ('email', 'password', 'url', 'source', 'temp_path')
        for cv in construct_vars:
            if locals().get(cv) is None:
                setattr(self, cv, getattr(settings, cv.upper()))
            else:
                setattr(self, cv, locals().get(cv))
        self._login()
        self._get_gdocs_key()
        self._ensure_temp_path_exists()

    def _login(self):
        try:
            self.gd_client = gdata.docs.client.DocsClient()
            self.gd_client.ClientLogin(self.email, self.password, self.source)
        except RequestError as e:
            raise PODocsError(e)

    def _get_gdocs_key(self):
        try:
            args = urlparse.parse_qs(urlparse.urlparse(self.url).query)
            self.key = args['key'][0]
        except KeyError as e:
            raise PODocsError(e)

    def _ensure_temp_path_exists(self):
        try:
            if not os.path.exists(self.temp_path):
                os.mkdir(self.temp_path)
        except OSError as e:
            raise PODocsError(e)

    def _clear_temp(self):
        temp_files = [LOCAL_ODS, GDOCS_TRANS_CSV, GDOCS_META_CSV, LOCAL_TRANS_CSV, LOCAL_META_CSV]
        for file in temp_files:
            file_path = os.path.join(self.temp_path, file)
            if os.path.exists(file_path):
                os.remove(file_path)

    def _download_csv_from_gdocs(self, trans_csv_path, meta_csv_path):
        try:
            entry = self.gd_client.GetResourceById(self.key)
            self.gd_client.DownloadResource(entry, trans_csv_path, extra_params={'gid': 0, 'exportFormat': 'csv'})
            self.gd_client.DownloadResource(entry, meta_csv_path, extra_params={'gid': 1, 'exportFormat': 'csv'})
        except (RequestError, IOError) as e:
            if 'Sheet 1 not found' in str(e):
                return None
            raise PODocsError(e)
        return entry

    def _upload_file_to_gdoc(self, file_path, content_type='application/x-vnd.oasis.opendocument.spreadsheet'):
        try:
            entry = self.gd_client.GetResourceById(self.key)
            media = gdata.data.MediaSource(file_path=file_path, content_type=content_type)
            self.gd_client.UpdateResource(entry, media=media, update_metadata=False)
        except (RequestError, IOError) as e:
            raise PODocsError(e)

    def _merge_local_and_gdoc(self, entry, languages, locale_root, po_files_path,
                              local_trans_csv, local_meta_csv, gdocs_trans_csv, gdocs_meta_csv):
        try:
            new_translations = po_to_csv_merge(languages, locale_root, po_files_path,
                                               local_trans_csv, local_meta_csv, gdocs_trans_csv, gdocs_meta_csv)
            if new_translations:
                local_ods = os.path.join(self.temp_path, LOCAL_ODS)
                csv_to_ods(local_trans_csv, local_meta_csv, local_ods)
                media = gdata.data.MediaSource(file_path=local_ods,
                                               content_type='application/x-vnd.oasis.opendocument.spreadsheet')
                self.gd_client.UpdateResource(entry, media=media, update_metadata=False)
        except (IOError, OSError, RequestError) as e:
            raise PODocsError(e)

    def synchronize(self, languages=None, locale_root=None, po_files_path=None, header=None):
        """
        Synchronize local po files with translations on GDocs Spreadsheet.
        Downloads two csv files, merges them and converts into po files structure.
        :param languages: list of languages
        :param locale_root: path to locale root folder containing directories with languages
        :param po_files_path: path from lang directory to po file
        :param header: header which will be put on top of every po file when downloading
        """
        if languages is None:
            languages = settings.LANGUAGES
        if locale_root is None:
            locale_root = settings.LOCALE_ROOT
        if po_files_path is None:
            po_files_path = settings.PO_FILES_PATH
        if header is None:
            header = settings.HEADER

        gdocs_trans_csv = os.path.join(self.temp_path, GDOCS_TRANS_CSV)
        gdocs_meta_csv = os.path.join(self.temp_path, GDOCS_META_CSV)
        local_trans_csv = os.path.join(self.temp_path, LOCAL_TRANS_CSV)
        local_meta_csv = os.path.join(self.temp_path, LOCAL_META_CSV)

        entry = self._download_csv_from_gdocs(gdocs_trans_csv, gdocs_meta_csv)

        if entry is None:
            self.upload(languages, locale_root, po_files_path)

        self._merge_local_and_gdoc(entry, languages, locale_root, po_files_path,
                                   local_trans_csv, local_meta_csv, gdocs_trans_csv, gdocs_meta_csv)

        try:
            csv_to_po(local_trans_csv, local_meta_csv, locale_root, po_files_path, header)
        except IOError as e:
            raise PODocsError(e)

        self._clear_temp()

    def download(self, locale_root=None, po_files_path=None, header=None):
        """
        Download po file from GDocs. If locale_root not specified, downloads csv file
        :param locale_root: path to locale root folder containing directories with languages
        :param po_files_path: path from lang directory to po file
        :param header: header which will be put on top of every po file when downloading
        """
        if locale_root is None:
            locale_root = settings.LOCALE_ROOT
        if po_files_path is None:
            po_files_path = settings.PO_FILES_PATH
        if header is None:
            header = settings.HEADER

        trans_csv_path = os.path.realpath(os.path.join(self.temp_path, GDOCS_TRANS_CSV))
        meta_csv_path = os.path.realpath(os.path.join(self.temp_path, GDOCS_META_CSV))

        self._download_csv_from_gdocs(trans_csv_path, meta_csv_path)

        try:
            csv_to_po(trans_csv_path, meta_csv_path, locale_root, po_files_path, header=header)
        except IOError as e:
            raise PODocsError(e)

        self._clear_temp()

    def upload(self, languages=None, locale_root=None, po_files_path=None):
        """
        Upload all po files to GDocs ignoring conflicts
        :param languages: list of language codes
        :param locale_root: path to locale root folder containing directories with languages
        :param po_files_path: path from lang directory to po file
        """
        if languages is None:
            languages = settings.LANGUAGES
        if locale_root is None:
            locale_root = settings.LOCALE_ROOT
        if po_files_path is None:
            po_files_path = settings.PO_FILES_PATH

        local_ods_path = os.path.join(self.temp_path, LOCAL_ODS)
        try:
            po_to_ods(languages, locale_root, po_files_path, local_ods_path)
        except (IOError, OSError) as e:
            raise PODocsError(e)

        self._upload_file_to_gdoc(local_ods_path)

        self._clear_temp()

    def clear(self):
        """
        Clear GDoc sending empty csv
        """
        empty_file_path = os.path.join(self.temp_path, 'empty.csv')
        try:
            empty_file = open(empty_file_path, 'w')
            empty_file.write(',')
            empty_file.close()
        except IOError as e:
            raise PODocsError(e)

        self._upload_file_to_gdoc(empty_file_path, content_type='text/csv')

        os.remove(empty_file_path)


def git_push(git_message=None, git_repository=None, git_branch=None, locale_root=None):
    """
    Pushes specified directory to git remote
    :param git_message: commit message
    :param git_repository: repository address
    :param git_branch: git branch
    :param locale_root: path to locale root folder containing directories with languages
    :return: tuple stdout, stderr of completed command
    """
    construct_vars = ('git_message', 'git_repository', 'git_branch', 'locale_root')
    for cv in construct_vars:
        if locals().get(cv) is None:
            locals()[cv] = getattr(settings, cv.upper())

    devnull = open(os.devnull, 'w')
    commands = ['git remote add po_translator ' + git_repository,
                'git branch ' + git_branch,
                'git checkout ' + git_branch]
    for command in commands:
        Popen(command, shell=True, stdout=devnull, stderr=devnull).wait()
    devnull.close()

    commands = 'git add ' + locale_root + \
               ' && git commit -m "' + git_message + '"' + \
               ' && git push po_translator ' + git_branch + ':' + git_branch
    proc = Popen(commands, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()

    return stdout, stderr


def git_checkout(git_branch=None, locale_root=None):
    """
    Checkouts branch to last commit
    :param git_branch: branch to checkout
    :param locale_root: locale folder path
    :return: tuple stdout, stderr of completed command
    """
    construct_vars = ('git_branch', 'locale_root')
    for cv in construct_vars:
        if locals().get(cv) is None:
            locals()[cv] = getattr(settings, cv.upper())

    proc = Popen('git checkout ' + git_branch + ' -- ' + locale_root, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()

    return stdout, stderr
