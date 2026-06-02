# -*- coding: utf-8 -*-
"""Shared helpers for the 2025 photovoltaic forecasting scripts.

The original course scripts were written as one-off notebooks/scripts.  These
helpers keep that workflow intact while making file lookup, plotting, and small
data-processing steps less fragile.
"""

from __future__ import annotations

import os
import random
import re
import json
from pathlib import Path
from typing import Any, Iterable, Sequence
from datetime import datetime, timezone

import numpy as np
import pandas as pd


UTF8_SIG = "utf-8-sig"
DEFAULT_SEED = 42
JOURNAL_FONTS = [
    "SimSun",
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
]
JOURNAL_PALETTE = [
    "#1f77b4",
    "#d62728",
    "#2ca02c",
    "#ff7f0e",
    "#9467bd",
    "#17becf",
    "#8c564b",
    "#7f7f7f",
]


def locate_2025_root(start: str | os.PathLike[str]) -> Path:
    """Return the nearest ancestor that represents the 2025 project folder."""

    path = Path(start).resolve()
    if path.is_file():
        path = path.parent

    for candidate in (path, *path.parents):
        if candidate.name == "2025":
            return candidate
        if (candidate / "00_course_materials").exists() and (
            candidate / "02_problem_solutions"
        ).exists():
            return candidate

    raise FileNotFoundError(f"Cannot locate 2025 root from {start!s}")


def script_dir(file: str | os.PathLike[str]) -> Path:
    """Return the directory containing a script file."""

    return Path(file).resolve().parent


def set_working_directory(file: str | os.PathLike[str]) -> Path:
    """Run relative input/output paths from the script directory."""

    directory = script_dir(file)
    os.chdir(directory)
    return directory


def resolve_input(
    filename: str,
    file: str | os.PathLike[str],
    extra_dirs: Iterable[str | os.PathLike[str]] | None = None,
) -> Path:
    """Find an input file using stable project-level fallback locations."""

    here = script_dir(file)
    root = locate_2025_root(here)
    search_dirs: list[Path] = [here]

    if extra_dirs:
        search_dirs.extend(Path(p).resolve() for p in extra_dirs)

    search_dirs.extend(
        [
            root / "01_modeling_workspace" / "pvod_full_experiment",
            root / "02_problem_solutions" / "problem2_baseline_forecasting",
            root / "02_problem_solutions" / "problem3_scenario_analysis",
            root / "02_problem_solutions" / "problem4_feature_ablation",
            root / "02_problem_solutions" / "problem1_data_analysis",
        ]
    )

    seen: set[Path] = set()
    for directory in search_dirs:
        directory = directory.resolve()
        if directory in seen:
            continue
        seen.add(directory)
        candidate = directory / filename
        if candidate.exists():
            return candidate

    matches = sorted(root.rglob(filename))
    if matches:
        return matches[0]

    searched = ", ".join(str(p) for p in seen)
    raise FileNotFoundError(f"Cannot find {filename!r}. Searched: {searched}")


def _available_matplotlib_font(candidates: Sequence[str]) -> str:
    """Return the first installed font from a candidate list."""

    from matplotlib import font_manager

    available = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in candidates:
        if font_name in available:
            return font_name
    return "DejaVu Sans"


def configure_matplotlib(fonts: Sequence[str] | None = None, dpi: int = 300) -> str:
    """Configure Chinese journal-style plotting defaults.

    The defaults target printable paper figures: high DPI, restrained grids,
    black axes, colorblind-aware line colors, and robust Chinese font fallback.
    """

    import matplotlib.pyplot as plt
    import seaborn as sns

    font_candidates = list(fonts or JOURNAL_FONTS)
    selected_font = _available_matplotlib_font(font_candidates)
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [selected_font, *font_candidates],
            "axes.unicode_minus": False,
            "figure.dpi": dpi,
            "savefig.dpi": 600,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#222222",
            "axes.linewidth": 0.9,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.fontsize": 9.5,
            "lines.linewidth": 1.8,
            "lines.markersize": 5,
            "grid.color": "#d9d9d9",
            "grid.linestyle": "--",
            "grid.linewidth": 0.55,
            "grid.alpha": 0.55,
            "legend.frameon": False,
            "legend.handlelength": 2.2,
            "mathtext.fontset": "stix",
        }
    )
    sns.set_theme(
        style="whitegrid",
        palette=JOURNAL_PALETTE,
        rc={
            "font.sans-serif": [selected_font, *font_candidates],
            "axes.edgecolor": "#222222",
            "axes.linewidth": 0.9,
        },
    )
    return selected_font


