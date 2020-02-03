from lxml import etree
import requests
import re
import time
from collections import namedtuple
from urllib import parse

post_info = namedtuple('post_info', 'title url url_path pic_url time accurate_time author category tags')
first_page = '/wp/'
other_page = '/wp/page/{}'
proxy = None
magnet_template = re.compile(r'[a-fA-F\d]{40}')

__all__ = ('Crawler', 'get_post_info')


def get_post_info(element):
    title = element.xpath('./header/h1/a/text()')[0].replace('/','・')
    url = element.xpath('./header/h1/a/@href')[0]
    url_path = parse.urlparse(url).path
    _pic_ele = element.xpath('.//img/@src')
    pic_url = _pic_ele[0] if _pic_ele else ''
    post_time = element.xpath('./header/div[@class="entry-meta"]/a/time/text()')[0]
    # 获取精确的发布时间,最终变为整数值
    _accurate_time = element.xpath('./header/div[@class="entry-meta"]/a/time/@datetime')[0]
    time_array = time.strptime(_accurate_time, "%Y-%m-%dT%H:%M:%S%z")
    timestamp = int(time.mktime(time_array))

    author = element.xpath('./header/div[@class="entry-meta"]/span[@class="by-author"]/span[2]/a/text()')[0]
    category = element.xpath('./footer/span[@class="cat-links"]/a/text()')[0]
    tags = [tag.strip() for tag in element.xpath('./footer/span[@class="tag-links"]/a/text()')]
    return post_info(title, url, url_path, pic_url, post_time, timestamp, author, category, tags)


class Crawler:
    def __init__(self, hostname='https://hacg.me'):
        self.hostname = hostname
        self.session = requests.Session()
        self.session.proxies = proxy

    def get_list(self, page=1):
        url_path = first_page if page == 1 else other_page.format(page)
        res = self.session.get(self.hostname + url_path, proxies=proxy)
        self.hostname = parse.urlparse(res.url).hostname
        res.encoding = 'utf-8'
        html = etree.HTML(res.text)
        elements = html.xpath('//article[starts-with(@id,"post") and contains('
                              '@class,"post type-post status-publish format-standard")]')
        return elements

    def get_page(self, url):
        return self.session.get(url)

    @staticmethod
    def get_magnets(text):
        return set((magnet.lower() for magnet in magnet_template.findall(text)))


if __name__ == '__main__':
    pass
