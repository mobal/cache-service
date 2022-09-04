import uuid

import pendulum
import pytest


@pytest.fixture
def data() -> dict:
    return {
        'key': str(uuid.uuid4()),
        'value': 'Some random value',
        'created_at': pendulum.now().to_iso8601_string(),
        'ttl': pendulum.now().int_timestamp,
    }
