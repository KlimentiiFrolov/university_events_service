
from time import perf_counter

from src.core.grpc.generated import recommendation_pb2


def test_serialization(count: int) -> None:
    # Создаем Protobuf-запрос
    request = recommendation_pb2.RecommendRequest(
        visited_event_tag_ids=[1, 2, 3],
        limit=10,
    )

    # Добавляем мероприятия
    for i in range(count):
        event = request.events.add()
        event.event_id = i + 1
        event.tag_ids.extend([1, 2, 3, 4, 5])

    # Сериализация
    start = perf_counter()
    serialized = request.SerializeToString()
    elapsed = perf_counter() - start

    # Проверка десериализации
    restored = recommendation_pb2.RecommendRequest()
    restored.ParseFromString(serialized)

    assert restored == request

    # Вывод результатов
    print(f"Количество мероприятий: {count}")
    print(f"Размер: {len(serialized)} байт")
    print(f"Размер: {len(serialized) / 1024:.2f} KiB")
    print(f"Размер: {len(serialized) / 1024**2:.4f} MiB")
    print(f"Время сериализации: {elapsed:.6f} сек")
    print("-" * 40)


if __name__ == "__main__":
    for count in [100, 1000, 10000, 100000]:
        test_serialization(count)
