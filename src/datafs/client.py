import json
from dataclasses import dataclass, field
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class DatafsError(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"{code}: {message}" if message else code)
        self.status = status
        self.code = code
        self.message = message


@dataclass
class ServerEvent:
    domain: str
    name: str
    url: str = ""
    referrer: str = ""
    props: dict = field(default_factory=dict)
    ip: str = ""
    user_agent: str = ""
    visitor_key: str = ""
    timestamp: str = ""
    idempotency_key: str = ""

    def as_dict(self):
        raw = {
            "domain": self.domain,
            "name": self.name,
            "url": self.url,
            "referrer": self.referrer,
            "props": self.props,
            "ip": self.ip,
            "user_agent": self.user_agent,
            "visitor_key": self.visitor_key,
            "timestamp": self.timestamp,
            "idempotency_key": self.idempotency_key,
        }
        return {key: value for key, value in raw.items() if value}


@dataclass
class Timeseries:
    from_: str
    to: str
    interval: str
    totals: dict
    points: list
    stale: bool = False
    rollup_freshness: str = ""


@dataclass
class Breakdown:
    from_: str
    to: str
    dimension: str
    rows: list


@dataclass
class Realtime:
    visitors: int


@dataclass
class Funnel:
    day: str
    steps: list


class Client:
    def __init__(self, base_url, api_key, timeout=15):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def version(self):
        return self._request("GET", "/api/v1/version")

    def server_event(self, event: ServerEvent):
        body = self._request("POST", "/api/v1/server-event", body=event.as_dict())
        return body["event_id"]

    def timeseries(self, site_id, from_, to, interval="day"):
        body = self._request(
            "GET",
            f"/api/v1/sites/{site_id}/timeseries",
            query={"from": from_, "to": to, "interval": interval},
        )
        return Timeseries(
            body["from"],
            body["to"],
            body["interval"],
            body["totals"],
            body.get("points", []),
            body.get("stale", False),
            body.get("rollup_freshness", ""),
        )

    def breakdown(self, site_id, from_, to, dimension, limit=100, country=""):
        query = {"from": from_, "to": to, "dimension": dimension, "limit": str(limit)}
        if country:
            query["country"] = country
        body = self._request("GET", f"/api/v1/sites/{site_id}/breakdown", query=query)
        return Breakdown(body["from"], body["to"], body["dimension"], body.get("rows", []))

    def realtime(self, site_id):
        body = self._request("GET", f"/api/v1/sites/{site_id}/realtime")
        return Realtime(body["visitors"])

    def funnel(self, site_id, day, steps):
        body = self._request("POST", f"/api/v1/sites/{site_id}/funnel", body={"day": day, "steps": steps})
        return Funnel(body["day"], body["steps"])

    def _request(self, method, path, query=None, body=None):
        url = self.base_url + path
        if query:
            url += "?" + urlencode(query)
        data = None
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as res:
                raw = res.read()
                if not raw:
                    return None
                return json.loads(raw)
        except HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
            raise DatafsError(exc.code, payload.get("error", str(exc.code)), payload.get("message", "")) from None
