import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.core.uow import UnitOfWork
from src.models.roles import RoleName
from src.models.tags import Tag
from src.schemas.events import CreateEventSchema, UpdateEventSchema
from src.schemas.exceptions.domain import (
    EventCapacityExceededError,
    NotFoundError,
    RegistrationAlreadyExistsError,
)
from src.services.events import EventService
from src.services.registrations import RegistrationService
from src.services.users import UserService

# ЛОГИ


def section(number: int, title: str) -> None:
    print()
    print("=" * 72)
    print(f"{number}. {title}")
    print("=" * 72)


def success(message: str) -> None:
    print(f"[OK] {message}")


# ОСНОВНОЙ DEMO-СЦЕНАРИЙ


async def main() -> None:
    suffix = uuid4().hex[:8]

    print()
    print("=" * 72)
    print("UNIVERSITY EVENTS SERVICE")
    print("Демонстрация работы слоя базы данных")
    print(f"Demo ID: {suffix}")
    print("=" * 72)

    participant_email = f"ivan-{suffix}@demo.local"
    rollback_email = f"rollback-{suffix}@demo.local"

    participant_id: int
    event_id: int

    # ЭТАП 1
    # ОСНОВНАЯ ТРАНЗАКЦИЯ

    async with UnitOfWork() as uow:
        user_service = UserService(uow)
        event_service = EventService(uow)
        registration_service = RegistrationService(uow)

        # ЭТАП 2
        # CRUD ПОЛЬЗОВАТЕЛЕЙ

        section(1, "Создание пользователей")

        organizer = await user_service.create_user(
            email=f"organizer-{suffix}@demo.local",
            first_name="Егор",
            second_name="Организатор",
            role=RoleName.ORGANIZER,
        )

        participant = await user_service.create_user(
            email=participant_email,
            first_name="Иван",
            second_name="Петров",
            role=RoleName.PARTICIPANT,
        )

        second_participant = await user_service.create_user(
            email=f"anna-{suffix}@demo.local",
            first_name="Анна",
            second_name="Сидорова",
            role=RoleName.PARTICIPANT,
        )

        third_participant = await user_service.create_user(
            email=f"pavel-{suffix}@demo.local",
            first_name="Павел",
            second_name="Смирнов",
            role=RoleName.PARTICIPANT,
        )

        participant_id = participant.id

        success(
            f"Создан организатор: "
            f"id={organizer.id}, "
            f"name={organizer.full_name}, "
            f"role={organizer.role.name}"
        )

        success(
            f"Создан участник: "
            f"id={participant.id}, "
            f"name={participant.full_name}"
        )

        success(
            f"Создан участник: "
            f"id={second_participant.id}, "
            f"name={second_participant.full_name}"
        )

        success(
            f"Создан участник: "
            f"id={third_participant.id}, "
            f"name={third_participant.full_name}"
        )


        section(2, "Чтение пользователя")

        fetched_user = await user_service.get_user(
            participant.id
        )

        assert fetched_user.id == participant.id

        success(
            f"Получен пользователь из БД: "
            f"id={fetched_user.id}, "
            f"name={fetched_user.full_name}"
        )


        section(3, "Обновление пользователя")

        updated_user = await user_service.update_user(
            participant.id,
            second_name="Петров-Обновлён",
        )

        assert updated_user.second_name == "Петров-Обновлён"

        success(
            f"Пользователь обновлён: "
            f"{updated_user.full_name}"
        )

        # ЭТАП 3
        # TAG REPOSITORY

        section(4, "Создание тегов через Repository")

        it_tag = await uow.tags.add(
            Tag(
                name=f"IT-{suffix}"
            )
        )

        university_tag = await uow.tags.add(
            Tag(
                name=f"University-{suffix}"
            )
        )

        backend_tag = await uow.tags.add(
            Tag(
                name=f"Backend-{suffix}"
            )
        )

        success(
            f"Создан тег: "
            f"id={it_tag.id}, "
            f"name={it_tag.name}"
        )

        success(
            f"Создан тег: "
            f"id={university_tag.id}, "
            f"name={university_tag.name}"
        )

        success(
            f"Создан тег: "
            f"id={backend_tag.id}, "
            f"name={backend_tag.name}"
        )


        section(5, "Поиск тега через Repository")

        fetched_tag = await uow.tags.get_by_name(
            it_tag.name
        )

        assert fetched_tag is not None
        assert fetched_tag.id == it_tag.id

        success(
            f"Тег найден в БД: "
            f"id={fetched_tag.id}, "
            f"name={fetched_tag.name}"
        )

        # ЭТАП 4
        # EVENT SERVICE

        section(6, "Создание мероприятия")

        event = await event_service.create_event(
            organizer_id=organizer.id,
            data=CreateEventSchema(
                title="Лекция по backend-разработке",
                text=(
                    "Демонстрационное мероприятие "
                    "для первой лабораторной работы"
                ),
                location="Аудитория 101",
                event_date=(
                    datetime.now(UTC)
                    + timedelta(days=7)
                ),
                capacity=2,
                tag_ids=[
                    it_tag.id,
                    university_tag.id,
                ],
            ),
        )

        event_id = event.id

        success(
            f"Мероприятие создано: "
            f"id={event.id}, "
            f"title={event.title}"
        )


        section(
            7,
            "Получение мероприятия вместе с тегами",
        )

        event_with_tags = await event_service.get_event(
            event.id
        )

        tag_names = [
            event_tag.tag.name
            for event_tag
            in event_with_tags.event_tags
        ]

        success(
            f"Получено мероприятие: "
            f"{event_with_tags.title}"
        )

        success(
            f"Теги мероприятия: {tag_names}"
        )


        section(
            8,
            "Фильтрация мероприятий по тегу",
        )

        filtered_events = await event_service.list_events(
            tag_ids=[it_tag.id]
        )

        assert event.id in {
            filtered_event.id
            for filtered_event in filtered_events
        }

        success(
            f"Фильтр по тегу нашёл "
            f"мероприятие id={event.id}"
        )


        section(
            9,
            "Получение мероприятий организатора",
        )

        organizer_events = (
            await event_service.list_organizer_events(
                organizer.id
            )
        )

        assert event.id in {
            organizer_event.id
            for organizer_event in organizer_events
        }

        success(
            f"Мероприятие id={event.id} "
            "найдено среди мероприятий организатора"
        )


        section(10, "Обновление мероприятия")

        updated_event = await event_service.update_event(
            event_id=event.id,
            organizer_id=organizer.id,
            data=UpdateEventSchema(
                title="Лекция по Python backend",
                location="Аудитория 505",
                capacity=2,
            ),
        )

        assert (
            updated_event.title
            == "Лекция по Python backend"
        )

        success(
            f"Новое название: "
            f"{updated_event.title}"
        )

        success(
            f"Новое место: "
            f"{updated_event.location}"
        )

        success(
            f"Вместимость: "
            f"{updated_event.capacity}"
        )


        section(
            11,
            "Изменение тегов мероприятия",
        )

        event_with_new_tags = (
            await event_service.set_event_tags(
                event_id=event.id,
                organizer_id=organizer.id,
                tag_ids=[
                    it_tag.id,
                    backend_tag.id,
                ],
            )
        )

        new_tag_names = {
            event_tag.tag.name
            for event_tag
            in event_with_new_tags.event_tags
        }

        assert new_tag_names == {
            it_tag.name,
            backend_tag.name,
        }

        success(
            f"Новый набор тегов: "
            f"{sorted(new_tag_names)}"
        )

        # ЭТАП 5
        # REGISTRATION SERVICE

        section(
            12,
            "Регистрация участников",
        )

        first_registration = (
            await registration_service.register(
                participant.id,
                event.id,
            )
        )

        second_registration = (
            await registration_service.register(
                second_participant.id,
                event.id,
            )
        )

        success(
            f"Регистрация id="
            f"{first_registration.id}, "
            f"user_id={participant.id}, "
            f"status="
            f"{first_registration.status.value}"
        )

        success(
            f"Регистрация id="
            f"{second_registration.id}, "
            f"user_id={second_participant.id}, "
            f"status="
            f"{second_registration.status.value}"
        )


        section(
            13,
            "Получение списка участников мероприятия",
        )

        participants = (
            await registration_service
            .get_event_participants(
                event.id
            )
        )

        participant_names = [
            user.full_name
            for user in participants
        ]

        assert len(participants) == 2

        success(
            "Активные участники: "
            + ", ".join(participant_names)
        )

        # ЭТАП 6
        # БИЗНЕС-ОГРАНИЧЕНИЯ

        section(
            14,
            "Запрет повторной регистрации",
        )

        try:
            await registration_service.register(
                participant.id,
                event.id,
            )

        except RegistrationAlreadyExistsError as error:
            success(
                "Повторная регистрация "
                "корректно запрещена"
            )

            print(
                f"Бизнес-ошибка: {error}"
            )

        else:
            raise AssertionError(
                "Повторная регистрация "
                "должна была завершиться ошибкой"
            )


        section(
            15,
            "Проверка ограничения capacity",
        )

        try:
            await registration_service.register(
                third_participant.id,
                event.id,
            )

        except EventCapacityExceededError as error:
            success(
                "Регистрация сверх capacity "
                "корректно запрещена"
            )

            print(
                f"Бизнес-ошибка: {error}"
            )

        else:
            raise AssertionError(
                "Регистрация сверх capacity "
                "должна была завершиться ошибкой"
            )

        # ЭТАП 7
        # CANCEL / REREGISTER

        section(
            16,
            "Отмена регистрации",
        )

        cancelled_registration = (
            await registration_service.cancel(
                second_participant.id,
                event.id,
            )
        )

        assert (
            cancelled_registration.status.value
            == "cancelled"
        )

        success(
            f"Регистрация id="
            f"{cancelled_registration.id}: "
            f"status="
            f"{cancelled_registration.status.value}"
        )


        participants_after_cancel = (
            await registration_service
            .get_event_participants(
                event.id
            )
        )

        assert len(
            participants_after_cancel
        ) == 1

        success(
            "После отмены активных участников: "
            + ", ".join(
                user.full_name
                for user
                in participants_after_cancel
            )
        )


        section(
            17,
            "Повторная регистрация после отмены",
        )

        reregistered = (
            await registration_service.reregister(
                second_participant.id,
                event.id,
            )
        )

        assert (
            reregistered.status.value
            == "active"
        )

        success(
            f"Регистрация id="
            f"{reregistered.id}: "
            f"status={reregistered.status.value}"
        )

        participants_after_reregister = (
            await registration_service
            .get_event_participants(
                event.id
            )
        )

        assert len(
            participants_after_reregister
        ) == 2

        success(
            "Количество активных участников "
            "снова равно 2"
        )


        section(
            18,
            "Получение регистраций пользователя",
        )

        user_registrations = (
            await registration_service
            .get_my_registrations(
                participant.id
            )
        )

        for registration in user_registrations:
            print(
                f"registration_id="
                f"{registration.id}, "
                f"event_id="
                f"{registration.event_id}, "
                f"status="
                f"{registration.status.value}"
            )

        assert any(
            registration.event_id == event.id
            for registration
            in user_registrations
        )

        success(
            "Регистрации пользователя "
            "получены из БД"
        )

        # ЭТАП 8
        # DELETE USER

        section(
            19,
            "Удаление пользователя",
        )

        deleted_user_id = third_participant.id

        await user_service.delete_user(
            deleted_user_id
        )

        try:
            await user_service.get_user(
                deleted_user_id
            )

        except NotFoundError:
            success(
                f"Пользователь "
                f"id={deleted_user_id} "
                "удалён"
            )

        else:
            raise AssertionError(
                "Удалённый пользователь "
                "не должен находиться"
            )

        # ЭТАП 9
        # SOFT DELETE EVENT

        section(
            20,
            "Soft delete мероприятия",
        )

        await event_service.delete_event(
            event.id,
            organizer.id,
        )

        visible_events = (
            await event_service.list_events()
        )

        visible_event_ids = {
            visible_event.id
            for visible_event
            in visible_events
        }

        assert (
            event.id
            not in visible_event_ids
        )

        success(
            f"Мероприятие id={event.id} "
            "скрыто из обычного списка"
        )

        success(
            "При soft delete активные "
            "регистрации отменяются"
        )

        # ЭТАП 10
        # COMMIT

        print()
        print(
            "Выходим из UnitOfWork "
            "без исключения."
        )

        print(
            "UnitOfWork должен выполнить COMMIT."
        )

    # НОВЫЙ UNIT OF WORK
    # ПРОВЕРЯЕМ, ЧТО COMMIT СОХРАНИЛ ДАННЫЕ

    section(
        21,
        "Проверка COMMIT в новой сессии",
    )

    async with UnitOfWork() as uow:
        persisted_user = (
            await uow.users.get_by_email(
                participant_email
            )
        )

        assert persisted_user is not None

        assert (
            persisted_user.id
            == participant_id
        )

        success(
            "Пользователь существует "
            "в новой транзакции"
        )

        print(
            f"id={persisted_user.id}, "
            f"name={persisted_user.full_name}"
        )

        registrations_after_delete = (
            await uow.registrations
            .get_by_user_id(
                participant_id
            )
        )

        event_registration = next(
            registration
            for registration
            in registrations_after_delete
            if registration.event_id
            == event_id
        )

        assert (
            event_registration.status.value
            == "cancelled"
        )

        success(
            "Регистрация после удаления "
            "мероприятия имеет status=cancelled"
        )


        visible_events = (
            await uow.events.list_filtered()
        )

        assert event_id not in {
            visible_event.id
            for visible_event
            in visible_events
        }

        success(
            "Soft-deleted мероприятие "
            "не отображается в списке"
        )

    # ЭТАП 11
    # ROLLBACK

    section(
        22,
        "Демонстрация ROLLBACK",
    )

    try:
        async with UnitOfWork() as uow:
            user_service = UserService(uow)

            temporary_user = (
                await user_service.create_user(
                    email=rollback_email,
                    first_name="Временный",
                    second_name="Пользователь",
                    role=RoleName.PARTICIPANT,
                )
            )

            success(
                f"Внутри транзакции "
                f"создан временный user "
                f"id={temporary_user.id}"
            )

            print(
                "Теперь искусственно "
                "создаём исключение..."
            )

            raise RuntimeError(
                "Demo rollback"
            )

    except RuntimeError:
        success(
            "UnitOfWork получил исключение "
            "и выполнил ROLLBACK"
        )

    # Новая транзакция.
    # Проверяем, что временный пользователь не сохранился.

    async with UnitOfWork() as uow:
        rolled_back_user = (
            await uow.users.get_by_email(
                rollback_email
            )
        )

        assert rolled_back_user is None

        success(
            "Временного пользователя "
            "нет в БД после ROLLBACK"
        )

    # ФИНАЛ

    print()
    print("=" * 72)
    print(
        "ВСЕ ДЕМОНСТРАЦИОННЫЕ "
        "СЦЕНАРИИ УСПЕШНО ВЫПОЛНЕНЫ"
    )
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())