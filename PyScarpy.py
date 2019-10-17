#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

class PyScarpy(object):
    """
    爬虫类
    """
    def __init__(self, u_start):
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
            'reflex_url': ''
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
                    self._conf[_k] = _v

        if self.u_start.startswith('http') is False:
            self.u_start = "http://{}".format(self.u_start)
        urlchange = urlparse.urlsplit(self.u_start)
        self._domain = "{}://{}".format(urlchange.scheme, urlchange.netloc)


    def init_check(self):
        """
        初始化检查
        """
        _c = self._conf
        if self.url_check(self._domain) is False:
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
        elif isinstance(_c.get('reflex_url'), str) is False or len(_c.get('reflex_url')) < 5:
            print ("[SCRAPY_ERR] reflex_url={} is invalid.".format(_c.get('reflex_url')))
        else:
            return True

        return False


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


    def url_math(self, _url):
        """
        链接简单检查
        """
        for p_url in self._conf.get('p_urls', []):
            if self.url_check(_url, p_url):
                return True
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
        :param url:
        :param retry_time:
        :return:
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


    def worker(self):
        """
        工作进程
        """
        while True:
            if self.q.empty():
                time.sleep(0.5)
            self.t_lock.acquire(2)
            _url = self.q.get()
            self.t_lock.release()

            # 处理已消费数据
            _md5 = self.get_str_md5(_url)
            self._consumed.add(_md5)

            # 抓取网页
            web_content = self.http_crawl(_url)
            soup = BeautifulSoup(web_content, 'html.parser')
            a_tags = soup.find_all('a')
            for a in a_tags:
                if a.attrs.has_key('href'):
                    a_href = a['href'].lower()
                    if 'javascript' in a_href:
                        continue
                else:
                    continue

                if a_href.startswith('http') is False or self.url_check(a_href) is False:
                    if a_href.startswith('/') is False:
                        u_params = _url.split('/')
                        u_params[-1] = a_href
                        a_href = '/'.join(u_params)
                    else:
                        a_href = urlparse.urljoin(self._domain, a_href)
                # print _url, a_href
                # 非目标链接弃
                if self.url_math(a_href) is False:
                    continue
                # 已抓取过记录弃
                a_href_md5 = self.get_str_md5(a_href)
                if a_href_md5 in self._consumed:
                    continue
                self.q.put(a_href)

            # 网页处理
            if self.url_check(_url, self._conf.get('reflex_url')):
                self.func_reflex(_url, web_content, soup)
                pass
            # self.t_lock.release()


    # 对外函数 def func_reflex(web_url, web_content, html_parse_obj)
    def func_reflex(self, web_url, web_content, html_parse_obj=None):
        """
        处理目标页面数据
        """
        pass


    def run(self):
        """
        触发入口
        """
        if self.url_check(self.u_start) is False:
            print ("[SCRAPY_ERR] url={} is invalid.".format(self.u_start))
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
                if check_cnt >= 1500:
                    break
            else:
                check_cnt = 0

            time.sleep(0.01)

        print ("[SCRAPY_MSG] url={} crawl size={}.".format(self.u_start, len(self._consumed)))
        print ("[SCRAPY_MSG] crawl End.")
