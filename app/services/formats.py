from app.models.download import Options

VIDEO_FORMATS = ["Auto", "MP4", "WEBM", "MKV"]
AUDIO_FORMATS = ["Original / Best Audio", "MP3", "WAV", "M4A", "OPUS", "FLAC"]
RESOLUTIONS = [2160, 1440, 1080, 720, 480, 360]


def resolutions(info: dict, container: str) -> list[str]:
    formats = info.get("formats", [])
    heights = set()
    for fmt in formats:
        if not fmt.get("height") or fmt.get("vcodec") == "none":
            continue
        if container == "WEBM" and fmt.get("ext") != "webm":
            continue
        heights.add(int(fmt["height"]))
    return ["Best"] + [f"{height}p" for height in RESOLUTIONS if height in heights or not formats]


def format_selector(options: Options) -> str:
    vc = {"H.264": "[vcodec^=avc]", "VP9": "[vcodec^=vp9]", "AV1": "[vcodec^=av01]"}.get(options.video_codec, "")
    ac = {"AAC": "[acodec^=mp4a]", "Opus": "[acodec^=opus]"}.get(options.audio_codec, "")
    if options.mode == "Audio":
        return f"bestaudio{ac}/best{ac}"
    limit = "" if options.quality == "Best" else f"[height<={int(options.quality.rstrip('p'))}]"
    if vc or ac:
        return f"bv{limit}{vc}+ba{ac}/b{limit}{vc}{ac}"
    if options.container == "MP4":
        return f"bv{limit}[vcodec^=avc1]+ba[ext=m4a]/b{limit}[ext=mp4]/bv{limit}+ba/b{limit}"
    if options.container == "WEBM":
        return f"bv{limit}[ext=webm]+ba[ext=webm]/b{limit}[ext=webm]/bv{limit}+ba/b{limit}"
    return f"bv{limit}+ba/b{limit}"


def postprocess_args(options: Options) -> list[str]:
    args = []
    if options.mode == "Audio":
        args += ["-x", "--audio-format", "best" if options.container == AUDIO_FORMATS[0] else options.container.lower()]
        if options.container == "MP3":
            args += ["--audio-quality", "0" if options.quality == "Best" else options.quality.split()[0] + "K"]
        if options.metadata:
            args += ["--embed-metadata", "--parse-metadata", "%(artist,creator,uploader)s:%(meta_artist)s"]
        if options.thumbnail and options.container in {"MP3", "M4A", "FLAC", "OPUS", AUDIO_FORMATS[0]}:
            args += ["--embed-thumbnail", "--convert-thumbnails", "jpg"]
    else:
        if options.container == "Auto":
            args += ["--merge-output-format", "mkv"]
        elif options.container == "WEBM":
            args += ["--merge-output-format", "webm/mkv", "--recode-video", "webm"]
        else:
            args += ["--merge-output-format", options.container.lower(), "--remux-video", options.container.lower()]
        if options.metadata:
            args += ["--embed-metadata"]
        if options.subtitle:
            args += ["--write-auto-subs" if options.auto_subtitle else "--write-subs", "--sub-langs", options.subtitle, "--convert-subs", "srt"]
            if options.subtitle_mode == "Embed into video":
                args += ["--embed-subs"]
    return args
