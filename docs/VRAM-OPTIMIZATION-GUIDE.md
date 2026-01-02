# VRAM Optimization Guide - RTX 3080 10GB

## TL;DR - You're Safe! ✅

Your RTX 3080 10GB can handle all models because **Ollama automatically unloads inactive models from VRAM**. Only ONE model runs at a time during the agent pipeline.

---

## Your Hardware

- **GPU:** RTX 3080 10GB VRAM
- **RAM:** 32GB System RAM
- **Status:** ✅ Sufficient for all Phase 1 models

---

## Model Memory Requirements

| Model | VRAM Required | Use Case |
|-------|---------------|----------|
| `llama3.2:3b` | ~2.0GB | Planner + Validator (lightweight, fast) |
| `qwen2.5-coder:7b` | ~4.7GB | Cypher Specialist (code generation) |
| `llama3:8b` | ~4.7GB | Analyst (reasoning) |
| **Total if all loaded** | ~11.4GB | ❌ Exceeds 10GB |
| **Max at one time** | ~4.7GB | ✅ Fits in 10GB |

---

## How Ollama Manages Memory (Sequential Loading)

### Default Behavior (Auto-Unload)

Ollama uses a **"load on demand, unload on idle"** strategy:

```
1. Request comes in for Planner Agent
   → Ollama loads llama3.2:3b (~2GB VRAM)
   → Inference runs
   → Response returned

2. Request comes in for Cypher Specialist
   → Ollama UNLOADS llama3.2:3b (after 5min timeout)
   → Ollama loads qwen2.5-coder:7b (~4.7GB VRAM)
   → Inference runs
   → Response returned

3. Request comes in for Validator
   → Ollama UNLOADS qwen2.5-coder:7b
   → Ollama loads llama3.2:3b (~2GB VRAM)
   → Inference runs
   → Response returned

4. Request comes in for Analyst
   → Ollama UNLOADS llama3.2:3b
   → Ollama loads llama3:8b (~4.7GB VRAM)
   → Inference runs
   → Response returned
```

**Peak VRAM Usage:** ~4.7GB (qwen2.5-coder:7b or llama3:8b)
**Your Available VRAM:** 10GB
**Headroom:** 5.3GB ✅

---

## Optimization Strategies

### Strategy 1: Default (Recommended for You)

**Configuration:**
```bash
# .env
OLLAMA_KEEP_ALIVE=300  # Keep loaded for 5 minutes
```

**Behavior:**
- Model stays in VRAM for 5 minutes after last use
- If same agent called again within 5min → instant response
- After 5min idle → model unloaded automatically

**Pros:**
- Faster repeated queries (no reload time)
- Still safe for 10GB VRAM

**Cons:**
- If switching between agents rapidly, you wait for model swap (~5-10s)

---

### Strategy 2: Aggressive Unload (Fastest Unload)

**Configuration:**
```bash
# .env
OLLAMA_KEEP_ALIVE=0  # Unload immediately after request
```

**Behavior:**
- Model unloads RIGHT AFTER each request
- Always free VRAM between requests

**Pros:**
- Minimum VRAM usage
- Best for multitasking (other GPU apps running)

**Cons:**
- Every request requires model reload (~5-10s overhead)
- Slower overall pipeline

---

### Strategy 3: Smart Batching (Best Performance)

**Configuration:**
```bash
# .env
OLLAMA_KEEP_ALIVE=60  # Keep loaded for 1 minute
```

**Behavior:**
- Model stays loaded for 1 minute
- Good balance between speed and memory

**Pros:**
- Fast repeated calls within 1 minute
- Quick unload for VRAM availability

**Cons:**
- Still 1min wait before VRAM freed

---

## Recommended Configuration for RTX 3080 10GB

Update your `.env` file:

```bash
# Ollama Memory Management
OLLAMA_KEEP_ALIVE=60  # Unload after 1 minute idle

# Model Selection (optimized for 10GB VRAM)
PLANNER_MODEL=llama3.2:3b          # 2GB VRAM
CYPHER_MODEL=qwen2.5-coder:7b      # 4.7GB VRAM
VALIDATOR_MODEL=llama3.2:3b        # 2GB VRAM
ANALYST_MODEL=llama3:8b            # 4.7GB VRAM

# Context Window (safe for all models on 10GB)
OLLAMA_NUM_CTX=8192
```

---

## Alternative: Smaller Models (If Issues Arise)

If you experience VRAM issues or want faster swapping:

### Option A: All Small Models (~2GB each)

```bash
PLANNER_MODEL=llama3.2:3b          # 2GB
CYPHER_MODEL=llama3.2:3b           # 2GB (less accurate Cypher)
VALIDATOR_MODEL=llama3.2:3b        # 2GB
ANALYST_MODEL=llama3.2:3b          # 2GB (weaker reasoning)
```

**Trade-off:** Faster, less VRAM, but lower quality outputs

