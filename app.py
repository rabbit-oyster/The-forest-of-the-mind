#섹스
import random
from sanic import Sanic, response
from sanic_session import Session, InMemorySessionInterface
import socketio
from diagnosis import Diagnosis
import json
from sentiment import asyncAnalyze
import copy
import collections

app = Sanic(__name__)
session = Session(app, interface=InMemorySessionInterface())
sio = socketio.AsyncServer(async_mode='sanic', cors_allowed_origins=[])
sio.attach(app)

sessionSidStorage = {}

with open("./badwords.json", "r", encoding="utf-8") as fp:
    badwordsFilter = json.load(fp)

@app.middleware("response")
async def allowCors(_, response):
    response.headers["Access-Control-Allow-Origin"] = "*"

def getQuestion(session):
    Sections = [(session["Diagnosis"].Negative, "Negative"), (session["Diagnosis"].Positive, "Positive"), (session["Diagnosis"].Useless, "Useless")]
    while True:
        Sections = list(filter(lambda x: bool(x[0]), Sections))

        if not Sections:
            break

        Section, SectionName = random.choice(Sections)
        random.shuffle(Section)
        
        if not Section:
            continue

        session["current"] = (Section.pop(), SectionName)
        return True
    
    return False

@sio.on("connect", namespace="/chatBot")
async def connect(sid, environ):
    await sio.emit("botMessage", {"content": f"""{random.choice(Diagnosis.Introduction)}

마음의 숲은 문맥속에 담긴 감정으로 우울증을 진단하는 서비스입니다.

정확한 분석을 위해서 예/아니오와 같은 단답보다는 글로 답변해주세요."""}, to=sid, namespace="/chatBot")

    async with sio.session(sid, namespace="/chatBot") as session:
        if not session.get("Diagnosis"):
            session["Diagnosis"] = copy.copy(Diagnosis)
        
        if not session.get("Results"):
            session["Results"] = collections.defaultdict(list)
        
        getQuestion(session)

        await sio.emit("botMessage", {"content": session["current"][0] }, to=sid, namespace="/chatBot")



@sio.on("clientMessage", namespace="/chatBot")
async def clientMessage(sid, data):
    async with sio.session(sid, namespace="/chatBot") as session:
        if any(filter(lambda x: x in data['content'].lower(), badwordsFilter)):
            return await sio.emit("messageDenied", {"content": data["content"]}, to=sid, namespace="/chatBot")

        await sio.emit("messageAccepted", {'content': data['content'], 'isDelivered': True}, to=sid, namespace="/chatBot")

        Sentiment = await asyncAnalyze(data['content'], app.loop)
        
        session["Results"][session["current"][1]].append(Sentiment)
        
        NewQuestion = getQuestion(session)

        if NewQuestion:
            return await sio.emit("botMessage", {"content": session["current"][0] }, to=sid, namespace="/chatBot")
        
        print(session["Results"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, auto_reload=True)