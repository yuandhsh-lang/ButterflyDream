#include "ButterflyTypography.h"

#include "Misc/CoreDelegates.h"
#include "Misc/Paths.h"
#include "Styling/CoreStyle.h"

namespace ButterflyFontCacheInternal
{
	static TSharedPtr<const FStandaloneCompositeFont> GBrushFont;
	static TSharedPtr<const FStandaloneCompositeFont> GClassicalFont;
	static TSharedPtr<const FStandaloneCompositeFont> GSealFont;
	static bool bGPreExitBound = false;

	static FString ResolveFontFilePath(const TCHAR* TtfFileName)
	{
		const TArray<FString> Candidates = {
			FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Fonts"), TtfFileName)),
			FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("../../Assets/Fonts"), TtfFileName))
		};

		for (const FString& Path : Candidates)
		{
			if (FPaths::FileExists(Path))
			{
				return Path;
			}
		}
		return FString();
	}

	static FSlateFontInfo BuildFontInfo(
		const TSharedPtr<const FCompositeFont>& Composite,
		float Size,
		int32 LetterSpacing,
		int32 OutlineSize,
		const FLinearColor& OutlineColor,
		bool bBoldFallback)
	{
		FFontOutlineSettings Outline(FMath::Max(0, OutlineSize), OutlineColor);
		Outline.bSeparateFillAlpha = true;

		if (Composite.IsValid())
		{
			FSlateFontInfo Info(Composite, Size, FName(TEXT("Regular")), Outline);
			Info.LetterSpacing = LetterSpacing;
			return Info;
		}

		FSlateFontInfo Fallback = FCoreStyle::GetDefaultFontStyle(bBoldFallback ? "Bold" : "Regular", Size);
		Fallback.OutlineSettings = Outline;
		Fallback.LetterSpacing = LetterSpacing;
		return Fallback;
	}
}

void FButterflyTypography::EnsurePreExitRegistered()
{
	if (!ButterflyFontCacheInternal::bGPreExitBound)
	{
		ButterflyFontCacheInternal::bGPreExitBound = true;
		FCoreDelegates::OnPreExit.AddStatic(&FButterflyTypography::Shutdown);
	}
}

void FButterflyTypography::Shutdown()
{
	ButterflyFontCacheInternal::GBrushFont.Reset();
	ButterflyFontCacheInternal::GClassicalFont.Reset();
	ButterflyFontCacheInternal::GSealFont.Reset();
}

