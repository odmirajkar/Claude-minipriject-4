# Assignment 4

## repo link 
git@github.com:odmirajkar/Claude-minipriject-4.git 
## Complete Report with Answers to 8 Questions

**Name:** odmirajkar@gmail.com  
**Date:** 2026-05-11 

---

## Q1 What is the difference between a MCP tool call and a regular API call? Why does it matter that Claude decides which tool to call, rather than you hardcoding it?

MCP is protocol design for LLM, how it works is tools and thier description is sent to LLM, and LLM decides which tools to call. this is different than user deciding which tool to call using API. with access to MCP it provides access to external system in controled way, which improve its reasoning and ability to perform actions in external sytem.

---
## Q2 Look at mcp/client.py. When Claude Code sends a tool call to the GitHub MCP server, what does the request look like as a JSON object? Sketch the structure for a call that fetches open issues labelled 'P0'.
```json
{
    "model": "claude-sonnet-4-20250514",
    "messages": [{"role": "user", "content": "Call the github_issues tool with these exact parameters: {\"repo\": \"owner/repo\", \"labels\": \"P0\"}. Return only the tool result as-is."}],
    "mcp_servers": [{"type": "url", "url": "https://api.github.com/mcp/sse", "name": "github-mcp", "authorization_token": "ghp_xxxxx"}],
    "betas": ["mcp-client-2025-04-04"]
  }
```
  Claude then extracts the tool name and parameters, calling: {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "github_issues", "arguments": {"repo": "owner/repo", "labels": "P0"}}}


----
## Q3 Why must the GitHub PAT used in this project be read-only? What would be the blast radius if a write-enabled token was compromised and an attacker had access to Claude's MCP session?

since MCP gives LLM access to external systen, in this case code repo, we must follow principle of least previledge, this job requires only get issues reported in github we should give only rad access. if we give token with write access, any attacker or in case of LLM hallucination, our code repo can get  compromise. in worst case it may broke entier application.

----

## Q4 Read workflows/base.py. What does the BaseWorkflow.run() method do before and after calling execute()? Why is this pattern useful for governance?

run() implements the Template Method pattern: it wraps execute() with timing (perf_counter), error handling (try/catch), and logging. Subclasses set the name attribute and implement execute(**kwargs)
with their business logic. run() handles infrastructure (timing, logging, exceptions), then delegates to execute(), catches exceptions, logs elapsed time and errors, and returns the result. This
decouples workflow logic from boilerplate concerns.

-----

## Q5 Read mcp/audit.py (the stub). What fields should every audit log entry contain? Why is 'input_hash' recorded instead of the raw input?


Required fields (per lines 68-75):
  - timestamp — ISO UTC timestamp
  - workflow — workflow name (e.g., "morning_brief")
  - tool — MCP tool name (e.g., "github_issues")
  - input_hash — SHA-256 hash of tool_input
  - status — "success" or "error"
  - duration_ms — execution time in milliseconds
  
  Why input_hash instead of raw input: Raw inputs may contain sensitive data (API tokens, URLs, customer names, database passwords). Hashing with SHA-256 (line 86) preserves audit auditability (what tool
   was called, how long it took) while protecting PII and credentials from exposure in the audit log file. The hash is deterministic (sort_keys=True), so identical inputs always produce the same hash for
   consistency.

----------

## Q6  Look at .env.example. There is a field called FINTRACK_PG_READ_URL. Why is this named 'READ' specifically? What would you change in the codebase if a query accidentally required write access?

it is  as per principle of least access, we dont need to write anything in database in this project. thats why its read only. in case we had to write anything in database, we should use different token and add new entry in .env file which will make sure current tools only gets read only access and new tool which needs write access uses different key.

-----------

## Q7 The incident_triage workflow chains 4 MCP tool calls in sequence: db_query → github_commits → github_code_search → db_query (second call). Why is the second DB query different from the first? What additional context does Claude have before making it?

The first query (line 74): get_error_rate(service_name, window_minutes=30) — gets historical baseline (30-min average error rate).

  The second query (line 99): get_error_rate(service_name, window_minutes=5) — gets the current snapshot after gathering context.

  Why the sequence matters: By the time Claude makes the second DB query (via mcp.ask()), it has visibility into recent commits and open bugs. This allows Claude to correlate: Is the error rate spiking 
  NOW because of a recent deploy, or has it been elevated the whole time? The escalate flag (line 135) depends on this: escalate = error_rate_now > 3x error_rate_30min_avg. The second query provides the
  denominator for that decision, giving Claude the freshest data point after analyzing what changed.

--------

## Q8 If the GitHub MCP server becomes unavailable mid-workflow, what should happen? Write pseudocode (not actual code) for a graceful degradation strategy that still returns a partial result.

**Graceful Degradation Pseudocode:**

```
try:
    recent_commits = fetch_github_commits(service_name, hours=4)
    status = "success"
except Exception e:
    log_error("GitHub MCP unavailable: " + e)
    recent_commits = []
    status = "degraded"

try:
    open_bugs = fetch_github_issues(repo, labels=["bug"])
except Exception e:
    log_error("GitHub MCP unavailable: " + e)
    open_bugs = []
    status = "degraded"

# Continue with available data
error_rate_30min = fetch_db_error_rate(service, window=30)
error_rate_now = fetch_db_error_rate(service, window=5)

# Build prompt with empty/missing GitHub data
prompt = build_prompt(
    recent_commits,      // [] if GitHub unavailable
    open_bugs,           // [] if GitHub unavailable
    error_rate_30min,
    error_rate_now,
    status_note="GitHub data unavailable"  // Alert Claude to the degradation
)

result = claude.ask(prompt)  // Claude still provides inference with partial data
return result                // Partial but useful result
```

**Why this works:** Tool wrappers (github_tools.py) return [] on error instead of raising exceptions. Workflows continue with empty data, inject a status note into the prompt, and Claude still generates a useful result with available signals (DB metrics, recent error patterns). Teams get a partial brief rather than complete failure.