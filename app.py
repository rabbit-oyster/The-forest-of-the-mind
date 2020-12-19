import asyncio
import collections
import copy
import json
import random
import secrets

import socketio
from sanic import Sanic, response
from sanic.exceptions import abort

from diagnosis import Diagnosis
from nearest import getNearest
from sentiment import asyncAnalyze

app = Sanic(__name__)
sio = socketio.AsyncServer(async_mode="sanic", cors_allowed_origins=[])
sio.attach(app)

sessionSidStorage = {}

with open("./badwords.json", "r", encoding="utf-8") as fp:
    badwordsFilter = json.load(fp)


@app.middleware("response")
async def allowCors(_, response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = [
        "GET, POST, OPTIONS, PUT, PATCH, DELETE"
    ]


@app.options("/nearest")
async def __(request):
    return response.empty()


@app.post("/nearest")
async def nearestAPI(request):
    return response.json(
        getNearest(
            tuple(map(float, request.form["Pos"].pop().split(","))),
            request.form["type"].pop(),
        )
    )


def getQuestion(session):
    if not session.get("Sections"):
        session["Sections"] = [
            (copy.deepcopy(Diagnosis.Negative), "Negative"),
            (copy.deepcopy(Diagnosis.Positive), "Positive"),
            (copy.deepcopy(Diagnosis.Useless), "Useless"),
        ]

    if not session.get("Results"):
        session["Results"] = collections.defaultdict(list)

    if not session.get("Count"):
        session["Count"] = 0

    while True:
        Sections = list(filter(lambda x: bool(x[0]), session["Sections"]))

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
async def connect(sid, _):
    await sio.emit(
        "botMessage",
        {
            "content": f"""{random.choice(Diagnosis.Introduction)}

마음의 숲은 문맥속에 담긴 감정으로 우울증을 진단하는 서비스입니다.

정확한 분석을 위해서 예/아니오와 같은 단답보다는 글로 답변해주세요.""",
            "waitForNext": False,
        },
        to=sid,
        namespace="/chatBot",
    )

    async with sio.session(sid, namespace="/chatBot") as session:
        if getQuestion(session):
            await sio.emit(
                "botMessage",
                {"content": session["current"][0], "waitForNext": True},
                to=sid,
                namespace="/chatBot",
            )


@sio.on("clientMessage", namespace="/chatBot")
async def clientMessage(sid, data):
    async with sio.session(sid, namespace="/chatBot") as session:
        if any(filter(lambda x: x in data["content"].lower(), badwordsFilter)):
            return await sio.emit(
                "messageDenied",
                {"content": data["content"]},
                to=sid,
                namespace="/chatBot",
            )

        await sio.emit(
            "messageAccepted",
            {"content": data["content"], "isDelivered": True},
            to=sid,
            namespace="/chatBot",
        )

        Sentiment = await asyncAnalyze(data["content"], app.loop)

        if session.get("current"):
            session["Count"] += 1
            session["Results"][session["current"][1]].append(Sentiment)

        NewQuestion = getQuestion(session)

        if NewQuestion:
            return await sio.emit(
                "botMessage",
                {"content": session["current"][0], "waitForNext": True},
                to=sid,
                namespace="/chatBot",
            )

        Score = 0
        TotalScore = session["Count"] * 4

        for Result in session["Results"]["Positive"]:
            Operators = {
                "POS": lambda x: 4 - x,
                "NEUT": lambda _: 2,
                "NEG": lambda x: x,
            }

            Type, Value = max(Result.items(), key=lambda x: x[1])
            Value = Operators[Type](round(Value / 25))

            Score += Value

        for Result in session["Results"]["Negative"]:
            Operators = {
                "POS": lambda x: x,
                "NEUT": lambda _: 2,
                "NEG": lambda x: 4 - x,
            }

            Type, Value = max(Result.items(), key=lambda x: x[1])
            Value = Operators[Type](round(Value / 25))

            Score += Value

        return await sio.emit(
            "returnResult",
            {"score": Score, "totalScore": TotalScore},
            to=sid,
            namespace="/chatBot",
        )


Meetings = []


@app.options("/1")
async def __(request):
    return response.empty()


@app.post("/1")
async def _(request):
    print(request.form)
    Score, TotalScore = float(request.form["Score"].pop()), float(
        request.form["TotalScore"].pop()
    )

    Percentage = round(Score / TotalScore * 100)

    if Meetings:
        if Percentage >= 60:
            abort(403, message="Score is too high.")

        Matched = sorted(
            Meetings, keys=lambda x: abs(x[0] - Percentage), reverse=True
        ).pop()

        roomId = secrets.token_hex()

        Matched[1].put_nowait(roomId)
        return response.text(roomId)

    event = asyncio.Queue(maxsize=1)

    Meetings.append([Percentage, event])

    try:
        roomId = await asyncio.wait_for(
            event.get(), timeout=float(request.form.get("timeout", ["30.0"]))
        )
    except asyncio.TimeoutError:
        abort(408, message="Matching Timed out.")
    finally:
        Meetings.remove([Percentage, event])

    return response.text(roomId)


@sio.on("setRoom", namespace="/chat")
async def setRoom(sid, data):
    async with sio.session(sid, namespace="/chat") as session:
        session["roomId"] = data["roomId"]

        sio.enter_room(sid, session["roomId"], namespace="/chat")

        await sio.emit(
            "userJoined", room=session["roomId"], skip_sid=sid, namespace="/chat"
        )


@sio.on("sendMessage", namespace="/chat")
async def sendMessage(sid, data):
    async with sio.session(sid, namespace="/chat") as session:
        roomId = session.get("roomId")

        if not roomId or any(
            filter(lambda x: x in data["content"].lower(), badwordsFilter)
        ):
            return await sio.emit(
                "messageDenied",
                {"content": data["content"]},
                to=sid,
                namespace="/chat",
            )

        await sio.emit(
            "messageAccepted",
            {"content": data["content"], "isDelivered": True},
            to=sid,
            namespace="/chat",
        )

        await sio.emit(
            "userMessage",
            {"content": data["content"]},
            room=roomId,
            skip_sid=sid,
            namespace="/chat",
        )


@sio.on("disconnect", namespace="/chat")
async def disconnectRoom(sid):
    async with sio.session(sid, namespace="/chat") as session:
        roomId = session.get("roomId")

        if not roomId:
            return

        await sio.emit("userLeft", room=roomId, skip_sid=sid, namespace="/chat")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
