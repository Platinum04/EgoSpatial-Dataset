package dev.egospatial

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LogicTest {
    private fun dirs(heading: Double) = Room.relations(Room.DEFAULT, heading).associate { it.obj.id to it.direction }

    @Test fun facingNorth() {
        assertEquals(mapOf("table" to "left", "couch" to "behind", "door" to "front", "storage" to "right"), dirs(0.0))
    }

    @Test fun facingEast() {
        // Turning right 90 degrees: the door (north) is now on the left, storage (east) in front.
        assertEquals(mapOf("table" to "behind", "couch" to "right", "door" to "left", "storage" to "front"), dirs(90.0))
    }

    @Test fun facingWestAndFullTurn() {
        assertEquals(mapOf("table" to "front", "couch" to "left", "door" to "right", "storage" to "behind"), dirs(270.0))
        assertEquals(dirs(0.0), dirs(360.0))
        assertEquals(dirs(90.0), dirs(-270.0))
    }

    @Test fun nearestFirstAndUserPositionSkipped() {
        val rows = Room.relations(Room.DEFAULT + RoomObject("me", "me", 0.0, 0.0), 0.0)
        assertEquals("table", rows.first().obj.id)
        assertTrue(rows.none { it.obj.id == "me" })
    }

    @Test fun answersAndAbstains() {
        val rows = Room.relations(Room.DEFAULT, 0.0)
        assertEquals("Table is on your left, 2.0 metres away.", Room.answer("Where is the table?", rows))
        assertTrue(Room.answer("where is the piano", rows).contains("won't guess"))
    }

    @Test fun uniqueIds() {
        assertEquals("mug", Room.nextId("mug", Room.DEFAULT))
        assertEquals("table2", Room.nextId("table", Room.DEFAULT))
    }

    @Test fun matchesPythonReferenceConvention() {
        // Same convention as engine/tests/vectors.json: heading 0 = North, +X = East is "right".
        val r = EgoSpatial.objectToAgent(
            SpatialState(Vec3(0.0, 0.0, 0.0), 0.0, listOf(SpatialObject("a", "a", Vec3(1.0, 0.0, 0.0)))), "a")
        assertEquals("right", r.direction)
        assertEquals(90.0, r.signedAngleDeg, 1e-9)
    }
}
