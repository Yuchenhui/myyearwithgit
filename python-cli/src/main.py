#!/usr/bin/env python3
"""MyYearWithGit - Git 年度提交统计命令行工具"""

import sys
from datetime import datetime
from pathlib import Path

import questionary
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .scanner import scan_repos
from .git_parser import parse_git_log, parse_git_diff, get_user_emails, get_all_contributor_emails
from .statistics import analyze_commits
from .display import display_stats
from .export import export_to_markdown

console = Console()


def select_directory() -> Path | None:
    """让用户输入要扫描的目录"""
    default_path = str(Path.home())

    path = questionary.path(
        "请选择要扫描的目录:",
        default=default_path,
        only_directories=True,
    ).ask()

    if path:
        return Path(path).resolve()
    return None


def scan_and_select_repos(root_path: Path) -> list[Path]:
    """扫描并选择仓库"""
    console.print(f"\n[cyan]正在扫描目录: {root_path}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("扫描中...", total=None)
        repos = list(scan_repos(root_path))
        progress.remove_task(task)

    if not repos:
        console.print("[yellow]未找到 Git 仓库[/yellow]")
        return []

    console.print(f"[green]找到 {len(repos)} 个仓库[/green]\n")

    # 让用户选择仓库
    choices = [
        questionary.Choice(
            title=f"{repo.name} ({repo})",
            value=repo,
            checked=True,
        )
        for repo in sorted(repos, key=lambda x: x.name.lower())
    ]

    selected = questionary.checkbox(
        "选择要分析的仓库 (空格选择/取消，回车确认):",
        choices=choices,
    ).ask()

    return selected or []


def select_year() -> int:
    """选择统计年份"""
    current_year = datetime.now().year
    years = [str(y) for y in range(current_year, current_year - 5, -1)]

    year = questionary.select(
        "选择统计年份:",
        choices=years,
        default=str(current_year),
    ).ask()

    return int(year) if year else current_year


def collect_emails(repos: list[Path]) -> set[str]:
    """收集用户邮箱"""
    all_emails: set[str] = set()

    # 从所有仓库收集当前用户邮箱
    for repo in repos:
        emails = get_user_emails(repo)
        all_emails.update(emails)

    if not all_emails:
        console.print("[yellow]未能自动检测到用户邮箱[/yellow]")
        # 从所有仓库获取贡献者邮箱供选择
        for repo in repos[:3]:  # 只检查前3个仓库
            contributor_emails = get_all_contributor_emails(repo)
            all_emails.update(contributor_emails)

    if all_emails:
        choices = [
            questionary.Choice(title=email, value=email, checked=True)
            for email in sorted(all_emails)
        ]

        selected = questionary.checkbox(
            "选择要统计的邮箱:",
            choices=choices,
        ).ask()

        if selected:
            return set(selected)

    # 手动输入
    manual = questionary.text(
        "请输入你的邮箱 (多个用逗号分隔):",
    ).ask()

    if manual:
        return {e.strip().lower() for e in manual.split(",") if e.strip()}

    return set()


def analyze_repos(repos: list[Path], year: int, emails: set[str]):
    """分析所有仓库"""
    all_commits = []
    seen_hashes = set()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("分析提交历史...", total=len(repos))

        for repo in repos:
            progress.update(task, description=f"分析: {repo.name}")

            # 获取提交
            commits = parse_git_log(repo, year, emails)

            for commit in commits:
                if commit.hash not in seen_hashes:
                    seen_hashes.add(commit.hash)
                    # 设置仓库名和 diff 信息
                    commit.repo_name = repo.name
                    commit.files = parse_git_diff(repo, commit.hash)
                    all_commits.append(commit)

            progress.advance(task)

    console.print(f"\n[green]共分析 {len(all_commits)} 个提交[/green]")

    return all_commits


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold cyan]MyYearWithGit[/bold cyan]\n"
        "[dim]Git 年度提交统计工具[/dim]",
        border_style="cyan",
    ))

    try:
        # 1. 选择目录
        root_path = select_directory()
        if not root_path:
            console.print("[yellow]已取消[/yellow]")
            return

        # 2. 扫描和选择仓库
        repos = scan_and_select_repos(root_path)
        if not repos:
            console.print("[yellow]未选择任何仓库[/yellow]")
            return

        # 3. 选择年份
        year = select_year()

        # 4. 选择邮箱
        emails = collect_emails(repos)
        if not emails:
            console.print("[yellow]未配置邮箱，将统计所有提交[/yellow]")

        console.print(f"\n[cyan]统计配置:[/cyan]")
        console.print(f"  仓库数量: {len(repos)}")
        console.print(f"  统计年份: {year}")
        console.print(f"  邮箱: {', '.join(emails) if emails else '全部'}")

        # 确认
        if not questionary.confirm("开始分析?", default=True).ask():
            console.print("[yellow]已取消[/yellow]")
            return

        # 5. 分析
        commits = analyze_repos(repos, year, emails)

        # 6. 统计
        stats = analyze_commits(commits, year)

        # 7. 展示结果
        display_stats(stats)

        # 8. 导出 Markdown
        output_dir = Path(__file__).parent.parent / "result"
        filepath = export_to_markdown(stats, output_dir)
        console.print(f"\n[green]✅ 报告已保存到: {filepath}[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]已中断[/yellow]")
        sys.exit(0)


# 为了让 rich 的 Panel 在 main 中可用
from rich.panel import Panel


if __name__ == "__main__":
    main()
