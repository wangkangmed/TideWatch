"""asyncio / queue 驱动的图执行封装（占位）。"""


async def run_acquisition_job(thread_id: str) -> None:
    """从 checkpoint 恢复同一 thread_id 的运行。"""
    raise NotImplementedError
