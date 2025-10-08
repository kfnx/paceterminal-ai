from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from celery.result import AsyncResult
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
)
from app.tasks.analysis_task import financial_analysis_task
from app.celery import app as celery_app
from app.api.dependencies import limiter
from app.core.config import settings
from loguru import logger
import json
import asyncio

router = APIRouter()


@router.post("/analysis/start", response_model=AnalysisResponse)
@limiter.limit(settings.RATE_LIMIT_ANALYSIS)
async def start_financial_analysis(request: Request, analysis_request: AnalysisRequest):
    """
    Start a financial analysis task asynchronously

    Returns task_id for status polling
    """
    try:
        # Start Celery task
        task = financial_analysis_task.delay(
            query=analysis_request.query,
            user_context=analysis_request.user_context,
            reasoning_depth=analysis_request.reasoning_depth,
        )

        logger.info(f"Started analysis task: {task.id}")

        return AnalysisResponse(
            task_id=task.id,
            status="started",
            message="Financial analysis started. Use the task_id to check progress.",
        )

    except Exception as e:
        logger.error(f"Failed to start analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(task_id: str):
    """
    Get the status of a financial analysis task

    Returns current state, progress, and results
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "state": task_result.state,
        }

        if task_result.state == "PENDING":
            response.update(
                {
                    "status": "pending",
                    "message": "Task is waiting to be processed",
                    "progress": 0,
                }
            )
        elif task_result.state == "PROGRESS":
            # Get progress metadata
            info = task_result.info or {}
            response.update(
                {
                    "status": info.get("status", "processing"),
                    "message": info.get("message", "Processing..."),
                    "progress": info.get("progress", 0),
                    "phase": info.get("phase"),
                }
            )
        elif task_result.state == "SUCCESS":
            response.update(
                {
                    "status": "completed",
                    "message": "Analysis completed successfully",
                    "progress": 100,
                    "result": task_result.result,
                }
            )
        elif task_result.state == "FAILURE":
            response.update(
                {
                    "status": "failed",
                    "message": "Analysis failed",
                    "error": str(task_result.info),
                }
            )

        return AnalysisStatusResponse(**response)

    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/stream/{task_id}")
async def stream_analysis_progress(task_id: str):
    """
    Stream analysis progress using Server-Sent Events (SSE)

    This provides real-time updates to the frontend
    """

    async def event_generator():
        """Generate SSE events with task progress updates"""
        task_result = AsyncResult(task_id, app=celery_app)
        last_info = None
        iterations = 0
        max_iterations = 600  # 10 minutes with 1s sleep

        try:
            while iterations < max_iterations:
                current_state = task_result.state
                current_info = task_result.info or {}

                # Create a hashable representation for comparison
                info_key = (
                    current_state,
                    current_info.get("phase"),
                    current_info.get("progress"),
                    current_info.get("status"),
                )

                # Send update if anything changed OR every 5 seconds as heartbeat
                should_send = (info_key != last_info) or (iterations % 5 == 0)

                if should_send:
                    if current_state == "PENDING":
                        data = {
                            "state": "PENDING",
                            "message": "Task is queued",
                            "progress": 0,
                        }
                    elif current_state == "PROGRESS":
                        data = {
                            "state": "PROGRESS",
                            "phase": current_info.get("phase"),
                            "status": current_info.get("status"),
                            "message": current_info.get("message"),
                            "progress": current_info.get("progress", 0),
                        }
                    elif current_state == "SUCCESS":
                        data = {
                            "state": "SUCCESS",
                            "message": "Analysis completed",
                            "progress": 100,
                            "result": task_result.result,
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        break  # Stop streaming
                    elif current_state == "FAILURE":
                        data = {
                            "state": "FAILURE",
                            "message": "Analysis failed",
                            "error": str(current_info),
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        break  # Stop streaming
                    else:
                        # Unknown state
                        data = {
                            "state": current_state,
                            "message": f"Task state: {current_state}",
                        }

                    yield f"data: {json.dumps(data)}\n\n"
                    last_info = info_key

                # Check if task is complete
                if current_state in ["SUCCESS", "FAILURE"]:
                    break

                # Wait before next check
                await asyncio.sleep(1)
                iterations += 1

            # Send timeout message if it's exceeded max iterations
            if iterations >= max_iterations:
                timeout_data = {
                    "state": "TIMEOUT",
                    "message": "Streaming timeout reached",
                }
                yield f"data: {json.dumps(timeout_data)}\n\n"

        except Exception as e:
            logger.error(f"Error in SSE stream for task {task_id}: {str(e)}")
            error_data = {
                "state": "ERROR",
                "message": f"Stream error: {str(e)}",
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@router.delete("/analysis/cancel/{task_id}")
async def cancel_analysis(task_id: str):
    """
    Cancel a running analysis task
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"Cancelled task: {task_id}")

        return {"task_id": task_id, "status": "cancelled"}

    except Exception as e:
        logger.error(f"Failed to cancel task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
