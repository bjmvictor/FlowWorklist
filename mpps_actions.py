import json
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def actions_dir(root_dir: Path) -> Path:
    p = Path(root_dir) / "mpps-actions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_action_id(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")
    return text or "action"


def default_action_config() -> Dict[str, Any]:
    return {
        "id": "",
        "name": "",
        "enabled": True,
        "mode": "none",  # none|api|sql|both
        "trigger_events": ["N-CREATE", "N-SET"],
        "trigger_statuses": [],
        "modality_filter_mode": "ANY",  # ANY|CT|CR|CUSTOM
        "trigger_modalities": [],       # used when modality_filter_mode=CUSTOM
        "include_raw_dataset": True,
        "api": {
            "url": "",
            "method": "POST",
            "headers_json": "{}",
            "timeout_seconds": 10,
            "payload_template_json": "{}",
        },
        "sql": {
            "on_n_create": "",
            "on_n_set": "",
        },
    }


def normalize_action_config(action_cfg: Dict[str, Any]) -> Dict[str, Any]:
    base = default_action_config()
    incoming = action_cfg if isinstance(action_cfg, dict) else {}
    api_cfg = incoming.get("api") if isinstance(incoming.get("api"), dict) else {}
    sql_cfg = incoming.get("sql") if isinstance(incoming.get("sql"), dict) else {}

    base["id"] = _safe_action_id(str(incoming.get("id", "")))
    base["name"] = str(incoming.get("name", "")).strip() or base["id"] or "action"
    base["enabled"] = _to_bool(incoming.get("enabled"), True)
    base["mode"] = str(incoming.get("mode", "none")).strip().lower() or "none"

    trig_events = incoming.get("trigger_events")
    if isinstance(trig_events, list):
        base["trigger_events"] = [str(x).strip().upper() for x in trig_events if str(x).strip()]
    elif isinstance(trig_events, str):
        base["trigger_events"] = [s.strip().upper() for s in trig_events.split(",") if s.strip()]

    trig_statuses = incoming.get("trigger_statuses")
    if isinstance(trig_statuses, list):
        base["trigger_statuses"] = [str(x).strip().upper() for x in trig_statuses if str(x).strip()]
    elif isinstance(trig_statuses, str):
        base["trigger_statuses"] = [s.strip().upper() for s in trig_statuses.split(",") if s.strip()]

    modality_mode = str(incoming.get("modality_filter_mode", base["modality_filter_mode"])).strip().upper()
    if modality_mode not in ("ANY", "CT", "CR", "CUSTOM"):
        modality_mode = "ANY"
    base["modality_filter_mode"] = modality_mode

    trig_modalities = incoming.get("trigger_modalities")
    if isinstance(trig_modalities, list):
        base["trigger_modalities"] = [str(x).strip().upper() for x in trig_modalities if str(x).strip()]
    elif isinstance(trig_modalities, str):
        base["trigger_modalities"] = [s.strip().upper() for s in trig_modalities.split(",") if s.strip()]

    base["include_raw_dataset"] = _to_bool(incoming.get("include_raw_dataset"), True)
    base["api"]["url"] = str(api_cfg.get("url", "")).strip()
    base["api"]["method"] = str(api_cfg.get("method", "POST")).strip().upper() or "POST"
    base["api"]["headers_json"] = str(api_cfg.get("headers_json", "{}"))
    base["api"]["timeout_seconds"] = int(api_cfg.get("timeout_seconds", 10) or 10)
    base["api"]["payload_template_json"] = str(api_cfg.get("payload_template_json", "{}"))
    base["sql"]["on_n_create"] = str(sql_cfg.get("on_n_create", "")).strip()
    base["sql"]["on_n_set"] = str(sql_cfg.get("on_n_set", "")).strip()

    return base


