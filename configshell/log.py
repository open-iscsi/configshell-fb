'''
This file is part of ConfigShell Community Edition.
Copyright (c) 2011 by RisingTide Systems LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, version 3 (AGPLv3).

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import time
import prefs
import inspect
import console
import traceback

class Log(object):
    '''
    Implements a file and console logger using python's logging facility.
    Log levels are, in raising criticality:
        - debug
        - info
        - warning
        - error
        - critical
    It uses configshell's Prefs() backend for storing some of its parameters,
    who can then be read/changed by other objects using Prefs()
    '''
    __borg_state = {}
    levels = ['critical', 'error', 'warning', 'info', 'debug']
    colors = {'critical': 'red', 'error': 'red', 'warning': 'blue',
              'info': 'green', 'debug': 'blue'}

    def __init__(self, console_level=None,
                 logfile=None, file_level=None):
        '''
        This class implements the Borg pattern.
        @param console_level: Console log level, defaults to 'info'
        @type console_level: str
        @param logfile: Optional logfile.
        @type logfile: str
        @param file_level: File log level, defaults to 'debug'.
        @type file_level: str
        '''
        self.__dict__ = self.__borg_state
        self.con = console.Console()
        self.prefs = prefs.Prefs()

        if console_level:
            self.prefs['loglevel_console'] = console_level
        elif not self.prefs['loglevel_console']:
            self.prefs['loglevel_console'] = 'info'

        if file_level:
            self.prefs['loglevel_file'] = file_level
        elif not self.prefs['loglevel_file']:
            self.prefs['loglevel_file'] = 'debug'

        if logfile:
            self.prefs['logfile'] = logfile

    # Private methods

    def _append(self, msg, level):
        '''
        Just appends the message to the logfile if it exists, prefixing it with
        the current time and level.
        @param msg: The message to log
        @type msg: str
        @param level: The debug level to prefix the message with.
        @type level: str
        '''
        date_fields = time.localtime()
        date = "%d-%02d-%02d %02d:%02d:%02d" \
                % (date_fields[0], date_fields[2], date_fields[1],
                   date_fields[3], date_fields[4], date_fields[5])

        if self.prefs['logfile']:
            path =  os.path.expanduser(self.prefs['logfile'])
            handle = open(path, 'a')
            try:
                handle.write("[%s] %s %s\n" % (level, date, msg))
            finally:
                handle.close()

    def _log(self, level, msg):
        '''
        Do the actual logging.
        @param level: The log level of the message.
        @type level: str
        @param msg: The message to log.
        @type msg: str
        '''
        if self.levels.index(self.prefs['loglevel_file']) \
           >= self.levels.index(level):
            self._append(msg, level.upper())

        if self.levels.index(self.prefs['loglevel_console']) \
           >= self.levels.index(level):
            if self.prefs["color_mode"]:
                msg = self.con.render_text(msg, self.colors[level])
            else:
                msg = "%s: %s" % (level.capitalize(), msg)
            self.con.display(msg)

    # Public methods

    def debug(self, msg):
        '''
        Logs a debug message.
        @param msg: The message to log.
        @type msg: str
        '''
        caller = inspect.stack()[1]
        msg = "%s:%d %s() %s" % (caller[1], caller[2], caller[3], msg)
        self._log('debug', msg)

    def exception(self, msg=None):
        '''
        Logs an error message and dumps a full stack trace.
        @param msg: The message to log.
        @type msg: str
        '''
        trace = traceback.format_exc().rstrip()
        if msg:
            trace += '\n%s' % msg
        self._log('error', trace)

    def info(self, msg):
        '''
        Logs an info message.
        @param msg: The message to log.
        @type msg: str
        '''
        self._log('info', msg)

    def warning(self, msg):
        '''
        Logs a warning message.
        @param msg: The message to log.
        @type msg: str
        '''
        self._log('warning', msg)

    def error(self, msg):
        '''
        Logs an error message.
        @param msg: The message to log.
        @type msg: str
        '''
        self._log('error', msg)

    def critical(self, msg):
        '''
        Logs a critical message.
        @param msg: The message to log.
        @type msg: str
        '''
        self._log('critical', msg)
