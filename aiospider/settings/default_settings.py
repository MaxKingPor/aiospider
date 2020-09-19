JOB_COUNT = 20
LOG_CONSOLE = True
LOG_ENCODING = 'utf-8'
LOG_LEVEL = 'DEBUG'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_SPIDER_HANDLERS = {
    'aiospider.handler.filter.FilterHandler': 200,
}
