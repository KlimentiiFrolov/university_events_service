import asyncio

import grpc

from src.core.config import settings
from src.core.grpc.generated import recommendation_pb2_grpc
from src.core.grpc.servicer import RecommendationServicer
from src.core.logger import log


async def main():

    server = grpc.aio.server()

    recommendation_pb2_grpc.add_RecommendationServiceServicer_to_server(
        RecommendationServicer(),
        server,
    )

    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)

    await server.start()

    log.info("gRPC server started on %s:%s", settings.grpc_host, settings.grpc_port)

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
