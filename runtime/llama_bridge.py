from __future__ import annotations

import ctypes
import json
import logging
import os
from ctypes import c_int, c_void_p
from dataclasses import dataclass
from pathlib import Path

from .flash_io import AsyncFlashReader, FlashIOConfig, FlashLayoutEntry

logger = logging.getLogger(__name__)

_LLAMA_LIB: ctypes.CDLL | None = None


def _load_llama(path: str | None = None) -> ctypes.CDLL | None:
    candidates = [path] if path else [
        "libllama.so", "libllama.dylib",
        "/usr/local/lib/libllama.so",
        os.path.expanduser("~/llama.cpp/build/libllama.so"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return ctypes.CDLL(c)
    return None


def _declare_ffi(lib: ctypes.CDLL) -> None:
    lib.llama_eval.restype = c_int
    lib.llama_eval.argtypes = [c_void_p, c_int, c_int, c_int]
    lib.llama_n_vocab.restype = c_int
    lib.llama_n_vocab.argtypes = [c_void_p]
    lib.llama_get_logits.restype = c_void_p
    lib.llama_get_logits.argtypes = [c_void_p]


@dataclass
class LlamaBridgeConfig:
    model_path: str | Path = ""
    n_gpu_layers: int = 0
    n_ctx: int = 4096
    n_batch: int = 512
    flash_device: str | Path = "/dev/nvme0n1"
    dram_buffer_gb: int = 8
    enable_prefetch: bool = True
    lookahead_tokens: int = 8


@dataclass
class BridgeMetrics:
    kv_loads_from_flash: int = 0
    kv_loads_from_dram: int = 0
    prefetches_issued: int = 0
    prefetch_hits: int = 0
    bytes_read_from_flash: int = 0
    total_inference_time_s: float = 0.0


class LlamaBridge:
    def __init__(self, config: LlamaBridgeConfig):
        self.config = config
        self._ctx: ctypes.c_void_p | None = None
        self._model: ctypes.c_void_p | None = None
        self._lib: ctypes.CDLL | None = _load_llama()
        self.flash_reader = AsyncFlashReader(
            FlashIOConfig(device_path=config.flash_device)
        ) if config.flash_device else None
        self.metrics = BridgeMetrics()
        self._kv_layout: dict[str, FlashLayoutEntry] = {}

    def is_available(self) -> bool:
        return self._lib is not None

    def load_model(self, model_path: str | Path) -> bool:
        if not self.is_available():
            return False
        _declare_ffi(self._lib)
        self._model = ctypes.c_void_p()
        return True

    def register_kv_layout(self, layout_path: str | Path) -> None:
        with open(layout_path) as f:
            entries = json.load(f)
        for e in entries:
            entry = FlashLayoutEntry(**e)
            self._kv_layout[entry.object_id] = entry
            if self.flash_reader:
                self.flash_reader.register_layout(entry)

    def kv_load(self, object_id: str) -> tuple[c_void_p, int]:
        if self._kv_layout.get(object_id) and self.flash_reader:
            req = self.flash_reader.submit_read(object_id)
            if req:
                self.metrics.kv_loads_from_flash += 1
                self.metrics.flash_reads += 1
                self.flash_reader.wait_completion(object_id)
                return (ctypes.c_void_p(req.buffer_addr), req.size_bytes)
        self.metrics.kv_loads_from_dram += 1
        return (ctypes.c_void_p(0), 0)

    def maybe_prefetch(self, future_ids: list[str]) -> None:
        if not self.config.enable_prefetch or not self.flash_reader:
            return
        for oid in future_ids[: self.config.lookahead_tokens]:
            req = self.flash_reader.submit_read(oid)
            if req:
                self.metrics.prefetches_issued += 1
                self.metrics.prefetch_hits += 1

    def run_inference(self, tokens: list[int]) -> bool:
        if not self._ctx:
            return False
        result = self._lib.llama_eval(self._ctx, (c_int * len(tokens))(*tokens), len(tokens), 0, 1)
        return result == 0

    def get_logits(self) -> list[float]:
        if not self._ctx:
            return []
        n_vocab = self._lib.llama_n_vocab(self._ctx)
        ptr = self._lib.llama_get_logits(self._ctx)
        arr = (ctypes.c_float * n_vocab).from_address(ptr)
        return list(arr)

    def close(self) -> None:
        if self.flash_reader:
            self.flash_reader.close()
        self._ctx = None
        self._model = None