def save_action_file(root_dir: Path, action_cfg: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_action_config(action_cfg)
    if not normalized.get("id"):
        normalized["id"] = _safe_action_id(normalized.get("name") or "action")
    path = actions_dir(root_dir) / f"{normalized['id']}.json"
    path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    return normalized


def load_action_file(root_dir: Path, action_id: str) -> Dict[str, Any] | None:
    aid = _safe_action_id(action_id)
    path = actions_dir(root_dir) / f"{aid}.json"
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        normalized = normalize_action_config(raw)
        if not normalized.get("id"):
            normalized["id"] = aid
        if not normalized.get("name"):
            normalized["name"] = aid
        return normalized
    except Exception:
        return None


def delete_action_file(root_dir: Path, action_id: str) -> bool:
    aid = _safe_action_id(action_id)
    path = actions_dir(root_dir) / f"{aid}.json"
    if not path.exists():
        return False
    path.unlink(missing_ok=True)
    return True


def list_action_files(root_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(actions_dir(root_dir).glob("*.json")):
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
            norm = normalize_action_config(cfg)
            if not norm.get("id"):
                norm["id"] = p.stem
            if not norm.get("name"):
                norm["name"] = p.stem
            out.append(norm)
        except Exception:
            continue
    return out


def default_mpps_config(root_dir: Path) -> Dict[str, Any]:
    test_payload_example = json.dumps(
        {
            "PerformedProcedureStepStatus": "COMPLETED",
            "PerformedProcedureStepID": "MPPS_TEST_001",
            "PatientID": "123456",
            "AccessionNumber": "ACC-20260313-001",
            "StudyInstanceUID": "1.2.826.0.1.3680043.8.498.999.1",
            "calling_ae": "MODALITY_AE"
        },
        indent=2,
        ensure_ascii=False
    )
    return {
        "enabled": False,
        "start_with_worklist": True,
        "debug_output": False,
        "listener": {
            "aet": "FLOWMPPS",
            "host": "0.0.0.0",
            "port": 4101,
            "accept_any_calling_aet": True,
            "calling_aet": "",
        },
        "test_payload_json": test_payload_example,
    }


def merge_mpps_config(cfg: Dict[str, Any], root_dir: Path) -> Dict[str, Any]:
    base = default_mpps_config(root_dir)
    incoming = cfg if isinstance(cfg, dict) else {}
    listener = incoming.get("listener", {}) if isinstance(incoming.get("listener"), dict) else {}

    base["enabled"] = _to_bool(incoming.get("enabled"), base["enabled"])
    base["start_with_worklist"] = _to_bool(incoming.get("start_with_worklist"), base["start_with_worklist"])
    base["debug_output"] = _to_bool(incoming.get("debug_output"), base["debug_output"])

    base["listener"]["aet"] = str(listener.get("aet", base["listener"]["aet"])).strip() or base["listener"]["aet"]
    base["listener"]["host"] = str(listener.get("host", base["listener"]["host"])).strip() or base["listener"]["host"]
    base["listener"]["port"] = int(listener.get("port", base["listener"]["port"]) or base["listener"]["port"])
    base["listener"]["accept_any_calling_aet"] = _to_bool(
        listener.get("accept_any_calling_aet"), base["listener"]["accept_any_calling_aet"]
    )
    base["listener"]["calling_aet"] = str(listener.get("calling_aet", "")).strip()

    # Keep compatibility with old location: mpps.actions.test_payload_json
    legacy_actions = incoming.get("actions") if isinstance(incoming.get("actions"), dict) else {}
    base["test_payload_json"] = str(incoming.get("test_payload_json", legacy_actions.get("test_payload_json", base["test_payload_json"])))

    return base


def _dataset_to_dict(ds: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if ds is None:
        return out

    def _is_scalar_like(v: Any) -> bool:
        # pydicom PersonName behaves like iterable, but should be treated as a single value.
        if isinstance(v, (str, bytes, dict)):
            return True
        return getattr(v, "__class__", type(v)).__name__ in ("PersonName",)

    try:
        for elem in ds:
            key = elem.keyword if getattr(elem, "keyword", None) else str(getattr(elem, "tag", "UNKNOWN"))
            value = elem.value
            if value is None:
                out[key] = None
            elif hasattr(value, "__class__") and value.__class__.__name__ == "Sequence":
                seq_items = []
                for item in value:
                    if hasattr(item, "__iter__"):
                        seq_items.append(_dataset_to_dict(item))
                    else:
                        seq_items.append(str(item))
                out[key] = seq_items
            elif hasattr(value, "__iter__") and not _is_scalar_like(value):
                out[key] = [str(v) for v in value]
            else:
                out[key] = str(value)
    except Exception:
        return out
    return out


def _flatten(obj: Any, prefix: str = "", out: Dict[str, Any] = None) -> Dict[str, Any]:
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else str(k)
            _flatten(v, new_prefix, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_prefix = f"{prefix}[{i}]"
            _flatten(v, new_prefix, out)
    else:
        out[prefix] = obj
        if "." in prefix:
            out[prefix.split(".")[-1]] = obj
    return out


_TPL_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.\[\]-]+)\s*\}\}")
_COLON_TPL_PATTERN = re.compile(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_.\[\]-]*)")

