# config.py
# 프로젝트 전체에서 같이 쓰는 설정값 (수집 기간, 종목·선수 목록, 이벤트 날짜)
# 종목이나 선수를 바꾸고 싶으면 이 파일만 고치면 된다.

# ---------------------------------------------------------------
# 1. 수집 기간
# ---------------------------------------------------------------
WIKI_START = "2015-07-01"   # 위키피디아 조회수 API가 제공하는 가장 이른 날짜
END_DATE = "2026-10-15"     # 수집 종료일 (2026 아이치·나고야 아시안게임 포함)

# ---------------------------------------------------------------
# 2. 6종목 3묶음
#    olympic_only : 올림픽 중심, 프로 시장 없음      (펜싱, 태권도)
#    combat_pro   : 1:1 투기 종목인데 프로 시장 있음 (복싱, MMA)
#    mass_league  : 연중 프로 리그, 최대 시장        (축구, 야구)
# ---------------------------------------------------------------
GROUPS = {
    "olympic_only": ["fencing", "taekwondo"],
    "combat_pro": ["boxing", "mma"],
    "mass_league": ["football", "baseball"],
}
SPORT_GROUP = {sport: g for g, sports in GROUPS.items() for sport in sports}

NAMES = {"fencing": "펜싱", "taekwondo": "태권도", "boxing": "복싱", "mma": "MMA",
         "football": "축구", "baseball": "야구"}
GROUP_NAMES = {"olympic_only": "올림픽형", "combat_pro": "투기 프로형", "mass_league": "대중 리그형"}

# 종목 위키 문서 제목 (리다이렉트여도 수집 코드가 실제 제목으로 바꿔준다)
WIKI_ARTICLES = {
    "ko": {"fencing": "펜싱", "taekwondo": "태권도", "boxing": "복싱", "mma": "종합격투기",
           "football": "축구", "baseball": "야구"},
    "en": {"fencing": "Fencing", "taekwondo": "Taekwondo", "boxing": "Boxing",
           "mma": "Mixed martial arts", "football": "Association football", "baseball": "Baseball"},
}

# ---------------------------------------------------------------
# 3. 스타 선수 위키 문서
#    한국어 위키: 한국 스타 / 영어 위키: 세계 스타 (+ 한국 스타의 영어 문서)
#    문서가 늦게 만들어진 선수는 첫 조회가 기록된 날부터 사용한다.
# ---------------------------------------------------------------
ATHLETES = {
    # key: (이름, 종목)
    "son": ("손흥민", "football"),
    "lee_jh": ("이정후", "baseball"),
    "messi": ("리오넬 메시", "football"),
    "ohtani": ("오타니 쇼헤이", "baseball"),
    "fury": ("타이슨 퓨리", "boxing"),
    "canelo": ("카넬로 알바레스", "boxing"),
    "mcgregor": ("코너 맥그리거", "mma"),
    "jung_cs": ("정찬성", "mma"),
    "lee_dh": ("이대훈", "taekwondo"),
    "oh_su": ("오상욱", "fencing"),
    "gu_bg": ("구본길", "fencing"),
    "kim_jh": ("김준호", "fencing"),
    "kim_jy": ("김지연", "fencing"),
}
WIKI_ATHLETES = {
    "ko": {"son": "손흥민", "lee_jh": "이정후", "jung_cs": "정찬성", "lee_dh": "이대훈",
           "oh_su": "오상욱", "gu_bg": "구본길", "kim_jh": "김준호 (펜싱 선수)",
           "kim_jy": "김지연 (펜싱 선수)", "fury": "타이슨 퓨리"},
    "en": {"messi": "Lionel Messi", "ohtani": "Shohei Ohtani", "fury": "Tyson Fury",
           "canelo": "Canelo Álvarez", "mcgregor": "Conor McGregor", "son": "Son Heung-min",
           "lee_jh": "Lee Jung-hoo", "oh_su": "Oh Sang-uk", "lee_dh": "Lee Dae-hoon"},
}

# ---------------------------------------------------------------
# 4. 구글 트렌드 '스포츠 주제' ID
#    단어로 검색하면 fencing=울타리, boxing=박싱데이(Boxing Day) 검색이 섞이므로 주제로 검색한다.
#    5개를 한 화면에서 비교해야 같은 척도가 되므로 반드시 한 번에 조회한다.
# ---------------------------------------------------------------
GTRENDS_TOPICS = {"fencing": "/m/02y8z", "taekwondo": "/m/07gyv", "boxing": "/m/01cgz",
                  "mma": "/m/01h7lh", "baseball": "/m/018jz"}

# ---------------------------------------------------------------
# 5. 이벤트 달력 (직접 만든 데이터)
# ---------------------------------------------------------------
EVENTS = [
    # type,          name,                         start,        end,          precision
    ("olympics",     "Athens 2004",               "2004-08-13", "2004-08-29", "day"),
    ("asian_games",  "Doha 2006",                 "2006-12-01", "2006-12-15", "day"),
    ("olympics",     "Beijing 2008",              "2008-08-08", "2008-08-24", "day"),
    ("asian_games",  "Guangzhou 2010",            "2010-11-12", "2010-11-27", "day"),
    ("olympics",     "London 2012",               "2012-07-27", "2012-08-12", "day"),
    ("asian_games",  "Incheon 2014",              "2014-09-19", "2014-10-04", "day"),
    ("olympics",     "Rio 2016",                  "2016-08-05", "2016-08-21", "day"),
    ("asian_games",  "Jakarta-Palembang 2018",    "2018-08-18", "2018-09-02", "day"),
    ("olympics",     "Tokyo 2020 (held 2021)",    "2021-07-23", "2021-08-08", "day"),
    ("asian_games",  "Hangzhou 2022 (held 2023)", "2023-09-23", "2023-10-08", "day"),
    ("olympics",     "Paris 2024",                "2024-07-26", "2024-08-11", "day"),
    ("asian_games",  "Aichi-Nagoya 2026",         "2026-09-19", "2026-10-04", "day"),
    ("milestone",    "UFC The Ultimate Fighter first broadcast", "2005-01-17", "2005-01-17", "day"),
]

# ---------------------------------------------------------------
# 6. 파일 경로
# ---------------------------------------------------------------
RAW_DIR = "data/raw"
GTRENDS_DIR = "data/raw/gtrends"        # 구글 트렌드에서 내려받은 CSV를 넣는 곳
PROCESSED_DIR = "data/processed"
INCOME_FILE = "data/star_income.csv"    # 직접 조사해서 만든 스타 선수 수입 표

# 위키피디아는 요청할 때 연락처가 담긴 User-Agent를 요구한다. (본인 이메일로 바꿔도 됨)
WIKI_USER_AGENT = "CAS1100-fencing-project/1.0 (student project; Yonsei University)"
