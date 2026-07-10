"""摘要形式审核规则"""
import re
from typing import List
from app.models import Section, FormIssue, TextRange, Severity, SectionType, IssueSource
from app.rules.base import BaseRule


class Abstract001Rule(BaseRule):
    """R22: 摘要不得超过300字"""
    section_type = SectionType.ABSTRACT

    @property
    def description(self) -> str:
        return "说明书摘要不得超过300字"

    @property
    def law_reference(self) -> str:
        return "实施细则第26条"

    def check(self, section: Section) -> List[FormIssue]:
        full_text = "".join(section.paragraphs)
        char_count = len(full_text.strip())
        if char_count > 300:
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.ERROR,
                rule_id="ABSTRACT-001",
                message=f"摘要内容超过300字（当前{char_count}字）",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []


class Abstract002Rule(BaseRule):
    """摘要缺少发明名称"""
    section_type = SectionType.ABSTRACT

    @property
    def description(self) -> str:
        return "摘要应当包含发明名称"

    @property
    def law_reference(self) -> str:
        return "实施细则第26条"

    def check(self, section: Section) -> List[FormIssue]:
        full_text = "".join(section.paragraphs)
        if len(full_text.strip()) < 5:
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.ERROR,
                rule_id="ABSTRACT-002",
                message="摘要缺少发明名称",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []
