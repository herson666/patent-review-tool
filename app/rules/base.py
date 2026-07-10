"""形式审核规则抽象基类"""
from abc import ABC, abstractmethod
from typing import List
from app.models import Section, FormIssue, SectionType


class BaseRule(ABC):
    """形式审核规则抽象基类"""

    def __init__(self):
        if self.section_type is None:
            self.section_type = SectionType.UNKNOWN

    @abstractmethod
    def check(self, section: Section) -> List[FormIssue]:
        """对给定节执行检查，返回问题列表"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """规则描述"""
        pass

    @property
    @abstractmethod
    def law_reference(self) -> str:
        """相关法规依据"""
        pass

    @property
    def rule_id(self) -> str:
        """从类名自动生成规则ID"""
        return self.__class__.__name__
