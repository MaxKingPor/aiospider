"""
:time 2020/09/16
"""
import typing

import aiohttp
from yarl import URL
from lxml import etree

from aiospider import Spider, Request, SpiderHandler


class MySpider(Spider):
    name = 'test'
    start_urls = [
        'https://mmp/tupian/list-%E8%87%AA%E6%8B%8D%E5%81%B7%E6%8B%8D.html',
        'https://mmp/tupian/list-%E4%BA%9A%E6%B4%B2%E8%89%B2%E5%9B%BE.html',
        'https://mmp/tupian/list-%E6%AC%A7%E7%BE%8E%E8%89%B2%E5%9B%BE.html',
        'https://mmp/tupian/list-%E7%BE%8E%E8%85%BF%E4%B8%9D%E8%A2%9C.html',
        'https://mmp/tupian/list-%E6%B8%85%E7%BA%AF%E5%94%AF%E7%BE%8E.html',
        'https://mmp/tupian/list-%E4%B9%B1%E4%BC%A6%E7%86%9F%E5%A5%B3.html',
        'https://mmp/tupian/list-%E5%8D%A1%E9%80%9A%E5%8A%A8%E6%BC%AB.html',
    ]

    async def parse(self, response: aiohttp.ClientResponse, meta: typing.Any):
        root = etree.HTML(await response.text())
        ls = root.xpath('//div[@id="tpl-img-content"]/li')
        for i in ls:
            url = i.xpath('./a[2]/@href')[0]
            name = i.xpath('./a[2]/h3/text()')[0]
            yield Request(response.url.join(URL(url)), meta={'name': name}, callback=self.parse2)
        data = root.xpath('//a[text()="下一页"]/@href')
        if data and (next_url := data[0]) != 'javascript:;':
            yield Request(response.url.join(URL(next_url)))

    async def parse2(self, response: aiohttp.ClientResponse, meta: typing.Any):
        root = etree.HTML(await response.text())
        meta['imgs'] = root.xpath('//div[@class="content"]/img/@src')
        yield meta

    def parse_item(self, item, meta):
        self.logger.info(f'name: {item["name"]}, imgs:{item["imgs"]}')


class MyHandler(SpiderHandler):
    async def process_request(self, request: Request) -> Request:
        if request.url.host != 'www.187bfeee594e.com':
            pass
            # request.url = request.url.with_host('www.187bfeee594e.com')
        return request


s = {
    'LOG_FILE': 'test.log',
    'JOB_COUNT': 1024,
    'SPIDER_HANDLERS': {
        MyHandler: 10
    }
}
MySpider.start(s)