TSharedPtr<const FCompositeFont> FButterflyTypography::GetOrLoadFont(
	TSharedPtr<const FStandaloneCompositeFont>& CacheSlot,
	const TCHAR* TtfFileName)
{
	EnsurePreExitRegistered();

	if (!CacheSlot.IsValid())
	{
		const FString ResolvedPath = ButterflyFontCacheInternal::ResolveFontFilePath(TtfFileName);
		if (!ResolvedPath.IsEmpty())
		{
			TSharedRef<FStandaloneCompositeFont> CreatedFont = MakeShared<FStandaloneCompositeFont>(
				FName(TEXT("Regular")),
				ResolvedPath,
				EFontHinting::Default,
				EFontLoadingPolicy::LazyLoad);
			const FString EngineFallback = FPaths::ConvertRelativePathToFull(
				FPaths::Combine(FPaths::EngineContentDir(), TEXT("Slate/Fonts/DroidSansFallback.ttf")));
			if (FPaths::FileExists(EngineFallback))
			{
				FTypefaceEntry& FallbackEntry = CreatedFont->FallbackTypeface.Typeface.Fonts.AddDefaulted_GetRef();
				FallbackEntry.Name = FName(TEXT("Regular"));
				FallbackEntry.Font = FFontData(EngineFallback, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
			}
			CacheSlot = CreatedFont;
		}
	}
	return CacheSlot;
}

FSlateFontInfo FButterflyTypography::MakeBrushFont(
	float Size,
	int32 LetterSpacing,
	int32 OutlineSize,
	const FLinearColor& OutlineColor)
{
	const TSharedPtr<const FCompositeFont> Font = GetOrLoadFont(
		ButterflyFontCacheInternal::GBrushFont,
		TEXT("MaShanZheng-Regular.ttf"));
	return ButterflyFontCacheInternal::BuildFontInfo(Font, Size, LetterSpacing, OutlineSize, OutlineColor, true);
}

FSlateFontInfo FButterflyTypography::MakeClassicalFont(
	float Size,
	int32 LetterSpacing,
	int32 OutlineSize,
	const FLinearColor& OutlineColor)
{
	const TSharedPtr<const FCompositeFont> Font = GetOrLoadFont(
		ButterflyFontCacheInternal::GClassicalFont,
		TEXT("ZCOOLXiaoWei-Regular.ttf"));
	return ButterflyFontCacheInternal::BuildFontInfo(Font, Size, LetterSpacing, OutlineSize, OutlineColor, false);
}

FSlateFontInfo FButterflyTypography::MakeSealFont(
	float Size,
	int32 LetterSpacing,
	int32 OutlineSize,
	const FLinearColor& OutlineColor)
{
	const TSharedPtr<const FCompositeFont> Font = GetOrLoadFont(
		ButterflyFontCacheInternal::GSealFont,
		TEXT("ZhiMangXing-Regular.ttf"));
	return ButterflyFontCacheInternal::BuildFontInfo(Font, Size, LetterSpacing, OutlineSize, OutlineColor, true);
}

const TArray<FButterflyRealmDescriptor>& FButterflyTypography::GetAllRealms()
{
	static const TArray<FButterflyRealmDescriptor> Realms = {
		{
			0,
			TEXT("/Game/Maps/Lux_StarSeaDream"),
			TEXT("Lux_StarSeaDream"),
			TEXT("Lux_StarSeaDream"),
			TEXT("「庄周梦蝶 — 第一境 ｜ 梦之境 ｜ 太虚瑶池星海」"),
			TEXT("『第一境 — 梦之境 ｜ 太虚瑶池星海』  [Lux_StarSeaDream]"),
			TEXT("万斛星辰坠如雨，玄镜星河浮琼阁玉莲；越浑天星轨法阵，听墨色云海钟磬悠扬。"),
			TEXT("太虚"),
			FLinearColor(0.50f, 0.88f, 1.0f, 1.0f)
		},
		{
			1,
			TEXT("/Game/Maps/Lux_InkCloudDream"),
			TEXT("Lux_InkCloudDream"),
			TEXT("InkCloudSea"),
			TEXT("「庄周梦蝶 — 第二境 ｜ 梦之悟 ｜ 墨染云海琴台」"),
			TEXT("『第二境 — 梦之悟 ｜ 墨染云海琴台』  [Lux_InkCloudDream]"),
			TEXT("墨分五色云开万象，流光古琴弦动齐物之道；穿水墨涟漪仙门，再观七宝琉璃幻象。"),
			TEXT("齐物"),
			FLinearColor(0.88f, 0.80f, 0.64f, 1.0f)
		},
		{
			2,
			TEXT("/Game/Maps/Lux_CrystalMirageDream"),
			TEXT("Lux_CrystalMirageDream"),
			TEXT("CrystalFantasy"),
			TEXT("「庄周梦蝶 — 第三境 ｜ 梦之幻 ｜ 七宝琉璃幻境」"),
			TEXT("『第三境 — 梦之幻 ｜ 七宝琉璃幻境』  [Lux_CrystalMirageDream]"),
			TEXT("琉璃七重光华万道，浮空晶庭万镜映心；放下万象破幻见真，向混沌归途振翅而升。"),
			TEXT("破幻"),
			FLinearColor(0.84f, 0.64f, 1.0f, 1.0f)
		},
		{
			3,
			TEXT("/Game/Maps/Lux_TaijiAwakeningDream"),
			TEXT("Lux_TaijiAwakeningDream"),
			TEXT("ChaosUnity"),
			TEXT("「庄周梦蝶 — 第四境 ｜ 梦之醒 ｜ 混沌太极归一」"),
			TEXT("『第四境 — 梦之醒 ｜ 混沌太极归一』  [Lux_TaijiAwakeningDream]"),
			TEXT("混沌初开太极运转，天地与我并生、万物与我为一；穿天书画卷仙门，梦醒皆成逍遥。"),
			TEXT("物化"),
			FLinearColor(1.0f, 0.86f, 0.44f, 1.0f)
		}
	};

	return Realms;
}

const FButterflyRealmDescriptor& FButterflyTypography::FindRealmByMapOrScene(const FString& MapOrSceneName)
{
	const TArray<FButterflyRealmDescriptor>& Realms = GetAllRealms();
	for (const FButterflyRealmDescriptor& Realm : Realms)
	{
		if (MapOrSceneName.Contains(Realm.MapShortName, ESearchCase::IgnoreCase) ||
			MapOrSceneName.Contains(Realm.StorySceneId, ESearchCase::IgnoreCase))
		{
			return Realm;
		}
	}
	return Realms[0];
}

FName FButterflyTypography::NormalizeToStorySceneId(const FString& MapOrSceneName)
{
	if (MapOrSceneName.IsEmpty())
	{
		return NAME_None;
	}

	const TArray<FButterflyRealmDescriptor>& Realms = GetAllRealms();
	for (const FButterflyRealmDescriptor& Realm : Realms)
	{
		if (MapOrSceneName.Contains(Realm.MapShortName, ESearchCase::IgnoreCase) ||
			MapOrSceneName.Contains(Realm.StorySceneId, ESearchCase::IgnoreCase))
		{
			return FName(Realm.StorySceneId);
		}
	}

	return FName(*MapOrSceneName);
}
