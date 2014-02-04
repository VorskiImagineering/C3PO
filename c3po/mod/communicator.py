#!/usr/bin/env python
# -*- coding: utf-8 -*

import os
import subprocess
import urlparse
from subprocess import Popen, PIPE

import gdata.spreadsheet.service
import gdata.docs.client
import gdata.docs.data
import gdata.data
import gdata.docs.service
from gdata.client import RequestError

from c3po.conf import settings
from c3po.converters.po_csv import csv_to_po, po_to_csv_merge
from c3po.converters.po_ods import po_to_ods, csv_to_ods


LOCAL_ODS = 'local.ods'
GDOCS_TRANS_CSV = 'c3po_gdocs_trans.csv'
GDOCS_META_CSV = 'c3po_gdocs_meta.csv'
LOCAL_TRANS_CSV = 'c3po_local_trans.csv'
LOCAL_META_CSV = 'c3po_local_meta.csv'


class PODocsError(Exception):
    pass


class Communicator(object):
    """
    Client for communicating with GDocs. Providing log in on object
    creation and methods for synchronizing, uploading,
    downloading files and clearing GDoc.

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
    languages = None
    locale_root = None
    po_files_path = None
    header = None

    def __init__(self, email=None, password=None, url=None, source=None,
                 temp_path=None, languages=None, locale_root=None,
                 po_files_path=None, header=None):
        """
        Initialize object with all necessary client information and log in
        :param email: user gmail account address
        :param password: password to gmail account
        :param url: url to spreadsheet where translations are or will be placed
        :param temp_path: path where temporary files will be saved
        :param source: source information to show on web
        :param languages: list of languages
        :param locale_root: path to locale root folder containing directories
                            with languages
        :param po_files_path: path from lang directory to po file
        :param header: header which will be put on top of every po file when
                       downloading
        """
        construct_vars = ('email', 'password', 'url', 'source', 'temp_path',
                          'languages', 'locale_root', 'po_files_path', 'header')
        for cv in construct_vars:
            if locals().get(cv) is None:
                setattr(self, cv, getattr(settings, cv.upper()))
            else:
                setattr(self, cv, locals().get(cv))
        self._login()
        self._get_gdocs_key()
        self._ensure_temp_path_exists()

    def _login(self):
        """
        Login into Google Docs with user authentication info.
        """
        try:
            self.gd_client = gdata.docs.client.DocsClient()
            self.gd_client.ClientLogin(self.email, self.password, self.source)
        except RequestError as e:
            raise PODocsError(e)

    def _get_gdocs_key(self):
        """
        Parse GDocs key from Spreadsheet url.
        """
        try:
            args = urlparse.parse_qs(urlparse.urlparse(self.url).query)
            self.key = args['key'][0]
        except KeyError as e:
            raise PODocsError(e)

    def _ensure_temp_path_exists(self):
        """
        Make sure temp directory exists and create one if it does not.
        """
        try:
            if not os.path.exists(self.temp_path):
                os.mkdir(self.temp_path)
        except OSError as e:
            raise PODocsError(e)

    def _clear_temp(self):
        """
        Clear temp directory from created csv and ods files during
        communicator operations.
        """
        temp_files = [LOCAL_ODS, GDOCS_TRANS_CSV, GDOCS_META_CSV,
                      LOCAL_TRANS_CSV, LOCAL_META_CSV]
        for temp_file in temp_files:
            file_path = os.path.join(self.temp_path, temp_file)
            if os.path.exists(file_path):
                os.remove(file_path)

    def _download_csv_from_gdocs(self, trans_csv_path, meta_csv_path):
        """
        Download csv from GDoc.
        :return: returns resource if worksheets are present
        :except: raises PODocsError with info if communication
                 with GDocs lead to any errors
        """
        try:
            entry = self.gd_client.GetResourceById(self.key)
            self.gd_client.DownloadResource(
                entry, trans_csv_path,
                extra_params={'gid': 0, 'exportFormat': 'csv'}
            )
            self.gd_client.DownloadResource(
                entry, meta_csv_path,
                extra_params={'gid': 1, 'exportFormat': 'csv'}
            )
        except (RequestError, IOError) as e:
            raise PODocsError(e)
        return entry

    def _upload_file_to_gdoc(
            self, file_path,
            content_type='application/x-vnd.oasis.opendocument.spreadsheet'):
        """
        Uploads file to GDocs spreadsheet.
        Content type can be provided as argument, default is ods.
        """
        try:
            entry = self.gd_client.GetResourceById(self.key)
            media = gdata.data.MediaSource(
                file_path=file_path, content_type=content_type)
            self.gd_client.UpdateResource(
                entry, media=media, update_metadata=True)
        except (RequestError, IOError) as e:
            raise PODocsError(e)

    def _merge_local_and_gdoc(self, entry, local_trans_csv,
                              local_meta_csv, gdocs_trans_csv, gdocs_meta_csv):
        """
        Download csv from GDoc.
        :return: returns resource if worksheets are present
        :except: raises PODocsError with info if communication with GDocs
                 lead to any errors
        """
        try:
            new_translations = po_to_csv_merge(
                self.languages, self.locale_root, self.po_files_path,
                local_trans_csv, local_meta_csv,
                gdocs_trans_csv, gdocs_meta_csv)
            if new_translations:
                local_ods = os.path.join(self.temp_path, LOCAL_ODS)
                csv_to_ods(local_trans_csv, local_meta_csv, local_ods)
                media = gdata.data.MediaSource(
                    file_path=local_ods, content_type=
                    'application/x-vnd.oasis.opendocument.spreadsheet'
                )
                self.gd_client.UpdateResource(entry, media=media,
                                              update_metadata=True)
        except (IOError, OSError, RequestError) as e:
            raise PODocsError(e)

    def synchronize(self):
        """
        Synchronize local po files with translations on GDocs Spreadsheet.
        Downloads two csv files, merges them and converts into po files
        structure. If new msgids appeared in po files, this method creates
        new ods with appended content and sends it to GDocs.
        """
        gdocs_trans_csv = os.path.join(self.temp_path, GDOCS_TRANS_CSV)
        gdocs_meta_csv = os.path.join(self.temp_path, GDOCS_META_CSV)
        local_trans_csv = os.path.join(self.temp_path, LOCAL_TRANS_CSV)
        local_meta_csv = os.path.join(self.temp_path, LOCAL_META_CSV)

        try:
            entry = self._download_csv_from_gdocs(gdocs_trans_csv,
                                                  gdocs_meta_csv)
        except PODocsError as e:
            if 'Sheet 1 not found' in str(e) \
                    or 'Conversion failed unexpectedly' in str(e):
                self.upload()
            else:
                raise PODocsError(e)
        else:
            self._merge_local_and_gdoc(entry, local_trans_csv, local_meta_csv,
                                       gdocs_trans_csv, gdocs_meta_csv)

            try:
                csv_to_po(local_trans_csv, local_meta_csv,
                          self.locale_root, self.po_files_path, self.header)
            except IOError as e:
                raise PODocsError(e)

        self._clear_temp()

    def download(self):
        """
        Download csv files from GDocs and convert them into po files structure.
        """
        trans_csv_path = os.path.realpath(
            os.path.join(self.temp_path, GDOCS_TRANS_CSV))
        meta_csv_path = os.path.realpath(
            os.path.join(self.temp_path, GDOCS_META_CSV))

        self._download_csv_from_gdocs(trans_csv_path, meta_csv_path)

        try:
            csv_to_po(trans_csv_path, meta_csv_path,
                      self.locale_root, self.po_files_path, header=self.header)
        except IOError as e:
            raise PODocsError(e)

        self._clear_temp()

    def upload(self):
        """
        Upload all po files to GDocs ignoring conflicts.
        This method looks for all msgids in po_files and sends them
        as ods to GDocs Spreadsheet.
        """
        local_ods_path = os.path.join(self.temp_path, LOCAL_ODS)
        try:
            po_to_ods(self.languages, self.locale_root,
                      self.po_files_path, local_ods_path)
        except (IOError, OSError) as e:
            raise PODocsError(e)

        self._upload_file_to_gdoc(local_ods_path)

        self._clear_temp()

    def clear(self):
        """
        Clear GDoc Spreadsheet by sending empty csv file.
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


