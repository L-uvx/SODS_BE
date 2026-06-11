from fastapi.testclient import TestClient

import app.core.license as lic_mod
import app.main as main_mod
from app.main import app


class TestLicenseMiddleware:
    def test_health_returns_200_without_license(self, monkeypatch):
        """/health 不校验 license，即使文件不存在也返回 200"""
        monkeypatch.setattr(main_mod, "_LICENSE_FILE", "nonexistent_file_xyz999.json")
        lic_mod._license_cache.clear()

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_non_health_returns_403_without_license(self, monkeypatch):
        """非 /health 路由在无 license 文件时返回 403"""
        monkeypatch.setattr(main_mod, "_LICENSE_FILE", "nonexistent_file_xyz999.json")
        lic_mod._license_cache.clear()

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "License" in data["detail"]

    def test_api_route_returns_403_with_invalid_license(self, monkeypatch, tmp_path):
        """API 路由在 license 内容无效时返回 403"""
        p = tmp_path / "invalid_license.json"
        p.write_text("{}")
        monkeypatch.setattr(main_mod, "_LICENSE_FILE", str(p))
        lic_mod._license_cache.clear()

        client = TestClient(app)
        response = client.get("/polygon-obstacle/bootstrap")
        assert response.status_code == 403
        data = response.json()
        assert "License" in data["detail"]

    def test_health_always_bypasses_license(self, monkeypatch):
        """/health 永远绕过 license 校验"""
        monkeypatch.setattr(main_mod, "is_license_valid", lambda path: False)
        lic_mod._license_cache.clear()

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_trailing_slash_bypasses_license(self, monkeypatch):
        """GET /health/ 同样绕过 license 校验"""
        monkeypatch.setattr(main_mod, "_LICENSE_FILE", "nonexistent_file_xyz999.json")
        lic_mod._license_cache.clear()

        client = TestClient(app)
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_routes_accessible_with_valid_license(self, monkeypatch):
        """有效 license 时路由不会被中间件拦截"""
        monkeypatch.setattr(main_mod, "is_license_valid", lambda path: True)
        lic_mod._license_cache.clear()

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

        # 无许可拦截时走正常路由匹配，该路径不存在应返回 404
        response = client.get("/some-nonexistent-path-xyz")
        assert response.status_code == 404

    def test_different_http_methods_also_blocked(self, monkeypatch):
        """POST 等其它 HTTP 方法同样被拦截"""
        monkeypatch.setattr(main_mod, "_LICENSE_FILE", "nonexistent_file_xyz999.json")
        lic_mod._license_cache.clear()

        client = TestClient(app)
        response = client.post("/polygon-obstacle/import")
        assert response.status_code == 403
