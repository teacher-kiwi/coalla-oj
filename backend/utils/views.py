import os

from django.conf import settings
from PIL import Image, UnidentifiedImageError

from account.decorators import login_required
from account.serializers import ImageUploadForm
from utils.api import CSRFExemptAPIView
from utils.shortcuts import rand_str

# 문제 설명·공지·대회 안내에 넣는 그림. 글과 함께 매번 학생에게 전송되므로 작게 묶는다.
MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_SUFFIXES = (".gif", ".jpg", ".jpeg", ".bmp", ".png")


class ImageUploadAPI(CSRFExemptAPIView):
    """마크다운 편집기에서 그림을 올린다.

    /api/admin/* 밖에 둔다. 문제를 만드는 사람은 관리자와 교사 둘 다인데,
    교사는 미들웨어의 admin_role 검사에서 의도적으로 빠져 있어 그 아래 두면
    교사 출제 화면에서 그림을 올릴 수 없다.
    """
    request_parsers = ()

    @login_required
    def post(self, request):
        user = request.user
        if not (user.is_teacher() or user.is_admin_role()):
            return self.error("그림을 올릴 수 있는 권한이 없습니다")

        form = ImageUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.error("파일 내용이 올바르지 않습니다")
        image = form.cleaned_data["image"]

        if image.size > MAX_IMAGE_BYTES:
            return self.error(f"그림은 {MAX_IMAGE_BYTES // (1024 * 1024)}MB 까지 올릴 수 있습니다")
        suffix = os.path.splitext(image.name)[-1].lower()
        if suffix not in ALLOWED_SUFFIXES:
            return self.error("지원하지 않는 파일 형식입니다")
        # 확장자만 보면 이름만 .png 로 바꾼 아무 파일이 저장된다. 실제로 열리는지 본다.
        try:
            Image.open(image).verify()
        except (UnidentifiedImageError, OSError, ValueError):
            return self.error("그림 파일이 아닙니다")

        name = rand_str(10) + suffix
        with open(os.path.join(settings.UPLOAD_DIR, name), "wb") as saved:
            for chunk in image:
                saved.write(chunk)
        return self.success({"url": f"{settings.UPLOAD_PREFIX}/{name}"})
