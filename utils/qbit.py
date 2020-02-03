# import re
# from pathlib import Path
#
# import qbittorrent
# import logging
#
# logger = logging.getLogger('QBitTorrent')
#
#
# def get_path(ti):
#     return ti["save_path"] + ti["name"]
#
#
# def _file_count(path: Path):
#     count = 0
#     if path.is_file():
#         return 1
#     elif path.is_dir():
#         for sub_path in path.iterdir():
#             count += _file_count(sub_path)
#         return count
#     return 0
#
#
# def file_count(ti):
#     path = Path(get_path(ti))
#     return _file_count(path)
#
#
# magnet_pattern = re.compile(r'[a-fA-F\d]{40}')
#
#
# def search_hash(*texts):
#     magnet_list = []
#     for text in texts:
#         magnet_list.extend(magnet_pattern.findall(text))
#     return set(magnet_list)
#
#
# class Client:
#
#     def __init__(self, host, user, pwd):
#         self.client = qbittorrent.Client(host)
#         self.client.login(user, pwd)
#         logger.debug("成功连接至qbittorrent管理")
#
#     @property
#     def torrents(self):
#         return self.client.torrents()
#
#     @property
#     def magnets(self):
#         return [ti['hash'] for ti in self.torrents]
#
#     def download_by_magnets(self, magnets):
#         for magnet in magnets:
#             magnet = 'magnet:?xt=urn:btih:' + magnet.lower()
#             self.client.download_from_link(magnet)
#
#     def download_from_file(self, file):
#         if isinstance(file, str):
#             with open(file, 'rb') as t:
#                 self.client.download_from_file(t)
#         elif isinstance(file, bytes):
#             self.client.download_from_file(file)
#
#     def find_by_magnets(self, magnets):
#         torrents_list = []
#         magnets = [magnet.lower() for magnet in magnets]
#         for ti in self.torrents:
#             if ti['hash'] in magnets:
#                 torrents_list.append(ti)
#         return torrents_list
#
#     def find_by_magnet(self, magnet, add=False):
#         if add:
#             self.download_by_magnets({magnet})
#         for ti in self.torrents:
#             if ti['hash'] == magnet.lower():
#                 return ti
#
#     def delete_torrent_by_magnet(self, magnet):
#         self.client.delete_permanently([magnet])
#
#     def is_downloaded(self, magnet):
#         ti = self.find_by_magnet(magnet)
#         if ti['progress'] == 1:
#             return True
#         else:
#             return False
#
#
# if __name__ == '__main__':
#     pass
