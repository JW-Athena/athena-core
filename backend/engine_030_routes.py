from fastapi import APIRouter

from engine_030_daily_briefing_executive import generate_daily_briefing


router = APIRouter(tags=["ATHENA Daily Briefing Executive"])


@router.get("/athena/executive/daily-briefing")
async def daily_briefing_executive():
    return generate_daily_briefing()
