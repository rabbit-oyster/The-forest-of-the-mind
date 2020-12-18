from typing import Any, Dict, Tuple
import pandas
import math

OpenDataSet = {
    "전국건강증진센터표준데이터": pandas.read_csv("./opendata/전국건강증진센터표준데이터.csv"),
    "정신건강관련전체기관정보": pandas.read_csv("./opendata/정신건강관련전체기관정보_2019..csv"),
}


def getNearest(Pos: Tuple[int, int], type: str) -> Dict[str, Any]:
    DataSet = OpenDataSet[type]

    return sorted(
        map(lambda x: x[1], DataSet.iterrows()),
        key=lambda x: math.dist(x[["위도", "경도"]].values.tolist(), Pos),
    )[0].to_dict()
