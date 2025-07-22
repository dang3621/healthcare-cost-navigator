from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.ai_service import AIService


class AskRequest(BaseModel):
    question: str

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Who is cheapest for DRG 470 within 25 miles of 10001?"
            }
        }


class ProviderData(BaseModel):
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


class AskResponse(BaseModel):
    answer: str
    data: Optional[List[ProviderData]] = None
    query_type: str
    parameters: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Based on your search, Presbyterian Hospital in New York appears to be the most affordable option at $79,800 for Major Joint Replacement procedures within 25 miles of 10001.",
                "data": [
                    {
                        "provider_id": "330126",
                        "name": "PRESBYTERIAN HOSPITAL",
                        "city": "NEW YORK",
                        "state": "NY",
                        "zip_code": "10032",
                        "procedure": "470 - Major Joint Replacement w/o MCC",
                        "total_discharges": 756,
                        "average_covered_charges": 79800.0,
                        "average_total_payments": 20500.0,
                        "average_medicare_payments": 18300.0,
                        "distance_km": 5.2
                    }
                ],
                "query_type": "cost",
                "parameters": {
                    "drg": "470",
                    "zip_code": "10001",
                    "radius_km": 40.2,
                    "query_type": "cost",
                    "limit": 10
                }
            }
        }


router = APIRouter(prefix="/ask", tags=["ai-assistant"])


@router.post("/", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Natural language interface for healthcare queries
    
    Ask questions like:
    - "Who is cheapest for DRG 470 within 25 miles of 10001?"
    - "Which hospitals have the best ratings for heart surgery near 10032?"
    - "What's the average cost for knee replacement in New York?"
    - "Show me hospitals with good ratings for cardiac procedures near 11201"
    - "Find affordable pneumonia treatment options within 30 miles of 10016"
    
    The AI will:
    1. Parse your natural language question
    2. Extract relevant parameters (DRG, location, preferences)
    3. Query the database for matching hospitals
    4. Return a conversational answer with supporting data
    
    **Out-of-scope questions** (weather, general info, etc.) will be politely declined.
    """
    
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        ai_service = AIService(db)
        result = await ai_service.process_natural_language_query(request.question.strip())
        
        # Convert data to Pydantic models if present
        provider_data = None
        if result.get("data"):
            provider_data = [ProviderData(**item) for item in result["data"]]
        
        return AskResponse(
            answer=result["answer"],
            data=provider_data,
            query_type=result["query_type"],
            parameters=result.get("parameters")
        )
        
    except Exception as e:
        # Log the error in a real application
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process question: {str(e)}"
        )


@router.get("/examples")
async def get_example_questions():
    """
    Get example questions that the AI assistant can answer
    """
    return {
        "examples": [
            {
                "category": "Cost Queries",
                "questions": [
                    "Who is cheapest for DRG 470 within 25 miles of 10001?",
                    "What's the most affordable hospital for knee replacement near 10032?",
                    "Show me low-cost options for heart surgery within 40 miles of 11201"
                ]
            },
            {
                "category": "Quality Queries", 
                "questions": [
                    "Which hospitals have the best ratings for heart surgery near 10032?",
                    "Show me top-rated hospitals for joint replacement in New York",
                    "What are the highest quality hospitals for cardiac procedures near 10016?"
                ]
            },
            {
                "category": "General Search",
                "questions": [
                    "Find hospitals that do pneumonia treatment near 10075",
                    "Show me all hospitals offering DRG 194 within 30 miles of 11215",
                    "What hospitals in Brooklyn do major joint replacement?"
                ]
            },
            {
                "category": "Comparative Queries",
                "questions": [
                    "Compare costs for knee replacement between Manhattan and Brooklyn hospitals",
                    "Which is better value - Mount Sinai or NYU Langone for heart surgery?"
                ]
            },
            {
                "category": "Out-of-Scope (Will be declined)",
                "questions": [
                    "What's the weather today?",
                    "How do I cook pasta?",
                    "What's the capital of France?"
                ]
            }
        ],
        "tips": [
            "Be specific about the procedure (DRG code or common name)",
            "Include a ZIP code for location-based searches",
            "Mention if you care about cost ('cheapest', 'affordable') or quality ('best rated', 'top quality')",
            "You can specify distance ('within 25 miles', 'nearby', 'close to')"
        ]
    }
