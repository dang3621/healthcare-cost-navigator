import re
import json
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.provider_service import ProviderService


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.provider_service = ProviderService(db)

    async def process_natural_language_query(self, question: str) -> Dict[str, Any]:
        """Process natural language query and return structured response"""
        
        # Check if question is out of scope
        if not self._is_healthcare_related(question):
            return {
                "answer": "I can only help with hospital pricing and quality information. Please ask about medical procedures, costs, or hospital ratings.",
                "data": None,
                "query_type": "out_of_scope"
            }

        try:
            # Extract query parameters using AI
            query_params = await self._extract_query_parameters(question)
            
            # Execute database query based on extracted parameters
            providers = await self.provider_service.search_providers(
                drg=query_params.get("drg"),
                zip_code=query_params.get("zip_code"),
                radius_km=query_params.get("radius_km", 50.0),
                limit=query_params.get("limit", 10)
            )

            # Generate natural language response
            response = await self._generate_response(question, providers, query_params)
            
            return {
                "answer": response,
                "data": [self._serialize_provider(p) for p in providers],
                "query_type": query_params.get("query_type", "search"),
                "parameters": query_params
            }

        except Exception as e:
            return {
                "answer": f"I encountered an error processing your request: {str(e)}. Please try rephrasing your question.",
                "data": None,
                "query_type": "error"
            }

    def _is_healthcare_related(self, question: str) -> bool:
        """Check if question is related to healthcare/hospital queries"""
        healthcare_keywords = [
            "hospital", "medical", "surgery", "procedure", "doctor", "treatment",
            "cost", "price", "rating", "quality", "drg", "medicare", "insurance",
            "knee", "heart", "cardiac", "joint", "replacement", "pneumonia",
            "cheap", "expensive", "best", "worst", "near", "close"
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in healthcare_keywords)

    async def _extract_query_parameters(self, question: str) -> Dict[str, Any]:
        """Extract structured parameters from natural language question"""
        
        system_prompt = """
        You are a healthcare query parser. Extract structured parameters from natural language questions about hospitals and medical procedures.

        Extract these parameters when present:
        - drg: DRG code or procedure name (e.g., "470", "knee replacement", "heart surgery")
        - zip_code: ZIP code mentioned (5-digit number)
        - radius_km: Distance mentioned (convert miles to km, default 50km)
        - query_type: "cost" (cheapest/price), "quality" (best ratings), or "search" (general)
        - limit: Number of results requested (default 10)

        Return JSON format only. If a parameter isn't mentioned, omit it or use null.
        
        Examples:
        "Who is cheapest for DRG 470 within 25 miles of 10001?" 
        -> {"drg": "470", "zip_code": "10001", "radius_km": 40.2, "query_type": "cost", "limit": 10}
        
        "Which hospitals have the best ratings for heart surgery near 10032?"
        -> {"drg": "heart surgery", "zip_code": "10032", "query_type": "quality", "limit": 10}
        """

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback to regex extraction
                return self._fallback_parameter_extraction(question)
                
        except Exception:
            # Fallback to regex extraction
            return self._fallback_parameter_extraction(question)

    def _fallback_parameter_extraction(self, question: str) -> Dict[str, Any]:
        """Fallback parameter extraction using regex"""
        params = {}
        
        # Extract ZIP code
        zip_match = re.search(r'\b(\d{5})\b', question)
        if zip_match:
            params["zip_code"] = zip_match.group(1)
        
        # Extract DRG number
        drg_match = re.search(r'drg\s*(\d+)', question.lower())
        if drg_match:
            params["drg"] = drg_match.group(1)
        
        # Extract distance
        distance_match = re.search(r'(\d+)\s*miles?', question.lower())
        if distance_match:
            miles = int(distance_match.group(1))
            params["radius_km"] = round(miles * 1.60934, 1)  # Convert to km
        
        # Determine query type
        if any(word in question.lower() for word in ["cheap", "cost", "price", "affordable"]):
            params["query_type"] = "cost"
        elif any(word in question.lower() for word in ["best", "rating", "quality", "top"]):
            params["query_type"] = "quality"
        else:
            params["query_type"] = "search"
        
        return params

    async def _generate_response(self, question: str, providers: list, params: Dict[str, Any]) -> str:
        """Generate natural language response based on query results"""
        
        if not providers:
            return "I couldn't find any hospitals matching your criteria. Try expanding your search radius or checking the procedure name."

        # Prepare data summary for AI
        provider_summaries = []
        for provider in providers[:5]:  # Limit to top 5 for response
            avg_rating = await self.provider_service.get_average_rating(provider.provider_id)
            summary = {
                "name": provider.provider_name,
                "city": provider.provider_city,
                "cost": f"${provider.average_covered_charges:,.0f}",
                "rating": f"{avg_rating}/10" if avg_rating else "N/A",
                "procedure": provider.ms_drg_definition
            }
            provider_summaries.append(summary)

        system_prompt = f"""
        You are a helpful healthcare assistant. Generate a natural, conversational response to the user's question based on the hospital data provided.

        User's question: "{question}"
        Query type: {params.get('query_type', 'search')}

        Guidelines:
        - Be conversational and helpful
        - Mention specific hospital names, costs, and ratings when relevant
        - If asking about cost, highlight the cheapest options
        - If asking about quality, highlight the highest-rated options
        - Keep response concise but informative
        - Include 2-3 top recommendations maximum
        """

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Hospital data: {json.dumps(provider_summaries, indent=2)}"}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception:
            # Fallback response
            if params.get("query_type") == "cost":
                cheapest = providers[0]
                return f"Based on your search, {cheapest.provider_name} in {cheapest.provider_city} appears to be the most affordable option at ${cheapest.average_covered_charges:,.0f} for {cheapest.ms_drg_definition}."
            else:
                return f"I found {len(providers)} hospitals matching your criteria. The top option is {providers[0].provider_name} in {providers[0].provider_city}."

    def _serialize_provider(self, provider) -> Dict[str, Any]:
        """Serialize provider object for JSON response"""
        return {
            "provider_id": provider.provider_id,
            "name": provider.provider_name,
            "city": provider.provider_city,
            "state": provider.provider_state,
            "zip_code": provider.provider_zip_code,
            "procedure": provider.ms_drg_definition,
            "total_discharges": provider.total_discharges,
            "average_covered_charges": provider.average_covered_charges,
            "average_total_payments": provider.average_total_payments,
            "average_medicare_payments": provider.average_medicare_payments,
            "distance_km": getattr(provider, 'distance_km', None)
        }
