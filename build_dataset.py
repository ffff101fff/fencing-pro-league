# build_dataset.py
# 원본 CSV들을 분석에 쓰는 통합 데이터셋으로 만든다.
# 실행: python build_dataset.py   (collect_wiki.py, load_gtrends.py 실행 후)
#
# 결과물 (data/processed/)
#   interest.csv : 종목 관심도 (위키 일별 + 구글 트렌드 월별, long 형식)
#       date, source, region, sport, group, value, value_type, value_norm
#   athletes.csv : 스타 선수 위키 일별 관심도
#       date, region, athlete, name, sport, group, views, value_norm
#   events.csv   : 이벤트 달력 (올림픽, 아시안게임, UFC TUF 첫 방송)

import os

import pandas as pd

import config


def load_total():
    return pd.read_csv(os.path.join(config.RAW_DIR, "wiki_total.csv"), parse_dates=["date"])


def fill_days(df, key):
    """조회수가 0인 날은 API 응답에서 빠지므로, 각 문서의 첫 날부터 마지막 날까지 0으로 채운다"""
    filled = []
    for (lang, k), g in df.groupby(["lang", key]):
        days = pd.date_range(g["date"].min(), config.END_DATE, freq="D")
        g = g.set_index("date").reindex(days)
        g.index.name = "date"
        g["views"] = g["views"].fillna(0)
        g["lang"], g[key] = lang, k
        g["article"] = g["article"].ffill().bfill()
        filled.append(g.reset_index())
    return pd.concat(filled, ignore_index=True)


def normalize(df, total):
    """실질 관심도 = 위키피디아 전체 조회 100만 건당 이 문서의 조회 수"""
    df = df.merge(total, on=["date", "lang"], how="left")
    df["value_norm"] = df["views"] / df["total_views"] * 1_000_000
    return df


def build_interest(total):
    wiki = pd.read_csv(os.path.join(config.RAW_DIR, "wiki_pageviews.csv"), parse_dates=["date"])
    wiki = normalize(fill_days(wiki, "sport"), total)
    wiki = pd.DataFrame({"date": wiki["date"], "source": "wikipedia", "region": wiki["lang"],
                         "sport": wiki["sport"], "value": wiki["views"],
                         "value_type": "page_views", "value_norm": wiki["value_norm"]})

    gt = pd.read_csv(os.path.join(config.RAW_DIR, "gtrends.csv"), parse_dates=["date"])
    gt = pd.DataFrame({"date": gt["date"], "source": "google_trends", "region": gt["region"],
                       "sport": gt["sport"], "value": gt["index"],
                       "value_type": "relative_index",   # 이미 전체 검색량 대비 상대값
                       "value_norm": gt["index"]})

    data = pd.concat([wiki, gt], ignore_index=True)
    data["group"] = data["sport"].map(config.SPORT_GROUP)
    cols = ["date", "source", "region", "sport", "group", "value", "value_type", "value_norm"]
    return data.sort_values(["source", "region", "sport", "date"])[cols]


def build_athletes(total):
    ath = pd.read_csv(os.path.join(config.RAW_DIR, "wiki_athletes.csv"), parse_dates=["date"])
    ath = normalize(fill_days(ath, "athlete"), total)
    ath["name"] = ath["athlete"].map(lambda k: config.ATHLETES[k][0])
    ath["sport"] = ath["athlete"].map(lambda k: config.ATHLETES[k][1])
    ath["group"] = ath["sport"].map(config.SPORT_GROUP)
    ath = ath.rename(columns={"lang": "region"})
    cols = ["date", "region", "athlete", "name", "sport", "group", "views", "value_norm"]
    return ath.sort_values(["region", "athlete", "date"])[cols]


def main():
    total = load_total()
    interest = build_interest(total)
    athletes = build_athletes(total)
    events = pd.DataFrame(config.EVENTS, columns=["type", "name", "start", "end", "precision"])

    os.makedirs(config.PROCESSED_DIR, exist_ok=True)
    interest.to_csv(os.path.join(config.PROCESSED_DIR, "interest.csv"), index=False, encoding="utf-8-sig")
    athletes.to_csv(os.path.join(config.PROCESSED_DIR, "athletes.csv"), index=False, encoding="utf-8-sig")
    events.to_csv(os.path.join(config.PROCESSED_DIR, "events.csv"), index=False, encoding="utf-8-sig")

    print(f"종목 관심도: {len(interest):,}행 / 선수 관심도: {len(athletes):,}행 / 이벤트: {len(events)}행")
    print(interest.groupby(["source", "region"])["sport"].nunique().rename("종목 수").to_string())
    print(athletes.groupby("region")["athlete"].nunique().rename("선수 수").to_string())


if __name__ == "__main__":
    main()
