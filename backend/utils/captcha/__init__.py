"""
Copyright 2013 TY<tianyu0915@gmail.com>
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import time
import random

from PIL import Image, ImageDraw, ImageFont


class Captcha(object):
    def __init__(self, request):
        """여러 속성을 초기화한다."""
        self.django_request = request
        self.session_key = "_django_captcha_key"
        self.captcha_expires_time = "_django_captcha_expires_time"

        # 보안 문자 이미지 크기
        self.img_width = 90
        self.img_height = 30

    def _get_font_size(self, code):
        """이미지 높이의 80% 를 글자 크기로 쓴다."""
        s1 = int(self.img_height * 0.8)
        s2 = int(self.img_width / len(code))
        return int(min((s1, s2)) + max((s1, s2)) * 0.05)

    def _set_answer(self, answer):
        """정답과 만료 시각을 저장한다."""
        self.django_request.session[self.session_key] = str(answer)
        self.django_request.session[self.captcha_expires_time] = time.time() + 60

    def _make_code(self):
        """임의의 숫자 또는 문자열을 만든다."""
        string = random.sample("abcdefghkmnpqrstuvwxyzABCDEFGHGKMNOPQRSTUVWXYZ23456789", 4)
        self._set_answer("".join(string))
        return string

    def get(self):
        """보안 문자 이미지를 만들어 bytes 로 돌려준다."""
        background = (random.randrange(200, 255), random.randrange(200, 255), random.randrange(200, 255))
        code_color = (random.randrange(0, 50), random.randrange(0, 50), random.randrange(0, 50), 255)

        font_path = os.path.join(os.path.normpath(os.path.dirname(__file__)), "timesbi.ttf")

        image = Image.new("RGB", (self.img_width, self.img_height), background)
        code = self._make_code()
        font_size = self._get_font_size(code)
        draw = ImageDraw.Draw(image)

        # 첫 글자의 x 좌표
        x = random.randrange(int(font_size * 0.3), int(font_size * 0.5))

        for i in code:
            # 글자 y 좌표
            y = random.randrange(1, 7)
            # 글자 크기를 무작위로
            font = ImageFont.truetype(font_path.replace("\\", "/"), font_size + random.randrange(-3, 7))
            draw.text((x, y), i, font=font, fill=code_color)
            # 글자 간격을 무작위로. 글자가 겹치면 자동 인식률이 떨어진다
            x += font_size * random.randrange(6, 8) / 10

        self.django_request.session[self.session_key] = "".join(code)
        return image

    def check(self, code):
        """사용자가 입력한 보안 문자가 맞는지 검사한다."""
        _code = self.django_request.session.get(self.session_key) or ""
        if not _code:
            return False
        expires_time = self.django_request.session.get(self.captcha_expires_time) or 0
        # 검증 후 이전 보안 문자를 지우지 않으면 같은 값으로 여러 번 통과할 수 있다
        del self.django_request.session[self.session_key]
        del self.django_request.session[self.captcha_expires_time]
        if _code.lower() == str(code).lower() and time.time() < expires_time:
            return True
        else:
            return False
