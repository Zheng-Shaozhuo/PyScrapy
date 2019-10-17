# PyScrapy
使用手册

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
