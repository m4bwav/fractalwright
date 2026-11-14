# 12. Neighbours: reaction-diffusion, cellular automata, tilings, Kleinian groups

Accessed 2026-11-14. Code: `scripts/fw_neighbours.py`. Claims marked **(recalled)** were not fetched this session and need a primary check before anything relies on them.

## Reaction-diffusion

Gray-Scott model. Fetched from Karl Sims, "Reaction-Diffusion Tutorial", https://www.karlsims.com/rd.html (2026-11-14):

- DA = 1.0, DB = 0.5, dt = 1.0.
- Laplacian: 3x3 convolution, centre -1, edge neighbours 0.2, diagonals 0.05.
- Feed and kill: typical default f 0.055, k 0.062; mitosis f 0.0367, k 0.0649; coral growth f 0.0545, k 0.062. These are the three presets.
- The page shows the update equations only as an image; the form in the code is the standard Gray-Scott update (recalled).

Pearson, "Complex Patterns in a Simple System", Science 261 (1993) is the classic parameter map **(recalled, not fetched)**; no preset uses a value taken from it. The seeded squares start at A 0.5, B 0.25, a perturbation in Pearson's style **(recalled)**: B = 1 inside A = 1 blew up to NaN at 64 px (measured). A Gray-Scott pattern is not a fractal: it has one characteristic length.

## Cellular automata

- Elementary CA: rule number bits indexed by (left, self, right) as 4l + 2s + r (Wolfram's numbering, **recalled**). Rule 90 from one cell draws the Sierpinski triangle; 2^k rows hold 3^k live cells (tested exactly), so D = log3/log2 = 1.585.
- Life-like rules in B/S notation (B3/S23 is Conway's Life) on a torus (**recalled** convention).

## Tilings

- Penrose P3 by Robinson-triangle substitution with ratio 1/phi from a 10-triangle sun (the construction popularised by Jeff Preshing's "Penrose Tiling Explained", **recalled**). Each triangle draws two sides; the base is the rhomb diagonal. Thick:thin ratio tends to phi (tested within 0.01 at 8 steps).
- Regular square, triangle and hex tilings.
- A tiling is not a fractal. Box counting of the edges reads slope ~1 at boxes below the tile size and ~1.7-1.9 above it; fw.py measure's local-slope spread (bar 0.30) returns "not fractal over this range" (measured spread 0.65-0.79).

## Kleinian

- Apollonian gasket Hausdorff dimension about 1.3056867. Fetched from Wikipedia "Apollonian gasket" (2026-11-14), which cites Boyd (1973), McMullen (1998, "Hausdorff dimension and conformal dynamics III: Computation of dimension") and Wormell and Vytnova (2025).
- Descartes circle theorem in reflection form: replacing circle i of a tangent quadruple gives k_i' = 2(k_j + k_k + k_l) - k_i, and the same for k z (complex Descartes, Lagarias, Mallows, Wilks 2002, **recalled**).
- Two-generator groups: "Grandma's recipe" from Mumford, Series and Wright, Indra's Pearls (2002), chapter 6 **(recalled; formulas typed from memory, tested only for the parabolic commutator trace -2)**. ta = tb = 2 gives the Apollonian group. Limit set drawn by inverse iteration over reduced random words. Reading the book (HANDOFF books #7) should check the formulas and add the DFS word enumeration.
