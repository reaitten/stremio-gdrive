import os
import re
from sgd.utils.cache import Json
from sgd.utils.ptn import parse_title
from urllib.parse import urlencode


class Streams:
    def __init__(self, gdrive, stream_meta):
        self.results = []
        self.gdrive = gdrive
        self.strm_meta = stream_meta
        self.proxy_url = os.environ.get('CF_PROXY_URL')

        if self.proxy_url:
            self.get_url = self.get_proxy_url
            self.acc_token = None
        else:
            self.get_url = self.get_gapi_url
            self.acc_token = gdrive.get_acc_token()

        for item in gdrive.results:
            self.item = item
            self.parsed = parse_title(item.get('name'))
            self.construct_stream(self.acc_token)
            self.results.append(self.constructed)

        self.results.sort(key=self.best_res, reverse=True)

    @staticmethod
    def hr_size(size):
        '''https://stackoverflow.com/a/43690506'''
        for unit in ['B','KiB','MiB','GiB','TiB']:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.2f}{unit}"

    def get_name(self):
        return self.parsed.get_str(f'GDrive \n;%quality \n;%resolution')

    def get_title(self):
        file_name = self.item.get('name')
        file_size = self.hr_size(int(self.item.get('size')))
        drive_id = self.item.get('driveId')
        drive_name = self.gdrive.drive_names.contents.get(drive_id, 'MyDrive')

        str_format = '🎥;%codec 🌈;%bitDepth;bit 🔊;%audio 👤;%encoder'
        suffix = self.parsed.get_str(str_format)
        return f"{file_name}\n💾 {file_size} ☁️ {drive_name}\n{suffix}"

    def get_proxy_url(self):
        file_id = self.item.get('id')
        file_name = self.item.get('name')
        params = {'i': file_id, 'n': file_name}
        return f"{self.proxy_url}/load?{urlencode(params)}"

    def get_gapi_url(self):
        file_id = self.item.get('id')
        return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    def get_behav_hints(self):
        return {
            'notWebReady': 'true', 'proxyHeaders': {
                'request': {
                    'Authorization': f'Bearer {self.acc_token}'
                }
            }
        }

    def construct_stream(self, behav_hints):
        self.constructed = {}
        self.constructed['url'] = self.get_url()
        self.constructed['name'] = self.get_name()
        self.constructed['title'] = self.get_title()
        self.constructed['sortkeys'] = self.parsed.sortkeys
        if behav_hints:
            self.constructed['behaviorHints'] = self.get_behav_hints()
        return self.constructed

    def best_res(self, item):
        sortkeys = item.get('sortkeys')
        resolution = sortkeys.get('res')

        if resolution:
            res_map = {"UHD": "2160p", "4K": "2160p", "HD": "720p"}
            if res_map.get(resolution):
                resolution = res_map[resolution]
            resolution = int(resolution[:-1])
        else:
            resolution = 2

        if self.strm_meta.type == 'series':
            invalid_se = int(self.strm_meta.se) != sortkeys.get('se')
            invalid_ep = int(self.strm_meta.ep) != sortkeys.get('ep')
            if invalid_se or invalid_ep:
                resolution = -resolution

        del item['sortkeys']  # It's not needed anymore
        return 1 / resolution if resolution < 0 else resolution
