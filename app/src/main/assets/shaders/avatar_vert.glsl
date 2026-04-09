// Linear Blend Skinning vertex shader.
// Supports up to 48 bone matrices with 4 joint influences per vertex.

precision mediump float;

// Vertex attributes
attribute vec3 a_position;
attribute vec3 a_normal;
attribute vec4 a_joints;   // joint indices (0-47)
attribute vec4 a_weights;  // joint weights (sum to 1.0)

// Uniforms
uniform mat4 u_mvp;        // model-view-projection
uniform mat4 u_model;      // model matrix (for world-space normals)
uniform mat4 u_joints[48]; // bone matrices (world × inverse-bind)

// Varyings → fragment shader
varying vec3 v_normal;
varying vec3 v_worldPos;

void main() {
    // Compute skinned position and normal via LBS
    // skin_matrix = sum(weight_i * joint_matrix_i)
    mat4 skinMatrix =
        a_weights.x * u_joints[int(a_joints.x)] +
        a_weights.y * u_joints[int(a_joints.y)] +
        a_weights.z * u_joints[int(a_joints.z)] +
        a_weights.w * u_joints[int(a_joints.w)];

    vec4 skinnedPos = skinMatrix * vec4(a_position, 1.0);
    vec4 skinnedNorm = skinMatrix * vec4(a_normal, 0.0);

    v_worldPos = (u_model * skinnedPos).xyz;
    v_normal = normalize((u_model * skinnedNorm).xyz);

    gl_Position = u_mvp * skinnedPos;
}
