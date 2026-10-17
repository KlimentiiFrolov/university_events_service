from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EventCandidate(_message.Message):
    __slots__ = ("event_id", "tag_ids")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    TAG_IDS_FIELD_NUMBER: _ClassVar[int]
    event_id: int
    tag_ids: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, event_id: _Optional[int] = ..., tag_ids: _Optional[_Iterable[int]] = ...) -> None: ...

class RecommendRequest(_message.Message):
    __slots__ = ("visited_event_tag_ids", "events", "limit")
    VISITED_EVENT_TAG_IDS_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    visited_event_tag_ids: _containers.RepeatedScalarFieldContainer[int]
    events: _containers.RepeatedCompositeFieldContainer[EventCandidate]
    limit: int
    def __init__(self, visited_event_tag_ids: _Optional[_Iterable[int]] = ..., events: _Optional[_Iterable[_Union[EventCandidate, _Mapping]]] = ..., limit: _Optional[int] = ...) -> None: ...

class RecommendResponse(_message.Message):
    __slots__ = ("event_ids",)
    EVENT_IDS_FIELD_NUMBER: _ClassVar[int]
    event_ids: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, event_ids: _Optional[_Iterable[int]] = ...) -> None: ...
