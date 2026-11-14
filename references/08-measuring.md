# 08 Measuring fractals

Research notes for fractalwright `measure` and `identify`. Accessed 2026-11-14.
Status flags: **[checked]** = confirmed on a fetched or searched page this session;
**[recalled]** = standard textbook result, source named but page not re-read this session.
Promote [recalled] rows to [checked] before using them as a release gate.

## 1. Dimensions: what each one measures

| Quantity | Definition (informal) | Use in fractalwright |
|---|---|---|
| Hausdorff dimension | infimum over coverings; exact theory value | only as the "true value" in tests |
| Box-counting (Minkowski) dimension | slope of log N(eps) vs log(1/eps) | `measure` default for pictures |
| Information dimension D1 | slope of sum p_i log p_i vs log eps | weighted by pixel/visit density |
| Correlation dimension D2 | slope of log C(r) vs log r (pairs closer than r) | point clouds, attractor orbits |
| Generalised Renyi D_q / f(alpha) | moments of box masses | multifractal option |
| Lacunarity Lambda(r) | gappiness at box size r | second number; separates same-D shapes |
| Hurst exponent H | scaling of rescaled range / fluctuation | 1-D signals, traces; D = 2 - H for graphs |

Ordering for any measure: D2 <= D1 <= D0 (box). For self-similar sets satisfying the open set
condition (Sierpinski, Koch, Cantor, Menger) Hausdorff = box = similarity dimension log N / log(1/r),
so those are clean tests. [checked: Falconer, *Fractal Geometry*, 2nd ed., Wiley 2003, ch. 2-3, 9]
For an IFS of similarities with ratios r_i the similarity dimension is the root s of sum r_i^s = 1
(`fw.py measure ifs --ratios`). It equals the Hausdorff dimension only when the pieces do not overlap;
with overlap it is an upper bound. [checked: Falconer 2nd ed. ch. 9.2]

## 2. Box counting

```
box_dimension(mask, sizes=None, fit=None):
    # mask: 2-D bool array (True = on the set); pad to power-of-two square
    if sizes is None: sizes = [2**k for k in range(1, floor(log2(min(mask.shape)))-1)]
    counts = []
    for s in sizes:
        for each of a few grid offsets (0, s/2) [optional: take min count]:
            reshape mask into (H/s, s, W/s, s) blocks; N = count blocks with any True
        counts.append(min over offsets)
    x = log(1/s); y = log(N)
    choose fit range: drop sizes < 2-4 px (pixel-scale saturation) and
                      sizes > 1/8 of image (too few boxes)
    slope, intercept, r2 = least_squares(x[fit], y[fit])
    also report local slopes d log N / d log(1/s) between neighbours
    return slope, stderr, r2, local_slopes, fit_range
```

Rules taken from the literature:
- Power law needs a fit range of at least two decades (log10 of largest over smallest box) before
  any "fractal" verdict; one to two decades is a descriptor only. Jones-Smith and Mathur made the
  same point against the Pollock analyses. [book rule: Rosenberg, *Fractal Dimensions of Networks*, ch. 6.1]
- Use 15 or more box sizes, each averaged over random grid offsets (seeded), and report the
  local-slope curve; a drifting local slope means no single scaling range. Random discs and
  spirals give a convincing slope over a short range and must not pass. [book rule: Rosenberg ch. 6.1, 6.4;
  fw.py measured: spiral spread 1.02, random discs 0.53, fractals 0.05-0.29]
- Coarse boxes bias D low (a line read 0.93, a filled disc 1.88 at 1024 px); never trust a fit over
  three or four coarse sizes. [book rule: Feldman, *Chaos and Fractals*, ch. 18]
