import time
import unittest
from backend.dispatch import manager
from backend.dispatch import sql_queue


class DispatchSQLiteTests(unittest.TestCase):
    def test_sql_enqueue_and_run(self):
        # Start a short job that uses the registered example_job
        rid = manager.start_task(manager.example_job, args=(0.1,))
        self.assertIsInstance(rid, str)
        # poll until done
        done = False
        for _ in range(50):
            s = manager.get_status(rid)
            if s['status'] == 'done':
                done = True
                break
            time.sleep(0.05)
        self.assertTrue(done, 'SQL-backed task should complete')
        # Check the SQL store contains the task id and status
        data = sql_queue.list_tasks()
        self.assertIn(rid, data)
        self.assertIn(data[rid]['status'], ('done', 'failed'))


if __name__ == '__main__':
    unittest.main()
