// Editor tools for the EgoSpatial Unity demo.
//   * Conformance: checks the C# engine against engine/tests/vectors.json (same checks as the JS port).
//   * Demo scene:  builds Assets/Scenes/EgoSpatialDemo.unity (camera, four objects, live labels).
// Batch mode:
//   Unity -batchmode -quit -projectPath . -executeMethod EgoSpatial.EditorTools.RunConformanceBatch
//   Unity -batchmode -quit -projectPath . -executeMethod EgoSpatial.EditorTools.BuildDemoScene
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace EgoSpatial
{
    public static class EditorTools
    {
        const string ScenePath = "Assets/Scenes/EgoSpatialDemo.unity";

        // ---------- conformance ----------
        [MenuItem("EgoSpatial/Run conformance")]
        public static void RunConformanceMenu() { var (p, f) = RunConformance(); Debug.Log($"Unity conformance: {p} passed, {f} failed"); }

        public static void RunConformanceBatch()
        {
            var (p, f) = RunConformance();
            Debug.Log($"Unity conformance: {p} passed, {f} failed");
            EditorApplication.Exit(f == 0 && p > 0 ? 0 : 1);
        }

        static string VectorsPath()
        {
            // engine/examples/unity-quest -> engine/tests/vectors.json
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "tests", "vectors.json"));
        }

        static Vec3 V(object o)
        {
            if (o is List<object> a) return new Vec3(D(a[0]), D(a[1]), D(a[2]));
            var d = (Dictionary<string, object>)o;
            return new Vec3(D(d["x"]), d.ContainsKey("y") ? D(d["y"]) : 0, D(d["z"]));
        }
        static double D(object o) => Convert.ToDouble(o, CultureInfo.InvariantCulture);

        static SpatialState State(Dictionary<string, object> st)
        {
            var ag = (Dictionary<string, object>)st["agent"];
            var s = new SpatialState { AgentPosition = V(ag["position"]), AgentHeading = D(ag["heading"]) };
            foreach (Dictionary<string, object> o in (List<object>)st["objects"])
                s.Objects.Add(new SpatialObject { Id = (string)o["id"], Label = o.ContainsKey("label") ? (string)o["label"] : (string)o["id"], Position = V(o["position"]) });
            return s;
        }

        public static (int, int) RunConformance()
        {
            var root = (Dictionary<string, object>)MiniJson.Parse(File.ReadAllText(VectorsPath()));
            int pass = 0, fail = 0;
            void Check(bool ok, string msg) { if (ok) pass++; else { fail++; if (fail < 10) Debug.LogError("FAIL " + msg); } }

            foreach (Dictionary<string, object> c in (List<object>)root["relations"])
            {
                var s = State((Dictionary<string, object>)c["state"]);
                var e = (Dictionary<string, object>)c["expected"];
                foreach (var kv in (Dictionary<string, object>)e["object_to_agent"])
                    Check(Engine.ObjectToAgent(s, kv.Key).Direction == (string)kv.Value, "o2a " + kv.Key);
                if (e.TryGetValue("reference_frame", out var rf) && rf != null) Check(Engine.ReferenceFrame(s, "o0", "o1").Direction == (string)rf, "rf");
                if (e.TryGetValue("object_to_object", out var oo) && oo != null) Check(Engine.ObjectToObject(s, "o0", "o1").Direction == (string)oo, "o2o");
                Check(Math.Abs(Engine.ObjectToAgent(s, "o0").SignedAngleDeg - D(e["signed_angle_o0"])) < 1e-5, "angle");
            }
            foreach (Dictionary<string, object> a in (List<object>)root["adapters"])
            {
                var q = (List<object>)a["quat"];
                var u = (Dictionary<string, object>)a["unity"];
                var s = new SpatialState { AgentPosition = new Vec3(0, 1.6, 0), AgentHeading = Engine.UnityHeading(D(q[0]), D(q[1]), D(q[2]), D(q[3])) };
                s.Objects.Add(new SpatialObject { Id = "o", Label = "o", Position = V(a["object"]) });
                Check(Math.Abs(s.AgentHeading - D(u["heading"])) < 1e-3 && Engine.ObjectToAgent(s, "o").Direction == (string)u["direction"], "unity adapter");
            }
            // validation must reject bad states
            var bad = new List<SpatialState>
            {
                new SpatialState { AgentHeading = double.NaN, Objects = { new SpatialObject { Id = "a", Position = new Vec3(1, 0, 0) } } },
                new SpatialState { AgentHeading = 0 },
                new SpatialState { AgentHeading = 0, Objects = { new SpatialObject { Id = "a", Position = new Vec3(1, 0, 0) }, new SpatialObject { Id = "a", Position = new Vec3(2, 0, 0) } } },
            };
            foreach (var b in bad)
            {
                bool threw = false; try { Engine.ObjectToAgent(b, "a"); } catch (SpatialStateException) { threw = true; }
                Check(threw, "validation");
            }
            return (pass, fail);
        }

        // ---------- demo scene ----------
        [MenuItem("EgoSpatial/Build demo scene")]
        public static void BuildDemoScene()
        {
            Directory.CreateDirectory("Assets/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

            var cam = Camera.main;
            cam.transform.position = new Vector3(0, 1.6f, 0);
            cam.transform.rotation = Quaternion.identity;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.07f, 0.08f, 0.11f);

            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "Floor"; floor.transform.localScale = new Vector3(1.2f, 1, 1.2f);
            floor.GetComponent<Renderer>().sharedMaterial = Mat("Floor", new Color(0.18f, 0.2f, 0.24f));

            // Same layout as the Android app's demo room (+Z = North, agent at origin facing North).
            var items = new (string id, Vector3 pos, Vector3 size, Color col)[]
            {
                ("table",   new Vector3(-2f, 0.4f, 0f),  new Vector3(1.2f, 0.8f, 0.8f), new Color(0.35f, 0.65f, 1f)),
                ("couch",   new Vector3(0f, 0.45f, -3f), new Vector3(2f, 0.9f, 0.9f),   new Color(1f, 0.4f, 0.4f)),
                ("storage", new Vector3(3f, 0.9f, -0.5f), new Vector3(0.8f, 1.8f, 0.6f), new Color(1f, 0.72f, 0.3f)),
                ("door",    new Vector3(0f, 1f, 4f),     new Vector3(1f, 2f, 0.1f),     new Color(0.3f, 0.85f, 0.5f)),
            };

            var bridgeGo = new GameObject("EgoSpatial");
            var bridge = bridgeGo.AddComponent<EgoSpatialSceneBridge>();
            bridge.xrCamera = cam.transform;
            bridge.source = "simulated";

            var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            foreach (var it in items)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                go.name = it.id; go.transform.position = it.pos; go.transform.localScale = it.size;
                go.GetComponent<Renderer>().sharedMaterial = Mat(it.id, it.col);
                bridge.objects.Add(new EgoSpatialSceneBridge.Tracked { id = it.id, label = it.id, transform = go.transform });

                var lab = new GameObject(it.id + "_label");
                lab.transform.position = it.pos + Vector3.up * (it.size.y / 2 + 0.35f);
                var tm = Label(lab, font, 0.06f);
                var ol = lab.AddComponent<EgoSpatialObjectLabel>();
                ol.bridge = bridge; ol.objectId = it.id; ol.text = tm; ol.faceCamera = cam.transform;
            }

            // HUD in front of the camera.
            var hud = new GameObject("HUD");
            hud.transform.SetParent(cam.transform, false);
            hud.transform.localPosition = new Vector3(-0.95f, -0.25f, 1.5f);
            bridge.debugLabel = Label(hud, font, 0.011f);
            bridge.debugLabel.anchor = TextAnchor.UpperLeft;
            bridge.debugLabel.alignment = TextAlignment.Left;

            cam.gameObject.AddComponent<EgoSpatialDemoTurner>();

            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            Debug.Log("EgoSpatial demo scene saved: " + ScenePath);
        }

        static TextMesh Label(GameObject go, Font font, float size)
        {
            var tm = go.AddComponent<TextMesh>();
            tm.font = font; tm.fontSize = 64; tm.characterSize = size;
            tm.anchor = TextAnchor.MiddleCenter; tm.alignment = TextAlignment.Center; tm.color = Color.white;
            go.GetComponent<MeshRenderer>().sharedMaterial = font.material;
            return tm;
        }

        static Material Mat(string name, Color c)
        {
            Directory.CreateDirectory("Assets/EgoSpatial/Materials");
            var path = $"Assets/EgoSpatial/Materials/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                var sh = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
                m = new Material(sh); AssetDatabase.CreateAsset(m, path);
            }
            m.color = c; EditorUtility.SetDirty(m);
            return m;
        }

        // ---------- batch: render screenshots at several headings ----------
        public static void RenderHeadingsBatch()
        {
            EditorSceneManager.OpenScene(ScenePath);
            var cam = Camera.main;
            var bridge = UnityEngine.Object.FindFirstObjectByType<EgoSpatialSceneBridge>();
            var labels = UnityEngine.Object.FindObjectsByType<EgoSpatialObjectLabel>(FindObjectsSortMode.None);
            var outDir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Screenshots"));
            Directory.CreateDirectory(outDir);
            var log = new StringBuilder();
            foreach (var h in new[] { 0, 90, 180, 270 })
            {
                cam.transform.rotation = Quaternion.Euler(0, h, 0);
                bridge.Tick();
                foreach (var l in labels) l.Tick();
                var rt = new RenderTexture(1280, 720, 24); cam.targetTexture = rt; cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(1280, 720, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 1280, 720), 0, 0); tex.Apply();
                File.WriteAllBytes(Path.Combine(outDir, $"heading_{h:000}.png"), tex.EncodeToPNG());
                cam.targetTexture = null; RenderTexture.active = null;
                log.AppendLine($"heading {h}: " + string.Join(", ", ListRel(bridge)));
            }
            File.WriteAllText(Path.Combine(outDir, "relations.txt"), log.ToString());
            Debug.Log(log.ToString());
            EditorApplication.Exit(0);
        }

        static IEnumerable<string> ListRel(EgoSpatialSceneBridge b) { foreach (var kv in b.Latest) yield return $"{kv.Key}={kv.Value.Direction}"; }
    }

    // Minimal JSON parser (objects, arrays, strings, numbers, true/false/null).
    static class MiniJson
    {
        public static object Parse(string s) { int i = 0; return Val(s, ref i); }
        static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }
        static object Val(string s, ref int i)
        {
            Ws(s, ref i);
            char c = s[i];
            if (c == '{') { i++; var d = new Dictionary<string, object>(); Ws(s, ref i); if (s[i] == '}') { i++; return d; }
                while (true) { Ws(s, ref i); var k = Str(s, ref i); Ws(s, ref i); i++; d[k] = Val(s, ref i); Ws(s, ref i); if (s[i++] == '}') return d; } }
            if (c == '[') { i++; var a = new List<object>(); Ws(s, ref i); if (s[i] == ']') { i++; return a; }
                while (true) { a.Add(Val(s, ref i)); Ws(s, ref i); if (s[i++] == ']') return a; } }
            if (c == '"') return Str(s, ref i);
            if (s.Substring(i).StartsWith("true")) { i += 4; return true; }
            if (s.Substring(i).StartsWith("false")) { i += 5; return false; }
            if (s.Substring(i).StartsWith("null")) { i += 4; return null; }
            int st = i; while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            return double.Parse(s.Substring(st, i - st), CultureInfo.InvariantCulture);
        }
        static string Str(string s, ref int i)
        {
            var sb = new StringBuilder(); i++;
            while (s[i] != '"') { if (s[i] == '\\') { i++; char e = s[i]; sb.Append(e == 'n' ? '\n' : e == 't' ? '\t' : e == 'u' ? (char)Convert.ToInt32(s.Substring(i + 1, 4), 16) : e); if (e == 'u') i += 4; } else sb.Append(s[i]); i++; }
            i++; return sb.ToString();
        }
    }
}
