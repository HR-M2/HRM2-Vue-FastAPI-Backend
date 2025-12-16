"""
任务进度内存缓存模块

用于存储任务的实时进度，避免频繁写入数据库。
前端通过轮询 /status API 获取进度。
"""
from typing import Dict, Optional
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class TaskProgress:
    """任务进度数据"""
    progress: int = 0
    current_speaker: str = ""
    step: int = 0
    total_steps: int = 6


class ProgressCache:
    """
    线程安全的进度缓存
    
    使用内存字典存储任务进度，任务完成后自动清理。
    """
    
    def __init__(self):
        self._cache: Dict[str, TaskProgress] = {}
        self._lock = Lock()
    
    def update(
        self,
        task_id: str,
        progress: int = None,
        current_speaker: str = None,
        step: int = None
    ) -> None:
        """更新任务进度"""
        with self._lock:
            if task_id not in self._cache:
                self._cache[task_id] = TaskProgress()
            
            entry = self._cache[task_id]
            if progress is not None:
                entry.progress = progress
            if current_speaker is not None:
                entry.current_speaker = current_speaker
            if step is not None:
                entry.step = step
                # 自动计算进度百分比
                entry.progress = int((step / entry.total_steps) * 100)
    
    def get(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务进度"""
        with self._lock:
            return self._cache.get(task_id)
    
    def remove(self, task_id: str) -> None:
        """移除任务进度（任务完成后调用）"""
        with self._lock:
            self._cache.pop(task_id, None)
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()


# 全局单例
progress_cache = ProgressCache()
