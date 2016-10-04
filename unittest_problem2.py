import unittest


class TestUM(unittest.TestCase):
    def setUp(self):
        pass

    def test_problem_2(self):
        prev, cur = 0, 1
        total = 0
        while True:
            prev, cur = cur, prev + cur
            if cur >= 4000000:
                break
            if cur % 2 == 0:
                total += cur
        print(total)


if __name__ == '__main__':
    unittest.main()
