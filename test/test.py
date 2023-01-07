#!/usr/bin/env python3
#
# Simple test suite

import os
import shlex
import subprocess
import sys
import unittest

ROOT_PATH = os.path.abspath(os.path.dirname(__file__) + "/../")


def pretty_print_command(cmd):
    print(" ".join([shlex.quote(s) for s in cmd]))


def bufferer_call(args, env=None):
    cmd = [sys.executable, "-m", "bufferer", "--verbose"]
    cmd.extend(args)
    pretty_print_command(cmd)
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=env,
    )
    stdout, stderr = p.communicate()

    return (stdout + stderr), p.returncode


def create_tmp_video():
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

    pretty_print_command(tmp_video_cmd)
    subprocess.check_output(tmp_video_cmd)

    return tmp_video_in, tmp_video_out


class TestBufferer(unittest.TestCase):
    def test_bufferer(self):
        tmp_video_in, tmp_video_out = create_tmp_video()

        output, _ = bufferer_call(
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

        print(output)

        self.assertTrue(os.path.isfile(tmp_video_out))

    def tearDown(self):
        for file in os.listdir(os.path.join(ROOT_PATH, "test")):
            if os.path.splitext(file)[1] == ".mp4":
                print("Deleting {}".format(file))
                os.remove(os.path.join(ROOT_PATH, "test", file))


if __name__ == "__main__":
    unittest.main()
