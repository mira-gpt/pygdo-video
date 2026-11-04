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

Which input and destination should be the first working prototype?

## Ideas

- Animated duck/avatar overlay, with modes such as work or brainstorm.
- Combine microphone and optional generated speech with the video.
- Per-destination health, reconnect policy and explicit failure reporting.
