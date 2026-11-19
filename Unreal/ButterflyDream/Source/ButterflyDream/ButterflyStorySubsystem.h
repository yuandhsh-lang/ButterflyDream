#pragma once

#include "CoreMinimal.h"
#include "Engine/DataTable.h"
#include "Subsystems/WorldSubsystem.h"
#include "ButterflyStoryTextActor.h"
#include "ButterflyStorySubsystem.generated.h"

class AButterflyPawn;
class AButterflyStoryTextActor;
class UDataTable;
class UFont;

/**
 * DataTable & JSON row definition describing a HUD verse milestone
 * along the butterfly's flight path across the four realms.
 */
USTRUCT(BlueprintType)
struct BUTTERFLYDREAM_API FStoryTextEntry : public FTableRowBase
{
	GENERATED_BODY()

	/** Unique entry identifier (prevents duplicate triggers). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FName EntryId;

	/** Canonical scene ID (Lux_StarSeaDream, InkCloudSea, CrystalFantasy, or ChaosUnity). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FName SceneId;

	/** Optional actor name/tag for explicit waypoint override in a level. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FName WaypointTag;

	/** Optional milestone distance in metres from story_config.json. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	float TriggerDistanceMeters = -1.0f;

	/** World-space trigger centre in centimetres. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FVector TriggerLocation = FVector::ZeroVector;

	/** Proximity trigger radius in centimetres. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "10.0"))
	float TriggerRadius = 460.0f;

	/** Legacy editor data; the current HUD-only presentation does not spawn world text. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FVector TextSpawnLocation = FVector::ZeroVector;

	/** Legacy world-text offset, not used for the current HUD presentation. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FVector SpawnOffset = FVector(0.0f, 0.0f, 195.0f);

	/** Primary poetic brush calligraphy verse. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FText DisplayText;

	/** Poetic subtitle / narrative annotation shown beneath the main verse and echoed on the HUD. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FText SubtitleText;

	/** Two-character cinnabar seal stamp text (e.g. 梦蝶, 太虚, 齐物, 破幻, 物化). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FText SealText;

	/** Optional custom UFont asset name. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FName FontName;

	/** Primary brush calligraphy colour. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FColor TextColor = FColor(255, 215, 80, 255);

	/** Secondary halo / aura light colour. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FColor GlowColor = FColor(255, 244, 196, 255);

	/** Legacy world-text display scale, not used for the current HUD presentation. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "8.0"))
	float WorldSize = 48.0f;

	/** Entrance / idle animation effect. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	ETextEffect TextEffect = ETextEffect::InkWrite;

	/** Entrance duration (seconds). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "0.05"))
	float FadeInDuration = 2.0f;

	/** Full-opacity hold duration (seconds). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "0.0"))
	float LingerDuration = 5.0f;

	/** Smooth fade-out duration (seconds). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "0.05"))
	float FadeOutDuration = 1.5f;

	/** True if TriggerLocation / TextSpawnLocation were explicitly authored in world coordinates. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	bool bHasExplicitWorldLocation = true;
};

/**
 * Tickable world subsystem presenting short HUD verse echoes across the four realms.
 * Auto-loads Content/StoryText/story_config.json, maps map names to canonical scene IDs,
 * lays out milestone triggers between PlayerStart and DreamGate, and avoids blocking the flight view.
 */
UCLASS()
class BUTTERFLYDREAM_API UButterflyStorySubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual TStatId GetStatId() const override;

	// ---- Public Blueprint API ----

	/** Register the playable butterfly pawn as the proximity tracking target. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void RegisterPawn(AButterflyPawn* InPawn);

	/** Set the active scene ID filter (supports map names and JSON scene_ids). */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void SetActiveSceneId(FName InSceneId);

	/** Get the normalized active scene ID filter. */
	UFUNCTION(BlueprintPure, Category = "StoryText")
	FName GetActiveSceneId() const { return ActiveSceneId; }

	/** Add a story entry at runtime. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void AddStoryEntry(const FStoryTextEntry& Entry);

	/** Load story entries from JSON (supports story_config.json and flat arrays). */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	bool LoadEntriesFromJsonFile(const FString& FilePath);

	/** Load story entries from a DataTable using FStoryTextEntry rows. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	int32 LoadEntriesFromDataTable(const UDataTable* DataTable);

	/** Locate and load the default story_config.json. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	bool AutoLoadDefaultStoryConfig();

	/** Compute staggered aerial corridor triggers between PlayerStart and DreamGate. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void ResolveWaypointsForCurrentWorld();

	/** Clear triggered history so entries in this scene can replay. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void ResetTriggeredState();

	/** Destroy active scroll actors and clear all loaded entries. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void ResetAllEntries();

	/** Total number of loaded entries across all scenes. */
	UFUNCTION(BlueprintPure, Category = "StoryText")
	int32 GetEntryCount() const { return StoryEntries.Num(); }

	/** True if a specific EntryId has already been triggered in this world. */
	UFUNCTION(BlueprintPure, Category = "StoryText")
	bool IsEntryTriggered(FName EntryId) const { return TriggeredIds.Contains(EntryId); }

private:
	UPROPERTY()
	TArray<FStoryTextEntry> StoryEntries;

	UPROPERTY()
	TWeakObjectPtr<AButterflyPawn> TrackedPawn;

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UFont>> CachedFonts;

	UPROPERTY()
	TArray<TWeakObjectPtr<AButterflyStoryTextActor>> ActiveTextActors;

	TSet<FName> TriggeredIds;
	FName ActiveSceneId;
	float WorldElapsedSeconds = 0.0f;
	bool bWaypointsResolved = false;
	bool bOpeningVerseAutoTriggered = false;

	static ETextEffect ParseTextEffectString(const FString& EffectStr);
	static FColor ParseHexColorOrDefault(const FString& HexStr, const FColor& DefaultColor);
	UFont* ResolveFontByName(FName FontName);
	FName DetectWorldSceneId(const UWorld& InWorld) const;
	bool DoesEntryMatchActiveScene(const FStoryTextEntry& Entry) const;
	void TryAutoTriggerOpeningVerse();
	void CheckProximityTriggers();
	void NotifyHudEcho(const FStoryTextEntry& Entry) const;
	void CleanUpFinishedActors();
};
