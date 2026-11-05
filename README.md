# Video

A PyGDO connector for rendering video in the background and streaming it to
YouTube, Twitch, or both.

# Video (For Humans)

Use video in two render modes: a layered composite sent to a virtual webcam,
or full-desktop effects for Discord/Slack screen sharing. Video can also be off.
Layers can be switched while running. YouTube and Twitch are planned outputs.

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
  `audio` is an optional Video module friendency; it is not enabled or
  installed automatically.

The Video connector starts the configured worker when Dog connects it;
the default mode is off, so an untouched installation does not capture or
display anything. Keep stream keys out of logs and the repository, and make
stopping straightforward. Desktop and webcam capture may expose private
information; review the intended view and participants' consent before
broadcasting.

## Methods

- `$video.start` starts the compositor with the configured sources and outputs.
- `$video.preview` opens or restarts the virtual-webcam compositor preview
  without restarting Dog or the virtual-camera output. The compositor must be
  running; the command queues a request, not a guarantee of a visible window.
- `$video.layer <desktop|bg_image> <1|0>` enables or disables a composite
  layer while running; disabling desktop releases its capture process.
- `$video.layer overlay <1|0>` shows or hides the desktop image overlay.
- `$video.close <key>` removes an effect such as `media`, `vintage`,
  `starwars`, `asciiart`, `magnify`, or `drawing`; `$video.close --all`
  removes all effects and hides the screensharing logo overlay. Neither stops
  the video worker nor changes its desktop/background input sources. These
  commands queue their work for Dog.
- `$video.draw <prompt>` clears the drawing layer and sends the prompt to Mira
  to draw live. Mira adds lines one by one using `$video.stroke x1 y1 x2 y2`;
  coordinates are percentages (0–100), with optional `--color=#RRGGBB` and
  `--width` as a percentage of the smaller frame dimension. `$video.draw off`
  clears the drawing. Both methods are owner-only and queue work through Dog;
  drawing requires a running video worker and the Mira delivery bridge. A
  queued reply does not guarantee the agent has drawn yet. The request is
  interpreted as drawing content, not permission for unrelated actions.
- `$video.vintage <1|0>` enables or disables the keyed vintage layer: randomly
  varying vertical scratches and gentle flicker in both video modes. It is
  queued for Dog; flicker can affect viewers sensitive to flashing.
- `$video.media <url>` displays an image or a silent video, with `--width`, `--height`, `--x`
  and `--y` accepting CSS `px` or `%`. Defaults are `25%` × `25%`, at `2%`,
  `2%` from the top left. The image preserves its proportions within that box;
  file, HTTP and HTTPS URLs are supported (images up to 4 MiB, videos up to
  32 MiB). Video plays once without sound, for at most 5 minutes. New media replaces
  the `media` layer; `$video.media off` removes it. Loading is queued for Dog;
  only show media and URLs appropriate for the audience.
- `$video.magnify <1|0> [--zoom=2] [--radius=90]` toggles a mouse-following
  lens in virtual-webcam mode. It requires an enabled X11 desktop source;
  the radius is in composite pixels. Screensharing magnification is TODO.
  The request is queued and does not confirm that the worker accepted it.

#### Testing the magnifier on X11

Install and enable the Video module and connector in the intended PyGDO
instance. In its module configuration set `video_mode` to `virtualwebcam`,
`video_desktop_url` to the X11 display to capture (for example `:0.0`), and
enable `video_output_preview` and/or `video_live`. Set `video_output_device`
to the virtual camera when using live output. The Dog process needs access to
the chosen X11 display and output device. Start the connector after changing
these settings; the desktop layer starts enabled when its URL is configured.

For the isolated Test Dog, once configured and started:

```sh
pygdotest '$video.magnify 1 --zoom=2 --radius=90'
pygdotest '$video.magnify 0'
```

The desktop source may contain private information and can be visible to
applications consuming the virtual camera. Previewing it on that same desktop
can also create visual recursion. The lens requires the desktop layer to be on;
turning that layer off removes the lens. The X11 implementation maps pointer
coordinates onto the scaled desktop frame. Screensharing support is TODO.
- `$video.asciiart [duration]` applies a timed full-frame ASCII filter to the
  virtual-webcam composite (default 5 seconds, maximum 5 minutes). Configure
  the desktop source if the desktop itself should be transformed. The command
  queues the effect for Dog. Screensharing and rectangle selection are TODO.
  `$video.asciiart 5s --flash` alternates the filtered and original image;
  this flickers and may affect viewers sensitive to flashing.
- `$starwars <text>` (also `$video.starwars`) queues a timed, upward-scrolling text effect in the
  active composite or desktop-overlay mode. A new invocation replaces the
  previous text. Nested GDO commands can supply the text, for example
  `$video.starwars $(wget file:///absolute/path/message.txt)`. Local `wget`
  reads are restricted to authenticated owners and UTF-8 regular files of at
  most 16 KiB; the effect accepts up to 4096 characters, subject to the IPC
  payload size limit. Dog must be running with an active video worker; a queued
  response does not confirm that the effect was displayed. Treat displayed text
  as public when a screen or virtual webcam is being shared.
  A short AI-to-human demo inspired by The Mentor's Hacker Manifesto is in
  `gdo/video/demo/mentor.txt`.
- Effect layers are identified by key. A new key is placed above existing
  effects by default; updating a key keeps its position, and an explicit
  integer z-index controls order (equal values retain insertion order). In the
  virtual-webcam worker, plugins can call `put_effect(key, effect, z=None)`
  and `remove_effect(key)`; effects draw on the frame and return false when
  finished. Starwars uses the key `starwars`. Screensharing currently uses the
  same ordering for its text effects, while the image overlay remains a
  separate window and cannot yet be reordered with them.
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
- `virtualwebcam`: optional layers → compositor → preview and/or virtual webcam.
- `screensharing`: show the overlay image and render effects over the full X11
  desktop in a transparent, click-through window for desktop sharing. The
  composite background image (`video_bg_image_url`) is not used in this mode;
  the separately configured `video_overlay_image_url` is an overlay.

Desktop overlays currently require X11, a compositing window manager, and
system Python with GTK 3, PyGObject and Cairo. `video_overlay_image_url`
selects a local image (the bundled ITMB logo by default). The initial overlay
is an always-on-top, click-through window in the upper right; it does not
capture the screen or open a virtual webcam. Mira and speech overlays are TODO.
The screensharing effect covers the X11 screen, including a multi-monitor
desktop where the X11 screen spans multiple monitors; application-window sharing
may omit the overlay. Test the actual sharing application and chosen source.

Composite sources:

- `video_desktop_url`: capture a display or window. X11 can use a display
  such as `:0.0`; Wayland normally needs a screen-sharing portal and consent.
- `video_bg_image_url`: a local background image path or `file:///` URL.
- `video_file_url`: decode a local video file, for example
  `file:///absolute/path/video.mp4`. Network URLs need a separate safety design.
- `video_webcam_url`: capture a camera device, for example `file:///dev/video0`.

You can leave any source empty. `video_output_preview` shows the composite in a
small local corner window; `video_live` sends that same composite to
`video_output_device`. `video_preview_w` and `video_preview_h` set the preview
window size in pixels (default 320 × 180), independently of output resolution.
Both outputs default to off. Enable at least one before
`video.start` or before starting the Video connector, and select `virtualwebcam`;
mode and output settings are read
at start. The bundled ITMB logo is the default background. Background images fill
the composite while preserving their proportions; excess edges may be cropped. A
configured desktop covers the background until its layer is disabled. Previewing
the captured desktop can
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
