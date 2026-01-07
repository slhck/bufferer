from __future__ import annotations

import datetime
import json
import logging
import os
import re
import shlex
import subprocess
from typing import Optional

logger = logging.getLogger("bufferer")


class Bufferer:
    """
    Bufferer class

    Args:
        input_file (str): Input file
        output_file (str): Output file
        buflist (list[list] | str): Buffering list
        spinner (str, optional): Spinner image. Defaults to "spinners/spinner-256-white.png".
        disable_spinner (bool, optional): Disable spinner. Defaults to False.
        speed (int, optional): Speed of spinner. Defaults to 2.
        trim (str | None, optional): Trim video. Defaults to None.
        force_overwrite (bool, optional): Force overwrite of output file. Defaults to False.
        dry (bool, optional): Dry run. Defaults to False.
        vcodec (str, optional): Video codec. Defaults to "ffv1".
        acodec (str, optional): Audio codec. Defaults to "pcm_s16le".
        pixfmt (str, optional): Pixel format. Defaults to "yuv420p".
        brightness (float, optional): Brightness of spinner. Defaults to 0.0.
        blur (int, optional): Blur of spinner. Defaults to 5.
        audio_disable (bool, optional): Disable audio. Defaults to False.
        black_frame (bool, optional): Add black frame at the end. Defaults to False.
        force_framerate (bool, optional): Force framerate. Defaults to False.
        skipping (bool, optional): Enable skipping. Defaults to False.

    Raises:
        RuntimeError: Buffering list parameter not properly formatted. Use a list like [[0, 1], [5, 10]]
    """

    def __init__(
        self,
        input_file: str,
        output_file: str,
        buflist: list[list] | str,
        spinner: str = "spinners/spinner-256-white.png",
        disable_spinner: bool = False,
        speed: int = 2,
        trim: str | None = None,
        force_overwrite: bool = False,
        dry: bool = False,
        vcodec: str = "ffv1",
        acodec: str = "pcm_s16le",
        pixfmt: str = "yuv420p",
        brightness: float = 0.0,
        blur: int = 5,
        audio_disable: bool = False,
        black_frame: bool = False,
        force_framerate: bool = False,
        skipping: bool = False,
    ):
        # assign arguments from commandline
        self.input_file = input_file
        self.output_file = output_file
        self.spinner = spinner
        self.disable_spinner = disable_spinner
        self.speed = speed
        self.trim = trim
        self.force_overwrite = force_overwrite
        self.dry = dry
        self.vcodec = vcodec
        self.acodec = acodec
        self.pixfmt = pixfmt
        self.brightness = brightness
        self.blur = blur
        self.audio_disable = audio_disable
        self.black_frame = black_frame
        self.force_framerate = force_framerate
        self.skipping = skipping

        if isinstance(buflist, str):
            try:
                self.buflist = json.loads(buflist)
                if not isinstance(self.buflist[0], list):
                    self.buflist = [self.buflist]
            except json.JSONDecodeError as e:
                buflist_mod = "[" + buflist + "]"
                try:
                    self.buflist = json.loads(buflist_mod)
                except json.JSONDecodeError:
                    raise RuntimeError(
                        f"Buffering list parameter not properly formatted.\n"
                        f"  Received: {buflist!r}\n"
                        f"  JSON error: {e.msg} at position {e.pos}\n"
                        f"  Expected format: '[[0, 1], [5, 10]]' or '[0, 1], [5, 10]'\n"
                        f"  where each pair is [position_in_seconds, duration_in_seconds]"
                    )
            except (IndexError, TypeError):
                raise RuntimeError(
                    f"Buffering list parameter is empty or invalid.\n"
                    f"  Received: {buflist!r}\n"
                    f"  Expected format: '[[0, 1], [5, 10]]' or '[0, 1], [5, 10]'\n"
                    f"  where each pair is [position_in_seconds, duration_in_seconds]"
                )
        else:
            self.buflist = buflist

        # presence of input streams
        self.has_video: bool = False
        self.has_audio: bool = False

        # video / audio attributes
        self.fps: float | None = None
        self.samplerate: float | None = None
        self.video_resolution: str | None = None
        self.input_duration: str | None = None

        # get info needed for processing
        self._parse_input()

    def run_command(self, cmd: list[str]) -> Optional[str]:
        """
        Run a command directly.

        Args:
            cmd (list[str]): Command to run

        Returns:
            Optional[str]: Output of the command
        """
        logger.info(" ".join([shlex.quote(c) for c in cmd]))
        if self.dry:
            return None

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            return stdout.decode("utf-8") + stderr.decode("utf-8")
        else:
            raise RuntimeError(
                f"running command: {' '.join(cmd)}: {stderr.decode('utf-8')}"
            )

    def _parse_input(self):
        """
        Parse various info from the input file
        """

        p = subprocess.Popen(
            ["ffmpeg", "-i", self.input_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, stderr = p.communicate()
        output = stderr.decode("utf-8")

        if video_match := re.compile(r"Video: (.*)").search(output):
            self.has_video = True
            video_line = video_match.group(1)
            if fps_match := re.compile(r".*, ([0-9.]+) fps,.*").search(video_line):
                self.fps = float(fps_match.group(1))

            if video_resolution_match := re.compile(r".*, (\d+x\d+)[, ].*").search(
                video_line
            ):
                self.video_resolution = video_resolution_match.group(1)

        if (
            audio_match := re.compile(r"Audio: (.*)").search(output)
        ) and not self.audio_disable:
            self.has_audio = True
            audio_line = audio_match.group(1)
            if hz_match := re.compile(r".*, ([0-9]+) Hz,.*").search(audio_line):
                self.samplerate = float(hz_match.group(1))

        if not (self.has_audio or self.has_video):
            raise RuntimeError("file has no video or audio stream")

        if input_duration_match := re.compile(
            r".* Duration: ([0-9.]+:[0-9.]+:[0-9.]+\.[0-9.]+), .*"
        ).search(output):
            self.input_duration = input_duration_match.group(1)

        if not self.fps:
            raise RuntimeError("Could not detect video fps from input file!")
        if self.has_audio and not self.samplerate:
            raise RuntimeError("Could not detect audio sample rate from input file!")
        if self.has_video and not self.video_resolution:
            raise RuntimeError("Could not detect video resolution from input file!")
        if not self.input_duration:
            raise RuntimeError("Could not detect duration from input file!")

    def _generate_loop_cmds(self):
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

        # trim_cmds are only used for freeze
        trim_cmds = []
        last_buf_end = 0

        for buf_event in self.buflist:
            buf_pos, buf_len = buf_event
            buf_pos_enable = round(total_buf_len + buf_pos, 3)
            buf_len_enable = round(buf_pos_enable + buf_len, 3)

            # FIXME: the enable time is slightly smaller than what one would expect, with video
            buf_len_enable_video = buf_len_enable - 0.001

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

                trim_cmd = f"trim=start_frame={last_buf_end}:end_frame={buf_pos_frames + buf_len_frames},setpts=PTS-STARTPTS"
                trim_cmds.append(trim_cmd)
                last_buf_end = buf_pos_frames + 2 * buf_len_frames

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

        # needs an extra trim at the end to get the end of the file
        if self.fps is None:
            raise RuntimeError("fps not specified!")

        duration_in_frames = (
            int(self._get_duration_in_seconds() * self.fps) + total_vlooped
        )
        trim_cmd = f"trim=start_frame={last_buf_end}:end_frame={duration_in_frames},setpts=PTS-STARTPTS"
        trim_cmds.append(trim_cmd)

        self.vloop_cmd = (",").join(vloop_cmds)
        self.aloop_cmd = (",").join(aloop_cmds)
        self.trim_cmds = trim_cmds
        self.venable_cmd = ("+").join(venable_cmds)
        self.aenable_cmd = ("+").join(aenable_cmds)

    def _set_specs(self):
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
                        "[black][stallvid]scale2ref[black2][stallvid]",
                        f"[stallvid][black2]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1:enable='{self.enable_black_cmd}'[stallvid2]",
                    ]
                )
            else:
                vfilters.append(
                    f"[0:v]{self.vloop_cmd}[stallvid2]",
                )
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

    def trim_video(self):
        """
        Remove frames after the frozen, repeated, ones to emulate freezing with skipping
        """
        trim_extra_frames = [
            "ffmpeg",
            self.overwrite_spec,
        ]

        trim_extra_frames.extend(
            [
                "-i",
                self._get_tmp_filename("video"),
            ]
        )

        vfilters = []
        filter_interface_list = []

        for ii in range(0, len(self.trim_cmds)):
            filter_interface_list.append(f"[i{ii}v]")

        remaining_trim_cmds = list(self.trim_cmds)
        for ii, jj in enumerate(filter_interface_list):
            filter_string = f"[0:v]{remaining_trim_cmds.pop(0)}{jj}"
            vfilters.append(filter_string)
        filters = ";".join(vfilters) + ";"
        filters += "".join(filter_interface_list)
        filters += f"concat=n={len(self.trim_cmds)}:v=1[outv]"

        trim_extra_frames.extend(["-filter_complex", filters])

        trim_extra_frames.extend(["-map", "[outv]"])

        trim_extra_frames.extend(
            [
                "-c:v",
                self.vcodec,
                "-vsync",
                "cfr",
                self._get_tmp_filename("skipping"),
            ]
        )

        self.run_command(trim_extra_frames)

    def merge_audio_video(self):
        """
        Merge the audio and video files
        """
        if self.skipping:
            if self.has_audio and self.has_video:
                output_codec_options = ["-map", "0:v", "-map", "1:a"]
            else:
                output_codec_options = []
            if self.force_framerate:
                output_codec_options.extend(
                    [
                        "-c:v",
                        self.vcodec,
                        "-filter:v",
                        "fps=fps=" + str(self.fps),
                    ]
                )
                if self.has_audio:
                    output_codec_options.extend(
                        [
                            "-c:a",
                            "copy",
                        ]
                    )
            else:
                output_codec_options.extend(["-c", "copy"])

        else:
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
        ]

        if self.has_video:
            if self.skipping:
                combine_cmd.extend(
                    [
                        "-i",
                        self._get_tmp_filename("skipping"),
                    ]
                )
            else:
                combine_cmd.extend(
                    [
                        "-i",
                        self._get_tmp_filename("video"),
                    ]
                )

        if self.has_audio:
            if self.skipping:
                combine_cmd.extend(
                    [
                        "-i",
                        self.input_file,
                    ]
                )
            else:
                combine_cmd.extend(
                    [
                        "-i",
                        self._get_tmp_filename("audio"),
                    ]
                )

        output_duration_options = None
        if self.skipping:
            output_duration_options = ["-t", self.input_duration]
        if self.trim:
            output_duration_options = self.trim_spec

        if output_duration_options:
            combine_cmd.extend([*output_duration_options])

        combine_cmd.extend(
            [
                *output_codec_options,
                self.output_file,
            ]
        )

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

        # if self.trim_spec:
        #     base_cmd.extend(self.trim_spec)

        return base_cmd

    def _get_duration_in_seconds(self):
        """
        Convert between the HH:MM:SS.sss format, to total number of seconds.
        """
        if self.input_duration is None:
            raise RuntimeError("Input duration not specified")
        h, m, s = self.input_duration.split(":")
        time_in_seconds = float(
            datetime.timedelta(
                hours=int(h), minutes=int(m), seconds=float(s)
            ).total_seconds()
        )
        return time_in_seconds

    def _get_tmp_filename(self, what="video"):
        if what not in ["video", "audio", "skipping"]:
            raise RuntimeError("Call _get_tmp_filename with video/audio/freeze!")

        suffix = f"_{what}.nut"

        return self.output_file + suffix

    def insert_buf_audiovisual(self):
        """
        Insert the buffering events on both audio and video tracks, looping the video
        frames and audio samples at the corresponding positions.
        """

        self._generate_loop_cmds()
        self._set_specs()

        tmp_file_list = []

        try:
            if self.has_video:
                logger.info("running command for processing video")
                self.insert_buf_video()
                tmp_file_list.append(self._get_tmp_filename("video"))
            if self.skipping:
                logger.info("running command for trimming video")
                self.trim_video()
                tmp_file_list.append(self._get_tmp_filename("skipping"))
            else:
                if self.has_audio:
                    logger.info("running command for processing audio")
                    self.insert_buf_audio()
                    tmp_file_list.append(self._get_tmp_filename("audio"))
            logger.info("running command for merging video/audio")
            self.merge_audio_video()
        except Exception as e:
            logger.error(f"error running processing: {e}")
        finally:
            if not self.dry:
                for file in tmp_file_list:
                    if os.path.isfile(file):
                        os.remove(file)
                    else:
                        logger.warn(f"temporary file {file} not found!")
