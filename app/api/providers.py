from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.provider_service import ProviderService


class ProviderResponse(BaseModel):
    provider_id: str
    name: str
    city: str
    state: str
    zip_code: str
    procedure: str
    total_discharges: int
    average_covered_charges: float
    average_total_payments: float
    average_medicare_payments: float
    distance_km: Optional[float] = None
    average_rating: Optional[float] = None

    class Config:
        from_attributes = True


class ProvidersSearchResponse(BaseModel):
    providers: List[ProviderResponse]
    total_count: int
    query_parameters: dict


router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/", response_model=ProvidersSearchResponse)
async def search_providers(
    drg: Optional[str] = Query(None, description="DRG code or procedure name"),
    zip: Optional[str] = Query(None, description="ZIP code for location search", alias="zip_code"),
    radius_km: float = Query(50.0, description="Search radius in kilometers", ge=1, le=500),
    limit: int = Query(20, description="Maximum number of results", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for hospitals offering MS-DRG procedures
    
    - **drg**: DRG code (e.g., "470") or procedure name (e.g., "knee replacement")
    - **zip_code**: ZIP code to search near
    - **radius_km**: Search radius in kilometers (default: 50km)
    - **limit**: Maximum number of results (default: 20)
    - **offset**: Number of results to skip for pagination (default: 0)
    
    Returns hospitals sorted by average covered charges (cheapest first)
    """
    
    try:
        service = ProviderService(db)
        providers = await service.search_providers(
            drg=drg,
            zip_code=zip,
            radius_km=radius_km,
            limit=limit,
            offset=offset
        )
        
        # Enrich with ratings
        provider_responses = []
        for provider in providers:
            avg_rating = await service.get_average_rating(provider.provider_id)
            
            provider_response = ProviderResponse(
                provider_id=provider.provider_id,
                name=provider.provider_name,
                city=provider.provider_city,
                state=provider.provider_state,
                zip_code=provider.provider_zip_code,
                procedure=provider.ms_drg_definition,
                total_discharges=provider.total_discharges,
                average_covered_charges=provider.average_covered_charges,
                average_total_payments=provider.average_total_payments,
                average_medicare_payments=provider.average_medicare_payments,
                distance_km=getattr(provider, 'distance_km', None),
                average_rating=avg_rating
            )
            provider_responses.append(provider_response)
        
        return ProvidersSearchResponse(
            providers=provider_responses,
            total_count=len(provider_responses),
            query_parameters={
                "drg": drg,
                "zip_code": zip,
                "radius_km": radius_km,
                "limit": limit,
                "offset": offset
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific provider"""
    
    try:
        service = ProviderService(db)
        provider = await service.get_provider_with_ratings(provider_id)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        avg_rating = await service.get_average_rating(provider.provider_id)
        
        return ProviderResponse(
            provider_id=provider.provider_id,
            name=provider.provider_name,
            city=provider.provider_city,
            state=provider.provider_state,
            zip_code=provider.provider_zip_code,
            procedure=provider.ms_drg_definition,
            total_discharges=provider.total_discharges,
            average_covered_charges=provider.average_covered_charges,
            average_total_payments=provider.average_total_payments,
            average_medicare_payments=provider.average_medicare_payments,
            average_rating=avg_rating
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get provider: {str(e)}")
