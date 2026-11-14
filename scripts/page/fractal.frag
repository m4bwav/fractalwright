#version 300 es
// fractalwright escape-time shader (own work, no copied code). One file serves
// the explorer page and the `render --route browser` accelerator.
// Matches fw.py escape_numpy + colour: n counts completed updates at escape
// (1-based), nu = n + 1 - log(log(|z|^2)/2)/log(d), t = nu*density + phase.
precision highp float;
precision highp int;
uniform vec2 u_size;      // canvas pixels (w, h)
uniform vec2 u_c;         // view centre
uniform float u_px;       // complex units per pixel
uniform float u_rot;      // radians
uniform int u_formula;    // 0 mandelbrot, 1 julia, 2 burning-ship, 3 tricorn, 4 multibrot
uniform int u_power;
uniform int u_maxit;
uniform float u_bail2;
uniform vec2 u_k;         // julia c
uniform int u_flip;       // burning ship: mirror y about the centre
uniform int u_paltype;    // 0 cosine, 1 stops
uniform vec3 u_a, u_b, u_cc, u_d;
uniform int u_nstops;
uniform float u_spos[8];
uniform vec3 u_scol[8];
uniform float u_density, u_phase;
uniform vec3 u_inside;
out vec4 frag;

vec3 pal(float t) {
  if (u_paltype == 0) return u_a + u_b * cos(6.283185307179586 * (u_cc * t + u_d));
  float f = t - floor(t);
  for (int i = 0; i < 7; i++) {
    if (i + 1 >= u_nstops) break;
    if (f >= u_spos[i] && f <= u_spos[i + 1]) {
      float w = u_spos[i + 1] - u_spos[i];
      float u = w > 0.0 ? (f - u_spos[i]) / w : 0.0;
      return mix(u_scol[i], u_scol[i + 1], u);
    }
  }
  return u_scol[u_nstops - 1];
}

void main() {
  float dx = (gl_FragCoord.x - 0.5 * u_size.x) * u_px;
  float dy = (gl_FragCoord.y - 0.5 * u_size.y) * u_px;
  float cr = cos(u_rot), sr = sin(u_rot);
  float rx = dx * cr - dy * sr, ry = dx * sr + dy * cr;
  if (u_flip == 1) ry = -ry;
  float x = u_c.x + rx, y = u_c.y + ry;
  float zr, zi, kr, ki;
  if (u_formula == 1) { zr = x; zi = y; kr = u_k.x; ki = u_k.y; }
  else { zr = 0.0; zi = 0.0; kr = x; ki = y; }
  int n = 0;
  float m = 0.0;
  bool esc = false;
  for (int i = 0; i < 1000000; i++) {
    if (i >= u_maxit) break;
    if (u_formula == 2) { zr = abs(zr); zi = abs(zi); }
    else if (u_formula == 3) { zi = -zi; }
    if (u_power == 2) {
      float t = zr * zr - zi * zi + kr;
      zi = 2.0 * zr * zi + ki; zr = t;
    } else {
      float pr = zr, pi = zi;
      for (int j = 1; j < 64; j++) {
        if (j >= u_power) break;
        float t = pr * zr - pi * zi;
        pi = pr * zi + pi * zr; pr = t;
      }
      zr = pr + kr; zi = pi + ki;
    }
    m = zr * zr + zi * zi;
    if (m > u_bail2) { n = i + 1; esc = true; break; }
  }
  if (!esc) { frag = vec4(u_inside, 1.0); return; }
  float nu = float(n) + 1.0 - log(log(m) * 0.5) / log(float(u_power));
  frag = vec4(clamp(pal(nu * u_density + u_phase), 0.0, 1.0), 1.0);
}
