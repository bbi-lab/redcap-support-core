from rss.rqueue.worker import WorkerSettings as RedisQueueSettings


# Expose the worker settings to arq Worker initialization
global WorkerSettings
WorkerSettings = RedisQueueSettings
