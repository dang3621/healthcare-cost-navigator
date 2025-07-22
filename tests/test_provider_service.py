"""Tests for provider service"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.provider_service import ProviderService
from app.models.provider import Provider
from app.models.rating import Rating


class TestProviderService:
    """Test provider service functionality"""

    @pytest.mark.asyncio
    async def test_search_providers_no_filters(self, test_db: AsyncSession, sample_providers):
        """Test searching providers without filters"""
        service = ProviderService(test_db)
        
        providers = await service.search_providers()
        
        assert len(providers) > 0
        assert all(isinstance(p, Provider) for p in providers)

    @pytest.mark.asyncio
    async def test_search_providers_with_drg(self, test_db: AsyncSession, sample_providers):
        """Test searching providers with DRG filter"""
        service = ProviderService(test_db)
        
        providers = await service.search_providers(drg="470")
        
        # Should only return providers with DRG 470
        for provider in providers:
            assert "470" in provider.ms_drg_definition

    @pytest.mark.asyncio
    async def test_search_providers_with_pagination(self, test_db: AsyncSession, sample_providers):
        """Test provider search with pagination"""
        service = ProviderService(test_db)
        
        # Test limit
        providers = await service.search_providers(limit=1)
        assert len(providers) <= 1
        
        # Test offset
        all_providers = await service.search_providers()
        if len(all_providers) > 1:
            offset_providers = await service.search_providers(offset=1)
            assert len(offset_providers) == len(all_providers) - 1

    @pytest.mark.asyncio
    async def test_get_provider_with_ratings(self, test_db: AsyncSession, sample_provider: Provider):
        """Test getting provider with ratings"""
        service = ProviderService(test_db)
        
        provider = await service.get_provider_with_ratings(sample_provider.provider_id)
        
        assert provider is not None
        assert provider.provider_id == sample_provider.provider_id

    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, test_db: AsyncSession):
        """Test getting nonexistent provider"""
        service = ProviderService(test_db)
        
        provider = await service.get_provider_with_ratings("nonexistent")
        
        assert provider is None

    @pytest.mark.asyncio
    async def test_get_average_rating(self, test_db: AsyncSession, sample_provider: Provider, sample_rating: Rating):
        """Test getting average rating for provider"""
        service = ProviderService(test_db)
        
        avg_rating = await service.get_average_rating(sample_provider.provider_id)
        
        assert avg_rating is not None
        assert isinstance(avg_rating, float)
        assert avg_rating == 4.5  # From sample_rating fixture

    @pytest.mark.asyncio
    async def test_get_average_rating_no_ratings(self, test_db: AsyncSession, sample_provider: Provider):
        """Test getting average rating for provider with no ratings"""
        service = ProviderService(test_db)
        
        avg_rating = await service.get_average_rating(sample_provider.provider_id)
        
        assert avg_rating is None

    def test_extract_drg_number(self, test_db: AsyncSession):
        """Test DRG number extraction from text"""
        service = ProviderService(test_db)
        
        # Test various formats
        assert service.extract_drg_number("DRG 470") == "470"
        assert service.extract_drg_number("drg 470") == "470"
        assert service.extract_drg_number("470") == "470"
        assert service.extract_drg_number("470 - MAJOR JOINT") == "470"
        assert service.extract_drg_number("no drg here") is None

    @pytest.mark.asyncio
    async def test_search_by_fuzzy_drg(self, test_db: AsyncSession, sample_providers):
        """Test fuzzy DRG search"""
        service = ProviderService(test_db)
        
        matches = await service.search_by_fuzzy_drg("joint replacement")
        
        assert isinstance(matches, list)
        # Should find matches containing "JOINT REPLACEMENT"
        if matches:
            assert any("JOINT" in match.upper() for match in matches)

    @pytest.mark.asyncio
    @patch('app.services.provider_service.Nominatim')
    async def test_filter_by_location_success(self, mock_nominatim, test_db: AsyncSession, sample_providers):
        """Test location filtering with successful geocoding"""
        # Mock geocoder
        mock_geocoder = Mock()
        mock_location = Mock()
        mock_location.latitude = 40.7128
        mock_location.longitude = -74.0060
        mock_geocoder.geocode.return_value = mock_location
        mock_nominatim.return_value = mock_geocoder
        
        service = ProviderService(test_db)
        
        filtered = await service._filter_by_location(sample_providers, "10001", 50.0)
        
        assert isinstance(filtered, list)
        # Should return providers (exact filtering depends on mock coordinates)

    @pytest.mark.asyncio
    @patch('app.services.provider_service.Nominatim')
    async def test_filter_by_location_geocoding_failure(self, mock_nominatim, test_db: AsyncSession, sample_providers):
        """Test location filtering when geocoding fails"""
        # Mock geocoder to return None
        mock_geocoder = Mock()
        mock_geocoder.geocode.return_value = None
        mock_nominatim.return_value = mock_geocoder
        
        service = ProviderService(test_db)
        
        filtered = await service._filter_by_location(sample_providers, "invalid", 50.0)
        
        # Should return all providers when geocoding fails
        assert len(filtered) == len(sample_providers)

    @pytest.mark.asyncio
    async def test_providers_sorted_by_cost(self, test_db: AsyncSession, sample_providers):
        """Test that providers are sorted by cost"""
        service = ProviderService(test_db)
        
        providers = await service.search_providers()
        
        if len(providers) > 1:
            # Check that providers are sorted by average_covered_charges
            for i in range(len(providers) - 1):
                assert providers[i].average_covered_charges <= providers[i + 1].average_covered_charges

    @pytest.mark.asyncio
    async def test_search_providers_case_insensitive(self, test_db: AsyncSession, sample_providers):
        """Test that DRG search is case insensitive"""
        service = ProviderService(test_db)
        
        providers_upper = await service.search_providers(drg="JOINT")
        providers_lower = await service.search_providers(drg="joint")
        
        # Should return same results regardless of case
        assert len(providers_upper) == len(providers_lower)
