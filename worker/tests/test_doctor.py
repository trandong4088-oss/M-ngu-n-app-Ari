"""
Unit tests for aro doctor environment, FFmpeg version, and capability diagnostics.
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

    # 1. Missing min_version in manifest
    def test_ffmpeg_manifest_missing_min_version(self):
        """Test that missing or empty min_version in specification explicitly fails."""
        mock_ffmpeg = MagicMock(returncode=0, stdout="ffmpeg version 4.4.2\n")
        mock_ffprobe = MagicMock(returncode=0, stdout="ffprobe version 4.4.2\n")

        with patch("subprocess.run", side_effect=[mock_ffmpeg, mock_ffprobe]):
            # Test empty dict
            res_empty = doctor.check_ffmpeg_binaries(ffmpeg_cmd="/usr/bin/ffmpeg", spec={})
            self.assertEqual(res_empty["status"], "FAIL")
            self.assertIn("Missing required 'min_version'", res_empty["detail"])
            self.assertIn("Define a valid 'min_version'", res_empty["actionable_reason"])

            # Test empty string
            res_blank = doctor.check_ffmpeg_binaries(ffmpeg_cmd="/usr/bin/ffmpeg", spec={"min_version": "   "})
            self.assertEqual(res_blank["status"], "FAIL")
            self.assertIn("Missing required 'min_version'", res_blank["detail"])

    # 2. Invalid min_version format in manifest
    def test_ffmpeg_manifest_invalid_min_version(self):
        """Test that unparseable/invalid min_version in specification explicitly fails."""
        mock_ffmpeg = MagicMock(returncode=0, stdout="ffmpeg version 4.4.2\n")
        mock_ffprobe = MagicMock(returncode=0, stdout="ffprobe version 4.4.2\n")

        spec = {"min_version": "invalid-semver-string"}

        with patch("subprocess.run", side_effect=[mock_ffmpeg, mock_ffprobe]):
            result = doctor.check_ffmpeg_binaries(ffmpeg_cmd="/usr/bin/ffmpeg", spec=spec)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("Invalid 'min_version' format", result["detail"])
            self.assertIn("Correct 'min_version' format", result["actionable_reason"])

    # 3. Valid min_version passes when detected FFmpeg is new enough
    def test_ffmpeg_valid_min_version_passes_when_detected_is_newer(self):
        """Test that valid min_version passes when detected FFmpeg is newer than minimum."""
        mock_ffmpeg = MagicMock(returncode=0, stdout="ffmpeg version 6.1.1-1ubuntu1 Copyright (c)\n")
        mock_ffprobe = MagicMock(returncode=0, stdout="ffprobe version 6.1.1\n")

        spec = {"min_version": "4.4.0"}

        with patch("subprocess.run", side_effect=[mock_ffmpeg, mock_ffprobe]):
            result = doctor.check_ffmpeg_binaries(
                ffmpeg_cmd="/usr/bin/ffmpeg",
                ffprobe_cmd="/usr/bin/ffprobe",
                spec=spec,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["detected_version"], "6.1.1")
            self.assertIn(">= minimum 4.4.0", result["detail"])

    # 4. Version at exact minimum
    def test_ffmpeg_version_at_minimum(self):
        """Test version parsing when detected FFmpeg version exactly matches minimum."""
        mock_ffmpeg = MagicMock(returncode=0, stdout="ffmpeg version 4.4.0 Copyright (c) 2000-2021\n")
        mock_ffprobe = MagicMock(returncode=0, stdout="ffprobe version 4.4.0\n")

        spec = {"min_version": "4.4.0"}

        with patch("subprocess.run", side_effect=[mock_ffmpeg, mock_ffprobe]):
            result = doctor.check_ffmpeg_binaries(
                ffmpeg_cmd="/usr/bin/ffmpeg",
                ffprobe_cmd="/usr/bin/ffprobe",
                spec=spec,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["detected_version"], "4.4.0")
            self.assertIn(">= minimum 4.4.0", result["detail"])

    # 5. Version below minimum
    def test_ffmpeg_version_below_minimum(self):
        """Test version parsing when detected FFmpeg version is below minimum."""
        mock_ffmpeg = MagicMock(returncode=0, stdout="ffmpeg version 4.3.2-ubuntu1 Copyright (c) 2000-2020\n")
        mock_ffprobe = MagicMock(returncode=0, stdout="ffprobe version 4.3.2\n")

        spec = {"min_version": "4.4.0"}

        with patch("subprocess.run", side_effect=[mock_ffmpeg, mock_ffprobe]):
            result = doctor.check_ffmpeg_binaries(
                ffmpeg_cmd="/usr/bin/ffmpeg",
                ffprobe_cmd="/usr/bin/ffprobe",
                spec=spec,
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["detected_version"], "4.3.2")
            self.assertIn("below required minimum 4.4.0", result["detail"])
            self.assertIn("Upgrade FFmpeg", result["actionable_reason"])

    # 6. Unparseable detected version
    def test_ffmpeg_version_unparseable(self):
        """Test version parsing when FFmpeg version string cannot be parsed into semver."""
        mock_ffmpeg = MagicMock(returncode=0, stdout="ffmpeg version git-devel-custom-snapshot Copyright (c)\n")
        mock_ffprobe = MagicMock(returncode=0, stdout="ffprobe version git-devel\n")

        spec = {"min_version": "4.4.0"}

        with patch("subprocess.run", side_effect=[mock_ffmpeg, mock_ffprobe]):
            result = doctor.check_ffmpeg_binaries(
                ffmpeg_cmd="/usr/bin/ffmpeg",
                ffprobe_cmd="/usr/bin/ffprobe",
                spec=spec,
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("Could not parse FFmpeg version", result["detail"])
            self.assertIn("Invalid or unparseable", result["actionable_reason"])

    # 7. Missing required encoder
    def test_ffmpeg_missing_required_encoder(self):
        """Test capability check when a required video/audio encoder is missing."""
        mock_filters = MagicMock(returncode=0, stdout="loudnorm\nsidechaincompress\nass\nsubtitles\n", stderr="")
        mock_encoders = MagicMock(returncode=0, stdout="aac\n", stderr="")  # missing libx264
        mock_decoders = MagicMock(returncode=0, stdout="aac\nmp3\nflac\npcm_s16le\npcm_f32le\n", stderr="")

        spec = {
            "required_filters": ["loudnorm"],
            "required_video_encoders": ["libx264"],
            "required_audio_encoders": ["aac"],
            "required_audio_decoders": ["aac"],
        }

        with patch("subprocess.run", side_effect=[mock_filters, mock_encoders, mock_decoders]):
            result = doctor.check_ffmpeg_capabilities(ffmpeg_cmd="/usr/bin/ffmpeg", spec=spec)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("encoder:libx264", result["missing_items"])
            self.assertIn("Missing components", result["actionable_reason"])

    # 8. Missing required decoder
    def test_ffmpeg_missing_required_decoder(self):
        """Test capability check when a required audio decoder is missing."""
        mock_filters = MagicMock(returncode=0, stdout="loudnorm\n", stderr="")
        mock_encoders = MagicMock(returncode=0, stdout="libx264\naac\n", stderr="")
        mock_decoders = MagicMock(returncode=0, stdout="aac\nmp3\n", stderr="")  # missing flac

        spec = {
            "required_filters": ["loudnorm"],
            "required_video_encoders": ["libx264"],
            "required_audio_encoders": ["aac"],
            "required_audio_decoders": ["flac"],
        }

        with patch("subprocess.run", side_effect=[mock_filters, mock_encoders, mock_decoders]):
            result = doctor.check_ffmpeg_capabilities(ffmpeg_cmd="/usr/bin/ffmpeg", spec=spec)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("decoder:flac", result["missing_items"])
            self.assertIn("Missing components", result["actionable_reason"])

    # 9. Non-zero return code from capability commands (filters, encoders, decoders)
    def test_ffmpeg_capability_commands_nonzero_returncode(self):
        """Test capability check when ffmpeg capability commands exit with non-zero code."""
        # 9a: filters command fails
        mock_fail = MagicMock(returncode=1, stdout="", stderr="Internal filter error")
        with patch("subprocess.run", return_value=mock_fail):
            res_flt = doctor.check_ffmpeg_capabilities(ffmpeg_cmd="/usr/bin/ffmpeg")
            self.assertEqual(res_flt["status"], "FAIL")
            self.assertIn("exit code 1", res_flt["detail"])

        # 9b: encoders command fails
        mock_pass_flt = MagicMock(returncode=0, stdout="loudnorm\nsidechaincompress\nass\nsubtitles\n", stderr="")
        mock_fail_enc = MagicMock(returncode=2, stdout="", stderr="Encoder enumeration failed")
        with patch("subprocess.run", side_effect=[mock_pass_flt, mock_fail_enc]):
            res_enc = doctor.check_ffmpeg_capabilities(ffmpeg_cmd="/usr/bin/ffmpeg")
            self.assertEqual(res_enc["status"], "FAIL")
            self.assertIn("exit code 2", res_enc["detail"])

        # 9c: decoders command fails
        mock_pass_enc = MagicMock(returncode=0, stdout="libx264\naac\n", stderr="")
        mock_fail_dec = MagicMock(returncode=127, stdout="", stderr="Command aborted")
        with patch("subprocess.run", side_effect=[mock_pass_flt, mock_pass_enc, mock_fail_dec]):
            res_dec = doctor.check_ffmpeg_capabilities(ffmpeg_cmd="/usr/bin/ffmpeg")
            self.assertEqual(res_dec["status"], "FAIL")
            self.assertIn("exit code 127", res_dec["detail"])

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
