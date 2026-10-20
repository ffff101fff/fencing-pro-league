# figures.py
# 분석 결과 그래프를 figures/ 폴더에 PNG로 저장한다.
# 실행: python figures.py   (analysis.py 실행 후)

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

import analysis
import config

FIG_DIR = "figures"
FENCING = "#2a78d6"      # 펜싱(올림픽형)만 파란색으로 강조
MMA = "#eb6834"          # 비교의 기준이 되는 MMA는 주황색
OTHER = "#9a9893"        # 나머지는 회색 + 직접 라벨
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def setup_font():
    """한글 폰트 설정 (Windows: 맑은 고딕, Mac: AppleGothic, Linux: Noto Sans CJK)"""
    for name in ["Malgun Gothic", "AppleGothic", "Noto Sans CJK KR", "NanumGothic"]:
        if any(name == f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams.update({"axes.unicode_minus": False, "font.size": 10,
                         "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                         "xtick.color": MUTED, "ytick.color": MUTED,
                         "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    fig.savefig(os.path.join(FIG_DIR, name), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("저장:", name)


def color_of(sport):
    return FENCING if config.SPORT_GROUP.get(sport) == "olympic_only" else OTHER


def fig1_timeline(data, games):
    """그림 1. 한국어 위키 펜싱 vs 축구 일별 관심도 (로그 축)"""
    fig, ax = plt.subplots(figsize=(9, 3.3))
    for _, g in games.iterrows():
        ax.axvspan(g["start"], g["end"], color=GRID, lw=0)
    fb = analysis.series(data, "wikipedia", "ko", "football").rolling(7, center=True).mean()
    fe = analysis.series(data, "wikipedia", "ko", "fencing")
    ax.plot(fb.index, fb.values, color=OTHER, lw=1.2)
    ax.plot(fe.index, fe.values, color=FENCING, lw=1.0)
    ax.set_yscale("log")
    ax.set_xlim(pd.Timestamp("2015-07-01"), pd.Timestamp("2026-10-15"))
    ax.set_ylabel("위키 전체 조회 100만 건당")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.text(pd.Timestamp("2015-08-01"), 160, "축구 (7일 평균)", color=MUTED, fontsize=9)
    ax.annotate("펜싱", (fe.idxmax(), fe.max()), xytext=(8, -4), textcoords="offset points",
                color=FENCING, fontsize=10, fontweight="bold")
    ax.set_title("펜싱은 대회 기간(회색 띠)에만 치솟는다 - 한국어 위키피디아 일별 관심도",
                 loc="left", color=INK, fontsize=11)
    save(fig, "fig1_timeline_ko.png")


def fig2_dependency(summary):
    """그림 2. 6종목 올림픽 의존도"""
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.0))
    for ax, region, title in zip(axes, ["ko", "en"], ["한국어 위키피디아", "영어 위키피디아"]):
        s = summary.loc[region, "olympic_dependency"].sort_values()
        ax.barh([config.NAMES[k] for k in s.index], s.values,
                color=[color_of(k) for k in s.index], height=0.6)
        ax.set_xscale("log")
        for i, v in enumerate(s.values):
            ax.text(v * 1.12, i, f"{v:,.0f}배" if v >= 10 else f"{v:.1f}배", va="center", fontsize=9)
        ax.set_xlim(0.8, s.max() * 6)
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.grid(axis="x", color=GRID, lw=0.6)
        ax.tick_params(axis="y", length=0)
    fig.suptitle("올림픽 의존도 = 대회 중 최고 관심도 ÷ 평상시 관심도 (리우·도쿄·파리 중앙값)",
                 x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout()
    save(fig, "fig2_dependency.png")


def fig3_mma_vs_fencing(gt_yearly):
    """그림 3. 구글 트렌드 전 세계 평상시 관심도 - 같은 척도에서 MMA와 펜싱 비교"""
    w = gt_yearly.loc["world"]
    years = [y for y in w.columns if 2004 <= y <= 2025]
    fig, ax = plt.subplots(figsize=(9, 3.3))
    for sport, color, lw in [("taekwondo", OTHER, 1.3), ("mma", MMA, 2.0), ("fencing", FENCING, 2.0)]:
        ax.plot(years, w.loc[sport, years].values, color=color, lw=lw)
        ax.text(years[-1] + 0.3, w.loc[sport, years[-1]], config.NAMES[sport], color=color,
                va="center", fontsize=9, fontweight="bold" if sport != "taekwondo" else "normal")
    ax.axvline(2005, color=INK, lw=0.8, ls="--")
    ax.text(2005.15, 9.6, "UFC 리얼리티쇼 TUF 첫 방송 (2005)", fontsize=9, color=INK, va="top")
    ax.set_ylabel("구글 트렌드 지수 (같은 척도)")
    ax.set_xlim(2004, 2026.5)
    ax.set_ylim(0, 10)
    ax.set_xticks(range(2004, 2026, 3))
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_title("2004년 MMA는 펜싱보다 작았다 - 전 세계 평상시 검색 관심도 (대회 달 제외 연도별 중앙값)",
                 loc="left", fontsize=11, color=INK)
    save(fig, "fig3_mma_vs_fencing.png")


def fig4_games_share(am):
    """그림 4. 스타 선수 관심의 몇 %가 대회 기간에 몰렸나 (한국어 위키, 2021~2026)"""
    ko = am[am["region"] == "ko"].sort_values("games_share")
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.barh(ko["name"], ko["games_share"] * 100, color=[color_of(s) for s in ko["sport"]], height=0.6)
    for i, (v, sp) in enumerate(zip(ko["games_share"] * 100, ko["sport"])):
        ax.text(v + 1, i, f"{v:.0f}%  ({config.NAMES[sp]})", va="center", fontsize=9)
    share_days = ko["days_in_games_windows"].median() * 100
    ax.axvline(share_days, color=INK, lw=0.8, ls="--")
    ax.text(share_days + 0.8, -0.75, f"← 관심이 고르게 퍼져 있다면 {share_days:.0f}% (대회 기간이 전체 날짜에서 차지하는 비율)",
            fontsize=8.5, color=INK, va="center")
    ax.set_ylim(-1.2, len(ko) - 0.4)
    ax.set_xlim(0, 105)
    ax.set_xlabel("2021~2026년 위키 관심 중 올림픽·아시안게임 기간(전후 30일 포함)의 비율 (%)")
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title("펜싱 스타가 받는 관심의 대부분은 대회 기간에 몰린다 - 한국어 위키피디아",
                 loc="left", fontsize=11, color=INK)
    save(fig, "fig4_games_share.png")


# 점이 몰린 선수들의 라벨 위치 (x 이동, y 이동, 정렬)
LABEL_POS = {"mcgregor": (-7, 9, "right"), "ohtani": (-7, -15, "right"), "messi": (7, 4, "left"),
             "fury": (-8, -3, "right"), "son": (7, -3, "left"), "lee_jh": (-7, -3, "right")}


def fig5_income(inc):
    """그림 5. 평상시 관심도 vs 연 수입 (영어 위키, 로그-로그)"""
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for _, r in inc.iterrows():
        c = color_of(r["sport"])
        ax.scatter(r["baseline"], r["income_usd"], s=60, color=c, edgecolor="white", linewidth=1.5, zorder=3)
        dx, dy, ha = LABEL_POS.get(r["athlete"], (7, -3, "left"))
        ax.annotate(f"{r['name']} ({config.NAMES[r['sport']]})", (r["baseline"], r["income_usd"]),
                    xytext=(dx, dy), textcoords="offset points", fontsize=9, color=INK, ha=ha)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(inc["baseline"].min() / 2, inc["baseline"].max() * 4)
    ax.set_ylim(5e3, 1e9)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"${v/1e6:,.0f}M" if v >= 1e6 else f"${v/1e3:,.0f}K"))
    ax.set_xlabel("최근 2년 평상시 하루 관심도 (영어 위키 전체 조회 100만 건당)")
    ax.set_ylabel("공개된 연 수입 (펜싱·태권도는 우승 상금)")
    ax.grid(color=GRID, lw=0.6)
    ax.set_title("돈은 '매일 보이는 얼굴'을 따라간다 - 스타 선수의 평상시 관심도와 수입",
                 loc="left", fontsize=11, color=INK)
    save(fig, "fig5_income.png")


def main():
    setup_font()
    os.makedirs(FIG_DIR, exist_ok=True)
    data, athletes, games = analysis.load()
    read = lambda n, **k: pd.read_csv(os.path.join(analysis.RESULT_DIR, n), **k)
    summary = read("dependency_summary.csv", index_col=[0, 1])
    gt = read("yearly_baseline_gtrends.csv", index_col=[0, 1])
    gt.columns = gt.columns.astype(int)
    am = read("athlete_metrics.csv", index_col=0)
    inc = read("income_vs_interest.csv", index_col=0)
    fig1_timeline(data, games)
    fig2_dependency(summary)
    fig3_mma_vs_fencing(gt)
    fig4_games_share(am)
    fig5_income(inc)


if __name__ == "__main__":
    main()
