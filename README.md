# fractalwright

<!-- banner: .github/images/banner.jpg (owed, Step F) -->

An agent plugin that renders, explains and measures fractals. Every picture comes with a recipe file that redraws it pixel for pixel.

## Quick start

```
python scripts/fw.py doctor
python scripts/fw.py explain mandelbrot
python scripts/fw.py render seahorse -o seahorse.png --size 1280x720
python scripts/fw.py measure box seahorse.png
python scripts/fw.py measure area --size 1024
python scripts/fw.py palette
```

Needs Python 3.9+ and NumPy (a slow pure Python fallback renders small pictures without it).

## Status

Early: stills of five escape-time families and measuring. Video, the interactive page, audio and 3D are planned.

## Licence

MIT.
