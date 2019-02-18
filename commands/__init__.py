import subprocess
from .command_logging import LogCommands
from .index_open_tab import IndexOpenTabCommand
from .jump_to_keyword import JumpToKeyword
from .on_save_create_table import OnSaveCreateTable
from .open_log_file import OpenLogFile
from .query_completions import RobotCompletion
from .scan import ScanCommand
from .scan_and_index import ScanIndexCommand
from .scan_index_open_tab import ScanAndIndexOpenTab
from .scan_open_tab import ScanOpenTabCommand
from .setting_import_helper import InsertImport
from .setting_import_helper import SettingImporter
from .show_documentation import ShowKeywordDocumentation
from sublime import error_message

__all__ = [
    'IndexOpenTabCommand',
    'InsertImport',
    'JumpToKeyword',
    'LogCommands',
    'OnSaveCreateTable',
    'OpenLogFile',
    'RobotCompletion',
    'ScanAndIndexOpenTab',
    'ScanCommand',
    'ScanIndexCommand',
    'ScanOpenTabCommand',
    'SettingImporter',
    'ShowKeywordDocumentation'
]

def check_binary_version(python_binary):
    result = subprocess.check_output([python_binary,"-c", "import sys;print(sys.version_info.major)"])
    version = int(result.decode('utf-8').strip())
    if version < 3:
       error_message('RobotFrameworkAssistant\n' +
        '***********************************\n' +
        'Plugin fully support on python 3\n')