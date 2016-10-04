import unittest

class TestUM(unittest.TestCase):

    def test_problem_1(self):
        sum = 0
        for num in range(0, 1000):
            if (num % 3 == 0) or (num % 5 == 0):
                sum += num

        print("The sum is : ", sum)
        print("Success")


if __name__ == '__main__':
    unittest.main()
