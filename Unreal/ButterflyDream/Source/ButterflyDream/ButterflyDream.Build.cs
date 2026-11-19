using System.IO;
using UnrealBuildTool;

public class ButterflyDream : ModuleRules
{
	public ButterflyDream(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.NoPCHs;
		bUseUnity = true;

		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine",
				"InputCore",
				"EnhancedInput",
				"UMG",
				"Slate",
				"SlateCore",
				"ApplicationCore",
				"Json",
				"JsonUtilities",
				"Niagara"
			});

		if (Target.bBuildEditor)
		{
			PrivateIncludePaths.Add(Path.Combine(Plugins.GetPlugin("Niagara").Directory.FullName, "Source", "Niagara", "Internal"));
			PublicDependencyModuleNames.AddRange(
				new string[]
				{
					"NiagaraEditor",
					"AssetTools"
				});
		}
	}
}
