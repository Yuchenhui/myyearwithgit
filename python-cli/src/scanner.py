"""Git 仓库扫描模块"""

import os
from pathlib import Path
from typing import Generator

# 跳过的目录
BLOCKED_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    "dist",
    "build",
    ".egg-info",
}


def scan_repos(root_path: str | Path, max_depth: int = 64) -> Generator[Path, None, None]:
    """
    递归扫描目录，查找所有 Git 仓库

    Args:
        root_path: 扫描起始路径
        max_depth: 最大递归深度

    Yields:
        找到的 Git 仓库路径
    """
    root = Path(root_path).resolve()

    def _scan(current: Path, depth: int) -> Generator[Path, None, None]:
        if depth > max_depth:
            return

        if not current.is_dir():
            return

        # 检查是否是 Git 仓库
        git_dir = current / ".git"
        if git_dir.exists():
            yield current
            # 继续扫描子模块

        try:
            for item in current.iterdir():
                if item.name.lower() in BLOCKED_DIRS:
                    continue
                if item.is_dir():
                    yield from _scan(item, depth + 1)
        except PermissionError:
            pass

    yield from _scan(root, 0)


def filter_repos_by_keyword(repos: list[Path], keyword: str) -> list[Path]:
    """根据关键词过滤仓库"""
    return [r for r in repos if keyword.lower() not in str(r).lower()]
