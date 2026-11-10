import json
import math
import random
import threading
import unittest
import urllib.request

import egospatial as es
from egospatial import adapters
from egospatial.neural import parse_json_reply
from egospatial.query import Query

CARD = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}
HEAD = {"north": 0, "east": 90, "south": 180, "west": 270}
# expected egocentric answer for (heading, object world direction)
REL = {0: "front", 90: "right", 180: "behind", 270: "left"}


def scene(heading, objs, pos=(0, 0, 0), source="simulated"):
    return es.SpatialState.from_dict({
        "agent": {"position": {"x": pos[0], "y": pos[1], "z": pos[2]}, "heading": heading},
        "objects": [{"id": i, "label": i, "position": {"x": x, "y": y, "z": z}} for i, (x, y, z) in objs.items()],
        "source": source})


class Frames(unittest.TestCase):
    def test_normalize(self):
        for a, b in [(0, 0), (360, 0), (-90, 270), (450, 90), (720.5, 0.5)]:
            self.assertAlmostEqual(es.normalize_heading(a), b)
        with self.assertRaises(ValueError):
            es.normalize_heading(float("nan"))

    def test_inverse(self):
        rnd = random.Random(1)
        for _ in range(500):
            v = {"x": rnd.uniform(-9, 9), "y": rnd.uniform(-2, 2), "z": rnd.uniform(-9, 9)}
            h = rnd.uniform(-720, 720)
            w = es.egocentric_to_world(es.world_to_egocentric(v, h), h)
            for k in "xyz":
                self.assertAlmostEqual(v[k], w[k], places=9)

    def test_bearing(self):
        for d, (x, z) in CARD.items():
            self.assertAlmostEqual(es.bearing_degrees({"x": x, "y": 0, "z": z}), HEAD[d])


class Relations(unittest.TestCase):
    def test_all_16_cardinal_egocentric(self):
        for hn, h in HEAD.items():
            for dn, (x, z) in CARD.items():
                st = scene(h, {"obj": (x, 0, z)})
                self.assertEqual(es.object_to_agent(st, "obj")["direction"], REL[(HEAD[dn] - h) % 360], (hn, dn))

    def test_reference_frame_v4_semantics(self):
        # V4: face the reference; target classified in that frame (agent heading irrelevant)
        for rn, (rx, rz) in CARD.items():
            for tn, (tx, tz) in CARD.items():
                if rn == tn:
                    continue
                for h in (0, 90, 180, 270):
                    st = scene(h, {"ref": (rx, 0, rz), "tgt": (tx, 0, tz)})
                    self.assertEqual(es.reference_frame(st, "ref", "tgt")["direction"],
                                     REL[(HEAD[tn] - HEAD[rn]) % 360])

    def test_object_to_object_08b3_semantics(self):
        st = scene(0, {"table": (0, 0, 2), "chair": (1, 0, 2)})   # chair east of table, agent faces north
        self.assertEqual(es.object_to_object(st, "table", "chair")["direction"], "right")
        st = scene(180, {"table": (0, 0, 2), "chair": (1, 0, 2)})  # facing south: east is on the left
        self.assertEqual(es.object_to_object(st, "table", "chair")["direction"], "left")

    def test_diagonal_tie_goes_front_behind(self):
        st = scene(0, {"a": (1, 0, 1), "b": (-1, 0, -1)})
        self.assertEqual(es.object_to_agent(st, "a")["direction"], "front")
        self.assertEqual(es.object_to_agent(st, "b")["direction"], "behind")

    def test_zero_vector_and_vertical(self):
        st = scene(0, {"above": (0, 3, 0), "x": (1, 0, 0)})
        with self.assertRaises(es.SpatialStateError):
            es.object_to_agent(st, "above")

    def test_translation_and_rotation_invariance(self):
        rnd = random.Random(7)
        for _ in range(300):
            h = rnd.uniform(0, 360); tx, tz = rnd.uniform(-50, 50), rnd.uniform(-50, 50)
            ox, oz = rnd.uniform(-5, 5), rnd.uniform(-5, 5)
            if math.hypot(ox, oz) < 1e-3:
                continue
            a = es.object_to_agent(scene(h, {"o": (ox, 0, oz)}), "o")
            b = es.object_to_agent(scene(h, {"o": (ox + tx, 0, oz + tz)}, pos=(tx, 0, tz)), "o")
            self.assertEqual(a["direction"], b["direction"])
            # rotating the world and the heading together leaves the answer unchanged
            r = rnd.uniform(0, 360); w = es.egocentric_to_world({"x": ox, "y": 0, "z": oz}, r)  # rotate world clockwise by r
            c = es.object_to_agent(scene(h + r, {"o": (w["x"], 0, w["z"])}), "o")
            if abs(abs(a["signed_angle_deg"]) - 45) > 1e-6 and abs(abs(a["signed_angle_deg"]) - 135) > 1e-6:
                self.assertEqual(a["direction"], c["direction"])

    def test_distance(self):
        st = scene(0, {"a": (3, 5, 4), "b": (0, 0, 0.5)}, pos=(0, 0, 0))
        self.assertAlmostEqual(es.distance(st, "a")["distance_m"], 5.0)
        self.assertAlmostEqual(es.distance(st, "a", horizontal=False)["distance_m"], math.sqrt(50))


