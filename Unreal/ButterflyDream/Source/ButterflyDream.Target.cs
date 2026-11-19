using UnrealBuildTool;

public class ButterflyDreamTarget : TargetRules
{
	public ButterflyDreamTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("ButterflyDream");
	}
}
