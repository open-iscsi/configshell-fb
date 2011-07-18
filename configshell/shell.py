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
import sys
import readline
import simpleparse.parser
import simpleparse.dispatchprocessor

import configshell.log as log
import configshell.prefs as prefs
import configshell.console as console

from configshell.node import ConfigNode, ExecutionError

# A fix for frozen packages
import signal
def handle_sigint(signum, frame):
    '''
    Raise KeyboardInterrupt when we get a SIGINT.
    This is normally done by python, but even after patching
    pyinstaller 1.4 to ignore SIGINT in the C wrapper code, we
    still have to do the translation ourselves.
    '''
    raise KeyboardInterrupt

try:
    signal.signal(signal.SIGINT, handle_sigint)
except Exception:
    # In a thread, this fails
    pass

class ConfigShell(object):
    '''
    This is a simple CLI command interpreter that can be used both in
    interactive or non-interactive modes.
    It is based on a tree of ConfigNode objects, which can be navigated.

    The ConfigShell object itself provides global navigation commands.
    It also handles the parsing of local commands (specific to a certain
    ConfigNode) according to the ConfigNode commands definitions.
    If the ConfigNode provides hooks for possible parameter values in a given
    context, then the ConfigShell will also provide command-line completion
    using the TAB key. If no completion hooks are available from the
    ConfigNode, the completion function will still be able to display some help
    and general syntax advice (as much as the ConfigNode will provide).

    Interactive sessions can be saved/loaded automatically by ConfigShell is a
    writable session directory is supplied. This includes command-line history,
    current node and global parameters.
    '''

    default_prefs = {'color_path': 'magenta',
                     'color_command': 'cyan',
                     'color_parameter': 'magenta',
                     'color_keyword': 'cyan',
                     'completions_in_columns': True,
                     'logfile': None,
                     'loglevel_console': 'info',
                     'loglevel_file': 'debug9',
                     'color_mode': True,
                     'prompt_length': 30,
                     'tree_max_depth': 0,
                     'tree_status_mode': True,
                     'tree_round_nodes': True,
                     'tree_show_root': True
                    }

    _completion_help_topic = ''
    _current_parameter = ''
    _current_token = ''
    _current_completions = []
    complete_key = 'tab'
    grammar = \
            r'''
            <eol>        := '\n'
            <space>      := ' '+
            line         := (linepath)/(space?, command), parameters?, eol?
            >linepath<   := space?, path, space?, command?
            command      := [a-zA-Z0-9_]+
            >parameters< := (space, kparam/pparam)+
            pparam       := var
            kparam       := keyword, '=', value
            >keyword<    := [a-zA-Z0-9_\-]+
            >value<      := var?
            path         := bookmark/pathstd/[0-9]+/'..'/'.'/'*'
            <pathstd>    := ([a-zA-Z0-9:_.-]*, '/', [a-zA-Z0-9:_./-]*, '*'?)
            <var>        := [a-zA-Z0-9_\\+/.<>~@:-%]+
            <bookmark>   := '@', var?
            '''

    def __init__(self, preferences_dir=None):
        '''
        Creates a new ConfigShell.
        @param preferences_dir: Directory to load/save preferences from/to
        @type preferences_dir: str
        '''
        self._current_node = None
        self._root_node = None
        self._exit = False

        self._parser = simpleparse.parser.Parser(self.grammar, root='line')
        readline.set_completer_delims('\t\n ~!#$^&()[{]}\|;\'",?')

        self.log = log.Log()

        if preferences_dir is not None:
            preferences_dir = os.path.expanduser(preferences_dir)
            if not os.path.exists(preferences_dir):
                os.makedirs(preferences_dir)
            self._prefs_file = preferences_dir + '/prefs.bin'
            self.prefs = prefs.Prefs(self._prefs_file)
            self._cmd_history = preferences_dir + '/history.txt'
            self._save_history = True
            if not os.path.isfile(self._cmd_history):
                try:
                    open(self._cmd_history, 'w').close()
                except:
                    self.log.warning("Cannot create history file %s, "
                                     % self._cmd_history
                                     + "command history will not be saved.")
                    self._save_history = False

            if os.path.isfile(self._cmd_history):
                try:
                    readline.read_history_file(self._cmd_history)
                except IOError:
                    self.log.warning("Cannot read command history file %s."
                                     % self._cmd_history)

            if self.prefs['logfile'] is None:
                self.prefs['logfile'] = preferences_dir + '/' + 'log.txt'

            self.prefs.autosave = True

        else:
            self.prefs = prefs.Prefs()
            self._save_history = False

        try:
            self.prefs.load()
        except IOError:
            self.log.warning("Could not load preferences file %s."
                             % self._prefs_file)

        for pref, value in self.default_prefs.iteritems():
            if pref not in self.prefs:
                self.prefs[pref] = value

        self.con = console.Console()

    # Private methods

    def _set_readline_display_matches(self):
        '''
        In order to stay compatible with python versions < 2.6,
        we are not using readline.set_completion_display_matches_hook() but
        instead use ctypes there to bind to the C readline hook if needed.
        This hooks a callback function to display readline completions.
        '''
        if 'set_completion_display_matches_hook' in dir(readline):
            readline.set_completion_display_matches_hook(
                self._display_completions_python)
        else:
            from ctypes import cdll, CFUNCTYPE, POINTER
            from ctypes import c_char_p, c_int, c_void_p, cast
            libreadline = None
            try:
                libreadline = cdll.LoadLibrary('libreadline.so')
            except OSError:
                try:
                    libreadline = cdll.LoadLibrary('libreadline.so.5')
                except OSError:
                    try:
                        libreadline = cdll.LoadLibrary('libreadline.so.6')
                    except OSError:
                        self.log.critical(
                            "Could not find readline shared library.")
            if libreadline:
                completion_func_type = \
                        CFUNCTYPE(None, POINTER(c_char_p), c_int, c_int)
                hook = completion_func_type(self._display_completions)
                ptr = c_void_p.in_dll(libreadline,
                                      'rl_completion_display_matches_hook')
                ptr.value = cast(hook, c_void_p).value

    def _display_completions_python(self, substitution, matches, max_length):
        '''
        A wrapper to be used with python>=2.6 readline display completion hook.
        '''
        self.log.debug("Using python >=2.6 readline display hook.")
        matches = [substitution] + matches
        self._display_completions(matches, len(matches)-1, max_length)

    def _display_completions(self, matches, num_matches, max_length):
        '''
        Hooked up to readline, this method displays:
            - Possible completions for path/command/parameters
            - Some help about the command being written
            - The current parameter name and type hovering above the cursor
        @param matches: Passed by readline, indexed from 1 to num_matches+1.
        @type matches: a C list
        @param num_matches: The number of matches.
        @type num_matches: int
        @param max_length: Length of the longer matches item.
        @type max_length: int
        '''
        (x_orig, y_pos) = self.con.get_cursor_xy()
        self.con.raw_write("\n")
        width = self.con.get_width()
        max_length += 2

        def just(text):
            '''
            Justifies the text to the max match length.
            '''
            return text.ljust(max_length, " ")

        # Sort the matches
        if self._current_parameter:
            keywords = []
            values = []
            for index in range(1, num_matches+1):
                match = matches[index]
                if match.endswith('='):
                    keywords.append(
                        self.con.render_text(
                            just(match), self.prefs['color_keyword']))
                else:
                    (keyword, sep, value) = match.partition('=')
                    if sep:
                        values.append(
                            self.con.render_text(
                                just(value), self.prefs['color_parameter']))
                    else:
                        values.append(
                            self.con.render_text(
                                just(match), self.prefs['color_parameter']))
            matches = [''] + values + keywords
        else:
            paths = []
            commands = []
            for index in range(1, num_matches+1):
                match = matches[index]
                if '/' in match or match.startswith('@') or '*' in match:
                    paths.append(
                        self.con.render_text(
                            just(match), self.prefs['color_path']))
                else:
                    commands.append(
                        self.con.render_text(
                            just(match), self.prefs['color_command']))
            matches = [''] + paths + commands

        # Display the possible completions

        if num_matches:

            if max_length < width:
                num_per_line = width / max_length
                if num_per_line * max_length == width:
                    num_per_line -= 1
            else:
                num_per_line = 1

            if not self.prefs['completions_in_columns']:
                index_match = 0
                done = False
                while not done:
                    for index_col in range(num_per_line):
                        index_match += 1
                        self.con.raw_write(matches[index_match])
                        if index_match == num_matches:
                            done = True
                            break
                    self.con.raw_write('\n')
            else:
                count = (num_matches + num_per_line - 1) / num_per_line
                if len > 0 and len <= num_per_line:
                    count = 1
                for i in range(1, count+1):
                    l = i
                    for j in range(num_per_line):
                        if l > num_matches or matches[l] == 0:
                            break
                        else:
                            self.con.raw_write(matches[l])
                        l += count
                    self.con.raw_write("\n")

        # Draw the "hovering" hint with currently filled parameter name
        line = "%s%s" % (self._get_prompt(), readline.get_line_buffer())
        line_offset = len(self._get_prompt())
        begidx = readline.get_begidx() + line_offset
        endidx = readline.get_endidx() + line_offset
        text = line[begidx:endidx]
        (keyword, sep, value) = text.partition('=')
        if sep:
            paramidx = begidx + len(keyword) + 1
        else:
            paramidx = begidx
        self.con.display("%s%s" % ("".rjust(paramidx, "."),
                                   self._current_token))
        self.con.raw_write("%s" % line)

        # Move the cursor where it should be
        y_pos = self.con.get_cursor_xy()[1]
        self.con.set_cursor_xy(x_orig, y_pos)

    def _complete_token_command(self, text, path, command, pparams, kparams):
        '''
        Completes a partial command token, which could also be the beginning
        of a path.
        @param path: Path of the target ConfigNode.
        @type path: str
        @param command: The command (if any) found by the parser.
        @type command: str
        @param pparams: Positional parameters from commandline.
        @type pparams: list of str
        @param kparams: Keyword parameters from commandline.
        @type kparams: dict of str:str
        @param text: Current text being typed by the user.
        @type text: str
        @return: Possible completions for the token.
        @rtype: list of str
        '''
        completions = []
        target = self._current_node.get_node(path)
        commands = target.list_commands()
        self.log.debug("Completing command token among %s" % str(commands))

        # Start with the possible commands
        for command in commands:
            if command.startswith(text):
                completions.append(command)
        if len(completions) == 1:
            completions[0] = completions[0] + ' '

        # No identified path yet on the command line, this might be it
        if not path:
            path_completions = [child.name + '/'
                                for child in self._current_node.children
                                if child.name.startswith(text)]
            if not text:
                path_completions.append('/')
                if len(self._current_node.children) > 1:
                    path_completions.append('* ')

            if path_completions:
                if completions:
                    self._current_token = \
                            self.con.render_text(
                                'path', self.prefs['color_path']) \
                            + '|' \
                            + self.con.render_text(
                                'command', self.prefs['color_command'])
                else:
                    self._current_token = \
                            self.con.render_text(
                                'path', self.prefs['color_path'])
            else:
                self._current_token = \
                        self.con.render_text(
                            'command', self.prefs['color_command'])
            if len(path_completions) == 1 and \
               not path_completions[0][-1] in [' ', '*'] and \
               not self._current_node.get_node(path_completions[0]).children:
                path_completions[0] = path_completions[0] + ' '
            completions.extend(path_completions)
        else:
            self._current_token = \
                    self.con.render_text(
                        'command', self.prefs['color_command'])

        # Even a bookmark
        bookmarks = ['@' + bookmark for bookmark in self.prefs['bookmarks']
                     if bookmark.startswith("%s" % text.lstrip('@'))]
        self.log.debug("Found bookmarks %s." % str(bookmarks))
        if bookmarks:
            completions.extend(bookmarks)


        # We are done
        return completions

    def _complete_token_path(self, text, path, command, pparams, kparams):
        '''
        Completes a partial path token.
        @param path: Path of the target ConfigNode.
        @type path: str
        @param command: The command (if any) found by the parser.
        @type command: str
        @param pparams: Positional parameters from commandline.
        @type pparams: list of str
        @param kparams: Keyword parameters from commandline.
        @type kparams: dict of str:str
        @param text: Current text being typed by the user.
        @type text: str
        @return: Possible completions for the token.
        @rtype: list of str
        '''
        completions = []
        if text.endswith('.'):
            text = text + '/'
        (basedir, slash, partial_name) = text.rpartition('/')
        self.log.debug("Got basedir=%s, partial_name=%s"
                       % (basedir, partial_name))
        basedir = basedir + slash
        target = self._current_node.get_node(basedir)
        names = [child.name for child in target.children]

        # Iterall path completion
        if names and partial_name in ['', '*']:
            # Not suggesting iterall to end a path that has only one
            # child allows for fast TAB action to add the only child's
            # name.
            if len(names) > 1:
                completions.append("%s* " % basedir)

        for name in names:
            num_matches = 0
            if name.startswith(partial_name):
                num_matches += 1
                if num_matches == 1:
                    completions.append("%s%s/" % (basedir, name))
                else:
                    completions.append("%s%s" % (basedir, name))

        # Bookmarks
        bookmarks = ['@' + bookmark for bookmark in self.prefs['bookmarks']
                     if bookmark.startswith("%s" % text.lstrip('@'))]
        self.log.debug("Found bookmarks %s." % str(bookmarks))
        if bookmarks:
            completions.extend(bookmarks)

        if len(completions) == 1:
            self.log.debug("One completion left.")
            if not completions[0].endswith("* "):
                if not self._current_node.get_node(completions[0]).children:
                    completions[0] = completions[0].rstrip('/') + ' '

        self._current_token = \
                self.con.render_text(
                    'path', self.prefs['color_path'])
        return completions

    def _complete_token_pparam(self, text, path, command, pparams, kparams):
        '''
        Completes a positional parameter token, which can also be the keywork
        part of a kparam token, as before the '=' sign is on the line, the
        parser cannot know better.
        @param path: Path of the target ConfigNode.
        @type path: str
        @param command: The command (if any) found by the parser.
        @type command: str
        @param pparams: Positional parameters from commandline.
        @type pparams: list of str
        @param kparams: Keyword parameters from commandline.
        @type kparams: dict of str:str
        @param text: Current text being typed by the user.
        @type text: str
        @return: Possible completions for the token.
        @rtype: list of str
        '''
        completions = []
        target = self._current_node.get_node(path)
        cmd_params, free_pparams, free_kparams = \
                target.get_command_signature(command)
        current_parameters = {}
        for index in range(len(pparams)):
            if index < len(cmd_params):
                current_parameters[cmd_params[index]] = pparams[index]
        for key, value in kparams.iteritems():
            current_parameters[key] = value
        self._completion_help_topic = command
        completion_method = target.get_completion_method(command)
        self.log.debug("Command %s accepts parameters %s."
                       % (command, cmd_params))

        # Do we still accept positional params ?
        pparam_ok = True
        for index in range(len(cmd_params)):
            param = cmd_params[index]
            if param in kparams:
                if index <= len(pparams):
                    pparam_ok = False
                    self.log.debug(
                        "No more possible pparams (because of kparams).")
                    break
            elif (text.strip() == '' and len(pparams) == len(cmd_params)) \
                  or (len(pparams) > len(cmd_params)):
                pparam_ok = False
                self.log.debug("No more possible pparams.")
                break
        else:
            if len(cmd_params) == 0:
                pparam_ok = False
                self.log.debug("No more possible pparams (none exists)")

        # If we do, find out which one we are completing
        if pparam_ok:
            if not text:
                pparam_index = len(pparams)
            else:
                pparam_index = len(pparams) - 1
            self._current_parameter = cmd_params[pparam_index]
            self.log.debug("Completing pparam %s." % self._current_parameter)
            if completion_method:
                pparam_completions = completion_method(
                    current_parameters, text, self._current_parameter)
                if pparam_completions is not None:
                    completions.extend(pparam_completions)

        # Add the keywords for parameters not already on the line
        if text:
            offset = 1
        else:
            offset = 0
        keyword_completions = [param + '=' \
                       for param in cmd_params[len(pparams)-offset:] \
                       if param not in kparams \
                       if param.startswith(text)]

        self.log.debug("Possible pparam values are %s."
                       % str(completions))
        self.log.debug("Possible kparam keywords are %s."
                       % str(keyword_completions))

        if keyword_completions:
            if self._current_parameter:
                self._current_token = \
                        self.con.render_text(
                            self._current_parameter, \
                            self.prefs['color_parameter']) \
                        + '|'  \
                        + self.con.render_text(
                            'keyword=', self.prefs['color_keyword'])
            else:
                self._current_token = \
                        self.con.render_text(
                            'keyword=', self.prefs['color_keyword'])
        else:
            if self._current_parameter:
                self._current_token = \
                        self.con.render_text(
                            self._current_parameter,
                            self.prefs['color_parameter'])
            else:
                self._current_token = ''

        completions.extend(keyword_completions)

        if free_kparams or free_pparams:
            self.log.debug("Command has free [kp]params.")
            if completion_method:
                self.log.debug("Calling completion method for free params.")
                free_completions = completion_method(
                    current_parameters, text, '*')
                do_free_pparams = False
                do_free_kparams = False
                for free_completion in free_completions:
                    if free_completion.endswith("="):
                        do_free_kparams = True
                    else:
                        do_free_pparams = True

                if do_free_pparams:
                    self._current_token = \
                            self.con.render_text(
                                free_pparams, self.prefs['color_parameter']) \
                            + '|' + self._current_token
                    self._current_token = self._current_token.rstrip('|')
                    if not self._current_parameter:
                        self._current_parameter = 'free_parameter'

                if do_free_kparams:
                    if not 'keyword=' in self._current_token:
                        self._current_token = \
                                self.con.render_text(
                                    'keyword=', self.prefs['color_keyword']) \
                                + '|' + self._current_token
                        self._current_token = self._current_token.rstrip('|')
                    if not self._current_parameter:
                        self._current_parameter = 'free_parameter'

                completions.extend(free_completions)

        self.log.debug("Found completions %s." % str(completions))
        return completions

    def _complete_token_kparam(self, text, path, command, pparams, kparams):
        '''
        Completes a keyword=value parameter token.
        @param path: Path of the target ConfigNode.
        @type path: str
        @param command: The command (if any) found by the parser.
        @type command: str
        @param pparams: Positional parameters from commandline.
        @type pparams: list of str
        @param kparams: Keyword parameters from commandline.
        @type kparams: dict of str:str
        @param text: Current text being typed by the user.
        @type text: str
        @return: Possible completions for the token.
        @rtype: list of str
        '''
        self.log.debug("Called for text='%s'" % text)
        target = self._current_node.get_node(path)
        cmd_params = target.get_command_signature(command)[0]
        self.log.debug("Command %s accepts parameters %s."
                       % (command, cmd_params))

        (keyword, sep, current_value) = text.partition('=')
        self.log.debug("Completing '%s' for kparam %s"
                       % (current_value, keyword))

        self._current_parameter = keyword
        current_parameters = {}
        for index in range(len(pparams)):
            current_parameters[cmd_params[index]] = pparams[index]
        for key, value in kparams.iteritems():
            current_parameters[key] = value
        completion_method = target.get_completion_method(command)
        if completion_method:
            completions = completion_method(
                current_parameters, current_value, keyword)
            if completions is None:
                completions = []

        self._current_token = \
                self.con.render_text(
                    self._current_parameter, self.prefs['color_parameter'])

        self.log.debug("Found completions %s." % str(completions))

        return ["%s=%s" % (keyword, completion) for completion in completions]

    def _complete(self, text, state):
        '''
        Text completion method, directly called by readline.
        Finds out what token the user wants completion for, and calls the
        _dispatch_completion() to get the possible completions.
        Then implements the state system needed by readline to return those
        possible completions to readline.
        @param text: The text to complete.
        @type text: str
        @returns: The next possible completion for text.
        @rtype: str
        '''
        self._set_readline_display_matches()

        if state == 0:
            cmdline = readline.get_line_buffer()
            self._current_completions = []
            self._completion_help_topic = ''
            self._current_parameter = ''

            (result_trees, path, command, pparams, kparams) = \
                    self._parse_cmdline(cmdline)

            beg = readline.get_begidx()
            end = readline.get_endidx()
            if beg == end:
                # No text under the cursor, fake it so that the parser
                # result_trees gives us a token name on a second parser call
                self.log.debug("Faking text entry on commandline.")
                result_trees = self._parse_cmdline(cmdline + 'x')[0]
                end += 1

            for tree in result_trees:
                if beg == tree[1] and end == tree[2]:
                    current_token = tree[0]
                    break

            self._current_completions = \
                    self._dispatch_completion(path, command,
                                              pparams, kparams,
                                              text, current_token)

            self.log.debug("Returning completions %s to readline."
                           % str(self._current_completions))

        if state < len(self._current_completions):
            return self._current_completions[state]
        else:
            return None

    def _dispatch_completion(self, path, command,
                             pparams, kparams, text, current_token):
        '''
        This method takes care of dispatching the current completion request
        from readline (via the _complete() method) to the relevant token
        completion methods. It has to cope with the fact that the commandline
        being incomplete yet,
        Of course, as the command line is still unfinished, the parser can
        only do so much of a job. For instance, until the '=' sign is on the
        command line, there is no way to distinguish a positional parameter
        from the begining of a keyword=value parameter.
        @param path: Path of the target ConfigNode.
        @type path: str
        @param command: The command (if any) found by the parser.
        @type command: str
        @param pparams: Positional parameters from commandline.
        @type pparams: list of str
        @param kparams: Keyword parameters from commandline.
        @type kparams: dict of str:str
        @param text: Current text being typed by the user.
        @type text: str
        @param current_token: Name of token to complete.
        @type current_token: str
        @return: Possible completions for the token.
        @rtype: list of str
        '''
        completions = []

        self.log.debug("Dispatching completion for %s token. "
                       % current_token
                       + "text='%s', path='%s', command='%s', "
                       % (text, path, command)
                       + "pparams=%s, kparams=%s"
                       % (str(pparams), str(kparams)))

        (path, iterall) = path.partition('*')[:2]
        if iterall:
            try:
                target = self._current_node.get_node(path)
            except ValueError:
                cpl_path = path
            else:
                children = target.children
                if children:
                    cpl_path = children[0].path
        else:
            cpl_path = path


        if current_token == 'command':
            completions = self._complete_token_command(text, cpl_path, command,
                                                 pparams, kparams)
        elif current_token == 'path':
            completions = \
                    self._complete_token_path(text, path, command,
                                              pparams, kparams)
        elif current_token == 'pparam':
            completions = \
                    self._complete_token_pparam(text, cpl_path, command,
                                                pparams, kparams)
        elif current_token == 'kparam':
            completions = \
                    self._complete_token_kparam(text, cpl_path, command,
                                                pparams, kparams)
        else:
            self.log.debug("Cannot complete unknown token %s."
                           % current_token)

        return completions

    def _get_prompt(self):
        '''
        Returns the command prompt string.
        '''
        prompt_path = self._current_node.path
        prompt_length = self.prefs['prompt_length']

        if prompt_length and prompt_length < len(prompt_path):
            half = (prompt_length-3)/2
            prompt_path = "%s...%s" \
                    % (prompt_path[:half], prompt_path[-half:])

        if 'prompt_msg' in dir(self._current_node):
            return "%s%s> " % (self._current_node.prompt_msg(),
                               prompt_path)
        else:
            return "%s> " % prompt_path

    def _cli_loop(self):
        '''
        Starts the configuration shell interactive loop, that:
            - Goes to the last current path
            - Displays the prompt
            - Waits for user input
            - Runs user command
        '''
        while not self._exit:
            try:
                readline.parse_and_bind("%s: complete" % self.complete_key)
                readline.set_completer(self._complete)
                cmdline = raw_input(self._get_prompt()).strip()
            except EOFError:
                self.con.raw_write('exit\n')
                cmdline = "exit"
            self.run_cmdline(cmdline)
            if self._save_history:
                try:
                    readline.write_history_file(self._cmd_history)
                except IOError, msg:
                    self.log.warning(
                        "Cannot write to command history file %s." \
                        % self._cmd_history)
                    self.log.warning(
                        "Saving command history has been disabled!")
                    self._save_history = False

    def _parse_cmdline(self, line):
        '''
        Parses the command line entered by the user. This is a wrapper around
        the actual simpleparse parsed that pre-chews the result trees to
        cleanly extract the tokens we care for (parameters, path, command).
        @param line: The command line to parse.
        @type line: str
        @return: (result_trees, path, command, pparams, kparams),
        pparams being positional parameters and kparams the keyword=value.
        @rtype: (list of tuple, str, str, list, dict) For the exact
        result_trees tuple format, c.f. the simpleparse documentation.
        '''
        self.log.debug("Parsing commandline.")
        path = ''
        command = ''
        pparams = []
        kparams = {}
        (success, result_trees, next_character) = self._parser.parse(line)
        if success:
            self.log.debug(str(result_trees))
            for tree in result_trees:
                token = tree[0]
                value = line[tree[1]:tree[2]]
                self.log.debug("Found %s token %s." % (token, value))
                if token == 'path':
                    path = value
                elif token == 'command':
                    command = value
                elif token == 'pparam':
                    pparams.append(value)
                elif token == 'kparam':
                    (keyword, sep, value) = value.partition('=')
                    kparams[keyword] = value

        self.log.debug("Parse gave path='%s' command='%s' " % (path, command)
                       + "pparams=%s " % str(pparams)
                       + "kparams=%s" % str(kparams))
        return (result_trees, path, command, pparams, kparams)

    def _execute_command(self, path, command, pparams, kparams):
        '''
        Calls the target node to execute a command.
        Behavior depends on the target node command's result:
            - An 'EXIT' string will trigger shell exit.
            - None will do nothing.
            - A ConfigNode object will trigger a current_node change.
        @param path: Path of the target node.
        @type path: str
        @param command: The command to call.
        @type command: str
        @param pparams: The positional parameters to use.
        @type pparams: list
        @param kparams: The keyword=value parameters to use.
        @type kparams: dict
        '''
        if path.endswith('*'):
            path = path.rstrip('*')
            iterall = True
        else:
            iterall = False

        if not path:
            path = '.'

        if not command:
            if iterall:
                command = 'ls'
            else:
                command = 'cd'
                pparams = ['.']

        try:
            target = self._current_node.get_node(path)
        except ValueError, msg:
            self.log.error(msg)
        else:
            result = None
            if not iterall:
                targets = [target]
            else:
                targets = target.children
            for target in targets:
                if iterall:
                    self.con.display("[%s]" % target.path)
                result = target.execute_command(command, pparams, kparams)
            self.log.debug("Command execution returned %r" % result)
            if isinstance(result, ConfigNode):
                self._current_node = result
            elif result == 'EXIT':
                self._exit = True
            elif result is not None:
                raise ExecutionError("Unexpected result: %r" % result)

    # Public methods

    def run_cmdline(self, cmdline):
        '''
        Runs the specified command. Global commands are checked first,
        then local commands from the current node.

        Command syntax is:
        [PATH] COMMAND [POSITIONAL_PARAMETER]+ [PARAMETER=VALUE]+

        @param cmdline: The command line to run
        @type cmdline: str
        '''
        if cmdline:
            self.log.debug("Running command line '%s'." % cmdline)
            path, command, pparams, kparams = self._parse_cmdline(cmdline)[1:]
            self._execute_command(path, command, pparams, kparams)

    def run_script(self, script_path, exit_on_error=True):
        '''
        Runs the script located at script_path.
        Script runs always start from the root context.
        @param script_path: File path of the script to run
        @type script_path: str
        @param exit_on_error: If True, stops the run if an error occurs
        @type exit_on_error: bool
        '''
        try:
            script_fd = open(script_path, 'r')
            self.run_stdin(script_fd, exit_on_error)
        except IOError, msg:
            raise IOError(msg)
        finally:
            script_fd.close()

    def run_stdin(self, file_descriptor=sys.stdin, exit_on_error=True):
        '''
        Reads commands to be run from a file descriptor, stdin by default.
        The run always starts from the root context.
        @param file_descriptor: The file descriptor to read commands from
        @type file_descriptor: file object
        @param exit_on_error: If True, stops the run if an error occurs
        @type exit_on_error: bool
        '''
        self._current_node = self._root_node
        for cmdline in file_descriptor:
            try:
                self.run_cmdline(cmdline)
            except Exception, msg:
                self.log.error(msg)
                if exit_on_error is True:
                    self.log.exception("Aborting run on error.")
                    break
                else:
                    self.log.exception("Keep running after an error.")

    def run_interactive(self):
        '''
        Starts interactive CLI mode.
        '''
        history = self.prefs['path_history']
        index = self.prefs['path_history_index']
        if history and index:
            if index < len(history):
                try:
                    target = self._root_node.get_node(history[index])
                except ValueError:
                    self._current_node = self._root_node
                else:
                    self._current_node = target
        try:
            old_completer = readline.get_completer()
            self._cli_loop()
        except KeyboardInterrupt:
            self.con.raw_write('\n')
            self.run_interactive()
        except Exception:
            self.log.exception()
            self.run_interactive()
        finally:
            readline.set_completer(old_completer)

    def attach_root_node(self, root_node):
        '''
        @param root_node: The root ConfigNode object
        @type root_node: ConfigNode
        '''
        self._current_node = root_node
        self._root_node = root_node
