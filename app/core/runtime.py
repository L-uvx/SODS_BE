from collections.abc import Callable

from app.core.config import Settings


dispatch_import_task: Callable[[str], object] | None = None
dispatch_analysis_task: Callable[[str], object] | None = None
settings: Settings | None = None
