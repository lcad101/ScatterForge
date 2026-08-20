"""文件探活服务（冻结规范第 3 章 场景 3）。

应用启动时后台异步探活所有 Project.source_file_path，
路径无效 → status = MISSING；UI 灰色显示，仅可"删除"（只删 DB）或"重新定位"。
"""
from __future__ import annotations

import os

from sqlalchemy.orm import Session

from src.models.project import ACTIVE, MISSING, Project


class FileProbeService:
    """探活导出文件路径并更新状态。"""

    @staticmethod
    def exists(path: str) -> bool:
        return bool(path) and os.path.isfile(path)

    def probe(self, session: Session) -> list[Project]:
        """遍历全部项目，更新 status，返回状态发生变化的项目列表。"""
        changed: list[Project] = []
        projects = session.query(Project).all()
        for project in projects:
            new_status = ACTIVE if self.exists(project.source_file_path) else MISSING
            if project.status != new_status:
                project.status = new_status
                changed.append(project)
        session.commit()
        return changed
