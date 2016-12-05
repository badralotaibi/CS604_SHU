import unittest

class MyTest(unittest.TestCase):
    def test_deposite(self):
        self.assertEqual(deposite(3), 33)

    def test_withdraw(self):
        self.assertEqual(withdraw(3), 33)

    def test_get_balance(self):
        self.assertEqual(get_balance(3), 33)

    def test_dump(self):
        self.assertEqual(dump(3), 33)

unittest.main()
