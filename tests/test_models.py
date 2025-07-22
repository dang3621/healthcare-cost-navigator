"""Tests for database models"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import Provider
from app.models.rating import Rating


class TestProviderModel:
    """Test Provider model"""

    @pytest.mark.asyncio
    async def test_create_provider(self, test_db: AsyncSession):
        """Test creating a provider"""
        provider = Provider(
            provider_id="TEST123",
            provider_name="Test Hospital",
            provider_city="Test City",
            provider_state="NY",
            provider_zip_code="10001",
            ms_drg_definition="470 - MAJOR JOINT REPLACEMENT",
            total_discharges=100,
            average_covered_charges=50000.0,
            average_total_payments=15000.0,
            average_medicare_payments=12000.0
        )
        
        test_db.add(provider)
        await test_db.commit()
        await test_db.refresh(provider)
        
        assert provider.id is not None
        assert provider.provider_id == "TEST123"
        assert provider.provider_name == "Test Hospital"
        assert provider.average_covered_charges == 50000.0

    @pytest.mark.asyncio
    async def test_provider_string_representation(self, test_db: AsyncSession):
        """Test provider string representation"""
        provider = Provider(
            provider_id="TEST123",
            provider_name="Test Hospital",
            provider_city="Test City",
            provider_state="NY",
            provider_zip_code="10001",
            ms_drg_definition="470 - MAJOR JOINT REPLACEMENT",
            total_discharges=100,
            average_covered_charges=50000.0,
            average_total_payments=15000.0,
            average_medicare_payments=12000.0
        )
        
        expected_str = "<Provider(id=None, name='Test Hospital', city='Test City')>"
        assert str(provider) == expected_str

    @pytest.mark.asyncio
    async def test_provider_required_fields(self, test_db: AsyncSession):
        """Test that provider requires all necessary fields"""
        # This should work with all required fields
        provider = Provider(
            provider_id="TEST123",
            provider_name="Test Hospital",
            provider_city="Test City",
            provider_state="NY",
            provider_zip_code="10001",
            ms_drg_definition="470 - MAJOR JOINT REPLACEMENT",
            total_discharges=100,
            average_covered_charges=50000.0,
            average_total_payments=15000.0,
            average_medicare_payments=12000.0
        )
        
        test_db.add(provider)
        await test_db.commit()
        
        assert provider.provider_id == "TEST123"


class TestRatingModel:
    """Test Rating model"""

    @pytest.mark.asyncio
    async def test_create_rating(self, test_db: AsyncSession, sample_provider: Provider):
        """Test creating a rating"""
        rating = Rating(
            provider_id=sample_provider.provider_id,
            rating_type="overall",
            rating=4.5
        )
        
        test_db.add(rating)
        await test_db.commit()
        await test_db.refresh(rating)
        
        assert rating.id is not None
        assert rating.provider_id == sample_provider.provider_id
        assert rating.rating == 4.5
        assert rating.rating_type == "overall"

    @pytest.mark.asyncio
    async def test_rating_string_representation(self, test_db: AsyncSession, sample_provider: Provider):
        """Test rating string representation"""
        rating = Rating(
            provider_id=sample_provider.provider_id,
            rating_type="overall",
            rating=4.5
        )
        
        expected_str = f"<Rating(id=None, provider_id='{sample_provider.provider_id}', rating=4.5)>"
        assert str(rating) == expected_str

    @pytest.mark.asyncio
    async def test_rating_relationship(self, test_db: AsyncSession, sample_provider: Provider):
        """Test rating relationship with provider"""
        rating = Rating(
            provider_id=sample_provider.provider_id,
            rating_type="overall",
            rating=4.5
        )
        
        test_db.add(rating)
        await test_db.commit()
        await test_db.refresh(rating)
        
        # Test that the rating is associated with the provider
        assert rating.provider_id == sample_provider.provider_id

    @pytest.mark.asyncio
    async def test_multiple_ratings_same_provider(self, test_db: AsyncSession, sample_provider: Provider):
        """Test multiple ratings for the same provider"""
        ratings = [
            Rating(
                provider_id=sample_provider.provider_id,
                rating_type="overall",
                rating=4.5
            ),
            Rating(
                provider_id=sample_provider.provider_id,
                rating_type="cleanliness",
                rating=4.0
            ),
            Rating(
                provider_id=sample_provider.provider_id,
                rating_type="staff",
                rating=5.0
            )
        ]
        
        for rating in ratings:
            test_db.add(rating)
        
        await test_db.commit()
        
        for rating in ratings:
            await test_db.refresh(rating)
            assert rating.provider_id == sample_provider.provider_id

    @pytest.mark.asyncio
    async def test_rating_types(self, test_db: AsyncSession, sample_provider: Provider):
        """Test different rating types"""
        rating_types = ["overall", "cleanliness", "staff", "communication", "pain_management"]
        
        for rating_type in rating_types:
            rating = Rating(
                provider_id=sample_provider.provider_id,
                rating_type=rating_type,
                rating=4.0
            )
            
            test_db.add(rating)
        
        await test_db.commit()
        
        # All ratings should be created successfully
        assert True  # If we get here without errors, the test passes

    @pytest.mark.asyncio
    async def test_rating_bounds(self, test_db: AsyncSession, sample_provider: Provider):
        """Test rating value bounds"""
        # Test minimum rating
        min_rating = Rating(
            provider_id=sample_provider.provider_id,
            rating_type="overall",
            rating=1.0
        )
        
        # Test maximum rating
        max_rating = Rating(
            provider_id=sample_provider.provider_id,
            rating_type="overall",
            rating=10.0  # Rating model uses 1-10 scale
        )
        
        test_db.add(min_rating)
        test_db.add(max_rating)
        await test_db.commit()
        
        await test_db.refresh(min_rating)
        await test_db.refresh(max_rating)
        
        assert min_rating.rating == 1.0
        assert max_rating.rating == 10.0

    @pytest.mark.asyncio
    async def test_rating_default_type(self, test_db: AsyncSession, sample_provider: Provider):
        """Test rating with default type"""
        # Rating with minimal required fields (rating_type should default to "overall")
        minimal_rating = Rating(
            provider_id=sample_provider.provider_id,
            rating=4.0
        )
        
        test_db.add(minimal_rating)
        await test_db.commit()
        await test_db.refresh(minimal_rating)
        
        assert minimal_rating.rating == 4.0
        assert minimal_rating.rating_type == "overall"  # Should default to "overall"
