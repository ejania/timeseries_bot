import random
import string

import cherrypy
import requests

import telebot

from plugins.payments import PaymentsPlugin

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
                     'Hi there, I am SeriesBot. <3 <3 <3')

  # Handle all other messages
  @bot.message_handler(func=lambda message: True, content_types=['text'])
  def echo_message(message):
    bot.send_message(message.chat.id, message.text)


if __name__ == '__main__':
  cherrypy.server.socket_host = '0.0.0.0'
  cherrypy.server.socket_port = 8443
  cherrypy.server.ssl_module = 'builtin'
  cherrypy.server.ssl_certificate = './webhook_cert.pem'
  cherrypy.server.ssl_private_key = './webhook_pkey.pem'

  PaymentsPlugin(cherrypy.engine).subscribe()
  cherrypy.quickstart(BotServer(), '/%s/' % API_TOKEN, {'/': {}})
