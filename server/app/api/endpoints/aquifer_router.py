# app/api/endpoints/aquifer_router.py
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import traceback
import json
from fastapi.responses import JSONResponse
from typing import List, Optional
from app.services.spatial_service import get_aquifer_spatial_data
from app.services.aquifer_service import generate_aquifer_summary # This is now an async function
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[UUID] = None

class SpatialRequest(BaseModel):
    objectids: Optional[List[int]] = None
    basin: Optional[str] = None
    properties: Optional[List[str]] = Query([
        "OBJECTID", "Porosity", "Permeability", "Depth", "Thickness", "Recharge", "Lake_area"
    ])

@router.post("/aquifer-summary")
async def get_aquifer_summary_endpoint(request: QuestionRequest):
    question = request.question
    try:
        # Change chat_history_for_llm to chat_history
        response = await generate_aquifer_summary(request.question, chat_history=[]) # Changed here

        return {
            "ai_response": response["ai_response"],
            "statistics": response.get("statistics", {}),
            "cypher_queries": [response.get("cypher_query")] if response.get("cypher_query") else [],
            "objectids": response.get("objectids", [])
        }
    except Exception as e:
        error_detail = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "question": question
        }
        logger.exception(f"Error processing request for question: {question}")

        return JSONResponse(
            status_code=500,
            content={
                "error": "Analysis failed",
                "message": "Our technical team has been notified. Please try a different query."
            }
        )

@router.post("/aquifer-spatial")
async def get_aquifer_spatial_data_endpoint(request: SpatialRequest):
    try:
        spatial_data = get_aquifer_spatial_data(
            request.objectids,
            request.basin,
            request.properties
        )
        return spatial_data
    except Exception as e:
        error_detail = {
            "error": str(e),
            "request": request.dict(),
            "message": "Failed to retrieve spatial data"
        }
        logger.exception(f"Spatial data error for request: {request.dict()}")
        return JSONResponse(
            status_code=500,
            content={"error": "Spatial data retrieval failed"}
        )