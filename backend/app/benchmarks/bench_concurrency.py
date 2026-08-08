"""ReconRoll concurrency benchmark.

Simulates the production frame-queue architecture from
app/recognition/recognition_runner.py:
  - N client sessions each push a frame into ONE shared queue
    (default maxsize 30) every 500 ms (2 fps, matching the React frontend);
  - N recognition threads (one per session) drain the queue and run
    detect + encode + match.

For each concurrency level it reports frames dropped (queue full), worker
latency, aggregate throughput, and whether the stack is sustainable, so you
can state how many concurrent sessions the deployment actually supports.

Usage:
    python benchmarks/bench_concurrency.py \
        --images-dir benchmarks/sample_faces \
        --sessions 1,2,4,8 \
        --duration 30
"""

import argparse
import json
import os
import queue
import threading
import time

import cv2
import numpy as np

import bench_common


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-dir", required=True,
                        help="Directory of face photos used to build the roster and test frames.")
    parser.add_argument("--sessions", default="1,2,4,8",
                        help="Comma-separated list of concurrent session counts to test.")
    parser.add_argument("--duration", type=float, default=30,
                        help="Seconds to run each concurrency level.")
    parser.add_argument("--queue-size", type=int, default=30,
                        help="Shared frame queue capacity (production default: 30).")
    parser.add_argument("--frame-interval", type=float, default=0.5,
                        help="Seconds between frames per client (production default: 0.5 = 2 fps).")
    parser.add_argument("--faces-per-frame", type=int, default=1,
                        help="Faces pasted into each synthetic frame.")
    parser.add_argument("--roster-size", type=int, default=None,
                        help="Cap on known encodings to match against (default: all images).")
    parser.add_argument("--model", choices=["hog", "dnn"], default="hog",
                        help="Face detection model (default: hog, matching production).")
    parser.add_argument("--dnn-proto", default=None,
                        help="Path to deploy.prototxt for DNN detection.")
    parser.add_argument("--dnn-weights", default=None,
                        help="Path to res10 caffemodel for DNN detection.")
    parser.add_argument("--upsample", type=int, default=2,
                        help="number_of_times_to_upsample for HOG (production default: 2).")
    parser.add_argument("--num-jitters", type=int, default=1,
                        help="num_jitters for encoding (production default: 1).")
    parser.add_argument("--tolerance", type=float, default=0.55,
                        help="Match distance threshold (production default: 0.55).")
    parser.add_argument("--frame-size", default="640x480",
                        help="Synthetic frame size WxH (default: 640x480).")
    parser.add_argument("--json-out", default=None,
                        help="Optional path to write machine-readable results.")
    return parser.parse_args()


def build_dnn_net(args):
    proto = args.dnn_proto
    weights = args.dnn_weights
    if not proto or not weights:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proto = proto or os.path.join(root, "recognition", "models", "deploy.prototxt")
        weights = weights or os.path.join(
            root, "recognition", "models", "res10_300x300_ssd_iter_140000.caffemodel"
        )
    if not (os.path.exists(proto) and os.path.exists(weights)):
        raise SystemExit(f"DNN model files not found: {proto} / {weights}")
    net = cv2.dnn.readNetFromCaffe(proto, weights)
    try:
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    except Exception:
        pass
    return net


def run_trial(session_count, args, known, names, frame, net_factory):
    q = queue.Queue(maxsize=args.queue_size)
    stop = threading.Event()
    lock = threading.Lock()
    latencies = []
    processed = {"n": 0}
    dropped = {"n": 0}

    def worker():
        # One net per worker, matching production where each recognition
        # thread loads its own DNN model. cv2.dnn.Net.forward() is not
        # thread-safe, so sharing a single net across workers deadlocks.
        net = net_factory()
        while not stop.is_set():
            try:
                f = q.get(timeout=0.05)
            except queue.Empty:
                continue
            t0 = time.perf_counter()
            locs, rgb = bench_common.detect_faces(
                f, model=args.model, upsample=args.upsample, dnn_net=net
            )
            encs = bench_common.encode_faces(rgb, locs, num_jitters=args.num_jitters)
            for enc in encs:
                bench_common.match_encoding(enc, known, names, tolerance=args.tolerance)
            elapsed = (time.perf_counter() - t0) * 1000
            with lock:
                processed["n"] += 1
                latencies.append(elapsed)

    def uploader():
        elapsed = 0.0
        while not stop.is_set():
            time.sleep(0.05)
            elapsed += 0.05
            if elapsed < args.frame_interval:
                continue
            elapsed = 0.0
            if q.full():
                with lock:
                    dropped["n"] += 1
            else:
                q.put_nowait(frame)

    threads = [threading.Thread(target=worker) for _ in range(session_count)]
    threads += [threading.Thread(target=uploader) for _ in range(session_count)]
    for t in threads:
        t.start()

    time.sleep(args.duration)
    stop.set()
    for t in threads:
        t.join(timeout=2)

    offered = processed["n"] + dropped["n"]
    drop_rate = (dropped["n"] / offered * 100) if offered else 0.0
    lat_arr = np.asarray(latencies, dtype=float) if latencies else np.zeros(1)
    avg_ms = float(np.mean(lat_arr))
    p50_ms = float(np.percentile(lat_arr, 50))
    p95_ms = float(np.percentile(lat_arr, 95))
    frames_per_s = processed["n"] / args.duration
    per_session_fps = frames_per_s / session_count if session_count else 0.0
    sustainable = (drop_rate <= 1.0) and (p95_ms < args.frame_interval * 1000)

    return {
        "sessions": session_count,
        "offered": offered,
        "processed": processed["n"],
        "dropped": dropped["n"],
        "drop_rate_pct": round(drop_rate, 2),
        "avg_ms": round(avg_ms, 1),
        "p50_ms": round(p50_ms, 1),
        "p95_ms": round(p95_ms, 1),
        "frames_per_s": round(frames_per_s, 2),
        "per_session_fps": round(per_session_fps, 2),
        "faces_per_s": round(frames_per_s * args.faces_per_frame, 2),
        "sustainable": sustainable,
    }


