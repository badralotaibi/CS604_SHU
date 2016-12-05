class Account(object):
    def __init__(self, name, account_number, initial_amount):
        self._name = name
        self._no = account_number
        self._balance = initial_amount

    def deposit(self, amount):
        self._balance += amount

    def withdraw(self, amount):
        self._balance -= amount

    def get_balance(self):
        return self._balance

    def dump(self):
        s = '%s, %s, balance: %s'% \
        (self._name, self._no, self._balance)
        print (s)

a1 = Account('badr alotaibi', '19371554951', 20000)
a1.deposit(10)
a1.withdraw(5)
a1.withdraw(6)
a1.dump()
print (a1._balance)
print (a1.get_balance())
print (a1.dump())
