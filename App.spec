# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for 专利申请文件形式审核工具
# 使用：pyinstaller --noconfirm --clean App.spec
import os
import sys

block_cipher = None

# 数据文件
datas = []
if os.path.isdir('assets'):
    datas.append(('assets', 'assets'))
if os.path.isdir('rules_kb'):
    datas.append(('rules_kb', 'rules_kb'))

# 隐藏导入（PyQt5 + llama-cpp-python + python-docx + 项目自身）
hiddenimports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',
    'docx',
    'docx.oxml',
    'docx.oxml.ns',
    'llama_cpp',
    'llama_cpp.llama_cpp',
    'requests',
    'app',
    'app.core',
    'app.llm',
    'app.rules',
    'app.ui',
    'app.utils',
    'app.core.annotator',
    'app.core.doc_parser',
    'app.core.model_review',
    'app.core.progress',
    'app.core.result_fusion',
    'app.core.rule_engine',
    'app.llm.llama_inference',
    'app.llm.model_manager',
    'app.llm.prompts',
    'app.models',
    'app.rules.abstract_rules',
    'app.rules.base',
    'app.rules.claims_rules',
    'app.rules.description_rules',
    'app.rules.figures_rules',
    'app.ui.main_window',
    'app.ui.model_download_dialog',
    'app.ui.widgets',
    'app.utils.path_manager',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='App',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='App',
)
