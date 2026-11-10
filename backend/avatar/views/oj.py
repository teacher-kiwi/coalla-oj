from account.decorators import login_required
from problem.models import Problem
from utils.api import APIView

from ..coins import balance
from ..models import CoinLog, CoinReason


class CoinLogAPI(APIView):
    """내 코인 잔액과 내역"""

    @login_required
    def get(self, request):
        logs = CoinLog.objects.filter(user=request.user)
        data = self.paginate_data(request, logs)
        page = list(data["results"])
        # 정답 코인은 어느 문제였는지 제목을 붙인다
        problem_ids = [int(log.ref) for log in page if log.reason == CoinReason.SOLVE and log.ref.isdigit()]
        titles = dict(Problem.objects.filter(id__in=problem_ids).values_list("id", "title"))
        data["results"] = [{
            "id": log.id, "amount": log.amount, "reason": log.reason, "ref": log.ref,
            "title": titles.get(int(log.ref)) if log.reason == CoinReason.SOLVE and log.ref.isdigit() else None,
            "create_time": log.create_time.isoformat(),
        } for log in page]
        data["balance"] = balance(request.user.id)
        return self.success(data)
