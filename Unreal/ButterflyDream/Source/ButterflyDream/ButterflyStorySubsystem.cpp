#include "ButterflyStorySubsystem.h"

#include "ButterflyDreamGateActor.h"
#include "ButterflyPawn.h"
#include "ButterflyPlayerController.h"
#include "ButterflyStoryTextActor.h"
#include "ButterflyTypography.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/DataTable.h"
#include "Engine/Font.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerStart.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

DEFINE_LOG_CATEGORY_STATIC(LogButterflyStory, Log, All);

// ---------------------------------------------------------------------------
// Subsystem lifecycle
// ---------------------------------------------------------------------------

bool UButterflyStorySubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World && DoesSupportWorldType(World->WorldType);
}

bool UButterflyStorySubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId UButterflyStorySubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UButterflyStorySubsystem, STATGROUP_Tickables);
}

void UButterflyStorySubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
}

void UButterflyStorySubsystem::Deinitialize()
{
	StoryEntries.Empty();
	TriggeredIds.Empty();
	ActiveTextActors.Empty();
	CachedFonts.Empty();
	TrackedPawn.Reset();
	WorldElapsedSeconds = 0.0f;
	bWaypointsResolved = false;
	bOpeningVerseAutoTriggered = false;

	Super::Deinitialize();
}

void UButterflyStorySubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	WorldElapsedSeconds = 0.0f;
	bOpeningVerseAutoTriggered = false;

	if (ActiveSceneId.IsNone())
	{
		ActiveSceneId = DetectWorldSceneId(InWorld);
	}

	if (StoryEntries.Num() == 0)
	{
		AutoLoadDefaultStoryConfig();
	}

	ResolveWaypointsForCurrentWorld();
}

void UButterflyStorySubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	WorldElapsedSeconds += DeltaTime;

	if (!TrackedPawn.IsValid())
	{
		if (UWorld* World = GetWorld())
		{
			if (AButterflyPawn* DiscoveredPawn = Cast<AButterflyPawn>(UGameplayStatics::GetPlayerPawn(World, 0)))
			{
				RegisterPawn(DiscoveredPawn);
			}
		}
	}

	if (!bWaypointsResolved && StoryEntries.Num() > 0)
	{
		ResolveWaypointsForCurrentWorld();
	}

	CleanUpFinishedActors();

	CheckProximityTriggers();
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

void UButterflyStorySubsystem::RegisterPawn(AButterflyPawn* InPawn)
{
	TrackedPawn = InPawn;
	if (InPawn && StoryEntries.Num() > 0 && !bWaypointsResolved)
	{
		ResolveWaypointsForCurrentWorld();
	}
}

void UButterflyStorySubsystem::SetActiveSceneId(FName InSceneId)
{
	const FName Normalized = InSceneId.IsNone()
		? NAME_None
		: FButterflyTypography::NormalizeToStorySceneId(InSceneId.ToString());

	if (ActiveSceneId != Normalized)
	{
		ActiveSceneId = Normalized;
		bWaypointsResolved = false;
		bOpeningVerseAutoTriggered = false;
		ResolveWaypointsForCurrentWorld();
	}
}

void UButterflyStorySubsystem::AddStoryEntry(const FStoryTextEntry& Entry)
{
	FStoryTextEntry NormalizedEntry = Entry;
	if (!NormalizedEntry.SceneId.IsNone())
	{
		NormalizedEntry.SceneId = FButterflyTypography::NormalizeToStorySceneId(NormalizedEntry.SceneId.ToString());
	}
	StoryEntries.Add(MoveTemp(NormalizedEntry));

	if (!Entry.bHasExplicitWorldLocation)
	{
		bWaypointsResolved = false;
	}
}

void UButterflyStorySubsystem::ResetTriggeredState()
{
	TriggeredIds.Empty();
	bOpeningVerseAutoTriggered = false;
}

void UButterflyStorySubsystem::ResetAllEntries()
{
	StoryEntries.Empty();
	TriggeredIds.Empty();
	bWaypointsResolved = false;
	bOpeningVerseAutoTriggered = false;

	for (TWeakObjectPtr<AButterflyStoryTextActor>& WeakActor : ActiveTextActors)
	{
		if (AButterflyStoryTextActor* Actor = WeakActor.Get())
		{
			Actor->Destroy();
		}
	}
	ActiveTextActors.Empty();
}

