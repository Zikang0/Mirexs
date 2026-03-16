"""
布局引擎（Layout Engine）

为视觉反馈提供“结构化布局计算”，以便后续接入真正 UI 框架。
当前实现提供两种常用布局：
- vertical_stack：垂直堆叠
- grid：网格布局
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class LayoutRect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class LayoutItem:
    item_id: str
    preferred_size: Tuple[int, int] = (0, 0)  # (w, h)
    min_size: Tuple[int, int] = (0, 0)


class LayoutEngine:
    """简单布局引擎"""

    def vertical_stack(
        self,
        items: List[LayoutItem],
        container: LayoutRect,
        padding: int = 8,
        spacing: int = 8,
        fixed_item_height: Optional[int] = None,
    ) -> Dict[str, LayoutRect]:
        rects: Dict[str, LayoutRect] = {}
        x = container.x + padding
        y = container.y + padding
        width = max(0, container.width - padding * 2)

        for item in items:
            pref_w, pref_h = item.preferred_size
            min_w, min_h = item.min_size

            h = fixed_item_height if fixed_item_height is not None else max(min_h, pref_h)
            h = max(0, h)

            rects[item.item_id] = LayoutRect(x=x, y=y, width=max(width, min_w), height=h)
            y += h + spacing

        return rects

    def grid(
        self,
        items: List[LayoutItem],
        container: LayoutRect,
        columns: int = 2,
        padding: int = 8,
        spacing: int = 8,
        row_height: Optional[int] = None,
    ) -> Dict[str, LayoutRect]:
        if columns <= 0:
            columns = 1

        rects: Dict[str, LayoutRect] = {}

        inner_x = container.x + padding
        inner_y = container.y + padding
        inner_w = max(0, container.width - padding * 2)

        col_w = max(0, (inner_w - spacing * (columns - 1)) // columns)

        for idx, item in enumerate(items):
            row = idx // columns
            col = idx % columns

            x = inner_x + col * (col_w + spacing)
            y = inner_y + row * ((row_height or 0) + spacing)

            pref_w, pref_h = item.preferred_size
            min_w, min_h = item.min_size

            w = max(min_w, min(col_w, pref_w or col_w))
            h = row_height if row_height is not None else max(min_h, pref_h)

            rects[item.item_id] = LayoutRect(x=x, y=y, width=w, height=h)

        return rects