- Remove specks (1-2 pixel components) before counting and warn: 3000 specks on a Koch curve moved
  D from 1.258 to 1.176. A dust (most pixels isolated) keeps its points. [checked: Falconer 2nd ed. ch. 3.2; measured in tests]
  [checked: https://www.nature.com/articles/nature05398 ; summary https://plus.maths.org/content/rollicking-pollock-debate]
- Small boxes saturate (every box on a 1-px line is filled, slope drifts to 1 or 2); large boxes
  have too few counts. Report the plateau of local slopes, not just one global fit. [checked: Falconer 2nd ed. ch. 3]
- Grid offset (box placement) changes N by tens of percent at large s; minimising over offsets
  or averaging reduces bias. [recalled: standard practice; see Foroutan-pour et al., Appl. Math. Comput. 105 (1999) 195]
- Thresholding a picture: decide what "the set" is. For an escape-time render, the boundary
  is not "inside pixels"; use an edge mask (pixels whose 4-neighbours differ in in/out) or a
  distance-estimate band. Filled interiors give slope ~2 for the filled region, which is
  correct for the area and wrong for the boundary. Otsu or a fixed iteration cut for photos;
  report the threshold since D moves with it.
- Antialiasing, JPEG ringing and colour gradients create spurious filled boxes at small s;
  binarise before counting and drop s < 4 px from the fit.

Expected accuracy (rule of thumb from the plugin's own tests to be measured; no published
table found): on a 1024-2048 px clean binary render of a self-similar set, box counting
lands within about +-0.03-0.05 of the true value; aligned grids (Sierpinski on a 2^k
lattice) can be within 0.01. Treat these as hypotheses fractalwright must confirm.

## 3. Information and multifractal spectrum

```
renyi(mask_or_weights, sizes, qs):
    for s in sizes:
        mu_i = mass in box i / total mass   (weights = pixel intensity or orbit visits)
        for q in qs:
            if q == 1: I = -sum mu_i log mu_i       # information
            else:      Z = sum mu_i**q
    D1 = slope of I vs log(1/s)
    tau(q) = slope of log Z vs log s ; D_q = tau(q)/(q-1)
    alpha(q) = d tau/dq ; f(alpha) = q*alpha - tau      # Legendre transform
```
Negative q is very noisy on images (empty-ish boxes dominate); limit q to [-5, 5] or [0, 5].
Chhabra-Jensen direct method avoids the numerical Legendre transform.
[recalled: Halsey et al., Phys. Rev. A 33 (1986) 1141; Chhabra & Jensen, PRL 62 (1989) 1327]

## 4. Correlation dimension (Grassberger-Procaccia)

```
correlation_dimension(points, rs):
    # points: (n, d) array, e.g. orbit of an attractor after transient
    for r in rs: C(r) = 2/(n(n-1)) * #{i<j : |x_i - x_j| < r}
    D2 = slope of log C vs log r over the linear range
    # O(n^2): subsample to ~5k points or use a KD-tree / sorted grid
```
Paper: Grassberger and Procaccia, "Measuring the strangeness of strange attractors",
Physica D 9 (1983) 189-208, doi:10.1016/0167-2789(83)90298-1.
[checked: https://portal.mardi4nfdi.de/wiki/Publication:1076387]
Caveats: needs n large (Eckmann-Ruelle: D2 estimates cannot exceed about 2 log10 n);
exclude temporally close pairs (Theiler window). [recalled: Eckmann & Ruelle, Physica D 56 (1992) 185]

## 5. Lacunarity (gliding box)

```
lacunarity(mask, r):
    S = sliding-window sums of mask with an r x r box over every position
    return E[S^2] / E[S]^2        # = var/mean^2 + 1
```
Compute for r = 1, 2, 4, ... ; plot log Lambda vs log r. Same-D sets with different gap
structure separate here. [recalled: Allain & Cloitre, Phys. Rev. A 44 (1991) 3552;
Plotnick et al., Landscape Ecology 8 (1993) 201]. NumPy: integral image makes it O(pixels).

## 6. Hurst exponent

R/S: split series into windows of length n, R/S averaged, H = slope of log(R/S) vs log n.
DFA is more robust to trends. For a self-affine graph, box dimension D = 2 - H.
Profiles and heightmaps are self-affine: measure them with the spectral slope (beta = 2H + 1) and the
semivariogram (gamma(l) ~ l^(2H)), never with square boxes (`fw.py measure profile`, `measure heightmap`;
`measure box` refuses a numbers file). Semivariogram for walks (1 < beta < 3); R/S or DFA for noises.
[book rule: Turcotte, *Fractals and Chaos in Geology and Geophysics*, ch. 7; recovery measured, see section 7]
Katz dimension of a sampled curve: log10(n) / (log10(n) + log10(d / L)), L the length, d the largest
distance from the first point, n = L / mean step (`fw.py measure katz`). Exact on a Koch polyline, about
1.03 on any fBm profile whatever its H: a cheap roughness number, not D. [book rule: Banerjee et al.,
*Fractal Patterns with MATLAB*, ch. 1; behaviour measured]
[recalled: Hurst 1951; Peng et al., Phys. Rev. E 49 (1994) 1685 (DFA); Mandelbrot, *The Fractal Geometry of Nature*, 1982]
Use for fractional Brownian terrain profiles, coastlines read as heights, audio.

## 7. Test values

| Shape | True value | Type | Expected estimate in fractalwright | Source |
|---|---|---|---|---|
| Middle-third Cantor set | log2/log3 = 0.6309 | Hausdorff = box | +-0.02 on 3^7 px line | [checked: https://en.wikipedia.org/wiki/List_of_fractals_by_Hausdorff_dimension , accessed 2026-11-14] |
| Koch curve | log4/log3 = 1.2619 | Hausdorff = box | +-0.04 at 2048 px | [checked: https://en.wikipedia.org/wiki/List_of_fractals_by_Hausdorff_dimension , accessed 2026-11-14] |
| Sierpinski triangle | log3/log2 = 1.5850 | Hausdorff = box | +-0.02 at 1024 px (lattice-aligned) | [checked: https://en.wikipedia.org/wiki/List_of_fractals_by_Hausdorff_dimension , accessed 2026-11-14] |
| Sierpinski carpet | log8/log3 = 1.8928 | Hausdorff = box | +-0.02 at 3^6 = 729 px | [checked: https://en.wikipedia.org/wiki/List_of_fractals_by_Hausdorff_dimension , accessed 2026-11-14] |
| Menger sponge | log20/log3 = 2.7268 | Hausdorff = box | +-0.03 on 3^5 voxel grid | [checked: https://en.wikipedia.org/wiki/List_of_fractals_by_Hausdorff_dimension , accessed 2026-11-14] |
| Line / filled square | 1 / 2 | sanity | +-0.01 | trivial |
| Mandelbrot boundary | 2 (Hausdorff) | Hausdorff | box count on renders gives well below 2 (pixel-limited, typically ~1.2-1.6 depending on zoom and iterations); test only "rises with resolution and iterations", never "equals 2" | Shishikura, Annals of Math 147 (1998) 225-267 [value 2 checked: https://en.wikipedia.org/wiki/List_of_fractals_by_Hausdorff_dimension , accessed 2026-11-14] |
| Mandelbrot area | ~1.50659177 +- 0.00000008 (pixel count) ; also cited 1.5065918849 +- 2.8e-9 | area | pixel count at 4096^2 with 10^4 iterations: within ~1e-3 | Förstemann via Munafo [checked: https://mrob.com/pub/muency/pixelcounting.html , https://mrob.com/pub/muency/areahistory.html ; arXiv 1410.1212 checked] |
| Lorenz attractor (s=10, r=28, b=8/3) | D2 ~ 2.05, D ~ 2.06 | correlation / Lyapunov | +-0.05 with 10^4-10^5 points | Grassberger-Procaccia 1983 [Lorenz figure checked via secondary notes https://arxiv.org/pdf/2105.14863] |
| Henon map (a=1.4, b=0.3) | D2 = 1.21 +- 0.01 ; box/Hausdorff ~1.26-1.28 | correlation ; capacity | +-0.03 with 10^4-10^5 points | GP 1983 (D2) [unverified after check (GP paper paywalled; Wikipedia correlation-dimension page gives no value)]; Russell, Hanson & Ott, PRL 45 (1980) 1175 (capacity 1.26) [checked: https://en.wikipedia.org/wiki/List_of_fractals_by_Hausdorff_dimension lists 1.261 +- 0.003, accessed 2026-11-14] |
| fBm profile, H = 0.7 | D = 2 - H = 1.3 | self-affine | not by box counting; spectral H +-0.045, semivariogram H +-0.07 on 2^16 Davies-Harte steps (measured max 0.033 and 0.055 over 10 seeds) | Mandelbrot 1982; Turcotte ch. 7 [measured] |
| fBm surface, H | D = 3 - H; radial beta = 2H + 2 = profile beta + 1 | self-affine | radial H +-0.025 at 1024^2 (measured max 0.015); radial minus profile beta 0.96-1.01 | Turcotte ch. 7.8 [measured] |
| Kronecker mask (k x k, m ones) | log m / log k | similarity | exact with boxes k^j; -0.05 to -0.07 with general boxes (log-periodic lattice bias) | Steeb, *The Nonlinear Workbook*, ch. 9.6 [measured] |
| Unequal Cantor, ratios 1/2 and 1/4 | log(golden ratio)/log 2 = 0.6942 | similarity | `measure ifs` to 1e-9 | Falconer 2nd ed. ch. 9.2 [checked] |

Note: the Mandelbrot area via the Laurent (Ewing-Schober) series converges toward 1.60-1.70,
which disagrees with pixel counting; pixel counting is the accepted practical estimate.
Hill's mu-atom lower bound is 1.506303622. [checked: https://mrob.com/pub/muency/areahistory.html]
Pixel counting: Förstemann used grids up to 2,097,152^2 on GPUs, about 35 days for the largest.
[checked: https://www.mrob.com/pub/muency/forstemannthorsten.html]

## 8. What the numbers cannot say

- Two decades minimum. A picture has at most ~log2(width) octaves of scale; boxes from 2 px to a
  quarter of the side give 2.1 decades at 1024 px and 1.9 at a 729 px Kronecker render. Under two
  decades `measure` says "descriptor only" and never "fractal"; over two, D is still a descriptor,
  not proof. [book rule: Rosenberg ch. 6.1]
- Rendering decides the answer: iteration cap (boundary thins as maxiter rises), colouring
  (smooth colouring has no edge to threshold), antialiasing, JPEG, resize filters, zoom window.
  `measure` must report these inputs alongside the number.
- Different sets share a D (Koch curve vs a random curve of D 1.26); D alone cannot identify.
- The Pollock dispute: Taylor et al. (Nature 1999) claimed drip paintings are fractal and D can
  authenticate; Jones-Smith & Mathur (Nature 444, 2006) showed simple Photoshop star scribbles
  pass the same criteria and that the box range was too short; Taylor replied the critique would
  also reject many physical fractal studies. Treat "fractal dimension of art" as contested.
  [checked: https://www.nature.com/articles/nature05398 ; https://www.sciencedaily.com/releases/2006/12/061204123447.htm ; https://plus.maths.org/content/rollicking-pollock-debate]
- Box dimension of the Mandelbrot boundary cannot be measured from renders: its value 2 is a
  limit statement, approached extremely slowly.

## 9. Features for `identify`

No standard benchmark for classifying fractal *families* from images was found this session;
the nearest work is texture classification with fractal/multifractal features (e.g.
Xu, Ji & Fermüller, "Viewpoint invariant texture description using fractal analysis", IJCV 2009
[recalled]) and IFS inverse problems (Barnsley collage theorem [recalled]). Hand-built features:

| Feature | How | Points to |
|---|---|---|
| Mirror symmetry about real axis | compare image with vertical flip of inside mask | Mandelbrot, Julia with real c |
| 180-degree point symmetry | compare with 180 rotation about centre | every quadratic Julia set |
| n-fold rotation | correlation with rotations 2pi/k | z^k+c sets (Multibrot: k-1 fold), Koch snowflake (6), Sierpinski (3) |
| Cardioid + circular bulbs | fit circle/cardioid to largest inside component; check bulb tangent at -0.75 | Mandelbrot |
| Connected vs dust | count components of inside mask | connected Julia (c in M) vs Cantor dust |
| Spiral arms | angle-vs-radius structure, log-polar FFT peaks | Julia near Siegel / seahorse valley zooms |
| Exact self-similar copies | template match at scale 1/2, 1/3 with rotations | IFS (Sierpinski, carpet, Koch, ferns) |
| Grid-aligned holes | holes at 1/3 grid | carpet, Menger, Cantor dust |
| Box D + lacunarity + local slope spread | from sections 2 and 5 | separates IFS (flat local slopes) from escape-time (drifting) |
| Colour bands | discrete iteration bands vs smooth | escape-time render vs photo |
| Burning-ship asymmetry | flame shapes, no left-right mirror of M | Burning Ship |

Parameter guesses: Julia c from symmetry axis angle and component count is weak; better
render candidate c on a coarse grid and compare (SSIM or IoU of masks). Mandelbrot zoom
location: match minibrot/bulb periods.

## 10. Implications for fractalwright (proof bar)

- `measure` outputs: slope, stderr, r2, fit range in px and decades, local-slope plateau width,
  threshold used, image size; refuse a "fractal" verdict if the range is under two decades
  (built: `fw.py measure box`, verdict thresholds in TESTS.md T-20261114-3).
- Gate tests (generated at runtime, no downloads): Cantor, Koch, Sierpinski triangle and carpet
  within +-0.03 at >=1024 px; Menger +-0.05 on 243^3 voxels; line/square +-0.01;
  Henon D2 within 1.21 +- 0.04 and Lorenz D2 within 2.05 +- 0.07 using <=20k points;
  Mandelbrot area 1.5066 +- 0.002 at 2048^2, 5000 iterations.
- Mandelbrot boundary: assert monotone increase with resolution, never equality with 2.
- Pure-Python fallback must give the same numbers as the NumPy path to 1e-9 on small images.
- `identify` must state confidence and the features that drove it; abstain on photos and art.

## 11. Open questions

- Verify Henon D2 = 1.21 and capacity 1.26 against the primary papers.
- Measure the actual tolerance tables above on fractalwright renders and replace the rules of thumb.
- Is there a published fractal-family image classifier/dataset worth benchmarking against?
- Best edge-extraction method for escape-time boundaries (edge mask vs distance estimator).

## 12. Sources

- Jones-Smith & Mathur, Nature 444 (2006) E9-E10 - https://www.nature.com/articles/nature05398
- Pollock debate summary - https://plus.maths.org/content/rollicking-pollock-debate
- ScienceDaily on the critique - https://www.sciencedaily.com/releases/2006/12/061204123447.htm
- Munafo, Pixel Counting - https://mrob.com/pub/muency/pixelcounting.html
- Munafo, Area History - https://mrob.com/pub/muency/areahistory.html
- Munafo, Förstemann entry - https://www.mrob.com/pub/muency/forstemannthorsten.html
- Bittner et al., area of the Mandelbrot set (arXiv 1410.1212) - https://arxiv.org/pdf/1410.1212v2.pdf
- Grassberger & Procaccia 1983 record - https://portal.mardi4nfdi.de/wiki/Publication:1076387
- Lorenz dimension (secondary) - https://arxiv.org/pdf/2105.14863
- Checked against the book (2nd ed., 2003): Falconer *Fractal Geometry*. Recalled (not fetched): Shishikura Ann. Math. 1998; Halsey et al. 1986;
  Chhabra & Jensen 1989; Allain & Cloitre 1991; Eckmann & Ruelle 1992; Russell, Hanson & Ott 1980; Peng et al. 1994.
