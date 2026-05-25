"""Interactive HP/MP bar color calibration tool.

Usage (with Tibia running):
    python scripts/calibrate_colors.py screenshot
    python scripts/calibrate_colors.py sample --x 662 --y 38 --width 92 --height 6
    python scripts/calibrate_colors.py verify

Results are saved to calibration_config.json (loaded automatically by parser.py).
Env var overrides (highest priority):
    HP_BAR_BGR=B,G,R          e.g. HP_BAR_BGR=0,0,192
    MP_BAR_BGR=B,G,R          e.g. MP_BAR_BGR=192,0,0
    OTS_HP_BAR_REGION=x,y,w,h
    OTS_MP_BAR_REGION=x,y,w,h
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

_CALIB_FILE = Path("calibration_config.json")


def _require_cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        print("ERROR: opencv-python not installed. Run: pip install opencv-python")
        sys.exit(1)


def _require_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        print("ERROR: numpy not installed.")
        sys.exit(1)


def _load_config() -> dict:
    if _CALIB_FILE.exists():
        try:
            return json.loads(_CALIB_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(data: dict) -> None:
    _CALIB_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved -> {_CALIB_FILE}")


def cmd_screenshot(args):
    cv2 = _require_cv2()
    _require_numpy()
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from bot.perception.window import find_tibia_window, capture_window
    handle = find_tibia_window()
    if handle is None:
        print("WARN: Tibia window not found -- capturing primary screen instead.")
    frame = capture_window(handle)
    if frame is None:
        print("ERROR: Could not capture screen. Install mss: pip install mss")
        sys.exit(1)
    out = args.output or "calibration_screenshot.png"
    cv2.imwrite(out, frame)
    print(f"Screenshot saved -> {out}")
    print(f"Window size: {frame.shape[1]}x{frame.shape[0]}")
    print("Next: open the image, note coordinates, then run:")
    print("  python scripts/calibrate_colors.py sample --x X --y Y --width W --height H")


def cmd_sample(args):
    cv2 = _require_cv2()
    np = _require_numpy()
    img_path = args.image or "calibration_screenshot.png"
    if not Path(img_path).exists():
        print(f"ERROR: {img_path} not found. Run screenshot first.")
        sys.exit(1)
    frame = cv2.imread(img_path)
    x, y = args.x, args.y
    w, h = args.width, args.height
    roi = frame[y:y+h, x:x+w]
    mean_bgr = roi.mean(axis=(0, 1))
    b, g, r  = float(mean_bgr[0]), float(mean_bgr[1]), float(mean_bgr[2])
    print(f"Region ({x},{y} {w}x{h})  mean BGR: B={b:.0f} G={g:.0f} R={r:.0f}")

    # Auto-detect HP (red) vs MP (blue)
    if r > 100 and r > b * 1.5:
        bar_key  = "hp"
        env_key  = "HP_BAR_BGR"
        reg_key  = "OTS_HP_BAR_REGION"
    elif b > 100 and b > r * 1.5:
        bar_key  = "mp"
        env_key  = "MP_BAR_BGR"
        reg_key  = "OTS_MP_BAR_REGION"
    else:
        bar_key = args.bar or "hp"
        env_key = "HP_BAR_BGR" if bar_key == "hp" else "MP_BAR_BGR"
        reg_key = "OTS_HP_BAR_REGION" if bar_key == "hp" else "OTS_MP_BAR_REGION"
        print(f"  Auto-detect uncertain -- using --bar={bar_key}")

    print(f"  Detected: {bar_key.upper()} bar")
    print(f"\nAdd to .env (or set env vars):")
    print(f"  {env_key}={int(b)},{int(g)},{int(r)}")
    print(f"  {reg_key}={x},{y},{w},{h}")

    # Merge into calibration_config.json
    config = _load_config()
    config[bar_key] = {
        "mean_bgr": [int(b), int(g), int(r)],
        "region": [x, y, w, h],
    }
    # Store regions separately for direct use by parser
    config[f"{bar_key}_region"] = [x, y, w, h]
    _save_config(config)

    print(f"\nTo reload at runtime call: bot.perception.parser.reload_calibration()")


def cmd_verify(args):
    cv2 = _require_cv2()
    if not _CALIB_FILE.exists():
        print("No calibration_config.json found. Run sample first.")
        sys.exit(1)
    data = json.loads(_CALIB_FILE.read_text(encoding="utf-8"))
    print("Current calibration:")
    print(json.dumps(data, indent=2))

    img_path = args.image or "calibration_screenshot.png"
    if Path(img_path).exists():
        frame = cv2.imread(img_path)
        for bar_key, colour in (("hp", (0, 0, 255)), ("mp", (255, 0, 0))):
            if bar_key in data:
                x, y, w, h = data[bar_key]["region"]
                cv2.rectangle(frame, (x, y), (x+w, y+h), colour, 2)
                cv2.putText(frame, bar_key.upper(), (x, y - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1)
        out = "calibration_verify.png"
        cv2.imwrite(out, frame)
        print(f"Annotated image saved -> {out}")
    print("\nCalibration OK. parser.py will use these values on next import.")


def main():
    ap = argparse.ArgumentParser(description="Tibia HP/MP bar color calibration")
    sub = ap.add_subparsers(dest="cmd")

    sc = sub.add_parser("screenshot", help="Capture Tibia window to PNG")
    sc.add_argument("--output", default="calibration_screenshot.png")

    sa = sub.add_parser("sample", help="Sample colour at region and save to config")
    sa.add_argument("--image",  default="calibration_screenshot.png")
    sa.add_argument("--x",      type=int, required=True)
    sa.add_argument("--y",      type=int, required=True)
    sa.add_argument("--width",  type=int, default=92)
    sa.add_argument("--height", type=int, default=6)
    sa.add_argument("--bar",    choices=["hp", "mp"], default=None,
                    help="Override auto-detect (hp or mp)")

    ve = sub.add_parser("verify", help="Show and annotate saved calibration")
    ve.add_argument("--image", default="calibration_screenshot.png")

    args = ap.parse_args()
    if args.cmd == "screenshot":
        cmd_screenshot(args)
    elif args.cmd == "sample":
        cmd_sample(args)
    elif args.cmd == "verify":
        cmd_verify(args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