def journal_palette(n: int | None = None) -> list[str]:
    """Return the shared color palette used for paper figures."""

    if n is None:
        return list(JOURNAL_PALETTE)
    repeats = (n + len(JOURNAL_PALETTE) - 1) // len(JOURNAL_PALETTE)
    return (JOURNAL_PALETTE * repeats)[:n]


def apply_journal_axes(ax: Any, *, grid: bool = True) -> None:
    """Apply final publication-style cleanup to one Matplotlib axes."""

    ax.grid(grid, axis="both")
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color("#222222")
        spine.set_linewidth(0.9)
    ax.tick_params(direction="out", length=3.5, width=0.8, colors="#222222")


def apply_journal_figure(fig: Any) -> None:
    """Apply publication-style cleanup to all axes in a figure."""

    for ax in fig.axes:
        apply_journal_axes(ax)


def set_random_seed(seed: int = DEFAULT_SEED, torch_module=None) -> None:
    """Make numpy/Python and optional torch code reproducible."""

    random.seed(seed)
    np.random.seed(seed)
    if torch_module is not None:
        torch_module.manual_seed(seed)
        if torch_module.cuda.is_available():
            torch_module.cuda.manual_seed_all(seed)


def make_tail_test_dates(
    df: pd.DataFrame,
    date_col: str = "date_time",
    months: Sequence[int] = (2, 5, 8, 11),
    tail_days: int = 7,
) -> list:
    """Select the last N available dates in each requested month."""

    dates = pd.to_datetime(df[date_col]).dt.date.drop_duplicates().reset_index(drop=True)
    selected: list = []
    for month in months:
        month_dates = dates[dates.map(lambda d: d.month) == month]
        if len(month_dates) >= tail_days:
            selected.extend(month_dates[-tail_days:].tolist())
    return selected


def mark_train_test_by_tail_dates(
    df: pd.DataFrame,
    date_col: str = "date_time",
    months: Sequence[int] = (2, 5, 8, 11),
    tail_days: int = 7,
) -> pd.DataFrame:
    """Add date/month/set/is_daytime columns used by the forecasting scripts."""

    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col])
    result["month"] = result[date_col].dt.month
    result["day"] = result[date_col].dt.day
    result["date"] = result[date_col].dt.date
    test_dates = set(make_tail_test_dates(result, date_col, months, tail_days))
    result["set"] = result["date"].apply(lambda d: "test" if d in test_dates else "train")
    if "power" in result.columns:
        result["is_daytime"] = result["power"] > 0.05
    return result


def minmax_scale_train_only(
    df: pd.DataFrame,
    features: Sequence[str],
    set_col: str = "set",
) -> tuple[pd.DataFrame, dict[str, object], list[str]]:
    """Scale features after fitting each scaler only on training rows."""

    from sklearn.preprocessing import MinMaxScaler

    result = df.copy()
    scalers: dict[str, object] = {}
    scaled_columns: list[str] = []
    train_mask = result[set_col] == "train"

    for feature in features:
        scaler = MinMaxScaler()
        scaler.fit(result.loc[train_mask, [feature]])
        scaled_col = f"{feature}_scaled"
        result[scaled_col] = scaler.transform(result[[feature]])
        scalers[feature] = scaler
        scaled_columns.append(scaled_col)

    return result, scalers, scaled_columns


def safe_qcut(series: pd.Series, q: int, labels: Sequence[str]) -> pd.Series:
    """Quantile-bin a series even when duplicate bin edges reduce bin count."""

    codes, bins = pd.qcut(series, q=q, labels=False, retbins=True, duplicates="drop")
    n_bins = max(len(bins) - 1, 0)
    if n_bins == 0:
        return pd.Series(pd.NA, index=series.index, dtype="object")

    selected_labels = list(labels)[:n_bins]
    if len(selected_labels) < n_bins:
        selected_labels.extend([f"bin_{i + 1}" for i in range(len(selected_labels), n_bins)])

    mapped = pd.Series(codes, index=series.index).map(
        {idx: label for idx, label in enumerate(selected_labels)}
    )
    return mapped.astype("category")


