# 09 Audio visuals: AVS, MilkDrop, analysis pipeline, flash limits

Research note for fractalwright's `audio` command (offline, frame-stepped song-to-fractal video) and the live page (file or microphone in the browser). Accessed 2026-11-14 unless marked. Sources are numbered [S#] and listed at the end. Lines marked "(not fetched)" come from well-known documentation that was not re-read this session; check them before quoting them as fact.

## 1. History in one page

- **Winamp AVS (Advanced Visualization Studio)**, Nullsoft, late 1990s to 2000s. A preset is a tree of "render" and "trans" components (oscilloscopes, spectrum bars, dot fields, movement, blur, colour fade, dynamic movement, effect lists with blend modes). The scriptable parts (Dynamic Movement, SuperScope, Color Modifier) use EEL expressions run per frame, per beat and per point. Announced as open source on 2005-05-18 under a BSD-style licence [S1]. Maintained forks: grandchild/vis_avs (BSD-3, MinGW and MSVC port) [S2], visbot/vis_avs (original readme, "Copyright 2005 Nullsoft") [S3].
- **Winamp's 2024 Legacy Player source** is a separate release under the Winamp Collaborative License, which forbids distributing modified versions. It does not govern the 2005 AVS code [S1][S4].
- **Geiss** (Ryan Geiss, 1998 onwards): a feedback-warp visualiser and screensaver. Its idea (feed the previous frame back through a warp, darken, add the waveform) became MilkDrop's core [S5]. Licence of Geiss code: not established (open question).
- **MilkDrop** (Ryan Geiss, 2001; MilkDrop 2 2007): per-frame and per-vertex equations driving a warped feedback buffer, then pixel shaders. MilkDrop 1.04 source BSD May 2005; MilkDrop 2.25c source BSD 2013-05-13 on SourceForge [S6][S7]. Wikipedia lists 2.25d as source-available after Winamp's 2024 change (unverified at a primary source) [S6].
- **projectM**: cross-platform reimplementation of MilkDrop. Core library LGPL-2.1; ships no presets itself [S8].
- **Butterchurn**: MilkDrop in WebGL 2, MIT; presets converted to JavaScript in the separate butterchurn-presets package (repository listed as MIT) [S9][S10]. API: `butterchurn.createVisualizer(audioContext, canvas, {width, height})`, `connectAudio(node)`, `loadPreset(preset, blendSeconds)`, `render()` [S9].

## 2. MilkDrop model summary

From Geiss's preset authoring guide [S5].

The frame loop:

