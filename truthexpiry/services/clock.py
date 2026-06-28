from datetime import date

from truthexpiry.ports.clock import ClockPort


class SystemClock:
    def today(self) -> date:
        return date.today()


def as_clock(clock: ClockPort | None) -> ClockPort:
    return clock or SystemClock()
