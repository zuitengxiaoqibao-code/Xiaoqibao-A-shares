from datetime import date, datetime, timezone

from qibao_api.a_shares.postclose_report import PostCloseReportBuilder
from qibao_api.shangshu.scheduler import DailyBriefingScheduler


def test_postclose_report_has_stable_identity():
    report = PostCloseReportBuilder().freeze(date(2026, 8, 21), datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc), {"涨停": 10})
    assert report.report_id.startswith("postclose-")


def test_scheduler_runs_postclose_report_once_after_close(tmp_path):
    class Calendar:
        def is_trading_day(self, _date): return True
    class Repository:
        def paused(self): return False
        def attempts_for(self, _key): return []
        def append_attempt(self, **_values): pass
    class Workflow:
        def run(self, *_args, **_kwargs): return type("Report", (), {"report_id": "brief"})()
    class Postclose:
        calls = 0
        def run(self, *_args, **_kwargs):
            self.calls += 1
            return type("Frozen", (), {"report_id": "frozen"})()
    postclose = Postclose()
    scheduler = DailyBriefingScheduler(Workflow(), Calendar(), Repository(), postclose_report_service=postclose, catchup_days=0)
    scheduler.tick(datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc))
    assert postclose.calls == 1
