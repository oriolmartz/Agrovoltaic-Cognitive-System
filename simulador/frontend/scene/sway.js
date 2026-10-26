/* Balanceig per vent als vèrtexs (GPU): costa gairebé res i s'aplica a cultius i arbres. */
export const SWAY = { uTime: { value: 0 }, uWind: { value: 0 } };

export function enableSway(material, amount = 0.18) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = SWAY.uTime;
    shader.uniforms.uWind = SWAY.uWind;
    shader.uniforms.uAmt = { value: amount };
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uTime;\nuniform float uWind;\nuniform float uAmt;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        #ifdef USE_INSTANCING
          vec2 swp = vec2(instanceMatrix[3].x, instanceMatrix[3].z);
        #else
          vec2 swp = vec2(0.0);
        #endif
        float swh = max(position.y, 0.0);
        float swv = sin(uTime * 1.7 + swp.x * 0.8 + swp.y * 0.6 + swh * 1.3) + 0.5 * sin(uTime * 3.1 + swp.x * 1.9);
        transformed.x += swv * uWind * swh * uAmt;
        transformed.z += swv * uWind * swh * uAmt * 0.45;`);
  };
  material.customProgramCacheKey = () => `sway${amount}`;
  return material;
}
