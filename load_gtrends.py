# load_gtrends.py
# 구글 트렌드에서 직접 내려받은 CSV 파일들을 읽어서 하나의 표로 정리한다.
#
# 구글 트렌드는 공식 API가 없고, 비공식 수집 라이브러리(pytrends)는 개발이 중단되어
# 자주 막힌다. 그래서 웹사이트에서 직접 CSV를 내려받는 방식을 쓴다.
#
# 내려받는 방법 (README의 '데이터 수집' 참고)
#   1) https://trends.google.com 접속 -> 기간 '2004 - 현재'
#   2) 아래 두 가지 비교를 만들고 각각 오른쪽 위 '다운로드(↓)' 버튼으로 CSV 저장
#      - world.csv : 전 세계 / fencing, boxing, taekwondo, handball  (주제 'Sport'로 선택)
#      - india.csv : 인도   / kabaddi
#   3) 파일을 data/raw/gtrends/ 폴더에 넣는다. 파일 이름이 지역 이름이 된다.
#
# 구글 트렌드 CSV의 특징
#   - 맨 위에 'Category: All categories' 같은 설명 줄이 있을 수 있다 -> 헤더 줄을 찾아서 읽는다
#   - 값이 1보다 작으면 '<1' 로 적혀 있다 -> 0.5로 바꾼다
#   - 열 이름이 'fencing: (Worldwide)' 형태다 -> ':' 앞부분만 종목 이름으로 쓴다

import glob
import io
import os

import pandas as pd

import config

DATE_HEADERS = ("Month", "Week", "Day", "Time", "월", "주", "일", "시간")

# 한국어 화면에서 내려받으면 열 이름이 한글로 나오므로 영어 종목 이름으로 통일한다
ALIASES = {"펜싱": "fencing", "복싱": "boxing", "권투": "boxing", "태권도": "taekwondo",
           "핸드볼": "handball", "카바디": "kabaddi"}


def normalize_sport(column_name):
    """'fencing: (Worldwide)', 'Fencing (Sport): (전 세계)', '펜싱: (전 세계)' -> 'fencing'"""
    name = column_name.split(":")[0]          # ':' 앞부분만
    name = name.split("(")[0].strip()         # '(Sport)' 같은 괄호 설명 제거
    return ALIASES.get(name, name.lower())


def read_gtrends_csv(path):
    """구글 트렌드 CSV 하나를 long 형식(date, sport, index)으로 읽는다."""
    with open(path, encoding="utf-8-sig") as f:
        lines = f.read().splitlines()

    # 날짜 열 이름으로 시작하는 줄을 헤더로 보고, 그 위의 설명 줄은 버린다
    header_idx = next(i for i, line in enumerate(lines)
                      if line.split(",")[0].strip() in DATE_HEADERS)
    df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))

    date_col = df.columns[0]
    df = df.rename(columns={date_col: "date"})
    df["date"] = pd.to_datetime(df["date"])

    long = df.melt(id_vars="date", var_name="term", value_name="index")
    long["sport"] = long["term"].map(normalize_sport)
    long["index"] = (long["index"].astype(str).str.strip()
                     .replace("<1", "0.5").astype(float))
    return long[["date", "sport", "index"]]


def load_all(folder=config.GTRENDS_DIR):
    frames = []
    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        region = os.path.splitext(os.path.basename(path))[0]   # world, india ...
        df = read_gtrends_csv(path)
        df["region"] = region
        frames.append(df)
    if not frames:
        raise SystemExit(f"{folder} 에 구글 트렌드 CSV가 없습니다. README를 보고 내려받으세요.")
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    out = load_all()
    path = os.path.join(config.RAW_DIR, "gtrends.csv")
    out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {path} ({len(out):,}행)")
