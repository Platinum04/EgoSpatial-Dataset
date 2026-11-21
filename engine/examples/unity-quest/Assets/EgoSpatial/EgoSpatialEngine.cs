// EgoSpatial deterministic engine — C# port for Unity / Meta Quest 3S.
// Pure C# (no UnityEngine dependency) so it can be unit-tested outside Unity.
// Canonical frame: +X East, +Y Up, +Z North; heading clockwise from North (degrees).
// Unity mapping: Unity +X -> East, +Z -> North, camera yaw (clockwise from +Z) -> heading.
// Conformance: must reproduce tests/vectors.json from the Python reference engine.
using System;
using System.Collections.Generic;

namespace EgoSpatial
{
    public class SpatialStateException : Exception { public SpatialStateException(string m) : base(m) { } }

    public struct Vec3 { public double x, y, z; public Vec3(double x, double y, double z) { this.x = x; this.y = y; this.z = z; } }

    public class SpatialObject { public string Id; public string Label; public Vec3 Position; }

    public class SpatialState
    {
        public Vec3 AgentPosition; public double AgentHeading; public string Source = "unspecified";
        public List<SpatialObject> Objects = new List<SpatialObject>();

        public SpatialObject Get(string id)
        {
            foreach (var o in Objects) if (o.Id == id) return o;
            throw new SpatialStateException("unknown object: " + id);
        }

        public void Validate()
        {
            if (double.IsNaN(AgentHeading) || double.IsInfinity(AgentHeading)) throw new SpatialStateException("agent heading must be finite");
            if (Objects.Count == 0) throw new SpatialStateException("objects must be non-empty");
            var seen = new HashSet<string>();
            foreach (var o in Objects)
            {
                if (string.IsNullOrEmpty(o.Id)) throw new SpatialStateException("object id required");
                if (!seen.Add(o.Id)) throw new SpatialStateException("duplicate object id: " + o.Id);
                if (double.IsNaN(o.Position.x) || double.IsNaN(o.Position.z) || double.IsInfinity(o.Position.x) || double.IsInfinity(o.Position.z))
                    throw new SpatialStateException("object position must be finite: " + o.Id);
            }
        }
    }

    public class Relation
    {
        public string Kind, Target, Reference, Direction;
        public double SignedAngleDeg, FrameHeadingDeg;
        public Vec3 WorldDisplacement, EgoDisplacement;
    }

    public static class Engine
    {
        const double Deg = Math.PI / 180.0;

        public static double NormalizeHeading(double d)
        {
            if (double.IsNaN(d) || double.IsInfinity(d)) throw new SpatialStateException("heading must be finite");
            double h = d % 360.0; if (h < 0) h += 360.0; return h == 360.0 ? 0.0 : h;
        }

        public static Vec3 WorldToEgocentric(Vec3 v, double heading)
        {
            double t = NormalizeHeading(heading) * Deg;
            return new Vec3(v.x * Math.Cos(t) - v.z * Math.Sin(t), v.y, v.x * Math.Sin(t) + v.z * Math.Cos(t));
        }

        public static double Bearing(Vec3 v)
        {
            if (v.x == 0 && v.z == 0) throw new SpatialStateException("bearing of zero vector is undefined");
            return NormalizeHeading(Math.Atan2(v.x, v.z) / Deg);
        }

        public static string Classify(Vec3 ego, double tol = 1e-9)
        {
            if (Math.Abs(ego.x) < tol && Math.Abs(ego.z) < tol) throw new SpatialStateException("cannot classify a zero-length horizontal vector");
            if (Math.Abs(ego.z) >= Math.Abs(ego.x)) return ego.z > 0 ? "front" : "behind";
            return ego.x > 0 ? "right" : "left";
        }

        static Vec3 Sub(Vec3 a, Vec3 b) => new Vec3(b.x - a.x, b.y - a.y, b.z - a.z);

        static Relation Make(string kind, string target, string reference, Vec3 world, double heading)
        {
            var ego = WorldToEgocentric(world, heading);
            double a = Math.Atan2(ego.x, ego.z) / Deg; if (a == -180.0) a = 180.0;
            return new Relation { Kind = kind, Target = target, Reference = reference, Direction = Classify(ego), SignedAngleDeg = a,
                                  FrameHeadingDeg = NormalizeHeading(heading), WorldDisplacement = world, EgoDisplacement = ego };
        }

        public static Relation ObjectToAgent(SpatialState s, string target)
        { s.Validate(); return Make("object_to_agent", target, "agent", Sub(s.AgentPosition, s.Get(target).Position), s.AgentHeading); }

        public static Relation ObjectToObject(SpatialState s, string reference, string target)
        {
            s.Validate(); if (reference == target) throw new SpatialStateException("reference and target must differ");
            return Make("object_to_object", target, reference, Sub(s.Get(reference).Position, s.Get(target).Position), s.AgentHeading);
        }

        public static Relation ReferenceFrame(SpatialState s, string reference, string target)
        {
            s.Validate(); if (reference == target) throw new SpatialStateException("reference and target must differ");
            double h = Bearing(Sub(s.AgentPosition, s.Get(reference).Position));
            return Make("reference_frame", target, reference, Sub(s.AgentPosition, s.Get(target).Position), h);
        }

        public static Dictionary<string, Relation> AllRelations(SpatialState s)
        {
            var d = new Dictionary<string, Relation>();
            foreach (var o in s.Objects) d[o.Id] = ObjectToAgent(s, o.Id);
            return d;
        }

        /// Heading from a Unity rotation quaternion (x,y,z,w): forward = q * (0,0,1).
        public static double UnityHeading(double qx, double qy, double qz, double qw)
        {
            double n = Math.Sqrt(qx * qx + qy * qy + qz * qz + qw * qw);
            if (!(n > 0)) throw new SpatialStateException("invalid quaternion");
            qx /= n; qy /= n; qz /= n; qw /= n;
            // rotate (0,0,1)
            double tx = 2 * qy, ty = -2 * qx, tz = 0;              // t = 2 * cross(q.xyz, v)
            double fx = 0 + qw * tx + (qy * tz - qz * ty);
            double fz = 1 + qw * tz + (qx * ty - qy * tx);
            if (Math.Abs(fx) < 1e-12 && Math.Abs(fz) < 1e-12) throw new SpatialStateException("heading undefined (looking up/down)");
            return NormalizeHeading(Math.Atan2(fx, fz) / Deg);
        }
    }
}
