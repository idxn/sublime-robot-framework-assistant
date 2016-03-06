from robot import parsing
from robot.variables.filesetter import VariableFileSetter
from robot.variables.store import VariableStore
from robot.variables.variables import Variables
from robot.libdocpkg.robotbuilder import LibraryDocBuilder
from robot.output import LOGGER as ROBOT_LOGGER
from robot.utils.importer import DataError
from os import path
import xml.etree.ElementTree as ET
from tempfile import mkdtemp
import logging
from parser_utils.util import normalise_path
from db_json_settings import DBJsonSetting

logging.basicConfig(
    format='%(levelname)s:%(asctime)s: %(message)s',
    level=logging.DEBUG)


def strip_and_lower(text):
    return text.lower().replace(' ', '_')


class DataParser():
    """ This class is used to parse different tables in test data.

    Class will return the the test data as in json format. Can parse
    Python libraries, library xml documentation generated by the libdoc
    resource and test suite files.
    """
    # Public
    def __init__(self):
        self.file_path = None
        self.rf_variables = Variables()
        self.rf_var_storage = VariableStore(self.rf_variables)
        self.libdoc = LibraryDocBuilder()

    def parse_resource(self, file_path):
        self.file_path = file_path
        if path.exists(file_path):
            model = parsing.ResourceFile(file_path).populate()
            return self._parse_robot_data(file_path, model)
        else:
            raise ValueError(
                'File does not exist: {0}'.format(file_path))

    def parse_suite(self, file_path):
        self.file_path = file_path
        if path.exists(file_path):
            model = parsing.TestCaseFile(source=file_path).populate()
            return self._parse_robot_data(file_path, model)
        else:
            raise ValueError(
                'File does not exist: {0}'.format(file_path))

    def parse_variable_file(self, file_path, args=None):
        if not args:
            args = []
        data = {}
        data[DBJsonSetting.file_name] = path.basename(file_path)
        data[DBJsonSetting.file_path] = normalise_path(file_path)
        self.file_path = file_path
        setter = VariableFileSetter(self.rf_var_storage)
        var_list = []
        for variable in setter.set(file_path, args):
            var_list.append(variable[0])
        data['variables'] = sorted(var_list)
        return data

    def parse_library(self, library, args=None):
        """Parses RF library to dictionary

        Uses internally libdoc modules to parse the library.
        Possible arguments to the library are provided in the
        args parameter.
        """
        data = {}
        if not args:
            data['arguments'] = []
        else:
            arg_list = []
            for arg in args:
                arg_list.append(arg)
            data['arguments'] = arg_list
        if path.isfile(library):
            data[DBJsonSetting.file_name] = path.basename(library)
            data[DBJsonSetting.file_path] = normalise_path(library)
            data[DBJsonSetting.library_module] = path.splitext(
                data[DBJsonSetting.file_name])[0]
            if library.endswith('.xml'):
                data[DBJsonSetting.keywords] = self._parse_xml_doc(library)
            elif library.endswith('.py'):
                data[DBJsonSetting.keywords] = self._parse_python_lib(
                    library, data['arguments'])
            else:
                raise ValueError('Unknown library')
        else:
            data[DBJsonSetting.library_module] = library
            data[DBJsonSetting.keywords] = self._parse_python_lib(
                library, data['arguments'])
        if data[DBJsonSetting.keywords] is None:
            raise ValueError('Library did not contain keywords')
        else:
            return data

    def register_console_logger(self):
        ROBOT_LOGGER.register_console_logger()

    def unregister_console_logger(self):
        ROBOT_LOGGER.unregister_console_logger()

    # Private
    def _parse_python_lib(self, library, args):
        library = self._lib_arg_formatter(library, args)
        kws = {}
        try:
            library = self.libdoc.build(library)
        except DataError:
            raise ValueError(
                'Library does not exist: {0}'.format(library))
        for keyword in library.keywords:
            kw = {}
            kw['keyword_name'] = keyword.name
            kw['tags'] = list(keyword.tags._tags)
            kw['keyword_arguments'] = keyword.args
            kw['documentation'] = keyword.doc
            kws[strip_and_lower(keyword.name)] = kw
        return kws

    def _lib_arg_formatter(self, library, args):
        args = self._argument_path_formatter(library, args)
        if not args:
            return library
        else:
            for item in args:
                library = '{lib}::{item}'.format(lib=library, item=item)
            return library

    def _argument_path_formatter(self, library, args):
        """Replace robot folder with real path

        If ${/}, ${OUTPUT_DIR} or ${EXECDIR} is found from args then
        a temporary directory is created and that one is used instead."""
        arguments = []
        for arg in args:
            if '${/}' in arg or '${OUTPUT_DIR}' in arg or '${EXECDIR}' in arg:
                f = mkdtemp()
                logging.info(
                    'Possible robot path encountered in library arguments')
                logging.debug('In library %s', library)
                logging.debug('Instead of %s using: %s', arg, f)
                arguments.append(f)
            else:
                arguments.append(arg)
        return arguments

    def _parse_xml_doc(self, library):
        root = ET.parse(library).getroot()
        if ('type', 'library') in root.items():
            return self._parse_xml_lib(root)
        else:
            ValueError('XML file is not library: {}'.format(root.items()))

    def _parse_xml_lib(self, root):
        kws = {}
        for element in root.findall('kw'):
            kw = {}
            kw['keyword_name'] = element.attrib['name']
            kw['documentation'] = element.find('doc').text
            tags = []
            [tags.append(tag.text) for tag in element.findall('.//tags/tag')]
            kw['tags'] = tags
            arg = []
            [arg.append(tag.text) for tag in element.findall('.//arguments/arg')]
            kw['keyword_arguments'] = arg
            kws[strip_and_lower(kw['keyword_name'])] = kw
        return kws

    def _parse_robot_data(self, file_path, model):
        data = {}
        data[DBJsonSetting.file_name] = path.basename(file_path)
        data[DBJsonSetting.file_path] = normalise_path(file_path)
        data[DBJsonSetting.keywords] = self._get_keywords(model)
        data['variables'] = self._get_global_variables(model)
        lib, res, v_files = self._get_imports(
            model,
            path.dirname(normalise_path(file_path)),
            file_path
        )
        data['resources'] = res
        data['libraries'] = lib
        data[DBJsonSetting.variable_files] = v_files
        return data

    def _get_keywords(self, model):
        kw_data = {}
        for kw in model.keywords:
            tmp = {}
            tmp['keyword_arguments'] = kw.args.value
            tmp['documentation'] = kw.doc.value
            tmp['tags'] = kw.tags.value
            tmp['keyword_name'] = kw.name
            kw_data[strip_and_lower(kw.name)] = tmp
        return kw_data

    def _get_imports(self, model, file_dir, file_path):
        lib = []
        res = []
        var_files = []
        for setting in model.setting_table.imports:
            if setting.type == 'Library':
                lib.append(self._format_library(setting, file_dir))
            elif setting.type == 'Resource':
                res.append(self._format_resource(setting, file_path))
            elif setting.type == 'Variables':
                var_files.append(self._format_variable_file(setting))
        return lib, res, var_files

    def _format_library(self, setting, file_dir):
        data = {}
        lib_name = setting.name
        if lib_name.endswith('.py') and not path.isfile(lib_name):
            lib_path = path.abspath(path.join(file_dir, lib_name))
            lib_name = path.basename(lib_path)
        elif lib_name.endswith('.py') and path.isfile(lib_name):
            lib_path = normalise_path(lib_name)
            lib_name = path.basename(lib_name)
        else:
            lib_path = None
        data['library_name'] = lib_name
        data['library_alias'] = setting.alias
        data['library_arguments'] = setting.args
        data['library_path'] = lib_path
        return data

    def _format_resource(self, setting, file_path):
        if path.isfile(setting.name):
            return setting.name
        else:
            c_dir = path.dirname(self.file_path)
            resource_path = normalise_path(path.join(c_dir, setting.name))
            if not path.isfile(resource_path):
                print ('Import failure on file: {0},'.format(file_path),
                       'could not locate: {0}'.format(setting.name))
            return resource_path

    def _format_variable_file(self, setting):
        data = {}
        v_path = normalise_path(path.join(
            path.dirname(self.file_path), setting.name))
        args = {}
        args['variable_file_arguments'] = setting.args
        data[v_path] = args
        return data

    def _get_global_variables(self, model):
        var_data = []
        for var in model.variable_table.variables:
            if var:
                var_data.append(var.name)
        return var_data
