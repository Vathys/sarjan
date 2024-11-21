from fs.base import FS


def recurse_remove_empty(fs: FS, dir: str):
    if fs.isempty(dir):
        fs.removedir(dir)
        recurse_remove_empty(fs, fs.path.dirname(dir))