import itertools
import cherrypy
import telebot

from tools.sqla import metadata, session
from plugins.payments import PaymentsPlugin, Sessions

import model

API_TOKEN = open('./api_token.txt').read().splitlines()[0]
API_URL_PREFIX = 'https://api.telegram.org/bot'
API_URL = API_URL_PREFIX + API_TOKEN

# Disable threading in order to make debug logging work properly.
bot = telebot.TeleBot(API_TOKEN, threaded=False)

class BotServer(object):
  @cherrypy.expose
  @cherrypy.tools.json_in()
  def index(self):
    json = cherrypy.request.json
    update = telebot.types.Update.de_json(json)
    bot.process_new_messages([update.message])

  @cherrypy.expose
  def debug(self):
    group = session.query(model.Group).get('123')
    if group is None:
      group = model.Group(id='123')
      session.add(group)
    return group.id

  # Handle '/start' and '/help'
  @bot.message_handler(commands=['help', 'start'])
  def send_welcome(message):
    bot.send_message(message.chat.id,
        'Hi there, I am SeriesBot.')

  # Handle '/pay'
  # TODO: Better order for error messaging.
  @bot.message_handler(commands=['pay'])
  def add_payments(message):
    usage_message = (
        'Please specify the payment amount after /pay, e.g. /pay 5.00')
    amount = None
    words = message.text.split()
    if not (len(words) == 2):
      bot.send_message(message.chat.id, usage_message)
      return
    try:
      amount = float(words[1])
    except ValueError:
      bot.send_message(message.chat.id, usage_message)
      return

    session_key = _GetSessionKey(message)
    session_is_open = cherrypy.engine.publish(
        'session-is-open', session_key)[0]
    if (session_is_open):
      open_session_message = (
          'Looks like you forgot to finish your previous session!')
      # TODO: Print out session info.
      bot.send_message(message.chat.id, open_session_message)
      return
    cherrypy.engine.publish('add-users-to-session', session_key,
        [message.from_user.username])

    payments = {message.from_user.username: amount}
    balance = session.query(model.Balance).filter_by(
        group=message.chat.id,
        user=message.from_user.username).one_or_none()
    if balance is None:
      balance = model.Balance(
          group=message.chat.id,
          user=message.from_user.username,
          amount=amount)
      session.add(balance)
    else:
      balance.amount += amount

    cherrypy.engine.publish(
        'add-payments', message.chat.id, payments)

    old_balance = cherrypy.engine.publish(
        'get-user', message.chat.id, message.from_user.username)[0]
    bot.send_message(message.chat.id,
        ('Thank you for your payment of %.2f, generous friend! '
         'Your total balance is %.2f now (%.2f in DB).' % (amount,
                                                           old_balance,
                                                           balance.amount)))

  # Handle '/done'
  @bot.message_handler(commands=['done'])
  def close_session(message):
    if _IsSessionOpen(message):
      # TODO: Handle splitting now.
      cherrypy.engine.publish('close-session', _GetSessionKey(message))
      bot.send_message(message.chat.id, 'Got it. Duly noted.')
    else:
      bot.send_message(message.chat.id, 'Nothing to close here, move along.')

  # Handle '/for'
  @bot.message_handler(commands=['for'])
  def for_users(message):
    if _IsSessionOpen(message):
      users = message.text.split()[1:]
      if len(users) < 1:
        bot.send_message(message.chat.id, 'Please provide some usernames')
        return
      valid, invalid = _ValidateUsers(users, message.chat.id)
      cherrypy.engine.publish(
          'add-users-to-session', _GetSessionKey(message), valid)
      bot.send_message(message.chat.id, _FormatUserLists(valid, invalid))
    else:
      # TODO: Allow different order; users first, payment second.
      bot.send_message(message.chat.id, 'Please pay first')

  # Handle '/listusers'
  @bot.message_handler(commands=['listusers'])
  def list_users(message):
    users = list(*itertools.chain(
      cherrypy.engine.publish('get-users-in-session', _GetSessionKey(message))))
    bot.send_message(message.chat.id, 'Current users: ' + _FormatUserList(users))

  # Handle '/balance'
  @bot.message_handler(commands=['balance'])
  def get_user_balance(message):
    balance = session.query(model.Balance).filter_by(
        group=message.chat.id, user=message.from_user.username).one()
    old_balance = cherrypy.engine.publish(
        'get-user', message.chat.id, message.from_user.username)[0]
    bot.send_message(message.chat.id,
        'Your current balance is %.2f (%.2f from DB).' % (old_balance, balance.amount))

  # Handle new users
  @bot.message_handler(content_types=['new_chat_participant'])
  def add_new_user(message):
    new_user = message.new_chat_participant
    balance = model.Balance(
        group=message.chat.id,
        user=new_user.username,
        amount=0)
    session.add(balance)
    cherrypy.engine.publish(
        'add-payments', message.chat.id, {new_user.username: 0})
    bot.send_message(message.chat.id,
        ('Welcome, %s! Sharing is caring.' % new_user.first_name))

  # Handle all other messages
  @bot.message_handler(func=lambda message: True, content_types=['text'])
  def echo_message(message):
    bot.send_message(message.chat.id, message.text)

def _GetSessionKey(message):
  return '%s:%s' % (message.from_user.username, message.chat.id)

def _IsSessionOpen(message):
  return cherrypy.engine.publish('session-is-open', _GetSessionKey(message))[0]

def _ValidateUsers(users, chat_id):
  assert len(users)
  #available_usernames = list(*itertools.chain(
  #  cherrypy.engine.publish('get-all-users', chat_id)))
  available_usernames = [balance.user
      for balance in session.query(model.Balance).filter(Balance.group == chat_id)]
  valid, invalid = [], []
  for user in users:
    user = user[1:]  # Delete leading '@'.
    (invalid, valid)[user in available_usernames].append(user)
  return valid, invalid

def _Dogify(usernames):
  return ['@%s' % user for user in usernames]

def _FormatUserLists(valid, invalid):
  response = []
  if valid:
    response.append('Added these guys: ' + _FormatUserList(valid))
  if invalid:
    response.append(
        'Couldn\'t find those, try again: ' +  _FormatUserList(invalid))
  return '\n'.join(response)

def _FormatUserList(users):
  return ', '.join(_Dogify(users))

if __name__ == '__main__':
  cherrypy.server.socket_host = '0.0.0.0'
  cherrypy.server.socket_port = 8443
  cherrypy.server.ssl_module = 'builtin'
  cherrypy.server.ssl_certificate = './webhook_cert.pem'
  cherrypy.server.ssl_private_key = './webhook_pkey.pem'

  PaymentsPlugin(cherrypy.engine).subscribe()
  Sessions(cherrypy.engine).subscribe()
  cherrypy.quickstart(BotServer(), '/%s/' % API_TOKEN, {'/': {
      'tools.SATransaction.on': True,
      'tools.SATransaction.dburi': model.DB_URI,
      'tools.SATransaction.echo': True,
  }})
