#!/usr/bin/env python
#
# Copyright (c) 2017 Werner Robitza
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
    bufferer    [-hfn] -i <input> -o <output>
                [-b <buflist>] [-v <vcodec>] [-a <acodec>]
                [-s <spinner>] [-p <speed>] [-t <trim>] [-r <brightness>]
                [-l <blur>]
                [--verbose] [--version]

    -h --help                     show help message
    -f --force                    force overwrite output files
    -n --dry-run                  only print final command, do not run
    -i --input <input>            input video file
    -o --output <output>          output video file
    -b --buflist <buflist>        list of buffering events in format "[[x1,y1], [x2,y2],...]" or
                                  "[x1,y1], [x2,y2], ..." where x = position of event in seconds, y = duration of event
    -v --vcodec <vcodec>          video encoder to use (see `ffmpeg -encoders`) [default: ffv1]
    -a --acodec <acodec>          audio encoder to use (see `ffmpeg -encoders`) [default: pcm_s16le]
    -s --spinner <spinner>        path to spinner animated file or video [default: spinners/spinner-256-white.png]
    -p --speed <speed>            speed of the spinner, rounded to integer [default: 2]
    -t --trim <trim>              trim video to length in seconds or "HH:MM:SS.msec" format
    -r --brightness <brightness>  change brightness during buffering, use values between -1.0 and 1.0 [default: 0.0]
    -l --blur <blur>              change blur during buffering, value specifies kernel size [default: 5]
    --verbose                     show verbose output
    --version                     show version
