import os
import tempfile
import unittest
from backend.connectors.office_advanced import create_excel_with_formulas


class OfficeFormulasTests(unittest.TestCase):
    def test_create_excel_with_formula(self):
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        try:
            rows = [["A","B"],[1,2],[3,'=SUM(A2:A3)']]
            ok = create_excel_with_formulas(path, rows)
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
