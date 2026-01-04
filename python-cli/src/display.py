"""结果展示模块"""

from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich import box

from .statistics import YearStats, get_time_period_name


console = Console()

MONTH_NAMES = ["一月", "二月", "三月", "四月", "五月", "六月",
               "七月", "八月", "九月", "十月", "十一月", "十二月"]

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def display_stats(stats: YearStats) -> None:
    """展示统计结果"""
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]我和我的代码，还有 {stats.year} 年[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    # 基础统计
    display_basic_stats(stats)

    # 连续提交
    display_streak(stats)

    # 热力图
    display_heatmap(stats)

    # 星期分布
    display_weekday_stats(stats)

    # 语言统计
    display_languages(stats)

    # 时间统计
    display_time_stats(stats)

    # 提交信息词频
    display_commit_words(stats)

    # 项目统计概览
    display_repo_stats(stats)

    # 项目详情
    display_repo_summaries(stats)

    # 趣味数据
    display_fun_facts(stats)

    # 成就
    display_achievements(stats)


def display_basic_stats(stats: YearStats) -> None:
    """显示基础统计"""
    table = Table(title="📊 年度总览", box=box.ROUNDED)
    table.add_column("指标", style="cyan")
    table.add_column("数值", style="green", justify="right")

    table.add_row("总提交数", f"{stats.total_commits:,}")
    table.add_row("新增代码行", f"+{stats.total_added_lines:,}")
    table.add_row("删除代码行", f"-{stats.total_deleted_lines:,}")
    table.add_row("净增代码行", f"{stats.total_added_lines - stats.total_deleted_lines:,}")
    table.add_row("活跃天数", f"{stats.active_days} / 365 天")
    table.add_row("周末提交天数", f"{stats.weekend_days} 天")

    if stats.total_commits > 0:
        avg_per_day = stats.total_commits / 365
        avg_per_active = stats.total_commits / max(stats.active_days, 1)
        table.add_row("日均提交", f"{avg_per_day:.1f}")
        table.add_row("活跃日均提交", f"{avg_per_active:.1f}")

    console.print(table)
    console.print()


def display_streak(stats: YearStats) -> None:
    """显示连续提交统计"""
    if stats.max_streak <= 0:
        return

    console.print("[bold]🔥 连续提交记录[/bold]")
    console.print(f"  最长连击: [bold green]{stats.max_streak}[/bold green] 天")
    if stats.current_streak > 0:
        console.print(f"  当前连击: [bold yellow]{stats.current_streak}[/bold yellow] 天 (保持中!)")
    console.print()


def display_heatmap(stats: YearStats) -> None:
    """显示热力图（简化版）"""
    if not stats.heatmap:
        return

    console.print("[bold]📅 提交热力图[/bold]")

    # 按月份统计
    month_commits = [0] * 12

    for day_of_year, count in stats.heatmap.items():
        try:
            date = datetime(stats.year, 1, 1) + timedelta(days=day_of_year - 1)
            month_commits[date.month - 1] += count
        except (ValueError, OverflowError):
            pass

    max_commits = max(month_commits) if month_commits else 1

    for i, (month, count) in enumerate(zip(MONTH_NAMES, month_commits)):
        bar_len = int((count / max_commits) * 30) if max_commits > 0 else 0
        bar = "█" * bar_len
        color = "green" if count > 0 else "dim"
        highlight = " ← 最活跃" if stats.most_active_month == i + 1 else ""
        console.print(f"  {month:>4} [{color}]{bar}[/{color}] {count}{highlight}")

    console.print()


def display_weekday_stats(stats: YearStats) -> None:
    """显示星期分布"""
    if not stats.commits_by_weekday:
        return

    console.print("[bold]📆 星期分布[/bold]")

    max_count = max(stats.commits_by_weekday.values()) if stats.commits_by_weekday else 1

    for i, day in enumerate(WEEKDAY_NAMES):
        count = stats.commits_by_weekday.get(i, 0)
        bar_len = int((count / max_count) * 20) if max_count > 0 else 0
        bar = "▓" * bar_len
        color = "yellow" if i >= 5 else "cyan"  # 周末用黄色
        console.print(f"  {day} [{color}]{bar}[/{color}] {count}")

    console.print()


def display_languages(stats: YearStats) -> None:
    """显示语言统计"""
    if not stats.languages:
        return

    table = Table(title="💻 编程语言统计", box=box.ROUNDED)
    table.add_column("语言", style="cyan")
    table.add_column("代码行数", style="green", justify="right")
    table.add_column("占比", justify="right")
    table.add_column("分布", justify="left")

    # 按行数排序
    sorted_langs = sorted(stats.languages.items(), key=lambda x: x[1], reverse=True)
    total_lines = sum(stats.languages.values())
    max_lines = sorted_langs[0][1] if sorted_langs else 1

    for lang, lines in sorted_langs[:10]:  # 只显示前10
        percentage = (lines / total_lines * 100) if total_lines > 0 else 0
        bar_len = int((lines / max_lines) * 15)
        bar = "█" * bar_len
        table.add_row(lang, f"{lines:,}", f"{percentage:.1f}%", bar)

    if len(sorted_langs) > 10:
        others = sum(lines for _, lines in sorted_langs[10:])
        percentage = (others / total_lines * 100) if total_lines > 0 else 0
        table.add_row("其他", f"{others:,}", f"{percentage:.1f}%", "")

    console.print(table)
    console.print()


def display_time_stats(stats: YearStats) -> None:
    """显示时间统计"""
    if not stats.commits_by_hour:
        return

    table = Table(title="⏰ 提交时间分布", box=box.ROUNDED)
    table.add_column("时间段", style="cyan")
    table.add_column("提交数", style="green", justify="right")
    table.add_column("分布", justify="left")

    # 按时间段分组
    periods = {
        "凌晨 (0-5点)": sum(stats.commits_by_hour.get(h, 0) for h in range(0, 5)),
        "早晨 (5-10点)": sum(stats.commits_by_hour.get(h, 0) for h in range(5, 10)),
        "中午 (10-14点)": sum(stats.commits_by_hour.get(h, 0) for h in range(10, 14)),
        "下午 (14-17点)": sum(stats.commits_by_hour.get(h, 0) for h in range(14, 17)),
        "傍晚 (17-19点)": sum(stats.commits_by_hour.get(h, 0) for h in range(17, 19)),
        "晚上 (19-24点)": sum(stats.commits_by_hour.get(h, 0) for h in range(19, 24)),
    }

    max_period = max(periods.values()) if periods else 1

    for period, count in periods.items():
        bar_len = int((count / max_period) * 20) if max_period > 0 else 0
        bar = "▓" * bar_len
        table.add_row(period, str(count), bar)

    console.print(table)
    console.print()

    # 最活跃的一天
    if stats.most_active_date:
        console.print(f"  🔥 最活跃的一天: [bold]{stats.most_active_date}[/bold] ({stats.most_active_date_commits} 次提交)")
        console.print()


def display_commit_words(stats: YearStats) -> None:
    """显示提交信息词频"""
    if not stats.commit_words:
        return

    console.print("[bold]💬 提交信息高频词[/bold]")

    # 取前 10 个
    top_words = list(stats.commit_words.items())[:10]
    max_count = top_words[0][1] if top_words else 1

    for word, count in top_words:
        bar_len = int((count / max_count) * 15)
        bar = "▪" * bar_len
        console.print(f"  {word:<15} [dim]{bar}[/dim] {count}")

    console.print()


def display_fun_facts(stats: YearStats) -> None:
    """显示趣味数据"""
    console.print("[bold]🎯 趣味数据[/bold]")

    net_lines = stats.total_added_lines - stats.total_deleted_lines

    # 代码行数比喻
    if net_lines > 0:
        # 假设一页代码 50 行
        pages = net_lines // 50
        console.print(f"  📖 你写的代码打印出来约 [bold]{pages:,}[/bold] 页 A4 纸")

        # 假设每行代码平均 40 个字符
        chars = net_lines * 40
        novels = chars // 100000  # 一本小说约 10 万字
        if novels > 0:
            console.print(f"  📚 字符数相当于 [bold]{novels}[/bold] 本小说")

    # 时间投入
    if stats.total_commits > 0:
        # 假设每次提交平均花费 30 分钟
        hours = stats.total_commits * 30 // 60
        console.print(f"  ⏱️  按每次提交 30 分钟算，约投入 [bold]{hours:,}[/bold] 小时")

    # 活跃度
    if stats.active_days > 0:
        coverage = stats.active_days / 365 * 100
        console.print(f"  📊 全年覆盖率 [bold]{coverage:.1f}%[/bold]")

    console.print()


def display_repo_stats(stats: YearStats) -> None:
    """显示项目统计概览"""
    if not stats.repo_summaries:
        return

    table = Table(title="📁 项目统计", box=box.ROUNDED)
    table.add_column("项目", style="cyan")
    table.add_column("提交数", style="green", justify="right")
    table.add_column("占比", justify="right")
    table.add_column("新增", style="green", justify="right")
    table.add_column("删除", style="red", justify="right")
    table.add_column("净增", justify="right")
    table.add_column("分布", justify="left")

    total_commits = sum(r.commits for r in stats.repo_summaries)
    max_commits = max(r.commits for r in stats.repo_summaries) if stats.repo_summaries else 1

    for repo in stats.repo_summaries:
        pct = (repo.commits / total_commits * 100) if total_commits > 0 else 0
        bar_len = int((repo.commits / max_commits) * 15) if max_commits > 0 else 0
        bar = "█" * bar_len
        net_lines = repo.added_lines - repo.deleted_lines
        net_style = "green" if net_lines >= 0 else "red"

        table.add_row(
            repo.name[:20] + "..." if len(repo.name) > 20 else repo.name,
            str(repo.commits),
            f"{pct:.1f}%",
            f"+{repo.added_lines:,}",
            f"-{repo.deleted_lines:,}",
            f"[{net_style}]{net_lines:,}[/{net_style}]",
            bar,
        )

    console.print(table)
    console.print()


def display_repo_summaries(stats: YearStats) -> None:
    """显示项目摘要"""
    if not stats.repo_summaries:
        return

    console.print(Panel(
        f"[bold magenta]📁 项目详情 ({len(stats.repo_summaries)} 个项目)[/bold magenta]",
        border_style="magenta"
    ))

    for i, repo in enumerate(stats.repo_summaries, 1):
        # 项目标题
        console.print(f"\n  [bold cyan]{i}. {repo.name}[/bold cyan]")

        # 基本信息
        net_lines = repo.added_lines - repo.deleted_lines
        console.print(f"     提交: {repo.commits} | 代码: +{repo.added_lines:,} -{repo.deleted_lines:,} (净增 {net_lines:,})")

        # 时间范围
        if repo.first_commit and repo.last_commit:
            console.print(f"     时间: {repo.first_commit} ~ {repo.last_commit}")

        # 主要语言
        if repo.languages:
            langs = ", ".join(f"{lang}" for lang in list(repo.languages.keys())[:3])
            console.print(f"     语言: [green]{langs}[/green]")

        # 主要工作
        if repo.main_work:
            works = " | ".join(repo.main_work[:3])
            console.print(f"     工作: [yellow]{works}[/yellow]")

        # 关键词
        if repo.keywords:
            keywords = ", ".join(repo.keywords[:5])
            console.print(f"     关键词: [dim]{keywords}[/dim]")

    console.print()


def display_achievements(stats: YearStats) -> None:
    """显示成就"""
    if not stats.achievements:
        return

    console.print(Panel(
        f"[bold yellow]🏆 解锁成就 ({len(stats.achievements)} 个)[/bold yellow]",
        border_style="yellow"
    ))

    for name, desc in stats.achievements:
        console.print(f"  [bold gold1]★ {name}[/bold gold1]")
        console.print(f"    [dim]{desc}[/dim]")

    console.print()
