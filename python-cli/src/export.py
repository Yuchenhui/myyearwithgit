"""Markdown 导出模块"""

from datetime import datetime, timedelta
from pathlib import Path

from .statistics import YearStats

MONTH_NAMES = ["一月", "二月", "三月", "四月", "五月", "六月",
               "七月", "八月", "九月", "十月", "十一月", "十二月"]

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def export_to_markdown(stats: YearStats, output_dir: Path) -> Path:
    """
    导出统计结果为 Markdown 文件

    Args:
        stats: 统计结果
        output_dir: 输出目录

    Returns:
        生成的文件路径
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"my_year_with_git_{stats.year}_{timestamp}.md"
    filepath = output_dir / filename

    content = generate_markdown(stats)
    filepath.write_text(content, encoding="utf-8")

    return filepath


def generate_markdown(stats: YearStats) -> str:
    """生成 Markdown 内容"""
    lines = []

    # 标题
    lines.append(f"# 🎉 我和我的代码，还有 {stats.year} 年")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 年度总览
    lines.append("## 📊 年度总览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总提交数 | **{stats.total_commits:,}** |")
    lines.append(f"| 新增代码行 | +{stats.total_added_lines:,} |")
    lines.append(f"| 删除代码行 | -{stats.total_deleted_lines:,} |")
    lines.append(f"| 净增代码行 | **{stats.total_added_lines - stats.total_deleted_lines:,}** |")
    lines.append(f"| 活跃天数 | {stats.active_days} / 365 天 |")
    lines.append(f"| 周末提交天数 | {stats.weekend_days} 天 |")
    if stats.total_commits > 0:
        lines.append(f"| 日均提交 | {stats.total_commits / 365:.1f} |")
        lines.append(f"| 活跃日均提交 | {stats.total_commits / max(stats.active_days, 1):.1f} |")
    lines.append("")

    # 连续提交记录
    if stats.max_streak > 0:
        lines.append("## 🔥 连续提交记录")
        lines.append("")
        lines.append(f"- **最长连击**: {stats.max_streak} 天")
        if stats.current_streak > 0:
            lines.append(f"- **当前连击**: {stats.current_streak} 天 (保持中!)")
        lines.append("")

    # 提交热力图
    lines.append("## 📅 月度提交分布")
    lines.append("")

    month_commits = [0] * 12
    for day_of_year, count in stats.heatmap.items():
        try:
            date = datetime(stats.year, 1, 1) + timedelta(days=day_of_year - 1)
            month_commits[date.month - 1] += count
        except (ValueError, OverflowError):
            pass

    max_commits = max(month_commits) if month_commits else 1

    lines.append("```")
    for i, (month, count) in enumerate(zip(MONTH_NAMES, month_commits)):
        bar_len = int((count / max_commits) * 30) if max_commits > 0 else 0
        bar = "█" * bar_len
        highlight = " ← 最活跃" if stats.most_active_month == i + 1 else ""
        lines.append(f"{month:>4} {bar} {count}{highlight}")
    lines.append("```")
    lines.append("")

    # 星期分布
    if stats.commits_by_weekday:
        lines.append("## 📆 星期分布")
        lines.append("")
        lines.append("| 星期 | 提交数 | 占比 |")
        lines.append("|------|--------|------|")

        total = sum(stats.commits_by_weekday.values())
        for i, day in enumerate(WEEKDAY_NAMES):
            count = stats.commits_by_weekday.get(i, 0)
            pct = (count / total * 100) if total > 0 else 0
            emoji = "🔥" if i < 5 and count == max(stats.commits_by_weekday.get(j, 0) for j in range(5)) else ""
            emoji = "🎮" if i >= 5 else emoji
            lines.append(f"| {day} {emoji} | {count} | {pct:.1f}% |")
        lines.append("")

    # 编程语言统计
    if stats.languages:
        lines.append("## 💻 编程语言统计")
        lines.append("")
        lines.append("| 排名 | 语言 | 代码行数 | 占比 |")
        lines.append("|------|------|----------|------|")

        sorted_langs = sorted(stats.languages.items(), key=lambda x: x[1], reverse=True)
        total_lines = sum(stats.languages.values())

        for i, (lang, line_count) in enumerate(sorted_langs[:10], 1):
            pct = (line_count / total_lines * 100) if total_lines > 0 else 0
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            lines.append(f"| {medal} | {lang} | {line_count:,} | {pct:.1f}% |")

        if len(sorted_langs) > 10:
            others = sum(line_count for _, line_count in sorted_langs[10:])
            pct = (others / total_lines * 100) if total_lines > 0 else 0
            lines.append(f"| ... | 其他 | {others:,} | {pct:.1f}% |")
        lines.append("")

    # 时间分布
    if stats.commits_by_hour:
        lines.append("## ⏰ 提交时间分布")
        lines.append("")

        periods = [
            ("🌙 凌晨 (0-5点)", sum(stats.commits_by_hour.get(h, 0) for h in range(0, 5))),
            ("🌅 早晨 (5-10点)", sum(stats.commits_by_hour.get(h, 0) for h in range(5, 10))),
            ("☀️ 中午 (10-14点)", sum(stats.commits_by_hour.get(h, 0) for h in range(10, 14))),
            ("🌤️ 下午 (14-17点)", sum(stats.commits_by_hour.get(h, 0) for h in range(14, 17))),
            ("🌆 傍晚 (17-19点)", sum(stats.commits_by_hour.get(h, 0) for h in range(17, 19))),
            ("🌃 晚上 (19-24点)", sum(stats.commits_by_hour.get(h, 0) for h in range(19, 24))),
        ]

        lines.append("| 时间段 | 提交数 | 占比 |")
        lines.append("|--------|--------|------|")

        total = sum(p[1] for p in periods)
        for name, count in periods:
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"| {name} | {count} | {pct:.1f}% |")
        lines.append("")

        if stats.most_active_date:
            lines.append(f"**🔥 最活跃的一天**: {stats.most_active_date} ({stats.most_active_date_commits} 次提交)")
            lines.append("")

    # 提交信息词频
    if stats.commit_words:
        lines.append("## 💬 提交信息高频词 Top 10")
        lines.append("")
        lines.append("| 排名 | 关键词 | 出现次数 |")
        lines.append("|------|--------|----------|")

        for i, (word, count) in enumerate(list(stats.commit_words.items())[:10], 1):
            lines.append(f"| {i} | `{word}` | {count} |")
        lines.append("")

    # 项目统计概览
    if stats.repo_summaries:
        lines.append(f"## 📁 项目统计 ({len(stats.repo_summaries)} 个项目)")
        lines.append("")
        lines.append("| 项目 | 提交数 | 占比 | 新增 | 删除 | 净增 |")
        lines.append("|------|--------|------|------|------|------|")

        total_commits = sum(r.commits for r in stats.repo_summaries)
        for repo in stats.repo_summaries:
            pct = (repo.commits / total_commits * 100) if total_commits > 0 else 0
            net_lines = repo.added_lines - repo.deleted_lines
            lines.append(
                f"| {repo.name} | {repo.commits} | {pct:.1f}% | "
                f"+{repo.added_lines:,} | -{repo.deleted_lines:,} | {net_lines:,} |"
            )
        lines.append("")

    # 项目详情
    if stats.repo_summaries:
        lines.append(f"## 📋 项目详情")
        lines.append("")

        for i, repo in enumerate(stats.repo_summaries, 1):
            net_lines = repo.added_lines - repo.deleted_lines
            lines.append(f"### {i}. {repo.name}")
            lines.append("")

            # 基本信息表格
            lines.append("| 指标 | 数值 |")
            lines.append("|------|------|")
            lines.append(f"| 提交数 | {repo.commits} |")
            lines.append(f"| 新增代码 | +{repo.added_lines:,} |")
            lines.append(f"| 删除代码 | -{repo.deleted_lines:,} |")
            lines.append(f"| 净增代码 | {net_lines:,} |")

            if repo.first_commit and repo.last_commit:
                lines.append(f"| 时间范围 | {repo.first_commit} ~ {repo.last_commit} |")
            lines.append("")

            # 主要语言
            if repo.languages:
                langs = ", ".join(f"**{lang}**" for lang in list(repo.languages.keys())[:3])
                lines.append(f"**主要语言**: {langs}")
                lines.append("")

            # 主要工作
            if repo.main_work:
                lines.append("**主要工作**:")
                for work in repo.main_work[:5]:
                    lines.append(f"- {work}")
                lines.append("")

            # 关键词
            if repo.keywords:
                keywords = ", ".join(f"`{kw}`" for kw in repo.keywords[:8])
                lines.append(f"**关键词**: {keywords}")
                lines.append("")

            # Commit Messages（供大模型分析）
            if repo.commit_messages:
                lines.append("<details>")
                lines.append(f"<summary>📝 Commit 历史 ({len(repo.commit_messages)} 条)</summary>")
                lines.append("")
                for date_str, message in repo.commit_messages:
                    lines.append(f"**{date_str}**")
                    lines.append("```")
                    lines.append(message)
                    lines.append("```")
                    lines.append("")
                lines.append("</details>")
                lines.append("")

    # 趣味数据
    lines.append("## 🎯 趣味数据")
    lines.append("")

    net_lines = stats.total_added_lines - stats.total_deleted_lines
    if net_lines > 0:
        pages = net_lines // 50
        lines.append(f"- 📖 代码打印出来约 **{pages:,}** 页 A4 纸")

        chars = net_lines * 40
        novels = chars // 100000
        if novels > 0:
            lines.append(f"- 📚 字符数相当于 **{novels}** 本小说")

    if stats.total_commits > 0:
        hours = stats.total_commits * 30 // 60
        lines.append(f"- ⏱️ 按每次提交 30 分钟算，约投入 **{hours:,}** 小时")

    if stats.active_days > 0:
        coverage = stats.active_days / 365 * 100
        lines.append(f"- 📊 全年覆盖率 **{coverage:.1f}%**")
    lines.append("")

    # 成就
    if stats.achievements:
        lines.append("## 🏆 解锁成就")
        lines.append("")

        for name, desc in stats.achievements:
            lines.append(f"### ⭐ {name}")
            lines.append(f"> {desc}")
            lines.append("")

    # 页脚
    lines.append("---")
    lines.append("")
    lines.append("*Generated by [MyYearWithGit](https://github.com/user/myyearwithgit) Python CLI*")

    return "\n".join(lines)
