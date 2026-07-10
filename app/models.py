"""数据模型"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SectionType(Enum):
    ABSTRACT = "abstract"        # 说明书摘要
    CLAIMS = "claims"           # 权利要求书
    DESCRIPTION = "description"  # 说明书
    FIGURES = "figures"          # 说明书附图
    UNKNOWN = "unknown"


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


class IssueSource(Enum):
    RULE_ENGINE = "rule_engine"
    MODEL_FORM = "model_form"
    MODEL_FLUENCY = "model_fluency"


@dataclass
class TextRange:
    paragraph_index: int
    start_offset: int = 0     # 字符级起始位置
    end_offset: int = -1      # 字符级结束位置，-1=段落末尾


@dataclass
class FormIssue:
    section: SectionType
    range: TextRange
    severity: Severity
    rule_id: str
    message: str
    law_reference: str = ""
    source: IssueSource = IssueSource.RULE_ENGINE
    file_path: str = ""  # 所属文件路径


@dataclass
class Section:
    section_type: SectionType
    title: str = ""            # 节标题
    paragraphs: List[str] = field(default_factory=list)
    raw_paragraphs: List = field(default_factory=list)  # python-docx Paragraph 对象
    start_para_index: int = 0


@dataclass
class DocumentModel:
    file_path: str
    sections: List[Section] = field(default_factory=list)
    patent_name: str = ""
    all_paragraphs: List = field(default_factory=list)
