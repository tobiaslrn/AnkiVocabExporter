from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ExportSettings:
    deck: Optional[str] = None
    fields: List[str] = field(default_factory=list)
    grouping: str = "status"
    include_fresh: bool = True
    include_young: bool = True
    include_mature: bool = True
    include_mastered: bool = True
    separate_today: bool = True
    predictive_days: int = 0


@dataclass
class ExportResult:
    success: bool
    total_cards: int = 0
    files_created: List[str] = field(default_factory=list)
    export_directory: str = ""
    output_path: str = ""
    error_message: str = ""
