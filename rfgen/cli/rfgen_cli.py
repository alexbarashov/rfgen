import argparse, json
from pathlib import Path
from ..core.wave_engine import build_iq
from ..backends.fileout import FileOutBackend
from ..utils.paths import out_dir as default_out_dir

def main():
    ap = argparse.ArgumentParser(description="rfgen CLI")
    ap.add_argument("--fs", type=int, default=2_000_000)
    ap.add_argument("--mod", choices=["None","AM","FM","PM"], default="FM")
    ap.add_argument("--dev", type=float, default=5000.0, help="FM deviation (Hz)")
    ap.add_argument("--pm_index", type=float, default=1.0)
    ap.add_argument("--am_depth", type=float, default=0.5)
    ap.add_argument("--pattern", choices=["Tone","Sweep","Noise","FF00","F0F0","3333","5555"], default="Tone")
    ap.add_argument("--tone", type=float, default=1000.0)
    ap.add_argument("--outdir", type=str, default=None, help="Output directory (default: rfgen/out/)")
    ap.add_argument("--name", type=str, default="quick_tx_frame")
    args = ap.parse_args()

    prof = {
        "standard": "generic",
        "modulation": {
            "type": args.mod,
            "deviation_hz": args.dev,
            "pm_index": args.pm_index,
            "am_depth": args.am_depth,
        },
        "pattern": {"type": args.pattern, "tone_hz": args.tone, "bitrate_bps": 9600},
        "schedule": {"mode": "loop", "gap_s": 0.0, "repeat": 1},
        "device": {"backend": "fileout", "fs_tx": args.fs, "tx_gain_db": 30, "pa": False,
                   "target_hz": 0, "if_offset_hz": 0, "freq_corr_hz": 0}
    }

    iq = build_iq(prof, frame_s=1.0)
    outdir = Path(args.outdir) if args.outdir else default_out_dir()
    backend = FileOutBackend(outdir)
    path = backend.write_cf32(args.name, iq)
    print(json.dumps({"saved": str(path), "fs": args.fs}, ensure_ascii=False))
