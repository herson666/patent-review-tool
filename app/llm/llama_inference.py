"""llama-cpp-python 推理封装"""
import gc
import os
from typing import Optional


class LlamaInference:
    """
    llama-cpp-python 推理封装，提供：
    - 模型加载 / 卸载
    - 同步推理接口
    - 内存管理
    """

    def __init__(self, model_path: str, n_ctx: int = 4096,
                 n_threads: int = 8, n_gpu_layers: int = 0,
                 chat_format: str = "qwen"):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.chat_format = chat_format
        self._model = None

    def load(self):
        """加载模型到内存（懒加载）"""
        if self._model is not None:
            return
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
        from llama_cpp import Llama
        self._model = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,
            n_gpu_layers=self.n_gpu_layers,
            chat_format=self.chat_format,
            verbose=False
        )

    def unload(self):
        """卸载模型，释放内存"""
        if self._model is not None:
            del self._model
            self._model = None
            gc.collect()

    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._model is not None

    def generate(self, prompt: str, max_tokens: int = 512,
                 temperature: float = 0.1,
                 stop: Optional[list] = None) -> str:
        """同步推理（基于 prompt）"""
        if self._model is None:
            self.load()
        if stop is None:
            stop = ["</s>", "null", "\n\n"]
        response = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop
        )
        return response["choices"][0]["text"].strip()

    def chat(self, messages: list, max_tokens: int = 512,
             temperature: float = 0.1) -> str:
        """对话接口（OpenAI 风格）"""
        if self._model is None:
            self.load()
        response = self._model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response["choices"][0]["message"]["content"].strip()
