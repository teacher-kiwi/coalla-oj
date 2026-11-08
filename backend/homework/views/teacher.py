"""바로 과제 교사 API (/api/teacher/hw...).

교사는 자기가 만든 과제만 본다. 최고관리자는 운영·점검을 위해 전부 본다
(수업 기능의 owned_class·owned_problem_set 과 같은 규칙).
"""
from django.db import transaction
from django.db.models import Count, Q
from django.utils.timezone import now

from account.decorators import teacher_required
from problem.models import Problem, ProblemVisibility
from submission.models import JudgeStatus, Submission
from utils.api import APIView, validate_serializer
from utils.cache import cache
from utils.shortcuts import int_or_none

from ..models import Homework, HomeworkParticipant, HomeworkProblem
from ..serializers import (CreateHomeworkSerializer, EditHomeworkSerializer,
                           EditParticipantSerializer, TeacherHomeworkDetailSerializer,
                           TeacherHomeworkSerializer, TeacherSubmissionSerializer)
from .oj import wrong_pin_key


def owned_homework(user, homework_id):
    homework_id = int_or_none(homework_id)
    if homework_id is None:
        return None
    homeworks = Homework.objects.annotate(
        participant_count=Count("participants", distinct=True),
        problem_count=Count("items", distinct=True))
    if not user.is_super_admin():
        homeworks = homeworks.filter(created_by=user)
    return homeworks.filter(id=homework_id).first()


def owned_participant(user, participant_id):
    participant = HomeworkParticipant.objects.select_related("homework") \
        .filter(id=int_or_none(participant_id)).first()
    if participant is None or not owned_homework(user, participant.homework_id):
        return None
    return participant


class TeacherHomeworkAPI(APIView):
    @teacher_required
    def get(self, request):
        homework_id = request.GET.get("id")
        if homework_id:
            homework = owned_homework(request.user, homework_id)
            if not homework:
                return self.error("과제가 존재하지 않습니다")
            return self.success(TeacherHomeworkDetailSerializer(homework).data)
        # 레포트: 진행 중인 것과 끝난 것을 한 목록에, 최근에 만든 것이 위로
        homeworks = Homework.objects.annotate(
            participant_count=Count("participants", distinct=True),
            problem_count=Count("items", distinct=True))
        if not request.user.is_super_admin():
            homeworks = homeworks.filter(created_by=request.user)
        return self.success(TeacherHomeworkSerializer(homeworks.order_by("-create_time"),
                                                      many=True).data)

    @validate_serializer(CreateHomeworkSerializer)
    @teacher_required
    def post(self, request):
        data = request.serializer.validated_data
        if data["end_time"] <= now():
            return self.error("마감 시각은 지금보다 뒤여야 합니다")
        problem_ids = list(dict.fromkeys(data["problems"]))
        # 문제집과 같은 규칙: 공개 문제와 내가 만든 문제. 끝나지 않은 대회에 담긴 문제는
        # 대회 전에 내용이 새어나가므로 뺀다.
        problems = {problem.id: problem for problem in Problem.objects.filter(
            Q(visibility=ProblemVisibility.public) | Q(created_by=request.user),
            id__in=problem_ids, visible=True)
            .exclude(contest_entries__contest__end_time__gte=now())}
        missing = [problem_id for problem_id in problem_ids if problem_id not in problems]
        if missing:
            numbers = ", ".join(map(str, missing))
            return self.error(f"담을 수 없는 문제가 있습니다: {numbers}번")

        with transaction.atomic():
            homework = Homework.objects.create(
                code=Homework.generate_code(), title=data["title"].strip(),
                created_by=request.user, languages=data["languages"], end_time=data["end_time"])
            HomeworkProblem.objects.bulk_create([
                HomeworkProblem(homework=homework, problem=problems[problem_id], order=order)
                for order, problem_id in enumerate(problem_ids)])
        return self.success(TeacherHomeworkDetailSerializer(
            owned_homework(request.user, homework.id)).data)

    @validate_serializer(EditHomeworkSerializer)
    @teacher_required
    def put(self, request):
        data = request.serializer.validated_data
        homework = owned_homework(request.user, data["id"])
        if not homework:
            return self.error("과제가 존재하지 않습니다")
        fields = []
        if "title" in data:
            if not data["title"].strip():
                return self.error("제목을 입력하세요")
            homework.title = data["title"].strip()
            fields.append("title")
        if "end_time" in data or "entry_locked" in data or data.get("end"):
            # 끝난 과제를 다시 열지는 않는다. 그동안 결과가 레포트에 굳어 있기 때문이다.
            if homework.is_ended:
                return self.error("이미 종료된 과제입니다")
        if "end_time" in data:
            if data["end_time"] <= now():
                return self.error("마감 시각은 지금보다 뒤여야 합니다. 바로 끝내려면 '종료'를 누르세요")
            homework.end_time = data["end_time"]
            fields.append("end_time")
        if "entry_locked" in data:
            homework.entry_locked = data["entry_locked"]
            fields.append("entry_locked")
        if data.get("end"):
            homework.ended_at = now()
            fields.append("ended_at")
        if fields:
            homework.save(update_fields=fields)
        return self.success(TeacherHomeworkDetailSerializer(homework).data)