def git_push(git_message=None, git_repository=None, git_branch=None,
             locale_root=None):
    """
    Pushes specified directory to git remote
    :param git_message: commit message
    :param git_repository: repository address
    :param git_branch: git branch
    :param locale_root: path to locale root folder containing directories
                        with languages
    :return: tuple stdout, stderr of completed command
    """
    if git_message is None:
        git_message = settings.GIT_MESSAGE
    if git_repository is None:
        git_repository = settings.GIT_REPOSITORY
    if git_branch is None:
        git_branch = settings.GIT_BRANCH
    if locale_root is None:
        locale_root = settings.LOCALE_ROOT

    try:
        subprocess.check_call(['git', 'checkout', git_branch])
    except subprocess.CalledProcessError:
        try:
            subprocess.check_call(['git', 'checkout', '-b', git_branch])
        except subprocess.CalledProcessError as e:
            raise PODocsError(e)

    try:
        subprocess.check_call(['git', 'ls-remote', git_repository])
    except subprocess.CalledProcessError:
        try:
            subprocess.check_call(['git', 'remote', 'add', 'po_translator',
                                   git_repository])
        except subprocess.CalledProcessError as e:
            raise PODocsError(e)

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
    if git_branch is None:
        git_branch = settings.GIT_BRANCH
    if locale_root is None:
        locale_root = settings.LOCALE_ROOT

    proc = Popen('git checkout ' + git_branch + ' -- ' + locale_root,
                 shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()

    return stdout, stderr