def daylight_metrics(
    true_values: np.ndarray,
    pred_values: np.ndarray,
    timestamps: Sequence,
    df: pd.DataFrame,
    capacity_kw: float = 6600,
) -> dict[str, float]:
    """Compute the attachment-style daylight evaluation metrics."""

    capacity_mw = capacity_kw / 1000.0
    all_true: list[float] = []
    all_pred: list[float] = []

    for idx, ts in enumerate(pd.to_datetime(list(timestamps))):
        mask = (df["date_time"] >= ts) & (df["date_time"] < ts + pd.Timedelta(days=1))
        is_day = df.loc[mask, "is_daytime"].to_numpy()[:96]
        all_true.extend(np.asarray(true_values[idx])[is_day])
        all_pred.extend(np.asarray(pred_values[idx])[is_day])

    y_true = np.asarray(all_true, dtype=float)
    y_pred = np.asarray(all_pred, dtype=float)
    err = (y_true - y_pred) / capacity_mw
    abs_err = np.abs(err)

    corr = np.corrcoef(y_true, y_pred)[0, 1] if len(y_true) > 1 else np.nan
    e_rmse = float(np.sqrt(np.mean(err**2)))
    return {
        "E_rmse": e_rmse,
        "E_mae": float(np.mean(abs_err)),
        "E_me": float(np.mean(err)),
        "r": float(corr),
        "C_R": float((1 - e_rmse) * 100),
        "Q_R": float(np.mean(abs_err < 0.25) * 100),
    }


def write_csv(df: pd.DataFrame, path: str | os.PathLike[str], **kwargs) -> None:
    """Write CSV with parent directory creation and Excel-friendly UTF-8 BOM."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, encoding=UTF8_SIG, **kwargs)


def output_dir(
    file: str | os.PathLike[str],
    *parts: str | os.PathLike[str],
    base: str = "outputs",
) -> Path:
    """Return a stable per-script output directory and create it."""

    target = script_dir(file) / base
    for part in parts:
        target /= Path(part)
    target.mkdir(parents=True, exist_ok=True)
    return target


def output_path(
    file: str | os.PathLike[str],
    *parts: str | os.PathLike[str],
    base: str = "outputs",
) -> Path:
    """Return a path under a script's output folder and create its parent."""

    if not parts:
        return output_dir(file, base=base)
    target = script_dir(file) / base
    for part in parts:
        target /= Path(part)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def save_figure(
    fig: Any,
    path: str | os.PathLike[str],
    *,
    dpi: int = 600,
    close: bool = True,
    show: bool = False,
    **kwargs: Any,
) -> Path:
    """Save a matplotlib figure with consistent defaults."""

    import matplotlib.pyplot as plt

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure = fig if fig is not None else plt.gcf()
    apply_journal_figure(figure)
    figure.savefig(target, dpi=dpi, bbox_inches=kwargs.pop("bbox_inches", "tight"), **kwargs)
    if show:
        plt.show()
    if close:
        plt.close(figure)
    return target


def save_plotly_html(
    fig: Any,
    path: str | os.PathLike[str],
    *,
    include_plotlyjs: str = "cdn",
    auto_open: bool = False,
) -> Path:
    """Save a Plotly figure as HTML without opening a browser."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(target, include_plotlyjs=include_plotlyjs, auto_open=auto_open)
    return target


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def write_json(data: Any, path: str | os.PathLike[str]) -> Path:
    """Write JSON with parent directory creation and readable UTF-8 output."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    return target


