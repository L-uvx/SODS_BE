import json
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.license_gen import _generate_key_pair, generate_license


@pytest.fixture
def key_pair():
    return _generate_key_pair()


@pytest.fixture
def valid_license_data(key_pair):
    private_key, _ = key_pair
    return generate_license(
        customer="TestCustomer",
        machine_code="A1B2-C3D4-E5F6-G7H8",
        private_key_pem=private_key,
        expire_date="2099-12-31",
    )


@pytest.fixture
def license_file(valid_license_data):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(valid_license_data, f)
        path = f.name
    yield Path(path)
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


class TestLoadLicense:
    def test_returns_none_for_missing_file(self):
        from app.core.license import load_license

        assert load_license("nonexistent_file_xyz123.json") is None

    def test_returns_none_for_invalid_json(self, tmp_path):
        from app.core.license import load_license

        p = tmp_path / "bad.json"
        p.write_text("not valid json{{{{")
        assert load_license(str(p)) is None

    def test_returns_none_for_missing_required_field(
        self, tmp_path, valid_license_data
    ):
        from app.core.license import load_license

        required = ["customer", "machine_code", "issue_date", "expire_date", "signature"]
        for field in required:
            data = {k: v for k, v in valid_license_data.items()}
            del data[field]
            p = tmp_path / f"missing_{field}.json"
            p.write_text(json.dumps(data))
            assert load_license(str(p)) is None, f"Should return None when '{field}' is missing"

    def test_returns_dict_for_valid_license(self, license_file):
        from app.core.license import load_license

        result = load_license(str(license_file))
        assert isinstance(result, dict)
        assert result["customer"] == "TestCustomer"
        assert "signature" in result

    def test_returns_none_when_field_is_null(self, tmp_path):
        from app.core.license import load_license

        for field in ("customer", "machine_code", "signature"):
            data = {
                "customer": "Test",
                "machine_code": "ABC",
                "issue_date": "2024-01-01",
                "expire_date": None,
                "signature": "sig",
            }
            data[field] = None
            p = tmp_path / f"null_{field}.json"
            p.write_text(json.dumps(data))
            assert load_license(str(p)) is None, f"Should return None when '{field}' is None"


class TestValidateLicense:
    def test_passes_for_valid_license(self, key_pair, valid_license_data, monkeypatch):
        import app.core.license as lic_mod
        from app.core.license import validate_license

        _, public_key = key_pair
        monkeypatch.setattr(lic_mod, "_PUBLIC_KEY_PEM", public_key)

        valid, msg = validate_license(
            valid_license_data,
            "a1b2c3d4e5f6g7h8",
        )
        assert valid is True
        assert "有效" in msg

    def test_fails_for_mismatched_machine_code(self, key_pair, valid_license_data):
        from app.core.license import validate_license

        valid, msg = validate_license(
            valid_license_data,
            "differentmachine",
        )
        assert valid is False
        assert "机器码" in msg

    def test_fails_for_expired_license(self, key_pair):
        from app.core.license import validate_license

        private_key, public_key = key_pair
        past_date = (date.today() - timedelta(days=30)).isoformat()
        expired_license = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
            expire_date=past_date,
        )
        valid, msg = validate_license(
            expired_license, "abc123"
        )
        assert valid is False
        assert "过期" in msg

    def test_passes_for_permanent_license(self, key_pair, monkeypatch):
        import app.core.license as lic_mod
        from app.core.license import validate_license

        private_key, public_key = key_pair
        monkeypatch.setattr(lic_mod, "_PUBLIC_KEY_PEM", public_key)

        permanent_license = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
        )
        valid, msg = validate_license(
            permanent_license, "abc123"
        )
        assert valid is True

    def test_fails_for_tampered_signature(self, key_pair, monkeypatch):
        import app.core.license as lic_mod
        from app.core.license import validate_license

        private_key, public_key = key_pair
        monkeypatch.setattr(lic_mod, "_PUBLIC_KEY_PEM", public_key)

        license_data = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
        )
        license_data["customer"] = "Hacker"
        valid, msg = validate_license(
            license_data, "abc123"
        )
        assert valid is False
        assert "签名" in msg

    def test_fails_with_wrong_public_key(self, key_pair):
        from app.core.license import validate_license

        private_key, _ = key_pair
        license_data = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
        )
        valid, msg = validate_license(
            license_data, "abc123"
        )
        assert valid is False

    def test_machine_code_case_insensitive(self, key_pair, monkeypatch):
        import app.core.license as lic_mod
        from app.core.license import validate_license

        private_key, public_key = key_pair
        monkeypatch.setattr(lic_mod, "_PUBLIC_KEY_PEM", public_key)

        license_data = generate_license(
            customer="Test",
            machine_code="a1b2C3D4",
            private_key_pem=private_key,
        )
        valid, _ = validate_license(
            license_data, "A1B2c3d4"
        )
        assert valid is True

    def test_machine_code_normalizes_separators(self, key_pair, monkeypatch):
        import app.core.license as lic_mod
        from app.core.license import validate_license

        private_key, public_key = key_pair
        monkeypatch.setattr(lic_mod, "_PUBLIC_KEY_PEM", public_key)

        license_data = generate_license(
            customer="Test",
            machine_code="A1B2-C3D4",
            private_key_pem=private_key,
        )
        valid, _ = validate_license(
            license_data, "a1b2c3d4"
        )
        assert valid is True

    def test_empty_expire_date_treated_as_permanent(self, key_pair, monkeypatch):
        import app.core.license as lic_mod
        from app.core.license import validate_license

        private_key, public_key = key_pair
        monkeypatch.setattr(lic_mod, "_PUBLIC_KEY_PEM", public_key)

        license_data = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
        )
        license_data["expire_date"] = ""
        valid, msg = validate_license(
            license_data, "abc123"
        )
        assert valid is True

    def test_invalid_expire_date_format_returns_false(self, key_pair):
        from app.core.license import validate_license

        private_key, public_key = key_pair
        license_data = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
        )
        license_data["expire_date"] = "not-a-valid-date"
        valid, msg = validate_license(
            license_data, "abc123"
        )
        assert valid is False
        assert "到期日期格式无效" in msg


