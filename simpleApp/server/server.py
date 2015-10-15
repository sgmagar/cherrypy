import cherrypy
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage

import redis
import json
import os

PATH = os.path.abspath(os.path.dirname(__file__))
PATH = PATH[:-6] + "client"
rediss = redis.StrictRedis(host="localhost", port="6379", db=0)
in_user_no=0

class TestWebSocketHandler(WebSocket):
	def opened(self):
		ack = "you are connected"
		cherrypy.engine.publish('websocket-broadcast', ack)
	def received_message(self, m):
		global rediss
		global in_user_no
		cherrypy.log("Recv: %s" %m.data)
		#cherrypy.engine.publish('websocket-broadcast', m)
		data = json.loads(m.data)
		command = data["cmd"]
		username = data["msg"]["username"]
		password = data["msg"]["password"]
		#jsonSend = {"username":username, "password":password}
		#sendData = json.dumps(jsonSend)
		if command=="login":
			for sr_user_no in range(rediss.dbsize()):
				user="user"+str(sr_user_no)
				cherrypy.log(user)
				if rediss.hget(user,"username")==username and rediss.hget(user,"password")==password:
					jsonSend = {"cmd":"login_success","username":username, "password":password}
					sendData = json.dumps(jsonSend)
					break
				else:
					jsonSend = {"cmd":"login_unsuccess","username":username, "password":password}
					sendData = json.dumps(jsonSend)

		elif command=="signup":
			user = "user"+str(in_user_no)
			for i in range(rediss.dbsize()):
				user = "user"+str(in_user_no)
				if rediss.hexists(user,"username"):
					in_user_no +=1
				else:
					break
			rediss.hmset(user,data["msg"])
			user_values=rediss.hvals(user)
			user_vals=""
			for i in range(len(user_values)):
				user_vals +=" " + user_values[i]
			cherrypy.log(user_vals)
			jsonSend = {"cmd":"signup_success","username":username, "password":password}
			sendData = json.dumps(jsonSend)
		rediss.bgsave()

		cherrypy.engine.publish('websocket-broadcast', sendData)

	def closed(self, code, reason="A client left the room"):
		cherrypy.engine.publish('websocket-broadcast', TextMessage(reason))

''' Cherrypy Websocket Server and Web server Handlers '''
class WS(object):
	@cherrypy.expose
	def ws(self):
		handler=cherrypy.request.ws_handler

class Static(object):
	@cherrypy.expose
	def index(self):
		return "it works!"


wsConfig = {
	'/ws': {
				'tools.websocket.on': True,
				'tools.websocket.handler_cls': TestWebSocketHandler,
				'tools.log_headers.on': False,
				'tools.log_tracebacks.on': False
	}
}

staticConfig = {
	'/' : 	{
				'tools.staticdir.on': True,
				'tools.staticdir.dir': PATH,
				'tools.staticdir.index': 'index.html',
				'tools.log_headers.on': False,
				'tools.log_tracebacks.on':False
	}

}

#Mounting static files directories
cherrypy.tree.mount(Static(),"/",staticConfig)

#Mounting the WebSocket Class with reqd conf
cherrypy.tree.mount(WS(),"/sock",wsConfig)
WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()
cherrypy.config.update({	'server.socket_host': "127.0.0.1",
							'server.socket_port':9000})

#Starting cherrypy server
cherrypy.engine.start()
cherrypy.engine.block()