class State(unittest.TestCase):
    def bad(self, d):
        with self.assertRaises(es.SpatialStateError):
            es.SpatialState.from_dict(d)

    def test_validation(self):
        ok = {"agent": {"heading": 0}, "objects": [{"id": "a", "position": {"x": 1, "z": 0}}]}
        es.SpatialState.from_dict(ok)
        self.bad({"objects": ok["objects"]})
        self.bad({"agent": {"heading": "north"}, "objects": ok["objects"]})
        self.bad({"agent": {"heading": float("inf")}, "objects": ok["objects"]})
        self.bad({"agent": {"heading": 0}, "objects": []})
        self.bad({"agent": {"heading": 0}, "objects": ok["objects"] * 2})
        self.bad({"agent": {"heading": 0}, "objects": [{"id": "a", "position": {"x": True, "z": 0}}]})
        self.bad({"agent": {"heading": 0}, "objects": [{"id": "", "position": {"x": 1, "z": 0}}]})
        self.bad({"agent": {"heading": 0}, "objects": [{"id": "a", "position": {"x": 1}}]})
        self.bad({"agent": {"heading": 0}, "objects": ok["objects"], "source": "dream"})
        with self.assertRaises(es.SpatialStateError):
            es.SpatialState.from_json("{nope")

    def test_deterministic_serialization(self):
        objs = [{"id": i, "position": {"x": n, "y": 0, "z": 1}} for n, i in enumerate("dcba")]
        a = es.SpatialState.from_dict({"agent": {"heading": 450}, "objects": objs})
        b = es.SpatialState.from_dict({"agent": {"heading": 90}, "objects": list(reversed(objs))})
        self.assertEqual(a.to_json(), b.to_json())
        self.assertEqual(es.SpatialState.from_json(a.to_json()).to_json(), a.to_json())


class Parsing(unittest.TestCase):
    names = ["lamp", "desk", "bookshelf", "shelf"]

    def test_v4_templates(self):
        cases = {
            "Where is the lamp relative to me?": Query("object_to_agent", "lamp"),
            "Which direction is the lamp from me?": Query("object_to_agent", "lamp"),
            "Where is the lamp with respect to me?": Query("object_to_agent", "lamp"),
            "Determine the direction of the lamp relative to me.": Query("object_to_agent", "lamp"),
            "What direction is the lamp relative to the desk?": Query("reference_frame", "lamp", "desk"),
            "Where is the shelf relative to the bookshelf?": Query("reference_frame", "shelf", "bookshelf"),
            "How far is the desk?": Query("distance", "desk", "agent"),
            "How far is the desk from the lamp?": Query("distance", "desk", "lamp"),
        }
        for q, exp in cases.items():
            self.assertEqual(es.template_parse(q, self.names), exp, q)
        self.assertEqual(es.template_parse("Where is the lamp relative to the desk?", self.names, "object_to_object"),
                         Query("object_to_object", "lamp", "desk"))

    def test_unparseable(self):
        for q in ["Where is the piano relative to me?", "Is the lamp on my left?", "hello"]:
            self.assertIsNone(es.template_parse(q, self.names), q)

    def test_neural_reply_validation(self):
        self.assertEqual(parse_json_reply('{"target": "lamp", "reference": "me"}', self.names), Query("object_to_agent", "lamp"))
        self.assertEqual(parse_json_reply('x {"target":"Lamp","reference":"desk"} y', self.names), Query("reference_frame", "lamp", "desk"))
        for raw in ['{"target": "piano", "reference": "me"}', '{"target": "lamp", "reference": "lamp"}', "no json", "{bad json}"]:
            self.assertIsNone(parse_json_reply(raw, self.names), raw)


class Orchestrator(unittest.TestCase):
    st = {"agent": {"position": {"x": 0, "y": 0, "z": 0}, "heading": 90},
          "objects": [{"id": "chair_01", "label": "chair", "position": {"x": 1.2, "y": 0, "z": -0.8}},
                      {"id": "table_01", "label": "table", "position": {"x": -0.5, "y": 0, "z": -1.4}}]}

    def test_ok_unresolved_error(self):
        e = es.SpatialEngine()
        r = e.ask(self.st, "Where is the chair_01 relative to me?")
        self.assertEqual((r["status"], r["answer"], r["path"]), ("ok", "front", "deterministic(template)"))
        r = e.ask(self.st, "Where is the table_01 relative to me?")
        self.assertEqual(r["answer"], "right")
        r = e.ask(self.st, "Is the chair to my left?")
        self.assertEqual(r["status"], "unresolved")
        self.assertNotIn("answer", r)
        r = e.ask("{broken", "Where is the chair_01 relative to me?")
        self.assertEqual(r["status"], "error")

    def test_neural_parser_is_validated(self):
        good = es.SpatialEngine(semantic_parser=lambda q, n: Query("object_to_agent", "chair_01"))
        self.assertEqual(good.ask(self.st, "the seat thing?")["path"], "deterministic(neural-parse)")
        bad = es.SpatialEngine(semantic_parser=lambda q, n: Query("object_to_agent", "ghost"))
        self.assertEqual(bad.ask(self.st, "the seat thing?")["status"], "unresolved")


