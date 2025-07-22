"""Tests for AI assistant API endpoints"""
import pytest
from unittest.mock import Mock, patch
from httpx import AsyncClient


class TestAssistantAPI:
    """Test AI assistant API endpoints"""

    @pytest.mark.asyncio
    async def test_ask_question_valid(self, client: AsyncClient):
        """Test asking a valid question"""
        with patch('app.services.ai_service.AIService') as mock_ai_service:
            # Mock the AI service response
            mock_service_instance = Mock()
            mock_service_instance.process_natural_language_query.return_value = {
                "answer": "Test answer",
                "data": [
                    {
                        "provider_id": "123456",
                        "name": "Test Hospital",
                        "city": "Test City",
                        "state": "NY",
                        "zip_code": "10001",
                        "procedure": "470 - MAJOR JOINT REPLACEMENT",
                        "total_discharges": 100,
                        "average_covered_charges": 50000.0,
                        "average_total_payments": 15000.0,
                        "average_medicare_payments": 12000.0,
                        "distance_km": 5.0
                    }
                ],
                "query_type": "cost",
                "parameters": {"drg": "470", "zip_code": "10001"}
            }
            mock_ai_service.return_value = mock_service_instance
            
            response = await client.post(
                "/ask/",
                json={"question": "Who is cheapest for DRG 470 near 10001?"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "answer" in data
            assert "data" in data
            assert "query_type" in data
            assert "parameters" in data
            
            assert data["answer"] == "Test answer"
            assert data["query_type"] == "cost"
            assert len(data["data"]) == 1
            assert data["data"][0]["provider_id"] == "123456"

    @pytest.mark.asyncio
    async def test_ask_question_empty(self, client: AsyncClient):
        """Test asking an empty question"""
        response = await client.post("/ask/", json={"question": ""})
        
        assert response.status_code == 400
        data = response.json()
        assert "empty" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_ask_question_whitespace_only(self, client: AsyncClient):
        """Test asking a question with only whitespace"""
        response = await client.post("/ask/", json={"question": "   "})
        
        assert response.status_code == 400
        data = response.json()
        assert "empty" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_ask_question_no_data(self, client: AsyncClient):
        """Test asking a question that returns no provider data"""
        with patch('app.services.ai_service.AIService') as mock_ai_service:
            # Mock the AI service response with no data
            mock_service_instance = Mock()
            mock_service_instance.process_natural_language_query.return_value = {
                "answer": "I couldn't find any hospitals matching your criteria.",
                "data": None,
                "query_type": "search",
                "parameters": {"drg": "999", "zip_code": "00000"}
            }
            mock_ai_service.return_value = mock_service_instance
            
            response = await client.post(
                "/ask/",
                json={"question": "Find hospitals for DRG 999 near 00000"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["answer"] == "I couldn't find any hospitals matching your criteria."
            assert data["data"] is None
            assert data["query_type"] == "search"

    @pytest.mark.asyncio
    async def test_ask_question_service_error(self, client: AsyncClient):
        """Test handling of AI service errors"""
        with patch('app.services.ai_service.AIService') as mock_ai_service:
            # Mock the AI service to raise an exception
            mock_service_instance = Mock()
            mock_service_instance.process_natural_language_query.side_effect = Exception("AI service error")
            mock_ai_service.return_value = mock_service_instance
            
            response = await client.post(
                "/ask/",
                json={"question": "Test question"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to process question" in data["detail"]

    @pytest.mark.asyncio
    async def test_ask_question_invalid_json(self, client: AsyncClient):
        """Test asking a question with invalid JSON"""
        response = await client.post(
            "/ask/",
            json={"invalid_field": "test"}
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_example_questions(self, client: AsyncClient):
        """Test getting example questions"""
        response = await client.get("/ask/examples")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "examples" in data
        assert "tips" in data
        
        examples = data["examples"]
        assert isinstance(examples, list)
        assert len(examples) > 0
        
        # Check structure of examples
        for example_category in examples:
            assert "category" in example_category
            assert "questions" in example_category
            assert isinstance(example_category["questions"], list)
        
        # Check that tips are provided
        tips = data["tips"]
        assert isinstance(tips, list)
        assert len(tips) > 0

    @pytest.mark.asyncio
    async def test_ask_response_structure(self, client: AsyncClient):
        """Test that ask response has correct structure"""
        with patch('app.services.ai_service.AIService') as mock_ai_service:
            # Mock the AI service response
            mock_service_instance = Mock()
            mock_service_instance.process_natural_language_query.return_value = {
                "answer": "Test answer",
                "data": [
                    {
                        "provider_id": "123456",
                        "name": "Test Hospital",
                        "city": "Test City",
                        "state": "NY",
                        "zip_code": "10001",
                        "procedure": "470 - MAJOR JOINT REPLACEMENT",
                        "total_discharges": 100,
                        "average_covered_charges": 50000.0,
                        "average_total_payments": 15000.0,
                        "average_medicare_payments": 12000.0,
                        "distance_km": 5.0
                    }
                ],
                "query_type": "cost",
                "parameters": {"drg": "470", "zip_code": "10001"}
            }
            mock_ai_service.return_value = mock_service_instance
            
            response = await client.post(
                "/ask/",
                json={"question": "Test question"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check required fields
            required_fields = ["answer", "data", "query_type", "parameters"]
            for field in required_fields:
                assert field in data
            
            # Check data structure if present
            if data["data"]:
                provider_data = data["data"][0]
                provider_required_fields = [
                    "provider_id", "name", "city", "state", "zip_code",
                    "procedure", "total_discharges", "average_covered_charges",
                    "average_total_payments", "average_medicare_payments"
                ]
                
                for field in provider_required_fields:
                    assert field in provider_data

    @pytest.mark.asyncio
    async def test_ask_question_long_text(self, client: AsyncClient):
        """Test asking a very long question"""
        with patch('app.services.ai_service.AIService') as mock_ai_service:
            # Mock the AI service response
            mock_service_instance = Mock()
            mock_service_instance.process_natural_language_query.return_value = {
                "answer": "Test answer",
                "data": None,
                "query_type": "search",
                "parameters": {}
            }
            mock_ai_service.return_value = mock_service_instance
            
            long_question = "This is a very long question " * 100
            
            response = await client.post(
                "/ask/",
                json={"question": long_question}
            )
            
            assert response.status_code == 200
            # Should handle long questions gracefully
