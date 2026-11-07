"""바로 과제 학생 API (/api/hw/<코드>/...).

로그인을 보지 않는다. 학생은 session.py 의 출입증으로 알아본다.
"""
from django.db.models import Count, Q
from django.middleware.csrf import get_token

from judge.run import read_run, start_run
from judge.tasks import judge_task, run_code_task
from options.options import SysOptions
from submission.models import JudgeStatus, Submission
from submission.serializers import CreateSubmissionSerializer, RunCodeSerializer
from submission.views.oj import RunCodeAPI, build_run_spec
from utils.api import APIError, APIView, validate_serializer
from utils.cache import cache
from utils.shortcuts import int_or_none
from utils.throttling import TokenBucket

from .. import session
from ..models import Homework, HomeworkParticipant
from ..serializers import (HomeworkDetailSerializer, HomeworkSerializer, JoinHomeworkSerializer,
                           ParticipantSerializer, StudentProblemSerializer,
                           StudentSubmissionSerializer)

# 틀린 코드를 마구 넣어 보는 것을 막는다. 학교는 반 전체가 공인 IP 하나로 나가므로
# 넉넉하게 잡는다(반 전체가 오타를 내도 닿지 않게). 맞는 코드는 세지 않는다.
WRONG_CODE_LIMIT = 100
WRONG_CODE_WINDOW = 10 * 60
# 4자리 숫자는 자리(과제·번호)마다 센다. IP 로 세면 같은 반 학생이 함께 막힌다.
WRONG_PIN_LIMIT = 5
WRONG_PIN_WINDOW = 5 * 60


def _count(key, window):
    count = cache.get(key, 0) + 1
    cache.set(key, count, window)
    return count


def wrong_pin_key(homework, number):
    return f"homework:wrong_pin:{homework.id}:{number}"


def find_homework(request, code):
    key = f"homework:wrong_code:{request.ip}"
    if cache.get(key, 0) >= WRONG_CODE_LIMIT:
        raise APIError("코드를 너무 많이 틀렸습니다. 10분 뒤에 다시 시도해주세요")
    homework = Homework.objects.filter(code=code).first()
    if homework is None:
        _count(key, WRONG_CODE_WINDOW)
        raise APIError("없는 과제 코드입니다. 선생님께 받은 6자리 숫자를 확인해주세요")
    return homework


def problem_status(participant):
    """문제마다 몇 번 냈는지, 맞혔는지. {문제 id: {"attempts": n, "solved": bool}}"""
    rows = (Submission.objects.filter(user=participant.user).values("problem_id")
            .annotate(attempts=Count("id"),
                      accepted=Count("id", filter=Q(result=JudgeStatus.ACCEPTED))))
    return {row["problem_id"]: {"attempts": row["attempts"], "solved": row["accepted"] > 0}
            for row in rows}


def joined_data(homework, participant):
    return {"homework": HomeworkDetailSerializer(
                homework, context={"status": problem_status(participant)}).data,
            "participant": ParticipantSerializer(participant).data}


def allowed_languages(homework, problem):
    """이 과제에서 이 문제에 쓸 수 있는 언어. 교사가 고른 것과 문제가 허용한 것의 겹침.

    블록 코딩은 Python3 로 채점하므로 문제가 Python3 를 허용해야 한다.
    """
    return [language for language in homework.languages
            if language in problem.languages
            or (language == "Block Coding" and "Python3" in problem.languages)]


class HomeworkStudentAPI(APIView):
    """출입증이 있어야 쓰는 API 의 부모."""
    def participant(self, request, code):
        homework = find_homework(request, code)
        participant = session.current_participant(request, homework)
        if participant is None:
            raise APIError(err="hw-join-required", msg="먼저 입장해주세요")
        return participant

    @staticmethod
    def problem(participant, problem_id):
        problem = participant.homework.items.select_related("problem") \
            .filter(problem_id=int_or_none(problem_id)).first()
        if problem is None:
            raise APIError("이 과제에 없는 문제입니다")
        return problem.problem

    def writable(self, request, code, data):
        """제출·실행 전에 거치는 검사. (참가자, 문제) 를 돌려준다."""
        participant = self.participant(request, code)
        if participant.homework.is_ended:
            raise APIError("종료된 과제입니다. 결과만 볼 수 있습니다")
        problem = self.problem(participant, data["problem_id"])
        language = data["language"]
        if language not in allowed_languages(participant.homework, problem):
            raise APIError(f"{language} 언어는 이 과제에서 쓸 수 없습니다")
        return participant, problem


class HomeworkAPI(APIView):
    def get(self, request, code):
        """입장 화면이 보여 줄 것. 참가 전이라 제목과 상태만 준다."""
        # 입장(POST)에 쓸 CSRF 쿠키를 여기서 준다. 사이트 화면은 상단 메뉴가 /api/profile 을
        # 불러 쿠키를 받는데, 과제 화면은 메뉴를 감춰서 링크로 바로 들어오면 쿠키가 없다.
        get_token(request)
        return self.success(HomeworkSerializer(find_homework(request, code)).data)


