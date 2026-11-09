# Video

A PyGDO connector for rendering video in the background and streaming it to
YouTube, Twitch, or both.

# Video (For Humans)

Use video in two render modes: a layered composite sent to a virtual webcam,
or full-desktop effects for Discord/Slack screen sharing. In screensharing mode,
optionally send the same overlaid X11 desktop to a virtual camera as well by
setting `video_live` to 1, `video_desktop_url` to the desktop display, and
`video_output_device` to a configured loopback device. Video can also be off.
The virtual camera carries video only; route audio separately. Previewing the
camera on the captured desktop can create a visual feedback loop. Verify the
capture in a private test before broadcasting; a running device is not proof
that the overlay or stream is visible to viewers.
The `pygdo_tes.toml` and `config_test.toml` test configurations cannot write
to a virtual camera, even if `video_live` is enabled; use screen sharing or a
local compositor preview for tests.
Layers can be switched while running. YouTube and Twitch are planned outputs.

`$cheese` (also `$video.screenshot`) lets an admin capture the configured
local X11 desktop and publishes a PNG under `gdo/mira/public`, returning its
URL. The whole desktop may contain passwords or other private information;
check the screen before using this command. The returned image is public.

The upper-left live-mode indicator shows `off`, `work`, `show`, or `discuss`.
It is black normally and red when the existing microphone meter reports
nonzero input. It does not start microphone capture; black can also mean the
meter is unavailable, not necessarily that the microphone is muted.

# Video (For ALs)

## Architecture draft

### Live 3D duck: target (not implemented yet)

The duck is a live-rendered, transparent 3D overlay in both screensharing and
virtual-webcam modes. It always has a looping animation: `idle` gently rocks
and blinks; `quacking` waddles and hops. `$duck.anim <key>` switches the active
animation quickly, without rebuilding or restarting the renderer. Animations
are authored in the project, loaded ahead of time, and can be selected by Mira.
Idle is the default; a selection remains active until changed. Speech controls
the beak independently of the body animation. Both outputs use the same model,
animation state and transparent rendered result; shutdown and failures must not
break the video worker. Initial testing is isolated to Test Dog.

Development status: the experimental offscreen renderer has been visually
tried in Test Dog's screensharing mode. The virtual-webcam adapter has isolated
tests, but still needs a live camera/stream test.
Optional dependencies are listed in `requirements-duck3d.txt`; installing them
does not activate the renderer. The current model has a beak rig; body and eye
motion are procedural pending authored animation clips.

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

## Installing the virtual camera

For a test instance, follow the module checkout/install steps in the Audio
README and verify the provider and branch before installation. Video's
`gdo_install` creates its Video connector server if one does not already exist;
check the configured server and ensure the connector is enabled in the intended
Dog. Do not create duplicates. The default `video_mode=off` captures nothing.

Install FFmpeg/FFplay, Pillow in the Dog interpreter and the distribution's
`v4l2loopback` package matching the running kernel. X11 access is required for
desktop capture. The transparent desktop-sharing mode instead requires an X11
compositor, GTK 3/PyGObject and Cairo; it does not need a virtual camera.

Inspect existing cameras first (`ls -l /dev/video*` and, if installed,
`v4l2-ctl --list-devices`). If no suitable loopback is already loaded, choose
an unused number and have an administrator explicitly create it, for example:

```sh
sudo modprobe v4l2loopback video_nr=2 card_label="Mira Video" exclusive_caps=1
```

