from sanic import Sanic, response
from sanic_session import Session, InMemorySessionInterface
import socketio

app = Sanic(__name__)
session = Session(app, interface=InMemorySessionInterface())
sio = socketio.AsyncServer(async_mode='sanic')
sio.attach(app)

sessionSidStorage = {}

@app.middleware("response")
async def allowCors(_, response):
    response.headers["Access-Control-Allow-Origin"] = "*"

@sio.event
async def connect(sid, environ):
    request = environ["sanic.request"]

    for sid, _ in list(filter(lambda x: x[1] == request.ctx.session.sid, sessionSidStorage.items())):
        del sessionSidStorage[sid]

    sessionSidStorage[sid] = request.ctx.session.sid

@sio.event
async def disconnect_request(sid):
    await sio.disconnect(sid)

@sio.event
async def disconnect(sid):
    if sid in sessionSidStorage.keys():
        del sessionSidStorage[sid]

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, auto_reload=True)