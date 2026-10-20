# main.py
# 프로젝트 전체를 한 번에 실행하거나, 원하는 종목·선수의 지표를 바로 조회하는 진입점.
#
# 사용법
#   python main.py                    데이터셋 생성 -> 분석 -> 그래프 생성을 순서대로 실행
#   python main.py --sport fencing    한 종목의 올림픽 의존도·잔존율·평상시 추세 조회
#   python main.py --athlete oh_su    한 선수의 평상시 관심도·대회 집중도·수입 조회
#   python main.py --list             조회할 수 있는 종목·선수 이름 목록

import argparse
import os
import sys

import pandas as pd

import config

REQUIRED_RAW = ["wiki_pageviews.csv", "wiki_athletes.csv", "wiki_total.csv"]


def check_raw_data():
    """원본 데이터가 없으면 어떤 파일이 없는지, 어떻게 만드는지 알려주고 멈춘다."""
    missing = [f for f in REQUIRED_RAW if not os.path.exists(os.path.join(config.RAW_DIR, f))]
    if not os.path.exists(os.path.join(config.RAW_DIR, "gtrends.csv")):
        missing.append("gtrends.csv")
    if missing:
        print("다음 원본 데이터가 없습니다:", ", ".join(missing))
        print("  -> python collect_wiki.py 와 python load_gtrends.py 를 먼저 실행하세요 (README 3번 참고).")
        sys.exit(1)


def run_all():
    import analysis
    import build_dataset
    import figures

    check_raw_data()
    print("=" * 60, "\n1) 통합 데이터셋 만들기\n" + "=" * 60)
    build_dataset.main()
    print("\n" + "=" * 60, "\n2) 분석\n" + "=" * 60)
    analysis.main()
    print("\n" + "=" * 60, "\n3) 그래프\n" + "=" * 60)
    figures.main()
    print("\n완료: results/ 에 분석 결과, figures/ 에 그래프가 저장되었습니다.")


def ensure_results():
    """조회 기능은 analysis.py 결과를 읽으므로, 결과가 없으면 먼저 만든다."""
    if not os.path.exists(os.path.join("results", "athlete_metrics.csv")):
        print("분석 결과가 없어 먼저 전체 실행을 합니다...\n")
        run_all()
        print()


def show_sport(sport):
    if sport not in config.SPORT_GROUP:
        print(f"'{sport}' 는 없는 종목입니다. 가능한 종목: {', '.join(config.SPORT_GROUP)}")
        sys.exit(1)
    ensure_results()
    summary = pd.read_csv("results/dependency_summary.csv", index_col=[0, 1])
    yearly = pd.read_csv("results/yearly_baseline_wiki.csv", index_col=[0, 1])
    print(f"[{config.NAMES[sport]}] 묶음: {config.GROUP_NAMES[config.SPORT_GROUP[sport]]}")
    for region, label in [("ko", "한국어 위키"), ("en", "영어 위키")]:
        r = summary.loc[(region, sport)]
        y = yearly.loc[(region, sport)]
        print(f"  {label}: 올림픽 의존도 {r['olympic_dependency']:.1f}배, "
              f"아시안게임 의존도 {r['asian_games_dependency']:.1f}배, 잔존율 {r['retention']:.2f}")
        print(f"            평상시 관심도(100만 건당) 2016년 {y['2016']:.1f} -> 2025년 {y['2025']:.1f}")


def show_athlete(key):
    if key not in config.ATHLETES:
        print(f"'{key}' 는 없는 선수입니다. 가능한 선수: {', '.join(config.ATHLETES)}")
        sys.exit(1)
    ensure_results()
    am = pd.read_csv("results/athlete_metrics.csv", index_col=0)
    income = pd.read_csv(config.INCOME_FILE).set_index("key")
    name, sport = config.ATHLETES[key]
    print(f"[{name}] 종목: {config.NAMES[sport]} ({config.GROUP_NAMES[config.SPORT_GROUP[sport]]})")
    rows = am[am["athlete"] == key].sort_values("region", ascending=False)   # 한국어 먼저
    for _, r in rows.iterrows():
        label = "한국어 위키" if r["region"] == "ko" else "영어 위키"
        print(f"  {label}: 최근 2년 평상시 관심도 {r['baseline']:.2f} (100만 건당), "
              f"관심 중 대회 기간 비율 {r['games_share']:.0%}")
        if r["coverage"] < 0.9:      # analysis.MIN_COVERAGE 와 같은 기준
            print(f"      ※ 최근 2년 중 조회 기록이 있는 날 {r['coverage']:.0%} "
                  "(90% 미만이라 수입 분석에서는 제외되는 문서)")
    if key in income.index:
        i = income.loc[key]
        print(f"  공개된 연 수입: ${i['income_usd']:,.0f} ({i['income_type']}, {i['period']})")
    else:
        print("  공개된 연 수입 자료 없음")


def main():
    parser = argparse.ArgumentParser(description="펜싱 프로 리그는 가능한가? - 분석 프로그램")
    parser.add_argument("--sport", help="종목 지표 조회 (예: fencing)")
    parser.add_argument("--athlete", help="선수 지표 조회 (예: oh_su)")
    parser.add_argument("--list", action="store_true", help="조회 가능한 종목·선수 목록")
    args = parser.parse_args()

    if args.list:
        print("종목:", ", ".join(f"{k}({v})" for k, v in config.NAMES.items()))
        print("선수:", ", ".join(f"{k}({v[0]})" for k, v in config.ATHLETES.items()))
    elif args.sport:
        show_sport(args.sport.lower())
    elif args.athlete:
        show_athlete(args.athlete.lower())
    else:
        run_all()


if __name__ == "__main__":
    main()
