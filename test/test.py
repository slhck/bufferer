#!/usr/bin/env python3
#
# Simple test suite for Bufferer

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from typing import Any

import pytest

ROOT_PATH = os.path.abspath(os.path.dirname(__file__) + "/../")


def _pretty_print_command(cmd):
    print(" ".join([shlex.quote(s) for s in cmd]))


def _get_ffprobe_info(video_path: str) -> dict[str, Any]:
    """
    Example output:

    {
      "streams": [
        {
          "index": 0,
          "codec_name": "h264",
          "codec_long_name": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
          "profile": "High",
          "codec_type": "video",
          "codec_tag_string": "avc1",
          "codec_tag": "0x31637661",
          "width": 640,
          "height": 480,
          "coded_width": 640,
          "coded_height": 480,
          "closed_captions": 0,
          "film_grain": 0,
          "has_b_frames": 2,
          "sample_aspect_ratio": "1:1",
          "display_aspect_ratio": "4:3",
          "pix_fmt": "yuv420p",
          "level": 31,
          "chroma_location": "left",
          "field_order": "progressive",
          "refs": 1,
          "is_avc": "true",
          "nal_length_size": "4",
          "id": "0x1",
          "r_frame_rate": "60/1",
          "avg_frame_rate": "60/1",
          "time_base": "1/61440",
          "start_pts": 0,
          "start_time": "0.000000",
          "duration_ts": 798720,
          "duration": "13.000000",
          "bit_rate": "171739",
          "bits_per_raw_sample": "8",
          "nb_frames": "780",
          "extradata_size": 46,
          "disposition": {
            "default": 1,
            "dub": 0,
            "original": 0,
            "comment": 0,
            "lyrics": 0,
            "karaoke": 0,
            "forced": 0,
            "hearing_impaired": 0,
            "visual_impaired": 0,
            "clean_effects": 0,
            "attached_pic": 0,
            "timed_thumbnails": 0,
            "captions": 0,
            "descriptions": 0,
            "metadata": 0,
            "dependent": 0,
            "still_image": 0
          },
          "tags": {
            "language": "und",
            "handler_name": "VideoHandler",
            "vendor_id": "[0][0][0][0]",
            "encoder": "Lavc59.37.100 libx264"
          }
        },
        {
          "index": 1,
          "codec_name": "aac",
          "codec_long_name": "AAC (Advanced Audio Coding)",
          "profile": "LC",
          "codec_type": "audio",
          "codec_tag_string": "mp4a",
          "codec_tag": "0x6134706d",
          "sample_fmt": "fltp",
          "sample_rate": "48000",
          "channels": 2,
          "channel_layout": "stereo",
          "bits_per_sample": 0,
          "id": "0x2",
          "r_frame_rate": "0/0",
          "avg_frame_rate": "0/0",
          "time_base": "1/48000",
          "start_pts": 0,
          "start_time": "0.000000",
          "duration_ts": 623616,
          "duration": "12.992000",
          "bit_rate": "101662",
          "nb_frames": "609",
          "extradata_size": 5,
          "disposition": {
            "default": 1,
            "dub": 0,
            "original": 0,
            "comment": 0,
            "lyrics": 0,
            "karaoke": 0,
            "forced": 0,
            "hearing_impaired": 0,
            "visual_impaired": 0,
            "clean_effects": 0,
            "attached_pic": 0,
            "timed_thumbnails": 0,
            "captions": 0,
            "descriptions": 0,
            "metadata": 0,
            "dependent": 0,
            "still_image": 0
          },
          "tags": {
            "language": "und",
            "handler_name": "SoundHandler",
            "vendor_id": "[0][0][0][0]"
          }
        }
      ],
      "format": {
        "filename": "/Users/werner/Documents/Projects/slhck/bufferer/test/tmp_out.mp4",
        "nb_streams": 2,
        "nb_programs": 0,
        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        "format_long_name": "QuickTime / MOV",
        "start_time": "0.000000",
        "duration": "13.000000",
        "size": "465857",
        "bit_rate": "286681",
        "probe_score": 100,
        "tags": {
          "major_brand": "isom",
          "minor_version": "512",
          "compatible_brands": "isomiso2avc1mp41",
          "encoder": "Lavf59.27.100"
        }
      }
    }
    """
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    _pretty_print_command(cmd)
    output = subprocess.check_output(cmd)
    return json.loads(output)


def _bufferer_call(args, env=None):
    cmd = [sys.executable, "-m", "bufferer", "--verbose"]
    cmd.extend(args)
    _pretty_print_command(cmd)
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=env,
    )
    stdout, stderr = p.communicate()

    return (stdout + stderr), p.returncode


@pytest.fixture(scope="module")
def tmp_video():
    tmp_video_in = os.path.join(ROOT_PATH, "test", "tmp.mp4")
    tmp_video_out = os.path.join(ROOT_PATH, "test", "tmp_out.mp4")

    tmp_video_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=10:size=640x480:rate=60,format=pix_fmts=yuv420p",
        "-i",
        os.path.join(ROOT_PATH, "spinners", "click_and_count.m4a"),
        "-vf",
        "drawtext=fontfile=/usr/share/fonts/truetype/ubuntu-font-family/UbuntuMono-R.ttf:text=%{n}:fontsize=72:r=60:x=(w-tw)/2: y=h-(2*lh): fontcolor=white: box=1: boxcolor=0x00000099",
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "copy",
        tmp_video_in,
    ]

    _pretty_print_command(tmp_video_cmd)
    subprocess.check_output(tmp_video_cmd)

    yield (tmp_video_in, tmp_video_out)

    if os.path.isfile(tmp_video_in):
        os.remove(tmp_video_in)

    if os.path.isfile(tmp_video_out):
        os.remove(tmp_video_out)


class TestBufferer:
    def test_bufferer(self, tmp_video: tuple[str, str]):
        tmp_video_in, tmp_video_out = tmp_video

        _bufferer_call(
            [
                "-f",
                "--black-frame",
                "-i",
                tmp_video_in,
                "-b",
                "[[0, 2],[5, 1]]",
                "-o",
                tmp_video_out,
                "-v",
                "libx264",
                "-a",
                "aac",
            ]
        )

        assert os.path.isfile(tmp_video_out)

        input_video_info = _get_ffprobe_info(tmp_video_in)
        output_video_info = _get_ffprobe_info(tmp_video_out)

        assert (
            round(float(output_video_info["format"]["duration"]), 1)
            == round(float(input_video_info["format"]["duration"]), 1) + 3
        )
