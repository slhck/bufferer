#!/usr/bin/env python3
#
# Simple test suite

import os
import sys
import unittest
import subprocess

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path  # python2 backport

ROOT_PATH = os.path.abspath(os.path.dirname(__file__) + '/../')
sys.path.append(ROOT_PATH)

from bufferer.__main__ import Bufferer


def bufferer_call(args, env=None):
    cmd = [sys.executable, '-m', 'bufferer', '--verbose']
    cmd.extend(args)
    print()
    print(" ".join(cmd))
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=env
    )
    stdout, stderr = p.communicate()

    return (stdout + stderr), p.returncode


def create_tmp_video():
    tmp_video_in = os.path.join(ROOT_PATH, 'test', 'tmp.mp4')
    tmp_video_out = os.path.join(ROOT_PATH, 'test', 'tmp_out.mp4')

    tmp_video_cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=10:size=640x480:rate=60,format=pix_fmts=yuv420p",
        "-i", os.path.join(ROOT_PATH, 'spinners', 'click_and_count.m4a'),
        "-shortest",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "copy",
        tmp_video_in
    ]

    print(tmp_video_cmd)

    subprocess.check_output(tmp_video_cmd)

    return tmp_video_in, tmp_video_out


class TestBufferer(unittest.TestCase):

    def test_bufferer(self):
        tmp_video_in, tmp_video_out = create_tmp_video()

        output, _ = bufferer_call([
            '-f',
            '--black-frame',
            '-i', tmp_video_in,
            '-b', '[[0, 2],[5, 1]]',
            '-o', tmp_video_out,
            '-v', 'libx264', '-a', 'aac'
        ])

        print(output)

        self.assertTrue(os.path.isfile(tmp_video_out))

    def tearDown(self):
        for file in os.listdir(os.path.join(ROOT_PATH, 'test')):
            if os.path.splitext(file)[1] == '.mp4':
                print("Deleting {}".format(file))
                os.remove(os.path.join(ROOT_PATH, 'test', file))


if __name__ == '__main__':
    unittest.main()