This affects the host, not just Test Dog. If the kernel module is already
loaded, do not unload it while another app uses it; `modprobe` with new options
does not necessarily add a device. With `exclusive_caps=1`, a receiving app may
only see the camera after a producer has started. Check device permissions and
that the path is the virtual device, not a physical camera. See the
[v4l2loopback documentation](https://github.com/v4l2loopback/v4l2loopback/blob/main/README.md).

For the isolated Test Dog, an owner/admin can configure an X11 desktop composite
with a local preview and virtual output, replacing the display and device with
the actual values:

```sh
pygdotest '$admin.conf video video_mode virtualwebcam'
pygdotest '$admin.conf video video_desktop_url :0.0'
pygdotest '$admin.conf video video_output_device /dev/video2'
pygdotest '$admin.conf video video_output_preview 1'
pygdotest '$admin.conf video video_live 1'
```

Review the desktop for private content before capture. Start/restart only the
intended Test Dog or its Video connector after configuration. Then inspect the
local preview and select `Mira Video` in a receiving app; verify the actual
image there. A queued command or visible device is not proof of a working
stream. `pygdotest '$video.stop'` stops the worker; the kernel device itself
remains until reboot or an explicitly managed module removal. `video_live=0`
with preview enabled is useful when no camera output is desired.

## Methods

`$duck.welcome <nickname>` waves and speaks one of three greetings in the
channel language (currently German or English). Automatic join greetings are
off by default and require a per-channel opt-in. In the desired channel, staff
can enable them with `$confc video.welcome video_welcome_enabled 1` and disable
them with `$confc video.welcome video_welcome_enabled 0`. Manual welcomes do
not require this opt-in. Actual channel-join events trigger a welcome only
when opted in and `mira_livemode` is `show`, with an eight-second
global cooldown; unsupported languages and bot/system accounts are skipped.
Join snapshots are not welcomed. This can expose nicknames on the show; only
enable live-show mode when that is intended. No stream or microphone is started.

`$live` (also `$video.liveshow`) reports the effective mode without confirming
whether a stream is broadcasting. `$live off|work|show|discuss` selects
`mira_livemode`; the old `$live 0|1` forms mean `off|show`. An old
`mira_quacking` setting remains the fallback until a new mode is saved.
Selecting `show` requests the 3D duck and microphone meter overlays on; other
modes request them off. `work` and `discuss` do not themselves control music or
microphone routing. The video connector must already be running; the requests
do not start capture or guarantee the overlays are visible.
When the microphone meter is visible, a red border marks the enabled mode in
both video outputs. It does not start or prove a stream or microphone capture;
when the meter is hidden no border is visible.

- `$video.start` starts the compositor with the configured sources and outputs.
- `$video.preview` opens or restarts the virtual-webcam compositor preview
  without restarting Dog or the virtual-camera output. The compositor must be
  running; the command queues a request, not a guarantee of a visible window.
- `$video.mic 1` shows the local Dog microphone input level in both
  video modes; `$video.mic 0` hides it. It uses the existing
  audio capture, does not start capture and says UNKNOWN when samples are stale.
  The compact meter shows the latest recognized text, or `----` when
  transcription is disabled. Long text scrolls; viewers of the output can see it.
  OFF describes Dog's input monitoring, not other applications or hardware mute. The
  screensharing overlay shares the same level data.
- `$video.duck 1` shows Mira's duck in either video mode. While `$spk` speech
  plays, it animates the beak and displays the spoken text as a caption;
  `$video.duck 0` removes both. This exposes spoken text to viewers whenever the
  output is shared; it does not expose unrelated terminal responses. The
  character uses pre-rendered poses of the included rigged 3D model, not a
  live 3D renderer or phoneme-accurate lip sync.
- `$video.ducktext <text>` explicitly shows a short caption for eight seconds
  with the enabled duck, without starting speech. It is visible to viewers;
  Codex responses are not published automatically. Maximum 250 characters.
- `$video.duck3d 1` requests the experimental live 3D duck; `$video.duck3d 0`
  removes it and stops its renderer. `$duck.anim <key>` requests an
  animation change. Both use Dog IPC and require
  the optional 3D dependencies and a working graphics display. A queued reply
  does not confirm that the renderer started or appeared on stream.
  With an audio module that emits speech envelopes, the beak approximately
  follows synthesized audio energy and pauses; this is not phoneme-level lip
  sync. Older audio modules retain the simple speaking animation.
  `lol` makes the duck hop excitedly and flap its wings.
  `goth` adds an exaggerated dark outfit, eye makeup and a smoking cigarette;
  `cheers` raises a randomly chosen whiskey glass, beer bottle or wine glass,
  with gently sloshing liquid. `bday` adds a party hat, an intermittently unrolling party blower and a
  birthday cake with 46 flickering candles.
  `$duck.anim --base=1 <key> [text]` saves any animation as the persistent
  `mira_mood`; `--base=0` plays any animation temporarily and then restores the
  current base. Optional speech is supported in either case. Without `--base`,
  the per-key defaults in `DuckAnimations.BASE_DEFAULTS` apply:

  - Persistent by default: `idle`, `quacking`, `sad`, `high`, `music`, `tipsy`,
    `drunk`, `embarrassed`, `angry`, `inlove`, `trip`, `tired`, `shrug`, `plz`,
    `teacher`, `xd`, `sorry`, `nerd`, `zombie`, `giveup`.
  - Temporary by default: `lol`, `cry`, `ouch`, `hello`, `rolleye`, `barf`, `cast`.

  Persistent animations require the Mira module. `$duck.lol` remains a
  temporary event.
- `$duck.event <key>` plays `idle`, `quacking`, `lol`, or `shrug` for two seconds, then
  restores the current `mira_mood` (`idle` if Mira is unavailable). A new event
  immediately replaces the previous event and its timer. A mood change during an
  event updates the base to restore without cutting the event short. The event
  is queued; it requires an already active live 3D duck and does not start one.
  A `lol` event changes a `sad` base mood to `idle`.
- `$duck.anim ouch` plays a short pain reaction with alternating feet and comic
  marks, then restores the current base mood. A newer event replaces it.
- `$duck.anim hello` waves one wing quickly using weighted base and tip joints,
  then restores the current base mood using the same smooth transition.
- `$duck.anim rolleye [--lang=de|en] [text]` briefly rolls the eyes, optionally
  speaking the provided text, then returns to the current base mood.
- `$duck.shrug [--lang=de|en] [text]` plays the surprise animation; optional
  text is spoken using the user's language by default, and the saved mood is
  restored after speech. Without text it is a two-second silent event.
- `$duck.cry [--lang=de|en] [text]` cries with optional speech and sets the
  persistent base mood to `sad`. Without text, the crying event lasts two seconds.
- `$duck.lol <text>` selects `LOL`, speaks the text using the configured Audio
  voice, and returns to the current saved `mira_mood` when playback finishes or
  fails (or `idle` if Mira is not installed). If the previous base was `sad`,
  it changes the saved base to `idle`. It uses the user's language by default
  (then channel, server, or English when unset);
  pass `--lang=en` or `--lang=de` to override.
  Audio with the `speech_language` helper (currently on Audio's
  `feature/pcm-io` branch) and the live 3D duck must be enabled. The request is
  queued, not proof of audible playback or visible animation.
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

To prepare the current Dog for a desktop-share overlay, select the mode and
start its connector:

```text
$conf video video_mode screensharing
$video.start
$video.status
```

This does not start screen sharing in Discord or another application: select
the intended desktop there and confirm the overlay is visible to viewers.
`$video.stop` stops the video connector. Use the isolated Test Dog for tests
and verify the destination before sending commands to a live instance.

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
- `$video.mic_ticker <text>` (alias `$mic.ticker`) queues a single-line,
  maximum 300-character message through the shared microphone ticker IPC.
  It is owner-only; modules can call `queue_ticker(text)`, which defers IPC
  until commit when needed. The queue is bounded and not restart-persistent;
  queueing IPC does not guarantee on-screen playback. An entry advances only
  when the renderer confirms that the measured text has completely scrolled
  out; time without rendering does not consume its display duration.
