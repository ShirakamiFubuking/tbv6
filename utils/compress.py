from pathlib import Path
import subprocess
import psutil


class BaseCompressException(Exception):
    pass


class CompressedError(BaseCompressException):
    def __init__(self, *args, zip_file):
        super(CompressedError, self).__init__(*args)
        self.zip_file = zip_file


class NoSpaceError(BaseCompressException):
    def __init__(self, free, path):
        super(NoSpaceError, self).__init__()
        self.free = free
        self.path = path


def get_size(path: Path):
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        size = 0
        for sub_path in path.iterdir():
            size += get_size(sub_path)
        return size


def rar(target_file, source_path, *args, rr=0, pwd='', level=3, volume=0, size=0, mkdir=False, append=False,
        crypt_filename=False):
    # 初始化source path和target path
    source_path = Path(source_path)
    if not (source_path.is_file() or source_path.is_dir()):
        raise FileNotFoundError(source_path, "源目标不是文件或目录,无法进行压缩")
    # 计算预计需要文件尺寸
    size = size or get_size(source_path)
    predict_size = size * (1 + rr * 0.01)
    # 初始化目标文件对象
    target_file = Path(target_file)
    # 初始化文件名,为分卷压缩做准备
    if target_file.suffix.lower() == '.rar':
        stem = target_file.stem + '*rar'
    else:
        stem = target_file.name + '*rar'
    # 判断压缩文件是否存在,但目前无法判断分卷压缩包文件
    parent = target_file.parent  # type:Path
    if not parent.exists():
        if mkdir:
            parent.mkdir(parents=True)
        else:
            raise FileNotFoundError(parent, '目录不存在,无法创建压缩文件')
    if target_file.exists() and not append:
        raise CompressedError(target_file, "文件已经存在,无法创建压缩文件", zip_file=[target_file])
    elif volume and size > volume:
        files = list(parent.glob(stem))
        if files:
            raise CompressedError(target_file, "文件已经存在,无法创建压缩文件", zip_file=files)
    free_size = psutil.disk_usage(str(parent)).free
    if free_size < predict_size:
        raise NoSpaceError(free_size, parent)

    rar_cmd = ['rar', 'a', f'-m{level}']
    if rr:
        rar_cmd.append(f'-rr{rr}')
    if pwd:
        rar_cmd.append(f'-{"hp" if crypt_filename else "p"}{pwd}')
    if volume:
        rar_cmd.append(f'-v{volume}b')
    rar_cmd.extend(args + (str(target_file), str(source_path)))
    subprocess.run(rar_cmd, capture_output=True)

    return parent.glob(stem)


def uncompress_commands(source, target, *args, pwd=''):
    suffix = source.suffix.lower()
    if suffix == '.rar':
        return ['unrar', 'x', '-y', f'-p{pwd or "-"}', *args, str(source), str(target)]
    elif suffix == '.7z':
        return ['7za', 'x', '-y', f'-p{pwd}', *args, str(source), '-o' + str(target)]
    elif suffix == '.zip':
        pwd_list = ['-p', pwd] if pwd else []
        return ['unar', *pwd_list, *args, str(source), '-o', str(target)]


def uncompress(source, target, *args, pwd='', mkdir=False):
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError("没有这个文件")
    target = Path(target)

    if not target.is_dir():
        if target.exists():
            raise FileExistsError("目标路径是一个非文件夹")
        if mkdir:
            target.mkdir(parents=True)
        else:
            raise FileNotFoundError("没有这个路径,请尝试创建一个")
    else:
        if list(target.iterdir()):
            "警告使用者文件夹非空"
    free_size = psutil.disk_usage(str(target)).free
    if free_size < source.stat().st_size:
        raise NoSpaceError(free_size, target.parent)
    cmd = uncompress_commands(source, target, *args, pwd=pwd)
    subprocess.run(cmd, capture_output=True)
    return target


if __name__ == '__main__':
    pass
