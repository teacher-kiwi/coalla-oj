import time


class TokenBucket:
    """주의: 같은 key 에 대한 연산은 스레드 안전하지 않다."""
    def __init__(self, key, capacity, fill_rate, default_capacity, redis_conn):
        """
        :param capacity: 최대 용량
        :param fill_rate: 초당 채워지는 양
        :param default_capacity: 초기 용량
        :param redis_conn: redis 연결
        """
        self._key = key
        self._capacity = capacity
        self._fill_rate = fill_rate
        self._default_capacity = default_capacity
        self._redis_conn = redis_conn

        self._last_capacity_key = "last_capacity"
        self._last_timestamp_key = "last_timestamp"

    def _init_key(self):
        self._last_capacity = self._default_capacity
        now = time.time()
        self._last_timestamp = now
        return self._default_capacity, now

    @property
    def _last_capacity(self):
        last_capacity = self._redis_conn.hget(self._key, self._last_capacity_key)
        if last_capacity is None:
            return self._init_key()[0]
        else:
            return float(last_capacity)

    @_last_capacity.setter
    def _last_capacity(self, value):
        self._redis_conn.hset(self._key, self._last_capacity_key, value)

    @property
    def _last_timestamp(self):
        return float(self._redis_conn.hget(self._key, self._last_timestamp_key))

    @_last_timestamp.setter
    def _last_timestamp(self, value):
        self._redis_conn.hset(self._key, self._last_timestamp_key, value)

    def _try_to_fill(self, now):
        delta = self._fill_rate * (now - self._last_timestamp)
        return min(self._last_capacity + delta, self._capacity)

    def consume(self, num=1):
        """토큰 num 개를 소비하고 성공 여부를 돌려준다.

        :return: (성공 여부: bool, 다음까지 기다릴 시간: float)
        """
        if self._last_capacity >= num:
            self._last_capacity -= num
            return True, 0
        else:
            now = time.time()
            cur_num = self._try_to_fill(now)
            if cur_num >= num:
                self._last_capacity = cur_num - num
                self._last_timestamp = now
                return True, 0
            else:
                return False, (num - cur_num) / self._fill_rate
