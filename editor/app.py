"""
Local Code Editor — powered by Qwen3-Coder-30B via Ollama.
Run: python editor/app.py
Then open: http://localhost:8000
"""

import json
from pathlib import Path

import ollama
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

MODEL = "qwen3-coder-30b-iq4xs"
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Local Code Editor")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

SYSTEM_PROMPT = (
    "You are an expert coding assistant. "
    "Be concise and direct. "
    "When returning code, wrap it in a single markdown code block with the language tag. "
    "Do not add unnecessary explanation unless asked."
)

ACTION_PROMPTS = {
    "explain": "Explain what this code does, step by step:\n\n```\n{code}\n```",
    "fix":     "Find and fix all bugs in this code. Return the corrected code with a brief summary of changes:\n\n```\n{code}\n```",
    "complete": "Complete the following code. Return only the completed version:\n\n```\n{code}\n```",
    "refactor": "Refactor this code for clarity and efficiency. Return the improved version with a short explanation:\n\n```\n{code}\n```",
    "tests":    "Write unit tests for this code using pytest:\n\n```\n{code}\n```",
    "docstring": "Add docstrings and type hints to this code:\n\n```\n{code}\n```",
}


class GenerateRequest(BaseModel):
    prompt: str = ""
    code: str = ""
    action: str = "chat"  # chat | explain | fix | complete | refactor | tests | docstring


@app.get("/", response_class=HTMLResponse)
async def root():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.post("/generate")
async def generate(req: GenerateRequest):
    # Build the user message based on action
    if req.action in ACTION_PROMPTS and req.code.strip():
        user_msg = ACTION_PROMPTS[req.action].format(code=req.code.strip())
        if req.prompt.strip():
            user_msg += f"\n\nAdditional context: {req.prompt}"
    elif req.action == "chat":
        user_msg = req.prompt
        if req.code.strip():
            user_msg = f"Code:\n```\n{req.code.strip()}\n```\n\n{req.prompt}"
    else:
        user_msg = req.prompt or "Help me with this code."

    user_msg += " /no_think"

    def stream_response():
        try:
            for chunk in ollama.chat(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                stream=True,
            ):
                text = chunk["message"]["content"]
                yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@app.get("/health")
async def health():
    try:
        ollama.list()
        return {"status": "ok", "model": MODEL}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


if __name__ == "__main__":
    print("=" * 50)
    print("Local Code Editor")
    print(f"Model: {MODEL}")
    print("Open: http://localhost:8000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
