"""会话配置与状态模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class SessionConfig:
    robot: Literal["airbot_play", "ur5e"]
    task: str
    enable_gs: bool = False
    gs_scene: str = "lab3"
    gs_assets: List[str] = field(default_factory=list)
    gs_offset: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    randomize: bool = False
    sync: bool = False
    xml_path: Optional[str] = None
    session_id: Optional[str] = None
    runtime: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionConfig":
        return cls(
            robot=data["robot"],
            task=data["task"],
            enable_gs=bool(data.get("enable_gs", False)),
            gs_scene=str(data.get("gs_scene", "lab3")),
            gs_assets=list(data.get("gs_assets") or []),
            gs_offset=list(data.get("gs_offset") or [0.0, 0.0, 0.0]),
            randomize=bool(data.get("randomize", False)),
            sync=bool(data.get("sync", False)),
            xml_path=data.get("xml_path"),
            session_id=data.get("session_id"),
            runtime=data.get("runtime"),
        )


@dataclass
class SessionRecord:
    session_id: str
    config: SessionConfig
    port: int
    pid: Optional[int]
    status: str
    viewer_url: str
    created_at: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "port": self.port,
            "pid": self.pid,
            "viewer_url": self.viewer_url,
            "created_at": self.created_at,
            "error": self.error,
            "config": self.config.to_dict(),
        }