int32 UButterflyStorySubsystem::LoadEntriesFromDataTable(const UDataTable* DataTable)
{
	if (!DataTable)
	{
		return 0;
	}

	TArray<FStoryTextEntry*> Rows;
	DataTable->GetAllRows<FStoryTextEntry>(TEXT("UButterflyStorySubsystem::LoadEntriesFromDataTable"), Rows);

	int32 LoadedCount = 0;
	const TArray<FName> RowNames = DataTable->GetRowNames();
	for (int32 Idx = 0; Idx < Rows.Num(); ++Idx)
	{
		if (const FStoryTextEntry* Row = Rows[Idx])
		{
			FStoryTextEntry Copy = *Row;
			if (Copy.EntryId.IsNone() && RowNames.IsValidIndex(Idx))
			{
				Copy.EntryId = RowNames[Idx];
			}
			if (!Copy.SceneId.IsNone())
			{
				Copy.SceneId = FButterflyTypography::NormalizeToStorySceneId(Copy.SceneId.ToString());
			}
			StoryEntries.Add(MoveTemp(Copy));
			++LoadedCount;
		}
	}

	bWaypointsResolved = false;
	return LoadedCount;
}

bool UButterflyStorySubsystem::AutoLoadDefaultStoryConfig()
{
	const TArray<FString> CandidatePaths = {
		FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectContentDir(), TEXT("StoryText/story_config.json"))),
		FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("../../Assets/StoryText/story_config.json")))
	};

	for (const FString& Candidate : CandidatePaths)
	{
		if (FPaths::FileExists(Candidate) && LoadEntriesFromJsonFile(Candidate))
		{
			return true;
		}
	}

	return false;
}

