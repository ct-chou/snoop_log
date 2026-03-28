# Risk Register

| ID | Description | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R-001 | railtracks does not exist on PyPI | High | Medium | T-007 checks first; pre-decided fallback to plain async runner in pipeline.py | Open |
| R-002 | Gemini Files API rejects test video (size/format constraints) | Medium | High | Use a real training clip; have a fallback mp4 ready; Files API minimum is ~1 second | Open |
| R-003 | GEMINI_API_KEY not provisioned | Medium | High | Legacy Claude path stays functional as demo fallback | Open |
| R-004 | DO Spaces creds not set | Low | Low | storage.py designed to no-op gracefully; not on critical path | Open |
| R-005 | Gemini JSON output schema drift from dog_system.md spec | Medium | Medium | Add schema validation in gemini_processor.py; fail loudly with diff | Open |
