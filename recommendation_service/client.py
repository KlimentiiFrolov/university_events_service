
import asyncio

import grpc

from src.core.grpc.generated import (
    recommendation_pb2,
    recommendation_pb2_grpc,
)


async def main():
    async with grpc.aio.insecure_channel(
        "localhost:50051"
    ) as channel:

        stub = recommendation_pb2_grpc.RecommendationServiceStub(
            channel
        )

        request = recommendation_pb2.RecommendRequest(
            visited_event_tag_ids=[1, 2, 3],
            limit=4,
        )

        request.events.add(event_id=10, tag_ids=[1, 2])
        request.events.add(event_id=11, tag_ids=[3])
        request.events.add(event_id=12, tag_ids=[4, 5])
        request.events.add(event_id=13, tag_ids=[1, 2, 3])

        response = await stub.Recommend(
            request,
            timeout=5.0,
        )

        print("Recommended event IDs:")
        print(list(response.event_ids))


if __name__ == "__main__":
    asyncio.run(main())
