from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from fuzzywuzzy import fuzz
import re

from app.models.provider import Provider
from app.models.rating import Rating


class ProviderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.geocoder = Nominatim(user_agent="healthcare-cost-navigator")

    async def search_providers(
        self,
        drg: Optional[str] = None,
        zip_code: Optional[str] = None,
        radius_km: float = 50.0,
        limit: int = 20,
        offset: int = 0
    ) -> List[Provider]:
        """Search providers by DRG and location"""
        
        query = select(Provider).options(selectinload(Provider.ratings))
        
        # Filter by DRG if provided
        if drg:
            # Try exact match first, then fuzzy match
            drg_filter = or_(
                Provider.ms_drg_definition.ilike(f"%{drg}%"),
                Provider.ms_drg_definition.contains(drg)
            )
            query = query.where(drg_filter)
        
        # Execute base query
        result = await self.db.execute(query)
        providers = result.scalars().all()
        
        # Filter by location if zip code provided
        if zip_code and providers:
            providers = await self._filter_by_location(providers, zip_code, radius_km)
        
        # Sort by average covered charges (ascending - cheapest first)
        providers.sort(key=lambda p: p.average_covered_charges)
        
        # Apply pagination
        return providers[offset:offset + limit]

    async def _filter_by_location(
        self, 
        providers: List[Provider], 
        zip_code: str, 
        radius_km: float
    ) -> List[Provider]:
        """Filter providers by distance from zip code"""
        
        try:
            # Get coordinates for search zip code
            search_location = self.geocoder.geocode(f"{zip_code}, USA")
            if not search_location:
                return providers  # Return all if can't geocode
            
            search_coords = (search_location.latitude, search_location.longitude)
            filtered_providers = []
            
            for provider in providers:
                try:
                    # Get coordinates for provider zip code
                    provider_location = self.geocoder.geocode(f"{provider.provider_zip_code}, USA")
                    if provider_location:
                        provider_coords = (provider_location.latitude, provider_location.longitude)
                        distance = geodesic(search_coords, provider_coords).kilometers
                        
                        if distance <= radius_km:
                            # Add distance as attribute for potential use
                            provider.distance_km = round(distance, 2)
                            filtered_providers.append(provider)
                except:
                    # If geocoding fails, include the provider
                    filtered_providers.append(provider)
            
            return filtered_providers
            
        except Exception:
            # If any error occurs, return all providers
            return providers

    async def get_provider_with_ratings(self, provider_id: str) -> Optional[Provider]:
        """Get a provider with their ratings"""
        query = select(Provider).options(selectinload(Provider.ratings)).where(
            Provider.provider_id == provider_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search_by_fuzzy_drg(self, drg_query: str, threshold: int = 70) -> List[str]:
        """Find DRG definitions using fuzzy matching"""
        query = select(Provider.ms_drg_definition).distinct()
        result = await self.db.execute(query)
        all_drgs = [row[0] for row in result.fetchall()]
        
        # Use fuzzy matching to find similar DRGs
        matches = []
        for drg in all_drgs:
            ratio = fuzz.partial_ratio(drg_query.lower(), drg.lower())
            if ratio >= threshold:
                matches.append((drg, ratio))
        
        # Sort by match ratio (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches[:10]]  # Return top 10 matches

    def extract_drg_number(self, text: str) -> Optional[str]:
        """Extract DRG number from text"""
        # Look for patterns like "DRG 470", "470", etc.
        patterns = [
            r'drg\s*(\d+)',
            r'\b(\d{3})\b',  # 3-digit numbers
            r'(\d+)\s*-\s*'  # Numbers followed by dash
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)
        return None

    async def get_average_rating(self, provider_id: str, rating_type: str = "overall") -> Optional[float]:
        """Get average rating for a provider"""
        query = select(func.avg(Rating.rating)).where(
            and_(
                Rating.provider_id == provider_id,
                Rating.rating_type == rating_type
            )
        )
        result = await self.db.execute(query)
        avg_rating = result.scalar()
        return round(avg_rating, 1) if avg_rating else None
