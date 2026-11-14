# 10 - Fractals and AI models

Research note for fractalwright. Accessed 2026-11-14. Scope: putting an exact fractal render through AI
image or video models on Mark's ComfyUI hosts. Which models are installed, where they run and how to drive them belongs to the
comfyui-gen skill (C:/Users/m4bwa/.claude/skills/comfyui-gen/SKILL.md), and this note does not repeat it.
Owner rules that apply here: no Krea 2 in anything that may be sold, and no Meta-gated models.

## The core point

The maths gives exact geometry: an escape-time or IFS render is correct to the pixel and can be reproduced from its
parameters. A diffusion model gives only plausibility. Every AI route trades exactness for texture, material,
lighting or scene context. So **an AI pass is always an optional stage after the exact render, never part of the
exact path.** Any output that went through a model has to be labelled as interpreted, not computed.

## Routes

The model column names models comfyui-gen already runs where possible. Host follows comfyui-gen: stills on the
idle host (Mac 192.168.86.100:8188 or PC 127.0.0.1:8199), video on the PC only.

| Route | What it adds | Failure modes on fractals | Candidate model | Licence class | Host |
|---|---|---|---|---|---|
| img2img, low denoise (about 0.2-0.4) | Surface texture, grain, colour grading, a painterly or photographic finish | Fine filaments near the set boundary get smeared or merged; thin spirals thicken; above about 0.5 denoise the model redraws the shapes | FLUX.2 Klein 4B (edit), Z-Image Turbo | Apache 2.0, open weights, commercial use allowed (Klein 4B: model card; Z-Image: secondary source, check the card) | Mac or PC |
| Edit model with the render as reference ("make this a glass sculpture") | Materials, lighting, a scene (fractal as a building, a coral reef, a landscape) | Keeps the overall silhouette but not the exact self-similar structure; symmetry drifts | FLUX.2 Klein 4B edit; FLUX.3 edit (per comfyui-gen) | Klein 4B Apache 2.0; FLUX.3: check its card before any commercial use | PC (FLUX.3), either (Klein) |
| ControlNet canny/lineart from the render | New content that follows the outline | Canny on a fractal gives thousands of edges, and the model either ignores most of them or fills everything with noise. Keep only the coarse boundary (downsample first) | SD1.5/SDXL ControlNets; Flux-family control if installed | Mostly OpenRAIL/OpenRAIL++ (commercial use allowed with use restrictions) | Mac or PC |
| ControlNet depth (from a 3D fractal's depth pass, or a heightfield from smoothed escape time) | Turns a Mandelbulb or a heightfield into a believable landscape, cliff or architecture | Depth estimators on a 2D render invent depth; use the exact depth exported from the ray marcher instead | Any depth ControlNet; Depth Anything 3 for estimates (comfyui-gen motion-control) | Varies; check each | Either |
| ControlNet tile / tiled-diffusion upscale | Detail at higher resolution | **Invents detail.** Low control strength (under about 0.5) leads to hallucination (forum reports). The invented detail is not the true deeper structure, so self-similarity breaks. Better to re-render at the target resolution, which is exact and costs little | SD tile ControlNet, SeedVR2 (comfyui-gen upscale) | OpenRAIL; SeedVR2 Apache 2.0 (check) | Either |
| Illusion / pattern ControlNet (QR Code Monster) | The fractal hidden in a scene as a large-scale luminance pattern | Only coarse luminance survives; fine detail is lost by design | monster-labs QR Code Monster v2 (SD1.5, SDXL) | OpenRAIL++ | Either |
| Style reference (IP-Adapter) | The look of a fractal applied to other content | Copies the palette and texture, not the geometry | IP-Adapter for SDXL/Flux | Mostly Apache or OpenRAIL; check per checkpoint | Either |
| Video-to-video, with an exact zoom as the motion source | A textured, "filmed" deep zoom; fractal-as-landscape flythrough | Flicker between frames (a texture boiling from frame to frame); the model drops the zoom's exact scale rate; detail at the vanishing point gets invented | Wan2.1 VACE (depth/V2V); MiniMax H3 image-to-video for single shots (comfyui-gen) | VACE Apache 2.0; H3 per comfyui-gen | PC only |
| Image-to-video from one fractal still | Short ambient motion | No relation to the true zoom; the motion is invented | MiniMax H3, LTX-2.5 (comfyui-gen) | Per comfyui-gen | PC only |

Known failure modes, in sum:
- **Smearing of fine detail.** VAEs compress 8x8 pixels into one latent, so structures thinner than a few pixels
  near the boundary cannot survive an encode and decode, even at denoise 0. Test: encode and decode the render with no
  denoise and compare. (Inference from the latent-diffusion design; no fractal-specific source found.)
- **Symmetry loss.** Mandelbrot conjugate symmetry and Julia point symmetry are not kept by any model. Mirror
  after the AI pass if symmetry must hold, or accept the loss.
- **Invented self-similarity.** Upscalers and tile passes add plausible "more fractal" texture that is not the set.
- **Temporal flicker** in video passes over high-frequency detail.

## What a model can add that maths cannot

- Materials and lighting from the physical world: glass, metal, coral, moss, stone, subsurface scattering, without writing a renderer.
- Scene context: the fractal as a city, a temple, an alien landscape, a reef, a tree, a tattoo, a printed fabric.
- A finish: film grain, paint, a photographic lens look.
- Style and atmosphere: fog and depth haze. A ray marcher can do these too, but only with more work.
Everything else (structure, zoom, colour mapping, exact repeats) is better and cheaper done in code.

## LoRA survey

| LoRA | Base | Where | Licence / note |
|---|---|---|---|
| Image Complexity and fractal art (+ soft version) | Flux.1 dev | civitai.com/models/1348637 | Flux.1 dev base is non-commercial for the weights; outputs per the BFL licence. Do not use in commercial work without checking |
| Krea 2 - Recursive Fractalism | Krea 2 | civitai.com/models/2815638 | **Excluded: Krea 2 (owner rule)** |
| Fractalia | SD 1.5 | civarchive.com/models/302341 | Archived mirror; SD1.5 CreativeML OpenRAIL-M; check the LoRA's own Civitai permissions |
| Mandelbrot Fractal Style (trigger ral-mndlbrt) | SDXL | huggingface.co/Muapi/mandelbrot-fractal-style-sdxl | Mirror of a Civitai upload; licence unclear |
| Mandelbulb Flux XL | Flux / SDXL | huggingface.co/Muapi/mandelbulb-flux-xl | Mirror; licence unclear |
| Fractal Geometry Style | FLUX + SDXL + 1.5 | huggingface.co/Jonjew/FractalGeometryStyle | Mirror; licence unclear |
| FractalLand v0.1 | FLUX.1 dev | huggingface.co/Borcherding/FLUX.1-dev-LoRA-FractalLand-v0.1 | Flux.1 dev non-commercial base |
| mandelbrot-fractals | (see card) | huggingface.co/baruga/mandelbrot-fractals | Check the card |

Findings: no fractal LoRA was found for the bases comfyui-gen prefers (FLUX.2 Klein 4B, Z-Image, FLUX.3). The
existing ones target SD1.5, SDXL, Flux.1 dev (non-commercial base) or Krea 2 (excluded). Many Hugging Face copies are
mirrors of Civitai uploads with unclear licences. Since fractalwright makes exact fractal images at any volume,
**training our own LoRA on our own renders** (clean provenance, any base) is the better route if a style LoRA is
ever needed. Licence rule: the LoRA inherits its base model's licence and adds its own.

## Recommended default

1. The exact render path uses no AI: parameters in, pixels out, reproducible, and the parameters are stored with the image.
2. AI passes are opt-in "interpret" stages that take a finished render plus an intent (texture, material, scene,
   video finish). They write to a separate output, marked as interpreted, with the model, licence and seed recorded.
3. Default models are open-weight models with commercial use allowed: FLUX.2 Klein 4B for edit and img2img, Z-Image Turbo as fallback,
   Wan VACE (Apache 2.0) for V2V. Flux.1 dev bases and Krea 2 are never used for anything sellable.
4. Never use AI to upscale or deepen a fractal; re-render at the target resolution or zoom instead.
5. For video, render the exact zoom first, then optionally run V2V at low strength with depth control taken from the exact render.

## Hand-over to comfyui-gen

fractalwright hands comfyui-gen: the exact render (PNG, plus a depth or edge pass when it exists), the intent in
words, a strength (denoise or control weight) and the licence class required (sellable or not). comfyui-gen picks the host
and the workflow, runs it, and returns the outputs plus model, seed and settings. fractalwright keeps no model
lists, host addresses or workflows; those live in comfyui-gen. A side-by-side of exact versus interpreted goes to
artwright-judge or an askwright page for Mark to pick from.

## Implications for fractalwright

- Keep a manifest per image: `exact: true/false`, parameters, and for AI passes the model, licence class, seed and the source render hash.
- Export auxiliary passes from the renderer (depth, normal, smoothed escape-time height, coarse edge mask); these make
  far better control images than estimates.
- Offer a "VAE round-trip check" (encode/decode with no denoise) so users see what detail any AI pass will lose.
- Offer symmetry re-imposition after an AI pass as an option.
- Video: the exact zoom stays the master; an AI version is a variant, never a replacement.
- The plugin itself downloads and bundles no model or LoRA.

## Background: fractals as pretraining data

Kataoka et al., "Pre-training without Natural Images" (ACCV 2020, best paper honourable mention) introduced
formula-driven supervised learning: FractalDB, images and labels generated from IFS fractals with no natural
images. Models pre-trained on it partly matched ImageNet/Places pre-training without beating it in every setting. The follow-up
"Can Vision Transformers Learn without Natural Images?" (AAAI-22) reported ViT results comparable to SimCLRv2 and
MoCov2 pre-training. Relevance here: fractalwright's IFS renderer could export FractalDB-style labelled sets, which
are free of copyright and personal-data problems. This is a possible export feature, not a core one.

## Open questions

- Z-Image Turbo licence: only a secondary source (invideo.io) says Apache 2.0; confirm on the official model card.
- FLUX.3 licence class for commercial work: check before any sellable use (comfyui-gen should record it).
- SeedVR2 and Depth Anything 3 licence classes: not verified in this pass.
- Is there a Flux-family or Z-Image tile/depth ControlNet installed on either host? Ask comfyui-gen; do not install.
- Owner decision: should fractalwright ship any AI stage in v1, or only document the hand-over?
- Worth measuring: how much boundary detail the Klein and Z-Image VAEs lose at 1024 px on a deep zoom (needs a run on the hosts).

## Sources (accessed 2026-11-14)

- Kataoka et al., Pre-training without Natural Images: https://arxiv.org/abs/2101.08515 ;
  https://openaccess.thecvf.com/content/ACCV2020/html/Kataoka_Pre-training_without_Natural_Images_ACCV_2020_paper.html
- Can Vision Transformers Learn without Natural Images? (AAAI-22): https://aaai-2022.virtualchair.net/poster_aaai7546
- FLUX.2 [klein] (BFL): https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence ; https://bfl.ai/models/flux-2-klein
- FLUX.2 klein base 4B card: https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B
- Z-Image licence (secondary): https://invideo.io/blog/open-source-image-models-licenses/
- QR Code Monster v2 (OpenRAIL++): https://huggingface.co/monster-labs/control_v1p_sd15_qrcode_monster
- VACE (Apache 2.0, depth V2V): https://github.com/ali-vilab/VACE ; https://docs.comfy.org/tutorials/video/wan/vace
- Tile ControlNet behaviour: https://replicate.com/lucataco/controlnet-tile/readme ;
  https://replicate.com/fermatresearch/high-resolution-controlnet-tile ;
  forum report (anecdotal) https://redlib.ssps.io/r/StableDiffusion/comments/1e3v6jy/tile_controlnet_tiled_diffusion_very_realistic/ldkmemn
- LoRAs: https://civitai.com/models/1348637 ; https://civitai.com/models/2815638 ; https://civarchive.com/models/302341 ;
  https://huggingface.co/Muapi/mandelbrot-fractal-style-sdxl ; https://huggingface.co/Muapi/mandelbulb-flux-xl ;
  https://huggingface.co/Jonjew/FractalGeometryStyle ;
  https://huggingface.co/Borcherding/FLUX.1-dev-LoRA-FractalLand-v0.1 ; https://huggingface.co/baruga/mandelbrot-fractals ;
  https://civitai.com/models/3026561 (prompt guide)
- Model and host inventory: comfyui-gen skill, C:/Users/m4bwa/.claude/skills/comfyui-gen/SKILL.md (local)