def main():
    args = parse_args()
    if not os.path.isdir(args.images_dir):
        raise SystemExit(f"Images directory not found: {args.images_dir}")

    dnn_net = build_dnn_net(args) if args.model == "dnn" else None
    del dnn_net

    def net_factory():
        return build_dnn_net(args) if args.model == "dnn" else None

    print("Building known encodings from roster images ...")
    known, names, _ = bench_common.load_known_encodings(
        args.images_dir, limit=args.roster_size, num_jitters=args.num_jitters
    )
    if known.shape[0] == 0:
        raise SystemExit("No faces could be encoded from the images directory.")
    if args.roster_size:
        known = known[: args.roster_size]
        names = names[: args.roster_size]

    image_paths = bench_common.load_face_images(args.images_dir)
    images = [cv2.imread(p) for p in image_paths]
    images = [img for img in images if img is not None]
    if not images:
        raise SystemExit("No decodable images found in the images directory.")

    frame_size = tuple(int(x) for x in args.frame_size.split("x"))
    frame = bench_common.build_test_frame(images, args.faces_per_frame, frame_size)

    print("=" * 74)
    print("ReconRoll concurrency benchmark")
    print("=" * 74)
    print(f"Model: {args.model} | upsample: {args.upsample} | jitters: {args.num_jitters}")
    print(f"Tolerance: {args.tolerance} | frame: {args.frame_size} | faces/frame: {args.faces_per_frame}")
    print(f"Roster encodings: {known.shape[0]}")
    print(f"Queue: {args.queue_size} (shared) | interval: {args.frame_interval}s | "
          f"duration: {args.duration}s per level")
    print(f"CPU cores: {os.cpu_count()}")
    print("-" * 74)

    results = []
    for raw in args.sessions.split(","):
        n = int(raw.strip())
        row = run_trial(n, args, known, names, frame, net_factory)
        results.append(row)
        verdict = "SUSTAINABLE" if row["sustainable"] else "OVERLOADED"
        print(f"Sessions: {row['sessions']}  ->  {verdict}")
        print(f"  Offered: {row['offered']} | processed: {row['processed']} | "
              f"dropped: {row['dropped']} ({row['drop_rate_pct']}%)")
        print(f"  Worker latency: avg {row['avg_ms']} ms | p50 {row['p50_ms']} | "
              f"p95 {row['p95_ms']} ms")
        print(f"  Throughput: {row['frames_per_s']} frames/s total | "
              f"{row['per_session_fps']} frames/s per session | {row['faces_per_s']} faces/s")
        print("-" * 74)

    sustainable_rows = [r for r in results if r["sustainable"]]
    best = sustainable_rows[-1]["sessions"] if sustainable_rows else 0

    print("\nSummary")
    print(f"{'sessions':>8} {'offered':>8} {'processed':>10} {'dropped %':>9} "
          f"{'avg ms':>8} {'p95 ms':>8} {'frames/s':>9} {'verdict':>11}")
    for row in results:
        verdict = "OK" if row["sustainable"] else "OVERLOADED"
        print(f"{row['sessions']:>8} {row['offered']:>8} {row['processed']:>10} "
              f"{row['drop_rate_pct']:>9.2f} {row['avg_ms']:>8.1f} {row['p95_ms']:>8.1f} "
              f"{row['frames_per_s']:>9.2f} {verdict:>11}")
    print(f"\nMax sustainable concurrent sessions on this host: {best}")

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"Results written to {args.json_out}")


if __name__ == "__main__":
    main()