_PLACEHOLDER_FALLBACKS = {
    # Many MPPS send this value as RequestedProcedureID instead of AccessionNumber
    "AccessionNumber": [
        "AccessionNumber",
        "RequestedProcedureID",
        "ScheduledProcedureStepID",
        "RequestedProcedureStepID",
        "StudyID",
        "PlacerOrderNumberImagingServiceRequest",
        "FillerOrderNumberImagingServiceRequest",
    ],
    "PatientID": ["PatientID"],
    "StudyInstanceUID": ["StudyInstanceUID"],
    "OperatorsName": [
        "OperatorsName",
        "PerformingPhysicianName",
        "NameOfPhysiciansReadingStudy",
        "calling_ae",
    ],
}


def _has_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _get_value_case_insensitive(values: Dict[str, Any], key: str) -> Any:
    if key in values:
        return values[key]
    lk = str(key).lower()
    for k, v in values.items():
        if str(k).lower() == lk:
            return v
    return None


def _resolve_placeholder_value(values: Dict[str, Any], key: str) -> Any:
    # 1) Direct (or case-insensitive) key
    direct = _get_value_case_insensitive(values, key)
    if _has_non_empty(direct):
        return direct

    # 2) Last-segment match for nested keys (e.g., dataset.AccessionNumber)
    lk = str(key).lower()
    for k, v in values.items():
        ks = str(k)
        if ks.lower().endswith("." + lk) or ks.lower().endswith("]" + lk):
            if _has_non_empty(v):
                return v

    # 3) Semantic fallbacks (e.g., AccessionNumber <- RequestedProcedureID)
    fallbacks = _PLACEHOLDER_FALLBACKS.get(key, [])
    for fb in fallbacks:
        candidate = _get_value_case_insensitive(values, fb)
        if _has_non_empty(candidate):
            return candidate
        fb_l = str(fb).lower()
        for k, v in values.items():
            ks = str(k).lower()
            if ks.endswith("." + fb_l):
                if _has_non_empty(v):
                    return v
    return direct


def _render_template(template: str, values: Dict[str, Any], sql_mode: bool = False) -> str:
    def repl(match: re.Match) -> str:
        key = match.group(1)
        raw = _resolve_placeholder_value(values, key)
        if raw is None:
            raw = ""
        text = str(raw)
        if sql_mode:
            return text.replace("'", "''")
        return text

    rendered = _TPL_PATTERN.sub(repl, template or "")
    # SQL convenience syntax: :PatientID, :PerformedProcedureStepStatus, etc.
    # Applied only in SQL mode to avoid affecting API URLs and JSON payloads.
    if sql_mode:
        def sql_literal(raw: Any) -> str:
            if raw is None:
                return "NULL"
            if isinstance(raw, bool):
                return "1" if raw else "0"
            if isinstance(raw, (int, float)):
                return str(raw)
            text = str(raw).replace("'", "''")
            return f"'{text}'"

        def colon_repl(match: re.Match) -> str:
            key = match.group(1)
            return sql_literal(_resolve_placeholder_value(values, key))

        rendered = _COLON_TPL_PATTERN.sub(colon_repl, rendered)
    return rendered


