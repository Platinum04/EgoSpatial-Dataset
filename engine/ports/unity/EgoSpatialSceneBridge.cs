// Unity / Meta Quest 3S scene bridge for EgoSpatial.
// Attach to any GameObject. Assign the XR camera (e.g. OVRCameraRig CenterEyeAnchor or Main Camera)
// and the tracked objects. Each frame (or on demand) it converts Unity transforms into the canonical
// spatial state and computes deterministic relations.
//
// Perception sources (be explicit in demos):
//   * Simulated   : objects placed by hand in the scene.
//   * Live (Quest): objects are anchors from Meta's Scene API / MRUK (e.g. MRUKAnchor transforms for
//                   tables, couches, doors) or spatial anchors created by the user. Set `source = "live"`.
using System.Collections.Generic;
using System.Text;
using UnityEngine;

namespace EgoSpatial
{
    public class EgoSpatialSceneBridge : MonoBehaviour
    {
        [System.Serializable] public class Tracked { public string id; public string label; public Transform transform; }

        public Transform xrCamera;
        public List<Tracked> objects = new List<Tracked>();
        [Tooltip("simulated | recorded | live")] public string source = "simulated";
        [Tooltip("Compass bearing of Unity +Z, if known (0 = treat +Z as North).")] public float northOffsetDeg = 0f;
        public TextMesh debugLabel;     // optional world-space label
        public bool logToConsole = false;

        public Dictionary<string, Relation> Latest { get; private set; }

        public SpatialState BuildState()
        {
            var s = new SpatialState { Source = source };
            var cam = xrCamera != null ? xrCamera : Camera.main.transform;
            s.AgentPosition = ToCanonical(cam.position);
            var q = cam.rotation;
            s.AgentHeading = Engine.NormalizeHeading(Engine.UnityHeading(q.x, q.y, q.z, q.w) + northOffsetDeg);
            foreach (var t in objects)
                if (t.transform != null)
                    s.Objects.Add(new SpatialObject { Id = t.id, Label = string.IsNullOrEmpty(t.label) ? t.id : t.label, Position = ToCanonical(t.transform.position) });
            return s;
        }

        Vec3 ToCanonical(Vector3 p)
        {
            if (northOffsetDeg == 0f) return new Vec3(p.x, p.y, p.z);
            double r = northOffsetDeg * System.Math.PI / 180.0;  // rotate clockwise into true-north frame
            return new Vec3(p.x * System.Math.Cos(r) + p.z * System.Math.Sin(r), p.y, -p.x * System.Math.Sin(r) + p.z * System.Math.Cos(r));
        }

        void Update()
        {
            if (objects.Count == 0) return;
            try
            {
                Latest = Engine.AllRelations(BuildState());
                var sb = new StringBuilder($"[{source.ToUpper()}]\n");
                foreach (var kv in Latest) sb.AppendLine($"{kv.Key}: {kv.Value.Direction} ({kv.Value.SignedAngleDeg:0}°)");
                if (debugLabel != null) debugLabel.text = sb.ToString();
                if (logToConsole) Debug.Log(sb.ToString());
            }
            catch (SpatialStateException e) { if (debugLabel != null) debugLabel.text = e.Message; }
        }
    }
}