bool UButterflyStorySubsystem::LoadEntriesFromJsonFile(const FString& FilePath)
{
	FString JsonString;
	if (!FFileHelper::LoadFileToString(JsonString, *FilePath))
	{
		UE_LOG(LogButterflyStory, Warning, TEXT("Failed to read story JSON file: %s"), *FilePath);
		return false;
	}

	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);
	TSharedPtr<FJsonValue> RootValue;
	if (!FJsonSerializer::Deserialize(Reader, RootValue) || !RootValue.IsValid())
	{
		UE_LOG(LogButterflyStory, Warning, TEXT("Failed to parse JSON in: %s"), *FilePath);
		return false;
	}

	int32 AddedCount = 0;

	// Format A: structured story_config.json root object containing "scenes": [...]
	if (RootValue->Type == EJson::Object)
	{
		const TSharedPtr<FJsonObject> RootObj = RootValue->AsObject();
		const TArray<TSharedPtr<FJsonValue>>* ScenesArray = nullptr;
		if (RootObj.IsValid() && RootObj->TryGetArrayField(TEXT("scenes"), ScenesArray) && ScenesArray)
		{
			for (const TSharedPtr<FJsonValue>& SceneVal : *ScenesArray)
			{
				const TSharedPtr<FJsonObject> SceneObj = SceneVal.IsValid() ? SceneVal->AsObject() : nullptr;
				if (!SceneObj.IsValid())
				{
					continue;
				}

				FString RawSceneId, SceneTitle, SceneSubtitle, BaseColorHex;
				SceneObj->TryGetStringField(TEXT("scene_id"), RawSceneId);
				SceneObj->TryGetStringField(TEXT("scene_title"), SceneTitle);
				SceneObj->TryGetStringField(TEXT("scene_subtitle"), SceneSubtitle);
				SceneObj->TryGetStringField(TEXT("text_base_color_hex"), BaseColorHex);

				const FName CanonicalSceneId = FButterflyTypography::NormalizeToStorySceneId(RawSceneId);
				const FButterflyRealmDescriptor& RealmInfo = FButterflyTypography::FindRealmByMapOrScene(RawSceneId);
				const FColor SceneDefaultColor = ParseHexColorOrDefault(BaseColorHex, FColor(255, 215, 80, 255));
				const FString FallbackSubtitle = (!SceneSubtitle.IsEmpty() && !SceneTitle.IsEmpty())
					? FString::Printf(TEXT("%s ｜ %s"), *SceneSubtitle, *SceneTitle)
					: TEXT("庄周梦蝶 — 齐物逍遥");

				const TArray<TSharedPtr<FJsonValue>>* TextsArray = nullptr;
				if (!SceneObj->TryGetArrayField(TEXT("texts"), TextsArray) || !TextsArray)
				{
					continue;
				}

				for (const TSharedPtr<FJsonValue>& TextVal : *TextsArray)
				{
					const TSharedPtr<FJsonObject> Obj = TextVal.IsValid() ? TextVal->AsObject() : nullptr;
					if (!Obj.IsValid())
					{
						continue;
					}

					FStoryTextEntry Entry;
					Entry.SceneId = CanonicalSceneId;
					Entry.SealText = FText::FromString(RealmInfo.SealText);

					FString IdStr;
					if (Obj->TryGetStringField(TEXT("id"), IdStr))
					{
						Entry.EntryId = FName(*IdStr);
					}

					FString RawText;
					if (Obj->TryGetStringField(TEXT("text"), RawText))
					{
						Entry.DisplayText = FText::FromString(RawText);
					}

					FString NarrativeNote;
					if (Obj->TryGetStringField(TEXT("narrative_note"), NarrativeNote) && !NarrativeNote.IsEmpty())
					{
						Entry.SubtitleText = FText::FromString(
							!SceneSubtitle.IsEmpty()
								? FString::Printf(TEXT("%s ｜ %s"), *SceneSubtitle, *NarrativeNote)
								: NarrativeNote);
					}
					else
					{
						Entry.SubtitleText = FText::FromString(FallbackSubtitle);
					}

					FString WaypointStr;
					if (Obj->TryGetStringField(TEXT("trigger_waypoint"), WaypointStr))
					{
						Entry.WaypointTag = FName(*WaypointStr);
					}

					double DistMeters = -1.0;
					if (Obj->TryGetNumberField(TEXT("trigger_distance_m"), DistMeters))
					{
						Entry.TriggerDistanceMeters = static_cast<float>(DistMeters);
					}

					double FadeInSec = 2.0;
					if (Obj->TryGetNumberField(TEXT("fade_in_seconds"), FadeInSec))
					{
						Entry.FadeInDuration = static_cast<float>(FadeInSec);
					}

					double DisplaySec = 5.0;
					if (Obj->TryGetNumberField(TEXT("display_seconds"), DisplaySec))
					{
						Entry.LingerDuration = static_cast<float>(DisplaySec);
					}

					double FadeOutSec = 1.5;
					if (Obj->TryGetNumberField(TEXT("fade_out_seconds"), FadeOutSec))
					{
						Entry.FadeOutDuration = static_cast<float>(FadeOutSec);
					}

					double RawFontSize = 76.0;
					if (Obj->TryGetNumberField(TEXT("font_size"), RawFontSize))
					{
						Entry.WorldSize = FMath::Clamp(static_cast<float>(RawFontSize) * 0.62f, 40.0f, 68.0f);
					}

					FString FontStr;
					if (Obj->TryGetStringField(TEXT("font"), FontStr))
					{
						Entry.FontName = FName(*FontStr);
					}

					FString ColorHex;
					Obj->TryGetStringField(TEXT("color_hex"), ColorHex);
					Entry.TextColor = ParseHexColorOrDefault(ColorHex, SceneDefaultColor);

					FString GlowHex;
					Obj->TryGetStringField(TEXT("glow_color_hex"), GlowHex);
					Entry.GlowColor = ParseHexColorOrDefault(GlowHex, Entry.TextColor);

					FString EffectStr;
					Obj->TryGetStringField(TEXT("effect"), EffectStr);
					Entry.TextEffect = ParseTextEffectString(EffectStr);

					Entry.bHasExplicitWorldLocation = false;
					StoryEntries.Add(MoveTemp(Entry));
					++AddedCount;
				}
			}
		}
	}
	// Format B: flat array of FStoryTextEntry JSON objects
	else if (RootValue->Type == EJson::Array)
	{
		const TArray<TSharedPtr<FJsonValue>>& JsonArray = RootValue->AsArray();
		for (const TSharedPtr<FJsonValue>& JsonValue : JsonArray)
		{
			const TSharedPtr<FJsonObject> Obj = JsonValue.IsValid() ? JsonValue->AsObject() : nullptr;
			if (!Obj.IsValid())
			{
				continue;
			}

			FStoryTextEntry Entry;
			FString EntryIdStr, SceneIdStr, DisplayStr, SubtitleStr, SealStr, EffectStr, FontStr;
			if (Obj->TryGetStringField(TEXT("EntryId"), EntryIdStr))
			{
				Entry.EntryId = FName(*EntryIdStr);
			}
			if (Obj->TryGetStringField(TEXT("SceneId"), SceneIdStr))
			{
				Entry.SceneId = FButterflyTypography::NormalizeToStorySceneId(SceneIdStr);
				Entry.SealText = FText::FromString(FButterflyTypography::FindRealmByMapOrScene(SceneIdStr).SealText);
			}
			if (Obj->TryGetStringField(TEXT("DisplayText"), DisplayStr))
			{
				Entry.DisplayText = FText::FromString(DisplayStr);
			}
			if (Obj->TryGetStringField(TEXT("SubtitleText"), SubtitleStr))
			{
				Entry.SubtitleText = FText::FromString(SubtitleStr);
			}
			if (Obj->TryGetStringField(TEXT("SealText"), SealStr))
			{
				Entry.SealText = FText::FromString(SealStr);
			}
			if (Obj->TryGetStringField(TEXT("FontName"), FontStr))
			{
				Entry.FontName = FName(*FontStr);
			}

			const TSharedPtr<FJsonObject>* TriggerLoc = nullptr;
			if (Obj->TryGetObjectField(TEXT("TriggerLocation"), TriggerLoc) && TriggerLoc && (*TriggerLoc).IsValid())
			{
				Entry.TriggerLocation.X = (*TriggerLoc)->GetNumberField(TEXT("X"));
				Entry.TriggerLocation.Y = (*TriggerLoc)->GetNumberField(TEXT("Y"));
				Entry.TriggerLocation.Z = (*TriggerLoc)->GetNumberField(TEXT("Z"));
				Entry.bHasExplicitWorldLocation = true;
			}

			const TSharedPtr<FJsonObject>* SpawnLoc = nullptr;
			if (Obj->TryGetObjectField(TEXT("TextSpawnLocation"), SpawnLoc) && SpawnLoc && (*SpawnLoc).IsValid())
			{
				Entry.TextSpawnLocation.X = (*SpawnLoc)->GetNumberField(TEXT("X"));
				Entry.TextSpawnLocation.Y = (*SpawnLoc)->GetNumberField(TEXT("Y"));
				Entry.TextSpawnLocation.Z = (*SpawnLoc)->GetNumberField(TEXT("Z"));
			}
			else
			{
				Entry.TextSpawnLocation = Entry.TriggerLocation + FVector(0.0f, 0.0f, 195.0f);
			}

			double NumVal = 0.0;
			if (Obj->TryGetNumberField(TEXT("TriggerRadius"), NumVal))
			{
				Entry.TriggerRadius = static_cast<float>(NumVal);
			}
			if (Obj->TryGetNumberField(TEXT("WorldSize"), NumVal))
			{
				Entry.WorldSize = static_cast<float>(NumVal);
			}
			if (Obj->TryGetNumberField(TEXT("FadeInDuration"), NumVal))
			{
				Entry.FadeInDuration = static_cast<float>(NumVal);
			}
			if (Obj->TryGetNumberField(TEXT("LingerDuration"), NumVal))
			{
				Entry.LingerDuration = static_cast<float>(NumVal);
			}
			if (Obj->TryGetNumberField(TEXT("FadeOutDuration"), NumVal))
			{
				Entry.FadeOutDuration = static_cast<float>(NumVal);
			}

			const TSharedPtr<FJsonObject>* ColorObj = nullptr;
			if (Obj->TryGetObjectField(TEXT("TextColor"), ColorObj) && ColorObj && (*ColorObj).IsValid())
			{
				Entry.TextColor.R = static_cast<uint8>((*ColorObj)->GetIntegerField(TEXT("R")));
				Entry.TextColor.G = static_cast<uint8>((*ColorObj)->GetIntegerField(TEXT("G")));
				Entry.TextColor.B = static_cast<uint8>((*ColorObj)->GetIntegerField(TEXT("B")));
				Entry.TextColor.A = 255;
				Entry.GlowColor = Entry.TextColor;
			}

			if (Obj->TryGetStringField(TEXT("TextEffect"), EffectStr))
			{
				Entry.TextEffect = ParseTextEffectString(EffectStr);
			}

			StoryEntries.Add(MoveTemp(Entry));
			++AddedCount;
		}
	}

	bWaypointsResolved = false;
	UE_LOG(LogButterflyStory, Log, TEXT("Loaded %d calligraphy story entries from %s"), AddedCount, *FilePath);
	return AddedCount > 0;
}

