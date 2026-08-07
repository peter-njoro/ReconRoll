"""ReconRoll recognition pipeline benchmark.

Times each stage of the per-frame hot path (face detection, 128-D
encoding, Euclidean matching) and reports how many faces fit inside the
frontend's 500 ms frame budget. Runs standalone - no Django, no database.

Usage:
    python benchmarks/bench_pipeline.py \
        --images-dir benchmarks/sample_faces \
        --roster-size 50 \
        --faces-per-frame 1,2,4,8 \
        --frames 30

Output is a per-stage latency table plus a per-config throughput table.
"""

import argparse
import json
import os
import time

import cv2
import numpy as np

import bench_common

FRAME_BUDGET_MS = 500


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-dir", required=True,
                        help="Directory of face photos used to build the roster and test frames.")
    parser.add_argument("--roster-size", type=int, default=None,
                        help="Cap on known encodings to match against (default: all images).")
    parser.add_argument("--faces-per-frame", default="1,2,4,8",
                        help="Comma-separated list of faces to paste per test frame.")
    parser.add_argument("--frames", type=int, default=30,
                        help="Frames to process per configuration (after 3-frame warmup).")
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


def stats(values):
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return 0.0, 0.0, 0.0
    return (float(np.mean(values)),
            float(np.percentile(values, 50)),
            float(np.percentile(values, 95)))


def run_config(faces_per_frame, args, known, names, images, dnn_net):
    frame_size = tuple(int(x) for x in args.frame_size.split("x"))
    frames = [
        bench_common.build_test_frame(images, faces_per_frame, frame_size)
        for _ in range(args.frames + 3)
    ]
    detect_ms, encode_ms, match_ms, total_ms = [], [], [], []
    detected_flags = []
    face_counts = []

    for i, frame in enumerate(frames):
        t0 = time.perf_counter()
        t1 = time.perf_counter()
        locs, rgb = bench_common.detect_faces(
            frame, model=args.model, upsample=args.upsample, dnn_net=dnn_net
        )
        detect_ms.append((time.perf_counter() - t1) * 1000)

        t2 = time.perf_counter()
        encs = bench_common.encode_faces(rgb, locs, num_jitters=args.num_jitters)
        encode_ms.append((time.perf_counter() - t2) * 1000)

        match_acc = 0.0
        for enc in encs:
            t3 = time.perf_counter()
            bench_common.match_encoding(enc, known, names, tolerance=args.tolerance)
            match_acc += (time.perf_counter() - t3) * 1000
        match_ms.append(match_acc)

        total_ms.append((time.perf_counter() - t0) * 1000)
        detected_flags.append(bool(locs))
        face_counts.append(len(locs))

    # Drop the 3 warmup frames.
    detect_ms = detect_ms[3:]
    encode_ms = encode_ms[3:]
    match_ms = match_ms[3:]
    total_ms = total_ms[3:]
    detected_flags = detected_flags[3:]
    face_counts = face_counts[3:]

    n = len(total_ms)
    frames_with_faces = sum(detected_flags)
    faces_detected = sum(face_counts)
    avg_total, p50_total, p95_total = stats(total_ms)
    _, p50_detect, p95_detect = stats(detect_ms)
    _, p50_encode, p95_encode = stats(encode_ms)
    _, p50_match, p95_match = stats(match_ms)

    per_face_encode = (np.mean(encode_ms) / faces_detected) if faces_detected else 0.0
    per_face_match = (np.mean(match_ms) / faces_detected) if faces_detected else 0.0

    frames_per_s = 1000.0 / avg_total if avg_total > 0 else 0.0
    faces_per_s = (faces_detected / n) * frames_per_s if n else 0.0
    budget_util = (avg_total / FRAME_BUDGET_MS) * 100 if avg_total else 0.0
    est_max_faces = int(faces_per_frame * FRAME_BUDGET_MS / avg_total) if avg_total else 0

    return {
        "faces_per_frame": faces_per_frame,
        "frames": n,
        "frames_with_faces": frames_with_faces,
        "faces_detected": faces_detected,
        "detect_p50_ms": round(p50_detect, 1),
        "detect_p95_ms": round(p95_detect, 1),
        "encode_p50_ms": round(p50_encode, 1),
        "encode_p95_ms": round(p95_encode, 1),
        "match_p50_ms": round(p50_match, 2),
        "match_p95_ms": round(p95_match, 2),
        "encode_per_face_ms": round(per_face_encode, 1),
        "match_per_face_ms": round(per_face_match, 3),
        "total_avg_ms": round(avg_total, 1),
        "total_p50_ms": round(p50_total, 1),
        "total_p95_ms": round(p95_total, 1),
        "frames_per_s": round(frames_per_s, 2),
        "faces_per_s": round(faces_per_s, 2),
        "budget_utilization_pct": round(budget_util, 1),
        "est_max_faces_in_budget": est_max_faces,
    }


