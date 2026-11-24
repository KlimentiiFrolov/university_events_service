import pytest

from src.notifications.websocket.tickets import TicketStore

USER_ID = 7
OTHER_USER_ID = 8
TTL = 60


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def store(clock: FakeClock) -> TicketStore:
    return TicketStore(clock=clock)


def test_issued_ticket_is_consumed_as_its_user(store: TicketStore):
    ticket = store.issue(USER_ID, TTL)

    assert store.consume(ticket) == USER_ID


def test_ticket_is_single_use(store: TicketStore):
    ticket = store.issue(USER_ID, TTL)
    store.consume(ticket)

    assert store.consume(ticket) is None


def test_unknown_ticket_is_rejected(store: TicketStore):
    store.issue(USER_ID, TTL)

    assert store.consume("unknown") is None


def test_tickets_are_unique_and_bound_to_their_users(store: TicketStore):
    first = store.issue(USER_ID, TTL)
    second = store.issue(OTHER_USER_ID, TTL)

    assert first != second
    assert store.consume(second) == OTHER_USER_ID
    assert store.consume(first) == USER_ID


def test_ticket_is_valid_until_expiry(store: TicketStore, clock: FakeClock):
    ticket = store.issue(USER_ID, TTL)
    clock.now += TTL - 0.001

    assert store.consume(ticket) == USER_ID


def test_expired_ticket_is_rejected_and_removed(store: TicketStore, clock: FakeClock):
    ticket = store.issue(USER_ID, TTL)
    clock.now += TTL

    assert store.consume(ticket) is None
    assert len(store) == 0


def test_issue_purges_expired_tickets(store: TicketStore, clock: FakeClock):
    store.issue(USER_ID, TTL)
    clock.now += TTL
    fresh = store.issue(OTHER_USER_ID, TTL)

    assert len(store) == 1
    assert store.consume(fresh) == OTHER_USER_ID
