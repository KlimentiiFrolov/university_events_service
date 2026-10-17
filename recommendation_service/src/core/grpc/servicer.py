import grpc
from src.core.grpc.generated import (
    recommendation_pb2,
    recommendation_pb2_grpc,
)
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

        if not 1 <= request.limit <= 100:
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

        return recommendation_pb2.RecommendResponse(
            event_ids=recommended_ids,
        )
