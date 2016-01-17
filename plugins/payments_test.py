import unittest
from payments import Payments

class TestPayments(unittest.TestCase):
  def setUp(self):
    self.payments = Payments()

  def test_add_payments(self):
    self.payments.add_payments({'u1': 1.0, 'u2': -1.0})
    self.assertAlmostEqual(1.0, self.payments.get_user('u1'))
    self.assertAlmostEqual(-1.0, self.payments.get_user('u2'))
    users = self.payments.get_all_users()
    self.assertEqual(2, len(users))

if __name__ == '__main__':
  unittest.main()
