# 펜싱 프로 리그는 가능한가?

CAS1100-01 Computer Programming 프로젝트 (2026 Fall)
2015101013 Jangbo Ha

펜싱 세계 챔피언이 '돈 버는 스타'가 되지 못하는 이유를, 6종목 3묶음
(올림픽형: 펜싱·태권도 / 투기 프로형: 복싱·MMA / 대중 리그형: 축구·야구)의
위키피디아 조회수와 구글 트렌드 데이터로 분석합니다.

## 1. 환경 설정

Python 3.9 이상이 필요합니다.

```bash
pip install -r requirements.txt
```

## 2. 결과 재현하기

수집이 끝난 원본 데이터가 `data/raw/` 에 들어 있으므로, 아래 세 줄이면 보고서의 표와 그래프가 그대로 만들어집니다.

```bash
python build_dataset.py   # data/processed/ 에 interest.csv, athletes.csv, events.csv 생성
python analysis.py        # 지표 계산 결과를 화면에 출력하고 results/ 에 CSV로 저장
python figures.py         # figures/ 에 그래프 5개 생성
```

## 3. 데이터를 처음부터 다시 수집하기

### 3-1. 위키피디아 (자동)

```bash
python collect_wiki.py
```

| 파일 | 내용 |
|---|---|
| `data/raw/wiki_pageviews.csv` | 6종목 × 한국어·영어 문서의 일별 조회수 (2015-07-01 ~ 2026-10-15) |
| `data/raw/wiki_athletes.csv` | 스타 선수 문서의 일별 조회수 (문서가 생긴 날부터) |
| `data/raw/wiki_total.csv` | 한국어·영어 위키피디아 전체 일별 조회수 (보정용) |

### 3-2. 구글 트렌드 (웹에서 CSV 다운로드)

구글 트렌드는 공식 API가 없어 웹에서 받습니다. 단어(fencing)로 검색하면 울타리 검색이,
boxing은 박싱데이 검색이 섞이므로 **'스포츠 주제' ID**로 검색하고, 5종목을 **한 화면에서**
비교해야 같은 척도가 됩니다.

| 저장할 이름 | 링크 |
|---|---|
| `world.csv` | https://trends.google.com/trends/explore?date=all&q=%2Fm%2F02y8z,%2Fm%2F07gyv,%2Fm%2F01cgz,%2Fm%2F01h7lh,%2Fm%2F018jz&hl=en |
| `korea.csv` | https://trends.google.com/trends/explore?date=all&geo=KR&q=%2Fm%2F02y8z,%2Fm%2F07gyv,%2Fm%2F01cgz,%2Fm%2F01h7lh,%2Fm%2F018jz&hl=en |

첫 번째 그래프('Interest over time')의 다운로드 버튼(↓)으로 받아 `data/raw/gtrends/` 에 저장한 뒤:

```bash
python load_gtrends.py
```

### 3-3. 직접 만든 데이터

- `data/star_income.csv` : 스타 선수 공개 연 수입 (Forbes, 연봉 공개 자료, 계약 보도, 국제연맹 상금 발표. 각 행에 출처 URL)
- 이벤트 달력은 `config.py` 의 `EVENTS` 에 있습니다.

## 4. 파일 구조

| 파일 | 역할 |
|---|---|
| `config.py` | 기간, 6종목 3묶음, 위키 문서·선수 목록, 구글 트렌드 주제 ID, 이벤트 달력 |
| `collect_wiki.py` | 위키 종목·선수·전체 일별 조회수 수집 (리다이렉트 처리, 빈 날짜 0 채우기) |
| `load_gtrends.py` | 구글 트렌드 CSV 읽기 (설명 줄 제거, `<1` 처리, 한글/영어 열 이름 통일) |
| `build_dataset.py` | 통합 데이터셋 생성, 전체 조회수로 나눈 실질 관심도(`value_norm`) 계산 |
| `analysis.py` | Q1 올림픽 의존도·잔존율·추세 / Q2 스타 대회 집중도·수입 상관 / Q3 MMA 기준선 |
| `figures.py` | 보고서용 그래프 5개 생성 |
| `data/raw/gtrends_keyword/`, `data/raw/archive/` | 초기 수집 데이터 (동음이의어 문제의 증거, 이전 비교 구성) |
