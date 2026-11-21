// Desktop/editor stand-in for head turning: slowly rotates the camera so the labels change.
// On a headset, remove this component; the XR rig drives the camera instead.
using UnityEngine;

namespace EgoSpatial
{
    public class EgoSpatialDemoTurner : MonoBehaviour
    {
        public float degreesPerSecond = 20f;
        public bool autoTurn = true;

        void Update()
        {
            if (autoTurn) transform.Rotate(0f, degreesPerSecond * Time.deltaTime, 0f, Space.World);
        }
    }
}
