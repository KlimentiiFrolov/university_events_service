from time import perf_counter

import grpc

from src.core.grpc.generated import recommendation_pb2, recommendation_pb2_grpc
from src.core.logger import log
from src.schemas.exceptions.domain import RecommendationUnavailableError

type Candidate = tuple[int, list[int]]


class RecommendationClient:
    def __init__(self, channel: grpc.aio.Channel, *, timeout: float):
        self._stub = recommendation_pb2_grpc.RecommendationServiceStub(channel)
        self._timeout = timeout

    async def recommend(
        self,
        visited_tag_ids: list[int],
        candidates: list[Candidate],
        limit: int,
    ) -> list[int]:
        request = recommendation_pb2.RecommendRequest(
            visited_event_tag_ids=visited_tag_ids,
            events=[
                recommendation_pb2.EventCandidate(event_id=event_id, tag_ids=tag_ids)
                for event_id, tag_ids in candidates
            ],
            limit=limit,
        )

        log.info(
            "gRPC Recommend: %d visited tags, %d candidates, limit=%d, %d bytes",
            len(visited_tag_ids), len(candidates), limit, request.ByteSize(),
        )

        started = perf_counter()
        try:
            response: recommendation_pb2.RecommendResponse = await self._stub.Recommend(request, timeout=self._timeout)
        except grpc.aio.AioRpcError as error:
            log.error(
                "gRPC Recommend failed: %s %s",
                error.code().name, error.details(),
            )
            raise RecommendationUnavailableError(
                f"Recommendation service error: {error.code().name}"
            ) from error

        event_ids = list(response.event_ids)
        log.info(
            "gRPC Recommend returned %d ids in %.1f ms: %s",
            len(event_ids), (perf_counter() - started) * 1000, event_ids,
        )
        return event_ids
