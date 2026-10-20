# analysis.py
# 통합 데이터셋으로 연구 질문에 답하는 지표를 계산한다.
# 실행: python analysis.py   -> 결과를 화면에 출력하고 results/ 폴더에 CSV로 저장
#
# Q1. 펜싱은 '올림픽 때만 보는 스포츠'인가?   (상위 k일 집중도, 대회 효과 회귀, 올림픽 의존도, 추세)
# Q2. 펜싱에는 왜 '돈 버는 스타'가 없는가?     (선수 대회 집중도, 맨-휘트니 검정, 순위상관 순열검정)
# Q3. 펜싱 프로 리그는 가능한가?               (MMA의 성장 전 관심도와 펜싱 현재 비교)
# Q4. 펜싱은 격투기 시장과 독립된 시장인가?     (전년 같은 달 대비 변화율의 상관)

import os

from itertools import permutations

import numpy as np
import pandas as pd
from scipy import stats

import config

RESULT_DIR = "results"
PAD = pd.Timedelta(days=30)   # 대회 전후 30일까지는 '대회 영향 기간'으로 보고 평상시에서 제외


# ---------------------------------------------------------------
# 공통 함수
# ---------------------------------------------------------------
def load():
    data = pd.read_csv(os.path.join(config.PROCESSED_DIR, "interest.csv"), parse_dates=["date"])
    athletes = pd.read_csv(os.path.join(config.PROCESSED_DIR, "athletes.csv"), parse_dates=["date"])
    events = pd.read_csv(os.path.join(config.PROCESSED_DIR, "events.csv"), parse_dates=["start", "end"])
    games = events[events["type"].isin(["olympics", "asian_games"])].reset_index(drop=True)
    return data, athletes, games


def series(data, source, region, sport):
    """특정 출처·지역·종목의 보정된 관심도 시계열 (날짜 -> 값)"""
    s = data[(data["source"] == source) & (data["region"] == region) & (data["sport"] == sport)]
    return s.set_index("date")["value_norm"].sort_index()


def athlete_series(athletes, region, key):
    s = athletes[(athletes["region"] == region) & (athletes["athlete"] == key)]
    return s.set_index("date")["value_norm"].sort_index()


def is_normal_day(dates, games):
    """대회 기간과 그 전후 30일에 속하지 않는 '평상시' 날짜이면 True"""
    mask = np.ones(len(dates), dtype=bool)
    for _, g in games.iterrows():
        mask &= ~((dates >= g["start"] - PAD) & (dates <= g["end"] + PAD))
    return mask


def normal_median(s, games):
    return s[is_normal_day(s.index, games)].median()


def annual_change(yearly):
    """연도별 값에 로그-직선을 맞춰 연평균 변화율(%)을 구한다"""
    y = yearly[yearly > 0]
    slope = np.polyfit(y.index, np.log(y.values), 1)[0]
    return (np.exp(slope) - 1) * 100


def spearman(x, y):
    """순위 상관계수: 값을 순위로 바꾼 뒤 상관계수를 구한다 (단위가 수천 배 차이 나도 쓸 수 있음)"""
    return np.corrcoef(pd.Series(x).rank(), pd.Series(y).rank())[0, 1]


# ---------------------------------------------------------------
# Q1-a. 대회별 올림픽 의존도와 잔존율
#   올림픽 의존도 = 대회 기간 최고값 / 직전 1년 평상시 중앙값
#   잔존율       = 대회 종료 60~90일 후 평균 / 대회 시작 30~90일 전 평균
# ---------------------------------------------------------------
def event_metrics(s, games):
    rows = []
    for _, g in games.iterrows():
        start, end = g["start"], g["end"]
        if start < s.index.min() + pd.Timedelta(days=365):
            continue                                      # 직전 1년 데이터가 없는 대회는 제외
        base = normal_median(s[start - pd.Timedelta(days=395): start - PAD], games)
        peak = s[start:end].max()
        after = s[end + pd.Timedelta(days=60): end + pd.Timedelta(days=90)]
        before = s[start - pd.Timedelta(days=90): start - PAD]
        retention = after.mean() / before.mean() if len(after) >= 25 else np.nan
        rows.append({"event": g["name"], "type": g["type"], "baseline": base, "peak": peak,
                     "dependency": peak / base if base > 0 else np.nan, "retention": retention})
    return pd.DataFrame(rows)


