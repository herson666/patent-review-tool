"""模型生命周期管理：下载/加载/卸载"""
import os
import time
from typing import Optional, Callable
import requests
from app.llm.llama_inference import LlamaInference
from app.utils.path_manager import PathManager


# HuggingFace 模型地址
MODEL_HF_URL = (
    "https://huggingface.co/Qwen/Qwen3-4B-Instruct-GGUF/"
    "resolve/main/Qwen3-4B-Instruct-Q4_K_M.gguf?download=true"
)
MODEL_FILENAME = "qwen3-4b-instruct-q4_k_m.gguf"
# 模型估算大小（2.5GB，用于进度条预估）
MODEL_SIZE_BYTES = 2_500_000_000
# 最小文件大小（小于此值视为下载失败/未完成）
MIN_MODEL_SIZE = 1_000_000_000


class ModelManager:
    """模型管理：处理下载、加载、卸载生命周期"""

    def __init__(self):
        self._inference: Optional[LlamaInference] = None

    @property
    def model_path(self) -> str:
        return PathManager.get_model_path(MODEL_FILENAME)

    def is_model_downloaded(self) -> bool:
        """检查模型是否已下载（文件存在且大小合理）"""
        return (os.path.exists(self.model_path)
                and os.path.getsize(self.model_path) >= MIN_MODEL_SIZE)

    def get_downloaded_size(self) -> int:
        """获取已下载大小（字节）"""
        if os.path.exists(self.model_path):
            return os.path.getsize(self.model_path)
        return 0

    def download_model(self,
                       progress_callback: Callable[[int, float], None] = None,
                       cancel_flag: Callable[[], bool] = None) -> bool:
        """
        从 HuggingFace 下载模型。
        progress_callback(percent: int, speed_mbps: float)
        cancel_flag() -> bool: 返回 True 时取消下载
        """
        model_dir = os.path.dirname(self.model_path)
        os.makedirs(model_dir, exist_ok=True)

        response = requests.get(MODEL_HF_URL, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", MODEL_SIZE_BYTES))

        downloaded = 0
        start_time = time.time()
        chunk_size = 1024 * 1024  # 1MB

        try:
            with open(self.model_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if cancel_flag and cancel_flag():
                        return False
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed / 1_000_000 if elapsed > 0 else 0
                        percent = min(int(downloaded * 100 / total_size), 100)
                        if progress_callback:
                            progress_callback(percent, speed)
            return True
        except Exception:
            if os.path.exists(self.model_path):
                try:
                    os.remove(self.model_path)
                except OSError:
                    pass
            raise

    def load_model(self) -> LlamaInference:
        """加载模型到内存"""
        if self._inference is None:
            if not self.is_model_downloaded():
                raise FileNotFoundError(f"模型未下载: {self.model_path}")
            self._inference = LlamaInference(model_path=self.model_path)
            self._inference.load()
        return self._inference

    def unload_model(self):
        """卸载模型释放内存"""
        if self._inference is not None:
            self._inference.unload()
            self._inference = None
            import gc
            gc.collect()

    def is_model_loaded(self) -> bool:
        return self._inference is not None and self._inference.is_loaded()


# 全局单例
model_manager = ModelManager()
