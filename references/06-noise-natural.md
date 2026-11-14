# 06 Noise and natural fractals

Research note for fractalwright. Accessed 2026-11-14 unless marked. Claims marked **(unverified)** came from
background knowledge or search snippets and were not confirmed on a fetched primary page this session.

## 1. Base noises (the "basis functions")

| Noise | What it is | Origin | Notes for us |
|---|---|---|---|
| Value noise | random values at lattice points, smoothly interpolated | classic | blocky look; cheapest; visible grid axis bias |
| Perlin (gradient) noise | random gradients at lattice points, dot with offset, smooth fade | Perlin 1985 | zero at lattice points; `cnoise`/`pnoise` in webgl-noise [S5] |
| Simplex noise | gradient noise on a simplex grid (triangles/tetrahedra), fewer corners, less axis bias | Perlin 2001 | patent US6867776 expired 2022-01-08 [S1][S2] |
| OpenSimplex2 (F, S) | patent-free simplex-like noise | KdotJPG | CC0-1.0, some dirs Unlicense; C#, Java, GLSL, HLSL, Rust [S3] |
| Worley / cellular | distance F_n to the n-th nearest random seed point | Worley, SIGGRAPH 1996 [S6] | F1 = cells, F2-F1 = cell borders/cracks (F2-F1 is common practice, not on [S6]) |

Scale convention: one noise "feature" is about one lattice unit; frequency f means the domain is scaled by f.

## 2. fBm (fractional Brownian motion) by summing octaves

Formula (Quilez [S4]; Musgrave via Blender source [S9]):

```
fbm(p) = sum_{i=0}^{N-1}  a_i * noise(f_i * p)
f_i = lacunarity^i          (lacunarity L, usually ~2)
a_i = gain^i                (gain G, usually 0.5)
G = L^(-H)  ->  for L = 2:  G = 2^(-H)
```

- **H (Hurst exponent)**, 0 < H < 1. Quilez: H near 0 is rough, near 1 smooth; H = 1/2 is ordinary Brownian
  motion; "G=0.5 is what most people have hardcoded", which corresponds to H = 1 [S4].
- **Lacunarity**: frequency gap between octaves. Non-integer values (e.g. 1.98, 2.01) avoid lattice
  alignment between octaves **(unverified; common advice)**.
- **Octaves N**: stop when the highest frequency reaches about one pixel (Nyquist): N ~ log_L(resolution /
  base_feature_size). More octaves past that add aliasing and cost only.
- stb_perlin's defaults: octaves 6, lacunarity 2.0, gain 0.5 [S7].
- Blender calls the gain "Roughness" and the octave count "Detail" (fractional detail blends the last
  octave) [S9].

## 3. Turbulence, ridged, hybrid, hetero (Musgrave multifractals)

- **Turbulence**: sum of `|noise|` per octave; creases where noise crosses zero (stb_perlin
  `stb_perlin_turbulence_noise3`) [S7].
- **Ridged multifractal** (Blender Cycles, Apache-2.0 [S9]); each octave is weighted by the previous signal,
  so detail concentrates on ridges and valleys stay smooth:

```
signal = offset - |noise(p)|; signal *= signal; value = signal; weight = 1
for i in 1..N:
    p *= lacunarity
    weight = clamp(signal * gain, 0, 1)
    signal = offset - |noise(p)|; signal *= signal; signal *= weight
    value += signal * pwr; pwr *= roughness
```
  Typical offset 1.0 (stb: "about 1.0, larger may be needed"), gain ~2 in Musgrave's book **(gain
  value unverified)** [S7].
- **Hybrid multifractal** (additive/multiplicative), from [S9]:
```
for i while weight > 0.001:
    weight = min(weight, 1)
    signal = (noise(p) + offset) * pwr; pwr *= roughness
    value += weight * signal
    weight *= gain * signal; p *= lacunarity
```
- **Hetero terrain**: `increment = (noise(p)+offset) * pwr * value; value += increment` - smooth low
  areas, rough high areas [S9].
- These are "multifractal": local roughness (local H) varies with height, so a single dimension
  measurement does not describe them. Test them by comparing local slope statistics low vs high, not
  global D.

## 4. Domain warping (Quilez)

`f(p) -> f(p + h(p))` with h itself an fBm [S4w]:

```
q = vec2(fbm(p + vec2(0.0,0.0)), fbm(p + vec2(5.2,1.3)))
r = vec2(fbm(p + 4.0*q + vec2(1.7,9.2)), fbm(p + 4.0*q + vec2(8.3,2.8)))
value = fbm(p + 4.0*r)
```
The constant offsets decorrelate the components; the 4.0 is the warp strength. Offsets per the
widely copied shader **(constants unverified on the live page; the article returned 404 to fetch,
search snippet confirms `fbm(p + 4.0*q)` nesting)**. q and r double as colour channels for marbled,
smoky or geological stills. Animate by adding time to the inner offsets.