def _extract_sql_placeholders(sql_text: str) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for key in _COLON_TPL_PATTERN.findall(sql_text or ""):
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def _should_trigger(action_cfg: Dict[str, Any], event_type: str, flat_payload: Dict[str, Any]) -> Tuple[bool, str]:
    mode = str(action_cfg.get("mode", "none")).strip().lower()
    if mode == "none":
        return False, "Action mode is none"
    if not _to_bool(action_cfg.get("enabled"), True):
        return False, "Action disabled"

    allowed_events = [str(x).strip().upper() for x in (action_cfg.get("trigger_events") or [])]
    ev = str(event_type or "").upper()
    if allowed_events and ev not in allowed_events:
        return False, f"Event {ev} not in trigger_events"

    statuses = [str(x).strip().upper() for x in (action_cfg.get("trigger_statuses") or [])]
    if statuses:
        step_status = str(flat_payload.get("PerformedProcedureStepStatus", "")).strip().upper()
        if not step_status:
            return False, "No PerformedProcedureStepStatus in payload"
        if step_status not in statuses:
            return False, f"Status {step_status} not in trigger_statuses"

    modality_mode = str(action_cfg.get("modality_filter_mode", "ANY")).strip().upper() or "ANY"
    if modality_mode != "ANY":
        modality = str(_resolve_placeholder_value(flat_payload, "Modality") or "").strip().upper()
        if not modality:
            return False, "No Modality in payload"

        if modality_mode == "CT":
            allowed_modalities = ["CT"]
        elif modality_mode == "CR":
            allowed_modalities = ["CR"]
        elif modality_mode == "CUSTOM":
            allowed_modalities = [str(x).strip().upper() for x in (action_cfg.get("trigger_modalities") or []) if str(x).strip()]
            if not allowed_modalities:
                return False, "modality_filter_mode=CUSTOM but trigger_modalities is empty"
        else:
            allowed_modalities = []

        if allowed_modalities and modality not in allowed_modalities:
            return False, f"Modality {modality} not allowed ({', '.join(allowed_modalities)})"

    return True, "Triggered"


def _db_connect(db_cfg: Dict[str, Any]):
    db_type = (db_cfg.get("type") or "oracle").lower()
    dsn = str(db_cfg.get("dsn") or "").strip()
    user = str(db_cfg.get("user") or "").strip()
    password = str(db_cfg.get("password") or "")
    if not all([db_type, dsn, user]):
        raise RuntimeError("Database config incomplete (type/dsn/user)")

    if db_type == "oracle":
        try:
            import oracledb  # type: ignore
            try:
                return "oracledb", oracledb.connect(user=user, password=password, dsn=dsn)
            except Exception as e:
                if "DPY-3015" not in str(e):
                    raise
                lib_dir = str(db_cfg.get("oracle_client_lib_dir") or "").strip()
                if not lib_dir:
                    raise RuntimeError(
                        "DPY-3015: thin mode unsupported password verifier. "
                        "Set database.oracle_client_lib_dir in config.json"
                    ) from e
                try:
                    oracledb.init_oracle_client(lib_dir=lib_dir)
                except Exception as init_err:
                    init_msg = str(init_err).lower()
                    if "already initialized" not in init_msg:
                        raise RuntimeError(
                            f"Failed to initialize Oracle thick mode at '{lib_dir}': {init_err}"
                        ) from e
                return "oracledb", oracledb.connect(user=user, password=password, dsn=dsn)
        except Exception:
            import cx_Oracle  # type: ignore
            return "cx_Oracle", cx_Oracle.connect(user=user, password=password, dsn=dsn)

    if db_type in ("postgres", "postgresql"):
        import psycopg2  # type: ignore
        host_part, dbname = dsn.split("/", 1)
        host, port = host_part.split(":", 1)
        conn = psycopg2.connect(
            host=host.strip(),
            port=int(port),
            dbname=dbname.strip(),
            user=user,
            password=password,
            connect_timeout=10,
        )
        return "psycopg2", conn

    if db_type == "mysql":
        import pymysql  # type: ignore
        host_part, dbname = dsn.split("/", 1)
        host, port = host_part.split(":", 1)
        conn = pymysql.connect(
            host=host.strip(),
            port=int(port),
            database=dbname.strip(),
            user=user,
            password=password,
            connect_timeout=10,
        )
        return "PyMySQL", conn

    raise RuntimeError(f"Unsupported DB type for MPPS action: {db_type}")


