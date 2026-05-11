"""机场电磁环境保护区配置参数"""

# runway_code_b → (radius_m, height_m, use_circle)
_CODE_B_CONFIG = {
    "A": (10000.0, 0.0, True),   # B类及以下：圆10000m，贴地
    "B": (10000.0, 10.0, False),  # C类：体育场形10000m，高10m
    "C": (13000.0, 10.0, False),  # D类及以上：体育场形13000m，高10m
    "D": (13000.0, 10.0, False),
    "E": (13000.0, 10.0, False),
    "F": (13000.0, 10.0, False),
}

ZONE_CODE = "runway_electromagnetic_environment"
ZONE_NAME = "机场电磁环境保护区"
RULE_CODE = "runway_electromagnetic_environment"
RULE_NAME = "runway_electromagnetic_environment"
REGION_CODE = "default"
REGION_NAME = "default"
