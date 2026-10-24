"""
ARO Studio Worker — Environment Doctor
Performs environment, hardware, FFmpeg, and capability diagnosis against project specifications.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_semver(v_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse '4.4.0' or '4.4' into (major, minor, patch)."""
    if not v_str or not isinstance(v_str, str):
        return None
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", v_str.strip())
    if not m:
        return None
    try:
        major = int(m.group(1))
        minor = int(m.group(2))
        patch = int(m.group(3)) if m.group(3) is not None else 0
        return (major, minor, patch)
    except (ValueError, TypeError):
        return None


def parse_ffmpeg_version(version_line: str) -> Optional[Tuple[int, int, int]]:
    """
    Extract (major, minor, patch) from FFmpeg -version output.
    Supports versions with distro suffixes and metadata, e.g.:
      'ffmpeg version 4.4.2-0ubuntu0.22.04.1+esm17 Copyright ...' -> (4, 4, 2)
      'ffmpeg version 6.1.1-1ubuntu1 ...' -> (6, 1, 1)
      'ffmpeg version 7.1 ...' -> (7, 1, 0)
      'ffmpeg version 4.4 ...' -> (4, 4, 0)
    Returns None if unparseable, malformed, or missing.
    """
    if not version_line or not isinstance(version_line, str):
        return None
    # Match ffmpeg version X.Y[.Z] followed by optional distro/build suffix
    m = re.search(r"ffmpeg version\s+(\d+)\.(\d+)(?:\.(\d+))?(?:[^\s]*)", version_line, re.IGNORECASE)
    if not m:
        return None
    try:
        major = int(m.group(1))
        minor = int(m.group(2))
        patch = int(m.group(3)) if m.group(3) is not None else 0
        return (major, minor, patch)
    except (ValueError, TypeError):
        return None


def load_ffmpeg_specification() -> Dict[str, Any]:
    """Load project requirements from locks/ffmpeg-manifest.json."""
    manifest_paths = [
        Path("locks/ffmpeg-manifest.json"),
        Path("../locks/ffmpeg-manifest.json"),
        Path(__file__).resolve().parent.parent.parent.parent.parent / "locks" / "ffmpeg-manifest.json",
    ]
    for p in manifest_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    spec = data.get("specification")
                    if isinstance(spec, dict):
                        return spec
            except Exception:
                pass
    return {}


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


