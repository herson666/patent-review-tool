# 专利申请文件形式审核工具

## 安装
pip install -r requirements.txt

## 运行
python main.py

## 卸载
运行 scripts/uninstall.bat（Windows）或 scripts/uninstall.sh（macOS/Linux）

## 功能
- 自动审核专利申请文件（.docx）的形式问题
- 支持规则引擎审核 + Qwen3-4b 模型增强审核（可选）
- 批量审核多个文件
- 审核结果以 Word 批注形式输出
- 关闭前提醒导出，关闭后自动清理缓存
