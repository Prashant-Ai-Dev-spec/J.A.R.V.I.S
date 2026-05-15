import time
import unittest
from backend.dispatch import manager
from backend.dispatch import persistence


class DispatchPersistenceTests(unittest.TestCase):
    def test_persistence_roundtrip(self):
        # start a short job
        rid = manager.start_task(manager.example_job, args=(0.1,))
        # wait for completion
        for _ in range(20):
            s = manager.get_status(rid)
            if s['status'] == 'done':
                break
            time.sleep(0.05)
        # load persisted tasks and check the id exists
        data = persistence.load_tasks()
        self.assertIn(rid, data)
        self.assertIn(data[rid]['status'], ('done','failed'))


if __name__ == '__main__':
    unittest.main()
