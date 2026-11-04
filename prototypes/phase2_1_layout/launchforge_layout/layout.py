"""Small, schema-free layout reference implementation.

All geometry is expressed in logical UI units. DPI conversion belongs to the
renderer/presentation boundary and is intentionally outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Sequence

_EPSILON = 1e-9


class Axis(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class SizeMode(str, Enum):
    FIXED = "fixed"
    FIT = "fit"
    FILL = "fill"


class Alignment(str, Enum):
    START = "start"
    CENTER = "center"
    END = "end"
    STRETCH = "stretch"


class MainDistribution(str, Enum):
    START = "start"
    CENTER = "center"
    END = "end"
    SPACE_BETWEEN = "space-between"


class Direction(str, Enum):
    LTR = "ltr"
    RTL = "rtl"


def _finite_non_negative(name: str, value: float) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite, non-negative number")


def _finite(name: str, value: float) -> None:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        _finite("x", self.x)
        _finite("y", self.y)
        _finite_non_negative("width", self.width)
        _finite_non_negative("height", self.height)

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class Insets:
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0

    def __post_init__(self) -> None:
        for name in ("top", "right", "bottom", "left"):
            _finite_non_negative(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AxisSpec:
    """A dimension request with optional minimum and maximum bounds.

    For FILL, value is the positive flex weight. For FIXED it is the requested
    logical size. FIT measures the child's intrinsic size.
    """

    mode: SizeMode
    value: float = 0.0
    minimum: float = 0.0
    maximum: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SizeMode):
            raise ValueError("mode must be a supported SizeMode")
        _finite_non_negative("value", self.value)
        _finite_non_negative("minimum", self.minimum)
        if self.maximum is not None:
            _finite_non_negative("maximum", self.maximum)
            if self.maximum < self.minimum:
                raise ValueError("maximum must be greater than or equal to minimum")
        if self.mode is SizeMode.FILL and self.value <= 0:
            raise ValueError("fill weight must be greater than zero")

    @classmethod
    def fixed(
        cls, value: float, *, minimum: float = 0.0, maximum: float | None = None
    ) -> "AxisSpec":
        return cls(SizeMode.FIXED, value, minimum, maximum)

    @classmethod
    def fit(
        cls, *, minimum: float = 0.0, maximum: float | None = None
    ) -> "AxisSpec":
        return cls(SizeMode.FIT, 0.0, minimum, maximum)

    @classmethod
    def fill(
        cls, weight: float = 1.0, *, minimum: float = 0.0, maximum: float | None = None
    ) -> "AxisSpec":
        return cls(SizeMode.FILL, weight, minimum, maximum)


@dataclass(frozen=True, slots=True)
class LayoutChild:
    key: str
    width: AxisSpec
    height: AxisSpec
    intrinsic_width: float = 0.0
    intrinsic_height: float = 0.0

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("child key must not be empty")
        if not isinstance(self.width, AxisSpec) or not isinstance(self.height, AxisSpec):
            raise ValueError("width and height must be AxisSpec instances")
        _finite_non_negative("intrinsic_width", self.intrinsic_width)
        _finite_non_negative("intrinsic_height", self.intrinsic_height)


@dataclass(frozen=True, slots=True)
class OverlayChild(LayoutChild):
    align_x: Alignment = Alignment.CENTER
    align_y: Alignment = Alignment.CENTER


@dataclass(frozen=True, slots=True)
class PlacedItem:
    key: str
    bounds: Rect


@dataclass(frozen=True, slots=True)
class LayoutResult:
    items: tuple[PlacedItem, ...]
    overflow_x: bool = False
    overflow_y: bool = False

    def by_key(self, key: str) -> Rect:
        for item in self.items:
            if item.key == key:
                return item.bounds
        raise KeyError(key)


def _clamp(value: float, spec: AxisSpec) -> float:
    value = max(value, spec.minimum)
    if spec.maximum is not None:
        value = min(value, spec.maximum)
    return value


def _natural_size(spec: AxisSpec, intrinsic: float) -> float:
    if spec.mode is SizeMode.FIXED:
        requested = spec.value
    elif spec.mode is SizeMode.FIT:
        requested = intrinsic
    else:
        raise ValueError("fill dimensions must be resolved against available space")
    return _clamp(requested, spec)


def _allocate_fill(specs: Sequence[AxisSpec], available: float) -> list[float]:
    """Allocate by flex weight, freezing constrained children and redistributing."""

    allocations = [0.0] * len(specs)
    active = set(range(len(specs)))
    remaining = max(0.0, available)

    while active:
        total_weight = sum(specs[index].value for index in active)
        proposed = {
            index: remaining * specs[index].value / total_weight
            for index in active
        }
        clamped: dict[int, float] = {}
        for index, share in proposed.items():
            spec = specs[index]
            if share < spec.minimum - _EPSILON:
                clamped[index] = spec.minimum
            elif spec.maximum is not None and share > spec.maximum + _EPSILON:
                clamped[index] = spec.maximum

        if not clamped:
            for index, share in proposed.items():
                allocations[index] = share
            break

        for index, value in clamped.items():
            allocations[index] = value
            active.remove(index)
            remaining -= value
        remaining = max(0.0, remaining)

    return allocations


def _inner_rect(bounds: Rect, padding: Insets) -> Rect:
    return Rect(
        bounds.x + padding.left,
        bounds.y + padding.top,
        max(0.0, bounds.width - padding.left - padding.right),
        max(0.0, bounds.height - padding.top - padding.bottom),
    )


def _cross_position(
    inner: Rect,
    size: float,
    *,
    axis: Axis,
    alignment: Alignment,
    direction: Direction,
) -> tuple[float, float]:
    if axis is Axis.HORIZONTAL:
        origin, available = inner.y, inner.height
        start_at_end = False
    else:
        origin, available = inner.x, inner.width
        start_at_end = direction is Direction.RTL

    if alignment is Alignment.CENTER:
        offset = (available - size) / 2.0
    elif alignment is Alignment.END:
        offset = 0.0 if start_at_end else available - size
    else:  # START and STRETCH use the logical start edge.
        offset = available - size if start_at_end else 0.0
    return origin + offset, size


def layout_stack(
    bounds: Rect,
    children: Sequence[LayoutChild],
    *,
    axis: Axis,
    padding: Insets = Insets(),
    gap: float = 0.0,
    justify: MainDistribution = MainDistribution.START,
    align_items: Alignment = Alignment.START,
    direction: Direction = Direction.LTR,
) -> LayoutResult:
    """Resolve a stack into logical rectangles without renderer-specific units."""

    _finite_non_negative("gap", gap)
    if not isinstance(axis, Axis):
        raise ValueError("axis must be horizontal or vertical")
    if not isinstance(direction, Direction):
        raise ValueError("direction must be LTR or RTL")
    if not isinstance(justify, MainDistribution) or not isinstance(align_items, Alignment):
        raise ValueError("unsupported stack alignment or distribution")
    keys = [child.key for child in children]
    if len(keys) != len(set(keys)):
        raise ValueError("child keys must be unique within a layout")

    inner = _inner_rect(bounds, padding)
    if axis is Axis.HORIZONTAL:
        available_main, available_cross = inner.width, inner.height
        main_specs = [child.width for child in children]
        cross_specs = [child.height for child in children]
        main_intrinsic = [child.intrinsic_width for child in children]
        cross_intrinsic = [child.intrinsic_height for child in children]
    else:
        available_main, available_cross = inner.height, inner.width
        main_specs = [child.height for child in children]
        cross_specs = [child.width for child in children]
        main_intrinsic = [child.intrinsic_height for child in children]
        cross_intrinsic = [child.intrinsic_width for child in children]

    natural_sizes = [
        _natural_size(spec, intrinsic) if spec.mode is not SizeMode.FILL else None
        for spec, intrinsic in zip(main_specs, main_intrinsic)
    ]
    fill_indices = [i for i, spec in enumerate(main_specs) if spec.mode is SizeMode.FILL]
    base_gaps = gap * max(0, len(children) - 1)
    fixed_total = sum(size for size in natural_sizes if size is not None)
    fill_available = max(0.0, available_main - fixed_total - base_gaps)
    fill_sizes = _allocate_fill([main_specs[i] for i in fill_indices], fill_available)

    main_sizes = list(natural_sizes)
    for index, size in zip(fill_indices, fill_sizes):
        main_sizes[index] = size
    resolved_main = [float(size) for size in main_sizes]

    used_main = sum(resolved_main) + base_gaps
    leftover = max(0.0, available_main - used_main)
    leading = 0.0
    extra_gap = 0.0
    if justify is MainDistribution.CENTER:
        leading = leftover / 2.0
    elif justify is MainDistribution.END:
        leading = leftover
    elif justify is MainDistribution.SPACE_BETWEEN and len(children) > 1:
        extra_gap = leftover / (len(children) - 1)

    rtl_main = axis is Axis.HORIZONTAL and direction is Direction.RTL
    if rtl_main:
        cursor = inner.right - leading
    elif axis is Axis.VERTICAL:
        cursor = inner.y + leading
    else:
        cursor = inner.x + leading

    items: list[PlacedItem] = []
    cross_overflow = False
    for child, main_size, cross_spec, intrinsic_cross in zip(
        children, resolved_main, cross_specs, cross_intrinsic
    ):
        if cross_spec.mode is SizeMode.FILL or align_items is Alignment.STRETCH:
            cross_size = _clamp(available_cross, cross_spec)
            cross_alignment = Alignment.STRETCH
        else:
            cross_size = _natural_size(cross_spec, intrinsic_cross)
            cross_alignment = align_items

        cross_origin, final_cross_size = _cross_position(
            inner,
            cross_size,
            axis=axis,
            alignment=cross_alignment,
            direction=direction,
        )
        cross_overflow = cross_overflow or final_cross_size > available_cross + _EPSILON

        if axis is Axis.HORIZONTAL:
            if rtl_main:
                x = cursor - main_size
                cursor = x - gap - extra_gap
            else:
                x = cursor
                cursor = x + main_size + gap + extra_gap
            rect = Rect(x, cross_origin, main_size, final_cross_size)
        else:
            y = cursor
            cursor = y + main_size + gap + extra_gap
            rect = Rect(cross_origin, y, final_cross_size, main_size)
        items.append(PlacedItem(child.key, rect))

    main_overflow = used_main > available_main + _EPSILON
    if axis is Axis.HORIZONTAL:
        return LayoutResult(tuple(items), overflow_x=main_overflow, overflow_y=cross_overflow)
    return LayoutResult(tuple(items), overflow_x=cross_overflow, overflow_y=main_overflow)


def _overlay_axis(
    origin: float,
    available: float,
    spec: AxisSpec,
    intrinsic: float,
    alignment: Alignment,
    *,
    reverse_start: bool,
) -> tuple[float, float]:
    if spec.mode is SizeMode.FILL or alignment is Alignment.STRETCH:
        size = _clamp(available, spec)
    else:
        size = _natural_size(spec, intrinsic)

    if alignment is Alignment.CENTER:
        offset = (available - size) / 2.0
    elif alignment is Alignment.END:
        offset = 0.0 if reverse_start else available - size
    else:
        offset = available - size if reverse_start else 0.0
    return origin + offset, size


def layout_overlay(
    bounds: Rect,
    children: Sequence[OverlayChild],
    *,
    padding: Insets = Insets(),
    direction: Direction = Direction.LTR,
) -> LayoutResult:
    """Place each child independently inside the same padded overlay bounds."""

    if not isinstance(direction, Direction):
        raise ValueError("direction must be LTR or RTL")
    keys = [child.key for child in children]
    if len(keys) != len(set(keys)):
        raise ValueError("child keys must be unique within a layout")
    if any(not isinstance(child.align_x, Alignment) or not isinstance(child.align_y, Alignment) for child in children):
        raise ValueError("overlay alignment must be supported Alignment values")

    inner = _inner_rect(bounds, padding)
    items: list[PlacedItem] = []
    overflow_x = False
    overflow_y = False
    for child in children:
        x, width = _overlay_axis(
            inner.x, inner.width, child.width, child.intrinsic_width,
            child.align_x, reverse_start=direction is Direction.RTL,
        )
        y, height = _overlay_axis(
            inner.y, inner.height, child.height, child.intrinsic_height,
            child.align_y, reverse_start=False,
        )
        overflow_x = overflow_x or x < inner.x - _EPSILON or x + width > inner.right + _EPSILON
        overflow_y = overflow_y or y < inner.y - _EPSILON or y + height > inner.bottom + _EPSILON
        items.append(PlacedItem(child.key, Rect(x, y, width, height)))
    return LayoutResult(tuple(items), overflow_x, overflow_y)
