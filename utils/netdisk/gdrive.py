import json
import requests


class GDrive:
    def __init__(self, remote, proxy):
        self.remote = remote
        self.proxy = proxy
        self.session = requests.Session()
        self.session.proxies = proxy

    def get_by_full_path(self, path):
        titles = path.split('/')
        root = 'root'
        if 'team_drive' in self.remote:
            root = self.remote['team_drive']
        if 'root_folder_id' in self.remote:
            root = self.remote['root_folder_id']
        return self.get_by_full_path_on_net(titles, root)

    @property
    def headers(self):
        token = json.loads(self.remote['token'])
        return {"Authorization": "{} {}".format(token['token_type'], token['access_token'])}

    def _net_handler(self, q):
        params = q
        if 'team_drive' in self.remote:
            params.update({"supportsTeamDrives": True,
                           "supportsAllDrives": True,
                           "corpora": "drive",
                           "includeItemsFromAllDrives": True,
                           "includeTeamDriveItems": True,
                           "driveId": self.remote['team_drive']})

        res = self.session.get("https://www.googleapis.com/drive/v3/files",
                               params=params,
                               headers=self.headers)
        res.raise_for_status()
        res_dict = res.json()
        if not res_dict['files']:
            raise FileNotFoundError(f"查询语句{q['q']}没有找到任何结果")
        file = res_dict['files'][0]
        return file

    def get_by_full_path_on_net(self, titles, id_):
        count = len(titles) - 1
        for i, name in enumerate(titles):
            if i != count:
                q = {
                    'q': f"'{id_}' in parents and name = '{name}' and mimeType = 'application/vnd.google-apps.folder'"}
            else:
                q = {'q': f"'{id_}' in parents and name = '{name}'"}
            file = self._net_handler(q)
            id_ = file['id']
        return id_