class HomeworkJoinAPI(APIView):
    @validate_serializer(JoinHomeworkSerializer)
    def post(self, request, code):
        """처음이면 자리를 만들고, 이미 있는 번호면 4자리 숫자로 다시 들어온다.

        종료된 과제나 새 입장을 막은 과제도 이미 들어온 학생은 다시 들어올 수 있다.
        종료 뒤에는 자기 결과만 본다(제출은 제출 API 가 막는다).
        """
        homework = find_homework(request, code)
        # request.data 는 다시 문자열로 바뀌어 있다. 번호는 숫자로 다뤄야 "05" == "5" 다.
        data = request.serializer.validated_data
        participant = homework.participants.filter(number=data["number"]).first()
        if participant:
            key = wrong_pin_key(homework, participant.number)
            if cache.get(key, 0) >= WRONG_PIN_LIMIT:
                return self.error("4자리 숫자를 너무 많이 틀렸습니다. "
                                  "5분 뒤에 다시 하거나 선생님께 말씀드리세요")
            if not participant.pin_matches(data["pin"]):
                _count(key, WRONG_PIN_WINDOW)
                return self.error("이미 들어온 번호입니다. 4자리 숫자가 맞지 않습니다")
            cache.delete(key)
        elif homework.is_ended:
            return self.error("종료된 과제라 새로 들어갈 수 없습니다")
        elif homework.entry_locked:
            return self.error("선생님이 새 입장을 막아 두었습니다")
        elif not data.get("nickname"):
            return self.error("닉네임을 넣어주세요")
        else:
            participant = HomeworkParticipant.join(homework, data["number"], data["nickname"],
                                                   data["pin"])

        response = self.success(joined_data(homework, participant))
        session.issue(response, participant)
        return response


class HomeworkMeAPI(HomeworkStudentAPI):
    def get(self, request, code):
        """과제 화면이 처음 열릴 때. 출입증이 없으면(hw-join-required) 입장 화면으로 보낸다."""
        get_token(request)  # 위 HomeworkAPI.get 과 같은 이유
        participant = self.participant(request, code)
        return self.success(joined_data(participant.homework, participant))

    def delete(self, request, code):
        """이 기기에서 나가기. 자리와 기록은 남고 번호·4자리 숫자로 다시 들어올 수 있다."""
        homework = find_homework(request, code)
        response = self.success()
        session.revoke(response, homework)
        return response


class HomeworkProblemAPI(HomeworkStudentAPI):
    def get(self, request, code):
        """문제 본문과, 이어서 풀도록 마지막으로 낸 코드."""
        participant = self.participant(request, code)
        problem = self.problem(participant, request.GET.get("problem_id"))
        data = StudentProblemSerializer(problem).data
        data["languages"] = allowed_languages(participant.homework, problem)
        last = Submission.objects.filter(user=participant.user, problem=problem) \
            .order_by("-create_time").first()
        data["last_submission"] = StudentSubmissionSerializer(last).data if last else None
        return self.success(data)


class HomeworkSubmissionAPI(HomeworkStudentAPI):
    @validate_serializer(CreateSubmissionSerializer)
    def post(self, request, code):
        participant, problem = self.writable(request, code, request.data)
        bucket = TokenBucket(key=str(participant.user_id), redis_conn=cache,
                             **SysOptions.throttling["user"])
        can_consume, wait = bucket.consume()
        if not can_consume:
            return self.error(f"제출이 너무 잦습니다. {int(wait)}초 후에 다시 시도해주세요")
        data = request.data
        submission = Submission.objects.create(
            user=participant.user, problem=problem, language=data["language"],
            code=data["code"], ip=request.ip,
            blockly_state=data.get("blockly_state") or None)
        judge_task.send(submission.id, problem.id)
        return self.success({"submission_id": submission.id})

    def get(self, request, code):
        """내 제출 하나(채점이 끝났는지 볼 때) 또는 한 문제에 낸 내 제출 목록."""
        participant = self.participant(request, code)
        mine = Submission.objects.filter(user=participant.user)
        submission_id = request.GET.get("id")
        if submission_id:
            submission = mine.filter(id=submission_id).first()
            if submission is None:
                return self.error("제출 기록이 존재하지 않습니다")
            return self.success(StudentSubmissionSerializer(submission).data)
        problem = self.problem(participant, request.GET.get("problem_id"))
        return self.success(StudentSubmissionSerializer(
            mine.filter(problem=problem).order_by("-create_time"), many=True).data)


class HomeworkRunAPI(HomeworkStudentAPI):
    """제출하기 전에 자기 입력으로 돌려 보기. 문제 화면의 실행과 같다(judge/run.py)."""
    @validate_serializer(RunCodeSerializer)
    def post(self, request, code):
        participant, problem = self.writable(request, code, request.data)
        user_id = participant.user_id
        bucket = TokenBucket(key=f"run:{user_id}", redis_conn=cache, **RunCodeAPI.THROTTLE)
        can_consume, wait = bucket.consume()
        if not can_consume:
            return self.error(f"실행이 너무 잦습니다. {int(wait) + 1}초 후에 다시 눌러주세요")
        data = request.data
        token = start_run(user_id)
        run_code_task.send(token, user_id,
                           build_run_spec(problem, data["language"], data["code"], data.get("input")))
        return self.success({"token": token})

    def get(self, request, code):
        participant = self.participant(request, code)
        record = read_run(request.GET.get("token"), participant.user_id)
        if not record:
            return self.error("실행 기록을 찾을 수 없습니다. 다시 실행해주세요")
        return self.success({k: v for k, v in record.items() if k != "user_id"})
