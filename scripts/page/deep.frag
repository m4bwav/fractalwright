#version 300 es
// fractalwright GPU perturbation (own work). Python computes the reference orbit Z[m]
// in Decimal and uploads it as an RG32F texture; each pixel iterates its float32 delta
//   dz' = 2 Z[m] dz + dz^2 + dc,   z = Z[m+1] + dz
// with Zhuoran rebasing: when |z - Z[0]| < |dz| or the orbit runs out, dz = z - Z[0], m = 0.
// Scaled phase: while |dz| is tiny the delta is held in pixel units (dz = s * w,
// s = pixel spacing = u_s1 * u_s2), so dc never underflows float32. When |w| passes
// u_T (|dz| about 1e-30) or the orbit runs out, w converts to dz = (w * s1) * s2.
// Output per pixel: (bits of nu, n, rebased, 1); nu = -1 inside. Python colours it.
precision highp float;
precision highp int;
precision highp usampler2D;
uniform vec2 u_size;
uniform float u_rot;
uniform sampler2D u_orbit;
uniform int u_tw;
uniform int u_last;
uniform int u_julia;
uniform int u_maxit;
uniform float u_bail2;
uniform float u_s1, u_s2, u_S, u_T;
uniform vec2 u_z0;
out uvec4 frag;

vec2 orbit(int m) { return texelFetch(u_orbit, ivec2(m % u_tw, m / u_tw), 0).rg; }
vec2 cmul(vec2 a, vec2 b) { return vec2(a.x * b.x - a.y * b.y, a.x * b.y + a.y * b.x); }

void main() {
  vec2 o = gl_FragCoord.xy - 0.5 * u_size;  // pixel units, exact
  float cr = cos(u_rot), sr = sin(u_rot);
  o = vec2(o.x * cr - o.y * sr, o.x * sr + o.y * cr);
  vec2 dz = u_julia == 1 ? o : vec2(0.0);
  vec2 dc = u_julia == 1 ? vec2(0.0) : o;
  bool scaled = true;
  uint rebased = 0u;
  int m = 0;
  for (int i = 0; i < 1000000; i++) {
    if (i >= u_maxit) break;
    vec2 Z = orbit(m);
    if (scaled) dz = 2.0 * cmul(Z, dz) + cmul(dz, dz * u_S) + dc;
    else dz = 2.0 * cmul(Z, dz) + cmul(dz, dz) + dc;
    m++;
    Z = orbit(m);
    if (scaled) {
      if (max(abs(dz.x), abs(dz.y)) <= u_T && m < u_last) continue;
      dz = (dz * u_s1) * u_s2;
      dc = (dc * u_s1) * u_s2;
      scaled = false;
    }
    vec2 z = Z + dz;
    float mag = dot(z, z);
    if (mag > u_bail2) {
      float nu = float(i + 1) + 1.0 - log(log(mag) * 0.5) / log(2.0);
      frag = uvec4(floatBitsToUint(nu), uint(i + 1), rebased, 1u);
      return;
    }
    vec2 e = z - u_z0;
    if (dot(e, e) < dot(dz, dz) || m >= u_last) { dz = e; m = 0; rebased = 1u; }
  }
  frag = uvec4(floatBitsToUint(-1.0), 0u, rebased, 1u);
}