void UButterflyStorySubsystem::ResolveWaypointsForCurrentWorld()
{
	UWorld* World = GetWorld();
	if (!World || StoryEntries.Num() == 0)
	{
		return;
	}

	if (ActiveSceneId.IsNone())
	{
		ActiveSceneId = DetectWorldSceneId(*World);
	}

	FVector StartLoc = FVector::ZeroVector;
	FRotator StartRot = FRotator::ZeroRotator;
	bool bHasStart = false;

	if (AActor* PlayerStart = UGameplayStatics::GetActorOfClass(World, APlayerStart::StaticClass()))
	{
		StartLoc = PlayerStart->GetActorLocation();
		StartRot = PlayerStart->GetActorRotation();
		bHasStart = true;
	}
	else if (const AButterflyPawn* Pawn = TrackedPawn.Get())
	{
		StartLoc = Pawn->GetActorLocation();
		StartRot = Pawn->GetActorRotation();
		bHasStart = true;
	}

	if (!bHasStart)
	{
		return;
	}

	// Pick the primary forward DreamGate in the scene (farthest gate from start if multiple exist)
	FVector EndLoc = StartLoc + StartRot.Vector() * 5400.0f;
	TArray<AActor*> GateActors;
	UGameplayStatics::GetAllActorsOfClass(World, AButterflyDreamGateActor::StaticClass(), GateActors);
	float BestGateDistSq = FMath::Square(450.0f);
	for (AActor* GateCandidate : GateActors)
	{
		if (!IsValid(GateCandidate))
		{
			continue;
		}
		const FVector CandidateLoc = GateCandidate->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f);
		const float DistSq = FVector::DistSquared(StartLoc, CandidateLoc);
		if (DistSq > BestGateDistSq)
		{
			BestGateDistSq = DistSq;
			EndLoc = CandidateLoc;
		}
	}

	const FVector PathDelta = EndLoc - StartLoc;
	const float PathLength = FMath::Max(800.0f, static_cast<float>(PathDelta.Size()));
	const FVector PathDir = PathDelta.GetSafeNormal(UE_SMALL_NUMBER, FVector::ForwardVector);
	const FVector RightDir = FVector::CrossProduct(FVector::UpVector, PathDir).GetSafeNormal(UE_SMALL_NUMBER, FVector::RightVector);

	TArray<int32> SceneEntryIndices;
	for (int32 Idx = 0; Idx < StoryEntries.Num(); ++Idx)
	{
		const FStoryTextEntry& Entry = StoryEntries[Idx];
		if (!Entry.bHasExplicitWorldLocation && DoesEntryMatchActiveScene(Entry))
		{
			SceneEntryIndices.Add(Idx);
		}
	}

	static constexpr float PresetRatios[7] = { 0.06f, 0.20f, 0.34f, 0.48f, 0.62f, 0.76f, 0.88f };
	const int32 NumDynamic = SceneEntryIndices.Num();
	const float BaseStepRadius = 140.0f;

	for (int32 OrderIdx = 0; OrderIdx < NumDynamic; ++OrderIdx)
	{
		FStoryTextEntry& Entry = StoryEntries[SceneEntryIndices[OrderIdx]];

		// 1. Honour explicit level waypoint actor if placed with matching tag/name
		AActor* MatchedWaypoint = nullptr;
		if (!Entry.WaypointTag.IsNone())
		{
			for (TActorIterator<AActor> It(World); It; ++It)
			{
				AActor* Candidate = *It;
				if (Candidate && (Candidate->ActorHasTag(Entry.WaypointTag) || Candidate->GetFName() == Entry.WaypointTag))
				{
					MatchedWaypoint = Candidate;
					break;
				}
			}
		}

		if (MatchedWaypoint)
		{
			Entry.TriggerLocation = MatchedWaypoint->GetActorLocation();
			Entry.TriggerRadius = BaseStepRadius;
			Entry.TextSpawnLocation = Entry.TriggerLocation + PathDir * 320.0f + FVector(0.0f, 0.0f, 195.0f);
			continue;
		}

		// 2. Staggered 7-milestone calligraphy corridor along Start -> DreamGate
		const float PathRatio = (NumDynamic == 7)
			? PresetRatios[OrderIdx]
			: ((NumDynamic > 1)
				? FMath::Lerp(0.06f, 0.88f, static_cast<float>(OrderIdx) / static_cast<float>(NumDynamic - 1))
				: 0.15f);

		const FVector CorridorPoint = FMath::Lerp(StartLoc, EndLoc, PathRatio);
		const float LateralStaggerCm = (OrderIdx % 2 == 1) ? -480.0f : 480.0f;

		Entry.TriggerLocation = CorridorPoint;
		Entry.TriggerRadius = BaseStepRadius;
		Entry.TextSpawnLocation =
			CorridorPoint +
			PathDir * 340.0f +
			RightDir * LateralStaggerCm +
			FVector(0.0f, 0.0f, 195.0f);
	}

	bWaypointsResolved = true;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

