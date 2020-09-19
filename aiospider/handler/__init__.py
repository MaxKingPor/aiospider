
import logging
import importlib

from aiospider.http import Request
from aiospider.exceptions import HandlerFilterError


class SpiderHandler:
    def __init__(self, spider, settings):
        self.spider = spider
        self.settings = settings
        self.logger = logging.getLogger(f'{spider.name}.{self.__class__.__name__}')

    async def process_request(self, request):
        return request

    async def process_response(self, response, meta):
        return response

    def process_item(self, item, meta):
        return item


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

    async def process_request(self, request):
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

    def process_item(self, item, meta):
        for i in self.handlers:
            item = i.process_item(item, meta)
            if item is None:
                return
        self.spider.parse_item(item, meta)
