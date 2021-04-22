import asyncio
import unittest


class FutureTests(unittest.IsolatedAsyncioTestCase):
    async def test_recursive_repr_for_pending_tasks(self):
        async def func():
            return asyncio.all_tasks()

        self.assertIn("...", repr((await asyncio.wait_for(func(), timeout=10))))
