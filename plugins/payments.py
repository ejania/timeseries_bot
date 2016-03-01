from collections import defaultdict, namedtuple

from cherrypy.process import wspbus, plugins


class Payments(object):
  def __init__(self):
    self.groups = dict()

  def create_group(self, group_id):
    self.groups[group_id] = defaultdict(float)

  def add_payments(self, group_id, payments):
    if not group_id in self.groups:
      self.create_group(group_id)
    for (user, amount) in payments.iteritems():
      self.groups[group_id][user] += amount

  def get_user(self, group_id, user):
    return self.groups[group_id].get(user)

  def get_all_users(self, group_id):
    return self.groups[group_id].keys()


# To be expanded with more fields.
Session = namedtuple('Session', 'users')


class Sessions(plugins.SimplePlugin):
  def __init__(self, bus):
    plugins.SimplePlugin.__init__(self, bus)
    self.sessions = dict()

  def start(self):
    self.bus.log('Enabling sessions API.')
    self.bus.subscribe('add-users-to-session', self.add_users)
    self.bus.subscribe('close-session', self.close)
    self.bus.subscribe('get-users-in-session', self.get_users)
    self.bus.subscribe('session-is-open', self.is_open)

  def stop(self):
    self.bus.log('Disabling sessions API.')
    self.bus.unsubscribe('add-users-to-session', self.add_users)
    self.bus.unsubscribe('close-session', self.close)
    self.bus.unsubscribe('get-users-in-session', self.get_users)
    self.bus.unsubscribe('session-is-open', self.is_open)

  def is_open(self, session_key):
    return session_key in self.sessions

  def close(self, session_key):
    if session_key in self.sessions:
      del self.sessions[session_key]

  def add_users(self, session_key, users_to_add):
    if not session_key in self.sessions:
      self.sessions[session_key] = Session(users=set())
    self.sessions[session_key].users.update(users_to_add)

  def get_users(self, session_key):
    if session_key in self.sessions:
      return self.sessions[session_key].users
    return {}

class PaymentsPlugin(plugins.SimplePlugin):
  def __init__(self, bus):
    plugins.SimplePlugin.__init__(self, bus)
    self.payments = Payments()

  def start(self):
    self.bus.log('Enabling payments API.')
    self.bus.subscribe('add-payments', self.add_payments)
    self.bus.subscribe('get-user', self.get_user)
    self.bus.subscribe('get-all-users', self.get_all_users)

  def stop(self):
    self.bus.log('Disabling payments API.')
    self.bus.unsubscribe('get-user', self.get_user)
    self.bus.unsubscribe('add-payments', self.add_payments)
    self.bus.unsubscribe('get-all-users', self.get_all_users)

  def add_payments(self, group_id, payments):
    self.bus.log('Adding a payment between %d entities.' % len(payments))
    self.payments.add_payments(group_id, payments)
    return True

  def get_user(self, user, group_id):
    return self.payments.get_user(user, group_id)

  def get_all_users(self, group_id):
    return self.payments.get_all_users(group_id)
