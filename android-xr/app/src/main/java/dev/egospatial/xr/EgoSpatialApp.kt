package dev.egospatial.xr

import android.speech.tts.TextToSpeech
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableDoubleStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.xr.compose.platform.LocalSpatialCapabilities
import androidx.xr.compose.spatial.Subspace
import androidx.xr.compose.subspace.SpatialPanel
import androidx.xr.compose.subspace.SpatialRow
import androidx.xr.compose.subspace.layout.SubspaceModifier
import androidx.xr.compose.subspace.layout.movable
import androidx.xr.compose.subspace.layout.resizable
import androidx.xr.compose.subspace.layout.size
import dev.egospatial.RelationRow
import dev.egospatial.Room
import dev.egospatial.RoomObject
import java.util.Locale
import kotlin.math.min
import kotlin.math.roundToInt

private val FRONT = Color(0xFF3DDC84)
private val BEHIND = Color(0xFFFF6B6B)
private val LEFT = Color(0xFF5AA9FF)
private val RIGHT = Color(0xFFFFB84D)
private val PANEL = Color(0xFF181B22)
private val GRID = Color(0xFF2A2F3A)

private fun colorFor(direction: String) = when (direction) {
    "front" -> FRONT
    "behind" -> BEHIND
    "left" -> LEFT
    else -> RIGHT
}

/**
 * EgoSpatial XR: where is everything around me?
 * On Android XR (Full Space) the room map and the relations panel are two movable, resizable spatial panels.
 * On a phone or tablet the same UI is shown side by side. Every direction comes from the deterministic engine.
 */
@Composable
fun EgoSpatialApp() {
    var objects by remember { mutableStateOf(Room.DEFAULT) }
    var heading by remember { mutableDoubleStateOf(0.0) }
    var question by remember { mutableStateOf("Where is the table?") }
    var said by remember { mutableStateOf("") }
    val rows = Room.relations(objects, heading)

    val context = LocalContext.current
    val tts = remember { arrayOfNulls<TextToSpeech>(1) }
    DisposableEffect(Unit) {
        val engine = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) tts[0]?.language = Locale.US
        }
        tts[0] = engine
        onDispose { engine.shutdown() }
    }
    val speak: (String) -> Unit = { text ->
        said = text
        tts[0]?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "egospatial")
    }
    val onTap: (Double, Double) -> Unit = { x, z ->
        objects = objects + RoomObject(Room.nextId("mug", objects), "mug", x, z)
    }

    val map: @Composable () -> Unit = {
        RoomMap(objects, heading, rows, onTap, Modifier.fillMaxSize())
    }
    val side: @Composable () -> Unit = {
        SidePanel(
            rows = rows,
            heading = heading,
            onHeading = { heading = it },
            question = question,
            onQuestion = { question = it },
            said = said,
            onAsk = { speak(Room.answer(question, rows)) },
            onSpeakAll = { speak(Room.summary(rows)) },
            onReset = { objects = Room.DEFAULT; heading = 0.0; said = "" },
        )
    }

    if (LocalSpatialCapabilities.current.isSpatialUiEnabled) {
        Subspace {
            SpatialRow {
                SpatialPanel(SubspaceModifier.size(720.dp).movable().resizable()) {
                    Surface(color = PANEL) { map() }
                }
                SpatialPanel(SubspaceModifier.size(720.dp).movable().resizable()) {
                    Surface { side() }
                }
            }
        }
    } else {
        Surface(Modifier.fillMaxSize()) {
            Row(Modifier.fillMaxSize().padding(16.dp)) {
                Box(Modifier.weight(1f).fillMaxHeight()) { map() }
                Spacer(Modifier.width(16.dp))
                Box(Modifier.width(380.dp).fillMaxHeight()) { side() }
            }
        }
    }
}

