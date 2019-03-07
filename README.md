# Bufferer

Inserts fake rebuffering events into video.

Author: Werner Robitza <werner.robitza@gmail.com>

# Requirements

- Python 3.6
- FFmpeg:
    - download a static build from [their website](http://ffmpeg.org/download.html))
    - put the `ffmpeg` executable in your `$PATH`

# Installation

    pip3 install bufferer

Or clone this repository, then run the tool with `python -m bufferer`.

# Usage

    Usage:
    bufferer    [-hfne] -i <input> -b <buflist> -o <output>
                [-v <vcodec>] [-a <acodec>]
                [-x <pixfmt>]
                [-s <spinner>] [--disable-spinner] [-p <speed>]
                [-t <trim>]
                [-r <brightness>]
                [-l <blur>]
                [--black-frame]
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
    --verbose                     show verbose output
    --version                     show version

# Caveats

- The time stamps for the buffering list must be given in media time. If, for example, you want an initial loading time of 5 seconds, and then a stalling event to occur 10 seconds into the video, specify `[[0, 5], [10, 5]]`.
- You need to pick a proper output file format for the codecs you choose. Use `.avi` for the FFV1 and PCM WAV defaults.
- Make sure to select the right pixel format as output, e.g. `--pixfmt yuv420p` for higher compatibility.

# Acknowledgements

- Big Buck Bunny: Blender Foundation
- Free spinners from http://preloaders.net/en/free
- Click from http://metronomer.com/
- Count from https://www.youtube.com/watch?v=U03lLvhBzOw

# Helpful info

To generate AV sync samples:

```
ffmpeg \
-y \
-f lavfi -i testsrc=duration=60:size=320x240:rate=60,format=pix_fmts=yuv420p \
-i click_and_count.m4a
<output>
```

Sample command to test buffering:

```
ffmpeg \
-y \
-f lavfi -i testsrc=duration=60:size=320x240:rate=60,format=pix_fmts=yuv420p \
-i spinners/click_and_count.m4a \
-filter_complex " \
    [0:v] \
        loop=loop=240:size=1:start=0, setpts=N/FRAME_RATE/TB, \
        loop=loop=30:size=1:start=840, setpts=N/FRAME_RATE/TB, \
        loop=loop=84:size=1:start=1140, setpts=N/FRAME_RATE/TB, \
        loop=loop=48:size=1:start=1548, setpts=N/FRAME_RATE/TB \
    [stallvid]; \
        movie=filename=spinners/spinner-64-white.png:loop=0, setpts=N/(FRAME_RATE*TB)*2 \
    [spinner]; \
    [stallvid][spinner] \
        overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1:\
        enable='between(t,0,4.0)+between(t,14.0,14.5)+between(t,19.0,20.4)+between(t,25.8,26.6)' \
    [outv];
    [1:a] \
        aloop=loop=192000:size=1:start=0, asetpts=N/SAMPLE_RATE/TB, \
        aloop=loop=24000:size=1:start=672000, asetpts=N/SAMPLE_RATE/TB, \
        aloop=loop=67200:size=1:start=912000, asetpts=N/SAMPLE_RATE/TB, \
        aloop=loop=38400:size=1:start=1238399, asetpts=N/SAMPLE_RATE/TB, \
        volume=0:enable='between(t,0,4.0)+between(t,14.0,14.5)+between(t,19.0,20.4)+between(t,25.8,26.6)' \
    [outa] \
" -shortest -map "[outv]" -map "[outa]" output.mp4
```

# License

bufferer, Copyright (c) 2017-2019 Werner Robitza

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.