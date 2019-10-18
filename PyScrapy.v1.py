#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import json
import Queue
import urllib2
import hashlib
import urlparse
import threading

# pip install beautifulsoup4
from bs4 import BeautifulSoup

reload(sys)
sys.setdefaultencoding('utf-8')

class Utils(object):
    """
    工具类
    """
    def url_check(self, _url, _pattern=None):
        """
        链接简单检查
        """
        if _pattern is None:
            _pattern=r'^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+$'
        m = re.search(_pattern, _url.decode("utf-8"))
        if m is not None:
            return True
        else:
            return False


    def get_str_md5(self, _str):
        """
        获取数据md5值
        """
        key = None
        if _str is not None:
            m2 = hashlib.md5()
            m2.update(_str)
            key = m2.hexdigest()
        return key


    def http_crawl(self, _url, retry_time=3, _timeout=1):
        """
        根据url，抓取detail实际数据
        """
        http_headers = {"Content-type": "application/json",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) Chrome/70.0.3538.102 Safari/537.36'}
        try:
            req = urllib2.Request(url=_url, headers=http_headers)
            resp = urllib2.urlopen(req, timeout=_timeout)
            if resp.code == 200:
                return resp.read()
            else:
                return None
        except Exception as e:
            print ("[HTTP_EXP] url={}, msg={}".format(_url, e))

            if retry_time > 0:
                time.sleep(1)
                return self.http_crawl(_url, retry_time - 1, _timeout)
            else:
                return None


    def save_file(self, file_content, file_path):
        """
        根据链接下载文件
        """
        file_dir = os.path.dirname(file_path)
        # 目录检测
        if os.path.exists(file_dir) is False:
            os.makedirs(file_dir)
        # 文件写入
        if file_content is None:
            return
        with open(file_path, 'wb') as code:
            code.write(file_content)


    def get_wash_str(self, _str):
        """
        清洗符号
        """
        return re.sub(r"[\s+\.\!\/_,$%^*()+\"\':;]+|[+—！，。？、~@#￥%……&*（）《》“”：；]+", "", _str)


