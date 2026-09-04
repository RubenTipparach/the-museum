using Godot;

// The renderer proof behind docs/ARCHITECTURE.md ADR-0, run by
// scripts/render-proof.sh. It builds a dark room with twelve shadow casting
// lights in code, which CLAUDE.md 7 forbids for game scenes and CLAUDE.md 12
// excepts for this one file: it exists to prove the renderer draws in the
// sandbox BEFORE any authored scene exists, and it is retired the day the first
// authored room can be rendered the same way. It waits for the renderer to
// settle, writes a screenshot, prints the frame time, and quits.
public partial class Shoot : Node3D
{
    private int _frame;
    private ulong _t0;

    public override void _Ready()
    {
        var env = new WorldEnvironment { Environment = new Godot.Environment() };
        env.Environment.BackgroundMode = Godot.Environment.BGMode.Color;
        env.Environment.BackgroundColor = new Color(0.01f, 0.01f, 0.012f);
        env.Environment.AmbientLightSource = Godot.Environment.AmbientSource.Color;
        env.Environment.AmbientLightColor = new Color(0.05f, 0.05f, 0.07f);
        env.Environment.TonemapMode = Godot.Environment.ToneMapper.Agx;
        env.Environment.VolumetricFogEnabled = true;
        env.Environment.VolumetricFogDensity = 0.03f;
        env.Environment.GlowEnabled = true;
        env.Environment.SsaoEnabled = true;
        AddChild(env);

        var floor = new MeshInstance3D { Mesh = new BoxMesh { Size = new Vector3(24, 0.2f, 24) } };
        floor.MaterialOverride = new StandardMaterial3D { AlbedoColor = new Color(0.35f, 0.33f, 0.3f), Roughness = 0.6f };
        AddChild(floor);
        var wall = new MeshInstance3D { Mesh = new BoxMesh { Size = new Vector3(24, 6, 0.2f) } };
        wall.Position = new Vector3(0, 3, -6);
        wall.MaterialOverride = new StandardMaterial3D { AlbedoColor = new Color(0.25f, 0.3f, 0.28f), Roughness = 0.8f };
        AddChild(wall);

        // Twelve "display cases", each with its own shadow casting light above it.
        for (int i = 0; i < 12; i++)
        {
            float x = -8 + (i % 6) * 3.2f;
            float z = -3 + (i / 6) * 4.0f;
            var pedestal = new MeshInstance3D { Mesh = new BoxMesh { Size = new Vector3(0.8f, 1.0f, 0.8f) } };
            pedestal.Position = new Vector3(x, 0.6f, z);
            pedestal.MaterialOverride = new StandardMaterial3D { AlbedoColor = new Color(0.1f, 0.1f, 0.1f) };
            AddChild(pedestal);
            var art = new MeshInstance3D { Mesh = new TorusMesh { InnerRadius = 0.15f, OuterRadius = 0.3f } };
            art.Position = new Vector3(x, 1.4f, z);
            art.MaterialOverride = new StandardMaterial3D { AlbedoColor = new Color(0.8f, 0.5f, 0.25f), Metallic = 0.6f, Roughness = 0.35f };
            AddChild(art);
            var light = new SpotLight3D
            {
                Position = new Vector3(x, 4.5f, z + 0.6f),
                LightColor = (i % 3 == 0) ? new Color(1.0f, 0.85f, 0.6f) : new Color(0.7f, 0.85f, 1.0f),
                LightEnergy = 6.0f, SpotRange = 7, SpotAngle = 28, ShadowEnabled = true,
                LightVolumetricFogEnergy = 2.0f,
            };
            light.LookAtFromPosition(light.Position, new Vector3(x, 1.2f, z), Vector3.Forward);
            AddChild(light);
        }
        var cam = new Camera3D { Position = new Vector3(0, 2.2f, 9), Fov = 65 };
        cam.LookAtFromPosition(cam.Position, new Vector3(0, 1.0f, -1), Vector3.Up);
        AddChild(cam);
        cam.Current = true;
        _t0 = Time.GetTicksMsec();
    }

    public override void _Process(double delta)
    {
        _frame++;
        if (_frame == 12)
        {
            var img = GetViewport().GetTexture().GetImage();
            img.SavePng("user://forward_plus_lights.png");
            var ms = (Time.GetTicksMsec() - _t0) / 12.0;
            GD.Print($"SHOT {img.GetWidth()}x{img.GetHeight()} lights=12 shadowed=12 avg_frame_ms={ms:F1} driver={RenderingServer.GetCurrentRenderingDriverName()} method={RenderingServer.GetCurrentRenderingMethod()} gpu={RenderingServer.GetVideoAdapterName()}");
            GetTree().Quit();
        }
    }
}
