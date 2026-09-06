"""교사가 자기 학급을 대상으로 여는 대회.

관리자 대회(views/admin.py)와 나누는 이유는 받는 값이 다르기 때문이다. 교사는
비밀번호·IP 제한·규칙 유형·공개 여부를 정하지 않는다. 참가 범위는 학급 배포로
정해지고 나머지는 수업에 맞는 값으로 서버가 고정한다.

순위 화면은 관리자 대회와 같은 것을 그대로 쓴다.
"""
from django.db import IntegrityError
from django.db.models import Q

from account.decorators import teacher_required
from account.views.teacher import owned_class
from problem.models import (ContestProblem, MAX_CONTEST_PROBLEMS, Problem,
                            ProblemVisibility)
from utils.api import APIView, validate_serializer
from utils.constants import ContestRuleType, ContestStatus
from utils.shortcuts import int_or_none
from ..models import ClassContestAssignment, Contest, ContestAnnouncement
from ..serializers import (AddClassContestProblemSerializer, AssignClassContestSerializer,
                           ClassContestAssignmentSerializer, ClassContestSerializer,
                           ContestAnnouncementSerializer,
                           CreateClassContestAnnouncementSerializer,
                           CreateClassContestSerializer,
                           EditClassContestAnnouncementSerializer, EditClassContestSerializer)


def owned_contest(user, contest_id):
    """내가 연 학급 대회만 돌려준다. 아니면 None."""
    contest_id = int_or_none(contest_id)
    if contest_id is None:
        return None
    return Contest.objects.filter(id=contest_id, created_by=user,
                                  is_class_contest=True).first()