class Adapters(unittest.TestCase):
    def test_v4(self):
        st = adapters.from_v4_situation('{"agent":{"heading":"east"},"objects":[{"id":"shelf","world_direction":"south"},{"id":"lamp","world_direction":"north"}]}')
        self.assertEqual(es.object_to_agent(st, "shelf")["direction"], "right")
        with self.assertRaises(es.SpatialStateError):
            adapters.from_v4_situation('{"agent":{"heading":"up"},"objects":[]}')

    def yaw_q(self, deg):  # rotation about +Y
        t = math.radians(deg) / 2
        return (0.0, math.sin(t), 0.0, math.cos(t))

    def test_unity(self):
        objs = [{"id": "r", "position": [1, 0, 0]}, {"id": "f", "position": [0, 0, 2]}]
        st = adapters.from_unity([0, 1.6, 0], self.yaw_q(0), objs)
        self.assertAlmostEqual(st.agent_heading, 0)
        self.assertEqual(es.object_to_agent(st, "r")["direction"], "right")
        self.assertEqual(es.object_to_agent(st, "f")["direction"], "front")
        st = adapters.from_unity([0, 1.6, 0], self.yaw_q(90), objs)  # Unity +yaw = turn right (clockwise)
        self.assertAlmostEqual(st.agent_heading, 90)
        self.assertEqual(es.object_to_agent(st, "r")["direction"], "front")
        self.assertEqual(es.object_to_agent(st, "f")["direction"], "left")

    def test_webxr_android(self):
        objs = [{"id": "r", "position": [1, 0, 0]}, {"id": "f", "position": [0, 0, -2]}]
        st = adapters.from_webxr([0, 1.6, 0], (0, 0, 0, 1), objs)
        self.assertAlmostEqual(st.agent_heading, 0)
        self.assertEqual(es.object_to_agent(st, "r")["direction"], "right")
        self.assertEqual(es.object_to_agent(st, "f")["direction"], "front")
        # right-handed +Y rotation of +90 deg is a LEFT turn (counter-clockwise from above)
        st = adapters.from_android_xr([0, 1.6, 0], self.yaw_q(90), objs)
        self.assertAlmostEqual(st.agent_heading, 270)
        self.assertEqual(es.object_to_agent(st, "f")["direction"], "right")
        self.assertEqual(es.object_to_agent(st, "r")["direction"], "behind")

    def test_north_offset(self):
        objs = [{"id": "f", "position": [0, 0, -2]}]
        st = adapters.from_webxr([0, 0, 0], (0, 0, 0, 1), objs, north_offset_deg=90)
        self.assertAlmostEqual(st.agent_heading, 90)
        self.assertAlmostEqual(st.object("f").position["x"], 2)
        self.assertEqual(es.object_to_agent(st, "f")["direction"], "front")

    def test_cross_platform_consistency(self):
        rnd = random.Random(3)
        for _ in range(200):
            yaw = rnd.uniform(0, 360); x, z = rnd.uniform(-5, 5), rnd.uniform(-5, 5)
            if math.hypot(x, z) < 1e-2:
                continue
            u = adapters.from_unity([0, 0, 0], self.yaw_q(yaw), [{"id": "o", "position": [x, 0, z]}])
            # same physical scene expressed in a right-handed -Z-forward frame: z -> -z, yaw -> -yaw
            w = adapters.from_webxr([0, 0, 0], self.yaw_q(-yaw), [{"id": "o", "position": [x, 0, -z]}])
            self.assertAlmostEqual(u.agent_heading, w.agent_heading, places=6)
            self.assertEqual(es.object_to_agent(u, "o")["direction"], es.object_to_agent(w, "o")["direction"])


class Server(unittest.TestCase):
    def test_http_api(self):
        from http.server import ThreadingHTTPServer
        from egospatial.server import _Handler
        srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"

        def post(path, body):
            req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
            try:
                return json.loads(urllib.request.urlopen(req).read())
            except urllib.error.HTTPError as e:
                return json.loads(e.read())
        st = Orchestrator.st
        self.assertEqual(json.loads(urllib.request.urlopen(base + "/health").read())["status"], "ok")
        self.assertEqual(post("/ask", {"state": st, "question": "Where is the chair_01 relative to me?"})["answer"], "front")
        self.assertEqual(post("/evaluate", {"state": st, "query": {"op": "object_to_agent", "target": "table_01"}})["result"]["direction"], "right")
        self.assertEqual(set(post("/relations", {"state": st})["relations"]), {"chair_01", "table_01"})
        self.assertEqual(post("/evaluate", {"state": st, "query": {"op": "object_to_agent", "target": "x"}})["status"], "error")
        srv.shutdown()


if __name__ == "__main__":
    unittest.main()