## 5. Midpoint displacement and diamond-square

- Fournier, Fussell, Carpenter, SIGGRAPH 1982 [S8].
- Grid (2^n + 1)^2; set corners; alternate **diamond** step (square centre = mean of 4 corners + rand) and
  **square** step (edge midpoints = mean of 3 or 4 neighbours, or wrap) [S8].
- Random amplitude shrinks by 2^(-H) per level; lower H = rougher [S8].
- Known artefact: axis-aligned "creases" (Miller 1986); Lewis 1987 generalised the weights to fix it [S8].
- 1D midpoint displacement gives coastline/mountain profiles; same amplitude rule.
- Use: fast, tileable when wrapped, a teaching/explorer mode. Prefer spectral or noise fBm for quality.
- Measured creases (`fw_extra.crease_ratio`: mean |second difference| across the coarse grid lines
  at multiples of n/8 over the mean elsewhere): diamond-square 1.17-1.19 at 513 px, H 0.8, three
  seeds; spectral synthesis 0.98-1.00. So `fw.py terrain` defaults to spectral; `--method midpoint`
  stays for teaching [book rule confirmed: Mandelbrot, *The Fractal Geometry of Nature*, ch. 26].

## 5b. Fractal interpolation and the Weierstrass sum

- Affine fractal interpolation function (FIF): maps w_i(x, y) = (a_i x + e_i, c_i x + d_i y + f_i)
  send the whole graph onto interval i; the curve passes through the given points and |d_i| < 1
  sets roughness. d = 0 gives the straight-line join. For equally spaced points and sum|d_i| > 1
  the graph has D = 1 + log(sum|d_i|) / log N. `fw.py fif` draws one; the semivariogram D of
  `measure profile` matched the formula within 0.035 on four scaling sets. The alpha-fractal mode
  (an FIF that perturbs a given function) uses the same maps with the base function in f_i.
  Source: Banerjee, Gowrisankar, Reddy, *Fractal Patterns with MATLAB*, ch. 2 and 4 (book rule
  for alpha mode; the affine case is checked). Row-and-column surfaces and splines: left out.
- Weierstrass sum W(t) = sum_k lambda^(-k H) sin(lambda^k t) with lambda > 1 gives a profile of
  known D = 2 - H, a generated test input beside fBm (Steeb, *The Nonlinear Workbook*, ch. 9).
  A Levy flight (heavy-tailed steps) makes clustered point sets; note only.

## 6. Spectral synthesis (1/f^beta)

Recipe: white Gaussian noise -> FFT -> multiply amplitude by `1/|k|^(beta/2)` -> inverse FFT. Equivalent to
filtering white noise; pink noise is made by dividing amplitudes by sqrt(f) in 1D [S10]. Periodic by
construction, so outputs tile.

| beta | name | 1D |
|---|---|---|
| 0 | white | flat spectrum |
| 1 | pink | equal energy per octave [S10] |
| 2 | brown / Brownian | H = 1/2 [S10] |

## 7. Dimension relations usable as tests

| Object | Relation | Source |
|---|---|---|
| fBm graph (1D trace), H in (0,1) | D = 2 - H (Hausdorff and box, a.s.) | [S11] [S12] |
| fBm 1D power spectrum | S(f) ~ 1/f^(2H+1), i.e. beta = 2H + 1 (inferred from "white noise filtered by w^(-H-1/2)") | [S11] |
| 1D spectral -> D | D = (5 - beta)/2 (consistent with the two rows above) | [S13] |
| fBm surface z(x,y) | D = 3 - H = profile D + 1 (checked by measurement: profile cuts of a 1024^2 synthetic surface return H within 0.021; differential cube counting read 0.1-0.3 low, so the D side rests on the spectral relation) | Turcotte ch. 7.8; fw.py tests |
| 2D surface spectrum (radial) | amplitude ~ 1/k^(H+1), so power per mode beta_2D = 2H + 2 = profile beta + 1, D = (8 - beta_2D)/2 (checked by measurement: radial minus profile beta 0.96-1.01 over 4 seeds and H 0.3-0.8; fit every mode, integer-k bin averages read H 0.04 low) | Turcotte ch. 7.8; fw.py tests |
| fBm covariance | E[B(t)B(s)] = 1/2(|t|^2H + |s|^2H - |t-s|^2H) | [S11] |
| Octave fBm | gain G = L^(-H) | [S4] |
| Coastline of Britain | D ~ 1.25 (Mandelbrot 1967) **(unverified this session)** |  |