class TeacherHomeworkBoardAPI(APIView):
    @teacher_required
    def get(self, request):
        """현황판: 학생 × 문제. 칸마다 몇 번 냈는지, 맞혔는지, 마지막 결과."""
        homework = owned_homework(request.user, request.GET.get("id"))
        if not homework:
            return self.error("과제가 존재하지 않습니다")
        participants = list(homework.participants.all())
        problems = homework.problems()
        cells = {}
        last_submit = {}
        rows = Submission.objects.filter(
            user_id__in=[p.user_id for p in participants],
            problem_id__in=[problem.id for problem in problems]) \
            .order_by("create_time").values("user_id", "problem_id", "result", "create_time")
        for row in rows:
            cell = cells.setdefault((row["user_id"], row["problem_id"]),
                                    {"attempts": 0, "solved": False, "last_result": None})
            cell["attempts"] += 1
            cell["solved"] = cell["solved"] or row["result"] == JudgeStatus.ACCEPTED
            cell["last_result"] = row["result"]
            last_submit[row["user_id"]] = row["create_time"]

        board = []
        for participant in participants:
            board.append({
                "id": participant.id, "number": participant.number,
                "nickname": participant.nickname, "pin": participant.pin,
                "join_time": participant.join_time,
                "last_submit_time": last_submit.get(participant.user_id),
                "cells": {str(problem.id): cells.get((participant.user_id, problem.id))
                          for problem in problems}})
        data = TeacherHomeworkDetailSerializer(homework).data
        for problem in data["problems"]:
            problem["solved_count"] = sum(
                1 for row in board if (row["cells"][str(problem["id"])] or {}).get("solved"))
        # DRF 를 거치지 않은 시각은 직렬화기로 바꿔 둔다(JSON 이 datetime 을 못 싣는다)
        field = TeacherSubmissionSerializer().fields["create_time"]
        for row in board:
            row["join_time"] = field.to_representation(row["join_time"])
            if row["last_submit_time"]:
                row["last_submit_time"] = field.to_representation(row["last_submit_time"])
        return self.success({"homework": data, "participants": board})


class TeacherHomeworkSubmissionAPI(APIView):
    @teacher_required
    def get(self, request):
        """현황판 칸을 눌렀을 때: 그 학생이 그 문제에 낸 것 전부(코드 포함)."""
        participant = owned_participant(request.user, request.GET.get("participant_id"))
        if not participant:
            return self.error("참가자가 존재하지 않습니다")
        submissions = Submission.objects.filter(
            user_id=participant.user_id, problem_id=int_or_none(request.GET.get("problem_id"))) \
            .order_by("-create_time")
        return self.success(TeacherSubmissionSerializer(submissions, many=True).data)


class TeacherHomeworkParticipantAPI(APIView):
    @validate_serializer(EditParticipantSerializer)
    @teacher_required
    def put(self, request):
        data = request.serializer.validated_data
        participant = owned_participant(request.user, data["id"])
        if not participant:
            return self.error("참가자가 존재하지 않습니다")
        fields = []
        if "nickname" in data:
            if not data["nickname"].strip():
                return self.error("닉네임을 넣어주세요")
            participant.nickname = data["nickname"].strip()
            fields.append("nickname")
        if "pin" in data:
            participant.pin = data["pin"]
            fields.append("pin")
            # 틀려서 잠긴 자리라면 새 숫자로 바로 들어올 수 있게 푼다
            cache.delete(wrong_pin_key(participant.homework, participant.number))
        if fields:
            participant.save(update_fields=fields)
        return self.success()

    @teacher_required
    def delete(self, request):
        """내보내기. 그 학생의 임시 계정과 제출이 함께 지워지고 번호가 빈다."""
        participant = owned_participant(request.user, request.GET.get("id"))
        if not participant:
            return self.error("참가자가 존재하지 않습니다")
        participant.delete()
        return self.success()