"""

from docopt import docopt
import json
import os
import pkg_resources
import re
import subprocess

class Bufferer:

    def __init__(self, arguments):
        # assign arguments from commandline
        self.input_file      = arguments["--input"]
        self.output_file     = arguments["--output"]
        self.spinner         = arguments["--spinner"]
        self.speed           = int(arguments["--speed"])
        self.trim            = arguments["--trim"]
        self.force_overwrite = arguments["--force"]
        self.dry             = arguments["--dry-run"]
        self.vcodec          = arguments["--vcodec"]
        self.acodec          = arguments["--acodec"]
        self.verbose         = arguments["--verbose"]
        self.brightness      = arguments["--brightness"]
        self.blur            = arguments["--blur"]

        try:
          self.buflist = json.loads(arguments["--buflist"])
        except Exception as e:
            buflist_mod = "[" + arguments["--buflist"] + "]"
            try:
                self.buflist = json.loads(buflist_mod)
            except Exception as e:
                raise StandardError("Buffering list parameter not properly formatted. Use a list like [[0, 1], [5, 10]]")

        # get info needed for processing
        self.parse_fps_samplerate()

    def run_command(self, cmd, raw=True):
        """
        Run a command directly
        """
        if self.dry or self.verbose:
            print("[cmd] " + str(cmd))
            if self.dry:
                return

        if raw:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        else:
            process = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = process.communicate()

        if process.returncode == 0:
            return stdout.decode('utf-8') + stderr.decode('utf-8')
        else:
            print("[error] running command: {}".format(cmd))
            print(stderr.decode('utf-8'))


    def parse_fps_samplerate(self):
        """
        Get FPS as a float from the input file using ffmpeg
        """

        p = subprocess.Popen(['ffmpeg', '-i', self.input_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        output = stderr.decode('utf-8')
        video_regex = re.compile(r'Video: (.*)')
        audio_regex = re.compile(r'Audio: (.*)')

        if video_regex.search(output):
            video_line = video_regex.search(output).group(1)
            fps_pattern = re.compile(r'.*, ([0-9.]+) fps,.*')
            fps_match = fps_pattern.search(video_line)
            if fps_match:
                self.fps = float(fps_match.group(1))

        if audio_regex.search(output):
            audio_line = audio_regex.search(output).group(1)
            hz_pattern = re.compile(r'.*, ([0-9]+) Hz,.*')
            hz_match = hz_pattern.search(audio_line)
            if hz_match:
                self.samplerate = float(hz_match.group(1))

        if not self.fps or not self.samplerate:
            raise StandardError("[error] could not find video stream or detect fps / samplerate")


    def set_loop_cmds(self):
        loop_cmds            = []
        aloop_cmds           = []
        enable_cmds          = []

        total_looped         = 0
        total_enable         = 0
        total_looped_samples = 0

        for buf_event in self.buflist:
            buf_pos, buf_len = buf_event

            # offset buf_position by the total number of looped frames
            buf_pos_frames = int(self.fps * buf_pos) + total_looped
            buf_len_frames = int(self.fps * buf_len)

            # offset buf_position by the total number of looped samples
            buf_pos_samples = int(self.samplerate * buf_pos) + total_looped_samples
            buf_len_samples = int(self.samplerate * buf_len)

            loop_cmd = "loop=loop={buf_len_frames}:size=1:start={buf_pos_frames},\
            setpts=N/FRAME_RATE/TB".format(**locals())
            loop_cmds.append(loop_cmd)

            aloop_cmd = "aloop=loop={buf_len_samples}:size=1:start={buf_pos_samples},\
            asetpts=N/SAMPLE_RATE/TB".format(**locals())
            aloop_cmds.append(aloop_cmd)

            buf_pos_enable = buf_pos + total_enable
            buf_len_enable = buf_pos_enable + buf_len
            enable_cmd = "between(t,{buf_pos_enable},{buf_len_enable})".format(**locals())
            enable_cmds.append(enable_cmd)

            total_looped = total_looped + buf_len_frames
            total_enable = total_enable + buf_len

            total_looped_samples = total_looped_samples + buf_len_samples

        self.loop_cmd = (", ").join(loop_cmds)
        self.aloop_cmd = (", ").join(aloop_cmds)
        self.enable_cmd = ("+").join(enable_cmds)

    def set_specs(self):
        # various ffmpeg options
        if self.force_overwrite:
            self.overwrite_spec = "-y"
        else:
            self.overwrite_spec = "-n"

        if self.trim:
            self.trim_spec = "-t " + self.trim
        else:
            self.trim_spec = ""

    def insert_buf_audiovisual(self):
        """
        Insert the buffering events on both audio and video tracks, looping the video
        frames and audio samples at the corresponding positions.
        """

        self.set_loop_cmds()
        self.set_specs()

        cmd = '''
        ffmpeg {self.overwrite_spec} -i {self.input_file}
        -filter_complex "[0:v]{self.loop_cmd}[stallvid];
        [0:a]{self.aloop_cmd},volume=0:enable='{self.enable_cmd}'[outa];
        [stallvid]avgblur={self.blur}:enable='{self.enable_cmd}', eq=brightness={self.brightness}:enable='{self.enable_cmd}'[stallvidblur]; \
        movie=filename={self.spinner}:loop=0, setpts=N/(FRAME_RATE*TB)*{self.speed}[spinner];
        [stallvidblur][spinner]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1:enable='{self.enable_cmd}'[outv]"
        -shortest -map "[outv]" -map "[outa]" {self.trim_spec} -c:v {self.vcodec} -c:a {self.acodec} {self.output_file}
        '''.format(**locals()).replace('\n',' ').replace('  ',' ').strip()

        if self.verbose:
            print("[info] running ffmpeg command, this may take a while")

        self.run_command(cmd)

def main():
    arguments = docopt(__doc__, version="0.1")

    if not os.path.isfile(arguments["--input"]):
        raise IOError("Input file does not exist")

    if not arguments["--buflist"]:
        raise StandardError("No buffering list given, please specify --buflist")

    b = Bufferer(arguments)
    try:
        b.insert_buf_audiovisual()
    except Exception as e:
        raise StandardError("Error while converting: " + e)

    if arguments["--verbose"]:
        print("Output written to " + b.output_file)

if __name__ == '__main__':
    main()
