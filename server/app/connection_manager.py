# connection_manager.py
import asyncio
import json
from typing import Set


class ConnectionManager:
    def __init__(self):
        self._queues: Set[asyncio.Queue] = set()

    async def connect(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.add(queue)
        return queue

    def disconnect(self, queue: asyncio.Queue):
        self._queues.discard(queue)

    async def broadcast(self, event: dict):
        payload = json.dumps(event)
        for queue in list(self._queues):
            await queue.put(payload)


manager = ConnectionManager()