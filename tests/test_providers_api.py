"""Tests for providers API endpoints"""
import pytest
from httpx import AsyncClient
from app.models.provider import Provider


class TestProvidersAPI:
    """Test providers API endpoints"""

    @pytest.mark.asyncio
    async def test_search_providers_no_params(self, client: AsyncClient, sample_providers):
        """Test searching providers without parameters"""
        response = await client.get("/providers/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "providers" in data
        assert "total_count" in data
        assert "query_parameters" in data
        assert isinstance(data["providers"], list)

    @pytest.mark.asyncio
    async def test_search_providers_with_drg(self, client: AsyncClient, sample_providers):
        """Test searching providers with DRG parameter"""
        response = await client.get("/providers/?drg=470")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "providers" in data
        providers = data["providers"]
        
        # Should only return providers with DRG 470
        for provider in providers:
            assert "470" in provider["procedure"]

    @pytest.mark.asyncio
    async def test_search_providers_with_zip(self, client: AsyncClient, sample_providers):
        """Test searching providers with ZIP code"""
        response = await client.get("/providers/?zip_code=10001&radius_km=100")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "providers" in data
        assert data["query_parameters"]["zip_code"] == "10001"
        assert data["query_parameters"]["radius_km"] == 100

    @pytest.mark.asyncio
    async def test_search_providers_with_pagination(self, client: AsyncClient, sample_providers):
        """Test provider search with pagination"""
        response = await client.get("/providers/?limit=1&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["providers"]) <= 1
        assert data["query_parameters"]["limit"] == 1
        assert data["query_parameters"]["offset"] == 0

    @pytest.mark.asyncio
    async def test_search_providers_invalid_params(self, client: AsyncClient):
        """Test provider search with invalid parameters"""
        # Test invalid radius
        response = await client.get("/providers/?radius_km=1000")
        assert response.status_code == 422  # Validation error
        
        # Test invalid limit
        response = await client.get("/providers/?limit=0")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_provider_by_id(self, client: AsyncClient, sample_provider: Provider):
        """Test getting a specific provider by ID"""
        response = await client.get(f"/providers/{sample_provider.provider_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["provider_id"] == sample_provider.provider_id
        assert data["name"] == sample_provider.provider_name
        assert data["city"] == sample_provider.provider_city
        assert data["state"] == sample_provider.provider_state
        assert data["zip_code"] == sample_provider.provider_zip_code

    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, client: AsyncClient):
        """Test getting a nonexistent provider"""
        response = await client.get("/providers/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_provider_response_structure(self, client: AsyncClient, sample_provider: Provider):
        """Test that provider response has correct structure"""
        response = await client.get(f"/providers/{sample_provider.provider_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields are present
        required_fields = [
            "provider_id", "name", "city", "state", "zip_code",
            "procedure", "total_discharges", "average_covered_charges",
            "average_total_payments", "average_medicare_payments"
        ]
        
        for field in required_fields:
            assert field in data
        
        # Check optional fields
        assert "distance_km" in data  # Can be None
        assert "average_rating" in data  # Can be None

    @pytest.mark.asyncio
    async def test_providers_sorted_by_cost(self, client: AsyncClient, sample_providers):
        """Test that providers are sorted by cost (cheapest first)"""
        response = await client.get("/providers/")
        
        assert response.status_code == 200
        data = response.json()
        
        providers = data["providers"]
        if len(providers) > 1:
            # Check that providers are sorted by average_covered_charges
            for i in range(len(providers) - 1):
                assert providers[i]["average_covered_charges"] <= providers[i + 1]["average_covered_charges"]