class PyScrapy(object):
    """
    爬虫类
    """
    def __init__(self, u_start):
        self.utils = Utils()
        # 入口链接
        self.u_start = u_start
        # 消费队列
        self.q = None
        # 多线程锁
        self.t_lock = None
        # 已消费集合
        self._consumed = set()
        # 主站
        self._domain = None
        # 配置参数
        self._conf = {
            'thread_num': 10,
            'queue_size': 10000,
            'p_urls': [],
            'is_resurs': True,
            'target_urls': [],
            'target_file_urls': [],
            'target_file': {
                '_path': os.path.join(os.getcwd(), 'images'),
                '_prefix': '',
                'gd_dir': False
            }
        }

        # 用户配置参数
        self.u_conf = {}


    def set_config(self, _conf): 
        """
        设置配置参数
        """
        if isinstance(_conf, dict):
            self.u_conf = _conf


    def init_data(self):
        """
        初始化配置参数
        """
        if isinstance(self.u_conf, dict) and len(self.u_conf) > 0:
            for _k, _v in self.u_conf.items():
                if _k in self._conf:
                    if isinstance(_v, dict) is False:
                        self._conf[_k] = _v
                    else:
                        for _vk, _vv in _v.items():
                            if _vk in self._conf[_k]:
                                self._conf[_k][_vk] = _vv

        if self.u_start.startswith('http') is False:
            self.u_start = "http://{}".format(self.u_start)
        urlchange = urlparse.urlsplit(self.u_start)
        self._domain = "{}://{}".format(urlchange.scheme, urlchange.netloc)


    def init_check(self):
        """
        初始化检查
        """
        _c = self._conf
        if self.utils.url_check(self._domain) is False:
            print ("[SCRAPY_ERR] domain={} is invalid.".format(self._domain))
        elif isinstance(_c.get('thread_num'), int) is False or \
            _c.get('thread_num') < 1 or _c.get('thread_num') > 30:
            print ("[SCRAPY_ERR] thread_num={} is invalid, range=[1:30].".format(_c.get('thread_num')))
        elif isinstance(_c.get('queue_size'), int) is False or \
            _c.get('queue_size') < 100 or _c.get('queue_size') > 50000:
            print ("[SCRAPY_ERR] queue_size={} is invalid, range=[100:50000].".format(_c.get('queue_size')))
        elif isinstance(_c.get('p_urls'), list) is False or len(_c.get('p_urls')) == 0:
            print ("[SCRAPY_ERR] p_urls={} is invalid, is list.".format(_c.get('p_urls')))
        elif isinstance(_c.get('is_resurs'), bool) is False:
            print ("[SCRAPY_ERR] is_resurs={} is invalid, is bool.".format(_c.get('is_resurs')))
        elif isinstance(_c.get('target_urls'), list) is False or isinstance(_c.get('target_file_urls'), list) is False:
            print ("[SCRAPY_ERR] target_urls or target_file_urls is invalid, is list")
        elif len(_c.get('target_urls')) == 0 and len(_c.get('target_file_urls')) == 0:
            print ("[SCRAPY_ERR] target_urls and target_file_urls is empty.")
        elif isinstance(_c.get('target_file'), dict) is False:
            print ("[SCRAPY_ERR] target_file is dict.")
        else:
            return True

        return False


    def url_math(self, _url):
        """
        链接简单检查
        """
        for p_url in self._conf.get('p_urls', []):
            if self.utils.url_check(_url, p_url):
                return True
        return False


    def _common_work(self, _url):
        """
        通用抓取逻辑
        """
        web_content = None
        soup = None
        is_target = True

        # 处理已消费数据
        _md5 = self.utils.get_str_md5(_url)
        self._consumed.add(_md5)

        # 抓取网页
        web_content = self.utils.http_crawl(_url)
        if web_content is None:
            return web_content, soup, is_target

        # 是否目标页
        for t_url in self._conf.get('target_urls'):
            if self.utils.url_check(_url, t_url):
                is_target = True
                break

        if is_target is True and self._conf.get('is_resurs') is False and _url != self.u_start:
            return web_content, soup, is_target

        soup = BeautifulSoup(web_content, 'html.parser')
        a_tags = soup.find_all('a')
        for _tag in a_tags:
            if _tag.attrs.has_key('href'):
                a_href = _tag['href'].lower()
                if 'javascript' in a_href:
                    continue
            else:
                continue

            if a_href.startswith('http') is False or self.utils.url_check(a_href) is False:
                if a_href.startswith('/') is False:
                    u_params = _url.split('/')
                    u_params[-1] = a_href
                    a_href = '/'.join(u_params)
                else:
                    a_href = urlparse.urljoin(self._domain, a_href)
            # 非目标链接弃
            if self.url_math(a_href) is False:
                continue
            # 已抓取过记录弃
            a_href_md5 = self.utils.get_str_md5(a_href)
            if a_href_md5 in self._consumed:
                continue
            self.q.put(a_href)

        return web_content, soup, is_target


    def worker_file(self):
        """
        工作进程, 抓取文件
        """
        while True:
            if self.q.empty():
                time.sleep(0.5)
                continue
            self.t_lock.acquire(2)
            _url = self.q.get()
            self.t_lock.release()

            web_content, soup, is_target = self._common_work(_url)
            if web_content is None:
                continue

            # 网页处理
            if is_target:
                self.func_reflex(_url, web_content, soup)

            self.func_file_reflex(_url, web_content, soup)


    # 对外函数 def func_file_reflex(web_url, web_content, html_parse_obj)
    def func_file_reflex(self, web_url, web_content, html_parse_obj=None):
        """
        处理目标页面数据
        """
        if html_parse_obj is None:
            html_parse_obj = BeautifulSoup(web_content, 'html.parser')

        # 文件相关配置
        t_file = self._conf.get('target_file', {})
        title_dir = ''
        if t_file.get('gd_dir', False) is True:
            title_dir = html_parse_obj.title.string
            if len(title_dir) == 0 or title_dir == '':
                title_dir = "dir_{}".format(self.utils.get_str_md5(web_url))
            title_dir = "{}".format(self.utils.get_wash_str(title_dir))
        file_dir = os.path.join(t_file.get('_path', os.path.join(os.getcwd(), 'images')), title_dir)
        file_prefix = ''
        if t_file.get('_prefix', '') != '':
            file_prefix = "{}_".format(t_file.get('_prefix'))

        # 拉取图片
        img_tags = html_parse_obj.find_all('img')
        for _tag in img_tags:
            if _tag.attrs.has_key('src') is False:
                continue
            img_src = _tag['src'].lower()
            if img_src.startswith('http') or img_src.startswith('data'):
                pass
            else:
                if img_src.startswith('/') is False:
                    u_params = web_url.split('/')
                    u_params[-1] = img_src
                    img_src = '/'.join(u_params)
                else:
                    img_src = urlparse.urljoin(self._domain, img_src)

            # 是否目标图片
            is_target = False
            for t_f_url in self._conf.get('target_file_urls'):
                if self.utils.url_check(img_src, t_f_url):
                    is_target = True
                    break
            if is_target is False:
                continue

            if img_src.startswith('http'):
                if '?' in img_src:
                    _file = img_src[:img_src.index('?')].split('/')[-1]
                _file = img_src.split('/')[-1]
            else:
                _file = "{}_{}.jpg".format(int(time.time()), self.utils.get_str_md5(img_src))

            web_content = self.utils.http_crawl(img_src)
            if web_content is None:
                return
            file_path = os.path.join(file_dir, "{}{}".format(file_prefix, _file))
            self.utils.save_file(web_content, file_path)


    def worker(self):
        """
        工作进程
        """
        while True:
            if self.q.empty():
                time.sleep(0.5)
                continue
            self.t_lock.acquire(2)
            _url = self.q.get()
            self.t_lock.release()

            web_content, soup, is_target = self._common_work(_url)
            if web_content is None:
                continue

            # 网页处理
            if is_target:
                self.func_reflex(_url, web_content, soup)


    # 对外函数 def func_reflex(web_url, web_content, html_parse_obj)
    def func_reflex(self, web_url, web_content, html_parse_obj=None):
        """
        处理目标页面数据
        """
        if html_parse_obj is None:
            html_parse_obj = BeautifulSoup(web_content, 'html.parser')
        title = self.utils.get_wash_str(html_parse_obj.title.string)
        if len(title) == 0 or title == '':
            title = self.utils.get_str_md5(web_url)
        file_path = os.path.join(os.getcwd(), 'html', "{}.html".format(title))
        # 保存至文件
        self.utils.save_file(web_content, file_path)


    def run(self):
        """
        触发入口
        """
        if self.utils.url_check(self.u_start) is False:
            print ("[SCRAPY_ERR] url='{}' is invalid.".format(self.u_start))
            return

        self.init_data()
        if self.init_check() is False:
            return

        self.q = Queue.Queue(maxsize=self._conf['queue_size'])
        self.q.put(self.u_start)

        # 多线程工作
        # _thread.isAlive() 进程是否存活
        work_threads = []
        self.t_lock = threading.Lock()
        for i in range(self._conf['thread_num']):
            if len(self._conf.get('target_file_urls')) > 0:
                t_thread = threading.Thread(target=self.worker_file)
            else:
                t_thread = threading.Thread(target=self.worker)
            t_thread.setDaemon(True)
            t_thread.start()
            work_threads.append(t_thread)
            time.sleep(0.01)

        # 主进程检查, 若连续15s队列为空, 即标识为抓取结束
        check_cnt = 0
        while True:
            if self.q.qsize() == 0:
                check_cnt += 1
                if check_cnt >= 1350:
                    break
            else:
                check_cnt = 0
            time.sleep(0.01)

        print ("[SCRAPY_MSG] url='{}' crawl size={}.".format(self.u_start, len(self._consumed)))
        print ("[SCRAPY_MSG] crawl End.")
