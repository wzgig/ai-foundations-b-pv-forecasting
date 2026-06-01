# -*- coding: utf-8 -*-
"""Shared helpers for the 2025 photovoltaic forecasting scripts.

The original course scripts were written as one-off notebooks/scripts.  These
helpers keep that workflow intact while making file lookup, plotting, and small
data-processing steps less fragile.
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


UTF8_SIG = "utf-8-sig"
DEFAULT_SEED = 42


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


def configure_matplotlib(fonts: Sequence[str] | None = None, dpi: int = 150) -> None:
    """Configure plotting defaults for Chinese labels and paper-style figures."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    font_candidates = list(fonts or ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC"])
    plt.rcParams["font.sans-serif"] = font_candidates
    plt.rcParams["font.family"] = font_candidates
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = dpi
    sns.set_theme(style="whitegrid")


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
