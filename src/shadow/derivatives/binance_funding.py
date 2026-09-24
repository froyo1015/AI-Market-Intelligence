"""Read-only Binance USD-M funding adapter. Standalone shadow output only."""

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .production_validator import (content_hash, milliseconds, validate_output,
                                   unique_pairs, reject_constant)
from .provider_security import (ProviderRequest, ProviderResult, FailureCode,
                                SecurityBoundaryError, EnvironmentSecretAccess)
from .validator import require, digest

PROVIDER = "binance_usdm"
SYMBOLS = {"BTCUSDT": "bitcoin", "ETHUSDT": "ethereum"}
REFS = {s: "instrument:binance-usdm-" + s.lower() + "@1" for s in SYMBOLS}
ROOT = Path(__file__).resolve().parents[3] / "outputs" / "shadow" / "derivatives"
MAX_BODY = 2 * 1024 * 1024
ENDPOINTS = {"exchange": "/fapi/v1/exchangeInfo", "intervals": "/fapi/v1/fundingInfo",
             "BTCUSDT": "/fapi/v1/fundingRate", "ETHUSDT": "/fapi/v1/fundingRate"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def utc_ms(value):
    require(type(value) is int and value >= 0, "invalid timestamp")
    seconds, ms = divmod(value, 1000)
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + f".{ms:03d}Z"


def canonical(value):
    require(isinstance(value, str) and len(value) <= 64 and
            re.fullmatch(r"-?\d+(?:\.\d+)?", value), "invalid rate")
    d = Decimal(value)
    require(d.is_finite(), "invalid rate")
    return "0" if d == 0 else format(d, "f").rstrip("0").rstrip(".") if "." in value else str(d)


def decode(body):
    require(isinstance(body, bytes) and len(body) <= MAX_BODY, "body budget")
    return json.loads(body.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=reject_constant)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PublicTransport:
    """Fixed-host HTTPS GET only; no env proxies, cookies, keys or redirects."""

    endpoints = ENDPOINTS
    host = "https://fapi.binance.com"

    def query(self, name, cutoff):
        return {"symbol": name, "startTime": max(0, cutoff - 72 * 3600000),
                "endTime": cutoff, "limit": 1000} if name in SYMBOLS else {}

    def get(self, name, cutoff, timeout):
        if name not in self.endpoints:
            raise SecurityBoundaryError("endpoint_not_allowlisted")
        params = self.query(name, cutoff)
        query = "?" + urlencode(params) if params else ""
        request = Request(self.host + self.endpoints[name] + query,
                          headers={"Accept": "application/json", "Accept-Encoding": "identity"})
        try:
            started = time.monotonic()
            with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=timeout) as response:
                # Enforce total read time as well as socket timeout; bound body size.
                start, chunks, size = started, [], 0
                while True:
                    if time.monotonic() - start > timeout:
                        raise TimeoutError()
                    chunk = response.read1(min(65536, MAX_BODY + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > MAX_BODY:
                        raise ValueError("body budget")
                return response.status, b"".join(chunks)
        except HTTPError as error:
            status = error.code
            error.close()  # never read/persist/log remote error text
            return status, b""


def classify(status):
    if status in (418, 429):
        return FailureCode.RATE_LIMITED
    if status == 401:
        return FailureCode.AUTHENTICATION_FAILED
    if status in (403, 451) or 300 <= status < 400:
        return FailureCode.ACCESS_DENIED
    return FailureCode.PROVIDER_ERROR if status >= 500 else FailureCode.INVALID_RESPONSE


class BinanceFundingAdapter:
    endpoints = ENDPOINTS
    metric = "funding_rate"
    transport_type = PublicTransport
    provider_id = PROVIDER
    instrument_refs = REFS

    def response_failure(self, parsed):
        return FailureCode.INVALID_RESPONSE if isinstance(parsed, dict) and "code" in parsed else None

    def build(self, *args):
        return assemble(*args)

    def validate(self, artifact):
        return validate_adapter_artifact(artifact)

    def __init__(self, run_id, transport=None, clock=utc_now, monotonic=time.monotonic, sleep=time.sleep):
        require(isinstance(run_id, str) and re.fullmatch(r"[A-Za-z0-9_-]+", run_id), "unsafe run ID")
        self.run_id, self.transport, self.clock = run_id, transport or self.transport_type(), clock
        self.monotonic, self.sleep = monotonic, sleep
        self.artifact = None

    def collect(self, request, secrets):
        # Deliberately never call secrets.get(): these endpoints are public.
        require(request.provider_id == self.provider_id and request.metrics == (self.metric,) and
                set(request.instrument_refs) == set(self.instrument_refs.values()), "unsupported request scope")
        cutoff = self.clock()
        cutoff_ms = milliseconds(cutoff)
        start, last, attempts = self.monotonic(), None, 0
        captures, failures, circuit = {}, {}, None
        for name in self.endpoints:
            if circuit:
                failures[name] = circuit.value
                continue
            failure = FailureCode.BUDGET_EXHAUSTED
            for retry in range(request.max_retries + 1):
                remaining = request.deadline_seconds - (self.monotonic() - start)
                delay = max(0, 1 - (self.monotonic() - last)) if last is not None else 0
                if attempts >= request.max_attempts or remaining <= delay:
                    break
                if delay:
                    self.sleep(delay)
                remaining = request.deadline_seconds - (self.monotonic() - start)
                if remaining <= 0:
                    break
                last, attempts = self.monotonic(), attempts + 1
                try:
                    status, body = self.transport.get(name, cutoff_ms, min(request.timeout_seconds, remaining))
                    if self.monotonic() - start >= request.deadline_seconds:
                        failure = FailureCode.BUDGET_EXHAUSTED
                    elif status == 200:
                        parsed = decode(body)
                        failure = self.response_failure(parsed)
                        if failure is None:
                            captures[name] = {"endpoint": self.endpoints[name], "captured_at": self.clock(),
                                              "sha256": "sha256:" + hashlib.sha256(body).hexdigest(),
                                              "body_base64": base64.b64encode(body).decode("ascii")}
                            failure = None
                    else:
                        failure = classify(status)
                except (TimeoutError, socket.timeout):
                    failure = FailureCode.TIMEOUT
                except (URLError, OSError):
                    failure = FailureCode.NETWORK_ERROR
                except Exception:
                    failure = FailureCode.INVALID_RESPONSE
                if failure in (FailureCode.RATE_LIMITED, FailureCode.ACCESS_DENIED,
                               FailureCode.AUTHENTICATION_FAILED):
                    circuit = failure  # no early retry against a provider cooldown
                if failure not in (FailureCode.TIMEOUT, FailureCode.NETWORK_ERROR, FailureCode.PROVIDER_ERROR):
                    break
            if failure:
                failures[name] = failure.value
        self.artifact = self.build(self.run_id, cutoff, self.clock(), captures, failures)
        result = self.validate(self.artifact)
        require(result.valid, "adapter validation failed")
        failure = next(iter(self.artifact["failures"].values()), None)
        return ProviderResult(tuple("receipt:" + n for n in captures), FailureCode(failure) if failure else None)


def normalize(symbol, documents, cutoff):
    """Closed mapping: retain originals; never pretend normalized JSON is raw HTTP."""
    exchange = documents["exchange"]
    require(isinstance(exchange, dict) and isinstance(exchange.get("symbols"), list), "invalid exchange metadata")
    matches = [s for s in exchange["symbols"] if isinstance(s, dict) and s.get("symbol") == symbol]
    require(len(matches) == 1, "ambiguous instrument")
    meta = matches[0]
    require(meta.get("contractType") == "PERPETUAL" and meta.get("baseAsset") == symbol[:-4] and
            meta.get("quoteAsset") == meta.get("marginAsset") == "USDT", "wrong instrument")
    intervals = documents["intervals"]
    require(isinstance(intervals, list) and all(isinstance(x, dict) for x in intervals), "invalid intervals")
    matches = [x for x in intervals if x.get("symbol") == symbol]
    require(len(matches) <= 1, "ambiguous interval")
    hours = matches[0].get("fundingIntervalHours") if matches else 8
    require(type(hours) is int and 1 <= hours <= 24, "invalid interval")
    rows = documents[symbol]
    require(isinstance(rows, list) and len(rows) >= 2 and len(rows) <= 1000, "insufficient funding history")
    values = {}
    for row in rows:
        require(isinstance(row, dict) and row.get("symbol") == symbol and row.get("rateType", "Regular") == "Regular",
                "invalid funding record")
        t = row.get("fundingTime")
        require(type(t) is int and 0 <= t <= cutoff, "future/invalid funding time")
        value = canonical(row.get("fundingRate"))
        require(t not in values or values[t] == value, "conflicting funding records")
        values[t] = value
    times = sorted(values)
    # Live fundingTime includes small settlement execution jitter (e.g. +4ms,
    # then +2ms). Preserve timestamps; compare interval with a bounded 1s tolerance.
    require(len(times) >= 2 and abs((times[-1] - times[-2]) - hours * 3600000) <= 1000,
            "interval mismatch")
    t = times[-1]
    definition = {"venue_id": "venue:binance-usdm", "native_symbol": symbol, "instrument_type": "perpetual",
                  "base_asset_id": "asset:" + SYMBOLS[symbol], "quote_asset_id": "asset:usdt",
                  "settlement_asset_id": "asset:usdt", "underlying_asset_id": "asset:" + SYMBOLS[symbol],
                  "oi_unit": "base_asset", "counting_basis": "single_side", "funding_interval_seconds": hours * 3600,
                  "funding_rate_kind": "settled", "funding_sign_convention": "positive_long_pays_short",
                  # Definition used ONLY for this observed settlement, not projected backward.
                  "effective_from": utc_ms(t), "effective_to": utc_ms(t + 1)}
    return definition, {"metric": "funding_rate", "symbol": symbol, "value": values[t], "time": t}


def assemble(run_id, requested, evaluated, captures, failures, *, spec=None,
             provider_spec=None, collection_started_at=None):
    """Deterministic normalization receipt bridge into the existing validator."""
    endpoints, normalizer, dependencies, selected_metric, schema, rule, policy = spec or (
        ENDPOINTS, normalize, ("exchange", "intervals"), "funding_rate", "binance_funding_shadow_v1",
        "binance-funding-normalization-v2", "fundingInfo-override-else-default8-history-tolerance1000ms")
    require(re.fullmatch(r"[A-Za-z0-9_-]+", run_id), "unsafe run")
    cutoff, evaluation = milliseconds(requested), milliseconds(evaluated)
    provider, source_id, publisher, venue, symbols, instrument_prefix, observation_prefix = provider_spec or (
        PROVIDER, "source:binance", "Binance", "venue:binance-usdm", SYMBOLS,
        "instrument:binance-usdm-", "derivatives:observation:binance-")
    capture_start = milliseconds(collection_started_at) if collection_started_at else cutoff
    require(capture_start <= cutoff, "collection cutoff order")
    require(evaluation >= cutoff, "clock moved backwards")
    require(set(captures) <= set(endpoints) and set(failures) <= set(endpoints), "unknown capture")
    require(not set(captures) & set(failures), "capture/failure conflict")
    require(all(v in {f.value for f in FailureCode} for v in failures.values()), "unsafe failure")
    docs = {}
    for name, capture in captures.items():
        require(set(capture) == {"endpoint", "captured_at", "sha256", "body_base64"} and
                capture["endpoint"] == endpoints[name], "invalid capture")
        require(capture_start <= milliseconds(capture["captured_at"]) <= evaluation, "capture time out of run")
        body = base64.b64decode(capture["body_base64"], validate=True)
        require(capture["sha256"] == "sha256:" + hashlib.sha256(body).hexdigest(), "capture hash mismatch")
        docs[name] = decode(body)
    output = {"schema_contract": "derivatives_shadow_output_v1", "synthetic": False, "run_id": run_id,
              "requested_cutoff": requested, "evaluation_cutoff": evaluated, "replay_mode": "archived_point_in_time",
              "sources": [{"source_id": source_id, "publisher": publisher, "venue_id": venue,
                           "data_reliability": 1}], "receipts": [], "instruments": [], "observations": [], "coverage": []}
    raw, bridges, symbol_status = {}, [], {}
    final_failures = dict(failures)
    for symbol in symbols:
        deps = (dependencies(symbol) if callable(dependencies) else dependencies) + (symbol,)
        if not all(n in docs for n in deps):
            final_failures[symbol] = failures.get(symbol) or failures.get("exchange") or failures.get("intervals") or "invalid_response"
            symbol_status[symbol] = "unavailable"
            continue
        try:
            definition, measurement = normalizer(symbol, docs, cutoff)
            require(measurement["time"] <= min(milliseconds(captures[n]["captured_at"]) for n in deps
                    if n == symbol), "observation newer than measurement capture")
        except Exception:
            final_failures[symbol] = "invalid_response"
            symbol_status[symbol] = "unavailable"
            continue
        # Both normalized receipts inherit the latest dependency capture time.
        known = max(captures[n]["captured_at"] for n in deps)
        base = "outputs/shadow/derivatives/" + run_id + "/"
        for kind, payload in (("metadata", definition), ("measurement", measurement)):
            name = symbol + "-" + kind
            path = base + name + ".json"
            raw[path] = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            output["receipts"].append({"receipt_id": "receipt:" + name, "source_id": source_id,
                                       "captured_at": known, "path": path,
                                       "sha256": "sha256:" + hashlib.sha256(raw[path]).hexdigest()})
            bridges.append({"normalized_receipt_ref": "receipt:" + name, "rule": rule,
                            "capture_refs": list(deps), "capture_hashes": [captures[n]["sha256"] for n in deps],
                            "symbol": symbol, "interval_policy": policy})
        # Revision identity is scoped by exact definition/capture hash, avoiding overwriting history.
        iid = instrument_prefix + symbol.lower()
        revision = int(digest({"definition": definition, "known": known})[7:19], 16) + 1
        instrument = {"instrument_id": iid, "version": revision, "metadata_receipt_ref": "receipt:" + symbol + "-metadata",
                      "definition_pointer": "", "definition": definition}
        instrument["content_hash"] = content_hash(instrument)
        output["instruments"].append(instrument)
        age = Decimal(evaluation - measurement["time"]) / 1000
        current = age <= (definition["funding_interval_seconds"] + 1800 if selected_metric == "funding_rate" else 7200)
        o = {"schema_contract": "derivatives_production_observation_v1", "synthetic": False,
             "observation_id": observation_prefix + ("oi-" if selected_metric == "open_interest" else "") + symbol + "-" + str(measurement["time"]),
             "version": int(digest({"measurement": measurement, "known": known, "generated": evaluated})[7:19], 16) + 1,
             "instrument_ref": iid + "@" + str(revision), "receipt_ref": "receipt:" + symbol + "-measurement",
             "pointers": {"metric": "/metric", "symbol": "/symbol", "value": "/value", "timestamp": "/time"},
             "metric": selected_metric, "value": measurement["value"],
             "unit": "fraction_per_interval" if selected_metric == "funding_rate" else definition["oi_unit"],
             "native_timestamp": measurement["time"], "native_time_unit": "ms", "source_timestamp": utc_ms(measurement["time"]),
             "retrieved_at": known, "known_at": known, "generated_at": evaluated,
             "freshness": {"age_seconds": canonical(format(age, "f")), "freshness_status": "current" if current else "stale",
                           "policy_id": "production-observation-freshness-v1"},
             "evidence_quality": {"policy_id": "production-observation-quality-v1", "data_reliability": 1,
                                  "timeliness": int(current), "temporal_coverage": 1, "definition_consistency": 1, "score": int(current)}}
        o["content_hash"] = content_hash(o)
        output["observations"].append(o)
        for metric in ("funding_rate", "open_interest", "liquidation_quantity", "long_short_ratio", "positioning_change"):
            output["coverage"].append({"instrument_ref": iid + "@" + str(revision), "metric": metric,
                                       "status": "available" if metric == selected_metric else "unavailable",
                                       "reason": None if metric == selected_metric else "not_collected"})
        symbol_status[symbol] = "available"
    count = len(output["observations"])
    artifact = {"schema_contract": schema, "provider_id": provider,
                "run_id": run_id, "requested_cutoff": requested, "evaluation_cutoff": evaluated,
                "captures": captures, "fetch_failures": failures, "failures": final_failures,
                "symbol_status": symbol_status, "status": "available" if count == 2 else "partial" if count else "unavailable",
                "normalization_receipts": bridges, "observation_output": output,
                "normalized_bytes": {p: base64.b64encode(b).decode("ascii") for p, b in raw.items()}}
    if collection_started_at is not None:
        artifact["collection_started_at"] = collection_started_at
    return artifact


def validate_adapter_artifact(a):
    expected = assemble(a["run_id"], a["requested_cutoff"], a["evaluation_cutoff"], a["captures"], a["fetch_failures"])
    require(a == expected, "normalization bridge mismatch")
    raw = {p: base64.b64decode(b, validate=True) for p, b in a["normalized_bytes"].items()}
    return validate_output(a["observation_output"], raw)


def write_shadow_artifact(artifact, *, validator=validate_adapter_artifact,
                          filename="binance_funding_observations.json"):
    """Exclusive private run directory; validate before writing any bytes."""
    require(filename in ("binance_funding_observations.json", "binance_oi_observations.json"), "unsafe artifact filename")
    require(validator(artifact).valid, "invalid shadow artifact")
    root = ROOT.resolve()
    require(not ROOT.is_symlink() and root == ROOT.absolute(), "unsafe output root")
    root.mkdir(parents=True, exist_ok=True)
    target = root / artifact["run_id"]
    target.mkdir(exist_ok=False, mode=0o700)
    path = target / filename
    temporary = target / "pending.json"
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(artifact, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    return path


def main():
    parser = argparse.ArgumentParser(description="Binance BTC/ETH funding; internal shadow only")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    adapter = BinanceFundingAdapter(args.run_id)
    adapter.collect(ProviderRequest(PROVIDER, tuple(REFS.values()), ("funding_rate",)), EnvironmentSecretAccess(set()))
    write_shadow_artifact(adapter.artifact)
    print(adapter.artifact["status"])


if __name__ == "__main__":
    main()
