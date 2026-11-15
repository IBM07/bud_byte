# 2. LLM gateway and free provider chain

Date: 2026-11-15 · Status: accepted (implemented in Phase 2)

## Context
No single free LLM tier is enough. Several providers disappeared or became trials in 2026:
- GitHub Models was retired on 2026-07-30.
- Cerebras is now a 30-day, $5 trial.
- Hugging Face gives free accounts no inference credits.

The product has open public signup, so quota exhaustion is the main operational risk.

## Decision
- All LLM traffic goes through one module (`budbyte_api.llm.gateway`), built on a LiteLLM Router. No other code imports a provider SDK.
- **Per-task fallback chains** live in configuration (YAML, overridable from the DB). Never hard-code a model.
  - route/extract: Groq, then Gemini flash-lite, Mistral, OpenRouter `:free`
  - agent/tools: Groq, then NVIDIA NIM, Mistral, Gemini flash, OpenRouter
  - vision: Gemini flash, then NIM vision, then OpenRouter vision
  - stt: Groq Whisper, then Gemini audio
  - judge: a different model family from the candidate
- **Embeddings:** local fastembed bge-small (384 dimensions) in the worker; Gemini embeddings as plan B.
- **Quota guard in Redis:**
  - Global per-model daily counters.
  - Per-user daily credits that scale with remaining headroom.
  - Priority lanes: interactive > nudge > ingest > eval.
- **Degradation ladder:** full chain, then small models, then no LLM (templates, search, dateparser), then queued with an ETA.
- **BYOK:** users can add their own key, which goes first in their chain and lifts their cap.

## Consequences
- **Provider churn becomes a config change**, not a code change.
- **Every LLM output is parsed into a Pydantic model.** A validation failure moves to the next model.
- **Free tiers for Gemini and Mistral train on prompts.** This is disclosed to users up front in `PRIVACY.md`.