def check_ffmpeg_binaries(
    ffmpeg_cmd: Optional[str] = None,
    ffprobe_cmd: Optional[str] = None,
    spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Check availability, execution return codes, and version compliance of ffmpeg and ffprobe.
    Compares detected version against locks/ffmpeg-manifest.json specification.min_version.
    Invalid or unparseable versions explicitly FAIL.
    Missing, empty, or invalid specification.min_version explicitly FAIL with actionable_reason.
    """
    ffmpeg_bin = ffmpeg_cmd or shutil.which("ffmpeg")
    ffprobe_bin = ffprobe_cmd or shutil.which("ffprobe")

    if not ffmpeg_bin:
        return {
            "name": "ffmpeg_binaries",
            "category": "media",
            "status": "FAIL",
            "ffmpeg_path": None,
            "ffprobe_path": None,
            "version": None,
            "detail": "ffmpeg binary not found in PATH",
            "actionable_reason": "Install FFmpeg using 'sudo apt install ffmpeg' or ensure ffmpeg/ffprobe are in PATH.",
        }

    # Verify ffmpeg execution and return code
    try:
        res_ffmpeg = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True, timeout=5)
        if res_ffmpeg.returncode != 0:
            return {
                "name": "ffmpeg_binaries",
                "category": "media",
                "status": "FAIL",
                "detail": f"ffmpeg -version returned non-zero exit code: {res_ffmpeg.returncode}",
                "actionable_reason": f"ffmpeg command failed with stderr: {res_ffmpeg.stderr.strip()}",
            }
        first_line = res_ffmpeg.stdout.splitlines()[0] if res_ffmpeg.stdout else ""
    except Exception as exc:
        return {
            "name": "ffmpeg_binaries",
            "category": "media",
            "status": "FAIL",
            "detail": str(exc),
            "actionable_reason": f"Error executing ffmpeg: {exc}",
        }

    # Specification min_version verification
    spec_data = spec if spec is not None else load_ffmpeg_specification()
    min_version_raw = spec_data.get("min_version")
    if min_version_raw is None or not isinstance(min_version_raw, str) or not min_version_raw.strip():
        return {
            "name": "ffmpeg_binaries",
            "category": "media",
            "status": "FAIL",
            "ffmpeg_path": ffmpeg_bin,
            "ffprobe_path": ffprobe_bin,
            "version_line": first_line,
            "detail": "Missing required 'min_version' field in FFmpeg specification.",
            "actionable_reason": "Define a valid 'min_version' (e.g. '4.4.0') in locks/ffmpeg-manifest.json specification.",
        }

    min_version_str = min_version_raw.strip()
    min_version_tuple = parse_semver(min_version_str)
    if min_version_tuple is None:
        return {
            "name": "ffmpeg_binaries",
            "category": "media",
            "status": "FAIL",
            "ffmpeg_path": ffmpeg_bin,
            "ffprobe_path": ffprobe_bin,
            "version_line": first_line,
            "min_version": min_version_str,
            "detail": f"Invalid 'min_version' format in FFmpeg specification: '{min_version_str}'.",
            "actionable_reason": f"Correct 'min_version' format in locks/ffmpeg-manifest.json to semver 'X.Y[.Z]' (got '{min_version_str}').",
        }

    # Parse detected version from ffmpeg output
    detected_version = parse_ffmpeg_version(first_line)
    if detected_version is None:
        return {
            "name": "ffmpeg_binaries",
            "category": "media",
            "status": "FAIL",
            "ffmpeg_path": ffmpeg_bin,
            "ffprobe_path": ffprobe_bin,
            "version_line": first_line,
            "min_version": min_version_str,
            "detail": f"Could not parse FFmpeg version from output: '{first_line}'",
            "actionable_reason": f"Invalid or unparseable FFmpeg version format. Expected 'ffmpeg version X.Y[.Z]', got '{first_line}'.",
        }

    detected_version_str = f"{detected_version[0]}.{detected_version[1]}.{detected_version[2]}"
    if detected_version < min_version_tuple:
        return {
            "name": "ffmpeg_binaries",
            "category": "media",
            "status": "FAIL",
            "ffmpeg_path": ffmpeg_bin,
            "ffprobe_path": ffprobe_bin,
            "version_line": first_line,
            "detected_version": detected_version_str,
            "min_version": min_version_str,
            "detail": f"Detected FFmpeg version {detected_version_str} is below required minimum {min_version_str}.",
            "actionable_reason": f"Upgrade FFmpeg to at least version {min_version_str} (recommended: {spec_data.get('recommended_version', '7.1.1')}).",
        }

    # Verify ffprobe execution and return code
    if not ffprobe_bin:
        return {
            "name": "ffmpeg_binaries",
            "category": "media",
            "status": "FAIL",
            "ffmpeg_path": ffmpeg_bin,
            "ffprobe_path": None,
            "version": first_line,
            "detected_version": detected_version_str,
            "min_version": min_version_str,
            "detail": "ffprobe binary not found in PATH (ffmpeg is present).",
            "actionable_reason": "Install ffprobe (part of ffmpeg package) to inspect media streams.",
        }

    try:
        res_ffprobe = subprocess.run([ffprobe_bin, "-version"], capture_output=True, text=True, timeout=5)
        if res_ffprobe.returncode != 0:
            return {
                "name": "ffmpeg_binaries",
                "category": "media",
                "status": "FAIL",
                "detail": f"ffprobe -version returned non-zero exit code: {res_ffprobe.returncode}",
                "actionable_reason": f"ffprobe command failed with stderr: {res_ffprobe.stderr.strip()}",
            }
    except Exception as exc:
        return {
            "name": "ffmpeg_binaries",
            "category": "media",
            "status": "FAIL",
            "detail": str(exc),
            "actionable_reason": f"Error executing ffprobe: {exc}",
        }

    return {
        "name": "ffmpeg_binaries",
        "category": "media",
        "status": "PASS",
        "ffmpeg_path": ffmpeg_bin,
        "ffprobe_path": ffprobe_bin,
        "version_line": first_line,
        "detected_version": detected_version_str,
        "min_version": min_version_str,
        "detail": f"{first_line} (Version {detected_version_str} >= minimum {min_version_str})",
        "actionable_reason": None,
    }


def check_ffmpeg_capabilities(
    ffmpeg_cmd: Optional[str] = None, spec: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compare actual host FFmpeg filters, encoders, and decoders against project specification.
    Verifies command execution return codes.
    """
    ffmpeg_bin = ffmpeg_cmd or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return {
            "name": "ffmpeg_capabilities",
            "category": "media",
            "status": "BLOCKED",
            "detail": "FFmpeg not available",
            "actionable_reason": "Install FFmpeg before verifying capabilities against specification.",
        }

    spec = spec if spec is not None else load_ffmpeg_specification()
    required_filters = spec.get("required_filters", [])
    required_video_encoders = spec.get("required_video_encoders", [])
    required_audio_encoders = spec.get("required_audio_encoders", [])
    required_audio_decoders = spec.get("required_audio_decoders", [])

    missing_items: List[str] = []

    # 1. Check Filters
    try:
        res_filters = subprocess.run([ffmpeg_bin, "-filters"], capture_output=True, text=True, timeout=5)
        if res_filters.returncode != 0:
            return {
                "name": "ffmpeg_capabilities",
                "category": "media",
                "status": "FAIL",
                "detail": f"ffmpeg -filters returned exit code {res_filters.returncode}",
                "actionable_reason": f"Failed to inspect FFmpeg filters: exit code {res_filters.returncode}.",
            }
        filters_output = res_filters.stdout + res_filters.stderr
        for flt in required_filters:
            if flt not in filters_output:
                missing_items.append(f"filter:{flt}")
    except Exception as exc:
        return {
            "name": "ffmpeg_capabilities",
            "category": "media",
            "status": "FAIL",
            "detail": str(exc),
            "actionable_reason": f"Error running ffmpeg -filters: {exc}",
        }

    # 2. Check Encoders
    try:
        res_enc = subprocess.run([ffmpeg_bin, "-encoders"], capture_output=True, text=True, timeout=5)
        if res_enc.returncode != 0:
            return {
                "name": "ffmpeg_capabilities",
                "category": "media",
                "status": "FAIL",
                "detail": f"ffmpeg -encoders returned exit code {res_enc.returncode}",
                "actionable_reason": f"Failed to inspect FFmpeg encoders: exit code {res_enc.returncode}.",
            }
        encoders_output = res_enc.stdout + res_enc.stderr
        for enc in required_video_encoders + required_audio_encoders:
            if enc not in encoders_output:
                missing_items.append(f"encoder:{enc}")
    except Exception as exc:
        return {
            "name": "ffmpeg_capabilities",
            "category": "media",
            "status": "FAIL",
            "detail": str(exc),
            "actionable_reason": f"Error running ffmpeg -encoders: {exc}",
        }

    # 3. Check Decoders
    try:
        res_dec = subprocess.run([ffmpeg_bin, "-decoders"], capture_output=True, text=True, timeout=5)
        if res_dec.returncode != 0:
            return {
                "name": "ffmpeg_capabilities",
                "category": "media",
                "status": "FAIL",
                "detail": f"ffmpeg -decoders returned exit code {res_dec.returncode}",
                "actionable_reason": f"Failed to inspect FFmpeg decoders: exit code {res_dec.returncode}.",
            }
        decoders_output = res_dec.stdout + res_dec.stderr
        for dec in required_audio_decoders:
            if dec not in decoders_output:
                missing_items.append(f"decoder:{dec}")
    except Exception as exc:
        return {
            "name": "ffmpeg_capabilities",
            "category": "media",
            "status": "FAIL",
            "detail": str(exc),
            "actionable_reason": f"Error running ffmpeg -decoders: {exc}",
        }

    if not missing_items:
        return {
            "name": "ffmpeg_capabilities",
            "category": "media",
            "status": "PASS",
            "verified_filters": required_filters,
            "verified_encoders": required_video_encoders + required_audio_encoders,
            "verified_decoders": required_audio_decoders,
            "detail": "Host FFmpeg satisfies all project requirements (filters, encoders, decoders).",
            "actionable_reason": None,
        }
    else:
        return {
            "name": "ffmpeg_capabilities",
            "category": "media",
            "status": "FAIL",
            "missing_items": missing_items,
            "detail": f"Host FFmpeg is missing required capabilities: {', '.join(missing_items)}",
            "actionable_reason": f"Missing components: {', '.join(missing_items)}. Recompile or install an FFmpeg build with libass and libx264 enabled.",
        }


def check_gpu() -> Dict[str, Any]:
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
        res = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
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
        check_ffmpeg_binaries(),
        check_ffmpeg_capabilities(),
        check_gpu(),
    ]

    has_fail = any(c["status"] == "FAIL" for c in checks)
    has_blocked = any(c["status"] == "BLOCKED" for c in checks)

    overall_status = "FAILED" if has_fail else ("DEGRADED" if has_blocked else "READY")

    # In Task A01, ONLY baseline CLI and doctor are implemented.
    # We DO NOT claim audio_extract_cpu, ffmpeg_loudnorm_cpu, or any unbuilt media logic.
    supported_features: List[str] = []
    if not has_fail:
        supported_features.extend(["cli", "doctor"])

    blocked_reasons: Dict[str, str] = {}

    # Hardware status
    gpu_check = next((c for c in checks if c["name"] == "cuda_gpu"), None)
    if gpu_check and gpu_check.get("cuda_available"):
        supported_features.append("cuda_acceleration")
    else:
        blocked_reasons["cuda_acceleration"] = "NVIDIA CUDA GPU not detected; running in CPU fallback mode."
        blocked_reasons["uvr_separation"] = "UVR vocal separation requires CUDA GPU; duck_original mode will be used."

    # Stage capabilities explicitly marked as pending implementation per taskbook
    blocked_reasons["contracts_v1"] = "Scheduled for implementation in Task A02 (Contracts and shared fixtures)."
    blocked_reasons["drive_adapter"] = "Scheduled for implementation in Task A03 (Drive storage adapter thực)."
    blocked_reasons["jobs_fencing"] = "Scheduled for implementation in Task A04 (Controller, jobs và fencing)."
    blocked_reasons["audio_extract_cpu"] = "Scheduled for implementation in Task A06 (FFmpeg wrapper, probe và audio extract)."
    blocked_reasons["ocr_hardsub"] = "Scheduled for implementation in Task A08 (OCR hardsub adapter)."
    blocked_reasons["asr_whisper"] = "Scheduled for implementation in Task A09 (ASR chunking, VAD và merge)."
    blocked_reasons["translation_engine"] = "Scheduled for implementation in Task A10/A11 (Memory/glossary & Gemini handoff)."
    blocked_reasons["tts_engine"] = "Scheduled for implementation in Task A12 (VieNeu và Edge TTS adapters)."
    blocked_reasons["ffmpeg_loudnorm_cpu"] = "Scheduled for implementation in Task A15 (Voice timeline, ducking và loudnorm)."
    blocked_reasons["render_pipeline"] = "Scheduled for implementation in Task A16 (ASS và video render)."

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
            print(f"  {status_tag:<8} {c['name']:<22}: {c['detail']}")
            if c.get("actionable_reason") and c["status"] != "PASS":
                print(f"           -> Note: {c['actionable_reason']}")

        print("\nSupported Features (A01 Baseline):")
        for sf in report["supported_features"]:
            print(f"  + {sf}")

        print("\nBlocked / Pending Tasks (A02–A28 Roadmap):")
        for feat, reason in report["blocked_reasons"].items():
            print(f"  - {feat:<22}: {reason}")

    if check_mode and report["overall_status"] == "FAILED":
        return 1
    return 0
