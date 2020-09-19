
import abc
import typing
import aiohttp
from yarl import URL
import logging

from aiospider.http import Request
from aiospider.settings import Settings

class Spider(metaclass=abc.ABCMeta):
    name: str
    start_urls: typing.List[typing.Union[str, URL]]
    settings: dict
    @property
    def logger(self)->logging.Logger:...
    @abc.abstractmethod
    def parse(self, response: aiohttp.ClientResponse, meta: typing.Any):...
    @classmethod
    def start(cls, settings: typing.Union[dict, str, Settings] = None):...
    def parse_item(self, item, meta):...
    @classmethod
    def from_settings(cls, settings:Settings):...
    async def start_requests(self):
        for i in self.start_urls:
            yield Request(url=URL(i), callback=self.parse)