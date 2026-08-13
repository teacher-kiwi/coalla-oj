import functools
import json
import logging

from django.http import HttpResponse, QueryDict
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

logger = logging.getLogger("")


class APIError(Exception):
    def __init__(self, msg, err=None):
        self.err = err
        self.msg = msg
        super().__init__(err, msg)


class ContentType(object):
    json_request = "application/json"
    json_response = "application/json;charset=UTF-8"
    url_encoded_request = "application/x-www-form-urlencoded"
    binary_response = "application/octet-stream"


class JSONParser(object):
    content_type = ContentType.json_request

    @staticmethod
    def parse(body):
        return json.loads(body.decode("utf-8"))


class URLEncodedParser(object):
    content_type = ContentType.url_encoded_request

    @staticmethod
    def parse(body):
        return QueryDict(body)


class JSONResponse(object):
    content_type = ContentType.json_response

    @classmethod
    def response(cls, data):
        resp = HttpResponse(json.dumps(data), content_type=cls.content_type)
        resp.data = data
        return resp


class APIView(View):
    """모든 API view 의 부모. django-rest-framework 와 쓰는 법이 거의 같다.

     - request.data: 파싱된 json 또는 urlencoded 데이터(dict)
     - self.success / self.error / self.invalid_serializer 로 응답 형식을 통일한다
     - self.response 는 self.response_class 가 만든 HttpResponse 를 돌려준다
     - 요청 파서는 request_parsers 에 정의한다(현재 json, urlencoded 만 지원)
    """
    request_parsers = (JSONParser, URLEncodedParser)
    response_class = JSONResponse

    def _get_request_data(self, request):
        if request.method not in ["GET", "DELETE"]:
            body = request.body
            content_type = request.META.get("CONTENT_TYPE")
            if not content_type:
                raise ValueError("content_type is required")
            for parser in self.request_parsers:
                if content_type.startswith(parser.content_type):
                    break
            # break 로 빠져나오지 못했다는 뜻
            else:
                raise ValueError("unknown content_type '%s'" % content_type)
            if body:
                return parser.parse(body)
            return {}
        return request.GET

    def response(self, data):
        return self.response_class.response(data)

    def success(self, data=None):
        return self.response({"error": None, "data": data})

    def error(self, msg="error", err="error"):
        return self.response({"error": err, "data": msg})

    def extract_errors(self, errors, key="field"):
        if isinstance(errors, dict):
            if not errors:
                return key, "입력값이 올바르지 않습니다"
            key = list(errors.keys())[0]
            return self.extract_errors(errors.pop(key), key)
        elif isinstance(errors, list):
            return self.extract_errors(errors[0], key)

        return key, errors

    def invalid_serializer(self, serializer):
        key, error = self.extract_errors(serializer.errors)
        if key == "non_field_errors":
            msg = error
        else:
            msg = f"{key}: {error}"
        return self.error(err=f"invalid-{key}", msg=msg)

    def server_error(self):
        return self.error(err="server-error", msg="서버 오류가 발생했습니다")

    def paginate_data(self, request, query_set, object_serializer=None):
        """limit/offset 페이지네이션.

        :param query_set: QuerySet 또는 list 처럼 슬라이스할 수 있는 객체
        :param object_serializer: 직렬화기. None 이면 잘라낸 결과를 그대로 넣는다
        """
        try:
            limit = int(request.GET.get("limit", "10"))
        except ValueError:
            limit = 10
        if limit < 0 or limit > 250:
            limit = 10
        try:
            offset = int(request.GET.get("offset", "0"))
        except ValueError:
            offset = 0
        if offset < 0:
            offset = 0
        # 파이썬에서 걸러낸 결과(list)도 그대로 넘어올 수 있다. list.count() 는
        # 인자를 요구하므로 QuerySet 인지 보고 세는 방법을 고른다.
        count = len(query_set) if isinstance(query_set, (list, tuple)) else query_set.count()
        results = query_set[offset:offset + limit]
        if object_serializer:
            results = object_serializer(results, many=True).data
        data = {"results": results,
                "total": count}
        return data

    def dispatch(self, request, *args, **kwargs):
        if self.request_parsers:
            try:
                request.data = self._get_request_data(self.request)
            except ValueError as e:
                return self.error(err="invalid-request", msg=str(e))
        try:
            return super(APIView, self).dispatch(request, *args, **kwargs)
        except APIError as e:
            ret = {"msg": e.msg}
            if e.err:
                ret["err"] = e.err
            return self.error(**ret)
        except Exception as e:
            logger.exception(e)
            return self.server_error()


class CSRFExemptAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(CSRFExemptAPIView, self).dispatch(request, *args, **kwargs)


def validate_serializer(serializer):
    """
    @validate_serializer(TestSerializer)
    def post(self, request):
        return self.success(request.data)
    """
    def validate(view_method):
        @functools.wraps(view_method)
        def handle(*args, **kwargs):
            self = args[0]
            request = args[1]
            s = serializer(data=request.data)
            if s.is_valid():
                request.data = s.data
                request.serializer = s
                return view_method(*args, **kwargs)
            else:
                return self.invalid_serializer(s)

        return handle

    return validate
