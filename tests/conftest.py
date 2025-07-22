"""Test configuration and fixtures"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient

from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.provider import Provider
from app.models.rating import Rating


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine):
    """Create test database session"""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client with database dependency override"""
    
    def override_get_db():
        return test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_provider(test_db: AsyncSession) -> Provider:
    """Create a sample provider for testing"""
    provider = Provider(
        provider_id="123456",
        provider_name="Test Hospital",
        provider_city="Test City",
        provider_state="NY",
        provider_zip_code="10001",
        ms_drg_definition="470 - MAJOR JOINT REPLACEMENT OR REATTACHMENT OF LOWER EXTREMITY W/O MCC",
        total_discharges=100,
        average_covered_charges=50000.0,
        average_total_payments=15000.0,
        average_medicare_payments=12000.0
    )
    
    test_db.add(provider)
    await test_db.commit()
    await test_db.refresh(provider)
    
    return provider


@pytest_asyncio.fixture
async def sample_providers(test_db: AsyncSession) -> list[Provider]:
    """Create multiple sample providers for testing"""
    providers = [
        Provider(
            provider_id="123456",
            provider_name="Test Hospital A",
            provider_city="New York",
            provider_state="NY",
            provider_zip_code="10001",
            ms_drg_definition="470 - MAJOR JOINT REPLACEMENT OR REATTACHMENT OF LOWER EXTREMITY W/O MCC",
            total_discharges=100,
            average_covered_charges=50000.0,
            average_total_payments=15000.0,
            average_medicare_payments=12000.0
        ),
        Provider(
            provider_id="789012",
            provider_name="Test Hospital B",
            provider_city="Brooklyn",
            provider_state="NY",
            provider_zip_code="11201",
            ms_drg_definition="470 - MAJOR JOINT REPLACEMENT OR REATTACHMENT OF LOWER EXTREMITY W/O MCC",
            total_discharges=80,
            average_covered_charges=45000.0,
            average_total_payments=14000.0,
            average_medicare_payments=11000.0
        ),
        Provider(
            provider_id="345678",
            provider_name="Test Hospital C",
            provider_city="Queens",
            provider_state="NY",
            provider_zip_code="11101",
            ms_drg_definition="291 - HEART FAILURE & SHOCK W MCC",
            total_discharges=150,
            average_covered_charges=30000.0,
            average_total_payments=10000.0,
            average_medicare_payments=8000.0
        )
    ]
    
    for provider in providers:
        test_db.add(provider)
    
    await test_db.commit()
    
    for provider in providers:
        await test_db.refresh(provider)
    
    return providers


@pytest_asyncio.fixture
async def sample_rating(test_db: AsyncSession, sample_provider: Provider) -> Rating:
    """Create a sample rating for testing"""
    rating = Rating(
        provider_id=sample_provider.provider_id,
        rating_type="overall",
        rating=4.5
    )
    
    test_db.add(rating)
    await test_db.commit()
    await test_db.refresh(rating)
    
    return rating