Test ideas for fractalwright's measuring module (see 08-measuring.md):
1. Generate 1D fBm by spectral synthesis with H = 0.3, 0.5, 0.8; estimate H by variogram slope
   (Var[z(x+d)-z(x)] ~ d^(2H)), by R/S or DFA [S12], and by periodogram slope; expect within +-0.05.
2. Box-count a thresholded profile/coastline: D ~ 2 - H.
3. For octave fBm with G = 2^-H, the variogram slope only holds between the lowest and highest octave
   scales; the test must restrict the fit range (beyond that, slope -> 2 at small d, 0 at large d).
4. Diamond-square with factor 2^-H: same H estimate, looser tolerance (creases bias it).
5. Isoline (coastline) of an fBm surface: D = 2 - H **(unverified relation, test empirically)**.
- Caution: Hurst H and D decouple for general processes; D is short-scale, H long-scale [S12].

## 8. Terrain, erosion, clouds, coastlines

- **Terrain**: ridged multifractal for mountains, hetero/hybrid for plains-to-peaks, domain-warped fBm
  for folded geology. Heights as 16-bit to avoid stepping.
- **Erosion**: Mei, Decaudin, Hu, Pacific Graphics 2007, "Fast Hydraulic Erosion Simulation and
  Visualization on GPU": shallow-water "virtual pipes" per cell, erosion/deposition/sediment transport,
  multi-pass GPU [S14]. Jako and Toth 2011 add thermal erosion (talus angle slumping) [S15]. Particle
  ("droplet") erosion is a separate, simpler CPU method (Beyer 2015 thesis) **(unverified)**.
  For stills, a few hundred thousand droplets on a 1025^2 map is the common scale **(unverified)**.
- **Clouds**: 2D: fBm or warped fBm thresholded with `smoothstep(c, c+w, fbm)` for coverage; 3D volumetric:
  Worley-inverted fBm ("Perlin-Worley") density, raymarched **(unverified; Schneider/Guerrilla 2015 talk
  is the usual source)**. Volumetric raymarching in a browser is threewright's territory.
- **Coastlines**: threshold an fBm/ridged heightfield at sea level, or 1D midpoint displacement of a
  polyline; measurable D makes a good "show the theory" still.

## 9. Licences of common implementations