def q1_sports(data, games):
    rows = []
    for region in ["ko", "en"]:
        for sport in config.WIKI_ARTICLES[region]:
            m = event_metrics(series(data, "wikipedia", region, sport), games)
            m.insert(0, "sport", sport)
            m.insert(0, "region", region)
            rows.append(m)
    ev = pd.concat(rows, ignore_index=True)

    summary = (ev[ev["type"] == "olympics"].groupby(["region", "sport"])
               .agg(olympic_dependency=("dependency", "median"), retention=("retention", "median")))
    summary["asian_games_dependency"] = (ev[ev["type"] == "asian_games"]
                                         .groupby(["region", "sport"])["dependency"].median())
    summary["group"] = summary.index.get_level_values("sport").map(config.SPORT_GROUP)
    return ev, summary


# ---------------------------------------------------------------
# Q1-b. 평상시 관심도의 연도별 추세
# ---------------------------------------------------------------
def q1_trend_wiki(data, games):
    rows = {}
    for region in ["ko", "en"]:
        for sport in config.WIKI_ARTICLES[region]:
            s = series(data, "wikipedia", region, sport)
            normal = s[is_normal_day(s.index, games)]
            rows[(region, sport)] = normal.groupby(normal.index.year).median()
    yb = pd.DataFrame(rows).T[list(range(2016, 2027))]
    change = pd.Series({k: annual_change(v[list(range(2016, 2026))]) for k, v in yb.iterrows()})
    return yb, change


def game_months(games):
    months = set()
    for _, g in games.iterrows():
        months |= set(pd.period_range(g["start"], g["end"], freq="M"))
    return months


def q1_trend_gtrends(data, games):
    gm = game_months(games)
    rows = {}
    for region in ["world", "korea"]:
        for sport in config.GTRENDS_TOPICS:
            s = series(data, "google_trends", region, sport)
            normal = s[[m not in gm for m in s.index.to_period("M")]]
            rows[(region, sport)] = normal.groupby(normal.index.year).median()
    yb = pd.DataFrame(rows).T
    change = pd.Series({k: annual_change(v[list(range(2004, 2026))]) for k, v in yb.iterrows()})
    return yb, change



# ---------------------------------------------------------------
# Q1-c. 상위 k일 집중도: 1년 관심 중 가장 많이 본 k일이 차지하는 비율 (%)
#   '대회'를 정의할 필요가 없어서 축구의 월드컵, 야구의 WBC처럼 종목마다 다른 메인 이벤트가
#   자동으로 들어간다. 관심이 1년 내내 고르게 퍼져 있으면 k/365 (3일이면 0.8%)가 된다.
# ---------------------------------------------------------------
TOP_K = [1, 3, 10]


def topk_share(data, years=range(2016, 2026)):
    rows = []
    for (region, sport), g in data[data["source"] == "wikipedia"].groupby(["region", "sport"]):
        s = g.set_index("date")["value_norm"]
        for y in years:
            x = s[str(y)]
            rows.append({"region": region, "sport": sport, "year": y,
                         **{f"top{k}": x.nlargest(k).sum() / x.sum() * 100 for k in TOP_K}})
    t = pd.DataFrame(rows)
    summary = t.groupby(["region", "sport"]).agg(
        **{f"top{k}_median": (f"top{k}", "median") for k in TOP_K},
        **{f"top{k}_max": (f"top{k}", "max") for k in TOP_K})
    summary["top3_max_year"] = t.loc[t.groupby(["region", "sport"])["top3"].idxmax()].set_index(
        ["region", "sport"])["year"]
    return t, summary


# ---------------------------------------------------------------
# Q1-d. 대회 효과 회귀분석 (최소제곱 + Newey-West 표준오차, numpy로 직접 구현)
#   log(펜싱 관심도) - log(비교 종목 관심도) = a + d * (올림픽·아시안게임 기간이면 1)
#   두 종목의 '차이'를 쓰면 위키 방문자 증감처럼 두 종목에 함께 작용하는 요인이 빠진다.
#   d 는 대회 기간에 펜싱이 비교 종목보다 '추가로' 오르는 정도(로그)이며, exp(d) 배로 해석한다.
#   하루하루의 관심도는 서로 이어져 있어(자기상관) 보통의 표준오차는 너무 작게 나오므로,
#   시계열에서 쓰는 Newey-West 방식으로 30일까지의 자기상관을 반영한 표준오차를 구한다.
# ---------------------------------------------------------------
HAC_LAGS = 30
LOG_FLOOR = 0.1   # 조회수 0인 날도 로그를 취할 수 있도록 더하는 작은 값 (100만 건당 0.1)


