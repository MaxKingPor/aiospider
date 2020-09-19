import logging
import typing
from aiospider.spider import Spider
from aiospider.settings import Settings
from aiospider.http.request import Request
from aiohttp import ClientResponse


class SpiderHandler:
    def __init__(self, spider:Spider, settings:Settings):
        self.spider:Spider = None
        self.settings:Settings = None
        self.logger:logging.Logger = None
    async def process_request(self, request:Request)->typing.Union[None, Request]:...
    async def process_response(self, response:ClientResponse, meta:typing.Any)->typing.Union[None, ClientResponse]:...
    def process_item(self, item:typing.Any, meta:typing.Any)->typing.Any:...

class MainHandler(SpiderHandler):
    def __init__(self, spider, settings):
        super().__init__(spider, settings)
        self.handlers:typing.List[SpiderHandler] = []

    def _init_handlers(self):...