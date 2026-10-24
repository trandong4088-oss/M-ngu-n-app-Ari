"""
Unit tests for aro doctor environment and capability diagnostics.
"""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

from aro_worker.core import doctor


class TestDoctor(unittest.TestCase):
    def test_diagnose_structure(self):
        report = doctor.diagnose()
        self.assertEqual(report["schema_version"], "1.0")
        self.assertEqual(report["aro_worker_version"], "0.1.0")
        self.assertIn(report["overall_status"], ["READY", "DEGRADED", "FAILED"])
        self.assertIsInstance(report["checks"], list)
        self.assertIsInstance(report["supported_features"], list)
        self.assertIsInstance(report["blocked_reasons"], dict)

    def test_supported_features_strict_a01_boundary(self):
        """
        Verify that A01 doctor only claims 'cli' and 'doctor' as supported.
        Unimplemented stages (audio_extract_cpu, ffmpeg_loudnorm_cpu, etc.) must NOT be claimed.
        """
        report = doctor.diagnose()
        self.assertIn("cli", report["supported_features"])
        self.assertIn("doctor", report["supported_features"])
        self.assertNotIn("audio_extract_cpu", report["supported_features"])
        self.assertNotIn("ffmpeg_loudnorm_cpu", report["supported_features"])
        self.assertNotIn("ocr_hardsub", report["supported_features"])
        self.assertNotIn("asr_whisper", report["supported_features"])

        # They must be in blocked_reasons instead
        self.assertIn("audio_extract_cpu", report["blocked_reasons"])
        self.assertIn("ffmpeg_loudnorm_cpu", report["blocked_reasons"])
        self.assertIn("contracts_v1", report["blocked_reasons"])
        self.assertIn("drive_adapter", report["blocked_reasons"])

    def test_ffmpeg_missing_behavior(self):
        """Test doctor behavior when FFmpeg binary is missing from PATH."""
        with patch("shutil.which", return_value=None):
            result = doctor.check_ffmpeg_binaries()
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("not found in PATH", result["detail"])
            self.assertIsNotNone(result["actionable_reason"])

    def test_ffmpeg_command_failure_return_code(self):
        """Test doctor behavior when ffmpeg -version returns non-zero exit code."""
        mock_proc = MagicMock()
        mock_proc.returncode = 127
        mock_proc.stderr = "Permission denied"
        mock_proc.stdout = ""

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run", return_value=mock_proc):
                result = doctor.check_ffmpeg_binaries(ffmpeg_cmd="/usr/bin/ffmpeg")
                self.assertEqual(result["status"], "FAIL")
                self.assertIn("non-zero exit code: 127", result["detail"])

    def test_ffmpeg_capabilities_missing_filters(self):
        """Test capability check when required filters are missing."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "null\nsplit\n"
        mock_proc.stderr = ""

        spec = {
            "required_filters": ["loudnorm", "ass"],
            "required_video_encoders": [],
            "required_audio_encoders": [],
            "required_audio_decoders": [],
        }

        with patch("subprocess.run", return_value=mock_proc):
            result = doctor.check_ffmpeg_capabilities(ffmpeg_cmd="/usr/bin/ffmpeg", spec=spec)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("filter:loudnorm", result["missing_items"])
            self.assertIn("filter:ass", result["missing_items"])
            self.assertIsNotNone(result["actionable_reason"])

    def test_gpu_missing_fallback(self):
        """Test that missing GPU returns BLOCKED status with CPU fallback."""
        with patch("shutil.which", return_value=None):
            result = doctor.check_gpu()
            self.assertEqual(result["status"], "BLOCKED")
            self.assertFalse(result["cuda_available"])
            self.assertEqual(result["device"], "cpu")
            self.assertIn("CPU fallback", result["actionable_reason"])

    def test_run_doctor_json_output(self):
        """Test that run_doctor with output_json=True produces valid JSON output."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = doctor.run_doctor(output_json=True)
        self.assertEqual(ret, 0)
        output = buf.getvalue()
        parsed = json.loads(output)
        self.assertEqual(parsed["schema_version"], "1.0")


if __name__ == "__main__":
    unittest.main()
