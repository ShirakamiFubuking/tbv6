import shutil
import subprocess
from pathlib import Path
from threading import Thread
from config import logger, const
from utils import db, compress, netdisk
from . import bddisk


def save_exc(func):
    def wrapper(cmd, *args, **kwargs):
        try:
            func(cmd, *args, **kwargs)
        except subprocess.CalledProcessError as e:
            with UploadDB('main.db') as d:
                d.exc_handler(cmd, e.returncode, e.stdout, e.stderr)
        except FileNotFoundError:
            with UploadDB("main.db") as d:
                d.exc_handler(cmd, 0, '系统没有找到指定的文件'.encode('utf-8'))

    return wrapper


class UploadDB(db.Handler):
    def exc_handler(self, cmd, return_code, stdout=b'', stderr=b''):
        self.cursor.execute('insert into SubprocessExc (cmd,ReturnCode,stdout,stderr) values (?,?,?,?)',
                            (str(cmd), return_code, stdout, stderr))

    def search_uploaded(self, magnet):
        self.cursor.execute('select * from MagnetNetspace where magnet=?', (magnet,))
        return self.cursor.fetchall()

    def save_uploaded(self, magnet, space_name, path):
        self.cursor.execute('insert into MagnetNetspace (magnet, remote, path) VALUES (?,?,?)',
                            (magnet, space_name, path))


@save_exc
def unrar(path, result_dict):
    path = Path(path)
    if path.suffix in ('.rar', '.7z', '.zip') and path.is_file() and path.stat().st_size < 1610612736:
        result_dict['unrar'] = compress.uncompress(path, f'./pre_up/{path.stem}_uncompress', mkdir=True)


@save_exc
def bd_rar(torrent, result_dict):
    source_path = torrent["save_path"] + torrent["name"]
    name = torrent['hash'].upper()
    size = torrent['size']
    result_dict['rar'] = list(compress.rar(f'pre_up/{name}/{name}.rar', source_path, '-ep1', mkdir=True,
                                           rr=5, pwd='⑨', level=0, size=size, volume=1610612736, crypt_filename=True))


class Upload(netdisk.Rclone):
    def __init__(self, local_path, rclone='rclone'):
        super().__init__(rclone, const.RCLONE_CONFIG, const.PROXY)
        self.local_path = local_path
        self.result_dict = {}
        self.tasks = []
        self._attr_dict = {}

    def set(self, key, value):
        self._attr_dict[key] = value

    def __getattr__(self, item):
        return self._attr_dict.get(item)

    def general_upload(self, local_path, field, remote_path):
        try:
            super().general_upload(local_path, field, remote_path)
        except subprocess.CalledProcessError as e:
            with UploadDB('main.db') as d:
                d.exc_handler(e.cmd, e.returncode, e.stdout, e.stderr)
        else:
            if self.magnet:
                with UploadDB('main.db') as d:
                    d.save_uploaded(self.magnet, field, remote_path)

    def up2od(self, local_path, remote_path):
        return Thread(target=self.general_upload, args=(local_path, 'od', remote_path,))

    def up2gd(self, local_path, remote_path):
        return Thread(target=self.general_upload, args=(local_path, 'gdedu', remote_path,))

    @staticmethod
    def up2bd(local_path, remote_path):
        """
        注意,由于是百度网盘所以流程和普通的网盘并不一样,其上传加密压缩包,
        同时不以真实文件名命名,而以神社补档链接中的数字命名文件夹,以磁力链接hash命名`文件.rar`
        :param local_path:
        :param remote_path:
        :return:
        """
        return Thread(target=bddisk.jinjia_upload, args=(local_path, remote_path))

    def rar(self, torrent):
        return Thread(target=bd_rar, args=(torrent, self.result_dict))

    def unrar(self, source_path):
        return Thread(target=unrar, args=(source_path, self.result_dict))

    def all_in_one(self, torrent, remote_path, rar_remote_path, unrar_remote_path, bd_name):
        od_t = self.up2od(self.local_path, remote_path)
        gd_t = self.up2gd(self.local_path, remote_path)
        # rar_t = self.rar(ti)
        # unrar_t = self.unrar(ti['save_path'] + ti['name'])

        od_t.start()
        gd_t.start()
        # rar_t.start()
        # unrar_t.start()
        od_t.join()
        gd_t.join()
        # rar_t.join()
        # unrar_t.join()

        rar_result = self.result_dict.get('rar')

        if rar_result:
            for file in rar_result:
                # bd_t = self.up2bd(file, bd_name)
                oda_t = self.up2od(file, rar_remote_path)
                gda_t = self.up2gd(file, rar_remote_path)
                oda_t.start()
                gda_t.start()

        unrar_result = self.result_dict.get('unrar')
        if unrar_result:
            odu_t = self.up2od(unrar_result, unrar_remote_path)
            gdu_t = self.up2gd(unrar_result, unrar_remote_path)
            odu_t.start()
            gdu_t.start()

        if rar_result:
            oda_t.join()
            gda_t.join()
            shutil.rmtree(rar_result[0].parent)
            logger.info(f"删除了压缩文件{rar_result}")
        if unrar_result:
            odu_t.join()
            gdu_t.join()
            shutil.rmtree(unrar_result)
            logger.info(f"删除了解压缩的文件{unrar_result}")