bool UButterflyStorySubsystem::DoesEntryMatchActiveScene(const FStoryTextEntry& Entry) const
{
	if (ActiveSceneId.IsNone() || Entry.SceneId.IsNone())
	{
		return true;
	}
	return Entry.SceneId == ActiveSceneId;
}

void UButterflyStorySubsystem::TryAutoTriggerOpeningVerse()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}

	APawn* PlayerPawn = TrackedPawn.Get();
	if (!PlayerPawn)
	{
		PlayerPawn = UGameplayStatics::GetPlayerPawn(World, 0);
	}
	if (!PlayerPawn)
	{
		return;
	}

	bOpeningVerseAutoTriggered = true;

	for (const FStoryTextEntry& Entry : StoryEntries)
	{
		if (!DoesEntryMatchActiveScene(Entry))
		{
			continue;
		}

		const FName EffectiveId = Entry.EntryId.IsNone()
			? FName(*Entry.DisplayText.ToString())
			: Entry.EntryId;

		if (TriggeredIds.Contains(EffectiveId))
		{
			return;
		}

		TriggeredIds.Add(EffectiveId);
		NotifyHudEcho(Entry);
		return;
	}
}

ETextEffect UButterflyStorySubsystem::ParseTextEffectString(const FString& EffectStr)
{
	const FString Lower = EffectStr.ToLower();
	if (Lower == TEXT("golden_seal") || Lower == TEXT("goldenseal"))
	{
		return ETextEffect::GoldenSeal;
	}
	if (Lower == TEXT("starlight_coalesce") || Lower == TEXT("starlightcoalesce"))
	{
		return ETextEffect::StarlightCoalesce;
	}
	if (Lower == TEXT("petal_gather") || Lower == TEXT("particlegather") || Lower == TEXT("chaos_emerge"))
	{
		return ETextEffect::ParticleGather;
	}
	if (Lower == TEXT("ink_write") || Lower == TEXT("inkwrite") || Lower == TEXT("ink_dissolve"))
	{
		return ETextEffect::InkWrite;
	}
	if (Lower == TEXT("crystal_refract") || Lower == TEXT("glowpulse") || Lower == TEXT("glow_pulse") || Lower == TEXT("fade_shimmer"))
	{
		return ETextEffect::GlowPulse;
	}
	return ETextEffect::FadeIn;
}

