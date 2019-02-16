from os import path
import glob

def normalise_path(f_path):
    dirname = path.abspath(path.dirname(f_path))
    basename = path.basename(f_path)
    dirname = path.normpath(dirname)
    return path.join(dirname, basename)


def get_index_name(table_name):
    return 'index-{0}'.format(table_name)
