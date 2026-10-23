"""
ARO Studio Worker — Environment Doctor
Performs environment, hardware, FFmpeg, and capability diagnosis.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List


def check_python() -> Dict[str, Any]:
    ver = sys.version_info
    version_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    passed = ver.major == 3 and ver.minor >= 10
    return {
        "name": "python_version",
        "category": "runtime",
        "status": "PASS" if passed else "FAIL",
        "version": version_str,
        "executable": sys.executable,
        "detail": f"Python {version_str} on {platform.system()} {platform.machine()}",
        "actionable_reason": None if passed else "Python >= 3.10 is required (Python 3.11 recommended).",
    }


def check_disk_space(path: str = ".") -> Dict[str, Any]:
    try:
        total, used, free = shutil.disk_usage(path)
        free_gb = round(free / (1024**3), 2)
        passed = free_gb >= 1.0  # at least 1 GB free for basic scratch operations
        return {
            "name": "disk_space",
            "category": "storage",
            "status": "PASS" if passed else "FAIL",
            "free_gb": free_gb,
            "total_gb": round(total / (1024**3), 2),
            "detail": f"{free_gb} GB free on {os.path.abspath(path)}",
            "actionable_reason": None if passed else f"Insufficient disk space: {free_gb} GB available, at least 1.0 GB required.",
        }
    except Exception as exc:
        return {
            "name": "disk_space",
            "category": "storage",
            "status": "FAIL",
            "detail": str(exc),
            "actionable_reason": f"Failed to check disk usage: {exc}",
        }


def check_ffmpeg() -> Dict[str, Any]:
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")

    if not ffmpeg_bin:
        return {
            "name": "ffmpeg_binary",
            "category": "media",
            "status": "FAIL",
            "path": None,
            "version": None,
            "detail": "ffmpeg binary not found in PATH",
            "actionable_reason": "Install FFmpeg using 'sudo apt install ffmpeg' or install static binary.",
        }

    try:
        res = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True, timeout=5)
        first_line = res.stdout.splitlines()[0] if res.stdout else "unknown"
        has_ffprobe = ffprobe_bin is not None
        status = "PASS" if has_ffprobe else "FAIL"
        reason = None if has_ffprobe else "ffprobe binary not found in PATH."
        return {
            "name": "ffmpeg_binary",
            "category": "media",
            "status": status,
            "ffmpeg_path": ffmpeg_bin,
            "ffprobe_path": ffprobe_bin,
            "version_line": first_line,
            "detail": first_line,
            "actionable_reason": reason,
        }
    except Exception as exc:
        return {
            "name": "ffmpeg_binary",
            "category": "media",
            "status": "FAIL",
            "detail": str(exc),
            "actionable_reason": f"Error executing ffmpeg: {exc}",
        }


def check_ffmpeg_filters() -> Dict[str, Any]:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return {
            "name": "ffmpeg_filters",
            "category": "media",
            "status": "BLOCKED",
            "detail": "FFmpeg not available",
            "actionable_reason": "Install FFmpeg before verifying audio/video filters.",
        }

    try:
        res = subprocess.run([ffmpeg_bin, "-filters"], capture_output=True, text=True, timeout=5)
        filters_output = res.stdout + res.stderr
        required_filters = ["loudnorm", "sidechaincompress", "ass", "subtitles"]
        missing = [f for f in required_filters if f not in filters_output]

        if not missing:
            return {
                "name": "ffmpeg_filters",
                "category": "media",
                "status": "PASS",
                "verified_filters": required_filters,
                "detail": "All required filters (loudnorm, sidechaincompress, ass, subtitles) verified.",
                "actionable_reason": None,
            }
        else:
            return {
                "name": "ffmpeg_filters",
                "category": "media",
                "status": "FAIL",
                "missing_filters": missing,
                "detail": f"Missing required FFmpeg filters: {', '.join(missing)}",
                "actionable_reason": f"FFmpeg build is missing: {', '.join(missing)}. Recompile FFmpeg with --enable-libass.",
            }
    except Exception as exc:
        return {
            "name": "ffmpeg_filters",
            "category": "media",
            "status": "FAIL",
            "detail": str(exc),
            "actionable_reason": f"Failed to inspect FFmpeg filters: {exc}",
        }


def check_gpu() -> Dict[str, Any]:
    # Check nvidia-smi
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {
            "name": "cuda_gpu",
            "category": "hardware",
            "status": "BLOCKED",
            "cuda_available": False,
            "device": "cpu",
            "detail": "No NVIDIA GPU (nvidia-smi not found). Running on CPU host.",
            "actionable_reason": "GPU acceleration disabled. CPU fallback will be used for ASR/OCR/TTS.",
        }

    try:
        res = subprocess.run([nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            gpu_info = res.stdout.strip().splitlines()[0]
            return {
                "name": "cuda_gpu",
                "category": "hardware",
                "status": "PASS",
                "cuda_available": True,
                "device": "cuda",
                "detail": f"GPU detected: {gpu_info}",
                "actionable_reason": None,
            }
    except Exception:
        pass

    return {
        "name": "cuda_gpu",
        "category": "hardware",
        "status": "BLOCKED",
        "cuda_available": False,
        "device": "cpu",
        "detail": "Failed to query GPU via nvidia-smi. Using CPU profile.",
        "actionable_reason": "GPU not operational. Worker will use CPU mode.",
    }


def diagnose() -> Dict[str, Any]:
    checks = [
        check_python(),
        check_disk_space(),
        check_ffmpeg(),
        check_ffmpeg_filters(),
        check_gpu(),
    ]

    has_fail = any(c["status"] == "FAIL" for c in checks)
    has_blocked = any(c["status"] == "BLOCKED" for c in checks)

    overall_status = "FAILED" if has_fail else ("DEGRADED" if has_blocked else "READY")

    supported_features: List[str] = []
    blocked_reasons: Dict[str, str] = {}

    # Basic baseline CLI and probe
    if not has_fail:
        supported_features.extend(["cli", "doctor", "audio_extract_cpu", "ffmpeg_loudnorm_cpu"])

    # GPU check
    gpu_check = next((c for c in checks if c["name"] == "cuda_gpu"), None)
    if gpu_check and gpu_check.get("cuda_available"):
        supported_features.append("cuda_acceleration")
    else:
        blocked_reasons["cuda_acceleration"] = "NVIDIA CUDA GPU not detected; running in CPU fallback mode."
        blocked_reasons["uvr_separation"] = "UVR vocal separation requires CUDA GPU; duck_original mode will be used."

    # Stage capabilities (to be implemented in subsequent tasks A02 - A18)
    blocked_reasons["contracts_v1"] = "Scheduled for implementation in Task A02."
    blocked_reasons["drive_adapter"] = "Scheduled for implementation in Task A03."
    blocked_reasons["ocr_hardsub"] = "Scheduled for implementation in Task A08."
    blocked_reasons["asr_whisper"] = "Scheduled for implementation in Task A09."
    blocked_reasons["tts_vieneu"] = "Scheduled for implementation in Task A12."
    blocked_reasons["render_pipeline"] = "Scheduled for implementation in Task A16."

    return {
        "schema_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "aro_worker_version": "0.1.0",
        "overall_status": overall_status,
        "checks": checks,
        "supported_features": supported_features,
        "blocked_reasons": blocked_reasons,
    }


def run_doctor(output_json: bool = False, check_mode: bool = False) -> int:
    report = diagnose()

    if output_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"=== ARO Studio Worker Doctor (v{report['aro_worker_version']}) ===")
        print(f"Overall Status: {report['overall_status']}")
        print(f"Timestamp:      {report['timestamp']}\n")
        print("Checks:")
        for c in report["checks"]:
            status_tag = f"[{c['status']}]"
            print(f"  {status_tag:<8} {c['name']:<20}: {c['detail']}")
            if c.get("actionable_reason") and c["status"] != "PASS":
                print(f"           -> Note: {c['actionable_reason']}")

        print("\nSupported Features:")
        for sf in report["supported_features"]:
            print(f"  + {sf}")

        print("\nBlocked / Pending Tasks:")
        for feat, reason in report["blocked_reasons"].items():
            print(f"  - {feat:<20}: {reason}")

    # Return code logic:
    # If check_mode is set, fail if overall_status == "FAILED"
    if check_mode and report["overall_status"] == "FAILED":
        return 1
    return 0
