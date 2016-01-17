from cherrypy.process import wspbus, plugins
from collections import defaultdict


class Payments(object):
  def __init__(self):
    self.users = defaultdict(float)

  def add_payments(self, payments):
    for (user, amount) in payments.iteritems():
      self.users[user] += amount

  def get_user(self, user):
    return self.users.get(user)

  def get_all_users(self):
    return self.users


class PaymentsPlugin(plugins.SimplePlugin):
  def __init__(self, bus):
    plugins.SimplePlugin.__init__(self, bus)
    self.payments = Payments()

  def start(self):
    self.bus.log('Enabling payments API.')
    self.bus.subscribe('add-payments', self.add_payments)
    self.bus.subscribe('get-user', self.get_user)

  def stop(self):
    self.bus.log('Disabling payments API.')
    self.bus.unsubscribe('get-user', self.get_user)
    self.bus.unsubscribe('add-payments', self.add_payments)

  def add_payments(self, payments):
    self.bus.log('Adding a payment between %d entities.' % len(payments))
    self.payments.add_payments(payments)
    return True

  def get_user(self, user):
    return self.payments.get_user(user)
