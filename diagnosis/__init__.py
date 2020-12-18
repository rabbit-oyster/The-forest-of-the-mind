import json
import os

_dirname = os.path.abspath(os.path.dirname(__file__))


class Diagnosis:
    with open(os.path.join(_dirname, "introduction.json"), "r", encoding="utf-8") as fp:
        Introduction = json.load(fp)
    with open(os.path.join(_dirname, "negative.json"), "r", encoding="utf-8") as fp:
        Negative = json.load(fp)
    with open(os.path.join(_dirname, "positive.json"), "r", encoding="utf-8") as fp:
        Positive = json.load(fp)
    with open(os.path.join(_dirname, "useless.json"), "r", encoding="utf-8") as fp:
        Useless = json.load(fp)