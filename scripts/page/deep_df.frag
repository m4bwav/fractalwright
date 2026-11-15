#version 300 es
// fractalwright GPU perturbation, double-float deltas (own work). Same algorithm as deep.frag
// (Decimal reference orbit, scaled phase, Zhuoran rebasing), but the orbit and every delta
// are float-float pairs (hi + lo, about 48 bits): Dekker/Knuth two-sum and a Veltkamp split
// two-product (no fma). u_one (= 1.0), u_split (= 4097.0) and u_zero (= 0u, see fence) are uniforms so
// ANGLE/HLSL cannot fold (s - a) - b style error terms to zero or reassociate them.
// Orbit texture RGBA32F: (Zr.hi, Zi.hi, Zr.lo, Zi.lo). A complex df is vec4 (re.hi, re.lo, im.hi, im.lo).
precision highp float;
precision highp int;
uniform vec2 u_size;
uniform float u_rot;
uniform sampler2D u_orbit;
uniform int u_tw;
uniform int u_last;
uniform int u_julia;
uniform int u_maxit;
uniform float u_bail2;
uniform vec2 u_s1d;     // s1 as a df pair; s2 is a power of two
uniform float u_s2, u_T;
uniform vec2 u_Sd;      // pixel spacing as a df pair (0 when it underflows float32)
uniform vec4 u_z0d;
uniform float u_one, u_split;
uniform uint u_zero;
out uvec4 frag;

// fence(x): x unchanged, but the compiler cannot see through an XOR with a uniform zero, so it
// cannot rewrite (a + b) - a as b (it did with the u_one multiply alone: two-sum lost its error).
float fence(float x) { return uintBitsToFloat(floatBitsToUint(x) ^ u_zero); }
vec2 two_sum(float a, float b) { float s = fence(a + b); float v = fence(s - a); float e = (a - fence(s - v)) + (b - v); return vec2(s, e); }
vec2 quick(float a, float b) { float s = fence(a + b); float e = b - fence(s - a); return vec2(s, e); }
vec2 split(float a) { float t = fence(u_split * a); float hi = t - fence(t - a); return vec2(hi, a - hi); }
vec2 two_prod(float a, float b) {
  float p = fence(a * b); vec2 A = split(a), B = split(b);
  float e = ((fence(A.x * B.x) - p) + fence(A.x * B.y) + fence(A.y * B.x)) + A.y * B.y;
  return vec2(p, e);
}
vec2 dadd(vec2 a, vec2 b) {
  vec2 s = two_sum(a.x, b.x), t = two_sum(a.y, b.y);
  s.y += t.x; s = quick(s.x, s.y); s.y += t.y; return quick(s.x, s.y);
}
vec2 dmul(vec2 a, vec2 b) { vec2 p = two_prod(a.x, b.x); p.y += a.x * b.y + a.y * b.x; return quick(p.x, p.y); }
vec2 dneg(vec2 a) { return -a; }
vec4 cadd(vec4 a, vec4 b) { return vec4(dadd(a.xy, b.xy), dadd(a.zw, b.zw)); }
vec4 csub(vec4 a, vec4 b) { return vec4(dadd(a.xy, -b.xy), dadd(a.zw, -b.zw)); }
vec4 cmul(vec4 a, vec4 b) {
  return vec4(dadd(dmul(a.xy, b.xy), -dmul(a.zw, b.zw)), dadd(dmul(a.xy, b.zw), dmul(a.zw, b.xy)));
}
vec4 cscale(vec4 a, vec2 s) { return vec4(dmul(a.xy, s), dmul(a.zw, s)); }
float cmax(vec4 a) { return max(abs(a.x), abs(a.z)); }
float cdot(vec4 a) { return a.x * a.x + a.z * a.z; }
vec4 orbit(int m) { vec4 t = texelFetch(u_orbit, ivec2(m % u_tw, m / u_tw), 0); return vec4(t.x, t.z, t.y, t.w); }

void main() {
  vec2 o = gl_FragCoord.xy - 0.5 * u_size;  // pixel units, exact
  float cr = cos(u_rot), sr = sin(u_rot);
  if (u_rot != 0.0) o = vec2(o.x * cr - o.y * sr, o.x * sr + o.y * cr);
  vec4 O = vec4(o.x, 0.0, o.y, 0.0);
  vec4 dz = u_julia == 1 ? O : vec4(0.0);
  vec4 dc = u_julia == 1 ? vec4(0.0) : O;
  bool scaled = true;
  uint rebased = 0u;
  int m = 0;
  for (int i = 0; i < 1000000; i++) {
    if (i >= u_maxit) break;
    vec4 Z = orbit(m);
    vec4 Z2 = 2.0 * Z;  // exact
    if (scaled) dz = cadd(cadd(cmul(Z2, dz), cmul(dz, cscale(dz, u_Sd))), dc);
    else dz = cadd(cadd(cmul(Z2, dz), cmul(dz, dz)), dc);
    m++;
    Z = orbit(m);
    if (scaled) {
      if (cmax(dz) <= u_T && m < u_last) continue;
      dz = cscale(dz, u_s1d) * u_s2;
      dc = cscale(dc, u_s1d) * u_s2;
      scaled = false;
    }
    vec4 z = cadd(Z, dz);
    float mag = cdot(z);
    if (mag > u_bail2) {
      float nu = float(i + 1) + 1.0 - log(log(mag) * 0.5) / log(2.0);
      frag = uvec4(floatBitsToUint(nu), uint(i + 1), rebased, 1u);
      return;
    }
    vec4 e = csub(z, u_z0d);
    if (cdot(e) < cdot(dz) || m >= u_last) { dz = e; m = 0; rebased = 1u; }
  }
  frag = uvec4(floatBitsToUint(-1.0), 0u, rebased, 1u);
}
