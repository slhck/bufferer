# Bufferer

Inserts fake rebuffering events into video.

Author: Werner Robitza <werner.robitza@gmail.com>

# Requirements

- Python
- FFmpeg:
    - download a static build from [their website](http://ffmpeg.org/download.html))
    - put the `ffmpeg` executable in your `$PATH`

# Installation

    pip install bufferer

Or clone this repository, then run the tool with `python -m bufferer`.

# Usage

    bufferer    [-hfn] -i <input> -b <buflist> -o <output>
                [-v <vcodec>] [-a <acodec>]
                [-s <spinner>] [-p <speed>] [-t <trim>] [-r <brightness>]
                [-l <blur>]
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
    -s --spinner <spinner>        path to spinner animated file or video [default: spinners/spinner-256-white.png]
    -p --speed <speed>            speed of the spinner, rounded to integer [default: 2]
    -t --trim <trim>              trim video to length in seconds or "HH:MM:SS.msec" format
    -r --brightness <brightness>  change brightness during buffering, use values between -1.0 and 1.0 [default: 0.0]
    -l --blur <blur>              change blur during buffering, value specifies kernel size [default: 5]
    --verbose                     show verbose output
    --version                     show version

# Caveats

- The script doesn't work on input files that have no video or no audio.
- You need to pick a proper output file format for the codecs you choose. Use `.avi` for the FFV1 and PCM WAV defaults.

# Acknowledgements

- Big Buck Bunny: Blender Foundation
- Free spinners from http://preloaders.net/en/free
- Click from http://metronomer.com/

# Helpful info

To generate AV sync samples:

    ffmpeg -f lavfi -i testsrc=duration=20:size=1280x720:rate=24 \
    -vf "drawtext=timecode='00\:00\:00\:00':fontsize=72:r=24:x=(w-tw)/2:y=h-(2*lh): \
    fontcolor=white:box=1:boxcolor=black@1.0" \
    -c:v huffyuv testsrc_24.avi
    ffmpeg -f lavfi -i testsrc=duration=20:size=1280x720:rate=23.97 \
    -vf "drawtext=timecode='00\:00\:00\:00':fontsize=72:r=23.97:x=(w-tw)/2:y=h-(2*lh): \
    fontcolor=white:box=1:boxcolor=black@1.0" \
    -c:v huffyuv testsrc_2397.avi

    ffmpeg -i testsrc_24.avi -i click.mp3 -c:v copy -c:a pcm_s16le \
    -map 0:v -map 1:a testsrc_24_c.avi
    ffmpeg -i testsrc_2397.avi -i click.mp3 -c:v copy -c:a pcm_s16le \
    -map 0:v -map 1:a testsrc_2397_c.avi

# License

bufferer, Copyright (c) 2017 Werner Robitza

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.