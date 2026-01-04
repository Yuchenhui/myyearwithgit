"""Git 日志和 Diff 解析模块"""

import subprocess
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# 编程语言扩展名映射
LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".ps1": "PowerShell",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".lua": "Lua",
    ".r": "R",
    ".m": "Objective-C/MATLAB",
    ".dart": "Dart",
    ".scala": "Scala",
    ".groovy": "Groovy",
    ".pl": "Perl",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".ml": "OCaml",
    ".fs": "F#",
    ".clj": "Clojure",
    ".nim": "Nim",
    ".zig": "Zig",
    ".v": "V",
    ".sol": "Solidity",
}


@dataclass
class FileDiff:
    """单个文件的变更信息"""
    filename: str
    language: Optional[str] = None
    added_lines: int = 0
    deleted_lines: int = 0
    empty_lines_added: int = 0


@dataclass
class CommitInfo:
    """提交信息"""
    hash: str
    email: str
    date: datetime
    message: str
    repo_name: str = ""  # 所属仓库名
    files: list[FileDiff] = field(default_factory=list)


def get_language(filename: str) -> Optional[str]:
    """根据文件扩展名获取编程语言"""
    ext = Path(filename).suffix.lower()
    return LANGUAGE_MAP.get(ext)


def run_git_command(repo_path: Path, args: list[str]) -> tuple[bool, str]:
    """执行 Git 命令"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0, result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)


def parse_git_log(repo_path: Path, year: int, emails: set[str]) -> list[CommitInfo]:
    """
    解析 Git 日志

    Args:
        repo_path: 仓库路径
        year: 统计年份
        emails: 要统计的邮箱集合（小写）

    Returns:
        提交信息列表
    """
    # 获取指定年份的提交
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    # 使用 NULL 字符分隔字段和记录，以支持多行 commit message
    # %x00 = NULL 字符，用于分隔字段
    # %x00%x00 = 双 NULL，用于分隔记录
    success, output = run_git_command(repo_path, [
        "log",
        "--all",
        f"--after={start_date}",
        f"--before={end_date} 23:59:59",
        "--format=%H%x00%ae%x00%aI%x00%B%x00%x00",
    ])

    if not success or not output.strip():
        return []

    commits = []
    seen_hashes = set()

    # 按双 NULL 分隔每条 commit 记录
    records = output.split("\x00\x00")

    for record in records:
        record = record.strip()
        if not record:
            continue

        parts = record.split("\x00", 3)
        if len(parts) < 4:
            continue

        commit_hash, email, date_str, message = parts
        email = email.lower()
        commit_hash = commit_hash.lower()
        message = message.strip()  # 去除 %B 末尾的换行

        # 过滤：邮箱和去重
        if emails and email not in emails:
            continue
        if commit_hash in seen_hashes:
            continue
        seen_hashes.add(commit_hash)

        try:
            # 解析 ISO 格式日期
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        commits.append(CommitInfo(
            hash=commit_hash,
            email=email,
            date=date,
            message=message,
        ))

    return commits


def parse_git_diff(repo_path: Path, commit_hash: str) -> list[FileDiff]:
    """
    解析单个提交的 diff

    Args:
        repo_path: 仓库路径
        commit_hash: 提交哈希

    Returns:
        文件变更列表
    """
    success, output = run_git_command(repo_path, [
        "diff",
        f"{commit_hash}^!",
        "--numstat",
    ])

    if not success:
        # 可能是初始提交
        success, output = run_git_command(repo_path, [
            "diff",
            "--numstat",
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904",  # empty tree
            commit_hash,
        ])

    if not success or not output.strip():
        return []

    files = []
    for line in output.strip().split("\n"):
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        added, deleted, filename = parts[0], parts[1], parts[2]

        # 处理二进制文件
        try:
            added_lines = int(added) if added != "-" else 0
            deleted_lines = int(deleted) if deleted != "-" else 0
        except ValueError:
            continue

        files.append(FileDiff(
            filename=filename,
            language=get_language(filename),
            added_lines=added_lines,
            deleted_lines=deleted_lines,
        ))

    return files


def get_user_emails(repo_path: Path) -> set[str]:
    """获取当前用户在仓库中使用的邮箱"""
    success, output = run_git_command(repo_path, ["config", "user.email"])
    if success and output.strip():
        return {output.strip().lower()}
    return set()


def get_all_contributor_emails(repo_path: Path) -> set[str]:
    """获取仓库所有贡献者邮箱"""
    success, output = run_git_command(repo_path, [
        "log",
        "--all",
        "--format=%ae",
    ])
    if success:
        return {email.lower() for email in output.strip().split("\n") if email}
    return set()
