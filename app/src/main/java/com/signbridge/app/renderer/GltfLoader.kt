package com.signbridge.app.renderer

import android.content.Context
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Minimal GLTF 2.0 / GLB parser.
 *
 * Extracts from the first mesh primitive:
 *  - POSITION, NORMAL attributes
 *  - JOINTS_0, WEIGHTS_0 for skinning
 *  - Triangle indices
 *  - Skin: inverse bind matrices, joint names
 *
 * Supports:
 *  - GLB binary container (single-file)
 *  - Embedded base64 buffers or external .bin (only GLB for now)
 *  - Component types: FLOAT (5126), UNSIGNED_SHORT (5123), UNSIGNED_BYTE (5121)
 *
 * Does NOT support: multiple meshes, morph targets, materials/textures, animations
 * (we drive animation ourselves via quaternion keyframes).
 */
class GltfLoader(private val context: Context) {

    companion object {
        private const val TAG = "GltfLoader"
        private const val GLB_MAGIC = 0x46546C67 // "glTF"
        private const val GLB_JSON_CHUNK = 0x4E4F534A
        private const val GLB_BIN_CHUNK = 0x004E4942
    }

    /**
     * Load a GLB file from assets and return a [GltfModel] ready for GPU upload.
     */
    fun loadFromAssets(assetPath: String): GltfModel {
        val inputStream = context.assets.open(assetPath)
        val bytes = inputStream.readBytes()
        inputStream.close()
        return parseGlb(bytes)
    }

    private fun parseGlb(data: ByteArray): GltfModel {
        val buf = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)

        // GLB header: magic(4) + version(4) + length(4)
        val magic = buf.int
        require(magic == GLB_MAGIC) { "Not a GLB file (magic: ${magic.toString(16)})" }
        val version = buf.int
        require(version == 2) { "Only GLTF 2.0 supported (got $version)" }
        buf.int // total length

        // Chunk 0: JSON
        val jsonLength = buf.int
        val jsonType = buf.int
        require(jsonType == GLB_JSON_CHUNK) { "Expected JSON chunk" }
        val jsonBytes = ByteArray(jsonLength)
        buf.get(jsonBytes)
        val json = JSONObject(String(jsonBytes))

        // Chunk 1: BIN (optional)
        var binData: ByteArray? = null
        if (buf.remaining() >= 8) {
            val binLength = buf.int
            val binType = buf.int
            if (binType == GLB_BIN_CHUNK) {
                binData = ByteArray(binLength)
                buf.get(binData)
            }
        }

        requireNotNull(binData) { "GLB has no binary chunk" }

