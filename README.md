# PyScrapy
使用手册

---  
#### PyScrapy 类配置项说明
- thread_num :int, 线程数, 默认为10
- queue_size :int, 队列容量, 默认10000
- p_urls :list, 页面url pattern集合
- is_resurs :bool, 是否递归抓取, 差异为target_urls是否抓取
- target_urls :list, 目标解析url pattern集合, setattr反射函数解析
- target_file_urls :list, 目标抓取文件url pattern集合
- target_file :dict, 文件抓取配置参数
- target_file._path :str, 文件保存路径, 默认为当前目录+images
- target_file._prefix :str, 文件名前缀, 默认为空
- target_file.gd_dir :str, 是否按网页title归档
---  

---  
#### PyScrapy.py 使用指导
1、指定起始URL, 即类初始化时传入  
2、配置正则URL pattern, set_config函数中传入, 参数dict类型  
3、指定目标URL处理函数, 暂定为 func_reflex(web_url, web_content, html_parse_obj), setattr传入  
4、执行类run函数，启动执行  

例:
```
url = 'http://jiuye.nwu.edu.cn/website/news_list.aspx?category_id=35'
obj = PyScarpy(url)
conf = {
    'p_urls': [
        r'http:\/\/jiuye.nwu.edu.cn\/website\/news_show.aspx\?id=\d+'
    ],
    'reflex_url': r'http:\/\/jiuye.nwu.edu.cn\/website\/news_show.aspx\?id=\d+'
}
def func_reflex(web_url, web_content, html_parse_obj):
    """
    目标页面解析
    """
    if html_parse_obj is None:
        html_parse_obj = BeautifulSoup(web_content, 'html.parser')
    print web_url, html_parse_obj.find('title')

obj.set_config(conf)
setattr(obj, 'func_reflex', func_reflex)
obj.run()
```
