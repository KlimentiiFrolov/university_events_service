import asyncio

import grpc
from src.grpc.generated import recommendation_pb2_grpc
from src.grpc.servicer import RecommendationServicer


async def main():

    server = grpc.aio.server()

    recommendation_pb2_grpc.add_RecommendationServiceServicer_to_server(
        RecommendationServicer(),
        server,
    )

    server.add_insecure_port("0.0.0.0:50051")

    await server.start()

    print("Start")

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