class TestVerifySignature:
    def test_empty_signature_returns_false(self):
        from app.core.license import _verify_signature

        result = _verify_signature("test message", "")
        assert result is False

    def test_invalid_base64_signature_returns_false(self):
        from app.core.license import _verify_signature

        result = _verify_signature("test", "!!!not-base64!!!")
        assert result is False

    def test_valid_signature_passes(self, key_pair, monkeypatch):
        import app.core.license as lic_mod
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        import base64

        private_key_pem, public_key_pem = key_pair
        monkeypatch.setattr(lic_mod, "_PUBLIC_KEY_PEM", public_key_pem)

        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )
        message = "test|payload|data"
        sig = private_key.sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())
        sig_b64 = base64.b64encode(sig).decode()

        assert lic_mod._verify_signature(message, sig_b64) is True


class TestComputeMachineCode:
    def test_produces_16_char_hex(self):
        from app.core.license import _compute_machine_code

        macs = ["00:11:22:33:44:55", "AA:BB:CC:DD:EE:FF"]
        result = _compute_machine_code(macs)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_output_for_same_macs_different_order(self):
        from app.core.license import _compute_machine_code

        macs_a = ["BB:BB:BB:BB:BB:BB", "AA:AA:AA:AA:AA:AA", "CC:CC:CC:CC:CC:CC"]
        macs_b = ["CC:CC:CC:CC:CC:CC", "AA:AA:AA:AA:AA:AA", "BB:BB:BB:BB:BB:BB"]
        assert _compute_machine_code(macs_a) == _compute_machine_code(macs_b)

    def test_returns_empty_for_empty_list(self):
        from app.core.license import _compute_machine_code

        assert _compute_machine_code([]) == ""

    def test_deterministic_output(self):
        from app.core.license import _compute_machine_code

        macs = ["00:11:22:33:44:55"]
        a = _compute_machine_code(macs)
        b = _compute_machine_code(macs)
        assert a == b

    def test_normalizes_mac_case(self):
        from app.core.license import _compute_machine_code

        a = _compute_machine_code(["AA:BB:CC:DD:EE:FF"])
        b = _compute_machine_code(["aa:bb:cc:dd:ee:ff"])
        assert a == b

    def test_different_macs_produce_different_codes(self):
        from app.core.license import _compute_machine_code

        a = _compute_machine_code(["00:11:22:33:44:55"])
        b = _compute_machine_code(["FF:EE:DD:CC:BB:AA"])
        assert a != b


class TestIsLicenseValid:
    def test_returns_false_for_missing_file(self):
        from app.core.license import is_license_valid

        assert is_license_valid("nonexistent_file_xyz999.json") is False

    def test_cache_works(self, monkeypatch, tmp_path):
        from app.core.license import is_license_valid
        import app.core.license as lic_mod

        p = tmp_path / "test.license"
        p.write_text("{}")

        call_count = 0
        original_load = lic_mod.load_license

        def counting_load(path):
            nonlocal call_count
            call_count += 1
            return original_load(path)

        monkeypatch.setattr(lic_mod, "load_license", counting_load)

        is_license_valid(str(p))
        assert call_count == 1

        is_license_valid(str(p))
        assert call_count == 1  # cached, no second load

    def test_cache_expires_after_ttl(self, monkeypatch, tmp_path):
        from app.core.license import is_license_valid
        import app.core.license as lic_mod

        p = tmp_path / "test2.license"
        p.write_text("{}")

        call_count = 0
        original_load = lic_mod.load_license

        def counting_load(path):
            nonlocal call_count
            call_count += 1
            return original_load(path)

        monkeypatch.setattr(lic_mod, "load_license", counting_load)
        monkeypatch.setattr(lic_mod, "_CACHE_TTL_SECONDS", 0)

        is_license_valid(str(p))
        assert call_count == 1

        is_license_valid(str(p))
        assert call_count == 2  # cache expired
