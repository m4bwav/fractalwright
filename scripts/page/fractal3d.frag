#version 300 es
// fractalwright 3D shader (own work, no copied code). Sphere tracing after Hart 1996:
// march a ray by the distance estimate DE(p), a lower bound on the distance to the set.
// DEs written from the published formulas (references/07-3d.md section 3):
//   Mandelbulb / quaternion Julia: 0.5 * r * log(r) / dr with a running derivative dr;
//   Mandelbox: |z| / |dr| after box fold, sphere fold, scale; Menger: box minus crosses;
//   hybrid: a box fold before each Mandelbulb step (folds are reflections, dr unchanged).
// Every remedy is a switch so the gate can render it alone. Deterministic: no time, no random.
precision highp float;
precision highp int;
uniform vec2 u_size;
uniform vec3 u_eye, u_target;
uniform float u_fov;        // vertical, radians
uniform float u_roll;       // radians
uniform int u_formula;      // 0 mandelbulb, 1 mandelbox, 2 quatjulia, 3 menger, 4 hybrid
uniform int u_iter;
uniform float u_power;      // mandelbulb / hybrid
uniform float u_scale;      // mandelbox
uniform vec4 u_jc;          // quaternion julia c
uniform int u_steps;
uniform float u_fudge, u_maxdist, u_eps;   // eps: hit threshold per unit distance (pixel cone)
uniform vec3 u_light, u_bg, u_fogcol;
uniform vec3 u_a, u_b, u_cc, u_d;          // cosine palette
uniform int u_ao, u_shadow, u_fog, u_trap, u_dof, u_aa;
uniform float u_aperture, u_focus, u_fogdens;
uniform int u_spp;
out vec4 frag;

vec4 trap;
int escN;

vec3 pal(float t) { return u_a + u_b * cos(6.283185307179586 * (u_cc * t + u_d)); }

float deBulb(vec3 c, bool fold) {
  vec3 z = c;
  float dr = 1.0, r = length(z);
  trap = vec4(abs(z), dot(z, z));
  escN = u_iter;
  for (int i = 0; i < 64; i++) {
    if (i >= u_iter) break;
    if (fold) z = clamp(z, -1.0, 1.0) * 2.0 - z;
    r = length(z);
    if (r > 2.0) { escN = i; break; }
    float th = acos(clamp(z.z / r, -1.0, 1.0));
    float ph = atan(z.y, z.x);
    dr = u_power * pow(r, u_power - 1.0) * dr + 1.0;
    float rp = pow(r, u_power);
    th *= u_power; ph *= u_power;
    z = rp * vec3(sin(th) * cos(ph), sin(th) * sin(ph), cos(th)) + c;
    trap = min(trap, vec4(abs(z), dot(z, z)));
  }
  r = length(z);
  return 0.5 * log(max(r, 1e-6)) * r / dr;
}

float deBox(vec3 c) {
  vec3 z = c;
  float dr = 1.0;
  trap = vec4(abs(z), dot(z, z));
  escN = u_iter;
  for (int i = 0; i < 64; i++) {
    if (i >= u_iter) break;
    z = clamp(z, -1.0, 1.0) * 2.0 - z;            // box fold
    float r2 = dot(z, z);
    if (r2 < 0.25) { z *= 4.0; dr *= 4.0; }        // sphere fold, min radius^2 0.25, fixed 1
    else if (r2 < 1.0) { z /= r2; dr /= r2; }
    z = u_scale * z + c;
    dr = dr * abs(u_scale) + 1.0;
    trap = min(trap, vec4(abs(z), dot(z, z)));
    if (dot(z, z) > 1e4) { escN = i; break; }
  }
  return length(z) / abs(dr);
}

vec4 qmul(vec4 a, vec4 b) {
  return vec4(a.x * b.x - dot(a.yzw, b.yzw), a.x * b.yzw + b.x * a.yzw + cross(a.yzw, b.yzw));
}

