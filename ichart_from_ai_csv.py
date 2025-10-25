# ichart_from_ai_csv.py
# Build an I-Chart for the "AI Snapshot" using precomputed stats.
# - Select FIRST N rows (latest-first CSV) for the chosen parameter, then display oldest->newest.
# - Use *only* AI_Mean_Value and AI_Sigma_Value (precomputed). If missing -> error.
# - Color points: green (|z|<=1σ), amber (1σ<|z|<=3σ), red (|z|>3σ).
# - Mean/UCL/LCL lines in gray; Design line in purple (distinct).
# - No chart title; parameter label bottom-centered.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

_KNOWN_TS_FORMATS = (
    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
)

GREEN = "#2E7D32"       # within ±1σ
AMBER = "#FFBF00"       # between 1σ and 3σ
RED   = "#D32F2F"       # OOC >3σ
DESIGN_COLOR = "tab:purple"  # not used elsewhere

def _parse_ts_series(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    best = None
    best_non_null = -1
    for fmt in _KNOWN_TS_FORMATS:
        parsed = pd.to_datetime(s, format=fmt, errors="coerce")
        nn = parsed.notna().sum()
        if nn > best_non_null:
            best_non_null = nn
            best = parsed
        if nn == len(s):
            return parsed
    fallback = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return fallback if (best is None or fallback.notna().sum() > best_non_null) else best

def build_ichart_from_ai(csv_path: str, param_name: str, window_minutes: int):
    # Load & filter all rows for the parameter
    df = pd.read_csv(csv_path, low_memory=False)
    if "parameter_name" not in df.columns:
        raise ValueError("CSV must contain a 'parameter_name' column.")
    all_param = df[df["parameter_name"].astype(str).str.upper() == str(param_name).upper()].copy()
    if all_param.empty:
        raise ValueError(f"No rows for parameter_name='{param_name}' in {csv_path}")

    # Precomputed stats are REQUIRED
    def _first_num(col: str):
        if col in all_param.columns:
            s = pd.to_numeric(all_param[col], errors="coerce").dropna()
            if not s.empty:
                return float(s.iloc[0])
        return None

    mean  = _first_num("AI_Mean_Value")
    sigma = _first_num("AI_Sigma_Value")
    if mean is None or sigma is None or not np.isfinite(mean) or not np.isfinite(sigma):
        raise ValueError("AI_Mean_Value / AI_Sigma_Value must be present and non-null for the selected parameter.")

    UCL, LCL = mean + 3.0 * sigma, mean - 3.0 * sigma

    # Take FIRST N rows (latest-first), then plot chronologically
    d = all_param.head(int(window_minutes)).copy()

    if "ts" in d.columns:
        d["ts"] = _parse_ts_series(d["ts"])
        d = d.dropna(subset=["ts"]).sort_values("ts")
        x = d["ts"]; xlab = f"Time - {window_minutes} min (latest→future window, AI)"
    else:
        d = d.iloc[::-1].reset_index(drop=True)
        x = d.index; xlab = "Index"

    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    d = d.dropna(subset=["value"])
    y = d["value"].to_numpy()

    unit = ""
    if "param_unit" in d.columns:
        u = d["param_unit"].dropna().astype(str).str.strip()
        if not u.empty:
            unit = u.iloc[0]

    design = None
    if "Design_Value" in all_param.columns:
        dv = pd.to_numeric(all_param["Design_Value"], errors="coerce").dropna()
        if not dv.empty:
            design = float(dv.iloc[0])

    # --- Figure (compact; constrained layout; no title) ---
    try:
        fig, ax = plt.subplots(figsize=(10.4, 3.5), dpi=120, layout="constrained")
        using_constrained = True
    except TypeError:
        fig, ax = plt.subplots(figsize=(10.4, 3.5), dpi=120)
        using_constrained = False

    # Thin line for continuity
    ax.plot(x, y, linewidth=1.1, color="#555", alpha=0.85)

    # Color-coded markers by distance from mean
    z = np.abs(y - mean)
    red_mask   = z > 3.0 * sigma
    green_mask = z <= 1.0 * sigma
    amber_mask = ~(green_mask | red_mask)  # between 1σ and 3σ

    if np.any(green_mask):
        ax.scatter(x[green_mask], y[green_mask], s=18, color=GREEN, zorder=3)
    if np.any(amber_mask):
        ax.scatter(x[amber_mask], y[amber_mask], s=18, color=AMBER, zorder=3)
    if np.any(red_mask):
        ax.scatter(x[red_mask], y[red_mask], s=20, color=RED, zorder=4)

    # Lines (short labels keep legend on one line)
    ax.axhline(mean, linestyle="-",  linewidth=1.0, color="#333", label="Mean")
    ax.axhline(UCL,  linestyle="--", linewidth=1.0, color="#666", label="UCL 3σ")
    ax.axhline(LCL,  linestyle="--", linewidth=1.0, color="#666", label="LCL −3σ")

    if design is not None:
        ax.axhline(design, linestyle="-", linewidth=2.6, color=DESIGN_COLOR, label="Design")

    ax.set_xlabel(xlab)
    ax.set_ylabel(f"Value [{unit}]" if unit else "Value")

    # Legend one row, top inside
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles, labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=max(1, len(labels)),
        frameon=False,
        fontsize=9,
        handlelength=2.2,
        columnspacing=1.0,
        borderaxespad=0.0,
    )

    # Bottom-centered parameter label
    fig.text(0.30, 0.20, f"{param_name}", ha="center", fontsize=10, color="tomato")

    if not using_constrained:
        fig.tight_layout(rect=[0.02, 0.06, 0.98, 0.90])

    return fig

# CLI for quick local test
if __name__ == "__main__":
    import argparse, matplotlib.pyplot as plt
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--param", required=True)
    ap.add_argument("--window", type=int, required=True)
    args = ap.parse_args()
    fig = build_ichart_from_ai(args.csv, args.param, args.window)
    plt.show()
