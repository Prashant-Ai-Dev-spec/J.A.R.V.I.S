import time
import unittest
from backend.dispatch import manager


class DispatchTests(unittest.TestCase):
    def test_start_and_status(self):
        rid = manager.start_task(manager.example_job, args=(1,))
        self.assertIsInstance(rid, str)
        # poll until done
        done = False
        for _ in range(10):
            s = manager.get_status(rid)
            if s['status'] == 'done':
                done = True
                self.assertEqual(s['result'], {'slept': 1})
                break
            time.sleep(0.2)
        self.assertTrue(done, 'task should complete')


if __name__ == '__main__':
    unittest.main()
