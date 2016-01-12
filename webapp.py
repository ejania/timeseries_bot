import random
import string

import cherrypy
import requests

PORT = 8443
API_URL_PREFIX = 'https://api.telegram.org/bot'
API_TOKEN = None
API_URL = None

def InitializeApiToken():
  token_file = open('./api_token.txt')
  global API_TOKEN
  API_TOKEN = token_file.read().splitlines()[0]
  global API_URL
  API_URL = API_URL_PREFIX + API_TOKEN

@cherrypy.popargs('token')
class WebApp(object):
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def index(self, token):
      assert token == API_TOKEN
      json = cherrypy.request.json 

      chat_id = json['message']['chat']['id']
      text = json['message']['text']
      echo_payload = {
          'chat_id' : chat_id,
          'text': text
      } 
      print requests.get(API_URL + '/sendMessage', params=echo_payload).text


if __name__ == '__main__':
    InitializeApiToken()

    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.server.socket_port = PORT
    cherrypy.server.ssl_module = 'builtin'
    cherrypy.server.ssl_certificate = "./webhook_cert.pem"
    cherrypy.server.ssl_private_key = "./webhook_pkey.pem"

    cherrypy.quickstart(WebApp())
