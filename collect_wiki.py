# collect_wiki.py
# 위키피디아 문서별 '일별 조회수'를 수집해서 data/raw/wiki_pageviews.csv 로 저장한다.
# 실행: python collect_wiki.py
#
# 조회수 API 형식:
# https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/
#     {언어}.wikipedia/all-access/user/{문서제목}/daily/{시작YYYYMMDD}/{끝YYYYMMDD}
# - agent=user : 검색 로봇(봇) 조회는 빼고 사람 조회만 센다
# - 조회수가 0인 날은 응답에서 빠지므로, 빈 날짜는 0으로 채운다

import os
import time
from urllib.parse import quote

import pandas as pd
import requests

import config

HEADERS = {"User-Agent": config.WIKI_USER_AGENT}


def resolve_title(lang, title):
    """리다이렉트 문서(예: '복싱' -> '권투')를 실제 문서 제목으로 바꾼다.
    조회수 API는 리다이렉트를 따라가지 않으므로 이 단계가 꼭 필요하다."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {"action": "query", "titles": title, "redirects": 1, "format": "json"}
    res = requests.get(url, params=params, headers=HEADERS, timeout=30)
    res.raise_for_status()
    pages = res.json()["query"]["pages"]
    page = next(iter(pages.values()))
    if "missing" in page:
        raise ValueError(f"[{lang}] '{title}' 문서가 없습니다. config.py의 제목을 확인하세요.")
    return page["title"]


def fetch_daily_views(lang, title, start, end):
    """한 문서의 일별 조회수를 DataFrame(date, views)으로 돌려준다."""
    article = quote(title.replace(" ", "_"), safe="")
    s = start.replace("-", "")
    e = end.replace("-", "")
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"{lang}.wikipedia/all-access/user/{article}/daily/{s}/{e}")
    res = requests.get(url, headers=HEADERS, timeout=30)
    if res.status_code == 404:          # 기간 내 조회 기록이 전혀 없는 경우
        items = []
    else:
        res.raise_for_status()
        items = res.json().get("items", [])

    df = pd.DataFrame(
        {"date": pd.to_datetime([it["timestamp"][:8] for it in items], format="%Y%m%d"),
         "views": [it["views"] for it in items]}
    )
    # 응답에 없는 날짜(=조회수 0)를 0으로 채워서 날짜가 빠짐없이 이어지게 만든다
    full_range = pd.date_range(start, end, freq="D")
    df = df.set_index("date").reindex(full_range, fill_value=0)
    df.index.name = "date"
    return df.reset_index()


def fetch_total_views(lang, start, end):
    """위키피디아 언어판 '전체' 일별 조회수. 종목별 조회수를 이 값으로 나눠서
    위키피디아 방문자 자체가 늘고 줄어드는 효과를 제거한다 (실질 관심도 보정)."""
    s = start.replace("-", "")
    e = end.replace("-", "")
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/"
           f"{lang}.wikipedia/all-access/user/daily/{s}/{e}")
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    items = res.json()["items"]
    return pd.DataFrame({
        "date": pd.to_datetime([it["timestamp"][:8] for it in items], format="%Y%m%d"),
        "lang": lang,
        "total_views": [it["views"] for it in items],
    })


def collect(articles_by_lang, key_name, trim_before_first_view=False):
    """언어별 {key: 문서 제목} 사전을 받아 일별 조회수를 하나의 표로 모은다.
    trim_before_first_view=True 이면 문서가 생기기 전(조회 기록이 없는 앞부분)을 잘라낸다."""
    frames = []
    for lang, articles in articles_by_lang.items():
        for key, title in articles.items():
            real_title = resolve_title(lang, title)
            df = fetch_daily_views(lang, real_title, config.WIKI_START, config.END_DATE)
            if trim_before_first_view:
                first_day = df.loc[df["views"] > 0, "date"].min()
                df = df[df["date"] >= first_day].copy()
            df["lang"], df[key_name], df["article"] = lang, key, real_title
            frames.append(df)
            print(f"[{lang}] {key:<10} '{title}' -> '{real_title}' ({len(df):,}일)")
            time.sleep(0.5)  # 서버에 부담을 주지 않도록 요청 사이에 잠깐 쉰다
    return pd.concat(frames, ignore_index=True)


def main():
    os.makedirs(config.RAW_DIR, exist_ok=True)

    totals = pd.concat([fetch_total_views(lang, config.WIKI_START, config.END_DATE)
                        for lang in config.WIKI_ARTICLES], ignore_index=True)
    totals.to_csv(os.path.join(config.RAW_DIR, "wiki_total.csv"), index=False)
    print(f"전체 조회수 저장 완료 ({len(totals):,}행)")

    sports = collect(config.WIKI_ARTICLES, "sport")
    sports.to_csv(os.path.join(config.RAW_DIR, "wiki_pageviews.csv"), index=False, encoding="utf-8-sig")
    print(f"종목 문서 저장 완료 ({len(sports):,}행)")

    # 선수 문서는 데뷔·활약 이후에 만들어진 경우가 많아 문서가 생긴 뒤부터만 쓴다
    athletes = collect(config.WIKI_ATHLETES, "athlete", trim_before_first_view=True)
    athletes.to_csv(os.path.join(config.RAW_DIR, "wiki_athletes.csv"), index=False, encoding="utf-8-sig")
    print(f"선수 문서 저장 완료 ({len(athletes):,}행)")


if __name__ == "__main__":
    main()
