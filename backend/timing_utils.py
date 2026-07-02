import time
from typing import Any, Callable, Dict, Optional


def new_request_context(request_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if request_context is None:
        request_context = {}

    request_context.setdefault("cache", {})
    request_context.setdefault("timings", [])
    return request_context


def timed_step(
    request_context: Dict[str, Any],
    engine: str,
    step: str,
    callback: Callable[[], Any],
) -> Any:
    started = time.perf_counter()
    status = "success"

    try:
        return callback()
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        request_context.setdefault("timings", []).append(
            {
                "engine": engine,
                "step": step,
                "elapsed_ms": elapsed_ms,
                "status": status,
            }
        )
        print(
            f"[timing] engine={engine} step={step} "
            f"elapsed_ms={elapsed_ms} status={status}"
        )


def cached_step(
    request_context: Dict[str, Any],
    cache_key: str,
    engine: str,
    step: str,
    callback: Callable[[], Any],
) -> Any:
    cache = request_context.setdefault("cache", {})

    if cache_key in cache:
        print(f"[timing] engine={engine} step={step} cache=hit")
        return cache[cache_key]

    print(f"[timing] engine={engine} step={step} cache=miss")
    result = timed_step(
        request_context=request_context,
        engine=engine,
        step=step,
        callback=callback,
    )
    cache[cache_key] = result
    return result
