#!/usr/bin/env python3
#
# Copyright (c) 2017-2019 Werner Robitza
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Bufferer

Inserts fake rebuffering events into video

Usage:
    bufferer    [-hfne] -i <input> -b <buflist> -o <output>
                [-v <vcodec>] [-a <acodec>]
                [-x <pixfmt>]
                [-s <spinner>] [--disable-spinner] [-p <speed>]
                [-t <trim>]
                [-r <brightness>]
                [-l <blur>]
                [--black-frame]
                [--force-framerate]
                [--verbose] [--version]

    -h --help                     show help message
    -f --force                    force overwrite output files
    -n --dry-run                  only print final command, do not run
    -i --input <input>            input video file
    -b --buflist <buflist>        list of buffering events in format "[[x1,y1], [x2,y2],...]" or
                                  "[x1,y1], [x2,y2], ..." where x = position of event in seconds, y = duration of event
    -o --output <output>          output video file
    -v --vcodec <vcodec>          video encoder to use (see `ffmpeg -encoders`) [default: ffv1]
    -a --acodec <acodec>          audio encoder to use (see `ffmpeg -encoders`) [default: pcm_s16le]
    -x --pixfmt <pixfmt>          set pixel format for output [default: yuv420p]
    -s --spinner <spinner>        path to spinner animated file or video [default: spinners/spinner-256-white.png]
    -e --disable-spinner          disable spinner, just show stopped video
    -p --speed <speed>            speed of the spinner, rounded to integer [default: 2]
    -t --trim <trim>              trim video to length in seconds or "HH:MM:SS.msec" format
    -r --brightness <brightness>  change brightness during buffering, use values between -1.0 and 1.0 [default: 0.0]
    -l --blur <blur>              change blur during buffering, value specifies kernel size [default: 5]
    -c --black-frame              start with a black frame if there is buffering at position 0.0
    --force-framerate             force output framerate to be the same as the input video file
    --verbose                     show verbose output
    --version                     show version
