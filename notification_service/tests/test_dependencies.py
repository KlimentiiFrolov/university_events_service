from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient

from src.notifications.core.config import RabbitMQSettings
from src.notifications.dependencies import CurrentUserIdDep, WsUserIdDep
from src.notifications.lifespan import NotificationLifespan
from src.notifications.websocket.tickets import TicketStore

from .tokens import USER_ID, bearer, make_token

WS_URL = "/ws"


@pytest.fixture
def notification_lifespan() -> NotificationLifespan:
    # Без start(): RabbitMQ не нужен, проверяем только состояние в app.state
    return NotificationLifespan(RabbitMQSettings.model_construct())


@pytest.fixture
def tickets(notification_lifespan: NotificationLifespan) -> TicketStore:
    return notification_lifespan.tickets


@pytest.fixture
def client(notification_lifespan: NotificationLifespan) -> Generator[TestClient, None, None]:
    app = FastAPI()

    @app.get("/me")
    def me(user_id: CurrentUserIdDep) -> dict[str, int]:
        return {"user_id": user_id}

    @app.websocket(WS_URL)
    async def ws(websocket: WebSocket, user_id: WsUserIdDep) -> None:
        await websocket.accept()
        await websocket.send_json({"user_id": user_id})
        await websocket.close()

    notification_lifespan.bind(app)
    with TestClient(app) as test_client:
        yield test_client


def issue(tickets: TicketStore, ttl_seconds: float = 60) -> str:
    return tickets.issue(USER_ID, ttl_seconds)


def assert_rejected(client: TestClient, url: str, headers: dict[str, str] | None = None) -> None:
    with (
        pytest.raises(WebSocketDisconnect) as error,
        client.websocket_connect(url, headers=headers or {}),
    ):
        pass

    assert error.value.code == 1008


# --- HTTP: access-токен ---


def test_valid_access_token_gives_user_id(client: TestClient):
    response = client.get("/me", headers=bearer(make_token()))

    assert response.status_code == 200
    assert response.json() == {"user_id": USER_ID}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": f"Basic {make_token()}"},
        bearer("not-a-jwt"),
        bearer(make_token(secret="other-secret")),
        bearer(make_token(expires_in=timedelta(minutes=-1))),
        bearer(make_token(token_type="refresh")),
        bearer(make_token(user_id=0)),
    ],
    ids=["no header", "basic scheme", "garbage", "wrong secret", "expired", "refresh type",
         "bad subject"],
)
def test_invalid_access_token_is_401(client: TestClient, headers: dict[str, str]):
    response = client.get("/me", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# --- WebSocket: тикет ---


def test_ticket_in_header_gives_user_id(client: TestClient, tickets: TicketStore):
    with client.websocket_connect(WS_URL, headers=bearer(issue(tickets))) as ws:
        assert ws.receive_json() == {"user_id": USER_ID}


def test_ticket_in_query_gives_user_id(client: TestClient, tickets: TicketStore):
    with client.websocket_connect(f"{WS_URL}?ticket={issue(tickets)}") as ws:
        assert ws.receive_json() == {"user_id": USER_ID}


def test_ticket_is_consumed_on_connect(client: TestClient, tickets: TicketStore):
    ticket = issue(tickets)
    with client.websocket_connect(WS_URL, headers=bearer(ticket)) as ws:
        ws.receive_json()

    assert_rejected(client, WS_URL, bearer(ticket))


def test_header_takes_precedence_over_query(client: TestClient, tickets: TicketStore):
    url = f"{WS_URL}?ticket={issue(tickets)}"

    assert_rejected(client, url, bearer("unknown"))


def test_expired_ticket_is_rejected(client: TestClient, tickets: TicketStore):
    assert_rejected(client, WS_URL, bearer(issue(tickets, ttl_seconds=0)))


def test_access_token_instead_of_ticket_is_rejected(client: TestClient):
    assert_rejected(client, WS_URL, bearer(make_token()))
    assert_rejected(client, f"{WS_URL}?ticket={make_token()}")


@pytest.mark.parametrize(
    "headers",
    [{}, bearer(""), bearer("unknown"), {"Authorization": "no-scheme"}],
    ids=["no ticket", "empty bearer", "unknown ticket", "no scheme"],
)
def test_invalid_ticket_is_rejected_with_1008(client: TestClient, headers: dict[str, str]):
    assert_rejected(client, WS_URL, headers)


def test_ticket_with_wrong_scheme_is_rejected_and_not_consumed(
    client: TestClient,
    tickets: TicketStore,
):
    ticket = issue(tickets)

    assert_rejected(client, WS_URL, {"Authorization": f"Basic {ticket}"})
    assert tickets.consume(ticket) == USER_ID
