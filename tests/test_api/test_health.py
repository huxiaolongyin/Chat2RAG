import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    assert "version" in data
    assert "responseTime" in data
    assert data["data"]["API"] == "health"
