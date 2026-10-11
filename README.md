# datafs-client

Python client for a self-hosted DataFS install. MIT. Standard library only.

```python
from datafs import Client, ServerEvent

client = Client("https://analytics.example.com", api_key="...")
series = client.timeseries("site-id", "2026-09-12", "2026-10-11")
event_id = client.server_event(ServerEvent(domain="example.com", name="signup"))
```

`server_event` wants an ingest token. The stats methods want a stats API key. See `API.md`.

```
python3 tests/test_client.py
```
