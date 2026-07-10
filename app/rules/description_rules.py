"""说明书形式审核规则"""
import re
from typing import List
from app.models import Section, FormIssue, TextRange, Severity, SectionType, IssueSource
from app.rules.base import BaseRule


DESCRIPTION_PARTS = ["技术领域", "背景技术", "发明内容", "附图说明", "具体实施方式"]


class Desc001Rule(BaseRule):
    """说明书缺少技术领域"""
    section_type = SectionType.DESCRIPTION

    @property
    def description(self) -> str:
        return "说明书应当包含技术领域部分"

    @property
    def law_reference(self) -> str:
        return "实施细则第20条"

    def check(self, section: Section) -> List[FormIssue]:
        full_text = "\n".join(section.paragraphs)
        if "技术领域" not in full_text:
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.ERROR,
                rule_id="DESC-001",
                message="说明书缺少「技术领域」部分",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []


class Desc002Rule(BaseRule):
    """说明书缺少背景技术"""
    section_type = SectionType.DESCRIPTION

    @property
    def description(self) -> str:
        return "说明书应当包含背景技术部分"

    @property
    def law_reference(self) -> str:
        return "实施细则第20条"

    def check(self, section: Section) -> List[FormIssue]:
        full_text = "\n".join(section.paragraphs)
        if "背景技术" not in full_text:
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.ERROR,
                rule_id="DESC-002",
                message="说明书缺少「背景技术」部分",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []


class Desc003Rule(BaseRule):
    """说明书缺少发明内容"""
    section_type = SectionType.DESCRIPTION

    @property
    def description(self) -> str:
        return "说明书应当包含发明内容部分"

    @property
    def law_reference(self) -> str:
        return "实施细则第20条"

    def check(self, section: Section) -> List[FormIssue]:
        full_text = "\n".join(section.paragraphs)
        if "发明内容" not in full_text:
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.ERROR,
                rule_id="DESC-003",
                message="说明书缺少「发明内容」部分",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []


class Desc004Rule(BaseRule):
    """说明书缺少附图说明（当有附图时）"""
    section_type = SectionType.DESCRIPTION

    @property
    def description(self) -> str:
        return "说明书有附图时应当包含附图说明部分"

    @property
    def law_reference(self) -> str:
        return "实施细则第20条"

    def check(self, section: Section) -> List[FormIssue]:
        full_text = "\n".join(section.paragraphs)
        has_figures = bool(re.search(r"图\d+", full_text))
        if has_figures and "附图说明" not in full_text:
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.WARNING,
                rule_id="DESC-004",
                message="说明书含有附图但缺少「附图说明」部分",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []


class Desc005Rule(BaseRule):
    """说明书缺少具体实施方式"""
    section_type = SectionType.DESCRIPTION

    @property
    def description(self) -> str:
        return "说明书应当包含具体实施方式部分"

    @property
    def law_reference(self) -> str:
        return "实施细则第20条"

    def check(self, section: Section) -> List[FormIssue]:
        full_text = "\n".join(section.paragraphs)
        if "具体实施方式" not in full_text:
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.ERROR,
                rule_id="DESC-005",
                message="说明书缺少「具体实施方式」部分",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []


class Desc006Rule(BaseRule):
    """说明书不得使用引用语"""
    section_type = SectionType.DESCRIPTION

    @property
    def description(self) -> str:
        return "说明书不得使用如权利要求所述的引用语"

    @property
    def law_reference(self) -> str:
        return "实施细则第20条"

    def check(self, section: Section) -> List[FormIssue]:
        issues = []
        pattern = re.compile(r"如权利要求.{0,10}所述")
        for i, para in enumerate(section.paragraphs):
            if pattern.search(para):
                issues.append(FormIssue(
                    section=section.section_type,
                    range=TextRange(paragraph_index=i),
                    severity=Severity.ERROR,
                    rule_id="DESC-006",
                    message="说明书不得使用「如权利要求…所述的」的引用语",
                    law_reference=self.law_reference,
                    source=IssueSource.RULE_ENGINE
                ))
        return issues


class Desc007Rule(BaseRule):
    """说明书不得使用商业性宣传用语"""
    section_type = SectionType.DESCRIPTION

    @property
    def description(self) -> str:
        return "说明书不得使用商业性宣传用语"

    @property
    def law_reference(self) -> str:
        return "实施细则第20条"

    def check(self, section: Section) -> List[FormIssue]:
        issues = []
        commercial_words = ["最先进的", "最优秀的", "世界领先", "国际一流", "独一无二",
                            "史无前例", "遥遥领先", "第一品牌", "完美无缺"]
        full_text = "\n".join(section.paragraphs)
        for word in commercial_words:
            if word in full_text:
                issues.append(FormIssue(
                    section=section.section_type,
                    range=TextRange(paragraph_index=0),
                    severity=Severity.ERROR,
                    rule_id="DESC-007",
                    message=f"说明书使用了商业性宣传用语「{word}」",
                    law_reference=self.law_reference,
                    source=IssueSource.RULE_ENGINE
                ))
        return issues


class Desc008Rule(BaseRule):
    """说明书各部分顺序不符合规范"""
    section_type = SectionType.DESCRIPTION

    @property
    def description(self) -> str:
        return "说明书各部分应当按规范顺序撰写"

    @property
    def law_reference(self) -> str:
        return "实施细则第20条"

    def check(self, section: Section) -> List[FormIssue]:
        positions = {}
        for i, para in enumerate(section.paragraphs):
            for part in DESCRIPTION_PARTS:
                if part in para and part not in positions:
                    positions[part] = i
        expected_order = [p for p in DESCRIPTION_PARTS if p in positions]
        actual_order = sorted(positions, key=positions.get)
        if expected_order != actual_order and len(expected_order) > 1:
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=0),
                severity=Severity.WARNING,
                rule_id="DESC-008",
                message="说明书各部分顺序不符合规范",
                law_reference=self.law_reference,
                source=IssueSource.RULE_ENGINE
            )]
        return []