class ExperimentArtifacts:
    """Collect tables, figures, predictions, and run summaries for one script."""

    def __init__(self, file: str | os.PathLike[str], base: str = "outputs") -> None:
        self.file = Path(file).resolve()
        self.script_directory = self.file.parent
        self.base = base
        self.root = output_dir(self.file, base=base)
        self.artifacts: dict[str, list[str]] = {
            "predictions": [],
            "metrics": [],
            "figures": [],
            "reports": [],
        }

    def directory(self, category: str) -> Path:
        target = self.root / category
        target.mkdir(parents=True, exist_ok=True)
        return target

    def path(self, category: str, filename: str | os.PathLike[str]) -> Path:
        candidate = Path(filename)
        if candidate.is_absolute():
            target = candidate
        elif candidate.parent != Path("."):
            target = self.root / candidate
        else:
            target = self.directory(category) / candidate
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def record(self, category: str, path: str | os.PathLike[str]) -> Path:
        target = Path(path)
        try:
            recorded = str(target.resolve().relative_to(self.script_directory))
        except ValueError:
            recorded = str(target)
        self.artifacts.setdefault(category, [])
        if recorded not in self.artifacts[category]:
            self.artifacts[category].append(recorded)
        return target

    def write_csv(
        self,
        category: str,
        filename: str | os.PathLike[str],
        df: pd.DataFrame,
        **kwargs: Any,
    ) -> Path:
        target = self.path(category, filename)
        write_csv(df, target, **kwargs)
        return self.record(category, target)

    def save_figure(
        self,
        filename: str | os.PathLike[str],
        fig: Any = None,
        *,
        category: str = "figures",
        show: bool = False,
        close: bool = True,
        dpi: int = 600,
        **kwargs: Any,
    ) -> Path:
        target = self.path(category, filename)
        save_figure(fig, target, show=show, close=close, dpi=dpi, **kwargs)
        return self.record(category, target)

    def save_plotly_html(
        self,
        filename: str | os.PathLike[str],
        fig: Any,
        *,
        category: str = "figures",
        include_plotlyjs: str = "cdn",
        auto_open: bool = False,
    ) -> Path:
        target = self.path(category, filename)
        save_plotly_html(
            fig,
            target,
            include_plotlyjs=include_plotlyjs,
            auto_open=auto_open,
        )
        return self.record(category, target)

    def write_summary(
        self,
        metadata: dict[str, Any],
        filename: str = "run_summary.json",
    ) -> Path:
        target = self.path("reports", filename)
        self.record("reports", target)
        payload = {
            "script": self.file.name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
            "artifacts": self.artifacts,
        }
        write_json(payload, target)
        return target


def slugify_checkpoint_name(name: str) -> str:
    """Make a model/checkpoint name safe for Windows and Git paths."""

    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", str(name), flags=re.UNICODE).strip("._")
    return text or "model"


def build_torch_checkpoint_signature(
    model: Any,
    train_X: np.ndarray,
    train_Y: np.ndarray,
    *,
    input_length: int | None = None,
    batch_size: int | None = None,
    epochs: int | None = None,
    lr: float | None = None,
    patience: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe the training setup enough to avoid loading stale checkpoints."""

    signature: dict[str, Any] = {
        "model_class": model.__class__.__name__,
        "train_X_shape": tuple(np.asarray(train_X).shape),
        "train_Y_shape": tuple(np.asarray(train_Y).shape),
        "input_length": input_length,
        "batch_size": batch_size,
        "epochs": epochs,
        "lr": lr,
        "patience": patience,
    }
    if extra:
        signature.update(extra)
    return signature


def torch_checkpoint_path(
    checkpoint_name: str,
    directory: str | os.PathLike[str] = "models",
) -> Path:
    """Return the checkpoint file path for a named model run."""

    return Path(directory) / f"{slugify_checkpoint_name(checkpoint_name)}.pth"


def try_load_torch_checkpoint(
    model: Any,
    path: str | os.PathLike[str],
    signature: dict[str, Any],
    *,
    torch_module: Any,
    device: Any,
) -> tuple[bool, float | None]:
    """Load a compatible checkpoint and return whether it was reused."""

    checkpoint_path = Path(path)
    if not checkpoint_path.exists():
        return False, None

    checkpoint = torch_module.load(checkpoint_path, map_location=device)
    if not isinstance(checkpoint, dict) or "state_dict" not in checkpoint:
        return False, None

    if checkpoint.get("signature") != signature:
        return False, None

    model.load_state_dict(checkpoint["state_dict"])
    model.to(device)
    model.eval()
    return True, checkpoint.get("max_power")


def save_torch_checkpoint(
    model: Any,
    path: str | os.PathLike[str],
    signature: dict[str, Any],
    *,
    torch_module: Any,
    max_power: float,
    best_val_loss: float | None = None,
) -> None:
    """Save a reusable PyTorch checkpoint with metadata."""

    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch_module.save(
        {
            "format_version": 1,
            "signature": signature,
            "state_dict": model.state_dict(),
            "max_power": float(max_power),
            "best_val_loss": None if best_val_loss is None else float(best_val_loss),
        },
        checkpoint_path,
    )
