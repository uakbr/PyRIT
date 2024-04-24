# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import pytest
import time

from datetime import datetime
from unittest.mock import MagicMock
from pyrit.models import PromptRequestPiece
from pyrit.models.prompt_request_response import PromptRequestResponse, group_conversation_request_pieces_by_sequence
from pyrit.orchestrator import PromptSendingOrchestrator
from pyrit.prompt_converter import Base64Converter
from tests.mocks import MockPromptTarget

from tests.mocks import get_sample_conversations


@pytest.fixture
def sample_conversations() -> list[PromptRequestPiece]:
    return get_sample_conversations()


def test_id_set():
    entry = PromptRequestPiece(
        role="user",
        original_prompt_text="Hello",
        converted_prompt_text="Hello",
    )
    assert entry.id is not None


def test_datetime_set():
    now = datetime.utcnow()
    time.sleep(0.1)
    entry = PromptRequestPiece(
        role="user",
        original_prompt_text="Hello",
        converted_prompt_text="Hello",
    )
    assert entry.timestamp > now


def test_converters_serialize():
    converter_identifiers = [Base64Converter().get_identifier()]
    entry = PromptRequestPiece(
        role="user",
        original_prompt_text="Hello",
        converted_prompt_text="Hello",
        converter_identifiers=converter_identifiers,
    )

    assert len(entry.converter_identifiers) == 1

    converter = entry.converter_identifiers[0]

    assert converter["__type__"] == "Base64Converter"
    assert converter["__module__"] == "pyrit.prompt_converter.base64_converter"


def test_prompt_targets_serialize():
    target = MockPromptTarget()
    entry = PromptRequestPiece(
        role="user",
        original_prompt_text="Hello",
        converted_prompt_text="Hello",
        prompt_target_identifier=target.get_identifier(),
    )

    assert entry.prompt_target_identifier["__type__"] == "MockPromptTarget"
    assert entry.prompt_target_identifier["__module__"] == "tests.mocks"


def test_orchestrators_serialize():
    orchestrator = PromptSendingOrchestrator(prompt_target=MagicMock(), memory=MagicMock())

    entry = PromptRequestPiece(
        role="user",
        original_prompt_text="Hello",
        converted_prompt_text="Hello",
        orchestrator_identifier=orchestrator.get_identifier(),
    )

    assert entry.orchestrator_identifier["id"] is not None
    assert entry.orchestrator_identifier["__type__"] == "PromptSendingOrchestrator"
    assert entry.orchestrator_identifier["__module__"] == "pyrit.orchestrator.prompt_sending_orchestrator"


def test_hashes_generated():
    entry = PromptRequestPiece(
        role="user",
        original_prompt_text="Hello1",
        converted_prompt_text="Hello2",
    )

    assert entry.original_prompt_data_sha256 == "948edbe7ede5aa7423476ae29dcd7d61e7711a071aea0d83698377effa896525"
    assert entry.converted_prompt_data_sha256 == "be98c2510e417405647facb89399582fc499c3de4452b3014857f92e6baad9a9"


def test_prompt_response_validate(sample_conversations: list[PromptRequestPiece]):
    for c in sample_conversations:
        c.conversation_id = sample_conversations[0].conversation_id

    request_response = PromptRequestResponse(request_pieces=sample_conversations)
    request_response.validate()


def test_prompt_response_empty_throws():
    request_response = PromptRequestResponse(request_pieces=[])
    with pytest.raises(ValueError, match="Empty request pieces."):
        request_response.validate()


def test_prompt_response_validate_conversation_id_throws(sample_conversations: list[PromptRequestPiece]):
    request_response = PromptRequestResponse(request_pieces=sample_conversations)
    with pytest.raises(ValueError, match="Conversation ID mismatch."):
        request_response.validate()


def test_prompt_response_converted_empty_throws(sample_conversations: list[PromptRequestPiece]):
    for c in sample_conversations:
        c.conversation_id = sample_conversations[0].conversation_id

    sample_conversations[0].converted_prompt_text = None
    request_response = PromptRequestResponse(request_pieces=sample_conversations)
    with pytest.raises(ValueError, match="Converted prompt text is None."):
        request_response.validate()


def test_group_conversation_request_pieces_throws(sample_conversations: list[PromptRequestPiece]):
    with pytest.raises(ValueError, match="Conversation ID must match."):
        group_conversation_request_pieces_by_sequence(sample_conversations)


def test_group_conversation_request_pieces(sample_conversations: list[PromptRequestPiece]):
    convo_group = [
        entry for entry in sample_conversations if entry.conversation_id == sample_conversations[0].conversation_id
    ]
    groups = group_conversation_request_pieces_by_sequence(convo_group)
    assert groups
    assert len(groups) == 1
    assert groups[0].request_pieces[0].sequence == 0


def test_group_conversation_request_pieces_multiple_groups(sample_conversations: list[PromptRequestPiece]):
    convo_group = [
        entry for entry in sample_conversations if entry.conversation_id == sample_conversations[0].conversation_id
    ]
    convo_group.append(
        PromptRequestPiece(
            role="user",
            original_prompt_text="Hello",
            conversation_id=convo_group[0].conversation_id,
            sequence=1,
        )
    )
    groups = group_conversation_request_pieces_by_sequence(convo_group)
    assert groups
    assert len(groups) == 2
    assert groups[0].request_pieces[0].sequence == 0
    assert groups[1].request_pieces[0].sequence == 1