def ols_newey_west(y, X, lags=HAC_LAGS):
    """최소제곱 계수와 Newey-West 표준오차"""
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    u = y - X @ beta
    Xu = X * u[:, None]
    S = Xu.T @ Xu
    for lag in range(1, lags + 1):
        w = 1 - lag / (lags + 1)                     # Bartlett 가중치
        G = Xu[lag:].T @ Xu[:-lag]
        S += w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    return beta, np.sqrt(np.diag(cov))


def games_effect_regression(data, games, target="fencing"):
    rows = []
    for region in ["ko", "en"]:
        t = series(data, "wikipedia", region, target)
        in_games = np.zeros(len(t), dtype=bool)
        for _, g in games.iterrows():
            in_games |= (t.index >= g["start"]) & (t.index <= g["end"])
        for other in config.WIKI_ARTICLES[region]:
            if other == target:
                continue
            o = series(data, "wikipedia", region, other).reindex(t.index)
            y = (np.log(t + LOG_FLOOR) - np.log(o + LOG_FLOOR)).values
            X = np.column_stack([np.ones(len(y)), in_games.astype(float)])
            beta, se = ols_newey_west(y, X)
            d, d_se = beta[1], se[1]
            p = 2 * stats.norm.sf(abs(d / d_se))
            rows.append({"region": region, "vs": other, "d": d, "se": d_se,
                         "times": np.exp(d), "ci_low": np.exp(d - 1.96 * d_se),
                         "ci_high": np.exp(d + 1.96 * d_se), "p_value": p})
    return pd.DataFrame(rows)

# ---------------------------------------------------------------
# Q2. 스타 선수: 평상시 관심도, 대회 집중도, 수입
#   최근 2년(2024.10.16~2026.10.15)의 평상시 하루 관심도를 '광고주가 보는 얼굴의 크기'로 본다.
#   대회 집중도 = 2021~2026 전체 관심 중 올림픽·아시안게임 기간(전후 30일 포함)에 몰린 비율
# ---------------------------------------------------------------
def athlete_metrics(athletes, games):
    rows = []
    recent_games = games[games["start"] >= "2021-01-01"]
    for (region, key), g in athletes.groupby(["region", "athlete"]):
        s = g.set_index("date")["value_norm"].sort_index()
        recent = s["2024-10-16":"2026-10-15"]
        baseline = normal_median(recent, games)
        # 최근 2년 중 조회 기록이 있는 날의 비율. 문서 제목이 바뀌면 조회수가 옛 제목과 새 제목으로
        # 나뉘어 기록이 비게 되므로, 이 비율이 낮은 문서는 수입 분석에서 뺀다.
        coverage = (recent > 0).sum() / len(pd.date_range("2024-10-16", "2026-10-15"))
        window = s["2021-01-01":"2026-10-15"]
        in_games = ~is_normal_day(window.index, recent_games)
        peak = np.nanmax([s[r["start"]:r["end"]].max() for _, r in recent_games.iterrows()])
        rows.append({"region": region, "athlete": key, "name": config.ATHLETES[key][0],
                     "sport": config.ATHLETES[key][1], "group": config.SPORT_GROUP[config.ATHLETES[key][1]],
                     "coverage": coverage, "baseline": baseline, "games_peak": peak,
                     "dependency": peak / baseline if baseline > 0 else np.nan,
                     "games_share": window[in_games].sum() / window.sum(),
                     "days_in_games_windows": in_games.mean()})
    return pd.DataFrame(rows)


MIN_COVERAGE = 0.9


