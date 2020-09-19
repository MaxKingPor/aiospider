import asyncio
import logging
import aiohttp
from concurrent.futures import Executor
from aiospider.handler import MainHandler
from aiospider.http import Request
from aiospider.settings import Settings
from aiospider.spider import Spider

class Core:
    def __init__(self, spider:Spider, settings: Settings):
        self.loop:asyncio.AbstractEventLoop = None
        self.logger:logging.Logger = None
        self.pool:Executor = None
        self.spider_handler:MainHandler = None
        self.spider:Spider = None
        self.settings:Settings = None
        self.queue:asyncio.Queue = None
        ...
    def _init_logger(self):...
    async def start_parse(self, req:Request, resp:aiohttp.ClientResponse):...
    async def job(self, session: aiohttp.ClientSession):...
    async def _start_task(self, count:int, session:aiohttp.ClientSession)->int:...
    async def start(self)->int:...