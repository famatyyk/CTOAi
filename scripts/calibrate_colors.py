"""Interactive HP/MP bar color calibration tool.

Usage (with Tibia running):
    python scripts/calibrate_colors.py --screenshot
    python scripts/calibrate_colors.py --sample --x 120 --y 5   # HP bar pixel
    python scripts/calibrate_colors.py --verify

The tool reads a screenshot from the Tibia window (or a provided image file)
and extracts the dominant BGR colour in the specified pixel region.
Results are printed as env-var overrides you can put in .env.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


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


def cmd_screenshot(args):
    cv2 = _require_cv2()
    np = _require_numpy()
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from bot.perception.window import find_tibia_window, capture_window

    handle = find_tibia_window()
    if handle is None:
        print("WARN: Tibia window not found — capturing primary screen instead.")
    frame = capture_window(handle)
    if frame is None:
        print("ERROR: Could not capture screen. Install mss: pip install mss")
        sys.exit(1)
    out = args.output or "calibration_screenshot.png"
    cv2.imwrite(out, frame)
    print(f"Screenshot saved → {out}")
    print(f"Window size: {frame.shape[1]}x{frame.shape[0]}")
    print("Next: open the image and note pixel coordinates of HP/MP bars.")


def cmd_sample(args):
    cv2 = _require_cv2()
    np = _require_numpy()
    img_path = args.image or "calibration_screenshot.png"
    if not Path(img_path).exists():
        print(f"ERROR: {img_path} not found. Run --screenshot first.")
        sys.exit(1)
    frame = cv2.imread(img_path)
    x, y = args.x, args.y
    w, h = args.width, args.height
    roi = frame[y:y+h, x:x+w]
    mean_bgr = roi.mean(axis=(0, 1))
    print(f"Region ({x},{y},{w},{h})  mean BGR: {mean_bgr.astype(int).tolist()}")
    print(f"  B={mean_bgr[0]:.0f}  G={mean_bgr[1]:.0f}  R={mean_bgr[2]:.0f}")

    # Check if it looks like HP (red) or MP (blue)
    b, g, r = mean_bgr
    if r > 150 and r > b * 1.5:
        bar_type = "HP (red)"
        env_key = "HP_BAR_BGR"
    elif b > 150 and b > r * 1.5:
        bar_type = "MP (blue)"
        env_key = "MP_BAR_BGR"
    else:
        bar_type = "unknown"
        env_key = "UNKNOWN_BGR"

    print(f"  Detected: {bar_type}")
    print(f"\nAdd to .env:")
    print(f"  {env_key}={int(b)},{int(g)},{int(r)}")
    print(f"  OTS_HP_BAR_REGION={x},{y},{x+w},{y+h}")

    results = {"x": x, "y": y, "w": w, "h": h,
               "mean_bgr": mean_bgr.tolist(), "bar_type": bar_type}
    Path("calibration_results.json").write_text(json.dumps(results, indent=2))
    print("\nSaved → calibration_results.json")


def cmd_verify(args):
    cv2 = _require_cv2()
    results_path = Path("calibration_results.json")
    if not results_path.exists():
        print("No calibration_results.json found. Run --sample first.")
        sys.exit(1)
    data = json.loads(results_path.read_text())
    print("Saved calibration:")
    print(json.dumps(data, indent=2))

    img_path = args.image or "calibration_screenshot.png"
    if Path(img_path).exists():
        frame = cv2.imread(img_path)
        x, y, w, h = data["x"], data["y"], data["w"], data["h"]
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        out = "calibration_verify.png"
        cv2.imwrite(out, frame)
        print(f"Annotated image saved → {out}")


def main():
    ap = argparse.ArgumentParser(description="Tibia HP/MP bar color calibration")
    sub = ap.add_subparsers(dest="cmd")

    sc = sub.add_parser("screenshot", help="Capture Tibia window")
    sc.add_argument("--output", default="calibration_screenshot.png")

    sa = sub.add_parser("sample", help="Sample colour at region")
    sa.add_argument("--image", default="calibration_screenshot.png")
    sa.add_argument("--x", type=int, required=True)
    sa.add_argument("--y", type=int, required=True)
    sa.add_argument("--width", type=int, default=140)
    sa.add_argument("--height", type=int, default=10)

    ve = sub.add_parser("verify", help="Verify saved calibration")
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