def exact_spearman_test(x, y):
    """순위상관의 정확 순열검정 (단측: 양의 상관인가)
    x 의 순서를 가능한 모든 방법(n!)으로 섞어 보고, 실제 순위상관 이상이 나오는 비율을 p값으로 한다.
    표본이 7명처럼 작을 때 정규분포 근사 없이 쓸 수 있는 비모수 검정이다."""
    rx, ry = pd.Series(x).rank().values, pd.Series(y).rank().values
    observed = np.corrcoef(rx, ry)[0, 1]
    count = total = 0
    for perm in permutations(rx):
        total += 1
        if np.corrcoef(perm, ry)[0, 1] >= observed - 1e-12:
            count += 1
    return observed, count / total


def games_share_test(ath_metrics, region="ko"):
    """올림픽형 선수의 대회 집중도가 다른 선수보다 큰가 (맨-휘트니 U 검정, 정확 p값)"""
    a = ath_metrics[ath_metrics["region"] == region]
    olympic = a[a["group"] == "olympic_only"]["games_share"]
    others = a[a["group"] != "olympic_only"]["games_share"]
    res = stats.mannwhitneyu(olympic, others, alternative="greater", method="exact")
    return {"olympic_n": len(olympic), "others_n": len(others),
            "olympic_median": olympic.median(), "others_median": others.median(),
            "U": res.statistic, "p_value": res.pvalue}


def q2_income(ath_metrics):
    income = pd.read_csv(config.INCOME_FILE)
    usable = ath_metrics[(ath_metrics["region"] == "en") & (ath_metrics["coverage"] >= MIN_COVERAGE)]
    excluded = ath_metrics[(ath_metrics["region"] == "en") & (ath_metrics["coverage"] < MIN_COVERAGE)]
    for _, r in excluded.iterrows():
        print(f"  (제외) {r['name']}: 최근 2년 조회 기록이 있는 날 {r['coverage']:.0%} - 문서 제목 변경 등으로 기록이 나뉨")
    en = usable.merge(income[["key", "income_usd", "income_type"]],
                                                          left_on="athlete", right_on="key")
    corr = {"수입-평상시 관심도": exact_spearman_test(en["income_usd"], en["baseline"]),
            "수입-대회 최고 관심도": exact_spearman_test(en["income_usd"], en["games_peak"])}
    return en.drop(columns="key"), corr


# ---------------------------------------------------------------
# Q3. MMA가 크기 전 관심도 vs 펜싱의 현재 관심도 (구글 트렌드: 같은 화면 비교라 같은 척도)
# ---------------------------------------------------------------
def q3_benchmark(gt_yearly):
    w = gt_yearly.loc["world"]
    return pd.DataFrame({
        "MMA": w.loc["mma"], "펜싱": w.loc["fencing"], "태권도": w.loc["taekwondo"],
        "복싱": w.loc["boxing"],
    })


# ---------------------------------------------------------------
# Q4. 펜싱은 격투기 시장과 독립된 시장인가?
#   월별 관심도(대회 달 제외)의 로그를 '전년 같은 달 대비 변화'로 바꿔 계절성과 장기 추세를 없앤 뒤,
#   종목끼리 변화가 같이 움직이는지 상관계수로 본다. 같은 시장이면 함께 움직이고(양의 상관),
#   독립된 시장이면 상관이 0에 가깝다.
# ---------------------------------------------------------------
Q4_PAIRS = [("taekwondo", "mma"), ("taekwondo", "boxing"),
            ("fencing", "mma"), ("fencing", "boxing"), ("fencing", "taekwondo")]


def yoy_correlations(data, games):
    gm = game_months(games)
    rows = []
    for source, region in [("wikipedia", "ko"), ("wikipedia", "en"), ("google_trends", "world")]:
        x = data[(data["source"] == source) & (data["region"] == region)]
        m = x.pivot_table(index="date", columns="sport", values="value_norm").resample("MS").mean()
        m = m[[p not in gm for p in m.index.to_period("M")]].replace(0, np.nan)
        yoy = np.log(m).diff(12)
        for a, b in Q4_PAIRS:
            rows.append({"source": f"{source}:{region}", "pair": f"{a}-{b}", "corr": yoy[a].corr(yoy[b])})
    return pd.DataFrame(rows).pivot(index="pair", columns="source", values="corr").loc[
        [f"{a}-{b}" for a, b in Q4_PAIRS]]


