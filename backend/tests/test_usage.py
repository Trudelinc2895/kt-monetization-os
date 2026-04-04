"""Unit tests for usage metering."""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.plan = "free"
    user.credits = 0
    return user

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_unlimited_plan_always_allowed():
    """Business plan (limit=-1) always returns allowed."""
    from api.services.usage_service import check_and_charge_usage
    user = MagicMock()
    user.id = uuid.uuid4()
    user.plan = "business"
    user.credits = 0
    db = AsyncMock()
    with patch("api.services.usage_service._get_redis") as mock_redis:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = "9999999"
        mock_redis.return_value = redis_mock
        allowed, reason = await check_and_charge_usage(user, db)
    assert allowed is True
    assert reason == "unlimited"

@pytest.mark.asyncio
async def test_within_limit(mock_user, mock_db):
    """User under quota returns within_limit."""
    from api.services.usage_service import check_and_charge_usage
    mock_user.plan = "pro"
    with patch("api.services.usage_service._get_redis") as mock_redis:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = "10"  # well under 1000
        mock_redis.return_value = redis_mock
        allowed, reason = await check_and_charge_usage(mock_user, mock_db)
    assert allowed is True
    assert reason == "within_limit"

@pytest.mark.asyncio
async def test_limit_exceeded_no_credits(mock_user, mock_db):
    """User over quota with no credits returns limit_exceeded."""
    from api.services.usage_service import check_and_charge_usage
    mock_user.plan = "free"
    mock_user.credits = 0
    with patch("api.services.usage_service._get_redis") as mock_redis:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = "9999"  # way over free limit (50)
        mock_redis.return_value = redis_mock
        allowed, reason = await check_and_charge_usage(mock_user, mock_db)
    assert allowed is False
    assert reason == "limit_exceeded"

@pytest.mark.asyncio
async def test_redis_unavailable_fail_open(mock_user, mock_db):
    """Redis down returns fail-open (allowed=True)."""
    from api.services.usage_service import check_and_charge_usage
    mock_user.plan = "pro"
    with patch("api.services.usage_service._get_redis", side_effect=Exception("Redis down")):
        allowed, reason = await check_and_charge_usage(mock_user, mock_db)
    assert allowed is True
    assert reason == "redis_unavailable"