/** Top-down room view: North is up, the user is the arrow in the centre, 1 grid square = 1 metre. Tap to add a mug. */
@Composable
private fun RoomMap(
    objects: List<RoomObject>,
    heading: Double,
    rows: List<RelationRow>,
    onTap: (Double, Double) -> Unit,
    modifier: Modifier = Modifier,
) {
    val measurer = rememberTextMeasurer()
    val tap by rememberUpdatedState(onTap)
    val directionOf = rows.associate { it.obj.id to it.direction }
    Canvas(
        modifier
            .background(PANEL)
            .pointerInput(Unit) {
                detectTapGestures { p ->
                    val ppm = min(size.width, size.height) / 10f
                    val x = (p.x - size.width / 2f) / ppm
                    val z = (size.height / 2f - p.y) / ppm
                    tap((x * 10).roundToInt() / 10.0, (z * 10).roundToInt() / 10.0)
                }
            }
    ) {
        val ppm = min(size.width, size.height) / 10f
        val c = Offset(size.width / 2f, size.height / 2f)
        for (i in -5..5) {
            drawLine(GRID, Offset(c.x + i * ppm, 0f), Offset(c.x + i * ppm, size.height), 1f)
            drawLine(GRID, Offset(0f, c.y + i * ppm), Offset(size.width, c.y + i * ppm), 1f)
        }
        drawText(measurer, "N", Offset(c.x - 6f, 8f), TextStyle(color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold))
        rotate(heading.toFloat(), c) {
            val s = ppm * 0.45f
            val arrow = Path().apply {
                moveTo(c.x, c.y - s)
                lineTo(c.x + s * 0.6f, c.y + s * 0.6f)
                lineTo(c.x, c.y + s * 0.25f)
                lineTo(c.x - s * 0.6f, c.y + s * 0.6f)
                close()
            }
            drawPath(arrow, Color.White)
        }
        for (o in objects) {
            val p = Offset(c.x + o.x.toFloat() * ppm, c.y - o.z.toFloat() * ppm)
            val dir = directionOf[o.id] ?: "front"
            drawCircle(colorFor(dir), radius = 14f, center = p)
            drawText(
                measurer,
                "${o.label.uppercase()} · ${dir.uppercase()}",
                Offset(p.x + 20f, p.y - 14f),
                TextStyle(color = Color.White, fontSize = 14.sp),
            )
        }
    }
}

@Composable
private fun SidePanel(
    rows: List<RelationRow>,
    heading: Double,
    onHeading: (Double) -> Unit,
    question: String,
    onQuestion: (String) -> Unit,
    said: String,
    onAsk: () -> Unit,
    onSpeakAll: () -> Unit,
    onReset: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().padding(24.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("EgoSpatial XR", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            "Where is everything around me? Directions come from a deterministic spatial engine, not from a language model's guess.",
            style = MaterialTheme.typography.bodyMedium,
        )
        Text("Facing ${heading.roundToInt()}° (0° = North)", style = MaterialTheme.typography.labelLarge)
        Slider(value = heading.toFloat(), onValueChange = { onHeading(it.toDouble()) }, valueRange = 0f..359f)
        for (r in rows) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.width(12.dp).height(12.dp).background(colorFor(r.direction)))
                Spacer(Modifier.width(10.dp))
                Text(r.obj.label.replaceFirstChar { it.uppercase() }, Modifier.weight(1f))
                Text(r.direction.uppercase(), Modifier.width(80.dp), color = colorFor(r.direction), fontWeight = FontWeight.Bold)
                Text("${(r.distance * 10).roundToInt() / 10.0} m", Modifier.width(64.dp))
            }
        }
        OutlinedTextField(question, onQuestion, Modifier.fillMaxWidth(), label = { Text("Ask") }, singleLine = true)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = onAsk) { Text("Answer") }
            Button(onClick = onSpeakAll) { Text("Speak all") }
            OutlinedButton(onClick = onReset) { Text("Reset") }
        }
        if (said.isNotEmpty()) Text(said, style = MaterialTheme.typography.bodyLarge)
        Text("Tap the map to place a mug.", style = MaterialTheme.typography.bodySmall)
    }
}
