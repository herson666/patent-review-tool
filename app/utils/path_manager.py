"""用户安装路径管理：所有数据写入用户指定目录，不写系统盘"""
import os
import json
from pathlib import Path


# 默认安装目录
DEFAULT_INSTALL_DIR = os.path.expanduser("~/PatentReviewTool")
CONFIG_FILE = "config.json"


class PathManager:
    """路径管理（所有用户数据都在安装目录下）"""
    DEFAULT_INSTALL_DIR = DEFAULT_INSTALL_DIR
    _install_dir: str = DEFAULT_INSTALL_DIR
    _config: dict = {}

    @classmethod
    def set_install_dir(cls, path: str):
        """设置用户安装根目录"""
        cls._install_dir = path
        cls.ensure_dirs()

    @classmethod
    def get_install_dir(cls) -> str:
        return cls._install_dir

    @classmethod
    def ensure_dirs(cls):
        """确保所有子目录存在"""
        subdirs = ["models", "cache", "exports", "bin"]
        for sub in subdirs:
            os.makedirs(os.path.join(cls._install_dir, sub), exist_ok=True)

    @classmethod
    def get_model_path(cls, filename: str = "qwen3-4b-instruct-q4_k_m.gguf") -> str:
        return os.path.join(cls._install_dir, "models", filename)

    @classmethod
    def get_cache_dir(cls) -> str:
        return os.path.join(cls._install_dir, "cache")

    @classmethod
    def get_exports_dir(cls) -> str:
        return os.path.join(cls._install_dir, "exports")

    @classmethod
    def get_config_path(cls) -> str:
        return os.path.join(cls._install_dir, CONFIG_FILE)

    @classmethod
    def save_config(cls, config: dict):
        with open(cls.get_config_path(), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_config(cls) -> dict:
        path = cls.get_config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    @classmethod
    def get_default_dir(cls) -> str:
        """获取默认建议目录"""
        return DEFAULT_INSTALL_DIR
