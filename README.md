> 基于asyncio+aiohttp 开发的类scrapy爬虫架构 
>
>
# 基本使用
``` python
from lxml import etree
from aiospider import Spider


class MySpider(Spider):
    start_urls = [
        'https://home.firefoxchina.cn/',
    ]

    def parse_item(self, item, meta):
        self.logger.debug(f'item:{item}, meta:{meta}')

    async def parse(self, response, meta):
        root = etree.HTML(await response.text())
        ls = root.xpath("//a/@href")
        for i in ls:
            yield {'url': i}

MySpider.start({'LOG_LEVEL': 'DEBUG'})
```

> myspider 是用aiospider写的一个小项目
