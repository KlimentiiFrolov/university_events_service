from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from notifications.lifespan import NotificationLifespan

from ..tokens import AUTH, USER_ID, bearer, make_token

URL = "/ws/tickets"


def test_ticket_is_issued_for_access_token_owner(
    client: TestClient,
    notification_lifespan: NotificationLifespan,
):
    response = client.post(URL, headers=bearer(make_token()))

    assert response.status_code == 201
    body = response.json()
    assert body["expires_in"] == AUTH.ws_ticket_ttl_seconds
    assert notification_lifespan.tickets.consume(body["ticket"]) == USER_ID


def test_each_request_gets_new_ticket(client: TestClient):
    first = client.post(URL, headers=bearer(make_token())).json()["ticket"]
    second = client.post(URL, headers=bearer(make_token())).json()["ticket"]

    assert first != second


@pytest.mark.parametrize(
    "headers",
    [
        {},
        bearer("not-a-jwt"),
        bearer(make_token(expires_in=timedelta(minutes=-1))),
        bearer(make_token(token_type="refresh")),
    ],
    ids=["no header", "garbage", "expired", "refresh type"],
)
def test_invalid_access_token_gets_no_ticket(
    client: TestClient,
    notification_lifespan: NotificationLifespan,
    headers: dict[str, str],
):
    response = client.post(URL, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert len(notification_lifespan.tickets) == 0
