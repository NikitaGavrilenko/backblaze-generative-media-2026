# ProofStudio demo video

`proofstudio-demo.mp4` is a 94-second, 1280x720 walkthrough of the deployed
ProofStudio application with English narration and burned-in English captions.
It uses screenshots captured from the public production deployment and the
verified public run documented in `SUBMISSION.md`.

The separate `proofstudio-demo-en.srt` file contains the same captions for video
platforms that support selectable subtitles. Captions are also burned into the
MP4 so the walkthrough remains understandable when playback is muted.

To rebuild the video after replacing screenshots in `frames/`:

```powershell
python scripts/build_demo_video.py
```

The script requires Pillow, FFmpeg, Windows PowerShell, and an installed English
Windows SAPI voice. Generated encoding intermediates are ignored by Git.
