"""마크다운 편집기의 그림 올리기.

문제를 만드는 사람은 관리자와 교사 둘 다인데, 교사는 미들웨어의 admin_role 검사에서
의도적으로 빠져 있다. 그래서 이 경로는 /api/admin/* 밖에 두고 권한을 직접 본다.
"""
import io
import os
import shutil

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from utils.api.tests import APITestCase

from .views import MAX_IMAGE_BYTES


def png_bytes(size=(4, 4)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


class ImageUploadAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("image_upload_api")
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    def _upload(self, content=None, name="a.png"):
        content = png_bytes() if content is None else content
        return self.client.post(self.url,
                                data={"image": SimpleUploadedFile(name, content)},
                                format="multipart")

    def _saved_path(self, resp):
        name = resp.data["data"]["url"].rsplit("/", 1)[-1]
        path = os.path.join(settings.UPLOAD_DIR, name)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_requires_login(self):
        self.assertFailed(self._upload())

    def test_teacher_can_upload(self):
        self.create_teacher()
        resp = self._upload()
        self.assertSuccess(resp)
        self.assertTrue(resp.data["data"]["url"].startswith(settings.UPLOAD_PREFIX))
        self.assertTrue(os.path.isfile(self._saved_path(resp)))

    def test_admin_can_upload(self):
        self.create_admin()
        self.assertSuccess(self._upload())

    def test_student_cannot_upload(self):
        """학생에게는 편집기가 없다. 올릴 이유도 권한도 없다."""
        self.create_user("학생", "test123")
        self.assertFailed(self._upload(), "그림을 올릴 수 있는 권한이 없습니다")

    def test_rejects_unsupported_suffix(self):
        self.create_teacher()
        self.assertFailed(self._upload(name="a.txt"), "지원하지 않는 파일 형식입니다")

    def test_rejects_too_large(self):
        self.create_teacher()
        resp = self._upload(content=b"x" * (MAX_IMAGE_BYTES + 1))
        self.assertFailed(resp)
        self.assertIn("MB 까지", resp.data["data"])

    def test_rejects_a_file_that_is_not_an_image(self):
        """확장자만 보면 이름만 .png 로 바꾼 아무 파일이 저장된다."""
        self.create_teacher()
        self.assertFailed(self._upload(content=b"not an image at all"),
                          "그림 파일이 아닙니다")
        self.assertEqual(os.listdir(settings.UPLOAD_DIR), [])

    def test_saved_file_keeps_the_original_bytes(self):
        """올린 그림이 잘리거나 바뀌지 않고 그대로 저장돼야 한다.

        검증하며 스트림을 읽어도 Django 의 File.chunks() 가 앞으로 되돌리므로
        따로 seek 할 필요가 없다. 그 전제가 깨지면 이 테스트가 잡는다.
        """
        self.create_teacher()
        content = png_bytes(size=(8, 8))
        resp = self._upload(content=content)
        self.assertSuccess(resp)
        with open(self._saved_path(resp), "rb") as saved:
            self.assertEqual(saved.read(), content)

    def tearDown(self):
        shutil.rmtree(settings.UPLOAD_DIR, ignore_errors=True)
