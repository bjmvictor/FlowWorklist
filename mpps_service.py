#!/usr/bin/env python3
import atexit
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

# Workaround for broken NumPy builds on some Windows/Python setups.
# pydicom/pynetdicom flows used here can run without NumPy.
if os.environ.get('FLOWWORKLIST_DISABLE_NUMPY', '1') == '1':
    sys.modules.setdefault('numpy', None)

from pydicom.uid import UID
from pynetdicom import AE, evt

from mpps_actions import execute_mpps_actions, merge_mpps_config


BASE_DIR = Path(__file__).parent
LOCK_FILE = BASE_DIR / "mpps_server.lock"
CONFIG_FILE = BASE_DIR / "config.json"


def _configure_logging():
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "mpps_service.log"
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=50 * 1024 * 1024,
        backupCount=1,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def _write_lock():
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _cleanup_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _load_cfg() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        raise RuntimeError(f"Missing config file: {CONFIG_FILE}")
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise RuntimeError("config.json must be a JSON object")
    return cfg


def _safe_ae_title(raw: Any) -> str:
    try:
        if isinstance(raw, bytes):
            return raw.decode(errors="ignore").strip()
        return str(raw).strip()
    except Exception:
        return ""


def _event_payload(event, dataset_obj) -> Dict[str, Any]:
    req = getattr(event, "request", None)
    assoc = getattr(event, "assoc", None)
    calling_ae = ""
    called_ae = ""
    try:
        if assoc and getattr(assoc, "requestor", None):
            calling_ae = _safe_ae_title(getattr(assoc.requestor, "ae_title", ""))
        if assoc and getattr(assoc, "acceptor", None):
            called_ae = _safe_ae_title(getattr(assoc.acceptor, "ae_title", ""))
    except Exception:
        pass

    payload = {
        "event_timestamp": datetime.now().isoformat(),
        "calling_ae": calling_ae,
        "called_ae": called_ae,
        "affected_sop_instance_uid": str(getattr(req, "AffectedSOPInstanceUID", "") or ""),
        "requested_sop_instance_uid": str(getattr(req, "RequestedSOPInstanceUID", "") or ""),
    }
    payload["sop_instance_uid"] = (
        payload.get("affected_sop_instance_uid")
        or payload.get("requested_sop_instance_uid")
        or ""
    )

    # Common MPPS fields when present
    if dataset_obj is not None:
        for key in (
            "Modality",
            "PerformedProcedureStepStatus",
            "PerformedProcedureStepID",
            "StudyInstanceUID",
            "PatientID",
            "AccessionNumber",
            "PerformedStationAETitle",
        ):
            try:
                if key in dataset_obj:
                    payload[key] = str(dataset_obj.get(key) or "")
            except Exception:
                pass

    return payload


