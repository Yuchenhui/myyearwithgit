"""统计分析模块"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .git_parser import CommitInfo, FileDiff


@dataclass
class RepoSummary:
    """单个仓库的摘要"""
    name: str
    commits: int = 0
    added_lines: int = 0
    deleted_lines: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)  # 主要关键词
    main_work: list[str] = field(default_factory=list)  # 主要工作内容
    first_commit: Optional[str] = None  # 最早提交日期
    last_commit: Optional[str] = None   # 最后提交日期
    commit_messages: list[tuple[str, str]] = field(default_factory=list)  # (日期, 消息)


@dataclass
class YearStats:
    """年度统计结果"""
    year: int

    # 基础统计
    total_commits: int = 0
    total_added_lines: int = 0
    total_deleted_lines: int = 0
    active_days: int = 0

    # 热力图数据 (day_of_year -> count)
    heatmap: dict[int, int] = field(default_factory=dict)

    # 语言统计 (language -> lines)
    languages: dict[str, int] = field(default_factory=dict)

    # 时间统计
    commits_by_hour: dict[int, int] = field(default_factory=dict)
    commits_by_weekday: dict[int, int] = field(default_factory=dict)
    weekend_days: int = 0

    # 特殊日期
    most_active_date: Optional[str] = None
    most_active_date_commits: int = 0
    most_active_month: Optional[int] = None
    most_active_month_commits: int = 0

    # 连续提交
    max_streak: int = 0
    current_streak: int = 0

    # 提交信息词频
    commit_words: dict[str, int] = field(default_factory=dict)

    # 仓库统计
    repos_count: int = 0
    repos_stats: dict[str, int] = field(default_factory=dict)  # repo_name -> commits
    repo_summaries: list[RepoSummary] = field(default_factory=list)  # 各仓库摘要

    # 成就
    achievements: list[tuple[str, str]] = field(default_factory=list)


# 默认排除的非代码语言
DEFAULT_EXCLUDE_LANGUAGES = {
    "Markdown",
    "JSON",
    "YAML",
    "XML",
    "reStructuredText",
}


def analyze_commits(
    commits: list[CommitInfo],
    year: int,
    exclude_languages: set[str] | None = None,
) -> YearStats:
    """
    分析提交数据，生成统计结果

    Args:
        commits: 提交信息列表（已包含 files）
        year: 统计年份
        exclude_languages: 要排除的语言集合（用于语言统计，不影响行数统计）

    Returns:
        年度统计结果
    """
    if exclude_languages is None:
        exclude_languages = DEFAULT_EXCLUDE_LANGUAGES

    stats = YearStats(year=year)

    if not commits:
        return stats

    # 按日期分组
    commits_by_date: dict[str, list[CommitInfo]] = defaultdict(list)
    commits_by_month: dict[int, int] = defaultdict(int)
    active_dates: set[str] = set()
    weekend_dates: set[str] = set()
    word_counter: Counter = Counter()

    for commit in commits:
        stats.total_commits += 1

        # 统计行数
        for f in commit.files:
            stats.total_added_lines += f.added_lines
            stats.total_deleted_lines += f.deleted_lines

            # 语言统计（排除非代码语言）
            if f.language and f.language not in exclude_languages:
                stats.languages[f.language] = stats.languages.get(f.language, 0) + f.added_lines

        # 日期统计
        date_str = commit.date.strftime("%Y-%m-%d")
        commits_by_date[date_str].append(commit)
        active_dates.add(date_str)

        # 月份统计
        commits_by_month[commit.date.month] += 1

        # 热力图
        day_of_year = commit.date.timetuple().tm_yday
        stats.heatmap[day_of_year] = stats.heatmap.get(day_of_year, 0) + 1

        # 时间统计
        hour = commit.date.hour
        stats.commits_by_hour[hour] = stats.commits_by_hour.get(hour, 0) + 1

        # 星期统计
        weekday = commit.date.weekday()  # 0=Monday, 6=Sunday
        stats.commits_by_weekday[weekday] = stats.commits_by_weekday.get(weekday, 0) + 1

        # 周末统计
        if weekday >= 5:  # Saturday or Sunday
            weekend_dates.add(date_str)

        # 提交信息词频
        words = extract_words(commit.message)
        word_counter.update(words)

    # 活跃天数
    stats.active_days = len(active_dates)
    stats.weekend_days = len(weekend_dates)

    # 最活跃的一天
    if commits_by_date:
        most_active = max(commits_by_date.items(), key=lambda x: len(x[1]))
        stats.most_active_date = most_active[0]
        stats.most_active_date_commits = len(most_active[1])

    # 最活跃的月份
    if commits_by_month:
        most_active_month = max(commits_by_month.items(), key=lambda x: x[1])
        stats.most_active_month = most_active_month[0]
        stats.most_active_month_commits = most_active_month[1]

    # 计算连续提交天数
    stats.max_streak, stats.current_streak = calculate_streak(active_dates, year)

    # 提交信息词频 (top 20)
    stats.commit_words = dict(word_counter.most_common(20))

    # 按仓库分组生成摘要
    stats.repo_summaries = generate_repo_summaries(commits, exclude_languages)
    stats.repos_count = len(stats.repo_summaries)

    # 计算成就
    stats.achievements = calculate_achievements(stats)

    return stats


def generate_repo_summaries(
    commits: list[CommitInfo],
    exclude_languages: set[str],
) -> list[RepoSummary]:
    """按仓库分组生成摘要"""
    from collections import defaultdict

    # 按仓库分组
    repo_commits: dict[str, list[CommitInfo]] = defaultdict(list)
    for commit in commits:
        if commit.repo_name:
            repo_commits[commit.repo_name].append(commit)

    summaries = []

    for repo_name, repo_commit_list in repo_commits.items():
        summary = RepoSummary(name=repo_name)
        summary.commits = len(repo_commit_list)

        # 统计代码行数和语言
        lang_counter: Counter = Counter()
        word_counter: Counter = Counter()
        commit_dates: list[datetime] = []

        for commit in repo_commit_list:
            commit_dates.append(commit.date)

            # 收集 commit message（日期, 消息）
            date_str = commit.date.strftime("%Y-%m-%d %H:%M")
            summary.commit_messages.append((date_str, commit.message))

            # 提取提交信息关键词
            words = extract_words(commit.message)
            word_counter.update(words)

            for f in commit.files:
                summary.added_lines += f.added_lines
                summary.deleted_lines += f.deleted_lines

                if f.language and f.language not in exclude_languages:
                    lang_counter[f.language] += f.added_lines

        # 主要语言
        summary.languages = dict(lang_counter.most_common(5))

        # 主要关键词
        summary.keywords = [w for w, _ in word_counter.most_common(10)]

        # 分析主要工作内容
        summary.main_work = analyze_main_work(repo_commit_list)

        # 时间范围
        if commit_dates:
            commit_dates.sort()
            summary.first_commit = commit_dates[0].strftime("%Y-%m-%d")
            summary.last_commit = commit_dates[-1].strftime("%Y-%m-%d")

        # 按时间排序 commit messages
        summary.commit_messages.sort(key=lambda x: x[0])

        summaries.append(summary)

    # 按提交数排序
    summaries.sort(key=lambda x: x.commits, reverse=True)

    return summaries


def analyze_main_work(commits: list[CommitInfo]) -> list[str]:
    """分析主要工作内容"""
    # 从提交信息中提取工作类型
    work_patterns = {
        "feat": "新功能开发",
        "feature": "新功能开发",
        "新增": "新功能开发",
        "添加": "新功能开发",
        "fix": "Bug 修复",
        "bugfix": "Bug 修复",
        "修复": "Bug 修复",
        "refactor": "代码重构",
        "重构": "代码重构",
        "优化": "性能优化",
        "perf": "性能优化",
        "docs": "文档编写",
        "文档": "文档编写",
        "test": "测试相关",
        "测试": "测试相关",
        "style": "代码风格",
        "chore": "工程配置",
        "ci": "CI/CD 配置",
        "build": "构建相关",
        "deploy": "部署相关",
        "部署": "部署相关",
        "api": "API 开发",
        "接口": "API 开发",
        "ui": "UI 开发",
        "界面": "UI 开发",
        "database": "数据库相关",
        "数据库": "数据库相关",
        "security": "安全相关",
        "安全": "安全相关",
        "auth": "认证授权",
        "登录": "认证授权",
    }

    work_counter: Counter = Counter()

    for commit in commits:
        msg_lower = commit.message.lower()
        for pattern, work_type in work_patterns.items():
            if pattern in msg_lower:
                work_counter[work_type] += 1

    # 返回前 5 个主要工作
    return [work for work, _ in work_counter.most_common(5)]


def extract_words(text: str) -> list[str]:
    """从文本中提取有意义的词汇"""
    import re
    # 移除特殊字符，保留字母数字和中文
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())
    words = text.split()

    # 过滤掉太短的词和常见无意义词
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'this', 'that', 'it', 'from', 'by', 'as', 'if', 'not', 'no',
        'fix', 'add', 'update', 'remove', 'change', 'merge', 'commit',
        'wip', 'todo', 'fixme', 'xxx', 'test', 'tests', 'file', 'files',
    }

    return [w for w in words if len(w) > 2 and w not in stop_words]


def calculate_streak(active_dates: set[str], year: int) -> tuple[int, int]:
    """计算最长连续提交天数和当前连击"""
    from datetime import date, timedelta

    if not active_dates:
        return 0, 0

    # 转换为 date 对象并排序
    dates = sorted([datetime.strptime(d, "%Y-%m-%d").date() for d in active_dates])

    max_streak = 1
    current = 1

    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 1

    # 计算当前连击（从今天往回数）
    today = date.today()
    current_streak = 0

    check_date = today
    while check_date.strftime("%Y-%m-%d") in active_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    return max_streak, current_streak


def calculate_achievements(stats: YearStats) -> list[tuple[str, str]]:
    """计算成就徽章"""
    achievements = []

    # 提交量成就
    score = stats.total_commits * 10 + stats.total_added_lines
    if score > 100000:
        achievements.append(("卷王本王", "代码量惊人，是团队的核心力量"))
    elif score > 10000:
        achievements.append(("发奋图强", "持续高产出，令人敬佩"))
    elif score > 1000:
        achievements.append(("勤劳努力", "稳定输出，值得表扬"))
    elif score > 500:
        achievements.append(("小试牛刀", "初露锋芒，继续加油"))
    else:
        achievements.append(("休养生息", "这一年比较轻松呢"))

    # 语言成就
    if len(stats.languages) >= 10:
        achievements.append(("全栈大神", f"精通 {len(stats.languages)} 种编程语言"))
    elif len(stats.languages) >= 6:
        achievements.append(("编程语言大师", f"使用了 {len(stats.languages)} 种编程语言"))

    # 时间偏好成就
    if stats.commits_by_hour:
        favorite_hour = max(stats.commits_by_hour.items(), key=lambda x: x[1])[0]
        if 0 <= favorite_hour < 5:
            achievements.append(("夜猫子", "凌晨还在写代码，注意休息"))
        elif 5 <= favorite_hour < 10:
            achievements.append(("早睡早起身体好", "早起的鸟儿有虫吃"))
        elif 10 <= favorite_hour < 14:
            achievements.append(("干饭人干饭魂", "午间时光也不忘coding"))
        elif 14 <= favorite_hour < 17:
            achievements.append(("下午茶时间", "下午是你的高效时段"))
        elif 17 <= favorite_hour < 19:
            achievements.append(("晚餐前冲刺", "抓住晚餐前的黄金时间"))
        else:
            achievements.append(("夜间模式", "夜晚是你的创作时间"))

    # 周末成就
    if stats.weekend_days > 40:
        achievements.append(("周末永动机", f"周末提交了 {stats.weekend_days} 天，老板看了都流泪"))
    elif stats.weekend_days > 20:
        achievements.append(("周末战士", f"周末也提交了 {stats.weekend_days} 天"))

    # 高产日成就
    if stats.most_active_date_commits > 100:
        achievements.append(("代码狂人", f"单日最高 {stats.most_active_date_commits} 次提交"))
    elif stats.most_active_date_commits > 50:
        achievements.append(("Bugfix 制造机", f"单日 {stats.most_active_date_commits} 次提交"))

    # 连续提交成就
    if stats.max_streak >= 30:
        achievements.append(("坚持就是胜利", f"连续 {stats.max_streak} 天提交，毅力惊人"))
    elif stats.max_streak >= 14:
        achievements.append(("两周连击", f"连续 {stats.max_streak} 天提交"))
    elif stats.max_streak >= 7:
        achievements.append(("一周达人", f"连续 {stats.max_streak} 天提交"))

    # 活跃度成就
    if stats.active_days >= 300:
        achievements.append(("全年无休", f"活跃 {stats.active_days} 天，代码就是生活"))
    elif stats.active_days >= 200:
        achievements.append(("劳模本模", f"活跃 {stats.active_days} 天"))

    # 代码净增成就
    net_lines = stats.total_added_lines - stats.total_deleted_lines
    if net_lines > 1000000:
        achievements.append(("百万代码", f"净增 {net_lines:,} 行代码"))
    elif net_lines > 100000:
        achievements.append(("十万行家", f"净增 {net_lines:,} 行代码"))
    elif net_lines < -10000:
        achievements.append(("代码清道夫", f"净删除 {-net_lines:,} 行代码，精简专家"))

    # 删除代码成就
    if stats.total_deleted_lines > stats.total_added_lines * 0.8:
        achievements.append(("重构达人", "删除的代码量接近新增量，重构高手"))

    return achievements


def get_time_period_name(hour: int) -> str:
    """获取时间段名称"""
    if 0 <= hour < 5:
        return "凌晨"
    elif 5 <= hour < 10:
        return "早晨"
    elif 10 <= hour < 14:
        return "中午"
    elif 14 <= hour < 17:
        return "下午"
    elif 17 <= hour < 19:
        return "傍晚"
    else:
        return "晚上"