def _execute_single_action(
    action_cfg: Dict[str, Any],
    db_cfg: Dict[str, Any],
    event_type: str,
    payload: Dict[str, Any],
    dataset_obj: Any = None,
    debug_output: bool = False,
) -> Dict[str, Any]:
    action_cfg = normalize_action_config(action_cfg)
    mode = str(action_cfg.get("mode", "none")).lower()
    event_type = str(event_type or "").upper()
    payload = payload if isinstance(payload, dict) else {}
    raw_dataset = _dataset_to_dict(dataset_obj) if dataset_obj is not None else {}
    composed_payload: Dict[str, Any] = dict(payload)
    if action_cfg.get("include_raw_dataset"):
        composed_payload["dataset"] = raw_dataset
    composed_payload["_event_type"] = event_type
    flat_payload = _flatten(composed_payload)

    trigger, reason = _should_trigger(action_cfg, event_type, flat_payload)
    if not trigger:
        return {
            "action_id": action_cfg.get("id"),
            "action_name": action_cfg.get("name"),
            "ok": True,
            "skipped": True,
            "reason": reason,
            "results": [],
        }

    results: List[Dict[str, Any]] = []
    overall_ok = True

    if mode in ("api", "both"):
        api_cfg = action_cfg.get("api") or {}
        api_url = str(api_cfg.get("url") or "").strip()
        if api_url:
            method = str(api_cfg.get("method", "POST")).strip().upper() or "POST"
            timeout_seconds = int(api_cfg.get("timeout_seconds", 10) or 10)
            headers_raw = str(api_cfg.get("headers_json", "{}"))
            tpl_raw = str(api_cfg.get("payload_template_json", "{}"))
            try:
                headers = json.loads(_render_template(headers_raw, flat_payload))
                if not isinstance(headers, dict):
                    headers = {}
            except Exception:
                headers = {}

            try:
                rendered_payload_text = _render_template(tpl_raw, flat_payload)
                body_obj = json.loads(rendered_payload_text) if rendered_payload_text.strip() else {}
            except Exception:
                body_obj = composed_payload

            try:
                body = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")
                req = urllib.request.Request(api_url, data=body, method=method)
                req.add_header("Content-Type", "application/json")
                for k, v in headers.items():
                    req.add_header(str(k), str(v))
                with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                    status_code = int(getattr(resp, "status", 200))
                    resp_text = resp.read().decode("utf-8", errors="replace")
                item_ok = 200 <= status_code < 300
                overall_ok = overall_ok and item_ok
                results.append(
                    {
                        "type": "api",
                        "ok": item_ok,
                        "url": api_url,
                        "status_code": status_code,
                        "response": resp_text[:1000],
                        **({"request_body": body_obj, "request_headers": headers} if debug_output else {}),
                    }
                )
            except urllib.error.HTTPError as e:
                overall_ok = False
                results.append(
                    {
                        "type": "api",
                        "ok": False,
                        "url": api_url,
                        "status_code": int(getattr(e, "code", 500)),
                        "error": str(e),
                    }
                )
            except Exception as e:
                overall_ok = False
                results.append({"type": "api", "ok": False, "url": api_url, "error": str(e)})
        else:
            results.append({"type": "api", "ok": True, "skipped": True, "reason": "API URL is empty"})

    if mode in ("sql", "both"):
        sql_cfg = action_cfg.get("sql") or {}
        sql_tpl = str(sql_cfg.get("on_n_create", "") if event_type == "N-CREATE" else sql_cfg.get("on_n_set", ""))
        if sql_tpl.strip():
            placeholder_debug = None
            if debug_output:
                placeholder_debug = {}
                for key in _extract_sql_placeholders(sql_tpl):
                    value = _resolve_placeholder_value(flat_payload, key)
                    placeholder_debug[key] = "" if value is None else str(value)
            sql_text = _render_template(sql_tpl, flat_payload, sql_mode=True)
            conn = None
            cursor = None
            try:
                driver_name, conn = _db_connect(db_cfg or {})
                cursor = conn.cursor()
                cursor.execute(sql_text)
                try:
                    rows = cursor.rowcount
                except Exception:
                    rows = None
                conn.commit()
                results.append({
                    "type": "sql",
                    "ok": True,
                    "driver": driver_name,
                    "rowcount": rows,
                    **({"executed_sql": sql_text} if debug_output else {}),
                    **({"resolved_placeholders": placeholder_debug} if debug_output else {}),
                })
            except Exception as e:
                overall_ok = False
                results.append({
                    "type": "sql",
                    "ok": False,
                    "error": str(e),
                    **({"executed_sql": sql_text} if debug_output else {}),
                    **({"resolved_placeholders": placeholder_debug} if debug_output else {}),
                })
            finally:
                try:
                    if cursor:
                        cursor.close()
                except Exception:
                    pass
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass
        else:
            results.append({"type": "sql", "ok": True, "skipped": True, "reason": "SQL template is empty"})

    for item in results:
        if item.get("ok"):
            logging.info("MPPS action success: %s | %s", action_cfg.get("id"), item.get("type"))
        else:
            logging.error("MPPS action failed: %s | %s | %s", action_cfg.get("id"), item.get("type"), item.get("error"))

    return {
        "action_id": action_cfg.get("id"),
        "action_name": action_cfg.get("name"),
        "ok": overall_ok,
        "skipped": False,
        "reason": reason,
        "results": results,
    }