float deQJulia(vec3 p) {
  vec4 q = vec4(p, 0.0);
  float dq = 1.0;                                 // |q'|, q' <- 2 q q' so |q'| <- 2 |q| |q'|
  trap = vec4(abs(q.xyz), dot(q, q));
  escN = u_iter;
  for (int i = 0; i < 64; i++) {
    if (i >= u_iter) break;
    dq = 2.0 * length(q) * dq;
    q = qmul(q, q) + u_jc;
    trap = min(trap, vec4(abs(q.xyz), dot(q, q)));
    if (dot(q, q) > 256.0) { escN = i; break; }
  }
  float r = length(q);
  return 0.5 * r * log(max(r, 1e-6)) / dq;
}

float sdBox(vec3 p, vec3 b) {
  vec3 q = abs(p) - b;
  return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
}

// Menger sponge from its definition: the unit cube, minus at each level k a cross of three
// square bars (half width 1/3 of the cell) in every cell of size 2 / 3^k.
float deMenger(vec3 p) {
  float d = sdBox(p, vec3(1.0));
  float cell = 2.0;                               // cell edge at this level
  trap = vec4(abs(p), dot(p, p));
  escN = u_iter;
  for (int i = 0; i < 16; i++) {
    if (i >= u_iter) break;
    vec3 q = mod(p + 1.0, cell) - 0.5 * cell;     // local cell coordinates, centred
    vec3 a = abs(q);
    float h = cell / 6.0;                         // bar half width
    float bx = max(a.y, a.z), by = max(a.x, a.z), bz = max(a.x, a.y);
    float hole = min(bx, min(by, bz)) - h;        // distance to the cross, negative inside it
    d = max(d, -hole);
    trap = min(trap, vec4(a / cell, hole * hole));
    cell /= 3.0;
  }
  return d;
}

float DE(vec3 p) {
  if (u_formula == 0) return deBulb(p, false);
  if (u_formula == 1) return deBox(p);
  if (u_formula == 2) return deQJulia(p);
  if (u_formula == 3) return deMenger(p);
  return deBulb(p * u_scale, true) / u_scale;      // hybrid: u_scale shrinks the set to bulb size
}

vec3 normalAt(vec3 p, float e) {
  vec2 k = vec2(e, 0.0);
  return normalize(vec3(DE(p + k.xyy) - DE(p - k.xyy), DE(p + k.yxy) - DE(p - k.yxy), DE(p + k.yyx) - DE(p - k.yyx)));
}

float ambientOcclusion(vec3 p, vec3 n, float scale) {
  float occ = 0.0, w = 1.0;
  for (int i = 1; i <= 5; i++) {
    float h = scale * float(i);
    occ += w * max(h - DE(p + n * h), 0.0) / h;
    w *= 0.6;
  }
  return clamp(1.0 - 0.9 * occ, 0.0, 1.0);
}

float softShadow(vec3 p, vec3 l, float start) {
  float res = 1.0, t = start;
  for (int i = 0; i < 96; i++) {
    float h = DE(p + l * t);
    if (h < 1e-4) return 0.0;
    res = min(res, 10.0 * h / t);
    t += clamp(h * u_fudge, 1e-3, 0.3);
    if (t > u_maxdist) break;
  }
  return clamp(res, 0.0, 1.0);
}

// Deterministic per-sample offsets: a fixed low-discrepancy sequence (R2 additive recurrence).
vec2 r2seq(int i) { return fract(0.5 + float(i) * vec2(0.7548776662466927, 0.5698402909980532)); }

