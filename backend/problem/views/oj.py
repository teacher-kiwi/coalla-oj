from django.db.models import Q, Count
from utils.api import APIView
from account.decorators import check_contest_permission, login_required
from ..models import (can_access_problem, ProblemTag, Problem, ProblemRuleType,
                      ProblemSet, ProblemSetAssignment, ProblemVisibility)
from ..serializers import (ProblemBriefSerializer, ProblemListSerializer, ProblemSerializer,
                           TagSerializer, ProblemSafeSerializer)
from ..utils import filter_problem_tags_by_keyword
from contest.models import ContestRuleType
from submission.models import JudgeStatus


class ProblemTagAPI(APIView):
    def get(self, request):
        keyword = request.GET.get("keyword")
        # 기본은 "문제가 붙어 있는 태그"만 준다. 문제 목록의 태그 사이드바에
        # 아무 문제도 없는 태그가 줄줄이 보이면 고를 수 없는 항목만 늘어난다.
        # 출제 화면처럼 "붙일 태그를 고르는" 곳은 all=1 로 전체를 받아야 한다.
        if request.GET.get("all") == "1":
            tags = ProblemTag.objects.order_by("name")
        else:
            tags = (ProblemTag.objects.annotate(problem_count=Count("problem"))
                    .filter(problem_count__gt=0))
        if keyword:
            tags = filter_problem_tags_by_keyword(tags, keyword)
        return self.success(TagSerializer(tags, many=True).data)


class PickOneAPI(APIView):
    def get(self, request):
        problem = (Problem.objects.filter(contest_id__isnull=True, visible=True,
                                          visibility=ProblemVisibility.public)
                   .order_by("?").first())
        if problem is None:
            return self.error("선택할 문제가 없습니다")
        return self.success(problem._id)


class ProblemAPI(APIView):
    @staticmethod
    def _add_problem_status(request, queryset_values):
        if request.user.is_authenticated:
            profile = request.user.userprofile
            acm_problems_status = profile.acm_problems_status.get("problems", {})
            oi_problems_status = profile.oi_problems_status.get("problems", {})
            results = queryset_values.get("results")
            if results is not None:
                problems = results
            else:
                problems = [queryset_values, ]
            for problem in problems:
                if problem["rule_type"] == ProblemRuleType.ACM:
                    problem["my_status"] = acm_problems_status.get(str(problem["id"]), {}).get("status")
                else:
                    problem["my_status"] = oi_problems_status.get(str(problem["id"]), {}).get("status")

    def get(self, request):
        problem_id = request.GET.get("problem_id")
        if problem_id:
            problem = (Problem.objects.select_related("created_by")
                       .filter(_id=problem_id, contest_id__isnull=True).first())
            # 비공개 문제는 만든 교사와 배포받은 학급 학생만 열 수 있다.
            # 없는 문제와 권한 없는 문제를 같은 문구로 돌려준다(존재 여부를 알리지 않는다).
            if problem is None or not can_access_problem(problem, request.user):
                return self.error("문제가 존재하지 않습니다")
            problem_data = ProblemSerializer(problem).data
            self._add_problem_status(request, problem_data)
            return self.success(problem_data)

        limit = request.GET.get("limit")
        if not limit:
            return self.error("limit 값이 필요합니다")

        problems = Problem.objects.prefetch_related("tags").filter(
            contest_id__isnull=True, visible=True)
        # 교사가 문제집에 담을 문제를 고르는 화면은 "공개 문제 + 내가 만든 문제"를 함께 본다.
        # 그 밖의 경로(학생 문제 목록 등)는 공개 문제만 본다.
        if request.GET.get("mine") == "1" and request.user.is_authenticated:
            problems = problems.filter(Q(visibility=ProblemVisibility.public)
                                       | Q(created_by=request.user))
        else:
            problems = problems.filter(visibility=ProblemVisibility.public)
        tag_text = request.GET.get("tag")
        if tag_text:
            problems = problems.filter(tags__name=tag_text)

        keyword = request.GET.get("keyword", "").strip()
        if keyword:
            problems = problems.filter(Q(title__icontains=keyword) | Q(_id__icontains=keyword))

        difficulty = request.GET.get("difficulty")
        if difficulty:
            problems = problems.filter(difficulty=difficulty)
        data = self.paginate_data(request, problems, ProblemListSerializer)
        self._add_problem_status(request, data)
        return self.success(data)


