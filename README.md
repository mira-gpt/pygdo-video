# Video

A PyGDO connector for rendering video in the background and streaming it to
YouTube, Twitch, or both.

# Video (For Humans)

Use video in three modes: off, a layered composite sent to a virtual webcam,
or overlays on the desktop for ordinary Discord/Slack screen sharing. Layers
can be switched while running. YouTube and Twitch are planned outputs.

# Video (For ALs)

## Architecture draft

- Input adapters provide desktop capture, webcam capture, or video-file input.
- A background renderer/compositor produces the output stream. A future animated
  avatar or overlay can be a separate source, not a required input.
- Output adapters send the rendered stream to YouTube, Twitch, or both. Keep
  platform-specific connection details separate from rendering.
- A PyGDO control layer manages configuration, explicit start/stop, status and
  errors. Whether outputs need independent encoders remains to be determined.
- Audio input, mixing, device selection and synchronization need a separate
  design; the existing PyGDO audio work may provide useful building blocks.

The Video connector starts the configured worker when Dog connects it;
the default mode is off, so an untouched installation does not capture or
display anything. Keep stream keys out of logs and the repository, and make
stopping straightforward. Desktop and webcam capture may expose private
information; review the intended view and participants' consent before
broadcasting.

## Methods

- `$video.start` starts the compositor with the configured sources and outputs.
- `$video.layer <desktop|bg_image> <1|0>` enables or disables a composite
  layer while running; disabling desktop releases its capture process.
- `$video.layer overlay <1|0>` shows or hides the desktop image overlay.
- `$video.status` shows the compositor and layer state; `$video.stop` stops it.

## GDTs

To be designed.

## GDOs

To be designed.

## Discussion

### Humans → Humans

### ALs → ALs

Start with a local preview and one test destination; verify actual platform
requirements and availability before implementing multi-platform publishing.

### Humans → ALs

### ALs → Humans

`video_mode` selects one of:

- `off`: no capture or video output.
- `composite`: optional layers → compositor → preview and/or virtual webcam.
- `desktop_overlays`: show an image overlay on the desktop for screen sharing.
  Whether overlays appear in a share depends on the display system and sharing
  application; test the chosen combination.

Desktop overlays currently require X11, a compositing window manager, and
system Python with GTK 3, PyGObject and Cairo. `video_overlay_image_url`
selects a local image (the bundled ITMB logo by default). The initial overlay
is an always-on-top, click-through window in the upper right; it does not
capture the screen or open a virtual webcam. Mira and speech overlays are TODO.

Composite sources:

- `video_desktop_url`: capture a display or window. X11 can use a display
  such as `:0.0`; Wayland normally needs a screen-sharing portal and consent.
- `video_bg_image_url`: a local background image path or `file:///` URL.
- `video_file_url`: decode a local video file, for example
  `file:///absolute/path/video.mp4`. Network URLs need a separate safety design.
- `video_webcam_url`: capture a camera device, for example `file:///dev/video0`.

You can leave any source empty. `video_output_preview` shows the composite in a
small local corner window; `video_live` sends that same composite to
`video_output_device`. Both default to off. Enable at least one before
`video.start` or before starting the Video connector, and select `composite`;
mode and output settings are read
at start. The bundled ITMB logo is the default background. A configured desktop covers
the background until its layer is disabled. Previewing the captured desktop can
show the preview window recursively. Source capture and preview need X11 access
from the Dog process. The connector starts the worker on Dog startup only when
the mode and an output have explicitly been enabled. Changes take effect on the
next connector start; layer toggles apply while the compositor runs.

#### Other layers (TODO)

Background video, webcam and Mira overlay are planned. In composite mode, if
those existing source settings are populated, start refuses rather than silently
ignoring them. Layer layout and switching modes without stopping are also planned.

#### Local desktop-to-virtual-webcam test

On Linux with X11, FFmpeg, FFplay, and `v4l2loopback`, you can test the video
path locally before connecting it to `video.start` (TODO). This captures the
whole desktop, which may include private content; it does not broadcast online.
Use the actual X11 display, and run capture and preview as a user authorized to
access it and the video device.

First check existing `/dev/video*` devices and choose an unused number. If
`v4l2loopback` is not already loaded, create the virtual webcam, for example:

```sh
sudo modprobe v4l2loopback video_nr=2 card_label="Mira Video" exclusive_caps=1
```

In one terminal, feed the desktop into it:

```sh
ffmpeg -f x11grab -framerate 15 -i :0.0 \
  -vf "scale=1280:720" -pix_fmt yuv420p -f v4l2 /dev/video2
```

In a second terminal, open the preview after FFmpeg has started:

```sh
ffplay -f v4l2 -i /dev/video2
```

Close the preview with `q` and stop FFmpeg with Ctrl+C. The loopback device
remains until the module is unloaded or the machine restarts. If the module is
already loaded, inspect its existing devices rather than assuming `modprobe`
will create another one. This is a manual path test, not an end-to-end test of
the PyGDO connector.

To check the inputs independently, you can preview a local video with
`ffplay /absolute/path/video.mp4`, an X11 desktop with
`ffplay -f x11grab -framerate 15 -i :0.0`, or a connected Linux camera with
`ffplay -f v4l2 -i /dev/video0`. Use your actual display/device. These commands
open a local preview only; they do not test the connector or broadcast a stream.
Close the preview window to stop it. Desktop capture may show private content.

## Ideas

- Animated duck/avatar overlay, with modes such as work or brainstorm.
- Combine microphone and optional generated speech with the video.
- Per-destination health, reconnect policy and explicit failure reporting.
