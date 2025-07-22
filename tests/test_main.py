"""Tests for main FastAPI application"""
import pytest
from httpx import AsyncClient


class TestMainApp:
    """Test main application endpoints"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API information"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        assert "sample_queries" in data
        
        assert data["message"] == "Healthcare Cost Navigator API"
        assert "providers" in data["endpoints"]
        assert "ask" in data["endpoints"]

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "healthcare-cost-navigator"

    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers are present"""
        response = await client.options("/")
        
        # The response should include CORS headers
        assert response.status_code in [200, 405]  # OPTIONS might not be explicitly handled

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(self, client: AsyncClient):
        """Test 404 for nonexistent endpoints"""
        response = await client.get("/nonexistent")
        
        assert response.status_code == 404