1. Read audio: `bass`, `mid`, `treb` are current band levels where 1.0 is "normal", below about 0.7 quiet, above about 1.3 loud. `bass_att`, `mid_att`, `treb_att` are slower smoothed versions. MilkDrop divides each band's current energy by its own running average (this ratio is why 1 is normal), so the values are self-normalising across quiet and loud songs (mechanism from the source, not the guide text; open question 3). Names `frame`, `time`, `fps`, `bass`, `bass_att`, `mid`, `mid_att`, `treb`, `treb_att` (plus meshx/y, aspectx/y, pixelsx/y) are the per-frame globals in Butterchurn https://github.com/jberg/butterchurn/blob/master/src/rendering/renderer.js (accessed 2026-11-14); `zoom`, `rot`, `warp`, `decay` are per-frame preset outputs there and `q1..q32` are handed on separately.
2. **Per-frame equations** run once: set zoom, rot, warp amount, cx/cy, dx/dy, sx/sy, decay, wave colour, etc. Up to 30 custom variables; `q1..q32` carry values on to per-vertex code, shaders, custom waves and shapes for that frame only. Values set in init code are the defaults restored each frame.
3. **Per-vertex equations** run on a coarse mesh (meshx 8 to 128 or 192, meshy 6 to 96 or 144 by the guide's two tables), with `x`, `y`, `rad`, `ang` in scope; the resulting UV offsets are interpolated across pixels. There is no per-pixel equation language: per-pixel work lives in shaders.
4. **Warp shader** (MilkDrop 2): runs over the internal canvas and writes back to it, so its result feeds the next frame. Gets warped `uv` and undistorted `uv_orig`. Usual job: darken (decay) and motion.
5. Draw on top of the feedback buffer: built-in waveform (8 `wave_mode`s), up to 4 custom waves (0 to 512 samples each, per-point code), up to 4 custom shapes (3 to 100 sides, up to 1024 instances each, may be textured with the previous frame), motion vectors (`mv_x` 0-64, `mv_y` 0-48, length, colour).
6. **Composite shader**: draws the buffer to the screen only; never feeds back. Usual job: brightness, colour, symmetry, hue.
7. Preset transitions blend two presets over a set number of seconds.

**Preset `.milk` format** (not fetched this session; check against a real file): an INI-like text file, `[preset00]` section, `key=value` lines for base values (`zoom=1.0`, `fDecay=0.98`, `nWaveMode=...`), then numbered code lines `per_frame_1=...`, `per_pixel_1=...` (the per-vertex code keeps the old name "per_pixel"), `per_frame_init_1=...`, `wave_0_per_point1=...`, `shape_0_per_frame1=...`, and shader bodies as `warp_1=`...`comp_1=` lines quoted with a leading backtick.

Why it matters for fractalwright: the MilkDrop recipe is "persistent image + warp field + audio-modulated parameters + decay". A fractal renderer can borrow the parameter side (bands with running-average normalisation, `_att` smoothing, q-variable hand-off) without the feedback buffer, or add feedback as an optional "trails" pass.

## 3. Analysis pipeline recommendations (with numbers)

Defaults below are fractalwright's proposed values; the reasoning cites the tools they follow.

### 3.1 Offline (`audio` command)

| Stage | Recommendation | Why |
|---|---|---|
| Decode | mono mix, resample to 44.1 or 48 kHz float | standard; keep original sample rate for timing |
| Frame clock | video fps drives everything: analysis hop = sr / fps rounded, or analyse at a finer hop (512 at 44.1 kHz = 11.6 ms) and sample at each frame's centre time | frame-stepped rendering must look up features by time t = n / fps, never by real-time clock |
| Window | Hann (periodic) | librosa's default `window='hann'` (not fetched); Web Audio uses Blackman [S11] |
| FFT size | 2048 at 44.1 kHz (46 ms, 21.5 Hz bins) for bands; 4096 if sub-bass separation (40 vs 60 Hz) matters | librosa default `n_fft=2048` (not fetched); same as AnalyserNode default [S11] |
| Hop | 512 (11.6 ms) for onset/beat; per-frame sampling for visuals | librosa default `hop_length=512` (not fetched) |
| Band map | log-spaced or mel bands; 3 "MilkDrop" bands (bass 20-250 Hz, mid 250-4000 Hz, treb 4-16 kHz, our choice) plus 16-32 log bands for detail | perception is roughly logarithmic in frequency; linear bins waste the top half on air |
| Level | power to dB, or power^0.3 compression | avoids a few loud bins dominating |
| Normalisation | per-band ratio to its own running average (MilkDrop style, window about 1-4 s) for "reaction"; plus global song-level percentile normalisation (map 5th-95th percentile to 0-1) for "intensity" | offline we can see the whole song, so percentiles beat an AGC that pumps |
| Smoothing | one-pole attack/release per band: attack 10-30 ms, release 150-400 ms; `_att` version with 1-2 s time constant | fast attack keeps hits sharp, slow release stops flicker; also the main flash-limit guard |
| Onsets | spectral flux (half-wave rectified frame-to-frame increase of log-magnitude, summed over bins), adaptive threshold (moving median + offset), peak-pick with minimum gap 50-100 ms | spectral flux is the standard robust method (Dixon 2006, not fetched); librosa `onset_strength` / `onset_detect` implement it |
| Tempo and beats | librosa `beat.beat_track` (Ellis 2007 dynamic programming) or `madmom` RNN+DBN if accuracy matters; expect half/double tempo errors | musicwright already notes "tempo can come back doubled or halved" (its mw.py line 1036) |
| Sections | novelty / self-similarity boundaries; musicwright `analyze --sections` already does this | use for scene changes in the fractal (palette, formula, camera path) |

Offline advantage: non-causal processing. Use zero-phase (forward-backward) smoothing for slow features, look-ahead so a zoom can *start* before a downbeat and land on it, and global normalisation. Keep onset-driven pulses causal (attack at the onset frame), or they read as early.

### 3.2 Live page (Web Audio)

- `AnalyserNode`: `fftSize` power of two 32 to 32768, default 2048; `frequencyBinCount = fftSize/2`; `smoothingTimeConstant` default 0.8 (0-1, exponential average between calls); `minDecibels` -100, `maxDecibels` -30; `getByteFrequencyData` maps dB linearly from [min, max] to 0-255; Blackman window [S11][S12].
- Recommendation: `fftSize` 2048, `smoothingTimeConstant` 0 (do our own attack/release per band in JS, since the built-in smoothing is symmetric and blunts hits), use `getFloatFrequencyData` for dB, then the same band map and running-average normalisation as offline so a preset looks the same in both paths.
- Microphone: request `getUserMedia({audio:{echoCancellation:false, noiseSuppression:false, autoGainControl:false}})` (constraint names from the Media Capture spec, not fetched); browser AGC and noise suppression flatten dynamics and kill transients.
- Live onset: causal spectral flux with a 1-2 s moving threshold; beat phase from an onset autocorrelation over the last 4-8 s. No look-ahead, so expect 1-2 frames of lag.
- Butterchurn is the reference for "MilkDrop in a browser" and is MIT, so its band code can be read and borrowed with attribution [S9].

## 4. Mappings that read as "the music"

Research on cross-modal correspondences gives the strongest, most consistent pairs [S13][S14][S15]:

- **Loudness to size / scale / zoom** and **pitch to vertical position** load on one factor; **pitch to brightness** and **pitch to shape sharpness** on another (factor analysis, PLOS ONE 2023) [S13].
- Pitch-height is the most robust and partly linguistic (faster reactions when only height is congruent) [S14].
- Users applied size-loudness and height-pitch easily; tempo-based mappings were harder to use (Leiden thesis 2025, not peer reviewed) [S15].

Practitioner rules (derived from MilkDrop's design [S5] and the above; our synthesis, not measured):

1. **Synchrony beats cleverness.** A visual event that starts within about one video frame of an onset reads as caused by it; a smooth variable drifting with RMS reads as random. Tie discrete visual events (pulse, palette step, zoom kick) to onsets and beats, continuous parameters to smoothed band levels.
2. **Bass to big, slow, global** (zoom, scale, overall brightness, iteration-count breathing). **Treble to small, fast, local** (detail, sparkle, edge glow, colour cycling speed). **Mids** to rotation or hue drift.
3. **Asymmetric envelopes**: fast attack, slow release. Symmetric smoothing looks laggy and mushy.
4. **Normalise per band** so quiet passages still move (MilkDrop's 1.0 = normal).
5. **Structure to scene**: section boundaries change formula, palette or camera path; beats inside a section only modulate.
6. **Few mappings at once.** 2-4 audible drivers per preset; more reads as noise.
7. **Bar-level camera**: camera moves of 1, 2 or 4 bars, landing on downbeats, read as choreographed (offline look-ahead makes this possible).
8. Avoid driving hue directly from noisy spectrum bins: colour flicker is the fastest way to look random, and it is also the main flash risk.

## 5. Photosensitivity: definitions and a test

### 5.1 WCAG 2.3.1 Three Flashes or Below Threshold (Level A) [S16]

Passes if either holds in **any one-second period**:
- no more than **three general flashes and/or no more than three red flashes**, or
- the flashing area is below the **general and red flash thresholds**: combined area no more than **0.006 steradians within any 10-degree visual field** (25% of that field). Practical stand-in: a **341 x 256 pixel rectangle** anywhere on a 1024 x 768 display (87,296 px, about 11.1% of the screen area; scale by screen area).

**General flash**: a pair of opposing changes in relative luminance (increase then decrease, or the reverse) of **10% or more of the maximum relative luminance (1.0)**, where the relative luminance of the **darker image is below 0.80**.

**Red flash**: any pair of opposing transitions involving a saturated red. A transition counts when one state has **R/(R+G+B) >= 0.8** and the chromaticity difference between the two states is **> 0.2 in CIE 1976 UCS**: sqrt((u'1-u'2)^2 + (v'1-v'2)^2).

Notes from the same page: loop looping clips while analysing; analyse at the largest viewing size [S16]. Relative luminance is the WCAG sRGB formula: linearise each channel (c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)^2.4), L = 0.2126 R + 0.7152 G + 0.0722 B (WCAG definition, not fetched this session).

### 5.2 ITU-R BT.1702 (television) [S17]

- Current edition BT.1702-3 (2023-11). The 2005 edition (BT.1702-0) defines a potentially harmful flash as a pair of opposing changes of **20 cd/m2 or more** where the darker image is below 160 cd/m2 (darker-image figure from Ofcom-derived practice, not confirmed in the snippet read), screen peak white taken as **200 cd/m2** (ITU-R BT.500 home viewing). That makes it the same 10%-of-peak rule as WCAG.
- Flash sequences longer than **5 s** may be a risk even when they comply; rapid cuts count as flashes when they make screen areas flash; automatic analysers are recommended. It also covers regular spatial patterns (stripes), which WCAG 2.3.1 does not.
- **Harding**: Harding and Jeavons' work underlies the guidance [S17]. The commercial "Harding test" (Harding FPA) is the broadcast tool UK broadcasters use; we cannot run it. Our checker is a WCAG/BT.1702-style approximation, not a certification.

### 5.3 Flash-limit test algorithm (for `fw.py flashcheck`)

Input: rendered frames (or the live canvas sampled each frame), fps.

1. For each frame, convert sRGB to relative luminance L per pixel, plus chromaticity u', v' (via XYZ) and red ratio R/(R+G+B).
2. Choose test regions: slide a window the size of the threshold area (341 x 256 scaled to the output resolution by area; for 1920x1080 about 0.111 x 2,073,600 = 230k px, e.g. 554 x 416) across the frame with 50% overlap. Also test the whole frame. A region "flashes" by its **mean** L (conservative variant: 25th/75th percentile, so a half-region flash is not averaged away).
3. Per region, build the luminance time series. Find **transitions**: walk the series, tracking the running extreme since the last confirmed turn; a transition is confirmed when L has moved >= 0.10 from that extreme in the opposite direction and the darker side is < 0.80. Count a **flash** for each opposing pair of transitions (two transitions = one flash).
4. Red: same walk on regions where either state has red ratio >= 0.8 and the u'v' distance between the states is > 0.2.
5. Slide a 1-second window (fps frames). **Fail** if any region has more than 3 general flashes or more than 3 red flashes in any window. **Warn** if any window has exactly 3, or if 3-per-second flashing persists more than 5 s (BT.1702).
6. Report: first failing time, region, flash count, and the frames, so the renderer can damp that section.
7. **Prevention in the renderer**, not just detection: clamp per-frame change in global mean luminance (slew limit, e.g. max 0.10 per 1/6 s), use release times >= 150 ms, never invert or strobe the whole palette on a beat, cap beat-triggered brightness kicks to 2-3 per second, and run the checker as a gate before `audio` reports success. The live page should apply the same slew limit, since it cannot be checked after the fact; show a photosensitivity warning before start.

At 30 fps the shortest flash pair is 2 frames (15 flashes/s possible), so any per-beat full-frame brightness pulse at 140 BPM 8th notes (4.7/s) fails. Treat 3/s as a hard ceiling for any large-area luminance swing.

## 6. Licence table

| Item | Licence | Source | Use in fractalwright |
|---|---|---|---|
| Winamp AVS (2005 code) | BSD-style (forks BSD-3) | [S1][S2][S3] | Ideas and code may be studied/reused with notice |
| Winamp Legacy Player (2024) | Winamp Collaborative License, no modified redistribution | [S4] | Do not copy |
| MilkDrop 1.04 / 2.25c | BSD | [S6][S7] | OK with notice |
| MilkDrop 2.25d+ | source-available (unverified) | [S6] | Avoid copying |
| Geiss | unknown | - | Ideas only |
| projectM libprojectM | LGPL-2.1 | [S8] | Dynamic link only, or reimplement; do not copy into an MIT plugin |
| Butterchurn | MIT | [S9] | OK with notice |
| butterchurn-presets package | listed MIT; presets converted from MilkDrop authors' work | [S10] | Package licence does not clear the authors' rights |
| projectM "Cream of the Crop" (~10k presets, Jason Fletcher / ISOSCELES) | no licence; README says Milkdrop presets were "in almost all cases, not released under any specific license", assumed public domain, removal on author request | [S8][S18] | **Not safe to bundle in a public repo**; link, don't ship |
| Other projectM packs (Classic, Milkdrop 2, En D) | not stated | [S8] | Same as above |
| librosa | ISC | [S19] | Fine (optional dependency) |
| aubio | GPL-3.0 (or later per some sources) | [S20] | Avoid as a dependency of a permissive plugin; subprocess only |
| Essentia | AGPL-3.0; models CC BY-NC-ND 4.0 or per-model | [S21] | Avoid |
| madmom | code BSD, models CC BY-NC-SA 4.0 (checked https://github.com/CPJKU/madmom/blob/main/LICENSE 2026-11-14) | - | Check before use |

## 7. musicwright hand-over

Read in D:/m4bwa/Claude/Projects/Ai/musicwright/skills/musicwright/scripts/mw.py (2026-11-14):
- `measure`: integrated loudness (LUFS), sample and true peak, LRA via ffmpeg ebur128.
- `sheet`: spectrogram + waveform PNGs (ffmpeg showspectrumpic, log frequency).
- `pulse` (stdlib): onsets from an envelope, inter-onset spread, autocorrelation tempo, grid fit, "is there a beat".
- `analyze` (librosa): tempo, beat times, key, tuning drift, repetition, `--sections` boundaries snapped to beats, onset strength mean.
- `mixcheck`, `compare`, `seam`, `diff`, loop/join/duck tools (not visual-relevant).

**Not in musicwright**: per-frame band energies (bass/mid/treb or N log bands) at a video frame rate, attack/release envelopes, running-average normalisation, onset times as a list at frame resolution (pulse computes them internally), downbeats.

Proposal: fractalwright calls `mw.py analyze --sections` and `pulse` for tempo, beats and sections (do not duplicate), and adds its own small `fw.py audiofeatures` that writes a per-frame feature track (JSON or .npy: t, bass, mid, treb, *_att, bands[16], onset flag, beat phase, section id). If that feature track proves useful elsewhere, offer it upstream to musicwright as `mw.py features --fps N`.

## 8. Implications for fractalwright

1. Model presets on MilkDrop's parameter side: per-frame expressions over `bass/mid/treb` (1 = normal) and `_att`, with q-variable style hand-off to the shader. Optional feedback "trails" pass with decay.
2. One analysis core, two clocks: offline samples features at t = n/fps with look-ahead and global percentile normalisation; live uses causal envelopes. Same band map and envelope constants so a preset looks alike.
3. Defaults: Hann, n_fft 2048, hop 512, 3 bands + 16 log bands, attack 20 ms / release 250 ms, `_att` 1.5 s, onset min gap 80 ms.
4. Mapping defaults: bass to zoom/scale, treb to detail/sparkle, mid to rotation/hue drift, onsets to pulses, sections to formula/palette changes, bar-length camera moves.
5. Flash gate is mandatory: `flashcheck` runs after every offline render; renderer slew-limits mean luminance; live page has the same limiter and a warning screen. Document it as an approximation, not a Harding certification.
6. Ship no third-party presets. Write our own presets; link to projectM/Butterchurn packs for users who want them. Port MilkDrop ideas from BSD 2.25c or MIT Butterchurn only, with notices.
7. Dependencies: librosa optional (ISC); numpy FFT for the core; no aubio/Essentia.

## 8b. Design rules from perception (for the `audio` command)

Book rules from Loy, *Musimathics* vol. 1-2, not yet checked on our own material:

1. Band edges follow critical bands (Bark or ERB), not equal octaves: about 100 Hz wide below
   500 Hz, then about a fifth of the centre frequency. The 3 MilkDrop bands stay, built from them.
2. Loudness is an energy sum over about 200 ms; drive "intensity" from a 200 ms window, and keep
   the short frames for onsets only.
3. Pitch class (chroma, 12 bins) maps to hue round the colour wheel, so a key change reads as a
   colour change and octaves keep their colour.
4. Never measure from an MP3 or other lossy file when a lossless one exists: encoders cut what is
   masked, so band energies and onsets shift. Warn when the input is lossy.
5. Sub-bass (below about 60 Hz) needs a longer frame (4096 or 8192 at 44.1 kHz) to separate
   40 from 60 Hz; use it for the bass band only. Masking is why a soft onset right after a loud
   one is missed: keep the onset minimum gap.
6. Endless zooms take a Shepard-Risset glide: octave-spaced tones under a fixed bell-shaped level
   curve, all rising with the zoom, so pitch seems to rise forever as the picture does.

## 9. Open questions

1. Does the plugin owner want to import user-supplied `.milk` presets (a translator) or only borrow the model? Translator scope is large.
2. Licence status of Geiss code; exact licence text of MilkDrop 2.25c (read the zip's license file before copying any code).
3. Confirm MilkDrop's exact bass/mid/treb band edges and the running-average window from the 2.25c source.
4. BT.1702-3 current numeric thresholds and pattern rules (read the 2023 PDF in full).
5. Is a WCAG-style checker enough for publishing videos on YouTube, or does the owner want a run through a commercial tool (Harding FPA, PEAT) for key releases?
6. madmom model licence before using it for downbeats.

## Sources

- [S1] Advanced Visualization Studio, Wikipedia: https://en.wikipedia.org/wiki/Advanced_Visualization_Studio
- [S2] grandchild/vis_avs: https://github.com/grandchild/vis_avs
- [S3] visbot/vis_avs: https://github.com/visbot/vis_avs
- [S4] Tom's Hardware, Winamp source release 2024: https://www.tomshardware.com/software/winamp-releases-its-source-code-on-github-but-the-legacy-media-player-doesnt-go-full-open-source
- [S5] Ryan Geiss, MilkDrop preset authoring guide: https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html
- [S6] MilkDrop, Wikipedia: https://en.wikipedia.org/wiki/MilkDrop
- [S7] MilkDrop 2 on SourceForge (BSD, 2.25c 2013-05-14 zip): https://sourceforge.net/projects/milkdrop2/ and https://geisswerks.com/milkdrop
- [S8] projectM repository: https://github.com/projectM-visualizer/projectm
- [S9] Butterchurn: https://github.com/jberg/butterchurn
- [S10] butterchurn-presets: https://github.com/jberg/butterchurn-presets
- [S11] Web Audio API spec, AnalyserNode: https://webaudio.github.io/web-audio-api/#AnalyserNode
- [S12] MDN AnalyserNode: https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode
- [S13] Crossmodal correspondences factor analysis (PLOS ONE 2023): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10645324/
- [S14] Pitch-height speeded classification (Frontiers in Cognition 2023): https://www.frontiersin.org/journals/cognition/articles/10.3389/fcogn.2023.1170422/pdf
- [S15] van den Bosch, sketch-based music synthesis, Leiden thesis 2025: https://theses.liacs.nl/pdf/2025-2026-BoschMvandenMarlinde.pdf
- [S16] W3C Understanding SC 2.3.1: https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html
- [S17] ITU-R BT.1702-0 (2005) and BT.1702-3 (2023): https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1702-0-200502-I!!PDF-E.pdf and https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1702-3-202311-I!!PDF-E.pdf
- [S18] Cream of the Crop LICENSE.md: https://github.com/projectM-visualizer/presets-cream-of-the-crop/blob/master/LICENSE.md
- [S19] librosa on PyPI mirror (ISC): https://simple-repository.app.cern.ch/project/librosa
- [S20] aubio: https://aubio.org/
- [S21] Essentia licensing: https://essentia.upf.edu/licensing_information.html