FColor UButterflyStorySubsystem::ParseHexColorOrDefault(const FString& HexStr, const FColor& DefaultColor)
{
	FString Trimmed = HexStr;
	Trimmed.TrimStartAndEndInline();
	if (Trimmed.StartsWith(TEXT("#")))
	{
		Trimmed.RightChopInline(1);
	}
	if (Trimmed.Len() == 6 || Trimmed.Len() == 8)
	{
		FColor Parsed = FColor::FromHex(Trimmed);
		if (Trimmed.Len() == 6)
		{
			Parsed.A = 255;
		}
		return Parsed;
	}
	return DefaultColor;
}

UFont* UButterflyStorySubsystem::ResolveFontByName(FName FontName)
{
	if (FontName.IsNone())
	{
		return nullptr;
	}

	if (const TObjectPtr<UFont>* Found = CachedFonts.Find(FontName))
	{
		return Found->Get();
	}

	const FString NameStr = FontName.ToString();
	const TArray<FString> CandidateAssetPaths = {
		FString::Printf(TEXT("/Game/StoryText/Fonts/%s.%s"), *NameStr, *NameStr),
		FString::Printf(TEXT("/Game/Fonts/%s.%s"), *NameStr, *NameStr)
	};

	for (const FString& AssetPath : CandidateAssetPaths)
	{
		if (FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(AssetPath)))
		{
			if (UFont* LoadedFont = Cast<UFont>(StaticLoadObject(UFont::StaticClass(), nullptr, *AssetPath)))
			{
				CachedFonts.Add(FontName, LoadedFont);
				return LoadedFont;
			}
		}
	}

	CachedFonts.Add(FontName, nullptr);
	return nullptr;
}