def main():
    args = parse_args()
    if not (os.path.isdir(args.images_dir)):
        raise SystemExit(f"Images directory not found: {args.images_dir}")

    dnn_net = build_dnn_net(args) if args.model == "dnn" else None

    print("Building known encodings from roster images ...")
    known, names, enroll_times = bench_common.load_known_encodings(
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

    enroll_avg, enroll_p50, enroll_p95 = stats(enroll_times)

    print("=" * 74)
    print("ReconRoll pipeline benchmark")
    print("=" * 74)
    print(f"Model: {args.model} | upsample: {args.upsample} | jitters: {args.num_jitters}")
    print(f"Tolerance: {args.tolerance} | frame: {args.frame_size}")
    print(f"Roster encodings: {known.shape[0]} | source images: {len(images)}")
    print(f"Enrollment detect+encode: avg {enroll_avg:.0f} ms/image "
          f"(p50 {enroll_p50:.0f}, p95 {enroll_p95:.0f})")
    print(f"CPU cores: {os.cpu_count()} | Frame budget: {FRAME_BUDGET_MS} ms")
    print("-" * 74)

    results = []
    for raw in args.faces_per_frame.split(","):
        faces = int(raw.strip())
        row = run_config(faces, args, known, names, images, dnn_net)
        results.append(row)
        print(f"Faces/frame: {row['faces_per_frame']}")
        print(f"  Frames: {row['frames']} | with faces: {row['frames_with_faces']} | "
              f"faces detected: {row['faces_detected']}")
        print(f"  Detect    p50 {row['detect_p50_ms']:>7.1f} ms | p95 {row['detect_p95_ms']:>7.1f} ms")
        print(f"  Encode    p50 {row['encode_p50_ms']:>7.1f} ms | p95 {row['encode_p95_ms']:>7.1f} ms "
              f"({row['encode_per_face_ms']} ms/face)")
        print(f"  Match     p50 {row['match_p50_ms']:>7.2f} ms | p95 {row['match_p95_ms']:>7.2f} ms "
              f"({row['match_per_face_ms']} ms/face)")
        print(f"  Total     avg {row['total_avg_ms']:>7.1f} ms | p50 {row['total_p50_ms']:>7.1f} | "
              f"p95 {row['total_p95_ms']:>7.1f} ms")
        print(f"  Throughput: {row['faces_per_s']} faces/s | {row['frames_per_s']} frames/s")
        print(f"  Budget: {row['budget_utilization_pct']}% of 500 ms | "
              f"est. max faces/frame within budget: {row['est_max_faces_in_budget']}")
        print("-" * 74)

    print("\nSummary (per config)")
    print(f"{'faces/frame':>12} {'total avg ms':>12} {'faces/s':>8} {'frames/s':>8} "
          f"{'budget %':>9} {'est max':>8}")
    for row in results:
        print(f"{row['faces_per_frame']:>12} {row['total_avg_ms']:>12.1f} "
              f"{row['faces_per_s']:>8.2f} {row['frames_per_s']:>8.2f} "
              f"{row['budget_utilization_pct']:>9.1f} {row['est_max_faces_in_budget']:>8}")

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"\nResults written to {args.json_out}")


if __name__ == "__main__":
    main()
