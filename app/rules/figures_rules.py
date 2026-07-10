"""说明书附图形式审核规则"""
import re
from typing import List
from app.models import Section, FormIssue, TextRange, Severity, SectionType, IssueSource
from app.rules.base import BaseRule


class Figures001Rule(BaseRule):
    """R28: 附图编号不连续"""
    section_type = SectionType.FIGURES

    @property
    def description(self) -> str:
        return "说明书附图应当按图1，图2…顺序编号排列"

    @property
    def law_reference(self) -> str:
        return "实施细则第21条"

    def check(self, section: Section) -> List[FormIssue]:
        fig_numbers = []
        for para in section.paragraphs:
            nums = re.findall(r"图(\d+)", para)
            fig_numbers.extend([int(n) for n in nums])
        if not fig_numbers:
            return []
        expected = list(range(1, max(fig_numbers) + 1))
        if sorted(set(fig_numbers)) != sorted(expected):
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.WARNING,
                rule_id="FIGURES-001",
                message="说明书附图编号不连续，应当按图1，图2…顺序排列",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []


class Figures002Rule(BaseRule):
    """R29: 附图中含有非必要注释"""
    section_type = SectionType.FIGURES

    @property
    def description(self) -> str:
        return "附图中除必需的词语外，不应当含有其他注释"

    @property
    def law_reference(self) -> str:
        return "实施细则第21条"

    def check(self, section: Section) -> List[FormIssue]:
        issues = []
        for i, para in enumerate(section.paragraphs):
            if len(para) > 150:  # 附图说明段落过长可能含非必要注释
                issues.append(FormIssue(
                    section=section.section_type,
                    range=TextRange(paragraph_index=i),
                    severity=Severity.WARNING,
                    rule_id="FIGURES-002",
                    message="附图说明段落过长，可能含有非必要注释",
                    law_reference=self.law_reference,
                    source=IssueSource.RULE_ENGINE
                ))
        return issues
