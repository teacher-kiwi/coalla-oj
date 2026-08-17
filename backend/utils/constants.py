class Choices:
    @classmethod
    def choices(cls):
        d = cls.__dict__
        return [d[item] for item in d.keys() if not item.startswith("__")]


class ContestType:
    PUBLIC_CONTEST = "Public"
    PASSWORD_PROTECTED_CONTEST = "Password Protected"


class ContestStatus:
    CONTEST_NOT_START = "1"
    CONTEST_ENDED = "-1"
    CONTEST_UNDERWAY = "0"


class ContestRuleType(Choices):
    ACM = "ACM"
    OI = "OI"


class CacheKey:
    waiting_queue = "waiting_queue"
    contest_rank_cache = "contest_rank_cache"
    website_config = "website_config"


class Difficulty(Choices):
    """문제 난이도 6단계.

    DB 에는 L1~L6 만 저장하고 사람이 읽는 이름(입문·기초·…)은 화면에서 붙인다.
    이름을 바꿔도 데이터를 건드리지 않아도 되고, 순서도 값에서 바로 드러난다.
    """
    L1 = "L1"   # 입문
    L2 = "L2"   # 기초
    L3 = "L3"   # 기본
    L4 = "L4"   # 응용
    L5 = "L5"   # 심화
    L6 = "L6"   # 도전


CONTEST_PASSWORD_SESSION_KEY = "contest_password"