class ContestProblemAPI(APIView):
    def _add_problem_status(self, request, queryset_values):
        if request.user.is_authenticated:
            profile = request.user.userprofile
            if self.contest.rule_type == ContestRuleType.ACM:
                problems_status = profile.acm_problems_status.get("contest_problems", {})
            else:
                problems_status = profile.oi_problems_status.get("contest_problems", {})
            for problem in queryset_values:
                problem["my_status"] = problems_status.get(str(problem["id"]), {}).get("status")

    @check_contest_permission(check_type="problems")
    def get(self, request):
        problem_id = request.GET.get("problem_id")
        if problem_id:
            try:
                problem = Problem.objects.select_related("created_by").get(_id=problem_id,
                                                                           contest=self.contest,
                                                                           visible=True)
            except Problem.DoesNotExist:
                return self.error("문제가 존재하지 않습니다.")
            if self.contest.problem_details_permission(request.user):
                problem_data = ProblemSerializer(problem).data
                self._add_problem_status(request, [problem_data, ])
            else:
                problem_data = ProblemSafeSerializer(problem).data
            return self.success(problem_data)

        contest_problems = Problem.objects.select_related("created_by").filter(contest=self.contest, visible=True)
        if self.contest.problem_details_permission(request.user):
            data = ProblemSerializer(contest_problems, many=True).data
            self._add_problem_status(request, data)
        else:
            data = ProblemSafeSerializer(contest_problems, many=True).data
        return self.success(data)


def _solved_status_map(user):
    """푼 문제 판정용 맵. 문제 목록 API 와 같은 출처(UserProfile)를 쓴다.

    ACM/OI 를 합쳐서 본다. 문제집은 규칙과 무관하게 "풀었는지"만 보여준다.
    """
    profile = user.userprofile
    status = {}
    status.update(profile.acm_problems_status.get("problems", {}))
    status.update(profile.oi_problems_status.get("problems", {}))
    return status


def _is_solved(status_map, problem_id):
    return status_map.get(str(problem_id), {}).get("status") == JudgeStatus.ACCEPTED


class ProblemSetListAPI(APIView):
    """내 학급에 배포된 문제집 목록.

    학급 소속이 없으면(개인 학생·교사) 빈 목록이다. 화면에서 메뉴를 감추더라도
    권한 판단은 여기서 한 번 더 한다.
    """
    @login_required
    def get(self, request):
        assignments = (ProblemSetAssignment.objects
                       .filter(school_class__memberships__student=request.user, is_open=True)
                       .select_related("problem_set", "school_class__school")
                       .prefetch_related("problem_set__items"))
        status_map = _solved_status_map(request.user)

        data = []
        for assignment in assignments:
            problem_ids = [item.problem_id for item in assignment.problem_set.items.all()]
            data.append({
                "id": assignment.problem_set_id,
                "title": assignment.problem_set.title,
                "description": assignment.problem_set.description,
                "class_name": f"{assignment.school_class.school.name} "
                              f"{assignment.school_class.display_name}",
                # 응답은 json.dumps 를 그대로 타므로(직렬화기 미사용) 문자열로 바꿔서 넘긴다
                "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
                "problem_count": len(problem_ids),
                "solved_count": sum(1 for pid in problem_ids if _is_solved(status_map, pid)),
            })
        return self.success(data)


class ProblemSetDetailAPI(APIView):
    """문제집 상세. 내 학급에 배포된 것만 열람할 수 있다.

    마감일이 지나도 잠그지 않는다. 문제집에 담기는 것은 어차피 공개 문제라
    제출을 막아도 문제 목록에서 그대로 풀 수 있고, 늦게라도 푸는 것을 막을 이유가 없다.
    마감일은 화면 표시와 교사의 진도 확인용이다.
    """
    @login_required
    def get(self, request):
        problem_set_id = request.GET.get("id")
        try:
            problem_set = (ProblemSet.objects.prefetch_related("items__problem")
                           .get(id=int(problem_set_id)))
        except (TypeError, ValueError, ProblemSet.DoesNotExist):
            return self.error("문제집이 존재하지 않습니다")

        assignment = (ProblemSetAssignment.objects
                      .filter(problem_set=problem_set, is_open=True,
                              school_class__memberships__student=request.user)
                      .select_related("school_class__school")
                      .order_by("due_at").first())
        # 교사 본인(과 최고관리자)은 배포 전에 내용을 확인할 수 있어야 한다
        if assignment is None and not (problem_set.created_by_id == request.user.id or
                                       request.user.is_super_admin()):
            return self.error("문제집이 존재하지 않습니다")

        status_map = _solved_status_map(request.user)
        problems = []
        for item in problem_set.items.all():
            problem = ProblemBriefSerializer(item.problem).data
            problem["my_status"] = status_map.get(str(item.problem_id), {}).get("status")
            # 관리자가 감춘 문제는 목록에서 빼지 않고 "지금 풀 수 없다"고 알려준다.
            # 조용히 사라지면 학생은 문제집이 짧아진 이유를 알 수 없다.
            problem["available"] = item.problem.visible
            problems.append(problem)

        return self.success({
            "id": problem_set.id,
            "title": problem_set.title,
            "description": problem_set.description,
            "class_name": (f"{assignment.school_class.school.name} "
                           f"{assignment.school_class.display_name}") if assignment else None,
            "due_at": assignment.due_at.isoformat() if assignment and assignment.due_at else None,
            "problems": problems,
        })
