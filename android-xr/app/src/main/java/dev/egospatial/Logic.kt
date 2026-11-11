// Pure-Kotlin app logic for EgoSpatial XR (no Android dependency, unit-tested on the JVM).
// Canonical frame: +X East, +Z North, heading in degrees clockwise from North; the user stands at the origin.
package dev.egospatial

import kotlin.math.hypot
import kotlin.math.roundToInt

data class RoomObject(val id: String, val label: String, val x: Double, val z: Double)

data class RelationRow(val obj: RoomObject, val direction: String, val angleDeg: Double, val distance: Double)

object Room {
    val DEFAULT = listOf(
        RoomObject("table", "table", -2.0, 0.3),
        RoomObject("couch", "couch", 0.4, -3.0),
        RoomObject("door", "door", 0.0, 4.0),
        RoomObject("storage", "storage", 3.0, -0.5),
    )

    /** Every object's direction relative to the user, nearest first. Objects exactly at the user are skipped. */
    fun relations(objects: List<RoomObject>, heading: Double): List<RelationRow> {
        if (objects.isEmpty()) return emptyList()
        val state = SpatialState(
            Vec3(0.0, 0.0, 0.0), heading,
            objects.map { SpatialObject(it.id, it.label, Vec3(it.x, 0.0, it.z)) },
        )
        return objects.mapNotNull { o ->
            try {
                val r = EgoSpatial.objectToAgent(state, o.id)
                RelationRow(o, r.direction, r.signedAngleDeg, hypot(o.x, o.z))
            } catch (e: SpatialStateException) {
                null
            }
        }.sortedBy { it.distance }
    }

    fun phrase(direction: String): String = when (direction) {
        "front" -> "in front of you"
        "behind" -> "behind you"
        "left" -> "on your left"
        else -> "on your right"
    }

    private fun metres(d: Double): String {
        val r = (d * 10).roundToInt() / 10.0
        return if (r == 1.0) "1 metre" else "$r metres"
    }

    /** Answers "where is the X?" from geometry only. Unknown objects get an explicit refusal instead of a guess. */
    fun answer(question: String, rows: List<RelationRow>): String {
        val q = question.lowercase()
        val hit = rows.sortedByDescending { it.obj.label.length }.firstOrNull { q.contains(it.obj.label.lowercase()) }
            ?: return "I can't find that object in this room, so I won't guess."
        val name = hit.obj.label.replaceFirstChar { it.uppercase() }
        return "$name is ${phrase(hit.direction)}, ${metres(hit.distance)} away."
    }

    fun summary(rows: List<RelationRow>, max: Int = 4): String {
        if (rows.isEmpty()) return "I don't see any objects yet."
        return rows.take(max).joinToString(" ") {
            "${it.obj.label.replaceFirstChar { c -> c.uppercase() }} is ${phrase(it.direction)}, ${metres(it.distance)}."
        }
    }

    fun nextId(label: String, objects: List<RoomObject>): String {
        if (objects.none { it.id == label }) return label
        var i = 2
        while (objects.any { it.id == "$label$i" }) i++
        return "$label$i"
    }
}
