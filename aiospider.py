import abc
import asyncio
import collections.abc
import copy
import hashlib
import importlib
import inspect
import json
import logging
import threading
import typing
from concurrent.futures import ThreadPoolExecutor

import aiohttp
from yarl import URL

default_settings = {
    'JOB_COUNT': 20,
    'LOG_CONSOLE': True,
    'LOG_ENCODING': 'utf-8',
    'LOG_LEVEL': "INFO",
    'LOG_FORMAT': '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    'LOG_DATEFORMAT': '%Y-%m-%d %H:%M:%S',
    'DEFAULT_SPIDER_HANDLERS': {
        f'{__name__}.FilterHandler': 200,
    }
}


class HandlerError(Exception):
    pass


class HandlerFilterError(HandlerError):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        super(HandlerFilterError, self).__init__(f'Filter {name!s} {value!s}')


class SpiderHandler:
    def __init__(self, spider, settings):
        self.spider = spider
        self.settings = settings
        self.logger = logging.getLogger(f'{spider.name}.{self.__class__.__name__}')

    async def process_request(self, request) -> 'Request':
        return request

    async def process_response(self, response, meta) -> aiohttp.ClientResponse:
        return response

    def process_item(self, item, meta) -> typing.Any:
        return item


class FilterHandler(SpiderHandler):
    def __init__(self, *args, **kwargs):
        super(FilterHandler, self).__init__(*args, **kwargs)
        self.filters = set()

    async def process_request(self, request: 'Request') -> typing.Union['Request', None]:
        if request.count >= 5:
            return None
        if request.filter:
            url = request.url
            if not isinstance(url, str):
                url = str(url)
            md5 = hashlib.md5(bytes(url, 'utf-8'))
            md5.update(bytes(f'{request!s}', 'utf-8'))
            hx = md5.hexdigest()
            if hx in self.filters:
                return None
            self.filters.add(hx)
        return request


class MainHandler(SpiderHandler):
    def __init__(self, spider, settings):
        super().__init__(spider, settings)
        self.handlers = []
        self._init_handlers()

    def _init_handlers(self):
        handlers = self.settings.get('DEFAULT_SPIDER_HANDLERS')
        handlers.update(self.settings.get('SPIDER_HANDLERS', {}))
        handlers = sorted(handlers.items(), key=lambda x: x[1], reverse=True)
        for k, v in handlers:
            if isinstance(k, str):
                module = k.rsplit('.', 1)
                k = importlib.import_module(module[0])
                k = getattr(k, module[1])
            if issubclass(k, SpiderHandler):
                self.handlers.append(k(self.spider, self.settings))
            elif isinstance(k, SpiderHandler):
                self.handlers.append(k)
            else:
                raise TypeError(f'{k}  不是SpiderHandler类型')

    async def process_request(self, request) -> 'Request':
        base = request
        for i in self.handlers:
            request = await i.process_request(request)
            if request is None or not isinstance(request, Request):
                self.logger.warning(f'Filter request {request}')
                raise HandlerFilterError('request', base)
        return request

    async def process_response(self, response, meta):
        base = response
        for i in self.handlers:
            response = await i.process_response(response, meta)
            if response is None:
                raise HandlerFilterError('response', base)
        return response

    def process_item(self, item, meta) -> typing.Any:
        for i in self.handlers:
            item = i.process_item(item, meta)
            if item is None:
                return
        self.spider.parse_item(item, meta)


class SettingsAttr:
    def __init__(self, value, priority):
        self.value = value
        self.priority = priority

    def set(self, value, priority):
        if 0 <= priority >= self.priority:
            self.value = value
            self.priority = priority

    def __str__(self):
        return f"<SettingsAttribute value={self.value!r} priority={self.priority}>"

    __repr__ = __str__

    def __deepcopy__(self, memodict=None):
        if self.priority < 0:
            return self
        else:
            return type(self)(copy.deepcopy(self.value), copy.deepcopy(self.priority))


class Settings(collections.abc.MutableMapping):
    def __init__(self, attrs=None, priority=0, key=lambda x: x):
        self.attrs: typing.Dict[typing.Any, SettingsAttr] = {}
        self.key = key
        self.update(attrs, priority)

    def update(self, attrs: typing.Union[str, dict], priority=0):
        if isinstance(attrs, str):
            attrs = json.loads(attrs)
        if isinstance(attrs, collections.abc.MutableMapping):
            for k, v in attrs.items():
                self.set(k, v, priority)

    def __setitem__(self, k, v) -> None:
        self.set(k, v)

    def set(self, k, v, priority=0):
        priority = self.key(priority)
        if k not in self:
            if isinstance(v, SettingsAttr):
                self.attrs[k] = v
            else:
                self.attrs[k] = SettingsAttr(v, priority)
        else:
            self.attrs[k].set(v, priority)

    def copy(self):
        return copy.deepcopy(self)

    def __contains__(self, item):
        return item in self.attrs

    def __delitem__(self, v) -> None:
        del self.attrs[v]

    def __getitem__(self, k):
        return self.attrs[k].value

    def __len__(self) -> int:
        return len(self.attrs)

    def __iter__(self):
        return iter(self.attrs)

    def __str__(self):
        return self.attrs.__str__()


class Request:
    def __init__(self, url, method='GET', callback=None, meta=None, on_filter=True, **kwargs):
        self.count = 0
        self.meta = meta
        self.url = URL(url)
        self.method = method
        self.callback = callback
        self.filter = on_filter
        self.kwargs = kwargs

    def __str__(self):
        return f'<Request url={self.url!s} method={self.method} count={self.count}>'

    __repr__ = __str__


