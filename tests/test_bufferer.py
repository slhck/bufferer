#!/usr/bin/env python3

import os
import subprocess
import tempfile

import bufferer


class TestBufferer:
    def test_import(self):
        """Test that we can import the module and get version."""
        assert bufferer.__version__
        assert hasattr(bufferer, "Bufferer")

    def test_bufferer_basic_functionality(self):
        """Test basic bufferer functionality with a simple video."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_video = os.path.join(tmpdir, "input.mp4")
            output_video = os.path.join(tmpdir, "output.mp4")

            # Create simple test video
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=2:size=320x240:rate=10,format=pix_fmts=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                input_video,
            ]
            subprocess.check_output(cmd, stderr=subprocess.DEVNULL)

            # Test bufferer
            b = bufferer.Bufferer(
                input_file=input_video,
                output_file=output_video,
                buflist="[[0.5, 0.5]]",
                disable_spinner=True,
                force_overwrite=True,
                vcodec="libx264",
                acodec="copy",
            )

            b.insert_buf_audiovisual()

            # Check that output exists and is a valid video
            assert os.path.isfile(output_video)
            assert os.path.getsize(output_video) > 0
