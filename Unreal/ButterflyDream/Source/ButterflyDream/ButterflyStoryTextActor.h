#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "GameFramework/Actor.h"
#include "ButterflyStoryTextActor.generated.h"

class UBorder;
class UFont;
class UPointLightComponent;
class USceneComponent;
class USizeBox;
class UStaticMeshComponent;
class UTextBlock;
class UWidgetComponent;

/** Visual entrance & idle effect styles for 3D floating calligraphy scrolls. */
UENUM(BlueprintType)
enum class ETextEffect : uint8
{
	FadeIn              UMETA(DisplayName = "Fade In"),
	InkWrite            UMETA(DisplayName = "Ink Write"),
	ParticleGather      UMETA(DisplayName = "Particle Gather / Petal Gather"),
	GlowPulse           UMETA(DisplayName = "Glow Pulse / Crystal Shimmer"),
	GoldenSeal          UMETA(DisplayName = "Golden Seal Stamp"),
	StarlightCoalesce   UMETA(DisplayName = "Starlight Coalesce")
};

/** Preset calligraphy colour palette for Zhuangzi Butterfly Dream realms. */
UENUM(BlueprintType)
enum class EStoryTextColorPreset : uint8
{
	ImperialGold    UMETA(DisplayName = "Imperial Gold (金色)"),
	MoonlitWhite    UMETA(DisplayName = "Moonlit White (白色)"),
	CelestialJade   UMETA(DisplayName = "Celestial Jade (翠色)"),
	NebulaViolet    UMETA(DisplayName = "Nebula Violet (紫色)"),
	SakuraBlossom   UMETA(DisplayName = "Sakura Blossom (绯樱)")
};

/**
 * Translucent obsidian-and-gold xianxia calligraphy scroll widget hosted inside a 3D UWidgetComponent.
 * Features a cinnabar running-script seal stamp on the left (ZhiMangXing), bold brush calligraphy
 * in the centre (MaShanZheng), and a poetic annotation subtitle underneath (ZCOOLXiaoWei).
 */
UCLASS()
class BUTTERFLYDREAM_API UButterflyStoryScrollWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void ConfigureScrollContent(
		const FText& InVerseText,
		const FText& InSubtitleText,
		const FText& InSealText,
		const FLinearColor& InVerseColor,
		const FLinearColor& InGlowAccent,
		UFont* OptionalCustomFont = nullptr);

	void SetDisplayedVerseText(const FText& PartialOrFullVerse);
	void SetSealScaleAndOpacity(float SealScale, float SealAlpha);

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	void EnsureScrollTreeBuilt();
	UPROPERTY(Transient)
	TObjectPtr<UBorder> ScrollPlaqueBorder;

	UPROPERTY(Transient)
	TObjectPtr<USizeBox> SealSizeBox;

	UPROPERTY(Transient)
	TObjectPtr<UBorder> SealStampBorder;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> SealStampLabel;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> MainVerseLabel;

	UPROPERTY(Transient)
	TObjectPtr<UBorder> HairlineDivider;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> SubtitleNoteLabel;
};

/**
 * 3D floating xianxia calligraphy scroll actor rendered in world space via UWidgetComponent,
 * accompanied by 10 orbiting Dream_Scale_Blade spirit motes and a breathing Candelas aura light.
 */
UCLASS()
class BUTTERFLYDREAM_API AButterflyStoryTextActor : public AActor
{
	GENERATED_BODY()

public:
	AButterflyStoryTextActor();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	// ---- Configuration ----