        return buildModel(json, binData)
    }

    private fun buildModel(json: JSONObject, bin: ByteArray): GltfModel {
        val model = GltfModel()

        val meshes = json.getJSONArray("meshes")
        val mesh = meshes.getJSONObject(0)
        val primitive = mesh.getJSONArray("primitives").getJSONObject(0)
        val attributes = primitive.getJSONObject("attributes")

        val accessors = json.getJSONArray("accessors")
        val bufferViews = json.getJSONArray("bufferViews")

        // Load vertex attributes
        model.positions = readFloatAccessor(accessors, bufferViews, bin, attributes.getInt("POSITION"))
        model.vertexCount = model.positions.size / 3

        model.normals = if (attributes.has("NORMAL")) {
            readFloatAccessor(accessors, bufferViews, bin, attributes.getInt("NORMAL"))
        } else {
            // Generate flat normals (placeholder)
            FloatArray(model.vertexCount * 3)
        }

        model.jointIndices = if (attributes.has("JOINTS_0")) {
            readJointAccessor(accessors, bufferViews, bin, attributes.getInt("JOINTS_0"))
        } else {
            FloatArray(model.vertexCount * 4) // all zeros → bone 0
        }

        model.jointWeights = if (attributes.has("WEIGHTS_0")) {
            readFloatAccessor(accessors, bufferViews, bin, attributes.getInt("WEIGHTS_0"))
        } else {
            // Default: full weight on first joint
            FloatArray(model.vertexCount * 4).also { arr ->
                for (i in 0 until model.vertexCount) arr[i * 4] = 1f
            }
        }

        // Load indices
        if (primitive.has("indices")) {
            model.indices = readIndexAccessor(accessors, bufferViews, bin, primitive.getInt("indices"))
            model.indexCount = model.indices.size
        } else {
            // Non-indexed: generate sequential indices
            model.indices = ShortArray(model.vertexCount) { it.toShort() }
            model.indexCount = model.vertexCount
        }

        // Load skin
        if (json.has("skins")) {
            val skin = json.getJSONArray("skins").getJSONObject(0)
            val joints = skin.getJSONArray("joints")

            // Joint names from nodes
            val nodes = json.getJSONArray("nodes")
            val names = mutableListOf<String>()
            for (i in 0 until joints.length()) {
                val nodeIdx = joints.getInt(i)
                val node = nodes.getJSONObject(nodeIdx)
                names.add(node.optString("name", "joint_$i"))
            }
            model.jointNames = names

            // Inverse bind matrices
            if (skin.has("inverseBindMatrices")) {
                val ibmAccessorIdx = skin.getInt("inverseBindMatrices")
                model.inverseBindMatrices = readFloatAccessor(accessors, bufferViews, bin, ibmAccessorIdx)
            } else {
                // Identity IBMs
                model.inverseBindMatrices = FloatArray(names.size * 16).also { arr ->
                    for (i in names.indices) {
                        android.opengl.Matrix.setIdentityM(arr, i * 16)
                    }
                }
            }

            // Pad to MAX_JOINTS if needed
            if (model.inverseBindMatrices.size < GltfModel.MAX_JOINTS * 16) {
                val padded = FloatArray(GltfModel.MAX_JOINTS * 16)
                System.arraycopy(model.inverseBindMatrices, 0, padded, 0, model.inverseBindMatrices.size)
                for (i in names.size until GltfModel.MAX_JOINTS) {
                    android.opengl.Matrix.setIdentityM(padded, i * 16)
                }
                model.inverseBindMatrices = padded
            }
        }

        Log.i(TAG, "Loaded: ${model.vertexCount} verts, ${model.indexCount} indices, ${model.jointNames.size} joints")
        return model
    }

    /**
     * Read a FLOAT accessor → FloatArray.
     */
    private fun readFloatAccessor(
        accessors: JSONArray, bufferViews: JSONArray, bin: ByteArray, accessorIdx: Int
    ): FloatArray {
        val accessor = accessors.getJSONObject(accessorIdx)
        val count = accessor.getInt("count")
        val componentType = accessor.getInt("componentType")
        val type = accessor.getString("type")
        val components = typeComponents(type)
        val totalFloats = count * components

        val bvIdx = accessor.getInt("bufferView")
        val bv = bufferViews.getJSONObject(bvIdx)
        val byteOffset = bv.optInt("byteOffset", 0) + accessor.optInt("byteOffset", 0)

        val result = FloatArray(totalFloats)
        val bbuf = ByteBuffer.wrap(bin, byteOffset, totalFloats * 4).order(ByteOrder.LITTLE_ENDIAN)

        when (componentType) {
            5126 -> { // FLOAT
                for (i in 0 until totalFloats) result[i] = bbuf.float
            }
            5123 -> { // UNSIGNED_SHORT
                for (i in 0 until totalFloats) result[i] = (bbuf.short.toInt() and 0xFFFF).toFloat()
            }
            5121 -> { // UNSIGNED_BYTE
                for (i in 0 until totalFloats) result[i] = (bbuf.get().toInt() and 0xFF).toFloat()
            }
            else -> throw IllegalArgumentException("Unsupported component type: $componentType")
        }
        return result
    }

    /**
     * Read JOINTS_0 accessor which may be UNSIGNED_BYTE or UNSIGNED_SHORT.
     */
    private fun readJointAccessor(
        accessors: JSONArray, bufferViews: JSONArray, bin: ByteArray, accessorIdx: Int
    ): FloatArray {
        val accessor = accessors.getJSONObject(accessorIdx)
        val count = accessor.getInt("count")
        val componentType = accessor.getInt("componentType")
        val totalValues = count * 4 // VEC4

        val bvIdx = accessor.getInt("bufferView")
        val bv = bufferViews.getJSONObject(bvIdx)
        val byteOffset = bv.optInt("byteOffset", 0) + accessor.optInt("byteOffset", 0)

        val result = FloatArray(totalValues)

        when (componentType) {
            5121 -> { // UNSIGNED_BYTE
                for (i in 0 until totalValues) {
                    result[i] = (bin[byteOffset + i].toInt() and 0xFF).toFloat()
                }
            }
            5123 -> { // UNSIGNED_SHORT
                val bbuf = ByteBuffer.wrap(bin, byteOffset, totalValues * 2).order(ByteOrder.LITTLE_ENDIAN)
                for (i in 0 until totalValues) {
                    result[i] = (bbuf.short.toInt() and 0xFFFF).toFloat()
                }
            }
            else -> {
                // FLOAT fallback
                val bbuf = ByteBuffer.wrap(bin, byteOffset, totalValues * 4).order(ByteOrder.LITTLE_ENDIAN)
                for (i in 0 until totalValues) result[i] = bbuf.float
            }
        }
        return result
    }

    /**
     * Read index accessor → ShortArray (UNSIGNED_SHORT or UNSIGNED_BYTE).
     */
    private fun readIndexAccessor(
        accessors: JSONArray, bufferViews: JSONArray, bin: ByteArray, accessorIdx: Int
    ): ShortArray {
        val accessor = accessors.getJSONObject(accessorIdx)
        val count = accessor.getInt("count")
        val componentType = accessor.getInt("componentType")

        val bvIdx = accessor.getInt("bufferView")
        val bv = bufferViews.getJSONObject(bvIdx)
        val byteOffset = bv.optInt("byteOffset", 0) + accessor.optInt("byteOffset", 0)

        val result = ShortArray(count)

        when (componentType) {
            5123 -> { // UNSIGNED_SHORT
                val bbuf = ByteBuffer.wrap(bin, byteOffset, count * 2).order(ByteOrder.LITTLE_ENDIAN)
                for (i in 0 until count) result[i] = bbuf.short
            }
            5121 -> { // UNSIGNED_BYTE
                for (i in 0 until count) {
                    result[i] = (bin[byteOffset + i].toInt() and 0xFF).toShort()
                }
            }
            5125 -> { // UNSIGNED_INT — downcast to short (mesh must be < 65K verts)
                val bbuf = ByteBuffer.wrap(bin, byteOffset, count * 4).order(ByteOrder.LITTLE_ENDIAN)
                for (i in 0 until count) result[i] = bbuf.int.toShort()
            }
            else -> throw IllegalArgumentException("Unsupported index type: $componentType")
        }
        return result
    }

    private fun typeComponents(type: String): Int = when (type) {
        "SCALAR" -> 1
        "VEC2" -> 2
        "VEC3" -> 3
        "VEC4" -> 4
        "MAT2" -> 4
        "MAT3" -> 9
        "MAT4" -> 16
        else -> throw IllegalArgumentException("Unknown type: $type")
    }
}
