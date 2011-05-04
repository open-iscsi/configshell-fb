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

import cPickle

class Prefs(object):
    '''
    This is a preferences backend object used to:
        - Hold the ConfigShell preferences
        - Handle persistent storage and retrieval of these preferences
        - Share the preferences between the ConfigShell and ConfigNode objects

    As it is inherently destined to be shared between objects, this is a Borg.
    '''
    _prefs = {}
    filename = None
    autosave = False
    __borg_state = {}

    def __init__(self, filename=None):
        '''
        Instanciates the ConfigShell preferences object.
        @param filename: File to store the preferencces to.
        @type filename: str
        '''
        self.__dict__ = self.__borg_state
        if filename is not None:
            self.filename = filename

    def __getitem__(self, key):
        '''
        Proxies dict-like references to prefs.
        One specific behavior, though, is that if the key does not exists,
        we will return None instead of raising an exception.
        @param key: The preferences dictionnary key to get.
        @type key: any valid dict key
        @return: The key value
        @rtype: n/a
        '''
        if key in self._prefs:
            return self._prefs[key]
        else:
            return None

    def __setitem__(self, key, value):
        '''
        Proxies dict-like references to prefs.
        @param key: The preferences dictionnary key to set.
        @type key: any valid dict key
        '''
        self._prefs[key] = value
        if self.autosave:
            self.save()

    def __contains__(self, key):
        '''
        Do the preferences contain key ?
        @param key: The preferences dictionnary key to check.
        @type key: any valid dict key
        '''
        if key in self._prefs:
            return True
        else:
            return False

    def __delitem__(self, key):
        '''
        Deletes a preference key.
        @param key: The preference to delete.
        @type key: any valid dict key
        '''
        del self._prefs[key]
        if self.autosave:
            self.save()

    def __iter__(self):
        '''
        Generic iterator for the preferences.
        '''
        return self._prefs.__iter__()

    # Public methods

    def keys(self):
        '''
        @return: Returns the list of keys in preferences.
        @rtype: list
        '''
        return self._prefs.keys()

    def items(self):
        '''
        @return: Returns the list of items in preferences.
        @rtype: list of (key, value) tuples
        '''
        return self._prefs.items()

    def iteritems(self):
        '''
        @return: Iterates on the items in preferences.
        @rtype: yields items that are (key, value) pairs
        '''
        return self._prefs.iteritems()

    def save(self, filename=None):
        '''
        Saves the preferences to disk. If filename is not specified,
        use the default one if it is set, else do nothing.
        @param filename: Optional alternate file to use.
        @type filename: str
        '''
        if filename is None:
            filename = self.filename

        if filename is not None:
            fsock = open(filename, 'wb')
            try:
                cPickle.dump(self._prefs, fsock, 2)
            finally:
                fsock.close()

    def load(self, filename=None):
        '''
        Loads the preferences from file. Use either the supplied filename,
        or the default one if set. Else, do nothing.
        '''
        if filename is None:
            filename = self.filename

        if filename is not None:
            fsock = open(filename, 'rb')
            try:
                self._prefs = cPickle.load(fsock)
            finally:
                fsock.close()
