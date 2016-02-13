import cherrypy
import telebot

from plugins.payments import PaymentsPlugin, Sessions

API_TOKEN = open('./api_token.txt').read().splitlines()[0]
API_URL_PREFIX = 'https://api.telegram.org/bot'
API_URL = API_URL_PREFIX + API_TOKEN

bot = telebot.TeleBot(API_TOKEN)


class BotServer(object):
  @cherrypy.expose
  @cherrypy.tools.json_in()
  def index(self):
    json = cherrypy.request.json
    update = telebot.types.Update.de_json(json)
    bot.process_new_messages([update.message])

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

    session_key = get_session_key(
        message.from_user.id, message.chat.id)
    session_is_open = cherrypy.engine.publish(
        'session-is-open', session_key)[0]
    if (session_is_open):
      open_session_message = (
          'Looks like you forgot to finish your previous session!')
      # TODO: Print out session info.
      bot.send_message(message.chat.id, open_session_message)
      return
    cherrypy.engine.publish('add-users-to-session', session_key,
        [message.from_user])

    payments = {message.from_user.id: amount}
    cherrypy.engine.publish('add-payments', payments)

    balance = cherrypy.engine.publish('get-user', message.from_user.id)[0]
    bot.send_message(message.chat.id,
        ('Thank you for your payment of %.2f, generous friend! '
         'Your total balance is %.2f now.' % (amount, balance)))

  # Handle '/done'
  @bot.message_handler(commands=['done'])
  def close_session(message):
    session_key = get_session_key(
        message.from_user.id, message.chat.id)
    session_is_open = cherrypy.engine.publish(
        'session-is-open', session_key)[0]
    if session_is_open:
      cherrypy.engine.publish('close-session', session_key)
      bot.send_message(message.chat.id, 'Got it. Duly noted.')
    else:
      bot.send_message(message.chat.id, 'Nothing to close here, move along.')

  # Handle '/listusers'
  @bot.message_handler(commands=['listusers'])
  def list_users(message):
    session_key = get_session_key(
        message.from_user.id, message.chat.id)
    users = cherrypy.engine.publish('get-users-in-session', session_key)[0]
    users = [user.username for user in users]
    bot.send_message(message.chat.id, 'Current users: %s' % users)

  # Handle '/balance'
  @bot.message_handler(commands=['balance'])
  def get_user_balance(message):
    balance = cherrypy.engine.publish('get-user', message.from_user.id)[0]
    bot.send_message(message.chat.id,
        'Your current balance is %.2f.' % balance)

  # Handle new users
  @bot.message_handler(content_types=['new_chat_participant'])
  def add_new_user(message):
    new_user = message.new_chat_participant
    cherrypy.engine.publish('add-payments', {new_user.id: 0})
    bot.send_message(message.chat.id,
        ('Welcome, %s! Sharing is caring.' % new_user.first_name))

  # Handle all other messages
  @bot.message_handler(func=lambda message: True, content_types=['text'])
  def echo_message(message):
    bot.send_message(message.chat.id, message.text)

def get_session_key(user, group):
  return '%s:%s' % (user, group)

if __name__ == '__main__':
  cherrypy.server.socket_host = '0.0.0.0'
  cherrypy.server.socket_port = 8443
  cherrypy.server.ssl_module = 'builtin'
  cherrypy.server.ssl_certificate = './webhook_cert.pem'
  cherrypy.server.ssl_private_key = './webhook_pkey.pem'

  # TODO: Find a nicer way to handle lists returned from cherrypy.engine.publish.
  PaymentsPlugin(cherrypy.engine).subscribe()
  Sessions(cherrypy.engine).subscribe()
  cherrypy.quickstart(BotServer(), '/%s/' % API_TOKEN, {'/': {}})
