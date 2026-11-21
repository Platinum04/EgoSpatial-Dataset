// One-click Quest 3S setup and build for the EgoSpatial Unity demo.
//   EgoSpatial > Setup for Quest      : Android target, IL2CPP/ARM64, API 32+, linear colour, OpenXR + Meta Quest feature.
//   EgoSpatial > Build Quest APK      : Builds/EgoSpatialQuest.apk
// Batch: Unity -batchmode -quit -projectPath . -executeMethod EgoSpatial.QuestSetup.SetupAndBuildBatch
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEngine;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features.Interactions;
using UnityEngine.XR.OpenXR.Features.MetaQuestSupport;

namespace EgoSpatial
{
    public static class QuestSetup
    {
        const string Apk = "Builds/EgoSpatialQuest.apk";

        [MenuItem("EgoSpatial/Setup for Quest")]
        public static void Setup()
        {
            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.Android)
                EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android);

            var android = NamedBuildTarget.Android;
            PlayerSettings.companyName = "EgoSpatial";
            PlayerSettings.productName = "EgoSpatial Quest";
            PlayerSettings.SetApplicationIdentifier(android, "dev.egospatial.unityquest");
            PlayerSettings.SetScriptingBackend(android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel32;
            PlayerSettings.colorSpace = ColorSpace.Linear;

            // XR Plug-in Management: OpenXR loader for Android.
            var getOrCreate = typeof(XRGeneralSettingsPerBuildTarget).GetMethod("GetOrCreate", BindingFlags.Static | BindingFlags.NonPublic);
            var perTarget = (XRGeneralSettingsPerBuildTarget)getOrCreate.Invoke(null, null);
            if (!perTarget.HasSettingsForBuildTarget(BuildTargetGroup.Android)) perTarget.CreateDefaultSettingsForBuildTarget(BuildTargetGroup.Android);
            if (!perTarget.HasManagerSettingsForBuildTarget(BuildTargetGroup.Android)) perTarget.CreateDefaultManagerSettingsForBuildTarget(BuildTargetGroup.Android);
            var gs = perTarget.SettingsForBuildTarget(BuildTargetGroup.Android);
            gs.InitManagerOnStart = true;
            XRPackageMetadataStore.AssignLoader(gs.AssignedSettings, "UnityEngine.XR.OpenXR.OpenXRLoader", BuildTargetGroup.Android);

            // OpenXR features: Meta Quest support + Touch controllers.
            var ox = OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Android);
            if (ox != null)
            {
                foreach (var f in ox.GetFeatures())
                    if (f is MetaQuestFeature || f is OculusTouchControllerProfile || f is MetaQuestTouchPlusControllerProfile) f.enabled = true;
                EditorUtility.SetDirty(ox);
            }

            // On the headset the user's head turns the camera, so disable the desktop auto-turner.
            foreach (var t in Object.FindObjectsByType<EgoSpatialDemoTurner>(FindObjectsSortMode.None))
            { t.autoTurn = false; EditorUtility.SetDirty(t); }
            UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes();

            AssetDatabase.SaveAssets();
            Debug.Log("EgoSpatial: Quest setup done (Android, IL2CPP ARM64, API 32+, OpenXR + Meta Quest).");
        }

        [MenuItem("EgoSpatial/Build Quest APK")]
        public static bool Build()
        {
            Directory.CreateDirectory("Builds");
            var r = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { "Assets/Scenes/EgoSpatialDemo.unity" },
                locationPathName = Apk,
                target = BuildTarget.Android,
                options = BuildOptions.None
            });
            Debug.Log($"EgoSpatial: build {r.summary.result}, {r.summary.totalSize / 1048576f:0.0} MB -> {Path.GetFullPath(Apk)}");
            return r.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded;
        }

        public static void SetupAndBuildBatch()
        {
            UnityEditor.SceneManagement.EditorSceneManager.OpenScene("Assets/Scenes/EgoSpatialDemo.unity");
            Setup();
            EditorApplication.Exit(Build() ? 0 : 1);
        }
    }
}
