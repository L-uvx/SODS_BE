import base64
import binascii
import hashlib
import json
import os as _os
import subprocess
import time
from datetime import date
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# 便携部署模式：从构建时注入的 _public_key 模块加载公钥。
# 开发模式回退：直接从 tools/public_key.pem 文件读取。
try:
    from app.core._public_key import PUBLIC_KEY_PEM as _PUBLIC_KEY_PEM
except ImportError:
    _KEY_PATH = _os.path.normpath(
        _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)),
            "..", "..", "tools", "public_key.pem",
        )
    )
    if _os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "r", encoding="utf-8") as _f:
            _PUBLIC_KEY_PEM = _f.read().strip()
    else:
        _PUBLIC_KEY_PEM = None

_license_cache: dict[str, tuple[float, bool]] = {}
_CACHE_TTL_SECONDS = 300


def _build_payload(
    customer: str, machine_code: str, issue_date: str, expire_date: str | None
) -> str:
    customer = customer.replace("|", "_")
    machine_code = machine_code.replace("|", "_")
    expire_str = expire_date if expire_date is not None else ""
    return f"{customer}|{machine_code}|{issue_date}|{expire_str}"


def _normalize_machine_code(code: str) -> str:
    return code.replace("-", "").replace(" ", "").lower()


def load_license(license_path: str) -> dict | None:
    p = Path(license_path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    required_fields = {"customer", "machine_code", "issue_date", "expire_date", "signature"}
    if not required_fields.issubset(data.keys()):
        return None
    for field in ("customer", "machine_code", "signature"):
        if not isinstance(data.get(field), str):
            return None
    return data


def validate_license(
    license_data: dict,
    current_machine_code: str,
) -> tuple[bool, str]:
    license_machine = _normalize_machine_code(str(license_data["machine_code"]))
    current_machine = _normalize_machine_code(current_machine_code)
    if license_machine != current_machine:
        return False, "机器码不匹配"

    expire_date = license_data.get("expire_date")
    if expire_date is not None:
        expire_date_str = str(expire_date).strip()
        if expire_date_str == "":
            pass
        else:
            try:
                expire_dt = date.fromisoformat(expire_date_str)
            except (ValueError, TypeError):
                return False, "许可证到期日期格式无效"
            if expire_dt < date.today():
                return False, "许可证已过期"

    payload = _build_payload(
        str(license_data["customer"]),
        str(license_data["machine_code"]),
        str(license_data["issue_date"]),
        expire_date,
    )

    if not _verify_signature(payload, str(license_data["signature"])):
        return False, "签名验证失败"

    return True, "许可证有效"


def _verify_signature(
    message: str,
    signature_b64: str,
) -> bool:
    try:
        public_key = serialization.load_pem_public_key(_PUBLIC_KEY_PEM.encode())
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False
    except (binascii.Error, ValueError):
        return False


def get_current_machine_code() -> str:
    macs = _collect_mac_addresses()
    return _compute_machine_code(macs)


def _collect_mac_addresses() -> list[str]:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_NetworkAdapter |"
                    " Where-Object { $_.PhysicalAdapter -and $_.MACAddress } |"
                    " ForEach-Object { $_.MACAddress }"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.TimeoutExpired, OSError):
        return []


def _compute_machine_code(mac_addresses: list[str]) -> str:
    if not mac_addresses:
        return ""
    normalized = sorted(m.strip().upper().replace(":", "").replace("-", "") for m in mac_addresses)
    joined = "".join(normalized)
    digest = hashlib.sha256(joined.encode()).hexdigest()
    return digest[:16]


def is_license_valid(license_path: str) -> bool:
    now = time.time()
    cached = _license_cache.get(license_path)
    if cached is not None:
        cache_time, result = cached
        if now - cache_time < _CACHE_TTL_SECONDS:
            return result

    license_data = load_license(license_path)
    if license_data is None:
        _license_cache[license_path] = (now, False)
        return False

    machine_code = get_current_machine_code()
    if not machine_code:
        _license_cache[license_path] = (now, False)
        return False

    valid, _ = validate_license(license_data, machine_code)
    _license_cache[license_path] = (now, valid)
    return valid
