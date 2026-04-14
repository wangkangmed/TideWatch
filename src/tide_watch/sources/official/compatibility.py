"""官方模块迁移兼容说明与聚合 re-export（可选）。

新代码请优先使用：

- ``tide_watch.web.*`` 通用网页能力
- ``tide_watch.sources.official.*`` 编排与 discovery/enrichment
- ``tide_watch.models.ingestion`` 抓取 DTO

历史路径 ``tide_watch.focused.*`` 仍通过各文件顶层的 import 转发保持可用。
"""

from __future__ import annotations
