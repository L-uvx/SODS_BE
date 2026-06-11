import argparse
import base64
import json
import sys
from datetime import date, datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def _normalize_machine_code(machine_code: str) -> str:
    result = machine_code.replace("-", "").replace(" ", "").lower()
    if not result:
        raise ValueError("机器码不能为空")
    return result


def _build_payload(customer: str, machine_code: str, issue_date: str, expire_date: str | None) -> str:
    # 防止分隔符注入：将 customer 和 machine_code 中的 | 替换为 _
    customer = customer.replace("|", "_")
    machine_code = machine_code.replace("|", "_")
    expire_str = expire_date if expire_date is not None else ""
    return f"{customer}|{machine_code}|{issue_date}|{expire_str}"


def generate_license(customer: str, machine_code: str, private_key_pem: str, expire_date: str | None = None) -> dict:
    machine_code = _normalize_machine_code(machine_code)
    issue_date = date.today().isoformat()

    if expire_date is not None:
        try:
            datetime.strptime(expire_date, "%Y-%m-%d")
        except ValueError:
            print("错误: expire_date 格式无效，应为 YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)

    payload = _build_payload(customer, machine_code, issue_date, expire_date)

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None
    )

    signature = private_key.sign(
        payload.encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    signature_b64 = base64.b64encode(signature).decode()

    return {
        "customer": customer,
        "machine_code": machine_code,
        "issue_date": issue_date,
        "expire_date": expire_date,
        "signature": signature_b64,
    }


def verify_license_signature(license_data: dict, public_key_pem: str) -> bool:
    customer = license_data["customer"]
    machine_code = license_data["machine_code"]
    issue_date = license_data["issue_date"]
    expire_date = license_data.get("expire_date")

    payload = _build_payload(customer, machine_code, issue_date, expire_date)

    public_key = serialization.load_pem_public_key(
        public_key_pem.encode()
    )

    signature = base64.b64decode(license_data["signature"])

    try:
        public_key.verify(
            signature,
            payload.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False


def _generate_key_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return private_key_pem, public_key_pem


def main():
    parser = argparse.ArgumentParser(description="SODS 许可证签发工具")
    parser.add_argument("--gen-key", action="store_true", help="生成 RSA 密钥对")
    parser.add_argument("--customer", type=str, help="客户名称")
    parser.add_argument("--machine", type=str, help="机器码")
    parser.add_argument("--expire", type=str, help="到期日期 (YYYY-MM-DD)，不指定则为永久")
    parser.add_argument("--output", type=str, help="输出文件路径，默认输出到标准输出")

    args = parser.parse_args()

    if args.gen_key:
        tool_dir = Path(__file__).resolve().parent
        private_path = tool_dir / "private_key.pem"
        public_path = tool_dir / "public_key.pem"

        if private_path.exists():
            print("密钥文件已存在。如需重新生成，请先删除 private_key.pem 和 public_key.pem。", file=sys.stderr)
            sys.exit(1)

        priv, pub = _generate_key_pair()
        private_path.write_text(priv, encoding="utf-8")
        public_path.write_text(pub, encoding="utf-8")

        print(f"私钥已保存到: {private_path}")
        print(f"公钥已保存到: {public_path}")
        return

    if args.customer and args.machine:
        tool_dir = Path(__file__).resolve().parent
        private_key_path = tool_dir / "private_key.pem"

        if not private_key_path.exists():
            print("错误: 未找到私钥文件。请先运行 --gen-key 生成密钥对。", file=sys.stderr)
            sys.exit(1)

        private_key_pem = private_key_path.read_text(encoding="utf-8")
        license_data = generate_license(
            customer=args.customer,
            machine_code=args.machine,
            private_key_pem=private_key_pem,
            expire_date=args.expire,
        )

        output = json.dumps(license_data, ensure_ascii=False, indent=2)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output, encoding="utf-8")
            print(f"许可证已保存到: {output_path}")
        else:
            print(output)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
