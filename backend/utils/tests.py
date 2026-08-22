from django.test import SimpleTestCase

from utils.models import RichTextField
from utils.xss_filter import clean_html


class CleanHtmlTest(SimpleTestCase):
    def test_keeps_normal_rich_text(self):
        """편집기가 내보내는 평범한 문제 설명은 그대로 통과한다."""
        html = ("<p>수를 <strong>2</strong>로 나눈 나머지를 출력하시오.</p>"
                "<ul><li>첫째 줄에 정수 N</li></ul>"
                "<blockquote>예시</blockquote>")
        self.assertEqual(clean_html(html), html)

    def test_keeps_code_block_language_class(self):
        """문법 강조용 lang-* 클래스는 남긴다(markdown-it 이 붙인다)."""
        html = '<pre><code class="lang-python">a = 1</code></pre>'
        self.assertEqual(clean_html(html), html)

    def test_drops_other_classes(self):
        """class 는 문법 강조용으로만 열어둔 것이라 다른 값은 뺀다."""
        self.assertEqual(clean_html('<code class="el-button">x</code>'),
                         "<code>x</code>")

    def test_drops_script_tag(self):
        cleaned = clean_html("<p>앞</p><script>alert(1)</script>")
        self.assertNotIn("<script", cleaned)

    def test_drops_event_handler(self):
        self.assertNotIn("onerror", clean_html('<img src="x" onerror="alert(1)">'))

    def test_drops_javascript_url(self):
        cleaned = clean_html('<a href="javascript:alert(1)">클릭</a>')
        self.assertNotIn("javascript:", cleaned)

    def test_drops_style_attribute(self):
        """화면 전체를 덮는 가짜 UI 를 만들 수 있어 style 은 통째로 막는다."""
        cleaned = clean_html('<p style="position:fixed;top:0;width:100vw;height:100vh">'
                             "가짜 로그인</p>")
        self.assertEqual(cleaned, "<p>가짜 로그인</p>")

    def test_adds_noopener_to_links(self):
        """target=_blank 링크가 원래 탭을 바꿔치기하지 못하게 한다."""
        cleaned = clean_html('<a href="https://example.com" target="_blank">링크</a>')
        self.assertIn('rel="noopener noreferrer"', cleaned)

    def test_handles_none(self):
        self.assertEqual(clean_html(None), "")


class RichTextFieldTest(SimpleTestCase):
    def test_cleans_on_save(self):
        """모델 필드를 거치는 값은 어느 경로로 저장하든 걸러진다."""
        prepared = RichTextField().get_prep_value('<p onclick="alert(1)">본문</p>')
        self.assertEqual(prepared, "<p>본문</p>")
