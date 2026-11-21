// Floating label above one object: "TABLE · LEFT · 2.0 m", recoloured by direction.
using UnityEngine;

namespace EgoSpatial
{
    public class EgoSpatialObjectLabel : MonoBehaviour
    {
        public EgoSpatialSceneBridge bridge;
        public string objectId;
        public TextMesh text;
        public Transform faceCamera;

        void LateUpdate() => Tick();

        public void Tick()
        {
            if (bridge == null || text == null || bridge.Latest == null || !bridge.Latest.TryGetValue(objectId, out var r)) return;
            var d = r.WorldDisplacement;
            double dist = System.Math.Sqrt(d.x * d.x + d.z * d.z);
            text.text = $"{objectId.ToUpper()} · {r.Direction.ToUpper()} · {dist:0.0} m";
            text.color = r.Direction == "left" ? new Color(0.4f, 0.7f, 1f) : r.Direction == "right" ? new Color(1f, 0.75f, 0.3f)
                       : r.Direction == "front" ? new Color(0.35f, 0.9f, 0.55f) : new Color(1f, 0.45f, 0.45f);
            if (faceCamera != null) transform.rotation = Quaternion.LookRotation(transform.position - faceCamera.position);
        }
    }
}
