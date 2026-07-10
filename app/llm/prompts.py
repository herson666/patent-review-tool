"""模型审核提示词模板"""

# 形式审核增强：检查规则引擎未覆盖的形式问题
PROMPT_FORM_AUDIT = """你是一名专利审查员，请检查以下专利文档段落是否存在以下形式问题：
1. 各部分内容是否完整、是否按规范顺序撰写；
2. 术语使用是否一致、表述是否清楚准确；
3. 是否有引用错误、编号错误、格式错误；
4. 是否符合《专利法实施细则》《审查指南》形式要求。

段落类型：{section_type}
段落内容：
{paragraph_text}

请按以下JSON格式输出（无问题输出"null"）：
{{
  "form_issues": [
    {{
      "type": "形式问题类型",
      "description": "问题描述",
      "severity": "error或warning",
      "law_reference": "相关法规条款"
    }}
  ]
}}
无问题时输出：null"""


# 语句通顺性审核
PROMPT_FLUENCY_AUDIT = """你是一名专利审查员，请检查以下专利文档段落是否存在语句不通顺、语法错误或表达不清的问题。
只输出问题描述，不要修改原文。如果没有问题，输出"无"。

段落：{paragraph_text}

问题（如有）："""


def build_form_prompt(section_type: str, paragraph_text: str) -> str:
    """构建形式审核提示词"""
    return PROMPT_FORM_AUDIT.format(
        section_type=section_type,
        paragraph_text=paragraph_text[:1500]
    )


def build_fluency_prompt(paragraph_text: str) -> str:
    """构建语句通顺审核提示词"""
    return PROMPT_FLUENCY_AUDIT.format(
        paragraph_text=paragraph_text[:1500]
    )
