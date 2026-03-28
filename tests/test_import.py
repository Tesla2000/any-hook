from unittest import TestCase


class TestImport(TestCase):
    @staticmethod
    def test_import():
        import any_hook  # ignore

        _ = any_hook