def _flatten_any(obj: Any, prefix: str = "", out: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            _flatten_any(v, p, out)
        return out
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            _flatten_any(v, p, out)
        return out
    out[prefix] = obj
    if "." in prefix:
        out[prefix.split(".")[-1]] = obj
    return out


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _pick_first(flat: Dict[str, Any], keys: list[str]) -> str:
    for k in keys:
        v = flat.get(k)
        if _is_non_empty(v):
            return str(v).strip()
        lk = k.lower()
        for fk, fv in flat.items():
            fks = str(fk)
            if fks.lower() == lk or fks.lower().endswith("." + lk):
                if _is_non_empty(fv):
                    return str(fv).strip()
    return ""


def _dataset_to_debug_dict(ds: Any) -> Dict[str, Any]:
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
                        seq_items.append(_dataset_to_debug_dict(item))
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


class MPPSService:
    MPPS_SOP_CLASS_UID = UID("1.2.840.10008.3.1.2.3.3")

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.mpps_cfg = merge_mpps_config(cfg.get("mpps"), BASE_DIR)
        self.db_cfg = cfg.get("database", {}) if isinstance(cfg.get("database"), dict) else {}
        self.stop_event = threading.Event()
        self.server = None
        self._context_by_sop_uid: Dict[str, Dict[str, str]] = {}

    def _extract_context(self, payload: Dict[str, Any], dataset_obj: Any) -> Dict[str, str]:
        raw_ds = _dataset_to_debug_dict(dataset_obj)
        flat = _flatten_any({"payload": payload, "dataset": raw_ds})
        return {
            "AccessionNumber": _pick_first(flat, [
                "AccessionNumber",
                "RequestedProcedureID",
                "ScheduledProcedureStepID",
                "RequestedProcedureStepID",
                "StudyID",
                "PlacerOrderNumberImagingServiceRequest",
                "FillerOrderNumberImagingServiceRequest",
            ]),
            "PatientID": _pick_first(flat, ["PatientID"]),
            "StudyInstanceUID": _pick_first(flat, ["StudyInstanceUID"]),
            "Modality": _pick_first(flat, ["Modality"]),
        }

    def _merge_payload_with_context(self, payload: Dict[str, Any], context: Dict[str, str]) -> Dict[str, Any]:
        merged = dict(payload or {})
        for key in ("AccessionNumber", "PatientID", "StudyInstanceUID", "Modality"):
            if not _is_non_empty(merged.get(key)) and _is_non_empty(context.get(key)):
                merged[key] = context.get(key)
        return merged

    def _is_calling_allowed(self, event) -> bool:
        listener = self.mpps_cfg.get("listener") or {}
        if listener.get("accept_any_calling_aet", True):
            return True
        expected = str(listener.get("calling_aet") or "").strip().upper()
        if not expected:
            return True
        calling = ""
        try:
            if event.assoc and event.assoc.requestor:
                calling = _safe_ae_title(event.assoc.requestor.ae_title).upper()
        except Exception:
            pass
        return calling == expected

    def _handle_n_create(self, event):
        if not self._is_calling_allowed(event):
            return 0x0124, None  # Refused: Not authorized
        dataset_obj = getattr(event, "attribute_list", None)
        payload = _event_payload(event, dataset_obj)
        sop_uid = str(payload.get("sop_instance_uid") or "").strip()
        if sop_uid:
            self._context_by_sop_uid[sop_uid] = self._extract_context(payload, dataset_obj)
        if self.mpps_cfg.get("debug_output"):
            logging.info("MPPS DEBUG N-CREATE payload: %s", json.dumps(payload, ensure_ascii=False))
            logging.info(
                "MPPS DEBUG N-CREATE dataset: %s",
                json.dumps(_dataset_to_debug_dict(dataset_obj), ensure_ascii=False),
            )
        result = execute_mpps_actions(self.mpps_cfg, self.db_cfg, "N-CREATE", payload, dataset_obj, root_dir=BASE_DIR)
        if self.mpps_cfg.get("debug_output"):
            logging.info("MPPS DEBUG N-CREATE action-result: %s", json.dumps(result, ensure_ascii=False))
        if not result.get("ok", True):
            logging.error("MPPS N-CREATE action errors: %s", result)
        return 0x0000, None

    def _handle_n_set(self, event):
        if not self._is_calling_allowed(event):
            return 0x0124, None
        dataset_obj = getattr(event, "modification_list", None)
        payload = _event_payload(event, dataset_obj)
        sop_uid = str(payload.get("sop_instance_uid") or "").strip()
        if sop_uid and sop_uid in self._context_by_sop_uid:
            payload = self._merge_payload_with_context(payload, self._context_by_sop_uid[sop_uid])
        elif sop_uid:
            # Update cache even if incomplete; useful when modality sends staggered content.
            self._context_by_sop_uid[sop_uid] = self._extract_context(payload, dataset_obj)
        if self.mpps_cfg.get("debug_output"):
            logging.info("MPPS DEBUG N-SET payload: %s", json.dumps(payload, ensure_ascii=False))
            logging.info(
                "MPPS DEBUG N-SET dataset: %s",
                json.dumps(_dataset_to_debug_dict(dataset_obj), ensure_ascii=False),
            )
        result = execute_mpps_actions(self.mpps_cfg, self.db_cfg, "N-SET", payload, dataset_obj, root_dir=BASE_DIR)
        if self.mpps_cfg.get("debug_output"):
            logging.info("MPPS DEBUG N-SET action-result: %s", json.dumps(result, ensure_ascii=False))
        if not result.get("ok", True):
            logging.error("MPPS N-SET action errors: %s", result)
        return 0x0000, None

    def run(self):
        listener = self.mpps_cfg.get("listener") or {}
        host = str(listener.get("host") or "0.0.0.0")
        port = int(listener.get("port") or 4101)
        aet = str(listener.get("aet") or "FLOWMPPS")

        ae = AE(ae_title=aet.encode("ascii", errors="ignore"))
        ae.add_supported_context(self.MPPS_SOP_CLASS_UID)
        handlers = [
            (evt.EVT_N_CREATE, self._handle_n_create),
            (evt.EVT_N_SET, self._handle_n_set),
        ]
        logging.info("Starting MPPS SCP on %s:%s (AE=%s)", host, port, aet)
        logging.info("MPPS debug_output=%s", "ON" if self.mpps_cfg.get("debug_output") else "OFF")
        self.server = ae.start_server((host, port), block=False, evt_handlers=handlers)
        while not self.stop_event.is_set():
            time.sleep(0.5)
        try:
            if self.server:
                self.server.shutdown()
        except Exception:
            pass
        logging.info("MPPS SCP stopped")

    def stop(self):
        self.stop_event.set()


def main():
    _configure_logging()
    _write_lock()
    atexit.register(_cleanup_lock)
    try:
        cfg = _load_cfg()
        mpps_cfg = merge_mpps_config(cfg.get("mpps"), BASE_DIR)
        if not mpps_cfg.get("enabled"):
            logging.info("MPPS disabled in config; exiting.")
            return
        service = MPPSService(cfg)
        service.run()
    except Exception as e:
        logging.exception("MPPS service fatal error: %s", e)
        raise


if __name__ == "__main__":
    main()