| Implementation | Licence | Source |
|---|---|---|
| stb_perlin.h (Barrett) | MIT or Public Domain (Unlicense), your choice | [S7] |
| OpenSimplex2 (KdotJPG) | CC0-1.0; some dirs Unlicense | [S3] |
| webgl-noise (Gustavson, ex-Ashima glsl-noise) | MIT | [S5] |
| Blender Cycles fractal_noise.h | Apache-2.0 | [S9] |
| Simplex noise algorithm | patent US6867776 expired 2022-01-08 | [S1] [S2] |
| FastNoiseLite | MIT (checked https://github.com/Auburn/FastNoiseLite 2026-11-14) |  |
| Inigo Quilez article code / Shadertoy | default Shadertoy licence is CC BY-NC-SA 3.0 unless stated **(unverified after check: shadertoy.com/terms returned 403)**; re-implement from the formulas instead of copying |  |
| numpy-only own implementation | ours; preferred for the Python CLI |  |

Safe default: write our own value/Perlin/simplex/Worley in numpy (formulas are not copyrightable) and
vendor webgl-noise (MIT) for any GLSL explorer, keeping its licence header.

## 10. Hand-over table

What siblings already hold (checked 2026-11-14 by grep of their skills and kb):
- threewright: no noise/fBm/terrain recipes; generative-art scenario says seed everything from one PRNG
  (`kb/scenarios/generative-art.md`); owns shaders (threewright-shaders, TSL), web pages, captured video.
- polywright: no procedural noise; owns real-place terrain from OpenStreetMap + DEM (`pw.py place`),
  engine heightmap sizes (Unity 2^n+1 16-bit RAW, Unreal 1009/2017/4033, `polywright-capture/references/places.md`),
  meshes, printing, Blender F-curve NOISE modifier.

| Task | fractalwright | threewright | polywright |
|---|---|---|---|
| Noise/fBm/multifractal maths, parameters, seeds | owns | uses ours | uses ours |
| Stills of noise, warped fBm, clouds, coastlines (PNG) | owns (numpy CLI) | - | - |
| Measuring H and D, theory demos | owns | - | - |
| Synthetic heightmap (16-bit PNG/RAW, 2^n+1) incl. erosion | owns (generation) | - | takes it to mesh, engine, print |
| Heightmap of a real place | - | - | owns (`pw.py place`) |
| Interactive 2D noise explorer (single HTML, GLSL) | owns simple fragment-shader page | owns anything three.js / 3D / TSL | - |
| 3D terrain flythrough, volumetric clouds in browser | supplies heightmap + params | owns | - |
| Terrain to mesh, LOD, game export, 3D print tile | - | - | owns |
| Video of evolving noise (time-sliced fBm) | owns offline frames + ffmpeg | owns if rendered in three.js | - |

Hand-over line: fractalwright makes and measures the field (noise, fBm, heightmap, still, data); threewright
renders it in 3D in the browser; polywright turns a heightmap into a mesh, a game asset or a print.

## 11. Implications for fractalwright

1. One `noise` module: value, Perlin, simplex (or OpenSimplex2-style), Worley F1/F2, all seeded, numpy
   vectorised, tileable option.
2. One `fbm` function with H, lacunarity, octaves, plus `mode` = fbm | turbulence | ridged | hybrid |
   hetero, mirroring Blender's parameter names (Detail, Roughness, Lacunarity, Offset, Gain) so users
   of Blender recognise them [S9]; document G = L^-H.
3. `warp` helper with strength and depth (1-2 levels), returning q and r for colouring.
4. Spectral synthesis generator (1D, 2D) with beta or H input: the reference "ground truth" for tests.
5. Diamond-square as an explorer/teaching mode, with the crease caveat.
6. Erosion: start with droplet erosion (simple, CPU); pipe model only if needed.
7. Tests: H recovery and D = 2 - H checks (section 7) belong in the test suite from day one.
8. Exports: 16-bit PNG and RAW at 2^n+1 for polywright and engines.

## 12. Open questions

- Confirm D = 3 - H for surfaces and the 2D spectral exponent from a primary text (Peitgen and Saupe,
  "The Science of Fractal Images", 1988, ch. 2 by Voss).
- Confirm Quilez's warp constants and licence of his article code (pages 404'd to WebFetch today).
- Confirm FastNoiseLite licence; decide whether to depend on it or stay numpy-only.
- Musgrave's original book code licence (Texturing and Modeling) before porting anything verbatim.
- How many droplets/iterations for convincing erosion at 1025^2 and 4097^2; benchmark.
- Should hybrid/ridged multifractals get a "local H map" visualisation as a measuring feature?

## Sources (accessed 2026-11-14)

- [S1] Google Patents, US6867776B2 "Standard for perlin noise": https://patents.google.com/patent/US6867776
- [S2] Wikipedia, Simplex noise (patent expiry 2022-01-08): https://en.wikipedia.org/wiki/Simplex_noise
- [S3] OpenSimplex2 repository: https://github.com/KdotJPG/OpenSimplex2
- [S4] Quilez, fBm article (via search snippet; page 404 to fetch): https://iquilezles.org/articles/fbm
- [S4w] Quilez, domain warping (via search snippet): https://iquilezles.org/articles/warp
- [S5] Gustavson, webgl-noise: https://github.com/stegu/webgl-noise
- [S6] Wikipedia, Worley noise: https://en.wikipedia.org/wiki/Worley_noise
- [S7] stb_perlin.h: https://github.com/nothings/stb/blob/master/stb_perlin.h
- [S8] Wikipedia, Diamond-square algorithm: https://en.wikipedia.org/wiki/Diamond-square_algorithm
- [S9] Blender Cycles fractal_noise.h: https://raw.githubusercontent.com/blender/blender/main/intern/cycles/kernel/svm/fractal_noise.h
- [S10] Wikipedia, Pink noise: https://en.wikipedia.org/wiki/Pink_noise
- [S11] Wikipedia, Fractional Brownian motion: https://en.wikipedia.org/wiki/Fractional_Brownian_motion
- [S12] Wikipedia, Hurst exponent: https://en.wikipedia.org/wiki/Hurst_exponent
- [S13] Paul Bourke, Generating noise with different power spectra: https://paulbourke.net/fractals/noise/
- [S14] Mei, Decaudin, Hu 2007 (HAL copy): https://core.ac.uk/download/52631892.pdf
- [S15] Jako and Toth, CESCG 2011: https://www.old.cescg.org/CESCG-2011/papers/TUBudapest-Jako-Balazs.pdf
- Blender manual (Musgrave node: offset applies to hybrid/ridged/hetero, gain to hybrid/ridged):
  https://docs.blender.org/manual/ja/3.6/modeling/geometry_nodes/texture/musgrave.html (search snippet)
