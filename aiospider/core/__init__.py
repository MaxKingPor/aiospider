import asyncio
import inspect
import logging

import aiohttp

from aiospider.exceptions import HandlerError
from aiospider.handler import MainHandler
from aiospider.http import Request


class Core:
    def __init__(self, spider, settings):
        self.spider = spider
        self.settings = settings
        self.loop = self.settings['loop']
        self.queue = asyncio.Queue()
        self.pool = self.settings['pool']
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
        def process_item_task_done(task: asyncio.Future):
            if not task.cancelled() and (exc := task.exception()):
                self.logger.exception("process_item error:", exc_info=exc)

        async def mod1():
            result = await func(resp, meta=req.meta)
            if isinstance(result, Request):
                await self.queue.put(result)
            elif result is not None:
                task = self.loop.run_in_executor(self.pool, self.spider_handler.process_item, result, req.meta)
                task.add_done_callback(process_item_task_done)
                # self.pool.submit(self.spider_handler.process_item, result, req.meta)

        async def mod2():
            async for i in func(resp, meta=req.meta):
                if isinstance(i, Request):
                    await self.queue.put(i)
                elif i is not None:
                    task = self.loop.run_in_executor(self.pool, self.spider_handler.process_item, i, req.meta)
                    task.add_done_callback(process_item_task_done)
                    # self.pool.submit(self.spider_handler.process_item, i, req.meta)

        func = req.callback
        if func is None:
            func = self.spider.parse
        if inspect.iscoroutinefunction(func):
            await mod1()
        elif inspect.isasyncgenfunction(func):
            await mod2()
        else:
            raise TypeError(f'{func} 类型暂不支持')

    async def job(self, session):
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