def execute_mpps_actions(
    mpps_cfg: Dict[str, Any],
    db_cfg: Dict[str, Any],
    event_type: str,
    payload: Dict[str, Any],
    dataset_obj: Any = None,
    root_dir: Path | None = None,
) -> Dict[str, Any]:
    root = Path(root_dir or ".")
    normalized_mpps = merge_mpps_config(mpps_cfg, root)
    debug_output = bool(normalized_mpps.get("debug_output"))

    all_action_results: List[Dict[str, Any]] = []
    overall_ok = True

    action_defs = list_action_files(root)

    # Backward compatibility: old single action block in config.json
    legacy_actions = (mpps_cfg or {}).get("actions") if isinstance((mpps_cfg or {}).get("actions"), dict) else None
    if legacy_actions:
        legacy = normalize_action_config(legacy_actions)
        if not legacy.get("id"):
            legacy["id"] = "legacy"
        if not legacy.get("name"):
            legacy["name"] = "Legacy Action"
        action_defs.append(legacy)

    if not action_defs:
        return {"ok": True, "skipped": True, "reason": "No MPPS actions configured", "actions": []}

    for action in action_defs:
        res = _execute_single_action(action, db_cfg, event_type, payload, dataset_obj, debug_output=debug_output)
        all_action_results.append(res)
        if not res.get("ok", True):
            overall_ok = False

    return {
        "ok": overall_ok,
        "skipped": False,
        "reason": "Executed",
        "actions": all_action_results,
        "mpps_enabled": normalized_mpps.get("enabled"),
        "debug_output": debug_output,
    }
