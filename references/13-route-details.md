# Route details: browser and GPU, AI styling, audio mapping

Read on demand from [skills/fractalwright/SKILL.md](../skills/fractalwright/SKILL.md): the browser section when a render uses `--route browser` or `--deep` on the GPU, the AI section when the user asks for `--ai`, the audio section when tuning or explaining `FW audio`. Moved out of SKILL.md in 0.3.1 so plain renders do not pay for it.

## Browser route and GPU perturbation

`FW render <recipe> --route browser` renders with headless Edge and the page's shader; views too deep for float32 (width under 1e-3 of the coordinate, or a pixel under 1e-6 of it) go to GPU perturbation when the formula is Mandelbrot or Julia (power 2), else to NumPy with a note. `--deep --route browser` (or any width under 1e-12) runs perturbation on the GPU: a Decimal reference orbit as a float texture, float32 scaled deltas, rebasing, down to width 1e-60; about 9% of escape counts in dense boundary areas differ from the float64 CPU route (float32 noise, no blobs), so use the CPU route when exact counts matter. `FW zoom ... --route browser` renders every frame that way. The burning ship is the least exact in float32 (mean diff 2.7 against NumPy).

## AI styling pass (`--ai`)

AI styling is off by default (Mark preferred the exact zoom, 2026-11-14); `--ai` turns it on for zoom, morph, loop and audio: when a ComfyUI host in `FW_COMFY_HOSTS` answers (default loopback 8188, 8199), `scripts/fw_ai.py` runs Z-Image Turbo img2img (Apache 2.0) on every exact frame at denoise 0.3 with one fixed seed, smooths the added texture in time (EMA over styled minus exact), and writes `<out>_ai.mp4`, `<out>_ai_frames/` and `<out>_ai.json` marked `interpreted` (model, licence, denoise, seed, flicker). The exact frames and video are always kept. No host: exact only, with a note; a host error: `ai_pass.status: failed`, exact kept. A busy GPU is waited on in its queue (`FW_AI_TIMEOUT_S`, default 1800). Never Krea 2 or Meta-gated models.

## Audio mapping (`FW audio`)

Envelopes come from musicwright's `mw.py envelopes` (critical bands, 200 ms loudness, onsets, beats, chroma), else a built-in NumPy fallback, noted in the recipe. Bass swells julia `c` and pulses the zoom, beats kick it (at most about 3 a second), mids drift the colour, chroma sets the hue, treble the palette density, loudness drives mandel-dive's zoom travel; nothing moves in silence. Frames are stepped at n/fps through a flash limiter, flashcheck gates the result (exit 4 on a fail), and the song is muxed with ffmpeg cut to the frame count. `FW serve` also serves `/audio`, a live page (file or microphone, Web Audio analyser, same mappings, a JS flash limiter, a photosensitivity warning first). Theory and the flash rules: [09-audio-visuals.md](09-audio-visuals.md).
