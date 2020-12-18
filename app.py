from sanic import Sanic, response
from sanic_session import Session, InMemorySessionInterface
from socketio import AsyncServer as AsyncioSocketIOServer

app = Sanic(__name__)
session = Session(app, interface=InMemorySessionInterface())
socketio = AsyncioSocketIOServer(async_mode='sanic')
socketio.attach(app)

@app.route("/")
async def index(request):
    ...

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, auto_reload=True)