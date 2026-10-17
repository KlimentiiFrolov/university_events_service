from src.clients.recommendations import RecommendationClient
from src.core.config import settings
from src.core.logger import log
from src.core.uow import UnitOfWork
from src.schemas.events import EventResponse
from src.services.mappers import to_event_response


class RecommendationService:
    def __init__(
        self,
        uow: UnitOfWork,
        client: RecommendationClient,
        *,
        max_candidates: int = settings.recommendation.max_candidates,
    ):
        self.uow = uow
        self.client = client
        self.max_candidates = max_candidates

    async def recommend_events(self, user_id: int, limit: int) -> list[EventResponse]:
        visited_tag_ids = await self.uow.registrations.list_visited_tag_ids(user_id)
        candidates = await self.uow.events.list_recommendation_candidates(
            user_id,
            limit=self.max_candidates,
        )

        log.info(
            "Recommendations for user id=%d: %d visited tags, %d candidates",
            user_id, len(visited_tag_ids), len(candidates),
        )

        if not candidates:
            return []

        event_ids = await self.client.recommend(visited_tag_ids, candidates, limit)

        # Восстанавливаем порядок по ответу сервиса рекомендаций в конце, т.к. порядок не сохраняется в БД
        events_by_id = {
            event.id: event
            for event in await self.uow.events.list_by_ids(event_ids, with_tags=True)
        }

        missing = [event_id for event_id in event_ids if event_id not in events_by_id]
        if missing:
            log.warning("Recommended events not found: %s", tuple(missing))

        return [
            to_event_response(events_by_id[event_id])
            for event_id in event_ids
            if event_id in events_by_id
        ]
