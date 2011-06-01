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

import re
import log
import prefs
import console
import inspect

class ExecutionError(Exception):
    pass

class ConfigNode(object):
    '''
    The ConfigNode class defines a common skeleton to be used by specific
    implementation. It is "purely virtual" (sorry for using non-pythonic
    vocabulary there ;-) ).
    '''
    _path_separator = '/'
    _path_current = '.'
    _path_previous = '..'

    ui_command_method_prefix = "ui_command_"
    ui_complete_method_prefix = "ui_complete_"
    ui_setgroup_method_prefix = "ui_setgroup_"
    ui_getgroup_method_prefix = "ui_getgroup_"

    help_intro = '''
                 GENERALITIES
                 ============
                 This is an interactive shell in which you can create, delete
                 and configure configuration objects.

                 The available commands depend on the work path you are in the
                 objects tree. The prompt that starts each command line
                 indicates your current position, or you can run the I{pwd}
                 command to that effect. Navigating the tree is done using the
                 I{cd} command. Please try I{help cd} for navigation tips.

                 COMMAND SYNTAX
                 ==============
                 Commands are built using the following syntax:

                 [I{PATH}] I{COMMAND_NAME} [I{OPTIONS}]

                 The I{PATH} indicates the object to run the command on. If
                 ommited, the command will be run from your working path.

                 The I{OPTIONS} depend on the command. Please use I{help
                 COMMAND} to get more information.
                 '''

    def __init__(self):
        self._name = 'config node'
        self._children = set([])
        self._parent = None

        self.prefs = prefs.Prefs()
        self.log = log.Log()
        self.con = console.Console()

        self._configuration_groups = {}
        self._configuration_groups['global'] = \
                {'tree_round_nodes': \
                 [self.ui_type_bool,
                  'Tree node display style.'],

                 'tree_status_mode': \
                 [self.ui_type_bool,
                  'Whether or not to display status in tree.'],

                 'tree_max_depth': \
                 [self.ui_type_number,
                  'Maximum depth of displayed node tree.'],

                 'tree_show_root': \
                 [self.ui_type_bool,
                  'Whether or not to disply tree root.'],

                 'color_mode': \
                 [self.ui_type_bool,
                  'Console color display mode.'],

                 'loglevel_console': \
                 [self.ui_type_loglevel,
                  'Log level for messages going to the console.'],

                 'loglevel_file': \
                 [self.ui_type_loglevel,
                  'Log level for messages going to the log file.'],

                 'logfile': \
                 [self.ui_type_string,
                  'Logfile to use.'],

                 'color_default': \
                 [self.ui_type_colordefault,
                  'Default text display color.'],

                 'color_path': \
                 [self.ui_type_color,
                  'Color to use for path completions'],

                 'color_command': \
                 [self.ui_type_color,
                  'Color to use for command completions.'],

                 'color_parameter': \
                 [self.ui_type_color,
                  'Color to use for parameter completions.'],

                 'color_keyword': \
                 [self.ui_type_color,
                  'Color to use for keyword completions.'],

                 'completions_in_columns': \
                 [self.ui_type_bool,
                  'If B{true}, completions are displayed in columns, ' \
                  + 'else in lines.'],

                 'prompt_length': \
                 [self.ui_type_number,
                  'Maximum length of the shell prompt path, 0 means infinite.']
                }

        if self.prefs['bookmarks'] is None:
            self.prefs['bookmarks'] = {}

    # User interface types

    def ui_type_number(self, value=None, enum=False, reverse=False):
        '''
        UI parameter type helper for number parameter type.
        @param value: Value to check against the type.
        @type value: anything
        @param enum: Has a meaning only if value is omitted. If set, returns
        a list of the possible values for the type, or [] if this is not
        possible. If not set, returns a text description of the type format.
        @type enum: bool
        @param reverse: If set, translates an internal value to its UI
        string representation.
        @type reverse: bool
        @return: c.f. parameter enum description.
        @rtype: str|list|None
        @raise ValueError: If the value does not check ok against the type.
        '''
        if reverse:
            if value is not None:
                return str(value)
            else:
                return 'n/a'

        type_enum = []
        syntax = "NUMBER"
        if value is None:
            if enum:
                return type_enum
            else:
                return syntax
        elif not value:
            return None
        else:
            try:
                value = int(value)
            except ValueError:
                raise ValueError("Syntax error, '%s' is not a %s." \
                                 % (value, syntax))
            else:
                return value

    def ui_type_string(self, value=None, enum=False, reverse=False):
        '''
        UI parameter type helper for string parameter type.
        @param value: Value to check against the type.
        @type value: anything
        @param enum: Has a meaning only if value is omitted. If set, returns
        a list of the possible values for the type, or [] if this is not
        possible. If not set, returns a text description of the type format.
        @type enum: bool
        @param reverse: If set, translates an internal value to its UI
        string representation.
        @type reverse: bool
        @return: c.f. parameter enum description.
        @rtype: str|list|None
        @raise ValueError: If the value does not check ok against the type.
        '''
        if reverse:
            if value is not None:
                return value
            else:
                return 'n/a'

        type_enum = []
        syntax = "STRING_OF_TEXT"
        if value is None:
            if enum:
                return type_enum
            else:
                return syntax
        elif not value:
            return None
        else:
            try:
                value = str(value)
            except ValueError:
                raise ValueError("Syntax error, '%s' is not a %s." \
                                 % (value, syntax))
            else:
                return value

    def ui_type_bool(self, value=None, enum=False, reverse=False):
        '''
        UI parameter type helper for boolean parameter type. Valid values are
        either 'true' or 'false'.
        @param value: Value to check against the type.
        @type value: anything
        @param enum: Has a meaning only if value is omitted. If set, returns
        a list of the possible values for the type, or None if this is not
        possible. If not set, returns a text description of the type format.
        @type enum: bool
        @param reverse: If set, translates an internal value to its UI
        string representation.
        @type reverse: bool
        @return: c.f. parameter enum description.
        @rtype: str|list|None
        @raise ValueError: If the value does not check ok againts the type.
        '''
        if reverse:
            if value:
                return 'true'
            else:
                return 'false'
        type_enum = ['true', 'false']
        syntax = '|'.join(type_enum)
        if value is None:
            if enum:
                return type_enum
            else:
                return syntax
        elif value == 'true':
            return True
        elif value == 'false':
            return False
        else:
            raise ValueError("Syntax error, '%s' is not %s." \
                             % (value, syntax))

    def ui_type_loglevel(self, value=None, enum=False, reverse=False):
        '''
        UI parameter type helper for log level parameter type.
        @param value: Value to check against the type.
        @type value: anything
        @param enum: Has a meaning only if value is omitted. If set, returns
        a list of the possible values for the type, or None if this is not
        possible. If not set, returns a text description of the type format.
        @type enum: bool
        @param reverse: If set, translates an internal value to its UI
        string representation.
        @type reverse: bool
        @return: c.f. parameter enum description.
        @rtype: str|list|None
        @raise ValueError: If the value does not check ok againts the type.
        '''
        if reverse:
            if value is not None:
                return value
            else:
                return 'n/a'

        type_enum = self.log.levels
        syntax = '|'.join(type_enum)
        if value is None:
            if enum:
                return type_enum
            else:
                return syntax
        elif value in type_enum:
            return value
        else:
            raise ValueError("Syntax error, '%s' is not %s" \
                             % (value, syntax))

    def ui_type_color(self, value=None, enum=False, reverse=False):
        '''
        UI parameter type helper for color parameter type.
        @param value: Value to check against the type.
        @type value: anything
        @param enum: Has a meaning only if value is omitted. If set, returns
        a list of the possible values for the type, or None if this is not
        possible. If not set, returns a text description of the type format.
        @type enum: bool
        @param reverse: If set, translates an internal value to its UI
        string representation.
        @type reverse: bool
        @return: c.f. parameter enum description.
        @rtype: str|list|None
        @raise ValueError: If the value does not check ok againts the type.
        '''
        if reverse:
            if value is not None:
                return value
            else:
                return 'default'

        type_enum = self.con.colors + ['default']
        syntax = '|'.join(type_enum)
        if value is None:
            if enum:
                return type_enum
            else:
                return syntax
        elif not value or value == 'default':
            return None
        elif value in type_enum:
            return value
        else:
            raise ValueError("Syntax error, '%s' is not %s" \
                             % (value, syntax))

    def ui_type_colordefault(self, value=None, enum=False, reverse=False):
        '''
        UI parameter type helper for default color parameter type.
        @param value: Value to check against the type.
        @type value: anything
        @param enum: Has a meaning only if value is omitted. If set, returns
        a list of the possible values for the type, or None if this is not
        possible. If not set, returns a text description of the type format.
        @type enum: bool
        @param reverse: If set, translates an internal value to its UI
        string representation.
        @type reverse: bool
        @return: c.f. parameter enum description.
        @rtype: str|list|None
        @raise ValueError: If the value does not check ok againts the type.
        '''
        if reverse:
            if value is not None:
                return value
            else:
                return 'none'

        type_enum = self.con.colors + ['none']
        syntax = '|'.join(type_enum)
        if value is None:
            if enum:
                return type_enum
            else:
                return syntax
        elif not value or value == 'none':
            return None
        elif value in type_enum:
            return value
        else:
            raise ValueError("Syntax error, '%s' is not %s" \
                             % (value, syntax))


    # User interface get/set methods

    def ui_setgroup_global(self, parameter, value):
        '''
        This is the backend method for setting parameters in configuration
        group 'global'. It simply uses the Prefs() backend to store the global
        preferences for the shell. Some of these group parameters are shared
        using the same Prefs() object by the Log() and Console() classes, so
        this backend should not be changed without taking this into
        consideration.

        The parameters getting to us have already been type-checked and casted
        by the type-check methods registered in the config group via the ui set
        command, and their existence in the group has also been checked. Thus
        our job is minimal here. Also, it means that overhead when called with
        generated arguments (as opposed to user-supplied) gets minimal
        overhead, and allows setting new parameters without error.

        @param parameter: The parameter to set.
        @type parameter: str
        @param value: The value
        @type value: arbitrary
        '''
        self.prefs[parameter] = value

    def ui_getgroup_global(self, parameter):
        '''
        This is the backend method for getting configuration parameters out of
        the B{global} configuration group. It gets the values from the Prefs()
        backend. Eventual casting to str for UI display is handled by the ui
        get command, for symmetry with the pendant ui_setgroup method.
        Existence of the parameter in the group should have already been
        checked by the ui get command, so we go blindly about this. This might
        allow internal client code to get a None value if the parameter does
        not exist, as supported by Prefs().

        @param parameter: The parameter to get the value of.
        @type parameter: str
        @return: The parameter's value
        @rtype: arbitrary
        '''
        return self.prefs[parameter]

    def ui_eval_param(self, ui_value, type_helper, default):
        '''
        Evaluates a user-provided parameter value using a given type helper.
        If the parameter value is None, the default will be returned. If the
        ui_value does not check out with the type helper, and execution error
        will be raised.

        @param ui_value: The user provided parameter value.
        @type ui_value: str
        @param type_helper: The ui_type_XXX helper method to be used
        @type type_helper: method
        @param default: The default value to return.
        @type default: any
        @return: The evaluated parameter value.
        @rtype: depends on type_helper
        @raise ExecutionError: If evaluation fails.
        '''
        if ui_value is None:
            return default
        else:
            try:
                value = type_helper(ui_value)
            except ValueError, msg:
                raise ExecutionError(msg)
            else:
                return value

    # User interface commands

    def ui_command_set(self, group=None, **parameter):
        '''
        Sets one or more configuration parameters in the given group.
        The B{global} group contains all global CLI preferences.
        Other groups are specific to the current path.

        Run with no parameter nor group to list all available groups, or
        with just a group name to list all available parameters within that
        group.

        Example: B{set global color_mode=true loglevel_console=info}

        SEE ALSO
        ========
        get
        '''
        if group is None:
            self.con.epy_write('''
                               AVAILABLE CONFIGURATION GROUPS
                               ==============================
                               %s
                               ''' % ' '.join(self._configuration_groups))
        elif not parameter:
            if group in self._configuration_groups:
                section = "%s PARAMETERS" % group.upper()
                underline1 = ''.ljust(len(section), '=')
                parameters = ''
                for parameter, param_def \
                        in self._configuration_groups[group].iteritems():
                    (type_helper, description) = param_def
                    parameter += '=I{' + type_helper() + '}'
                    underline2 = ''.ljust(len(parameter), '-')
                    parameters += '%s\n%s\n%s\n\n' \
                            % (parameter, underline2, description)

                self.con.epy_write('''%s\n%s\n%s\n''' \
                                   % (section, underline1, parameters))
            else:
                self.log.error("Unknown configuration group: %s" % group)
        elif group in self._configuration_groups:
            for param, value in parameter.iteritems():
                if param in self._configuration_groups[group]:
                    type_helper = self._configuration_groups[group][param][0]
                    try:
                        value = type_helper(value)
                    except ValueError, msg:
                        self.log.error("Not setting %s! %s" % (param, msg))
                    else:
                        group_setter = self.get_group_setter(group)
                        group_setter(param, value)
                        group_getter = self.get_group_getter(group)
                        value = group_getter(param)
                        value = type_helper(value, reverse=True)
                        self.con.display("Parameter %s has been set to '%s'." \
                                     % (param, value))
                else:
                    self.log.error(
                        "There is no parameter named '%s' in group '%s'." \
                        % (param, group))
        else:
            self.log.error("Unknown configuration group: %s" % group)

    def ui_complete_set(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command set.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        completions = []

        self.log.debug("Called with parameters=%s, text='%s', current='%s'" \
                      % (str(parameters), text, current_param))

        if current_param == 'group':
            completions = [group for group in self._configuration_groups
                           if group.startswith(text)]
        elif 'group' in parameters:
            group = parameters['group']
            if group in self._configuration_groups:
                group_params = self._configuration_groups[group]
                if current_param in group_params:
                    type_method = group_params[current_param][0]
                    type_enum = type_method(enum=True)
                    if type_enum is not None:
                        type_enum = [item for item in type_enum
                                     if item.startswith(text)]
                        completions.extend(type_enum)
                else:
                    group_params = ([param + '=' for param in group_params
                                     if param.startswith(text)
                                     if param not in parameters
                                    ])
                    if group_params:
                        completions.extend(group_params)

        if len(completions) == 1 and not completions[0].endswith('='):
            completions = [completions[0] + ' ']

        self.log.debug("Returning completions %s." % str(completions))
        return completions

    def ui_command_get(self, group=None, *parameter):
        '''
        Gets the value of one or more configuration parameters in the given
        group.

        Run with no parameter nor group to list all available groups, or
        with just a group name to list all available parameters within that
        group.

        Example: B{get global color_mode loglevel_console}

        SEE ALSO
        ========
        set
        '''
        if group is None:
            self.con.epy_write('''
                               AVAILABLE CONFIGURATION GROUPS
                               ==============================
                               %s
                               ''' % ' '.join(self._configuration_groups))
        elif not parameter:
            if group in self._configuration_groups:
                section = "%s PARAMETERS" % group.upper()
                underline1 = ''.ljust(len(section), '=')
                parameters = ''
                params = self._configuration_groups[group].items()
                params.sort()
                for parameter, param_def in params:
                    description = param_def[1]
                    group_getter = self.get_group_getter(group)
                    value = group_getter(parameter)
                    group_params = self._configuration_groups[group]
                    type_method = group_params[parameter][0]
                    value = type_method(value, reverse=True)
                    parameter = parameter + '=' + value
                    underline2 = ''.ljust(len(parameter), '-')
                    parameters += '%s\n%s\n%s\n\n' \
                            % (parameter, underline2, description)

                self.con.epy_write('''%s\n%s\n%s\n''' \
                                   % (section, underline1, parameters))
            else:
                self.log.error("Unknown configuration group: %s" % group)
        elif group in self._configuration_groups:
            for param in parameter:
                if param in self._configuration_groups[group]:
                    self.log.debug("About to get the parameter's value.")
                    group_getter = self.get_group_getter(group)
                    value = group_getter(param)
                    group_params = self._configuration_groups[group]
                    type_method = group_params[param][0]
                    value = type_method(value, reverse=True)
                    self.con.display("%s=%s" % (param, value))
                else:
                    self.log.error(
                        "There is no parameter named '%s' in group '%s'." \
                        % (param, group))
        else:
            self.log.error("Unknown configuration group: %s" % group)

    def ui_complete_get(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command get.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        completions = []

        self.log.debug("Called with parameters=%s, text='%s', current='%s'" \
                      % (str(parameters), text, current_param))

        if current_param == 'group':
            completions = [group for group in self._configuration_groups
                           if group.startswith(text)]
        elif 'group' in parameters:
            group = parameters['group']
            if group in self._configuration_groups:
                group_params = self._configuration_groups[group]
                group_params = ([param for param in group_params
                                 if param.startswith(text)
                                 if param not in parameters
                                ])
                if group_params:
                    completions.extend(group_params)

        if len(completions) == 1 and not completions[0].endswith('='):
            completions = [completions[0] + ' ']

        self.log.debug("Returning completions %s." % str(completions))
        return completions

    def ui_command_ls(self, path=None, depth=None):
        '''
        Display either the nodes tree relative to path or to the current node.

        PARAMETERS
        ==========

        I{path}
        -------
        The I{path} to display the nodes tree of. Can be an absolute path, a
        relative path or a bookmark.

        I{depth}
        --------
        The I{depth} parameter limits the maximum depth of the tree to display.
        If set to 0, then the complete tree will be displayed (the default).

        SEE ALSO
        ========
        cd bookmarks
        '''
        try:
            target = self.get_node(path)
        except ValueError, msg:
            self.log.error(msg)
            return

        if depth is None:
            depth = self.prefs['tree_max_depth']
        try:
            depth = int(depth)
        except ValueError:
            self.log.error('The tree depth must be a number.')
        else:
            if depth == 0:
                depth = None
            tree = self._render_tree(target, depth=depth)
            self.con.display(tree)

    def _render_tree(self, root, margin=None, depth=None, do_list=False):
        '''
        Renders an ascii representation of a tree of ConfigNodes.
        @param root: The root node of the tree
        @type root: ConfigNode
        @param margin: Format of the left margin to use for children.
        True results in a pipe, and False results in no pipe.
        Used for recursion only.
        @type margin: list
        @param depth: The maximum depth of nodes to display, None means
        infinite.
        @type depth: None or int
        @param do_list: Return two lists, one with each line text
        representation, the other with the corresponding paths.
        @type do_list: bool
        @return: An ascii tree representation or (lines, paths).
        @rtype: str
        '''
        lines = []
        paths = []

        node_length = 2
        node_shift = 2
        level = root.path.rstrip('/').count('/')
        if margin is None:
            margin = [0]
            root_call = True
        else:
            root_call = False

        if do_list:
            color = None
        elif not level % 3:
            color = None
        elif not (level - 1) % 3:
            color = 'blue'
        else:
            color = 'magenta'

        if do_list:
            styles = None
        elif root_call:
            styles = ['bold', 'underline']
        else:
            styles = ['bold']

        if do_list:
            name = root.name
        else:
            name = self.con.render_text(root.name, color, styles=styles)
        name_len = len(root.name)

        (description, is_healthy) = root.summary()
        if not description:
            if is_healthy is True:
                description = "OK"
            elif is_healthy is False:
                description = "ERROR"
            else:
                description = "..."

        description_len = len(description) + 3

        if do_list:
            summary = '['
        else:
            summary = self.con.render_text(' [', styles=['bold'])

        if is_healthy is True:
            if do_list:
                summary += description
            else:
                summary += self.con.render_text(description, 'green')
        elif is_healthy is False:
            if do_list:
                summary += description
            else:
                summary += self.con.render_text(description, 'red',
                                                styles=['bold'])
        else:
            summary += description

        if do_list:
            summary += ']'
        else:
            summary += self.con.render_text(']', styles=['bold'])

        children = list(root.children)
        children.sort(key=lambda child: str(child))
        line = ""

        for pipe in margin[:-1]:
            if pipe:
                line = line + "|".ljust(node_shift)
            else:
                line = line + ''.ljust(node_shift)

        if self.prefs['tree_round_nodes']:
            node_char = 'o'
        else:
            node_char = '+'
        line += node_char.ljust(node_length, '-')
        line += ' '
        margin_len = len(line)

        pad = (self.con.get_width() - 1
               - description_len
               - margin_len
               - name_len) * '.'
        if not do_list:
            pad = self.con.render_text(pad, color)

        line += name
        if self.prefs['tree_status_mode']:
            line += ' %s%s' % (pad, summary)

        lines.append(line)
        paths.append(root.path)

        if root_call and not self.prefs['tree_show_root'] and not do_list:
            tree = ''
            for child in children:
                tree = tree + self._render_tree(child, [False], depth)
        else:
            tree = line + '\n'
            if depth is None or depth > 0:
                if depth is not None:
                    depth = depth - 1
                for i in range(len(children)):
                    margin.append(i<len(children)-1)
                    if do_list:
                        new_lines, new_paths = \
                                self._render_tree(children[i], margin, depth,
                                                  do_list=True)
                        lines.extend(new_lines)
                        paths.extend(new_paths)
                    else:
                        tree = tree \
                                + self._render_tree(children[i], margin, depth)
                    margin.pop()

        if root_call:
            if do_list:
                return (lines, paths)
            else:
                return tree[:-1]
        else:
            if do_list:
                return (lines, paths)
            else:
                return tree


    def ui_complete_ls(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command ls.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        if current_param == 'path':
            (basedir, slash, partial_name) = text.rpartition('/')
            basedir = basedir + slash
            target = self.get_node(basedir)
            names = [child.name for child in target.children]
            completions = []
            for name in names:
                num_matches = 0
                if name.startswith(partial_name):
                    num_matches += 1
                    if num_matches == 1:
                        completions.append("%s%s/" % (basedir, name))
                    else:
                        completions.append("%s%s" % (basedir, name))
            if len(completions) == 1:
                if not self.get_node(completions[0]).children:
                    completions[0] = completions[0].rstrip('/') + ' '

            # Bookmarks
            bookmarks = ['@' + bookmark for bookmark in self.prefs['bookmarks']
                         if ('@' + bookmark).startswith(text)]
            self.log.debug("Found bookmarks %s." % str(bookmarks))
            if bookmarks:
                completions.extend(bookmarks)

            self.log.debug("Completions are %s." % str(completions))
            return completions

        elif current_param == 'depth':
            if text:
                try:
                    int(text.strip())
                except ValueError:
                    self.log.debug("Text is not a number.")
                    return []
            return [ text + number for number
                    in [str(num) for num in range(10)]
                    if (text + number).startswith(text)]

    def ui_command_cd(self, path=None):
        '''
        Change current work path to path.

        The path is constructed just like a unix path, with B{/} as separator
        character, B{.} for the current node, B{..} for the parent node.

        Suppose the nodes tree looks like this::
           +-/
           +-a0      (1)
           | +-b0    (*)
           |  +-c0
           +-a1      (3)
             +-b0
              +-c0
               +-d0  (2)

        Suppose the current node is the one marked (*) at the beginning of all
        the following examples:
            - B{cd ..} takes you to the node marked (1)
            - B{cd .} makes you stay in (*)
            - B{cd /a1/b0/c0/d0} takes you to the node marked (2)
            - B{cd ../../a1} takes you to the node marked (3)
            - B{cd /a1} also takes you to the node marked (3)
            - B{cd /} takes you to the root node B{/}
            - B{cd /a0/b0/./c0/../../../a1/.} takes you to the node marked (3)

        You can also navigate the path history with B{<} and B{>}:
            - B{cd <} takes you back one step in the path history
            - B{cd >} takes you one step forward in the path history

        SEE ALSO
        ========
        ls cd
        '''
        self.log.debug("Changing current node to '%s'." % path)

        if self.prefs['path_history'] is None:
            self.prefs['path_history'] = [self.path]
            self.prefs['path_history_index'] = 0

        # Go back in history to the last existing path
        if path == '<':
            if self.prefs['path_history_index'] == 0:
                self.log.info("Reached begining of path history.")
                return self
            exists = False
            while not exists:
                if self.prefs['path_history_index'] > 0:
                    self.prefs['path_history_index'] = \
                            self.prefs['path_history_index'] - 1
                    index = self.prefs['path_history_index']
                    path = self.prefs['path_history'][index]
                    try:
                        target_node = self.get_node(path)
                    except ValueError:
                        pass
                    else:
                        exists = True
                else:
                    path = '/'
                    self.prefs['path_history_index'] = 0
                    self.prefs['path_history'][0] = '/'
                    exists = True
            self.log.info('Taking you back to %s.' % path)
            return self.get_node(path)

        # Go forward in history
        if path == '>':
            if self.prefs['path_history_index'] == \
               len(self.prefs['path_history']) - 1:
                self.log.info("Reached the end of path history.")
                return self
            exists = False
            while not exists:
                if self.prefs['path_history_index'] \
                   < len(self.prefs['path_history']) - 1:
                    self.prefs['path_history_index'] = \
                            self.prefs['path_history_index'] + 1
                    index = self.prefs['path_history_index']
                    path = self.prefs['path_history'][index]
                    try:
                        target_node = self.get_node(path)
                    except ValueError:
                        pass
                    else:
                        exists = True
                else:
                    path = self.path
                    self.prefs['path_history_index'] \
                            = len(self.prefs['path_history'])
                    self.prefs['path_history'].append(path)
                    exists = True
            self.log.info('Taking you back to %s.' % path)
            return self.get_node(path)

        # Use an urwid walker to select the path
        if path is None:
            lines, paths = self._render_tree(self.get_root(), do_list=True)
            start_pos = paths.index(self.path)
            selected = self._lines_walker(lines, start_pos=start_pos)
            path = paths[selected]

        # Normal path
        try:
            target_node = self.get_node(path)
        except ValueError, msg:
            self.log.error(msg)
            return None
        else:
            index = self.prefs['path_history_index']
            if target_node.path != self.prefs['path_history'][index]:
                # Truncate the hostory to retain current path as last one
                self.prefs['path_history'] = \
                        self.prefs['path_history'][:index+1]
                # Append the new path and update the index
                self.prefs['path_history'].append(target_node.path)
                self.prefs['path_history_index'] = index + 1
            self.log.debug("After cd, path history is: %s, index is %d" \
                           % (str(self.prefs['path_history']),
                              self.prefs['path_history_index']))
            return target_node

    def _lines_walker(self, lines, start_pos):
        '''
        Using the curses urwid library, displays all lines passed as argument,
        and after allowing selection of one line using up, down and enter keys,
        returns its index.
        @param lines: The lines to display and select from.
        @type lines: list of str
        @param start_pos: The index of the line to select initially.
        @type start_pos: int
        @return: the index of the selected line.
        @rtype: int
        '''
        import urwid

        class Selected(Exception):
            pass

        palette = [('header', 'white', 'black'),
                   ('reveal focus', 'black', 'yellow', 'standout')]

        content = urwid.SimpleListWalker(
            [urwid.AttrMap(w, None, 'reveal focus')
             for w in [urwid.Text(line) for line in lines]])

        listbox = urwid.ListBox(content)
        frame = urwid.Frame(listbox)

        def handle_input(input, raw):
            for key in input:
                widget, pos = content.get_focus()
                if unicode(key) == 'up':
                    if pos > 0:
                        content.set_focus(pos-1)
                elif unicode(key) == 'down':
                    content.set_focus(pos+1)
                elif unicode(key) == 'enter':
                    raise Selected(pos)

        content.set_focus(start_pos)
        loop = urwid.MainLoop(frame, palette, input_filter=handle_input)
        try:
            loop.run()
        except Selected, pos:
            return int(str(pos))

    def ui_complete_cd(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command cd.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        if current_param == 'path':
            completions = self.ui_complete_ls(parameters, text, current_param)
            completions.extend([nav for nav in ['<', '>']
                                if nav.startswith(text)])
            return completions

    def ui_command_help(self, topic=None):
        '''
        Displays the manual page for a topic, or list available topics.
        '''
        commands = self.list_commands()
        if topic is None:
            msg = self.con.dedent(self.help_intro)
            msg += self.con.dedent('''

                                   AVAILABLE COMMANDS
                                   ==================
                                   The following commands are available in the
                                   work path:

                                   ''')
            for command in commands:
                msg += "  - %s\n" % self.get_command_syntax(command)[0]
            self.con.epy_write(msg)
        elif topic in commands:
            syntax, comments, defaults = self.get_command_syntax(topic)
            msg = self.con.dedent('''
                                 SYNTAX
                                 ======
                                 %s

                                 ''' % syntax)
            for comment in comments:
                msg += comment + '\n'

            if defaults:
                msg += self.con.dedent('''
                                      DEFAULT VALUES
                                      ==============
                                      %s

                                      ''' % defaults)
            msg += self.con.dedent('''
                                  DESCRIPTION
                                  ===========
                                  ''')
            msg += self.get_command_description(topic)
            self.con.epy_write(msg)
        else:
            self.log.error("Cannot find help topic %s." % topic)

    def ui_complete_help(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command help.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        if current_param == 'topic':
            # TODO Add other types of topics
            topics = self.list_commands()
            completions = [topic for topic in topics
                           if topic.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

    def ui_command_exit(self):
        '''
        Exits the command line interface.
        '''
        return 'EXIT'

    def ui_command_bookmarks(self, action, bookmark=None):
        '''
        Manage your bookmarks.

        Note that you can also access your bookmarks with the
        B{cd} command. For instance, the following commands
        are equivalent:
            - B{cd mybookmark}
            - C{bookmarks go mybookmark}

        You can also use bookmarks anywhere where you would use
        a normal path:
            - B{@mybookmark ls} would perform the B{ls} command
            in the bookmarked path.
            - B{ls @mybookmark} would show you the objects tree from
            the bookmarked path.


        PARAMETERS
        ==========

        I{action}
        ---------
        The I{action} is one of:
            - B{add} adds the current path to your bookmarks.
            - B{del} deletes a bookmark.
            - B{go} takes you to a bookmarked path.
            - B{show} shows you all your bookmarks.

        I{bookmark}
        -----------
        This is the name of the bookmark.

        SEE ALSO
        ========
        ls cd
        '''
        if action == 'add' and bookmark:
            if bookmark in self.prefs['bookmarks']:
                self.log.error("Bookmark %s already exists." % bookmark)
            else:
                self.prefs['bookmarks'][bookmark] = self.path
                # No way Prefs is going to account for that :-(
                self.prefs.save()
                self.log.info("Bookmarked %s as %s." % (self.path, bookmark))
        elif action == 'del' and bookmark:
            if bookmark in self.prefs['bookmarks']:
                del self.prefs['bookmarks'][bookmark]
                # No way Prefs is going to account for that deletion
                self.prefs.save()
                self.log.info("Deleted bookmark %s." % bookmark)
            else:
                self.log.error("No such bookmark %s." % bookmark)
        elif action == 'go' and bookmark:
            if bookmark in self.prefs['bookmarks']:
                return self.ui_command_cd(self.prefs['bookmarks'][bookmark])
            else:
                self.log.error("No such bookmark %s." % bookmark)
        elif action == 'show':
            bookmarks = self.con.dedent('''
                                        BOOKMARKS
                                        =========

                                        ''')
            if not self.prefs['bookmarks']:
                bookmarks += "No bookmarks yet.\n"
            else:
                for (bookmark, path) \
                        in self.prefs['bookmarks'].iteritems():
                    if len(bookmark) == 1:
                        bookmark += '\0'
                    underline = ''.ljust(len(bookmark), '-')
                    bookmarks += "%s\n%s\n%s\n\n" % (bookmark, underline, path)
            self.con.epy_write(bookmarks)
        else:
            self.log.error("Syntax error, see 'help bookmarks'.")

    def ui_complete_bookmarks(self, parameters, text, current_param):
        '''
        Parameter auto-completion method for user command bookmarks.
        @param parameters: Parameters on the command line.
        @type parameters: dict
        @param text: Current text of parameter being typed by the user.
        @type text: str
        @param current_param: Name of parameter to complete.
        @type current_param: str
        @return: Possible completions
        @rtype: list of str
        '''
        if current_param == 'action':
            completions = [action for action in ['add', 'del', 'go', 'show']
                           if action.startswith(text)]
        elif current_param == 'bookmark':
            if 'action' in parameters:
                if parameters['action'] not in ['show', 'add']:
                    completions = [mark for mark in self.prefs['bookmarks']
                                   if mark.startswith(text)]
        else:
            completions = []

        if len(completions) == 1:
            return [completions[0] + ' ']
        else:
            return completions

    def ui_command_pwd(self):
        '''
        Displays the current working path.

        SEE ALSO
        ========
        ls cd
        '''
        self.con.display(self.path)

    # Private methods

    def __str__(self):
        if self.is_root():
            return '/'
        else:
            return self.name

    def _get_parent(self):
        '''
        Get this node's parent.
        @return: The node's parent.
        @rtype: ConfigNode
        '''
        return self._parent

    def _set_parent(self, parent):
        '''
        Sets the node's parent. Works only if it does not already have one.
        @param parent: The parent node to assign.
        @type parent: ConfigNode
        '''
        if self.is_root():
            self._parent = parent
        else:
            raise AttributeError("Node %s already has a parent" % self._name)

    def _get_name(self):
        '''
        @return: The node's name.
        @rtype: str
        '''
        return self._name

    def _set_name(self, name):
        '''
        Sets the node's name.
        @param name: The new node name.
        @type name: str
        '''
        self._name = str(name)

    def _get_path(self):
        '''
        @returns: The absolute path for this node.
        @rtype: str
        '''
        subpath = self._path_separator + self.name
        if self.is_root():
            return self._path_separator
        elif self._parent.is_root():
            return subpath
        else:
            return self._parent.path + subpath

    def _list_children(self):
        '''
        Lists the children of this node.
        @return: The set of children nodes.
        @rtype: set of ConfigNode
        '''
        return self._children

    # Public methods

    def summary(self):
        '''
        Returns a tuple with a status/description string for this node and a
        health flag, to be displayed along the node's name in object trees,
        etc.
        @returns: (description, is_healthy)
        @rtype: (str, bool or None)
        '''
        return ('', None)

    def execute_command(self, command, pparams=[], kparams={}):
        '''
        Execute a user command on the node. This works by finding out which is
        the support command method, using ConfigNode naming convention:
        The support method's name is 'PREFIX_COMMAND', where PREFIX is defined
        by ConfigNode.ui_command_method_prefix and COMMAND is the commands's
        name as seen by the user.
        @param command: Name of the command.
        @type command: str
        @param pparams: The positional parameters to use.
        @type pparams: list
        @param kparams: The keyword=value parameters to use.
        @type kparams: dict
        @return: The support method's return value.
        See ConfigShell._execute_command() for expected return values and how
        they are interpreted by ConfigShell.
        @rtype: str or ConfigNode or None
        '''
        self.log.debug("Executing command %s " % command \
                       + "with pparams %s " % str(pparams) \
                       + "and kparams %s." % str(kparams))

        if command in self.list_commands():
            method = self.get_command_method(command)
        else:
            self.log.error("Command not found %s" % command)
            return

        try:
            result = method(*pparams, **kparams)
        except TypeError, msg:
            # TODO Find a cleaner way to do this
            msg = str(msg)
            if "takes at most" in msg \
               or "takes exactly" in msg \
               or "takes at least" in msg \
               or "unexpected keyword" in msg:
                self.log.error("Wrong parameters for %s, see 'help %s'."\
                              % (command, command))
            else:
                raise
        except ExecutionError, msg:
            self.log.error(msg)
        else:
            return result

    def list_commands(self):
        '''
        @return: The list of user commands available for this node.
        @rtype: list of str
        '''
        prefix = self.ui_command_method_prefix
        prefix_len = len(prefix)
        return tuple([name[prefix_len:] for name in dir(self)
                if name.startswith(prefix) and name != prefix
                and inspect.ismethod(getattr(self, name))])

    def get_group_getter(self, group):
        '''
        @param group: A valid configuration group
        @type group: str
        @return: The getter method for the configuration group.
        @rtype: method object
        '''
        prefix = self.ui_getgroup_method_prefix
        return getattr(self, '%s%s' % (prefix, group))

    def get_group_setter(self, group):
        '''
        @param group: A valid configuration group
        @type group: str
        @return: The setter method for the configuration group.
        @rtype: method object
        '''
        prefix = self.ui_setgroup_method_prefix
        return getattr(self, '%s%s' % (prefix, group))

    def get_command_method(self, command):
        '''
        @param command: The command to get the method for.
        @type command: str
        @return: The user command support method.
        @rtype: method
        @raise ValueError: If the command is not found.
        '''
        prefix = self.ui_command_method_prefix
        if command in self.list_commands():
            return getattr(self, '%s%s' % (prefix, command))
        else:
            self.log.debug('No command named %s in %s (%s)' \
                               % (command, self.name, self.path))
            raise ValueError('No command named "%s".' % command)

    def get_completion_method(self, command):
        '''
        @return: A user command's completion method or None.
        @rtype: method or None
        @param command: The command to get the completion method for.
        @type command: str
        '''
        prefix = self.ui_complete_method_prefix
        try:
            method = getattr(self, '%s%s' % (prefix, command))
        except AttributeError:
            return None
        else:
            return method

    def get_command_description(self, command):
        '''
        @return: An description string for a user command.
        @rtype: str
        @param command: The command to describe.
        @type command: str
        '''
        doc = self.get_command_method(command).__doc__
        if not doc:
            doc = "No description available."
        return self.con.dedent(doc)

    def get_command_syntax(self, command):
        '''
        @return: A list of formatted syntax descriptions for the command:
            - (syntax, comments, default_values)
            - syntax is the syntax definition line.
            - comments is a list of additionnal comments about the syntax.
            - default_values is a string with the default parameters values.
        @rtype: (str, [str...], str)
        @param command: The command to document.
        @type command: str
        '''
        method = self.get_command_method(command)
        parameters, args, kwargs, default = inspect.getargspec(method)
        parameters = parameters[1:]
        if default is None:
            num_defaults = 0
        else:
            num_defaults = len(default)

        if num_defaults != 0:
            required_parameters = parameters[:-num_defaults]
            optional_parameters = parameters[-num_defaults:]
        else:
            required_parameters = parameters
            optional_parameters = []

        self.log.debug("Required: %s" % str(required_parameters))
        self.log.debug("Optional: %s" % str(optional_parameters))

        syntax = "B{%s} " % command

        required_parameters_str = ''
        for param in required_parameters:
            required_parameters_str += "I{%s} " % param
        syntax += required_parameters_str

        optional_parameters_str = ''
        for param in optional_parameters:
            optional_parameters_str += "[I{%s}] " % param
        syntax += optional_parameters_str

        comments = []
        #if optional_parameters:
        #    comments.append(self.con.dedent(
        #        '''
        #        %s - These are optional parameters that can either be
        #        specified in the above order as positional parameters, or in
        #        any order at the end of the line as keyword=value parameters.
        #        ''' % optional_parameters_str[:-1]))

        if args is not None:
            syntax += "[I{%s}...] " % args
        #    comments.append(self.con.dedent(
        #        '''
        #        [I{%s}...] - This command accepts an arbitrary number of
        #        parameters before any keyword=value parameter. In order to use
        #        them, you must fill in all previous positional parameters if
        #        any. See B{DESCRIPTION} below.
        #        ''' % args))

        if kwargs is not None:
            syntax += "[I{%s=value}...] " % (kwargs)
        #    comments.append(self.con.dedent(
        #        '''
        #        This command also accepts an arbitrary number of
        #        keyword=value parameters. See B{DESCRIPTION} below.
        #        '''))

        default_values = ''
        if num_defaults > 0:
            index = 0
            for param in optional_parameters:
                if default[index] is not None:
                    default_values += "%s=%s " % (param, str(default[index]))

        return syntax, comments, default_values

    def get_command_signature(self, command):
        '''
        Get a command's signature.
        @param command: The command to get the signature of.
        @type command: str
        @return: (parameters, free_pparams, free_kparams) where parameters is a
        list of all the command's parameters and free_pparams and free_kparams
        booleans set to True is the command accepts an arbitrary number of,
        respectively, pparams and kparams.
        @rtype: ([str...], bool, bool)
        '''
        method = self.get_command_method(command)
        parameters, args, kwargs, default = inspect.getargspec(method)
        parameters = parameters[1:]
        if args is not None:
            free_pparams = args
        else:
            free_pparams = False
        if kwargs is not None:
            free_kparams = kwargs
        else:
            free_kparams = False
        self.log.debug("Signature is %s, %s, %s." \
                       % (str(parameters), \
                          str(free_pparams), \
                          str(free_kparams)))
        return parameters, free_pparams, free_kparams

    def get_root(self):
        '''
        @return: The root node of the nodes tree.
        @rtype: ConfigNode
        '''
        if self.is_root():
            return self
        else:
            return self.parent.get_root()

    name = property(_get_name,
                    _set_name,
                    doc="Gets or sets the node's name.")

    path = property(_get_path,
                   doc="Gets the node's path.")

    children = property(_list_children,
                        doc="Lists the node's children.")

    parent = property(_get_parent,
                      _set_parent,
                      doc="Gets or sets for the first time the node's parent.")

    def is_root(self):
        '''
        @return: Wether or not we are a root node.
        @rtype: bool
        '''
        if self._parent is None:
            return True
        else:
            return False

    def get_child(self, name):
        '''
        @param name: The child's name.
        @type name: str
        @return: Our child named by name.
        @rtype: ConfigNode
        @raise ValueError: If there is no child named by name.
        '''
        for child in self._children:
            if child.name == name:
                return child
        else:
            raise ValueError("No such path %s/%s" \
                             % (self.path.rstrip('/'), name))

    def get_node(self, path):
        '''
        Looks up a node by path in the nodes tree.
        @param path: The node's path.
        @type path: str
        @return: The node that has the given path.
        @rtype: ConfigNode
        @raise ValueError: If there is no node with that path.
        '''
        def adjacent_node(name):
            '''
            Returns an adjacent node or ourself.
            '''
            if name == self._path_current:
                return self
            elif name == self._path_previous:
                if self._parent is not None:
                    return self._parent
                else:
                    return self
            else:
                return self.get_child(name)


        # Cleanup the path
        if path is None or path == '':
            path = '.'

        # Is it a bookmark ?
        if path.startswith('@'):
            bookmark = path.lstrip('@').strip()
            if bookmark in self.prefs['bookmarks']:
                path = self.prefs['bookmarks'][bookmark]
            else:
                raise ValueError("No such bookmark %s" % bookmark)

        # More cleanup
        path = re.sub('%s+' % self._path_separator, self._path_separator, path)
        if len(path) > 1:
            path = path.rstrip(self._path_separator)
        self.log.debug("Looking for path '%s'" % path)


        # Absolute path - make relative and pass on to root node
        if path.startswith(self._path_separator):
            next_node = self.get_root()
            next_path = path.lstrip(self._path_separator)
            if next_path:
                return next_node.get_node(next_path)
            else:
                return next_node

        # Relative path
        if self._path_separator in path:
            next_node_name, next_path = path.split(self._path_separator, 1)
            next_node = adjacent_node(next_node_name)
            return next_node.get_node(next_path)

        # Path is just one of our children
        return adjacent_node(path)

    def add_child(self, child, name=None):
        '''
        Adds a new child to the node.
        Performs necessary checks to enforce our hierarchy conventions:
            - A node cannot be its own child
            - A new node must not already have a parent
            - Our children names must be unique
            - We must not be a child of this child
        @param child: The new child node.
        @type child: A ConfigNode object.
        @param name: If specified, the new child name, else uses the one from
        child.
        @type name: str
        @raise ValueError: if the node breaks our hierarchy conventions.
        '''
        if child == self:
            raise ValueError("A node cannot be it's own child.")

        if not child.is_root():
            raise ValueError("Child node already has a parent.")

        for grandchild in child.children:
            if grandchild == self:
                raise ValueError("Refusing to add cyclic parent link.")

        if name is not None:
            child.name = name

        if child.name in [ourchild.name for ourchild in self.children]:
            raise ValueError("Node already has a child named %s" % name)
        else:
            child.parent = self
            self._children.add(child)

    def del_child(self, child):
        '''
        Deletes a child from the node.
        @param child: The new child node.
        @type child: A ConfigNode object.
        '''
        if child in self._children:
            self._children.remove(child)
        else:
            raise ValueError("Cannot delete: no such child.")

