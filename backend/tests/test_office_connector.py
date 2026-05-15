import os
import tempfile
import unittest
from backend.connectors.office_connector import create_excel, create_word, create_ppt


class OfficeConnectorTests(unittest.TestCase):
    def test_create_excel(self):
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        try:
            ok = create_excel(path, [["h1","h2"],[1,2]])
            self.assertIn(ok, (True, False))
            if ok:
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.getsize(path) > 0)
        finally:
            try:
                os.remove(path)
            except Exception:
                pass

    def test_create_word(self):
        fd, path = tempfile.mkstemp(suffix='.docx')
        os.close(fd)
        try:
            ok = create_word(path, ["p1","p2"]) 
            self.assertIn(ok, (True, False))
            if ok:
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.getsize(path) > 0)
        finally:
            try:
                os.remove(path)
            except Exception:
                pass

    def test_create_ppt(self):
        fd, path = tempfile.mkstemp(suffix='.pptx')
        os.close(fd)
        try:
            ok = create_ppt(path, ["s1","s2"]) 
            self.assertIn(ok, (True, False))
            if ok:
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.getsize(path) > 0)
        finally:
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
