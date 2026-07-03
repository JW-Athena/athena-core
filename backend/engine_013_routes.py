from typing import Optional

from fastapi import APIRouter, Query

from engine_013_learning_engine import (
    find_similar_patterns,
    find_successful_patterns,
    list_learning_records,
)


router = APIRouter(tags=["ATHENA Executive Brain Learning"])


@router.get("/athena/brain/learning-records")
async def learning_records():
    return list_learning_records()


@router.get("/athena/brain/successful-patterns")
async def successful_patterns(objective_type: Optional[str] = Query(default=None)):
    return find_successful_patterns(objective_type=objective_type)


@router.get("/athena/brain/similar-patterns")
async def similar_patterns(objective: str = Query(default="")):
    return find_similar_patterns(objective=objective)