### Option B: Mixed Sizes (Recommended Minimum)

```bash
PLANNER_MODEL=llama3.2:3b          # 2GB
CYPHER_MODEL=qwen2.5-coder:7b      # 4.7GB (keep this - best for Cypher)
VALIDATOR_MODEL=llama3.2:3b        # 2GB
ANALYST_MODEL=llama3.2:3b          # 2GB (downgrade if needed)
```

**Trade-off:** Cypher generation stays good, analyst is weaker

---

## Monitoring VRAM Usage

### Check Ollama Memory

```bash
# List loaded models
curl http://localhost:11434/api/tags | jq

# Check GPU usage
nvidia-smi

# Watch VRAM in real-time
watch -n 1 nvidia-smi
```

### Expected VRAM During Pipeline

```
Agent Pipeline Execution (10GB VRAM available):

[Planner]
GPU: ████░░░░░░ 2.0GB / 10GB

[Cypher Specialist]
GPU: █████████░ 4.7GB / 10GB

[Validator]
GPU: ████░░░░░░ 2.0GB / 10GB

[Analyst]
GPU: █████████░ 4.7GB / 10GB
```

---

## Comparison with Your V1 System

### V1 Configuration
```bash
GENERATE_CYPHER_MODEL=deepseek-coder-v2:16b  # ❌ 16B model = ~9GB VRAM!
AI_CHATBOT_MODEL=llama3:8b                    # ~4.7GB VRAM
SUMMARY_MODEL=llama3:8b                       # ~4.7GB VRAM
```

**Issue:** `deepseek-coder-v2:16b` uses ~9GB VRAM alone! This is why V1 might have memory issues.

### V2 Configuration (Optimized)
```bash
CYPHER_MODEL=qwen2.5-coder:7b      # ✅ 4.7GB VRAM (better fit)
PLANNER_MODEL=llama3.2:3b          # ✅ 2GB VRAM
VALIDATOR_MODEL=llama3.2:3b        # ✅ 2GB VRAM
ANALYST_MODEL=llama3:8b            # ✅ 4.7GB VRAM
```

**Improvement:** Max 4.7GB vs V1's 9GB peak → much safer!

---

## Performance Expectations

### RTX 3080 10GB (Your Setup)

| Agent | Model | Inference Time | VRAM |
|-------|-------|----------------|------|
| Planner | llama3.2:3b | 2-4s | 2GB |
| Cypher Specialist | qwen2.5-coder:7b | 5-8s | 4.7GB |
| Validator | llama3.2:3b | 2-4s | 2GB |
| Analyst | llama3:8b | 6-10s | 4.7GB |

**Total Pipeline:** ~15-25s for complex queries
**Model Swap Time:** ~5-10s when switching between models

### With OLLAMA_KEEP_ALIVE=60

If same agent called within 60s → **NO reload time** → instant response!

---

## Troubleshooting

### Issue: "CUDA out of memory"

**Solution 1:** Aggressive unload
```bash
OLLAMA_KEEP_ALIVE=0
```

**Solution 2:** Smaller models
```bash
CYPHER_MODEL=llama3.2:3b  # Downgrade from 7b
ANALYST_MODEL=llama3.2:3b  # Downgrade from 8b
```

**Solution 3:** Close other GPU applications
```bash
# Check what's using GPU
nvidia-smi

# Close browser tabs, Discord, etc.
```

### Issue: "Model loading is slow"

**Expected:** First load takes 5-10s (normal)

**If consistently slow:**
- Check disk speed (models loaded from disk)
- Ensure Ollama server has enough CPU resources

### Issue: "Agent pipeline times out"

**Increase timeout in llm_provider.py:**
```python
async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minutes
```

---

## Summary

### ✅ You're Good to Go!

1. **Your RTX 3080 10GB is sufficient** for all Phase 1 models
2. **Ollama auto-manages VRAM** - no manual unloading needed
3. **Peak VRAM usage: 4.7GB** - well within 10GB limit
4. **Recommended setting:** `OLLAMA_KEEP_ALIVE=60`

### Recommended Next Steps

1. Keep default V2 model configuration
2. Add `OLLAMA_KEEP_ALIVE=60` to `.env`
3. Run `./setup_ollama.sh` to pull models
4. Monitor VRAM with `nvidia-smi` during first pipeline run
5. Adjust `OLLAMA_KEEP_ALIVE` if needed

---

## Quick Reference

| Scenario | OLLAMA_KEEP_ALIVE | Trade-off |
|----------|-------------------|-----------|
| **Default** | `300` (5min) | Balanced |
| **Your GPU (Recommended)** | `60` (1min) | Fast + Safe |
| **Max Performance** | `300` or `-1` | Faster, more VRAM |
| **Min VRAM** | `0` (instant unload) | Slower, safest |
| **Multitasking** | `0` or `30` | Free VRAM quickly |

**Your Optimal:** `OLLAMA_KEEP_ALIVE=60` ✅
