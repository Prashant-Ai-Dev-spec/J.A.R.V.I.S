import unittest
from backend.plugins import registry


class PluginRegistryTests(unittest.TestCase):
    def test_load_sample_plugin(self):
        res = registry.load_plugin('backend.plugins.sample_plugin')
        self.assertTrue(res)
        import backend.plugins.sample_plugin as sp
        self.assertTrue(getattr(sp, 'initialized', False))


if __name__ == '__main__':
    unittest.main()
