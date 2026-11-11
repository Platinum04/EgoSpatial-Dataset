// EgoSpatial deterministic engine — Kotlin port for Android XR (Jetpack XR / ARCore for Jetpack XR).
// Pure Kotlin, no Android dependency. Axis convention of ARCore / OpenXR poses:
// right-handed, +X right, +Y up, -Z forward. Canonical: x = x, z = -z, heading from the pose forward (-Z).
// Conformance: must reproduce tests/vectors.json (adapter cases use the "webxr" expectations).
package dev.egospatial

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

class SpatialStateException(msg: String) : Exception(msg)
data class Vec3(val x: Double, val y: Double, val z: Double)
data class SpatialObject(val id: String, val label: String, val position: Vec3)
data class SpatialState(val agentPosition: Vec3, val agentHeading: Double, val objects: List<SpatialObject>, val source: String = "live")
data class Relation(val kind: String, val target: String, val reference: String, val direction: String, val signedAngleDeg: Double)

object EgoSpatial {
    private const val DEG = Math.PI / 180.0

    fun normalizeHeading(d: Double): Double {
        if (!d.isFinite()) throw SpatialStateException("heading must be finite")
        var h = d % 360.0; if (h < 0) h += 360.0; return if (h == 360.0) 0.0 else h
    }

    fun worldToEgo(v: Vec3, heading: Double): Vec3 {
        val t = normalizeHeading(heading) * DEG
        return Vec3(v.x * cos(t) - v.z * sin(t), v.y, v.x * sin(t) + v.z * cos(t))
    }

    fun classify(e: Vec3, tol: Double = 1e-9): String {
        if (abs(e.x) < tol && abs(e.z) < tol) throw SpatialStateException("cannot classify a zero-length horizontal vector")
        return if (abs(e.z) >= abs(e.x)) (if (e.z > 0) "front" else "behind") else (if (e.x > 0) "right" else "left")
    }

    private fun validate(s: SpatialState) {
        normalizeHeading(s.agentHeading)
        if (s.objects.isEmpty()) throw SpatialStateException("objects must be non-empty")
        val seen = HashSet<String>()
        for (o in s.objects) {
            if (o.id.isEmpty()) throw SpatialStateException("object id required")
            if (!seen.add(o.id)) throw SpatialStateException("duplicate object id: ${o.id}")
            if (!o.position.x.isFinite() || !o.position.z.isFinite()) throw SpatialStateException("non-finite position: ${o.id}")
        }
    }

    private fun get(s: SpatialState, id: String) = s.objects.firstOrNull { it.id == id } ?: throw SpatialStateException("unknown object: $id")
    private fun sub(a: Vec3, b: Vec3) = Vec3(b.x - a.x, b.y - a.y, b.z - a.z)

    private fun make(kind: String, t: String, r: String, w: Vec3, heading: Double): Relation {
        val e = worldToEgo(w, heading)
        var a = atan2(e.x, e.z) / DEG; if (a == -180.0) a = 180.0
        return Relation(kind, t, r, classify(e), a)
    }

    fun objectToAgent(s: SpatialState, target: String): Relation {
        validate(s); return make("object_to_agent", target, "agent", sub(s.agentPosition, get(s, target).position), s.agentHeading)
    }

    fun referenceFrame(s: SpatialState, reference: String, target: String): Relation {
        validate(s); if (reference == target) throw SpatialStateException("reference and target must differ")
        val rv = sub(s.agentPosition, get(s, reference).position)
        if (rv.x == 0.0 && rv.z == 0.0) throw SpatialStateException("bearing of zero vector is undefined")
        return make("reference_frame", target, reference, sub(s.agentPosition, get(s, target).position), normalizeHeading(atan2(rv.x, rv.z) / DEG))
    }

    fun allRelations(s: SpatialState): Map<String, Relation> = s.objects.associate { it.id to objectToAgent(s, it.id) }

    /** Build canonical state from an ARCore/Jetpack XR pose (position + quaternion x,y,z,w) and object positions
     *  (e.g. Anchor / Plane center poses) expressed in the same session space. */
    fun fromArPose(px: Double, py: Double, pz: Double, qx: Double, qy: Double, qz: Double, qw: Double,
                   objects: List<Triple<String, String, Vec3>>, source: String = "live"): SpatialState {
        val n = sqrt(qx * qx + qy * qy + qz * qz + qw * qw); if (!(n > 0)) throw SpatialStateException("invalid quaternion")
        val x = qx / n; val y = qy / n; val z = qz / n; val w = qw / n
        // rotate v = (0,0,-1): t = 2*cross(q, v) = (-2y, 2x, 0)
        val tx = -2 * y; val ty = 2 * x; val tz = 0.0
        val fx = 0 + w * tx + (y * tz - z * ty)
        val fz = -1 + w * tz + (x * ty - y * tx)
        val cx = fx; val cz = -fz
        if (abs(cx) < 1e-12 && abs(cz) < 1e-12) throw SpatialStateException("heading undefined (looking up/down)")
        val heading = normalizeHeading(atan2(cx, cz) / DEG)
        return SpatialState(Vec3(px, py, -pz), heading,
            objects.map { (id, label, p) -> SpatialObject(id, label, Vec3(p.x, p.y, -p.z)) }, source)
    }
}
