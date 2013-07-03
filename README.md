C3PO
====
C3PO is Python module responsible for converting all .po files from locale directory into one .ods file
and sending it to the Google Docs (spreadsheet link provided by user), so users with access to that spreadsheet
can translate expression included there.

This module provides Communicator which deals with uploading, downloading these translations and synchronizing
whole content by merging it.
Package contains basic methods for converting po files into csv, ods formats and back. It also provides
methods for git push and git checkout po files into repository.

Getting started
---------------
### Settings
To manage all settings values module gives possibility to pass them directly as arguments to every method call
or define them in special settings file. Default settings can be found in settings_default.py file.
During the first usage, module copies this file to your home directory into .c3po/settings.py.
In order to change default user authentication info and url, you have to change values in this setting file.
Look into the file and feel free to change variables' standard values.

Module gives you possibility to overload settings.py values when executing from command line.
Execute script with -h option to see what can be changed. For example, executing with different email address:

    $ python c3po.py upload -e email@email.com

### Using Communicator
To start communication with GDOcs you should import `c3po.mod.communicator.Communicator` and create `Communicator`
object. If you have your settings.py properly defined, just create Communicator without any arguments. It will then
take settings values and log in into your Google account.

Object provides methods:
 - `synchronize()` - looks for all .po files, converts them into .csv, looks for differences between them and GDoc,
    writes them into .ods file and uploads merged content to spreadsheet
 - `upload()` - looks for all .po files, converts them into .ods and uploads it to spreadsheet
 - `download()` - downloads two .csv files with translations and metadata from Google Spreadsheet and converts
    it's content into .po files structure
 - `clear()` - clears content of the spreadsheet

Package communicator also provides functions `git_push()` responsible for uploading locale folder into git
and `git_checkout()` doing branch checkout. It's values also can be defined in settings file
or passed to function directly as arguments.

### Converters
Package converters contains three functions used by communicator:
 - `po_to_csv_merge()` - looks for .po files in locale directory structure, and merges new translations with gdoc.csv
    writing them into two new csv files with translations and metadata
 - `csv_to_po()` - converts translations and metadata csv files into .po files structure
 - `po_to_ods()` - converts locale folder with po files into one ods file with two worksheets - translations
    and metadata
 - `csv_to_ods()` - converts two csv files with translations and metadata info one ods file
