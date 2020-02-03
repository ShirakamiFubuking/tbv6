import re
import time
import psutil
import logging
import statistics
import qbittorrent
from pathlib import Path
from threading import Lock
from collections import deque, namedtuple

logger = logging.getLogger('QBitTorrent')
tinfo = namedtuple('tinfo', 'eta speed state')


def get_path(torrent):
    return torrent["save_path"] + torrent["name"]


def _file_count(path: Path):
    count = 0
    if path.is_file():
        return 1
    elif path.is_dir():
        for sub_path in path.iterdir():
            count += _file_count(sub_path)
        return count
    return 0


def file_count(torrent):
    path = Path(get_path(torrent))
    return _file_count(path)


magnet_pattern = re.compile(r'[a-fA-F\d]{40}')


def search_hash(*texts):
    magnet_list = []
    for text in texts:
        magnet_list.extend(magnet_pattern.findall(text))
    return set(magnet_list)


class TorrentDownloadInfo:
    error_states = ('error', 'missingFiles')
    over_states = ('uploading', 'pausedUP', 'queuedUP', 'stalledUP', 'checkingUP', 'forcedUP')
    downloading_states = ('downloading', 'checkingDL')
    stalled_download_states = ('stalledDL', 'metaDL')

    def __init__(self, torrent):
        self.len_limit = 10
        self.speed_threshold = 4096  # Bytes/s
        self.eta_threshold = 86400  # second
        self.adjust_threshold = 60  # second
        self.max_download_time = 86400  # second
        self.max_adjust_times = 5
        self.magnet = torrent['hash']
        self.eta_list = deque()
        self.speed_list = deque()
        self._last_refresh_time = time.time()
        self._add(torrent['eta'], torrent['dlspeed'])
        self._ss_time = {}  # states_sustain_time
        self.adjust_times = 0
        self.torrent = torrent

    def _add(self, eta, speed):
        if len(self.eta_list) == self.len_limit:
            self.eta_list.popleft()
        self.eta_list.append(eta)
        if len(self.speed_list) == self.len_limit:
            self.speed_list.popleft()
        self.speed_list.append(speed)

    def _calc_time(self):
        state = self.torrent['state']
        refresh_time = time.time()
        sustain_time = refresh_time - self._last_refresh_time
        self._last_refresh_time = refresh_time
        self._ss_time[state] = self._ss_time.get(state, 0.0) + sustain_time

    def refresh(self, torrent):
        self.torrent = torrent
        self._add(torrent['eta'], torrent['dlspeed'])
        self._calc_time()

    def get_states_time(self, *states):
        total_time = 0.0
        for state in states:
            total_time += self._ss_time.get(state, 0.0)
        return total_time

    @property
    def over(self):
        return self.torrent['progress'] == 1

    @property
    def overtime(self):
        if self.downloading_well():
            return False
        if self.max_download_time < self.get_states_time(*self.stalled_download_states):
            return True
        return False

    @property
    def info(self):
        return tinfo(self.eta_list[-1], self.speed_list[-1], self.torrent['state'])

    @property
    def avg_info(self):
        return tinfo(statistics.mean(self.eta_list),
                     statistics.mean(self.speed_list),
                     self.torrent['state'])

    def __getitem__(self, item):
        return self.torrent[item]

    def downloading_well(self):
        if 0 <= self.info.speed < self.speed_threshold:
            return False
        if self.info.eta > self.eta_threshold:
            return False
        if not self.available():
            return False
        return True

    def available(self):
        if 0 <= self.torrent['availability'] < 1:
            return False
        return True


refresh_lock = Lock()


class AutoDownloadManager:

    def __init__(self, client):
        self.client = client  # type:qbittorrent.Client

        self.torrents = {}
        self.stop_action = 'pause'

    def refresh(self):
        with refresh_lock:
            for torrent in self.client.torrents():
                magnet = torrent['hash']  # type:str
                if magnet in self.torrents:
                    ti = self.torrents[magnet]  # type:TorrentDownloadInfo
                    ti.refresh(torrent)
                else:
                    ti = TorrentDownloadInfo(torrent)  # type:TorrentDownloadInfo
                    self.torrents[magnet] = ti

    def adjust(self):
        stop_list = []
        force_dl_list = []
        retire_force_dl_list = []
        decrease_priority_list = []
        pause_list = []
        for ti in self.torrents.values():  # type:TorrentDownloadInfo
            if ti.torrent['state'] in ti.error_states:
                stop_list.append(ti.magnet)
                continue
            if ti.torrent['size'] > self.max_size(ti.torrent['save_path']):
                stop_list.append(ti.magnet)
                continue
            adjust_temp = int(ti.get_states_time('metaDL', 'stalledDL') // ti.eta_threshold)
            if ti.torrent['state'] in ('metaDL', 'stalledDL'):
                if ti.adjust_times < adjust_temp < ti.max_adjust_times:
                    decrease_priority_list.append(ti.magnet)
                    ti.adjust_times += 1
                elif adjust_temp == ti.max_adjust_times:
                    force_dl_list.append(ti.magnet)
                    ti.adjust_times += 1
            if not ti.available() and ti["added_on"] - time.time() > 180:
                decrease_priority_list.append(ti.magnet)
            if ti.downloading_well():
                retire_force_dl_list.append(ti.magnet)
            if (not self.available(ti.torrent)) and ti['state'] not in ('queuedDL', 'downloading'):
                # force_dl_list.append(ti.magnet)
                pass
            if ti.over:
                pause_list.append(ti.magnet)
        if decrease_priority_list:
            print('decrease priority',   decrease_priority_list)
            self.client.decrease_priority(decrease_priority_list)
        if force_dl_list:
            # self.client.force_start(force_dl_list, True)
            # print('Force DL on', force_dl_list)
            # self.client.set_min_priority(force_dl_list)
            pass
        if retire_force_dl_list:
            # self.client.force_start(retire_force_dl_list, False)
            # print("Force DL off", retire_force_dl_list)
            pass
            # self.client.set_max_priority(retire_force_dl_list)
        if stop_list:
            if self.stop_action == 'pause':
                self.client.pause_multiple(stop_list)
            elif self.stop_action == 'delete':
                self.client.delete_permanently(stop_list)
        if pause_list:
            self.client.pause_multiple(pause_list)

    def downloading_well(self, ti: TorrentDownloadInfo):
        if 0 <= ti.avg_info.speed < ti.speed_threshold:
            return False
        if ti.avg_info.eta > ti.eta_threshold:
            return False
        if not self.available(ti.torrent):
            return False
        return True

    @staticmethod
    def max_size(path):
        return psutil.disk_usage(path).free

    @staticmethod
    def available(torrent):
        if 0 <= torrent['availability'] < 1:
            return False
        return True


if __name__ == '__main__':
    pass
