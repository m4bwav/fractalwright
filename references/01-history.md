# 01 - History and people of fractals

Researched 2026-11-14 (all URLs accessed 2026-11-14). Claims marked **(unverified)** come from the researcher's background knowledge and were not confirmed against a fetched source in this pass; confirm before quoting them in plugin text.

## Summary

1. Fractal history runs from pure mathematics (Fatou and Julia's iteration theory, 1917-1920) through computer pictures (Brooks-Matelski 1978, Mandelbrot 1979-1982) to hobbyist software and art (Fractint 1988, fractal flames and Electric Sheep 1990s-2000s).
2. The 3D era came from an amateur forum, not academia: Daniel White and Paul Nylander's Mandelbulb (2007-2009) and Tom Lowe's Mandelbox (2010) on Fractal Forums.
3. Credit is often disputed or shared (Brooks-Matelski vs Mandelbrot; White vs Nylander), so `explain` should name all parties and say "credited to" rather than "invented by".
4. Licences vary widely: Fractint is freeware with credit-only source terms, flam3 is GPL-3.0, the Electric Sheep client is GPL, and sheep content is CC-BY-NC or CC-BY.
5. The demoscene made real-time GPU raymarching of distance-estimated fractals common in 4k and 64k intros; this is the direct ancestor of fractalwright's browser explorer and 3D work.

## Timeline

- 1917-1920: Pierre Fatou and Gaston Julia publish competing studies of iterating rational functions in the complex plane; Julia's 1918 memoir won the Grand Prix of the French Academy. **(unverified dates and prize; see MacTutor history for context)** Source: https://mathshistory.st-andrews.ac.uk/HistTopics/fractals
- 1968: Aristid Lindenmayer, a biologist, introduces a formal method (L-systems) for modelling plant development. Wolfram's notes give work starting in 1967. Sources: https://gauss.math.yale.edu/fractals/IntroToFrac/InitGen/LSystems/LSysHist.html , https://wolframscience.com/nksonline/page-1005d/
- 1975: Mandelbrot coins the word "fractal". **(unverified in this pass)**
- 1978: Robert Brooks and Peter Matelski publish the first image of the set now called the Mandelbrot set, without exploring it deeply. Source: https://mrob.com/pub/muency/history.html
- 1979-1980: Mandelbrot, at IBM, studies the set independently while working on Julia and Fatou sets; one source credits Mandelbrot and IBM programmers with the first fractal printouts in 1979. Sources: https://mrob.com/pub/muency/history.html , https://mathshistory.st-andrews.ac.uk/HistTopics/fractals
- 1981: John Hutchinson's paper "Fractals and self-similarity" lays the mathematics of iterated function systems. **(unverified)**
- 1982: Mandelbrot's book *The Fractal Geometry of Nature*. **(unverified date in this pass)**
- 1985-1988: Michael Barnsley popularises iterated function systems (the Barnsley fern; book *Fractals Everywhere*, 1988). Source for the fern/IFS work: https://mathshistory.st-andrews.ac.uk/HistTopics/fractals ; book date **(unverified)**
- 1988, spring-September: Bert Tyler writes FRACT386 on a new IBM PS/2 386 and uploads it with full source to Byte Magazine's online storage. Source: https://fractint.org/
- 1988-1989: With version 4.0 and Mike Kelly's contribution, the group takes the name Stone Soup Group (after the folk tale); the program becomes Fractint. Sources: https://fractint.org/ , https://en.wikipedia.org/wiki/Fractint
- 1992: Scott Draves creates the fractal flame algorithm (date per a Wikipedia mirror; conflicts in sources). Source: https://en.wikipedia.org/wiki/Electric_Sheep
- 1999: Electric Sheep, a distributed screensaver that evolves fractal flames by audience votes, first released. Source: https://en.wikipedia.org/wiki/Electric_Sheep
- 1998 onward: Inigo Quilez begins demoscene productions; Luxo 4k (raymarched Julia fractal SDF on GPU in 4096 bytes) wins BCN Party 2007. Source: https://iquilezles.org/demoscene
- 2003: Draves and Reckase, "The Fractal Flame Algorithm" paper. **(unverified; reported at https://flam3.com/flame.pdf, not fetched)**
- 2005: Draves, "The Electric Sheep Screen-Saver: A Case Study in Aesthetic Evolution", EvoMusArt05. Source: https://en.wikipedia.org/wiki/Electric_Sheep
- 2007: Daniel White proposes on Fractal Forums a 3D formula replacing complex multiplication's rotation with rotation about two angles; he names the target "Mandelbulb". Source: https://www.ams.org/journals/notices/202204/rnoti-p624.pdf
- 2009, about August: Paul Nylander renders the power-8 Mandelbulb, the form now usually shown. Sources: https://www.ams.org/journals/notices/202204/rnoti-p624.pdf , https://www.rudyrucker.com/blog/2009/09/15/in-search-of-the-mandelbulb/ , https://www.scientificamerican.com/blog/cocktail-party-physics/meet-the-mandelbulb/
- 2009, December: Tom Beddard (subblue) publishes a GPU Mandelbulb ray tracer. Source: https://dcmpx.remotevs.com/com/subblue/www/PL/blog/2009/12/13/mandelbulb (mirror of subblue.com)
- 2010: Tom Lowe finds the Mandelbox, built from box folds and sphere folds, after reading White's account. Source: https://www.ams.org/journals/notices/202204/rnoti-p624.pdf
- 2012: A fractal-heavy 4k wins Assembly 2012's 4k demo competition (title not confirmed). Source: https://scitepress.org/publishedPapers/2024/123805/pdf/index.html
- 2019-2020: Fractal 4k and Mandelbox demos continue (Kali at Evoke 2019; Peisik's "Eternal Fortress", Revision Online 2020, with a distance estimator credited to Rrola after Buddhi). Source: https://peisik.untergrund.net/rendering_eternal_fortress

## People and contributions

**Pierre Fatou (1878-1929) and Gaston Julia (1893-1978).** Founded the theory of iterating complex rational maps. The "Fatou set" (where iteration is stable) and the "Julia set" (its chaotic boundary) are named after them. Life dates **(unverified)**. Source: https://mathshistory.st-andrews.ac.uk/HistTopics/fractals

**Robert Brooks and Peter Matelski.** Published the first picture of the Mandelbrot set in 1978. Fairness in `explain` means naming them. Source: https://mrob.com/pub/muency/history.html

**Benoit Mandelbrot (1924-2010).** Coined "fractal", studied the set at IBM, and wrote the books that brought fractal geometry to a wide audience. The set bears his name. Source: https://mathshistory.st-andrews.ac.uk/HistTopics/fractals

**John Hutchinson and Michael Barnsley.** Hutchinson gave the mathematics of self-similar sets as fixed points of contraction maps (1981, unverified); Barnsley turned it into iterated function systems, the chaos game, the fern, and image compression work. Source: https://mathshistory.st-andrews.ac.uk/HistTopics/fractals

**Aristid Lindenmayer (1925-1989).** Biologist; L-systems, rewriting grammars for plant growth. Later extended with Przemyslaw Prusinkiewicz (*The Algorithmic Beauty of Plants*, 1990, unverified in this pass). Source: https://gauss.math.yale.edu/fractals/IntroToFrac/InitGen/LSystems/LSysHist.html

**Bert Tyler, Mike Kelly, Tim Wegner and the Stone Soup Group.** Fractint began as Tyler's FRACT386 (1988); Kelly's contribution led to version 4.0 and the group name; Wegner maintains the site and source tree. Fractint used integer maths to run fast on 1980s PCs. Source: https://fractint.org/

**Scott Draves.** Fractal flame algorithm (nonlinear IFS variations, log-density colouring), flam3 renderer, and Electric Sheep, a crowd-voted evolving screensaver. Erik Reckase co-authored the flame paper (unverified). Source: https://en.wikipedia.org/wiki/Electric_Sheep

**Daniel White.** Amateur who searched for a "true" 3D Mandelbrot and proposed the spherical-coordinate power formula; named the Mandelbulb. Source: https://www.ams.org/journals/notices/202204/rnoti-p624.pdf

**Paul Nylander.** Used higher powers (power 8) and produced the renders that made the Mandelbulb famous. Source: https://www.ams.org/journals/notices/202204/rnoti-p624.pdf

**Tom Lowe.** Mandelbox (2010), a folding-based 3D fractal family with architectural forms. Source: https://www.ams.org/journals/notices/202204/rnoti-p624.pdf

**Rudy Rucker.** Wrote an early public account of the Mandelbulb search (2009) and had earlier written about 3D Mandelbrot attempts. Source: https://www.rudyrucker.com/blog/2009/09/15/in-search-of-the-mandelbulb/

**Inigo Quilez (iq).** Demoscener and graphics author; about 60 productions since 1998, including raymarched fractal 4k intros; his articles on distance functions and Shadertoy (co-founded with Pol Jeremias, unverified here) spread GPU fractal techniques. Source: https://iquilezles.org/demoscene

**Other demoscene and forum figures.** Kali (fractal folding shaders), Rrola and Buddhi (Mandelbox distance estimators), Mikael Hvidtfeldt Christensen (Syntopia blog series on distance-estimated 3D fractals, Fragmentarium). Sources: https://peisik.untergrund.net/rendering_eternal_fortress ; Hvidtfeldt series **(unverified link, not fetched)**

## Notable software and licence

| Software | Who | Licence (as found) | Source |
|---|---|---|---|
| Fractint (DOS), WinFract | Stone Soup Group | Freeware; copyright kept by the group; may be copied unmodified, not sold; source free, terms in FRACTSRC.DOC ("in most cases we just want credit") | https://fractint.org/ , https://discmaster.textfiles.com/view/32585/INFESPGAMES.mdf/os2/fractint/intro.doc |
| Iterated Dynamics | Fork of Fractint 20.04p4 | Not checked (source on GitHub) | https://en.wikipedia.org/wiki/Fractint |
| ManPWin | Fork of WinFract 18 | Not checked | https://en.wikipedia.org/wiki/Fractint |
| flam3 | Scott Draves et al. | GPL-3.0 (GitHub metadata) | https://awesome.ecosyste.ms/projects/github.com%2Fscottdraves%2Fflam3 |
| Electric Sheep client | Scott Draves | GPL (v2 per one listing); server not open, freemium model | https://en.wikipedia.org/wiki/Electric_Sheep |
| Electric Sheep content | Draves and users | Generated sheep and movies CC-BY-NC; user-made parameters CC-BY | https://en.wikipedia.org/wiki/Electric_Sheep |
| GIMP "flame" plug-in | Based on Draves' flame code | GPL (part of GIMP) | https://cdn05042023.gitlink.org.cn/dnrops/gimp/src/commit/af9a052b26da28ca0bf72cd0259d426d17b4929a/plug-ins/flame |
| Mandelbulb 3D, Mandelbulber, Fragmentarium, Apophysis, Chaotica, Ultra Fractal, XaoS | Various | Not checked in this pass; belongs in a later software-survey file | - |

## Implications for fractalwright

What `explain` should say:
- Present the Mandelbrot set with its lineage: Fatou and Julia's iteration theory, first pictured by Brooks and Matelski (1978), studied and popularised by Mandelbrot (1979-1982).
- Present the Mandelbulb as "found by Daniel White and Paul Nylander on Fractal Forums, 2007-2009" and the Mandelbox as "found by Tom Lowe, 2010". Say that there is no true 3D analogue of complex multiplication, which is why these are formulas chosen for looks rather than unique extensions.
- For IFS, name Hutchinson (theory) and Barnsley (popularisation, chaos game, fern). For L-systems, name Lindenmayer.
- For fractal flames, name Scott Draves and the flame algorithm; for audio visuals, note that Electric Sheep is not audio-reactive while MilkDrop and AVS (covered in another reference) are.

Terms to use consistently: Julia set, Fatou set, Mandelbrot set, escape-time, iterated function system (IFS), chaos game, L-system, fractal flame, variation, distance estimator (DE), raymarching (sphere tracing), box fold, sphere fold, Mandelbulb, Mandelbox, 4k intro.

Credit lines (suggested defaults in generated metadata and `explain` output):
- "Mandelbulb formula: Daniel White and Paul Nylander (2009)."
- "Mandelbox formula: Tom Lowe (2010)."
- "Fractal flame algorithm: Scott Draves."
- "Inspired by Fractint (Stone Soup Group)" only if a Fractint formula or palette is reused, and then check FRACTSRC.DOC terms first.

Design consequences:
- Do not copy flam3 or Electric Sheep code into a non-GPL plugin; reimplement the flame algorithm from the paper or keep any flam3 use as an external optional tool.
- Do not ship Electric Sheep sheep files or movies as bundled examples (CC-BY-NC content blocks commercial use and needs attribution).
- Distance estimators found on forums and Shadertoy are often unlicensed or CC-BY-NC-SA (Shadertoy default, unverified); write fractalwright's own and cite the technique, not the code.

## Open questions

- Exact dates: Fatou and Julia papers, Julia's prize, "fractal" coinage, Hutchinson 1981, Fractals Everywhere 1988, flame algorithm 1992 vs Draves-Reckase paper 2003. Fetch primary sources (MacTutor biographies, flam3.com/flame.pdf).
- Fractal Forums is archived (fractalforums.com is read-only; successor fractalforums.org) - the original Mandelbulb and Mandelbox threads were not fetched; link to archive copies.
- FRACTSRC.DOC wording not read; needed before reusing any Fractint formula files or colour maps.
- Licence of Iterated Dynamics and ManPWin forks not checked.
- Shadertoy default licence for shaders (believed CC-BY-NC-SA 3.0) not verified.
- Which demoscene productions to cite as canonical fractal works (Pouet search not done).

## Sources (accessed 2026-11-14)

- https://mathshistory.st-andrews.ac.uk/HistTopics/fractals
- https://mrob.com/pub/muency/history.html
- https://gauss.math.yale.edu/fractals/IntroToFrac/InitGen/LSystems/LSysHist.html
- https://wolframscience.com/nksonline/page-1005d/
- https://fractint.org/
- https://en.wikipedia.org/wiki/Fractint
- https://discmaster.textfiles.com/view/32585/INFESPGAMES.mdf/os2/fractint/intro.doc
- https://en.wikipedia.org/wiki/Electric_Sheep
- https://awesome.ecosyste.ms/projects/github.com%2Fscottdraves%2Fflam3
- https://sprott.physics.wisc.edu/pubs/paper303.htm
- https://www.ams.org/journals/notices/202204/rnoti-p624.pdf
- https://www.rudyrucker.com/blog/2009/09/15/in-search-of-the-mandelbulb/
- https://www.scientificamerican.com/blog/cocktail-party-physics/meet-the-mandelbulb/
- https://dcmpx.remotevs.com/com/subblue/www/PL/blog/2009/12/13/mandelbulb
- https://iquilezles.org/demoscene
- https://peisik.untergrund.net/rendering_eternal_fortress
- https://scitepress.org/publishedPapers/2024/123805/pdf/index.html