# ---------------------------------------------------------------
# 실행
# ---------------------------------------------------------------
def main():
    os.makedirs(RESULT_DIR, exist_ok=True)
    pd.set_option("display.width", 200)
    data, athletes, games = load()

    def save(df, name):
        df.to_csv(os.path.join(RESULT_DIR, name), encoding="utf-8-sig")

    # Q1
    ev, summary = q1_sports(data, games)
    save(ev, "event_metrics.csv")
    save(summary, "dependency_summary.csv")
    print("[Q1] 종목별 올림픽 의존도·잔존율 (리우·도쿄·파리 중앙값)")
    print(summary.round(2).to_string())

    tk, tk_summary = topk_share(data)
    save(tk, "topk_share_yearly.csv")
    save(tk_summary, "topk_share_summary.csv")
    print("\n[Q1] 1년 관심 중 상위 k일 비율 (%, 2016~2025 연도별 중앙값 / 최댓값)")
    print(tk_summary.round(1).to_string())

    reg = games_effect_regression(data, games)
    save(reg, "games_effect_regression.csv")
    print("\n[Q1] 회귀분석: 대회 기간 펜싱의 추가 상승 배수 (Newey-West 95% 신뢰구간)")
    print(reg.round({"d": 3, "se": 3, "times": 1, "ci_low": 1, "ci_high": 1}).to_string(index=False))

    yb, change = q1_trend_wiki(data, games)
    save(yb, "yearly_baseline_wiki.csv")
    print("\n[Q1] 위키 평상시 관심도 (전체 조회 100만 건당, 연도별 중앙값)")
    print(yb.round(1).to_string())
    print("\n[Q1] 위키 평상시 관심도 연평균 변화율 (%, 2016~2025)")
    print(change.round(1).unstack().to_string())

    gty, gtc = q1_trend_gtrends(data, games)
    save(gty, "yearly_baseline_gtrends.csv")
    print("\n[Q1] 구글 트렌드 평상시 관심도 (대회 달 제외 연도별 중앙값)")
    print(gty[[2004, 2006, 2008, 2010, 2014, 2018, 2022, 2025]].to_string())
    print("\n[Q1] 구글 트렌드 연평균 변화율 (%, 2004~2025)")
    print(gtc.round(1).unstack().to_string())

    # Q2
    am = athlete_metrics(athletes, games)
    save(am, "athlete_metrics.csv")
    print("\n[Q2] 스타 선수 지표 (최근 2년 평상시 관심도, 2021~ 대회 기간 집중도)")
    print(am.sort_values(["region", "baseline"], ascending=[True, False]).round(3).to_string(index=False))
    mw = games_share_test(am)
    print("\n[Q2] 맨-휘트니 U 검정: 올림픽형 선수의 대회 집중도가 더 큰가 (한국어 위키)")
    print(f"  올림픽형 {mw['olympic_n']}명 중앙값 {mw['olympic_median']:.0%} vs 나머지 {mw['others_n']}명 "
          f"{mw['others_median']:.0%}, U={mw['U']:.0f}, 정확 p값={mw['p_value']:.4f}")
    pd.Series(mw).to_csv(os.path.join(RESULT_DIR, "games_share_test.csv"), encoding="utf-8-sig")

    inc, corr = q2_income(am)
    save(inc, "income_vs_interest.csv")
    print("\n[Q2] 수입 vs 관심도 (영어 위키)")
    print(inc[["name", "income_usd", "baseline", "games_peak", "games_share"]]
          .sort_values("income_usd").round(3).to_string(index=False))
    for k, (rho, p) in corr.items():
        print(f"  순위상관 {k}: {rho:+.2f} (정확 순열검정 단측 p값 {p:.3f})")
    pd.DataFrame(corr, index=["rho", "p_value"]).T.to_csv(
        os.path.join(RESULT_DIR, "income_correlation.csv"), encoding="utf-8-sig")

    # Q3
    bench = q3_benchmark(gty)
    save(bench, "mma_vs_fencing.csv")
    print("\n[Q3] 전 세계 구글 트렌드 평상시 관심도 (같은 척도)")
    print(bench.loc[[2004, 2005, 2006, 2008, 2010, 2015, 2020, 2025]].to_string())

    # Q4
    q4 = yoy_correlations(data, games)
    save(q4, "independence_correlation.csv")
    print("\n[Q4] 전년 같은 달 대비 변화율의 상관 (대회 달 제외)")
    print(q4.round(2).to_string())


if __name__ == "__main__":
    main()