vec3 shade(vec3 ro, vec3 rd) {
  float t = 0.0, d = 0.0;
  int steps = 0;
  bool hit = false;
  for (int i = 0; i < 1024; i++) {
    if (i >= u_steps) break;
    vec3 p = ro + rd * t;
    d = DE(p);
    if (d < u_eps * max(t, 0.05)) { hit = true; steps = i; break; }
    t += d * u_fudge;
    steps = i;
    if (t > u_maxdist) break;
  }
  float sky = 0.5 + 0.5 * rd.y;
  vec3 bg = u_fog == 1 ? mix(u_fogcol * 0.7, u_fogcol, sky) : u_bg;
  if (!hit) return bg;
  vec3 p = ro + rd * t;
  float e = max(u_eps * t * 0.5, 1e-5);
  vec3 n = normalAt(p, e);
  DE(p);                                          // refresh trap and escN at the hit
  vec4 tr = trap;
  vec3 l = normalize(u_light);
  float dif = max(dot(n, l), 0.0);
  vec3 base;
  if (u_trap == 1) {
    vec3 c1 = pal(0.6 * sqrt(tr.w) + 0.1);
    vec3 c2 = vec3(0.95, 0.75, 0.45);
    base = mix(c1, c2, clamp(pow(clamp(tr.x * 2.0, 0.0, 1.0), 0.6), 0.0, 1.0) * 0.5);
    base = mix(base, vec3(0.25, 0.45, 0.65), clamp(1.0 - tr.y * 3.0, 0.0, 1.0) * 0.35);
  } else {
    base = pal(float(steps) / float(u_steps) * 4.0);
  }
  float occ = u_ao == 1 ? ambientOcclusion(p, n, max(0.02, 0.006 * t)) : 1.0;
  float sh = u_shadow == 1 ? softShadow(p + n * e * 4.0, l, e * 10.0) : 1.0;
  vec3 col;
  if (u_ao == 1 || u_shadow == 1) {
    float sky_l = 0.5 + 0.5 * n.y;
    col = base * (1.15 * dif * sh * vec3(1.0, 0.93, 0.82) + 0.22 * sky_l * occ * vec3(0.55, 0.65, 0.9) + 0.06 * occ);
    vec3 h = normalize(l - rd);
    col += 0.25 * pow(max(dot(n, h), 0.0), 32.0) * sh;
  } else {
    col = base * (0.3 + 0.7 * dif);               // flat light: ambient + lambert, no shadow
  }
  if (u_fog == 1) {
    float f = 1.0 - exp(-u_fogdens * t * t);
    vec3 gray = vec3(dot(col, vec3(0.299, 0.587, 0.114)));
    col = mix(col, gray, clamp(f, 0.0, 0.4)); // depth cue: far things lose saturation
    col = mix(col, bg, f);
  }
  return col;
}

void main() {
  vec3 fw = normalize(u_target - u_eye);
  vec3 up0 = vec3(-sin(u_roll), cos(u_roll), 0.0);
  vec3 rt = normalize(cross(fw, up0));
  vec3 up = cross(rt, fw);
  float th = tan(0.5 * u_fov);
  vec3 acc = vec3(0.0);
  int n = max(u_spp, 1);
  for (int s = 0; s < 64; s++) {
    if (s >= n) break;
    vec2 j = (u_aa == 1 && n > 1) ? r2seq(s) : vec2(0.5);
    vec2 uv = (gl_FragCoord.xy - 0.5 + j - 0.5 * u_size) / (0.5 * u_size.y);
    vec3 rd = normalize(fw + th * (uv.x * rt + uv.y * up));
    vec3 ro = u_eye;
    if (u_dof == 1 && n > 1) {
      vec2 lj = r2seq(s + 17);
      float ang = 6.283185307179586 * lj.x, rad = u_aperture * sqrt(lj.y);
      vec3 fp = u_eye + rd * (u_focus / dot(rd, fw));
      ro = u_eye + rad * (cos(ang) * rt + sin(ang) * up);
      rd = normalize(fp - ro);
    }
    acc += shade(ro, rd);
  }
  vec3 col = acc / float(n);
  col = pow(clamp(col, 0.0, 1.0), vec3(1.0 / 2.2));
  frag = vec4(col, 1.0);
}
