import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

_KNOWN_TS_FORMATS = (
    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
)

def _parse_ts_series(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    # Try exact formats first (no warnings), then dayfirst=True fallback
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

def build_ichart_from_history(csv_path: str, param_name: str):
    """Return a Matplotlib Figure for `param_name` using mean/sigma/design from the CSV."""
    df = pd.read_csv(csv_path, low_memory=False)
    if "parameter_name" not in df.columns:
        raise ValueError("CSV must contain a 'parameter_name' column.")

    d = df[df["parameter_name"].astype(str).str.upper() == str(param_name).upper()].copy()
    if d.empty:
        raise ValueError(f"No rows for parameter_name='{param_name}' in {csv_path}")

    # X axis (timestamp preferred)
    if "ts" in d.columns:
        d["ts"] = _parse_ts_series(d["ts"])
        d = d.dropna(subset=["ts"]).sort_values("ts")
        x = d["ts"]; xlab = "Time"
    else:
        d = d.reset_index(drop=True)
        x = d.index; xlab = "Index"

    # y values
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    d = d.dropna(subset=["value"])
    y = d["value"].to_numpy()

    # Stats from CSV (no recompute)
    mean  = pd.to_numeric(d["History_Mean_Value"], errors="coerce").dropna().iloc[0]
    sigma = pd.to_numeric(d["History_Sigma_Value"], errors="coerce").dropna().iloc[0]
    UCL, LCL = mean + 3 * sigma, mean - 3 * sigma

    # Optional design value
    design = None
    if "Design_Value" in d.columns:
        dv = pd.to_numeric(d["Design_Value"], errors="coerce").dropna()
        if not dv.empty:
            design = float(dv.iloc[0])

    # Unit (optional)
    unit = ""
    if "param_unit" in d.columns:
        u = d["param_unit"].dropna().astype(str).str.strip()
        if not u.empty:
            unit = u.iloc[0]

    # ---- Figure (no title). Use constrained layout; avoid tight_layout warning. ----
    try:
        fig, ax = plt.subplots(figsize=(10.4, 3.5), dpi=120, layout="constrained")
        using_constrained = True
    except TypeError:  # older Matplotlib
        fig, ax = plt.subplots(figsize=(10.4, 3.5), dpi=120)
        using_constrained = False

    # Series line
    ax.plot(x, y, linewidth=1.6, label="Value")

    # Control lines with SHORT labels so the legend fits on one row
    ax.axhline(mean, linestyle="-",  linewidth=1.0, label="Mean")
    ax.axhline(UCL,  linestyle="--", linewidth=1.0, label="UCL 3σ")
    ax.axhline(LCL,  linestyle="--", linewidth=1.0, label="LCL −3σ")

    # OOC red dots (not added to legend to keep it on one line)
    ooc = (y > UCL) | (y < LCL)
    if np.any(ooc):
        ax.scatter(x[ooc], y[ooc], s=18, color="red", zorder=3)

    # Design line (if present)
    if design is not None:
        ax.axhline(design, linestyle="-", linewidth=2.6, color="tab:orange", label="Design")

    ax.set_xlabel(xlab)
    ax.set_ylabel(f"Value [{unit}]" if unit else "Value")

    # Legend: one row, top inside the figure, compact spacing to prevent wrapping
    # Count visible legend entries by reading handles/labels
    handles, labels = ax.get_legend_handles_labels()
    ncols = max(1, len(labels))  # all in one line
    ax.legend(
        handles, labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=ncols,
        frameon=False,
        fontsize=9,
        handlelength=2.2,
        columnspacing=1.0,
        borderaxespad=0.0,
    )

    # Bottom-center parameter label (acts as the "title" without overlapping)
    fig.text(0.35, 0.20, f"{param_name} - History Records", ha="center", fontsize=10, color="tomato")

    # If constrained layout not available, do a careful final tighten only then
    if not using_constrained:
        # Leave room for legend (top) and bottom label
        fig.tight_layout(rect=[0.02, 0.06, 0.98, 0.90])

    return fig

if __name__ == "__main__":
    import argparse, matplotlib.pyplot as plt
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--param", required=True)
    args = ap.parse_args()
    fig = build_ichart_from_history(args.csv, args.param)
    plt.show()
