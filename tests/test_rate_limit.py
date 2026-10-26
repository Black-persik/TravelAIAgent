from app.api.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_blocks_after_limit_and_recovers_after_window():
    clock = FakeClock()
    limiter = RateLimiter(limit=2, window_seconds=60, clock=clock)

    assert limiter.allow("user")
    assert limiter.allow("user")
    assert not limiter.allow("user")

    clock.now = 61
    assert limiter.allow("user")


def test_keys_are_counted_separately():
    limiter = RateLimiter(limit=1, clock=FakeClock())
    assert limiter.allow("alice")
    assert limiter.allow("bob")
    assert not limiter.allow("alice")
