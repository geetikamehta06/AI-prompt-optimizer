"""
Enterprise Prompt — FastAPI Web Server

Provides the REST API and serves the frontend SPA.
Streams enhancement progress via Server-Sent Events (SSE).
"""

import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.frameworks.registry import FrameworkRegistry
from src.orchestrator.pipeline import PromptPipeline
from src.providers.provider_factory import create_provider, list_providers
from src.security.sanitizer import PromptSanitizer
from src.storage.database import DatabaseManager
from src.storage.prompt_store import PromptStore
from src.utils.config import load_config, get_config
from src.utils.logging_setup import setup_logging, get_logger

logger = get_logger(__name__)

# ── App Setup ───────────────────────────────────────────────

config = load_config()

db = DatabaseManager()
store = PromptStore(db)
registry = FrameworkRegistry()
sanitizer = PromptSanitizer()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(config.server.log_level)
    await db.initialize()
    logger.info("Enterprise Prompt server started — %d frameworks loaded", registry.enabled_count)
    yield

app = FastAPI(title="Enterprise Prompt", version="1.0.0",
              description="AI-Powered Prompt Enhancement Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Pages ───────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main SPA shell."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(template_path.read_text(encoding="utf-8"))


# ── Enhancement API ─────────────────────────────────────────

@app.post("/api/enhance")
async def enhance_prompt(request: Request):
    """Enhance a prompt — streams progress via SSE."""
    body = await request.json()
    raw_prompt = body.get("prompt", "")
    framework_id = body.get("framework_id")
    provider_name = body.get("provider")
    enable_eval = body.get("enable_evaluation", True)
    enable_refine = body.get("enable_refinement", True)
    refinement_rounds = body.get("refinement_rounds")

    # Validate
    valid, error = sanitizer.validate(raw_prompt)
    if not valid:
        return JSONResponse({"error": error}, status_code=400)

    async def event_stream():
        queue = asyncio.Queue()

        async def progress_cb(stage, progress, log):
            await queue.put({"stage": stage, "progress": progress, "log": log})

        try:
            provider = create_provider(provider_name)
            pipeline = PromptPipeline(provider=provider, registry=registry, progress_callback=progress_cb)

            task = asyncio.create_task(pipeline.run(
                raw_prompt, framework_id=framework_id,
                enable_evaluation=enable_eval,
                enable_refinement=enable_refine,
                refinement_rounds=refinement_rounds,
            ))

            while not task.done():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    pass

            result = await task

            # Drain remaining
            while not queue.empty():
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"

            if result.success and result.enhanced_prompt:
                # Save to database
                await store.save(result.enhanced_prompt)

                yield f"data: {json.dumps({'complete': True, 'result': result.enhanced_prompt.model_dump(mode='json')})}\n\n"
            else:
                yield f"data: {json.dumps({'error': result.error or 'Enhancement failed'})}\n\n"

        except Exception as e:
            logger.error("Enhancement error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                                      "X-Accel-Buffering": "no"})


@app.post("/api/analyze")
async def analyze_prompt(request: Request):
    """Analyze a prompt without enhancing it."""
    body = await request.json()
    raw_prompt = body.get("prompt", "")
    valid, error = sanitizer.validate(raw_prompt)
    if not valid:
        return JSONResponse({"error": error}, status_code=400)

    from src.engine.analyzer import PromptAnalyzer
    provider = create_provider()
    analyzer = PromptAnalyzer(provider)
    analysis = await analyzer.analyze(raw_prompt)
    return JSONResponse(analysis.model_dump(mode="json"))


@app.post("/api/evaluate")
async def evaluate_prompt(request: Request):
    """Evaluate prompt quality."""
    body = await request.json()
    prompt_text = body.get("prompt", "")
    valid, error = sanitizer.validate(prompt_text)
    if not valid:
        return JSONResponse({"error": error}, status_code=400)

    from src.engine.evaluator import PromptEvaluator
    provider = create_provider()
    evaluator = PromptEvaluator(provider)
    report = await evaluator.evaluate(prompt_text)
    return JSONResponse(report.model_dump(mode="json"))


# ── Framework API ───────────────────────────────────────────

@app.get("/api/frameworks")
async def get_frameworks():
    """List all frameworks."""
    frameworks = registry.get_all(enabled_only=False)
    return JSONResponse([fw.model_dump() for fw in frameworks])


@app.get("/api/frameworks/{framework_id}")
async def get_framework(framework_id: str):
    """Get framework details."""
    fw = registry.get(framework_id)
    if not fw:
        return JSONResponse({"error": "Framework not found"}, status_code=404)
    return JSONResponse(fw.model_dump())


# ── History API ─────────────────────────────────────────────

@app.get("/api/history")
async def get_history(limit: int = 50, offset: int = 0):
    """Get prompt history."""
    items = await store.get_history(limit=limit, offset=offset)
    return JSONResponse(items)


@app.get("/api/history/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Get a specific prompt with versions."""
    prompt = await store.get(prompt_id)
    if not prompt:
        return JSONResponse({"error": "Not found"}, status_code=404)
    versions = await store.get_versions(prompt_id)
    return JSONResponse({"prompt": prompt, "versions": versions})


@app.delete("/api/history/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt."""
    deleted = await store.delete(prompt_id)
    if not deleted:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({"deleted": True})


# ── Analytics API ───────────────────────────────────────────

@app.get("/api/analytics")
async def get_analytics():
    """Get dashboard analytics."""
    data = await store.get_analytics()
    return JSONResponse(data)


# ── Settings API ────────────────────────────────────────────

@app.get("/api/providers")
async def get_providers():
    """List available providers."""
    return JSONResponse({"providers": list_providers(), "default": config.providers.default})


@app.get("/api/settings")
async def get_settings():
    """Get current settings."""
    return JSONResponse({
        "provider": config.providers.default,
        "pipeline": config.pipeline.model_dump(),
        "rate_limiting": config.rate_limiting.model_dump(),
    })


# ── Entry Point ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    setup_logging(config.server.log_level)
    logger.info("Starting Enterprise Prompt server on http://localhost:%d", config.server.port)
    uvicorn.run(app, host=config.server.host, port=config.server.port, log_level="info")
