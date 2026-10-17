import asyncio
from collections.abc import AsyncGenerator

import grpc
import pytest

from src.clients.recommendations import RecommendationClient
from src.core.grpc.generated import recommendation_pb2, recommendation_pb2_grpc
from src.schemas.exceptions.domain import RecommendationUnavailableError


class FakeRecommendationServicer(recommendation_pb2_grpc.RecommendationServiceServicer):
    def __init__(self):
        self.requests: list[recommendation_pb2.RecommendRequest] = []
        self.event_ids: list[int] = []
        self.abort_code: grpc.StatusCode | None = None
        self.delay: float = 0

    async def Recommend(self, request, context):
        self.requests.append(request)

        if self.delay:
            await asyncio.sleep(self.delay)
        if self.abort_code is not None:
            await context.abort(self.abort_code, "fake error")

        return recommendation_pb2.RecommendResponse(event_ids=self.event_ids)


@pytest.fixture
def servicer() -> FakeRecommendationServicer:
    return FakeRecommendationServicer()


@pytest.fixture
async def grpc_target(servicer: FakeRecommendationServicer) -> AsyncGenerator[str, None]:
    server = grpc.aio.server()
    recommendation_pb2_grpc.add_RecommendationServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("localhost:0")
    await server.start()

    yield f"localhost:{port}"

    await server.stop(grace=None)


@pytest.fixture
async def client(grpc_target: str) -> AsyncGenerator[RecommendationClient, None]:
    async with grpc.aio.insecure_channel(grpc_target) as channel:
        yield RecommendationClient(channel, timeout=1.0)


async def test_recommend_builds_request_and_returns_ids(
    client: RecommendationClient,
    servicer: FakeRecommendationServicer,
):
    servicer.event_ids = [12, 10]

    event_ids = await client.recommend(
        visited_tag_ids=[1, 2],
        candidates=[(10, [1]), (11, []), (12, [1, 2])],
        limit=5,
    )

    assert event_ids == [12, 10]

    assert len(servicer.requests) == 1
    request = servicer.requests[0]
    assert list(request.visited_event_tag_ids) == [1, 2]
    assert [(event.event_id, list(event.tag_ids)) for event in request.events] == [
        (10, [1]),
        (11, []),
        (12, [1, 2]),
    ]
    assert request.limit == 5


async def test_recommend_raises_on_server_error(
    client: RecommendationClient,
    servicer: FakeRecommendationServicer,
):
    servicer.abort_code = grpc.StatusCode.INVALID_ARGUMENT

    with pytest.raises(RecommendationUnavailableError, match="INVALID_ARGUMENT"):
        await client.recommend([1], [(10, [1])], limit=1)


async def test_recommend_raises_on_deadline_exceeded(
    grpc_target: str,
    servicer: FakeRecommendationServicer,
):
    servicer.delay = 0.5

    async with grpc.aio.insecure_channel(grpc_target) as channel:
        client = RecommendationClient(channel, timeout=0.1)

        with pytest.raises(RecommendationUnavailableError, match="DEADLINE_EXCEEDED"):
            await client.recommend([1], [(10, [1])], limit=1)


async def test_recommend_raises_when_service_unavailable(unused_tcp_port: int):
    async with grpc.aio.insecure_channel(f"localhost:{unused_tcp_port}") as channel:
        client = RecommendationClient(channel, timeout=0.5)

        # Код зависит от ОС: на Linux отказ в соединении приходит сразу (UNAVAILABLE),
        # на Windows — после повторов, и раньше срабатывает deadline (DEADLINE_EXCEEDED)
        with pytest.raises(RecommendationUnavailableError):
            await client.recommend([1], [(10, [1])], limit=1)