FName UButterflyStorySubsystem::DetectWorldSceneId(const UWorld& InWorld) const
{
	FString MapName = InWorld.GetMapName();
	if (!InWorld.StreamingLevelsPrefix.IsEmpty())
	{
		MapName.RemoveFromStart(InWorld.StreamingLevelsPrefix);
	}
	return FButterflyTypography::NormalizeToStorySceneId(MapName);
}

void UButterflyStorySubsystem::CheckProximityTriggers()
{
	const AButterflyPawn* Pawn = TrackedPawn.Get();
	if (!Pawn)
	{
		return;
	}

	const FVector PawnLocation = Pawn->GetActorLocation();

	for (const FStoryTextEntry& Entry : StoryEntries)
	{
		if (!DoesEntryMatchActiveScene(Entry))
		{
			continue;
		}

		const FName EffectiveId = Entry.EntryId.IsNone()
			? FName(*Entry.DisplayText.ToString())
			: Entry.EntryId;

		if (TriggeredIds.Contains(EffectiveId))
		{
			continue;
		}

		const float DistSq = FVector::DistSquared(PawnLocation, Entry.TriggerLocation);
		if (DistSq <= FMath::Square(Entry.TriggerRadius))
		{
			TriggeredIds.Add(EffectiveId);
			NotifyHudEcho(Entry);
			break;
		}
	}
}

void UButterflyStorySubsystem::NotifyHudEcho(const FStoryTextEntry& Entry) const
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}

	if (AButterflyPlayerController* ButterflyPC = Cast<AButterflyPlayerController>(
		UGameplayStatics::GetPlayerController(World, 0)))
	{
		const float EchoSeconds = Entry.FadeInDuration + Entry.LingerDuration + 0.6f;
		ButterflyPC->NotifyStoryVerseTriggered(
			Entry.DisplayText,
			Entry.SubtitleText,
			FLinearColor::FromSRGBColor(Entry.TextColor),
			EchoSeconds);
	}
}

void UButterflyStorySubsystem::CleanUpFinishedActors()
{
	ActiveTextActors.RemoveAll([](const TWeakObjectPtr<AButterflyStoryTextActor>& WeakActor)
	{
		const AButterflyStoryTextActor* Actor = WeakActor.Get();
		return !Actor || !Actor->IsTextVisible();
	});
}