class Spider(metaclass=abc.ABCMeta):
    name: str = 'Spider'
    start_urls: typing.List[typing.Union[str, URL]] = []
    settings: dict = {}

    @property
    def logger(self):
        logger = logging.getLogger(f'{self.name}.Spider')
        return logger

    async def start_requests(self):
        for i in self.start_urls:
            yield Request(url=URL(i), callback=self.parse)

    @abc.abstractmethod
    def parse(self, response: aiohttp.ClientResponse, meta: typing.Any):
        ...

    def parse_item(self, item, meta):
        ...

    @classmethod
    def start(cls, settings: typing.Union[dict, str, Settings] = None):
        if not isinstance(settings, Settings):
            settings = Settings(settings, 10)
            settings.update(default_settings)
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


class Core:
    def __init__(self, spider: Spider, settings: Settings):
        self.spider = spider
        self.settings = settings
        self.loop = self.settings['loop']
        self.queue = asyncio.Queue()
        self.pool: ThreadPoolExecutor = self.settings['pool']
        self._finished = asyncio.locks.Event()
        self._finished.clear()
        self.spider_handler = MainHandler(self.spider, self.settings)
        self._init_logger()
        self.logger = logging.getLogger(f'{self.spider.name}.Core')

    def _init_logger(self):
        logger = logging.getLogger(self.spider.name)
        leve = self.settings.get('LOG_LEVEL')
        logger.setLevel(leve)
        formatter = logging.Formatter(
            fmt=self.settings.get('LOG_FORMAT'),
            datefmt=self.settings.get('LOG_DATEFORMAT')
        )

        def _do_handler(hd):
            hd.setFormatter(formatter)
            hd.setLevel(leve)
            logger.addHandler(hd)

        filename = self.settings.get('LOG_FILE')
        if filename:
            encoding = self.settings.get('LOG_ENCODING')
            handler = logging.FileHandler(filename, encoding=encoding)
            _do_handler(handler)
        if self.settings.get('LOG_CONSOLE'):
            handler = logging.StreamHandler()
            _do_handler(handler)

    async def start_parse(self, req, resp):
        async def mod1():
            result = await func(resp, meta=req.meta)
            if isinstance(result, Request):
                await self.queue.put(result)
            elif result is not None:
                self.pool.submit(self.spider_handler.process_item, result, req.meta)

        async def mod2():
            async for i in func(resp, meta=req.meta):
                if isinstance(i, Request):
                    await self.queue.put(i)
                elif i is not None:
                    self.pool.submit(self.spider_handler.process_item, i, req.meta)

        func = req.callback
        if func is None:
            func = self.spider.parse
        if inspect.iscoroutinefunction(func):
            await mod1()
        elif inspect.isasyncgenfunction(func):
            await mod2()
        else:
            raise TypeError(f'{func} 类型暂不支持')

    async def job(self, session: aiohttp.ClientSession):
        req: Request

        while req := await self.queue.get():
            try:
                req = await self.spider_handler.process_request(req)
                self.logger.info(f"start {req}")
                async with session.request(req.method, req.url, **req.kwargs) as resp:
                    resp = await self.spider_handler.process_response(resp, req.meta)
                    await self.start_parse(req, resp)
            except (aiohttp.ClientError, asyncio.exceptions.TimeoutError):
                req.count += 1
                await self.queue.put(req)
            except asyncio.exceptions.CancelledError:
                raise
            except HandlerError:
                pass
            except BaseException:
                self.logger.exception('')
                raise
            else:
                self.logger.info(f'success {req}')
            finally:
                self.queue.task_done()

    async def _start_task(self, count, session):
        return_code = 0
        waiter = self.loop.create_future()
        tasks = []
        # 等待 queue.join 完成后取消所有任务task
        join_task = self.loop.create_task(self.queue.join())
        join_task.add_done_callback(lambda t: [i.cancel() for i in tasks])

        def _don_callback(t: asyncio.Task):
            """任务处理 携程回调"""
            nonlocal count, return_code
            count -= 1
            # 如果task 不是被取消的 同时还有异常就会停止所有任务
            if not t.cancelled() and t.exception() is not None:
                join_task.cancel()
                [i.cancel() for i in tasks]
                return_code = 1
            if count <= 0:
                waiter.set_result(None)
            self.logger.debug(f'shutdown {t.get_name()}')

        # 任务携程创建
        for n in range(count):
            self.logger.debug(f'start 任务_{n}')
            task: asyncio.Task = self.loop.create_task(self.job(session))
            task.set_name(f'任务_{n}')
            task.add_done_callback(_don_callback)
            tasks.append(task)
        # 等待任务完成
        await waiter
        return return_code

    async def start(self):
        # 初始化request
        async for req in self.spider.start_requests():
            assert isinstance(req, Request), 'TypeError'
            await self.queue.put(req)

        conn = aiohttp.TCPConnector(limit=0)
        async with aiohttp.ClientSession(connector=conn) as session:
            count = self.settings.get('JOB_COUNT')
            return await self._start_task(count, session)


if __name__ == "__main__":
    from lxml import etree


    class MySpider(Spider):
        start_urls = [
            'https://home.firefoxchina.cn/',
        ]

        def parse_item(self, item, meta):
            self.logger.debug(f'item:{item}, meta:{meta}')

        async def parse(self, response: aiohttp.ClientResponse, meta: typing.Any):
            root = etree.HTML(await response.text())
            ls = root.xpath("//a/@href")
            for i in ls:
                yield {'url': i}


    MySpider.start({'LOG_LEVEL': 'DEBUG'})
