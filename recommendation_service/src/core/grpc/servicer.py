from time import perf_counter

import grpc

from src.core.grpc.generated import (
    recommendation_pb2,
    recommendation_pb2_grpc,
)
from src.core.logger import log
from src.services.recommendations import (
    EventCandidate,
    recommend_event_ids,
)


class RecommendationServicer(
    recommendation_pb2_grpc.RecommendationServiceServicer
):
    async def Recommend(
        self,
        request: recommendation_pb2.RecommendRequest,
        context: grpc.aio.ServicerContext,
    ) -> recommendation_pb2.RecommendResponse:
        started = perf_counter()

        log.info(
            "Recommend request from %s: %d visited tags, %d candidates, limit=%d, %d bytes",
            context.peer(),
            len(request.visited_event_tag_ids),
            len(request.events),
            request.limit,
            request.ByteSize(),
        )

        if not 1 <= request.limit <= 100:
            log.warning("Recommend rejected: limit=%d is out of range 1..100", request.limit)
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "limit must be between 1 and 100",
            )

        events = [
            EventCandidate(
                event_id=event.event_id,
                tag_ids=list(event.tag_ids),
            )
            for event in request.events
        ]

        recommended_ids = recommend_event_ids(
            visited_event_tag_ids=list(
                request.visited_event_tag_ids
            ),
            events=events,
            limit=request.limit,
        )

        log.info(
            "Recommend response: %d ids in %.1f ms: %s",
            len(recommended_ids),
            (perf_counter() - started) * 1000,
            recommended_ids,
        )

        return recommendation_pb2.RecommendResponse(
            event_ids=recommended_ids,
        )
