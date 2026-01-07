#!/usr/bin/env python3

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
                [--audio-disable]
                [--black-frame]
                [--force-framerate]
                [--skipping]
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
    --audio-disable               disable audio for the output, even if input contains audio
    --force-framerate             force output framerate to be the same as the input video file
    --skipping                    insert frame freezes with skipping (without indicator) at the <buflist> locations and durations
    --verbose                     show verbose output
    --version                     show version
"""

import logging
import os
import shutil
import sys

from docopt import docopt

from . import __version__
from ._bufferer import Bufferer
from ._log import CustomLogFormatter


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("bufferer")
    logger.setLevel(level)

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(level)

    ch.setFormatter(CustomLogFormatter())

    logger.addHandler(ch)

    return logger


def main():
    arguments = docopt(__doc__, version=str(__version__))

    # Check FFmpeg is available
    if not shutil.which("ffmpeg"):
        print(
            "Error: ffmpeg not found. Please install FFmpeg and ensure it's in your PATH.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isfile(arguments["--input"]):
        raise IOError("Input file does not exist")

    if not arguments["--buflist"]:
        raise RuntimeError("No buffering list given, please specify --buflist")

    # Check spinner file exists (unless disabled)
    if not arguments["--disable-spinner"] and not arguments["--skipping"]:
        spinner_path = arguments["--spinner"]
        if not os.path.isfile(spinner_path):
            print(f"Error: Spinner file not found: {spinner_path}", file=sys.stderr)
            print(
                "Use --disable-spinner to run without a spinner, or provide a valid spinner path with --spinner",
                file=sys.stderr,
            )
            sys.exit(1)

    logger = setup_logger(logging.DEBUG if arguments["--verbose"] else logging.INFO)

    b = Bufferer(
        input_file=arguments["--input"],
        output_file=arguments["--output"],
        buflist=arguments["--buflist"],
        spinner=arguments["--spinner"],
        disable_spinner=arguments["--disable-spinner"],
        speed=int(arguments["--speed"]),
        trim=arguments["--trim"],
        force_overwrite=arguments["--force"],
        dry=arguments["--dry-run"],
        vcodec=arguments["--vcodec"],
        acodec=arguments["--acodec"],
        pixfmt=arguments["--pixfmt"],
        brightness=arguments["--brightness"],
        blur=arguments["--blur"],
        audio_disable=arguments["--audio-disable"],
        black_frame=arguments["--black-frame"],
        force_framerate=arguments["--force-framerate"],
        skipping=arguments["--skipping"],
    )

    try:
        b.insert_buf_audiovisual()
    except Exception as e:
        raise RuntimeError("Error while converting: " + str(e))

    logger.info("Output written to " + b.output_file)


if __name__ == "__main__":
    main()
