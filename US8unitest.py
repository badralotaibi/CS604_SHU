import unittest

class MyTest(unittest.TestCase):
    def test_create_table(self):
        self.assertEqual(deposite(3), 33)

    def test_data_entry(self):
        self.assertEqual(withdraw(3), 33)

    def test_dynamic_data_entry(self):
        self.assertEqual(get_balance(3), 33)

    def test_read_form_db(self):
        self.assertEqual(dump(3), 33)

unittest.main()