	/** Primary poetic calligraphy line (Chinese / Unicode). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FText DisplayText;

	/** Poetic subtitle / narrative annotation displayed beneath the main brush verse. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FText SubtitleText;

	/** Two-character cinnabar seal stamp inscription (e.g. 梦蝶, 太虚, 齐物, 破幻, 物化). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FText SealText;

	/** Primary brush calligraphy colour. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FColor TextColor = FColor(255, 215, 80, 255);

	/** Secondary aura light & scroll trim accent colour. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	FColor GlowColor = FColor(255, 244, 196, 255);

	/** Controls overall 3D scroll world scale (default 48.0 -> 0.26 world widget scale). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "8.0"))
	float WorldSize = 48.0f;

	/** Optional custom UFont asset override (defaults to MaShanZheng open-source brush calligraphy). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	TObjectPtr<UFont> CustomFont;

	/** Entrance and idle animation style. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	ETextEffect TextEffect = ETextEffect::InkWrite;

	/** Entrance animation duration in seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "0.05"))
	float FadeInDuration = 2.0f;

	/** Full-readability hold duration in seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "0.0"))
	float LingerDuration = 5.0f;

	/** Smooth fade-out duration in seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText", meta = (ClampMin = "0.05"))
	float FadeOutDuration = 1.5f;

	/** Automatically destroy this actor after fade-out completes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	bool bAutoDestroy = true;

	/** Smoothly face the active player camera (Billboard). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText")
	bool bFaceCamera = true;

	/** Gentle vertical levitation amplitude in centimetres. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText|Motion")
	float FloatAmplitude = 9.0f;

	/** Gentle vertical levitation angular speed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "StoryText|Motion")
	float FloatSpeed = 1.45f;

	// ---- Blueprint API ----

	/** Activate with full scroll metadata (main verse, poetic annotation, seal stamp, colours & effect). */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void ActivateScroll(
		const FText& InVerseText,
		const FText& InSubtitleText,
		const FText& InSealText,
		FColor InTextColor,
		FColor InGlowColor,
		ETextEffect InEffect);

	/** Activate with primary verse, colour and effect. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void ActivateText(const FText& InText, FColor InColor, ETextEffect InEffect);

	/** Apply a named xianxia colour preset. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void ApplyColorPreset(EStoryTextColorPreset Preset);

	/** Adjust world-space calligraphy scale at runtime. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void SetCalligraphyWorldSize(float NewWorldSize);

	/** Skip directly to smooth fade-out. */
	UFUNCTION(BlueprintCallable, Category = "StoryText")
	void DismissText();

	/** True while the scroll is fading in, lingering, or fading out. */
	UFUNCTION(BlueprintPure, Category = "StoryText")
	bool IsTextVisible() const { return Phase != EPhase::Finished; }

	/** Convert a preset enum into an FColor. */
	UFUNCTION(BlueprintPure, Category = "StoryText")
	static FColor GetPresetColor(EStoryTextColorPreset Preset);

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UWidgetComponent> CalligraphyWidgetComp;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TArray<TObjectPtr<UStaticMeshComponent>> OrbitScaleMotes;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> CalligraphyGlowLight;

private:
	static constexpr int32 NumOrbitScaleMotes = 10;

	enum class EPhase : uint8
	{
		FadingIn,
		Lingering,
		FadingOut,
		Finished
	};

	EPhase Phase = EPhase::FadingIn;
	float PhaseElapsed = 0.0f;
	float CurrentAlpha = 0.0f;
	float ElapsedTime = 0.0f;
	int32 LastRevealedChars = -1;
	bool bLastAppendedBrushSpark = false;
	FVector BaseLocation = FVector::ZeroVector;
	bool bBaseLocationInitialized = false;
	bool bBillboardSnapPending = true;

	UButterflyStoryScrollWidget* GetScrollWidget() const;
	float ComputeBaseWidgetWorldScale() const;
	void RefreshScrollVisuals();
	void UpdateBrushStrokeReveal(float RevealProgress, bool bShowBrushSpark);
	void UpdateBillboard(float DeltaSeconds);
	void UpdateOrbitingScaleMotes();
	void ApplyAlphaAndGlow(float Alpha, float LightCandelasRatio = 1.0f);
	void AdvancePhase(float DeltaSeconds);
};
