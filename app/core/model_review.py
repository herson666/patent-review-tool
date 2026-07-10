"""模型审核异步线程：双重审核（形式增强 + 语句通顺）"""
import json
import re
from typing import List
from PyQt5.QtCore import QThread, pyqtSignal
from app.models import (
    DocumentModel, FormIssue, TextRange,
    Severity, SectionType, IssueSource
)
from app.llm.model_manager import model_manager
from app.llm.prompts import build_form_prompt, build_fluency_prompt


class ModelReviewThread(QThread):
    """模型审核线程 - 形式 + 语句通顺双重能力"""
    finished_signal = pyqtSignal(list)   # List[FormIssue]
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def __init__(self, document_model: DocumentModel, enable_fluency: bool = True):
        super().__init__()
        self.model = document_model
        self.enable_fluency = enable_fluency
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            inference = model_manager.load_model()
            all_issues = []
            total_paras = sum(len(s.paragraphs) for s in self.model.sections
                              if s.section_type != SectionType.UNKNOWN)
            processed = 0

            for section in self.model.sections:
                if section.section_type == SectionType.UNKNOWN:
                    continue
                if self._cancelled:
                    break

                for i, para_text in enumerate(section.paragraphs):
                    if self._cancelled:
                        break
                    if not para_text.strip():
                        processed += 1
                        continue

                    # 形式审核增强
                    self.progress_signal.emit(
                        int(processed / max(total_paras, 1) * 50),
                        f"模型形式审核: {section.section_type.value} 第{i+1}段"
                    )
                    form_issues = self._review_form_audit(
                        inference, section, i, para_text
                    )
                    all_issues.extend(form_issues)

                    # 语句通顺审核
                    if self.enable_fluency:
                        self.progress_signal.emit(
                            int(processed / max(total_paras, 1) * 50) + 25,
                            f"模型通顺审核: {section.section_type.value} 第{i+1}段"
                        )
                        fluency_issues = self._review_fluency(
                            inference, section, i, para_text
                        )
                        all_issues.extend(fluency_issues)

                    processed += 1

            if self._cancelled:
                self.error_signal.emit("用户取消")
                return
            self.finished_signal.emit(all_issues)
        except Exception as e:
            self.error_signal.emit(f"模型审核失败: {e}")

    def _review_form_audit(self, inference, section, para_idx, text) -> List[FormIssue]:
        """形式审核增强"""
        prompt = build_form_prompt(section.section_type.value, text)
        try:
            result = inference.generate(prompt, max_tokens=512, temperature=0.1)
            result = result.strip()
            if result.lower() == "null" or not result:
                return []
            # 尝试解析 JSON
            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if not json_match:
                return []
            data = json.loads(json_match.group(0))
            if not data or not data.get("form_issues"):
                return []

            issues = []
            for item in data["form_issues"]:
                severity = (Severity.ERROR
                            if str(item.get("severity", "")).lower() == "error"
                            else Severity.WARNING)
                issues.append(FormIssue(
                    section=section.section_type,
                    range=TextRange(paragraph_index=para_idx),
                    severity=severity,
                    rule_id=f"MODEL-{item.get('type', 'FORM')}",
                    message=item.get("description", ""),
                    law_reference=item.get("law_reference", ""),
                    source=IssueSource.MODEL_FORM
                ))
            return issues
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    def _review_fluency(self, inference, section, para_idx, text) -> List[FormIssue]:
        """语句通顺审核"""
        prompt = build_fluency_prompt(text)
        try:
            result = inference.generate(prompt, max_tokens=256, temperature=0.1)
            result = result.strip()
            if result == "无" or not result:
                return []
            return [FormIssue(
                section=section.section_type,
                range=TextRange(paragraph_index=para_idx),
                severity=Severity.WARNING,
                rule_id="MODEL-FLUENCY",
                message=f"语句不通顺: {result}",
                source=IssueSource.MODEL_FLUENCY
            )]
        except Exception:
            return []
