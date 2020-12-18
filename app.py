import random
from sanic import Sanic, response
from sanic_session import Session, InMemorySessionInterface
import socketio
from diagnosis import Diagnosis

app = Sanic(__name__)
session = Session(app, interface=InMemorySessionInterface())
sio = socketio.AsyncServer(async_mode='sanic', cors_allowed_origins=[])
sio.attach(app)

sessionSidStorage = {}

@app.middleware("response")
async def allowCors(_, response):
    response.headers["Access-Control-Allow-Origin"] = "*"

@sio.event
async def connect(sid, environ):
    await sio.emit("botMessage", {"content": random.choice(Diagnosis.Introduction)})

@sio.event
async def clientMessage(sid, data):
    await sio.emit("messageAccepted", {'content': data['content'], 'isDelivered': True}, to=sid)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, auto_reload=True)