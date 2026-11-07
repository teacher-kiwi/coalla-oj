from problem.serializers import ProblemSerializer
from submission.models import Submission
from utils.api import serializers

from .models import MAX_NUMBER, NICKNAME_MAX_LENGTH, Homework, HomeworkParticipant


class JoinHomeworkSerializer(serializers.Serializer):
    # 숫자 1~5자리. 출석번호든 학번이든 교사가 정한 대로 쓴다. 앞자리 0 은 무시한다.
    number = serializers.RegexField(r"^\d{1,5}$", error_messages={
        "invalid": "번호는 숫자 1~5자리로 넣어주세요"})
    # 처음 들어올 때만 쓴다(다시 들어올 때는 무시한다). 앞뒤 공백은 지운다.
    nickname = serializers.CharField(max_length=NICKNAME_MAX_LENGTH, required=False,
                                     allow_blank=True, error_messages={
                                         "max_length": f"닉네임은 {NICKNAME_MAX_LENGTH}자까지입니다"})
    pin = serializers.RegexField(r"^\d{4}$", error_messages={
        "invalid": "4자리 숫자를 넣어주세요"})

    def validate_number(self, value):
        number = int(value)
        if number > MAX_NUMBER:
            raise serializers.ValidationError("번호는 숫자 1~5자리로 넣어주세요")
        return number


class HomeworkSerializer(serializers.ModelSerializer):
    """입장 전에도 보여 주는 것. 문제와 언어는 참가한 뒤에만 준다."""
    ended = serializers.BooleanField(source="is_ended")

    class Meta:
        model = Homework
        fields = ("code", "title", "end_time", "ended", "entry_locked")


class HomeworkDetailSerializer(HomeworkSerializer):
    problems = serializers.SerializerMethodField()

    class Meta(HomeworkSerializer.Meta):
        fields = HomeworkSerializer.Meta.fields + ("languages", "problems")

    def get_problems(self, homework):
        # 참가자가 볼 때는 문제마다 내 현황(몇 번 냈는지, 맞혔는지)을 붙인다
        status = self.context.get("status", {})
        return [{"id": problem.id, "title": problem.title,
                 **status.get(problem.id, {"attempts": 0, "solved": False})}
                for problem in homework.problems()]


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeworkParticipant
        fields = ("number", "nickname", "join_time")


class StudentProblemSerializer(ProblemSerializer):
    """과제 학생이 보는 문제. 일반 문제 화면과 같은 본문을 주되 누적 통계와 작성자는 뺀다."""
    # 부모가 선언한 필드는 exclude 에 넣을 수 없어 먼저 지운다
    created_by = None

    class Meta(ProblemSerializer.Meta):
        exclude = ProblemSerializer.Meta.exclude + (
            "created_by", "submission_number", "accepted_number", "statistic_info",
            "archived_submission_number", "archived_accepted_number",
            "archived_statistic_info", "solver_verified_at", "solver_passed", "solver_message",
            "visibility", "difficulty")


class StudentSubmissionSerializer(serializers.ModelSerializer):
    """내 제출. 채점 상세(info)는 일반 화면(ACM)과 같이 감추고 결과·시간·메모리만 준다."""
    class Meta:
        model = Submission
        fields = ("id", "problem", "language", "code", "blockly_state", "result",
                  "statistic_info", "create_time")
