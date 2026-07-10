"""规则引擎结果与模型结果融合引擎"""
import re
from typing import List
from app.models import FormIssue, IssueSource


def _normalize(text: str) -> str:
    """文本归一化：去除空格、标点，转小写，用于相似度比较"""
    return re.sub(r"[\s，。、：；！？「」『』（）【】]", "", text).lower()


def deduplicate_issues(rule_issues: List[FormIssue],
                       model_issues: List[FormIssue]) -> List[FormIssue]:
    """
    融合规则引擎结果与模型结果：
    - 规则引擎结果优先级最高（基于明确法规条文）
    - 相同位置 + 相似描述 → 保留规则引擎结果
    - 模型独立发现的新问题追加
    """
    result = list(rule_issues)
    seen = set()

    for issue in rule_issues:
        key = (issue.section, issue.range.paragraph_index, _normalize(issue.message))
        seen.add(key)

    for issue in model_issues:
        key = (issue.section, issue.range.paragraph_index, _normalize(issue.message))
        if key not in seen:
            result.append(issue)
            seen.add(key)

    result.sort(key=lambda i: (i.section.value, i.range.paragraph_index))
    return result


def merge_multiple_files_results(file_results: dict) -> List[FormIssue]:
    """
    合并多个文件的审核结果为一个扁平列表。
    file_results: {file_path: List[FormIssue]}
    """
    merged = []
    for file_path, issues in file_results.items():
        for issue in issues:
            issue.file_path = file_path
            merged.append(issue)
    return merged
