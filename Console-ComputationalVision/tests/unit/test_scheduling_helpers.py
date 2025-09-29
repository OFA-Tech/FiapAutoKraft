import time

from shared.scheduling import IntervalScheduler


def test_interval_scheduler_skip_and_execute():
    scheduler = IntervalScheduler(0.1)
    # Immediate timeout on creation
    assert scheduler.timeout() <= 0.1
    assert scheduler.skip_if(True) is True
    first_timeout = scheduler.timeout()
    assert 0.09 <= first_timeout <= 0.11
    scheduler.executed()
    time.sleep(0.02)
    timeout_after_execute = scheduler.timeout()
    assert 0.07 <= timeout_after_execute <= 0.11
    assert scheduler.skip_if(False) is False