class TeacherContestAPI(APIView):
    @teacher_required
    def get(self, request):
        contest_id = int_or_none(request.GET.get("id"))
        if contest_id is not None:
            contest = owned_contest(request.user, contest_id)
            if not contest:
                return self.error("대회가 존재하지 않습니다")
            return self.success(ClassContestSerializer(contest).data)

        contests = Contest.objects.filter(created_by=request.user, is_class_contest=True)
        return self.success(ClassContestSerializer(contests, many=True).data)

    @validate_serializer(CreateClassContestSerializer)
    @teacher_required
    def post(self, request):
        data = request.serializer.validated_data
        contest = Contest.objects.create(
            title=data["title"],
            description=data["description"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            created_by=request.user,
            is_class_contest=True,
            # 수업용 고정값. 참가 범위는 학급 배포가 정하므로 비밀번호를 쓰지 않는다.
            rule_type=ContestRuleType.ACM,
            real_time_rank=True,
            password=None,
            visible=True,
            allowed_ip_ranges=[])
        return self.success(ClassContestSerializer(contest).data)

    @validate_serializer(EditClassContestSerializer)
    @teacher_required
    def put(self, request):
        data = request.serializer.validated_data
        contest = owned_contest(request.user, data["id"])
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        for field in ("title", "description", "start_time", "end_time"):
            setattr(contest, field, data[field])
        contest.save()
        return self.success(ClassContestSerializer(contest).data)

    @teacher_required
    def delete(self, request):
        contest = owned_contest(request.user, request.GET.get("id"))
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        if contest.status == ContestStatus.CONTEST_UNDERWAY:
            return self.error("진행 중인 대회는 삭제할 수 없습니다")
        # 대회 문제와 제출, 순위가 함께 사라진다(모두 CASCADE)
        contest.delete()
        return self.success()


class TeacherContestAssignmentAPI(APIView):
    """대회를 학급에 배포한다. 배포받은 학급의 학생만 대회에 들어갈 수 있다."""
    @teacher_required
    def get(self, request):
        contest = owned_contest(request.user, request.GET.get("contest_id"))
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        assignments = contest.assignments.select_related("school_class__school")
        return self.success(ClassContestAssignmentSerializer(assignments, many=True).data)

    @validate_serializer(AssignClassContestSerializer)
    @teacher_required
    def post(self, request):
        contest = owned_contest(request.user, request.data["contest_id"])
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        school_class = owned_class(request.user, request.data["class_id"])
        if not school_class:
            return self.error("학급이 존재하지 않습니다")
        assignment, created = ClassContestAssignment.objects.get_or_create(
            contest=contest, school_class=school_class)
        if not created:
            return self.error("이미 배포한 학급입니다")
        return self.success(ClassContestAssignmentSerializer(assignment).data)

    @teacher_required
    def delete(self, request):
        contest = owned_contest(request.user, request.GET.get("contest_id"))
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        class_id = int_or_none(request.GET.get("class_id"))
        if class_id is None:
            return self.error("잘못된 요청입니다. class_id가 필요합니다")
        ClassContestAssignment.objects.filter(contest=contest,
                                              school_class_id=class_id).delete()
        return self.success()


class TeacherContestProblemAPI(APIView):
    """대회에 문제를 넣고 뺀다.

    복사하지 않고 ContestProblem 으로 가리키기만 한다. 한 문제가 여러 대회에
    담길 수 있고, 문제를 고치면 대회에도 그대로 반영된다.
    """
    @teacher_required
    def get(self, request):
        contest = owned_contest(request.user, request.GET.get("contest_id"))
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        entries = (ContestProblem.objects.filter(contest=contest)
                   .select_related("problem").order_by("order"))
        return self.success([{"id": e.problem_id, "display_id": e.label,
                              "title": e.problem.title,
                              "difficulty": e.problem.difficulty} for e in entries])

    @validate_serializer(AddClassContestProblemSerializer)
    @teacher_required
    def post(self, request):
        """고른 문제를 대회 끝에 넣는다. 이미 담긴 문제는 조용히 건너뛴다.

        문제집(ProblemSetProblemAPI.post)과 같은 방식이다. 화면이 여러 개를
        한 번에 고르므로 하나씩 오류를 내면 어디까지 들어갔는지 알 수 없다.
        """
        contest = owned_contest(request.user, request.data["contest_id"])
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        if contest.status != ContestStatus.CONTEST_NOT_START:
            return self.error("시작한 대회에는 문제를 넣을 수 없습니다")

        # 내가 만든 문제와 공개 문제만, 그리고 대회와 규칙이 같은 것만 넣을 수 있다
        problems = Problem.objects.filter(
            Q(created_by=request.user) | Q(visibility=ProblemVisibility.public),
            id__in=request.data["problems"], rule_type=contest.rule_type)
        if not problems:
            return self.error("문제가 존재하지 않습니다")

        existing = set(ContestProblem.objects.filter(contest=contest)
                       .values_list("problem_id", flat=True))
        order = ContestProblem.next_order(contest)
        entries = []
        for problem in problems:
            if problem.id in existing:
                continue
            entries.append(ContestProblem(contest=contest, problem=problem, order=order))
            order += 1

        # 한 개라도 넘치면 아무것도 넣지 않는다. 일부만 들어가면 무엇이 빠졌는지 모른다.
        if order - 1 > MAX_CONTEST_PROBLEMS:
            return self.error(f"대회에는 문제를 {MAX_CONTEST_PROBLEMS}개까지 넣을 수 있습니다")

        try:
            ContestProblem.objects.bulk_create(entries)
        except IntegrityError:
            # 자리를 읽는 것과 저장하는 것 사이에 다른 요청이 같은 자리를 먼저 썼다
            # (버튼 두 번 누르기)
            return self.error("문제를 넣지 못했습니다. 다시 시도해주세요")
        return self.success({"added": len(entries)})

    @teacher_required
    def delete(self, request):
        contest = owned_contest(request.user, request.GET.get("contest_id"))
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        if contest.status != ContestStatus.CONTEST_NOT_START:
            return self.error("시작한 대회에서는 문제를 뺄 수 없습니다")
        problem_id = int_or_none(request.GET.get("problem_id"))
        if problem_id is None:
            return self.error("잘못된 요청입니다. problem_id가 필요합니다")
        # 문제 자체는 남는다. 대회에서 빼기만 한다.
        ContestProblem.objects.filter(contest=contest, problem_id=problem_id).delete()
        # 가운데를 빼면 라벨이 A, C 로 벌어지므로 다시 붙인다
        ContestProblem.repack(contest)
        return self.success()


class TeacherContestAnnouncementAPI(APIView):
    """교사가 자기 대회에 올리는 공지.

    수업 중에 "3번 문제 입력 조건이 잘못됐습니다" 같은 것을 바로 알리는 용도다.
    학생이 읽는 쪽은 관리자 대회와 같은 API 를 쓴다(ContestAnnouncementListAPI).
    """
    @teacher_required
    def get(self, request):
        contest = owned_contest(request.user, request.GET.get("contest_id"))
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        announcements = (ContestAnnouncement.objects.filter(contest=contest)
                         .select_related("created_by"))
        return self.success(ContestAnnouncementSerializer(announcements, many=True).data)

    @validate_serializer(CreateClassContestAnnouncementSerializer)
    @teacher_required
    def post(self, request):
        data = request.data
        contest = owned_contest(request.user, data["contest_id"])
        if not contest:
            return self.error("대회가 존재하지 않습니다")
        announcement = ContestAnnouncement.objects.create(
            contest=contest, title=data["title"], content=data["content"],
            created_by=request.user)
        return self.success(ContestAnnouncementSerializer(announcement).data)

    @validate_serializer(EditClassContestAnnouncementSerializer)
    @teacher_required
    def put(self, request):
        data = request.data
        announcement = self._owned(request.user, data["id"])
        if not announcement:
            return self.error("공지가 존재하지 않습니다")
        announcement.title = data["title"]
        announcement.content = data["content"]
        announcement.save(update_fields=["title", "content"])
        return self.success(ContestAnnouncementSerializer(announcement).data)

    @teacher_required
    def delete(self, request):
        announcement = self._owned(request.user, request.GET.get("id"))
        if not announcement:
            return self.error("공지가 존재하지 않습니다")
        announcement.delete()
        return self.success()

    @staticmethod
    def _owned(user, announcement_id):
        """내가 연 학급 대회의 공지만 돌려준다. 아니면 None."""
        announcement_id = int_or_none(announcement_id)
        if announcement_id is None:
            return None
        return ContestAnnouncement.objects.filter(
            id=announcement_id, contest__created_by=user,
            contest__is_class_contest=True).first()
