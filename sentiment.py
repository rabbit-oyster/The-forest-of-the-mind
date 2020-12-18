import asyncio
import collections
import os
from typing import Any, Dict, List

import pandas
from konlpy.tag import Kkma


class DataSet(dict):
    def set(self, keys: List[str], value: Any) -> None:
        dic = self
        for key in keys[:-1]:
            dic = dic.setdefault(key, DataSet())
        dic[keys[-1]] = value

        return None


def loadLexicon(path: os.PathLike) -> DataSet:
    LexiconFrame = pandas.read_csv(path)

    RealData = DataSet()
    for _, data in LexiconFrame.iterrows():
        ngrams = data.ngram.split(";")

        RealData.set(ngrams, dict(data))

    return RealData


class Lexicon:
    Polarity = loadLexicon("./lexicon/polarity.csv")


class LexiconKeys:
    Polarity = ["COMP", "NEG", "NEUT", "None", "POS"]


kkma = Kkma()


def calc(source, ret, func) -> None:
    for sourceKey in ret.keys():
        sourceData = source.get(sourceKey)

        if sourceData:
            if isinstance(sourceData, str):
                sourceData = float(sourceData)
            if isinstance(sourceData, (int, float)):
                ret[sourceKey] = func(sourceData, ret[sourceKey])


def analyze(Text: str):
    Sentences = kkma.sentences(Text)

    analyzedData = collections.defaultdict(list)

    for Sentence in Sentences:
        ngrams = list(map(lambda x: f"{x[0]}/{x[1]}", kkma.pos(Sentence)))

        LexiconObject = Lexicon.Polarity
        LexiconKeyPair = LexiconKeys.Polarity

        ret = dict(zip(LexiconKeyPair, [0.0] * len(LexiconKeyPair)))

        beforeData = currentData = None
        for ngram in ngrams:
            if not beforeData:
                currentData = LexiconObject.get(ngram)
            else:
                currentData = beforeData.get(ngram)

                if currentData:
                    calc(beforeData, ret, lambda x, y: y - x)

            if currentData:
                calc(currentData, ret, lambda x, y: x + y)

            beforeData = currentData

        for key, value in ret.items():
            analyzedData[key].append(value)

    concattedData = {
        key: sum(values) / len(values) for key, values in analyzedData.items()
    }

    if "COMP" in concattedData:
        del concattedData["COMP"]
    if "None" in concattedData:
        del concattedData["None"]

    totalValue = sum(concattedData.values())

    return {
        key: value / totalValue * 100 if totalValue != 0 else 0.0
        for key, value in concattedData.items()
    }


async def asyncAnalyze(Text: str, loop=asyncio.get_event_loop()) -> Dict[str, float]:
    return await loop.run_in_executor(None, analyze, Text)
