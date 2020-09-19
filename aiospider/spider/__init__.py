import abc
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from yarl import URL

from aiospider.core import Core
from aiospider.http import Request
from aiospider.settings import Settings, default_settings


class Spider(metaclass=abc.ABCMeta):
    name: str = 'Spider'
    start_urls = []
    settings: dict = {}

    @property
    def logger(self):
        logger = logging.getLogger(f'{self.name}.Spider')
        return logger

    async def start_requests(self):
        for i in self.start_urls:
            yield Request(url=URL(i), callback=self.parse)

    @abc.abstractmethod
    def parse(self, response, meta):
        ...

    def parse_item(self, item, meta):
        ...

    @classmethod
    def start(cls, settings=None):
        if not isinstance(settings, Settings):
            settings = Settings(settings, 10)
            settings.setmodule(default_settings)
        settings.update(cls.settings, 20)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if "pool" not in settings:
            pool = ThreadPoolExecutor()
            settings.set("pool", pool, -1)
        settings.set('loop', loop, -1)

        cor = Core(cls.from_settings(settings), settings)
        return loop.run_until_complete(cor.start())

    @classmethod
    def from_settings(cls, _):
        return cls()
