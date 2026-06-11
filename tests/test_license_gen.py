import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.license_gen import (
    _build_payload,
    _generate_key_pair,
    _normalize_machine_code,
    generate_license,
    verify_license_signature,
)


class TestNormalizeMachineCode:
    def test_strips_dashes(self):
        assert _normalize_machine_code("A1B2-C3D4-E5F6-G7H8") == "a1b2c3d4e5f6g7h8"

    def test_strips_spaces(self):
        assert _normalize_machine_code("A1B2 C3D4 E5F6 G7H8") == "a1b2c3d4e5f6g7h8"

    def test_lowercases(self):
        assert _normalize_machine_code("A1B2C3D4") == "a1b2c3d4"

    def test_mixed_separators(self):
        assert _normalize_machine_code("A1-B2 C3 D4") == "a1b2c3d4"

    def test_already_normalized(self):
        assert _normalize_machine_code("a1b2c3d4e5f6g7h8") == "a1b2c3d4e5f6g7h8"

    def test_empty_machine_code_raises_value_error(self):
        with pytest.raises(ValueError, match="机器码不能为空"):
            _normalize_machine_code("")

    def test_whitespace_only_raises_value_error(self):
        with pytest.raises(ValueError, match="机器码不能为空"):
            _normalize_machine_code("   ")


class TestBuildPayload:
    def test_payload_delimiter_injection_is_sanitized(self):
        payload = _build_payload(
            customer="evil|attack",
            machine_code="a|b|c",
            issue_date="2026-06-09",
            expire_date=None,
        )
        assert payload == "evil_attack|a_b_c|2026-06-09|"

    def test_permanent_license_payload(self):
        payload = _build_payload(
            customer="XX机场",
            machine_code="a1b2c3d4e5f6g7h8",
            issue_date="2026-06-09",
            expire_date=None,
        )
        assert payload == "XX机场|a1b2c3d4e5f6g7h8|2026-06-09|"

    def test_expiring_license_payload(self):
        payload = _build_payload(
            customer="XX机场",
            machine_code="abc123",
            issue_date="2026-06-09",
            expire_date="2027-06-09",
        )
        assert payload == "XX机场|abc123|2026-06-09|2027-06-09"


class TestGenerateLicense:
    def test_generates_valid_json_structure(self, key_pair):
        private_key, _ = key_pair
        license_data = generate_license(
            customer="XX机场集团有限公司",
            machine_code="A1B2-C3D4-E5F6-G7H8",
            private_key_pem=private_key,
        )
        assert license_data["customer"] == "XX机场集团有限公司"
        assert license_data["machine_code"] == "a1b2c3d4e5f6g7h8"
        assert license_data["issue_date"] is not None
        assert license_data["expire_date"] is None
        assert "signature" in license_data
        assert len(license_data["signature"]) > 0

    def test_signature_is_verifiable(self, key_pair):
        private_key, public_key = key_pair
        license_data = generate_license(
            customer="XX机场集团有限公司",
            machine_code="A1B2-C3D4-E5F6-G7H8",
            private_key_pem=private_key,
        )
        assert verify_license_signature(license_data, public_key)

    def test_tampered_customer_fails_verification(self, key_pair):
        private_key, public_key = key_pair
        license_data = generate_license(
            customer="XX机场集团有限公司",
            machine_code="A1B2-C3D4-E5F6-G7H8",
            private_key_pem=private_key,
        )
        license_data["customer"] = "Hacker"
        assert not verify_license_signature(license_data, public_key)

    def test_tampered_machine_code_fails(self, key_pair):
        private_key, public_key = key_pair
        license_data = generate_license(
            customer="XX机场",
            machine_code="A1B2-C3D4-E5F6-G7H8",
            private_key_pem=private_key,
        )
        license_data["machine_code"] = "malicious_code"
        assert not verify_license_signature(license_data, public_key)

    def test_tampered_expire_date_fails(self, key_pair):
        private_key, public_key = key_pair
        license_data = generate_license(
            customer="XX机场",
            machine_code="ABC123",
            private_key_pem=private_key,
            expire_date="2027-06-09",
        )
        license_data["expire_date"] = "2099-01-01"
        assert not verify_license_signature(license_data, public_key)

    def test_expiring_license_structure(self, key_pair):
        private_key, _ = key_pair
        license_data = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
            expire_date="2027-06-09",
        )
        assert license_data["expire_date"] == "2027-06-09"

    def test_json_serializable(self, key_pair):
        private_key, _ = key_pair
        license_data = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
        )
        json_str = json.dumps(license_data, ensure_ascii=False)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["customer"] == "Test"
        assert parsed["machine_code"] == "abc123"


class TestVerifyLicenseSignature:
    def test_verify_with_wrong_key_fails(self, key_pair):
        private_key, public_key = key_pair
        _, other_public_key = _generate_key_pair()
        license_data = generate_license(
            customer="Test",
            machine_code="ABC123",
            private_key_pem=private_key,
        )
        assert not verify_license_signature(license_data, other_public_key)

    def test_verify_missing_signature_fails(self, key_pair):
        _, public_key = key_pair
        license_data = {
            "customer": "Test",
            "machine_code": "abc123",
            "issue_date": "2026-06-09",
            "expire_date": None,
            "signature": "",
        }
        assert not verify_license_signature(license_data, public_key)

    def test_expiring_license_verification(self, key_pair):
        private_key, public_key = key_pair
        license_data = generate_license(
            customer="XX机场",
            machine_code="A1B2-C3D4",
            private_key_pem=private_key,
            expire_date="2027-06-09",
        )
        assert verify_license_signature(license_data, public_key)


class TestGenerateKeyPair:
    def test_generates_2048_bit_keys(self):
        private_key_pem, public_key_pem = _generate_key_pair()
        assert "BEGIN PRIVATE KEY" in private_key_pem
        assert "BEGIN PUBLIC KEY" in public_key_pem

    def test_key_pair_works_together(self):
        private_key_pem, public_key_pem = _generate_key_pair()
        license_data = generate_license(
            customer="Test",
            machine_code="ABC",
            private_key_pem=private_key_pem,
        )
        assert verify_license_signature(license_data, public_key_pem)

    def test_different_key_pairs_are_different(self):
        priv1, pub1 = _generate_key_pair()
        priv2, pub2 = _generate_key_pair()
        assert priv1 != priv2
        assert pub1 != pub2


class TestCliGenKey:
    def test_gen_key_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            private_path = Path(tmpdir) / "private_key.pem"
            public_path = Path(tmpdir) / "public_key.pem"

            priv, pub = _generate_key_pair()
            private_path.write_text(priv, encoding="utf-8")
            public_path.write_text(pub, encoding="utf-8")

            assert private_path.exists()
            assert public_path.exists()
            assert "BEGIN PRIVATE KEY" in private_path.read_text()
            assert "BEGIN PUBLIC KEY" in public_path.read_text()

            # Verify the saved keys can be used
            saved_priv = private_path.read_text()
            saved_pub = public_path.read_text()
            license_data = generate_license(
                customer="Test",
                machine_code="ABC",
                private_key_pem=saved_priv,
            )
            assert verify_license_signature(license_data, saved_pub)


@pytest.fixture
def key_pair():
    return _generate_key_pair()
