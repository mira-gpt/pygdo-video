# Video

A PyGDO connector for rendering video in the background and streaming it to
YouTube, Twitch, or both.

# Video (For Humans)

Choose a desktop, webcam, or video as input, then stream to the destinations
you select. This project is an idea; streaming is not implemented yet.

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

Streaming must not start automatically merely because Dog or the module starts.
Show the selected sources and destinations before starting, keep stream keys
out of logs and the repository, and make stopping straightforward. Desktop and
webcam capture may expose private information; review the intended view and
participants' consent before broadcasting.

## Methods

To be designed: configure sources and outputs, start, stop and inspect status.

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

The planned path is three optional inputs → compositor → virtual webcam:

- `video_desktop_url`: capture a display or window. X11 can use a display
  such as `:0.0`; Wayland normally needs a screen-sharing portal and consent.
- `video_file_url`: decode a local video file, for example
  `file:///absolute/path/video.mp4`. Network URLs need a separate safety design.
- `video_webcam_url`: capture a camera device, for example `file:///dev/video0`.

You can leave any source empty. In the intended design, configured sources can
be combined; layout and switching controls still need to be built. The virtual
webcam output is configured separately with `video_output_device`.

**Current test status:** the settings exist, but the multi-input compositor and
webcam capture do not. `video.start` deliberately refuses to start; no picture
can yet be tested through this module. The unfinished single-input FFmpeg
prototype is not connected to `video.start`. A virtual video device is also
required, and none was present when last checked.

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
