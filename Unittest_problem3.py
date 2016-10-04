import unittest


class TestUM(unittest.TestCase):
    def setUp(self):
        pass

    def test_problem_3(self):
        num = 600851475143
        factor = 2
        while factor * factor <= num:
            while num % factor == 0:
                num /= factor
            factor += 1
        if (num > 1):
            print (num)


if __name__ == '__main__':
    unittest.main()