"""

from docopt import docopt
import json
import os
import re
import subprocess
import sys

from . import __version__


class Bufferer:
    def __init__(self, arguments):
        # assign arguments from commandline
        self.input_file = arguments["--input"]
        self.output_file = arguments["--output"]
        self.spinner = arguments["--spinner"]
        self.disable_spinner = arguments["--disable-spinner"]
        self.speed = int(arguments["--speed"])
        self.trim = arguments["--trim"]
        self.force_overwrite = arguments["--force"]
        self.dry = arguments["--dry-run"]
        self.vcodec = arguments["--vcodec"]
        self.acodec = arguments["--acodec"]
        self.pixfmt = arguments["--pixfmt"]
        self.verbose = arguments["--verbose"]
        self.brightness = arguments["--brightness"]
        self.blur = arguments["--blur"]
        self.black_frame = arguments["--black-frame"]
        self.force_framerate = arguments["--force-framerate"]

        try:
            self.buflist = json.loads(arguments["--buflist"])
            if not isinstance(self.buflist[0], list):
                self.buflist = [self.buflist]
        except Exception as e:
            buflist_mod = "[" + arguments["--buflist"] + "]"
            try:
                self.buflist = json.loads(buflist_mod)
            except Exception as e:
                raise Exception(
                    "Buffering list parameter not properly formatted. Use a list like [[0, 1], [5, 10]]"
                )

        # presence of input streams
        self.has_video = False
        self.has_audio = False

        # video / audio attributes
        self.fps = None
        self.samplerate = None

        # get info needed for processing
        self.parse_input()

    def run_command(self, cmd):
        """
        Run a command directly
        """
        if self.dry or self.verbose:
            import shlex

            print(" ".join([shlex.quote(c) for c in cmd]))
            if self.dry:
                return

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            return stdout.decode("utf-8") + stderr.decode("utf-8")
        else:
            print("[error] running command: {}".format(" ".join(cmd)))
            print(stderr.decode("utf-8"))
            sys.exit(1)

    def parse_input(self):
        """
        Parse various info from the input file
        """

        p = subprocess.Popen(
            ["ffmpeg", "-i", self.input_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = p.communicate()
        output = stderr.decode("utf-8")
        video_regex = re.compile(r"Video: (.*)")
        audio_regex = re.compile(r"Audio: (.*)")

        if video_regex.search(output):
            self.has_video = True
            video_line = video_regex.search(output).group(1)
            fps_pattern = re.compile(r".*, ([0-9.]+) fps,.*")
            fps_match = fps_pattern.search(video_line)
            if fps_match:
                self.fps = float(fps_match.group(1))

        if audio_regex.search(output):
            self.has_audio = True
            audio_line = audio_regex.search(output).group(1)
            hz_pattern = re.compile(r".*, ([0-9]+) Hz,.*")
            hz_match = hz_pattern.search(audio_line)
            if hz_match:
                self.samplerate = float(hz_match.group(1))

        if not (self.has_audio or self.has_video):
            raise Exception("[error] file has no video or audio stream")

        if not (self.fps or self.samplerate):
            raise Exception(
                "[error] could not find video stream or detect fps / samplerate"
            )

    def generate_loop_cmds(self):
        """
        Construct the looping commands
        """

        vloop_cmds = []
        aloop_cmds = []
        venable_cmds = []
        aenable_cmds = []

        total_vlooped = 0
        total_alooped = 0
        total_buf_len = 0

        self.enable_black_cmd = None

        for buf_event in self.buflist:
            buf_pos, buf_len = buf_event
            buf_pos_enable = round(total_buf_len + buf_pos, 3)
            buf_len_enable = round(buf_pos_enable + buf_len, 3)

            # FIXME: the enable time is slightly smaller than what one would expect, with video
            buf_len_enable_video = buf_len_enable - 0.01

            total_buf_len = total_buf_len + buf_len

            if self.has_video:
                # offset buf_position by the total number of looped frames
                buf_pos_frames = int(self.fps * buf_pos) + total_vlooped
                # FIXME: the number of frames needs to be 1 shorter?
                buf_len_frames = int(self.fps * buf_len)

                loop_cmd = f"loop=loop={buf_len_frames}:size=1:start={buf_pos_frames},setpts=N/FRAME_RATE/TB"
                vloop_cmds.append(loop_cmd)

                total_vlooped += buf_len_frames

                venable_cmd = f"between(t,{buf_pos_enable},{buf_len_enable_video})"
                venable_cmds.append(venable_cmd)

            if self.has_audio:
                # offset buf_position by the total number of looped samples
                buf_pos_samples = int(self.samplerate * buf_pos) + total_alooped
                buf_len_samples = int(self.samplerate * buf_len)

                aloop_cmd = f"aloop=loop={buf_len_samples}:size=1:start={buf_pos_samples},asetpts=N/SAMPLE_RATE/TB"
                aloop_cmds.append(aloop_cmd)

                total_alooped += buf_len_samples

                aenable_cmd = f"between(t,{buf_pos_enable},{buf_len_enable})"
                aenable_cmds.append(aenable_cmd)

            if int(buf_pos_enable) == 0:
                self.enable_black_cmd = f"between(t,0,{buf_len_enable_video})"

        self.vloop_cmd = (",").join(vloop_cmds)
        self.aloop_cmd = (",").join(aloop_cmds)
        self.venable_cmd = ("+").join(venable_cmds)
        self.aenable_cmd = ("+").join(aenable_cmds)

    def set_specs(self):
        """
        set various ffmpeg options
        """

        if self.force_overwrite:
            self.overwrite_spec = "-y"
        else:
            self.overwrite_spec = "-n"

        if self.trim:
            self.trim_spec = ["-t", self.trim]
        else:
            self.trim_spec = None

    def insert_buf_video(self):
        """
        Insert buffering into the video file
        """
        base_cmd = self._get_base_cmd()

        vfilters = []
        if self.disable_spinner:
            vfilters = [f"[0:v]{self.vloop_cmd}[outv]"]
        else:
            if self.black_frame and self.enable_black_cmd:
                vfilters.extend(
                    [
                        f"[0:v]{self.vloop_cmd}[stallvid]",
                        f"color=c=black:r={self.fps}[black]",
                        f"[black][stallvid]scale2ref[black2][stallvid]",
                        f"[stallvid][black2]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1:enable='{self.enable_black_cmd}'[stallvid2]",
                    ]
                )
            else:
                vfilters.append(f"[0:v]{self.vloop_cmd}[stallvid2]",)
            vfilters.extend(
                [
                    f"[stallvid2]avgblur={self.blur}:enable='{self.venable_cmd}',eq=brightness={self.brightness}:enable='{self.venable_cmd}'[stallvidblur]",
                    f"movie=filename={self.spinner}:loop=0,setpts=N/(FRAME_RATE*TB)*{self.speed},fps=fps={self.fps}[spinner]",
                    f"[stallvidblur][spinner]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1:enable='{self.venable_cmd}'[outv]",
                ]
            )

        filters = [";".join(vfilters)]

        base_cmd.extend(["-filter_complex", ";".join(filters)])
        base_cmd.extend(["-map", "[outv]"])
        base_cmd.extend(["-c:v", self.vcodec, "-pix_fmt", self.pixfmt, "-vsync", "cfr"])
        base_cmd.append(self._get_tmp_filename("video"))

        self.run_command(base_cmd)

    def insert_buf_audio(self):
        """
        Insert buffering into the audio file
        """

        base_cmd = self._get_base_cmd()

        afilter = f"[0:a]{self.aloop_cmd},volume=0:enable='{self.aenable_cmd}'[outa]"

        base_cmd.extend(["-filter_complex", afilter])
        base_cmd.extend(["-map", "[outa]"])
        base_cmd.extend(["-c:a", self.acodec])
        base_cmd.append(self._get_tmp_filename("audio"))

        self.run_command(base_cmd)

    def merge_audio_video(self):
        """
        Merge the audio and video files
        """

        if self.force_framerate:
            # FIXME: this seems to be necessary sometimes
            output_codec_options = [
                "-c:v",
                self.vcodec,
                "-filter:v",
                "fps=fps=" + str(self.fps),
                "-c:a",
                "copy",
            ]
        else:
            output_codec_options = ["-c", "copy"]

        combine_cmd = [
            "ffmpeg",
            self.overwrite_spec,
            "-i",
            self._get_tmp_filename("video"),
            "-i",
            self._get_tmp_filename("audio"),
            *output_codec_options,
            self.output_file,
        ]

        self.run_command(combine_cmd)

    def _get_base_cmd(self):
        """
        Get the base command to build the ffmpeg command
        """
        base_cmd = [
            "ffmpeg",
            "-nostdin",
            "-threads",
            "1",
            self.overwrite_spec,
            "-i",
            self.input_file,
        ]

        if self.trim_spec:
            base_cmd.extend(self.trim_spec)

        return base_cmd

    def _get_tmp_filename(self, what="video"):
        if what not in ["video", "audio"]:
            raise RuntimeError("Call _get_tmp_filename with video/audio!")

        suffix = "_video.nut" if what == "video" else "_audio.nut"

        return self.output_file + suffix

    def insert_buf_audiovisual(self):
        """
        Insert the buffering events on both audio and video tracks, looping the video
        frames and audio samples at the corresponding positions.
        """

        self.generate_loop_cmds()
        self.set_specs()

        try:
            if self.has_video:
                if self.verbose:
                    print("[info] running command for processing video")
                self.insert_buf_video()
            if self.has_audio:
                if self.verbose:
                    print("[info] running command for processing audio")
                self.insert_buf_audio()

            if self.verbose:
                print("[info] running command for merging video/audio")
            self.merge_audio_video()
        except Exception as e:
            print(f"[error] error running processing: {e}")
        finally:
            if not self.dry:
                for file in [
                    self._get_tmp_filename("video"),
                    self._get_tmp_filename("audio"),
                ]:
                    if os.path.isfile(file):
                        os.remove(file)
                    else:
                        print(f"[warn] temporary file {file} not found!")


def main():
    arguments = docopt(__doc__, version=str(__version__))

    if not os.path.isfile(arguments["--input"]):
        raise IOError("Input file does not exist")

    if not arguments["--buflist"]:
        raise Exception("No buffering list given, please specify --buflist")
    b = Bufferer(arguments)
    try:
        b.insert_buf_audiovisual()
    except Exception as e:
        raise Exception("Error while converting: " + str(e))

    if arguments["--verbose"]:
        print("Output written to " + b.output_file)


if __name__ == "__main__":
    main()
