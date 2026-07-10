"""形式审核规则引擎：分发到对应规则集并执行"""
from typing import List, Callable
from app.models import DocumentModel, FormIssue, SectionType
from app.rules.base import BaseRule
from app.rules.claims_rules import (
    Claims001Rule, Claims002Rule, Claims003Rule, Claims004Rule,
    Claims005Rule, Claims006Rule, Claims007Rule, Claims008Rule,
    Claims009Rule, Claims010Rule, Claims011Rule
)
from app.rules.description_rules import (
    Desc001Rule, Desc002Rule, Desc003Rule, Desc004Rule, Desc005Rule,
    Desc006Rule, Desc007Rule, Desc008Rule
)
from app.rules.abstract_rules import Abstract001Rule, Abstract002Rule
from app.rules.figures_rules import Figures001Rule, Figures002Rule


# 规则注册表：SectionType → 规则列表
RULES_BY_SECTION: dict = {
    SectionType.CLAIMS: [
        Claims001Rule(), Claims002Rule(), Claims003Rule(), Claims004Rule(),
        Claims005Rule(), Claims006Rule(), Claims007Rule(), Claims008Rule(),
        Claims009Rule(), Claims010Rule(), Claims011Rule()
    ],
    SectionType.DESCRIPTION: [
        Desc001Rule(), Desc002Rule(), Desc003Rule(), Desc004Rule(), Desc005Rule(),
        Desc006Rule(), Desc007Rule(), Desc008Rule()
    ],
    SectionType.ABSTRACT: [
        Abstract001Rule(), Abstract002Rule()
    ],
    SectionType.FIGURES: [
        Figures001Rule(), Figures002Rule()
    ],
}


class RuleEngine:
    """规则引擎：执行所有已注册规则"""

    def __init__(self):
        self.rules = RULES_BY_SECTION

    def run(self, model: DocumentModel,
            progress_callback: Callable[[str, int], None] = None) -> List[FormIssue]:
        """对 DocumentModel 执行所有规则"""
        all_issues = []
        for section in model.sections:
            section_rules = self.rules.get(section.section_type, [])
            for rule in section_rules:
                if progress_callback:
                    progress_callback(f"规则审核 [{rule.__class__.__name__}]", 0)
                issues = rule.check(section)
                all_issues.extend(issues)

        # 按节和段落排序
        all_issues.sort(key=lambda i: (i.section.value, i.range.paragraph_index))
        return all_issues

    def get_rule_count(self) -> int:
        """获取已注册规则总数"""
        return sum(len(rules) for rules in self.rules.values())
