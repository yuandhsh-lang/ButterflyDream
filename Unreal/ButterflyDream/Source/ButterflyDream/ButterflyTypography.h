#pragma once

#include "CoreMinimal.h"
#include "Fonts/CompositeFont.h"
#include "Fonts/SlateFontInfo.h"

/** Metadata for each of the four Zhuangzi Butterfly Dream celestial realms. */
struct BUTTERFLYDREAM_API FButterflyRealmDescriptor
{
	int32 RealmIndex = 0;
	const TCHAR* MapPackagePath = TEXT("");
	const TCHAR* MapShortName = TEXT("");
	const TCHAR* StorySceneId = TEXT("");
	const TCHAR* PlaqueTitle = TEXT("");
	const TCHAR* CompassHeader = TEXT("");
	const TCHAR* CompassDesc = TEXT("");
	const TCHAR* SealText = TEXT("");
	FLinearColor AccentColor = FLinearColor::White;
};

/**
 * Shared open-source Chinese calligraphy font registry (SIL OFL 1.1) and four-realm metadata.
 * Uses UE 5.8 FStandaloneCompositeFont to load runtime TTF calligraphy without deprecated constructors,
 * and cleans up FGCObject font references cleanly on engine PreExit.
 */
class BUTTERFLYDREAM_API FButterflyTypography
{
public:
	/** MaShanZheng (马善政毛笔楷书) — bold artistic brush calligraphy for primary poetic verses & titles. */
	static FSlateFontInfo MakeBrushFont(
		float Size,
		int32 LetterSpacing = 85,
		int32 OutlineSize = 2,
		const FLinearColor& OutlineColor = FLinearColor(0.015f, 0.012f, 0.032f, 0.90f));

	/** ZCOOLXiaoWei (站酷小薇体) — refined classical serif/handwritten font for subtitles, plaques & compass cards. */
	static FSlateFontInfo MakeClassicalFont(
		float Size,
		int32 LetterSpacing = 50,
		int32 OutlineSize = 1,
		const FLinearColor& OutlineColor = FLinearColor(0.010f, 0.014f, 0.028f, 0.82f));

	/** ZhiMangXing (芷芒行书) — expressive running-script brush font for cinnabar seal stamps. */
	static FSlateFontInfo MakeSealFont(
		float Size,
		int32 LetterSpacing = 20,
		int32 OutlineSize = 1,
		const FLinearColor& OutlineColor = FLinearColor(0.22f, 0.02f, 0.02f, 0.78f));

	/** Returns all four canonical realms in progression order (Realms I through IV). */
	static const TArray<FButterflyRealmDescriptor>& GetAllRealms();

	/** Match a world/package map name or story_config scene_id to one of the four canonical realms. */
	static const FButterflyRealmDescriptor& FindRealmByMapOrScene(const FString& MapOrSceneName);

	/** Normalize any map short name or JSON scene_id to the canonical StorySceneId in story_config.json. */
	static FName NormalizeToStorySceneId(const FString& MapOrSceneName);

	/** Release cached FStandaloneCompositeFont instances prior to UObject shutdown. */
	static void Shutdown();

private:
	static TSharedPtr<const FCompositeFont> GetOrLoadFont(
		TSharedPtr<const FStandaloneCompositeFont>& CacheSlot,
		const TCHAR* TtfFileName);
	static void EnsurePreExitRegistered();
};
