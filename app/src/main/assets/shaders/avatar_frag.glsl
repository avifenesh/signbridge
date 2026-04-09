// Fragment shader: diffuse lighting + confidence glow border.

precision mediump float;

varying vec3 v_normal;
varying vec3 v_worldPos;

// Lighting
uniform vec3 u_lightDir;       // directional light (normalized, world space)
uniform vec3 u_lightColor;     // light color (typically white)
uniform vec3 u_ambientColor;   // ambient fill

// Material (simple diffuse — no textures in V1)
uniform vec3 u_baseColor;      // avatar skin/body color

// Confidence glow
uniform vec3 u_glowColor;      // green/yellow/red based on confidence
uniform float u_glowStrength;  // 0.0 = no glow, 1.0 = full glow

void main() {
    // Lambertian diffuse
    vec3 N = normalize(v_normal);
    float NdotL = max(dot(N, u_lightDir), 0.0);
    vec3 diffuse = u_baseColor * u_lightColor * NdotL;
    vec3 ambient = u_baseColor * u_ambientColor;

    vec3 color = ambient + diffuse;

    // Rim/edge glow for confidence indicator.
    // Uses a fresnel-like effect: edges glow more than centers.
    vec3 viewDir = normalize(-v_worldPos); // camera at origin in view space
    float rim = 1.0 - max(dot(N, viewDir), 0.0);
    rim = smoothstep(0.4, 1.0, rim);

    color += u_glowColor * u_glowStrength * rim * 0.6;

    // Slight tone-mapping to avoid oversaturation
    color = color / (color + vec3(1.0));

    gl_FragColor = vec4(color, 1.0);
}
