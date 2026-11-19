#include "ButterflyStoryTextActor.h"

#include "Blueprint/WidgetTree.h"
#include "ButterflyTypography.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/Border.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SizeBox.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WidgetComponent.h"
#include "Engine/Font.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateColor.h"
#include "Styling/SlateTypes.h"
#include "UObject/ConstructorHelpers.h"

namespace ButterflyScrollConstants
{
	static constexpr float DefaultWorldSizeRef = 48.0f;
	static constexpr float DefaultWidgetWorldScale = 0.26f;
	static constexpr float BaseAuraLightCandelas = 175.0f;
	static constexpr float MaxAuraLightCandelas = 220.0f;

	static FSlateBrush MakeRoundedScrollBrush(
		const FLinearColor& Fill,
		const FLinearColor& Trim,
		float CornerRadius,
		float OutlineWidth)
	{
		FSlateBrush Brush;
		Brush.DrawAs = ESlateBrushDrawType::RoundedBox;
		Brush.TintColor = FSlateColor(Fill);
		Brush.OutlineSettings = FSlateBrushOutlineSettings(CornerRadius, FSlateColor(Trim), OutlineWidth);
		return Brush;
	}
}

// ===========================================================================
// UButterflyStoryScrollWidget
// ===========================================================================

TSharedRef<SWidget> UButterflyStoryScrollWidget::RebuildWidget()
{
	EnsureScrollTreeBuilt();
	return Super::RebuildWidget();
}

void UButterflyStoryScrollWidget::EnsureScrollTreeBuilt()
{
	if (!WidgetTree || WidgetTree->RootWidget)
	{
		return;
	}

	UOverlay* Root = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("ScrollRootOverlay"));
	WidgetTree->RootWidget = Root;

	ScrollPlaqueBorder = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("ScrollPlaqueBorder"));
	UHorizontalBox* ScrollRow = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(), TEXT("ScrollRow"));
	SealSizeBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("SealSizeBox"));
	SealStampBorder = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("SealStampBorder"));
	SealStampLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("SealStampLabel"));
	UVerticalBox* VerseColumn = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("VerseColumn"));
	MainVerseLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("MainVerseLabel"));
	USizeBox* DividerSizeBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("ScrollDividerSize"));
	HairlineDivider = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("ScrollHairlineDivider"));
	SubtitleNoteLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("SubtitleNoteLabel"));

	if (UOverlaySlot* PlaqueSlot = Root->AddChildToOverlay(ScrollPlaqueBorder))
	{
		PlaqueSlot->SetHorizontalAlignment(HAlign_Center);
		PlaqueSlot->SetVerticalAlignment(VAlign_Center);
	}

	ScrollPlaqueBorder->SetBrushColor(FLinearColor::White);
	ScrollPlaqueBorder->SetBrush(ButterflyScrollConstants::MakeRoundedScrollBrush(
		FLinearColor(0.005f, 0.008f, 0.016f, 0.88f),
		FLinearColor(0.96f, 0.82f, 0.44f, 0.90f),
		24.0f,
		2.0f));
	ScrollPlaqueBorder->SetPadding(FMargin(38.0f, 22.0f, 44.0f, 22.0f));
	ScrollPlaqueBorder->SetContent(ScrollRow);

	// Left: Cinnabar-red gold-rimmed square seal stamp (朱砂方印)
	SealSizeBox->SetWidthOverride(88.0f);
	SealSizeBox->SetHeightOverride(88.0f);
	SealSizeBox->SetContent(SealStampBorder);

	SealStampBorder->SetBrushColor(FLinearColor::White);
	SealStampBorder->SetBrush(ButterflyScrollConstants::MakeRoundedScrollBrush(
		FLinearColor(0.56f, 0.055f, 0.045f, 0.92f),
		FLinearColor(0.98f, 0.82f, 0.44f, 0.90f),
		10.0f,
		2.0f));
	SealStampBorder->SetPadding(FMargin(6.0f, 6.0f));
	SealStampBorder->SetHorizontalAlignment(HAlign_Center);
	SealStampBorder->SetVerticalAlignment(VAlign_Center);
	SealStampBorder->SetContent(SealStampLabel);

	SealStampLabel->SetFont(FButterflyTypography::MakeSealFont(34.0f, 18, 1));
	SealStampLabel->SetColorAndOpacity(FSlateColor(FLinearColor(1.0f, 0.94f, 0.78f, 0.98f)));
	SealStampLabel->SetJustification(ETextJustify::Center);
	SealStampLabel->SetText(FText::FromString(TEXT("梦蝶")));

	if (UHorizontalBoxSlot* SealSlot = ScrollRow->AddChildToHorizontalBox(SealSizeBox))
	{
		SealSlot->SetVerticalAlignment(VAlign_Center);
		SealSlot->SetPadding(FMargin(0.0f, 0.0f, 28.0f, 0.0f));
	}

	// Center/Right: Brush calligraphy verse + gold hairline + classical poetic subtitle
	MainVerseLabel->SetFont(FButterflyTypography::MakeBrushFont(66.0f, 92, 3));
	MainVerseLabel->SetColorAndOpacity(FSlateColor(FLinearColor(1.0f, 0.88f, 0.50f, 1.0f)));
	MainVerseLabel->SetShadowOffset(FVector2D(0.0f, 3.0f));
	MainVerseLabel->SetShadowColorAndOpacity(FLinearColor(0.0f, 0.0f, 0.0f, 0.82f));
	MainVerseLabel->SetJustification(ETextJustify::Center);

	DividerSizeBox->SetHeightOverride(1.6f);
	HairlineDivider->SetBrushColor(FLinearColor(0.94f, 0.78f, 0.42f, 0.48f));
	DividerSizeBox->SetContent(HairlineDivider);

	SubtitleNoteLabel->SetFont(FButterflyTypography::MakeBrushFont(22.0f, 65, 2, FLinearColor(0.02f, 0.03f, 0.06f, 0.95f)));
	SubtitleNoteLabel->SetColorAndOpacity(FSlateColor(FLinearColor(0.96f, 0.92f, 0.82f, 0.98f)));
	SubtitleNoteLabel->SetShadowOffset(FVector2D(0.0f, 1.5f));
	SubtitleNoteLabel->SetShadowColorAndOpacity(FLinearColor(0.0f, 0.0f, 0.0f, 0.85f));
	SubtitleNoteLabel->SetJustification(ETextJustify::Center);

	if (UVerticalBoxSlot* MainSlot = VerseColumn->AddChildToVerticalBox(MainVerseLabel))
	{
		MainSlot->SetHorizontalAlignment(HAlign_Center);
		MainSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 6.0f));
	}
	if (UVerticalBoxSlot* DivSlot = VerseColumn->AddChildToVerticalBox(DividerSizeBox))
	{
		DivSlot->SetHorizontalAlignment(HAlign_Fill);
		DivSlot->SetPadding(FMargin(18.0f, 2.0f, 18.0f, 6.0f));
	}
	if (UVerticalBoxSlot* SubSlot = VerseColumn->AddChildToVerticalBox(SubtitleNoteLabel))
	{
		SubSlot->SetHorizontalAlignment(HAlign_Center);
	}

	if (UHorizontalBoxSlot* ColSlot = ScrollRow->AddChildToHorizontalBox(VerseColumn))
	{
		ColSlot->SetVerticalAlignment(VAlign_Center);
	}
}

void UButterflyStoryScrollWidget::ConfigureScrollContent(
	const FText& InVerseText,
	const FText& InSubtitleText,
	const FText& InSealText,
	const FLinearColor& InVerseColor,
	const FLinearColor& InGlowAccent,
	UFont* OptionalCustomFont)
{
	EnsureScrollTreeBuilt();
	if (ScrollPlaqueBorder)
	{
		const FLinearColor TrimColor = FLinearColor::LerpUsingHSV(
			FLinearColor(0.95f, 0.79f, 0.42f, 0.78f),
			FLinearColor(InGlowAccent.R, InGlowAccent.G, InGlowAccent.B, 0.82f),
			0.42f);
		ScrollPlaqueBorder->SetBrush(ButterflyScrollConstants::MakeRoundedScrollBrush(
			FLinearColor(0.005f, 0.008f, 0.016f, 0.88f),
			TrimColor,
			24.0f,
			2.0f));
	}

	if (HairlineDivider)
	{
		HairlineDivider->SetBrushColor(FLinearColor(InGlowAccent.R, InGlowAccent.G, InGlowAccent.B, 0.50f));
	}

	if (SealStampLabel)
	{
		const FText EffectiveSeal = InSealText.IsEmpty()
			? FText::FromString(TEXT("梦蝶"))
			: InSealText;
		SealStampLabel->SetText(EffectiveSeal);
	}

	if (MainVerseLabel)
	{
		if (IsValid(OptionalCustomFont))
		{
			FFontOutlineSettings Outline(3, FLinearColor(0.015f, 0.012f, 0.032f, 0.90f));
			Outline.bSeparateFillAlpha = true;
			FSlateFontInfo CustomInfo(OptionalCustomFont, 66.0f, NAME_None, Outline);
			CustomInfo.LetterSpacing = 92;
			MainVerseLabel->SetFont(CustomInfo);
		}
		else
		{
			MainVerseLabel->SetFont(FButterflyTypography::MakeBrushFont(66.0f, 92, 3));
		}
		MainVerseLabel->SetColorAndOpacity(FSlateColor(InVerseColor));
		MainVerseLabel->SetText(InVerseText);
	}

	if (SubtitleNoteLabel)
	{
		if (InSubtitleText.IsEmpty())
		{
			SubtitleNoteLabel->SetVisibility(ESlateVisibility::Collapsed);
		}
		else
		{
			SubtitleNoteLabel->SetVisibility(ESlateVisibility::HitTestInvisible);
			SubtitleNoteLabel->SetText(FText::FromString(
				FString::Printf(TEXT("—  %s  —"), *InSubtitleText.ToString())));
		}
	}
}

void UButterflyStoryScrollWidget::SetDisplayedVerseText(const FText& PartialOrFullVerse)
{
	if (MainVerseLabel)
	{
		MainVerseLabel->SetText(PartialOrFullVerse);
	}
}

void UButterflyStoryScrollWidget::SetSealScaleAndOpacity(float SealScale, float SealAlpha)
{
	if (SealSizeBox)
	{
		SealSizeBox->SetRenderScale(FVector2D(SealScale, SealScale));
		SealSizeBox->SetRenderOpacity(FMath::Clamp(SealAlpha, 0.0f, 1.0f));
	}
}

// ===========================================================================
// AButterflyStoryTextActor
// ===========================================================================

AButterflyStoryTextActor::AButterflyStoryTextActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	CalligraphyWidgetComp = CreateDefaultSubobject<UWidgetComponent>(TEXT("CalligraphyWidgetComp"));
	CalligraphyWidgetComp->SetupAttachment(SceneRoot);
	CalligraphyWidgetComp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	CalligraphyWidgetComp->SetCastShadow(false);
	CalligraphyWidgetComp->SetWidgetSpace(EWidgetSpace::World);
	CalligraphyWidgetComp->SetBlendMode(EWidgetBlendMode::Transparent);
	CalligraphyWidgetComp->SetTwoSided(true);
	CalligraphyWidgetComp->SetDrawAtDesiredSize(false);
	CalligraphyWidgetComp->SetDrawSize(FVector2D(2200.0f, 480.0f));
	CalligraphyWidgetComp->SetPivot(FVector2D(0.5f, 0.5f));
	CalligraphyWidgetComp->SetBackgroundColor(FLinearColor(0.0f, 0.0f, 0.0f, 0.0f));
	CalligraphyWidgetComp->SetTickWhenOffscreen(true);
	CalligraphyWidgetComp->SetWidgetClass(UButterflyStoryScrollWidget::StaticClass());
	CalligraphyWidgetComp->SetRelativeScale3D(FVector(ButterflyScrollConstants::DefaultWidgetWorldScale));

	static ConstructorHelpers::FObjectFinder<UStaticMesh> ScaleBladeAsset(
		TEXT("/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"));

	for (int32 MoteIdx = 0; MoteIdx < NumOrbitScaleMotes; ++MoteIdx)
	{
		const FName MoteName(*FString::Printf(TEXT("ScrollScaleMote_%d"), MoteIdx));
		UStaticMeshComponent* MoteComp = CreateDefaultSubobject<UStaticMeshComponent>(MoteName);
		MoteComp->SetupAttachment(SceneRoot);
		MoteComp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		MoteComp->SetCastShadow(false);
		MoteComp->SetRelativeScale3D(FVector(0.18f));
		if (ScaleBladeAsset.Succeeded())
		{
			MoteComp->SetStaticMesh(ScaleBladeAsset.Object);
		}
		OrbitScaleMotes.Add(MoteComp);
	}

	CalligraphyGlowLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("CalligraphyGlowLight"));
	CalligraphyGlowLight->SetupAttachment(SceneRoot);
	CalligraphyGlowLight->SetIntensityUnits(ELightUnits::Candelas);
	CalligraphyGlowLight->SetIntensity(0.0f);
	CalligraphyGlowLight->SetAttenuationRadius(640.0f);
	CalligraphyGlowLight->SetLightColor(FLinearColor::FromSRGBColor(GlowColor));
	CalligraphyGlowLight->SetCastShadows(false);
}

void AButterflyStoryTextActor::BeginPlay()
{
	Super::BeginPlay();

	BaseLocation = GetActorLocation();
	bBaseLocationInitialized = true;

	if (!DisplayText.IsEmpty())
	{
		ActivateScroll(DisplayText, SubtitleText, SealText, TextColor, GlowColor, TextEffect);
	}
}

FColor AButterflyStoryTextActor::GetPresetColor(EStoryTextColorPreset Preset)
{
	switch (Preset)
	{
	case EStoryTextColorPreset::ImperialGold:
		return FColor(255, 215, 80, 255);
	case EStoryTextColorPreset::MoonlitWhite:
		return FColor(242, 246, 255, 255);
	case EStoryTextColorPreset::CelestialJade:
		return FColor(110, 238, 198, 255);
	case EStoryTextColorPreset::NebulaViolet:
		return FColor(202, 158, 255, 255);
	case EStoryTextColorPreset::SakuraBlossom:
		return FColor(255, 183, 197, 255);
	default:
		return FColor(255, 215, 80, 255);
	}
}

void AButterflyStoryTextActor::ApplyColorPreset(EStoryTextColorPreset Preset)
{
	TextColor = GetPresetColor(Preset);
	GlowColor = TextColor;
	RefreshScrollVisuals();
}

void AButterflyStoryTextActor::SetCalligraphyWorldSize(float NewWorldSize)
{
	WorldSize = FMath::Max(8.0f, NewWorldSize);
	if (CalligraphyWidgetComp)
	{
		CalligraphyWidgetComp->SetRelativeScale3D(FVector(ComputeBaseWidgetWorldScale()));
	}
}

float AButterflyStoryTextActor::ComputeBaseWidgetWorldScale() const
{
	return FMath::Clamp(
		(WorldSize / ButterflyScrollConstants::DefaultWorldSizeRef) * ButterflyScrollConstants::DefaultWidgetWorldScale,
		0.08f,
		0.75f);
}

UButterflyStoryScrollWidget* AButterflyStoryTextActor::GetScrollWidget() const
{
	if (!CalligraphyWidgetComp || IsRunningCommandlet())
	{
		return nullptr;
	}
	if (!CalligraphyWidgetComp->GetUserWidgetObject())
	{
		CalligraphyWidgetComp->InitWidget();
	}
	return Cast<UButterflyStoryScrollWidget>(CalligraphyWidgetComp->GetUserWidgetObject());
}

void AButterflyStoryTextActor::RefreshScrollVisuals()
{
	const FLinearColor LinearText = FLinearColor::FromSRGBColor(TextColor);
	const FLinearColor LinearGlow = FLinearColor::FromSRGBColor(GlowColor);

	if (UButterflyStoryScrollWidget* ScrollWidget = GetScrollWidget())
	{
		ScrollWidget->ConfigureScrollContent(
			DisplayText,
			SubtitleText,
			SealText,
			LinearText,
			LinearGlow,
			CustomFont);
	}

	if (CalligraphyWidgetComp)
	{
		CalligraphyWidgetComp->SetRelativeScale3D(FVector(ComputeBaseWidgetWorldScale()));
		CalligraphyWidgetComp->SetHiddenInGame(false);
		CalligraphyWidgetComp->SetVisibility(true);
		CalligraphyWidgetComp->RequestRenderUpdate();
	}

	if (CalligraphyGlowLight)
	{
		CalligraphyGlowLight->SetLightColor(LinearGlow);
	}
}

void AButterflyStoryTextActor::ActivateScroll(
	const FText& InVerseText,
	const FText& InSubtitleText,
	const FText& InSealText,
	FColor InTextColor,
	FColor InGlowColor,
	ETextEffect InEffect)
{
	if (!bBaseLocationInitialized)
	{
		BaseLocation = GetActorLocation();
		bBaseLocationInitialized = true;
	}

	DisplayText = InVerseText;
	SubtitleText = InSubtitleText;
	SealText = InSealText;
	TextColor = InTextColor;
	GlowColor = InGlowColor;
	TextEffect = InEffect;

	Phase = EPhase::FadingIn;
	PhaseElapsed = 0.0f;
	CurrentAlpha = 0.0f;
	LastRevealedChars = -1;
	bLastAppendedBrushSpark = false;
	bBillboardSnapPending = true;

	RefreshScrollVisuals();

	const bool bProgressiveBrush =
		(TextEffect == ETextEffect::InkWrite ||
		 TextEffect == ETextEffect::ParticleGather ||
		 TextEffect == ETextEffect::StarlightCoalesce);
	UpdateBrushStrokeReveal(bProgressiveBrush ? 0.0f : 1.0f, bProgressiveBrush);
	UpdateBillboard(0.0f);
	UpdateOrbitingScaleMotes();
	ApplyAlphaAndGlow(0.0f, 0.0f);
}

void AButterflyStoryTextActor::ActivateText(const FText& InText, FColor InColor, ETextEffect InEffect)
{
	ActivateScroll(InText, SubtitleText, SealText, InColor, GlowColor, InEffect);
}

void AButterflyStoryTextActor::DismissText()
{
	if (Phase == EPhase::FadingIn || Phase == EPhase::Lingering)
	{
		UpdateBrushStrokeReveal(1.0f, false);
		Phase = EPhase::FadingOut;
		PhaseElapsed = 0.0f;
	}
}

void AButterflyStoryTextActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (Phase == EPhase::Finished)
	{
		return;
	}

	ElapsedTime += DeltaSeconds;

	if (bFaceCamera)
	{
		UpdateBillboard(DeltaSeconds);
	}

	const float FloatOffsetZ = FMath::Sin(ElapsedTime * FloatSpeed) * FloatAmplitude;
	SetActorLocation(BaseLocation + FVector(0.0f, 0.0f, FloatOffsetZ));

	UpdateOrbitingScaleMotes();
	AdvancePhase(DeltaSeconds);
}

void AButterflyStoryTextActor::UpdateBillboard(float DeltaSeconds)
{
	const APlayerCameraManager* CameraManager = UGameplayStatics::GetPlayerCameraManager(this, 0);
	if (!CameraManager)
	{
		return;
	}

	const FVector ToCamera = CameraManager->GetCameraLocation() - GetActorLocation();
	if (ToCamera.IsNearlyZero())
	{
		return;
	}

	const FRotator LookRot = ToCamera.Rotation();
	const float SubtlePitch = FMath::Clamp(FRotator::NormalizeAxis(LookRot.Pitch) * 0.28f, -18.0f, 18.0f);
	const FRotator TargetRot(SubtlePitch, LookRot.Yaw, 0.0f);

	if (bBillboardSnapPending || DeltaSeconds <= 0.0f)
	{
		SetActorRotation(TargetRot);
		bBillboardSnapPending = false;
	}
	else
	{
		SetActorRotation(FMath::RInterpTo(GetActorRotation(), TargetRot, DeltaSeconds, 9.5f));
	}
}

void AButterflyStoryTextActor::UpdateOrbitingScaleMotes()
{
	const int32 NumMotes = OrbitScaleMotes.Num();
	if (NumMotes <= 0)
	{
		return;
	}

	const float ScaleRatio = ComputeBaseWidgetWorldScale() / ButterflyScrollConstants::DefaultWidgetWorldScale;
	const float GatherSpread = (Phase == EPhase::FadingIn &&
		(TextEffect == ETextEffect::ParticleGather || TextEffect == ETextEffect::StarlightCoalesce))
		? FMath::Lerp(1.85f, 1.0f, CurrentAlpha)
		: 1.0f;

	for (int32 Idx = 0; Idx < NumMotes; ++Idx)
	{
		UStaticMeshComponent* Mote = OrbitScaleMotes[Idx];
		if (!Mote)
		{
			continue;
		}

		const bool bVisible = IsValid(Mote->GetStaticMesh()) && (CurrentAlpha > 0.02f);
		Mote->SetHiddenInGame(!bVisible);
		if (!bVisible)
		{
			continue;
		}

		const float PhaseAngle = ElapsedTime * 1.65f + (static_cast<float>(Idx) / static_cast<float>(NumMotes)) * 2.0f * PI;
		const float RibbonWidthY = 305.0f * ScaleRatio * GatherSpread;
		const float RibbonHeightZ = 78.0f * ScaleRatio * GatherSpread;
		const float DepthWaveX = 28.0f * FMath::Sin(PhaseAngle * 2.0f);

		const FVector LocalPos(
			DepthWaveX,
			FMath::Cos(PhaseAngle) * RibbonWidthY,
			FMath::Sin(PhaseAngle) * RibbonHeightZ + 14.0f * FMath::Sin(PhaseAngle * 3.0f));
		Mote->SetRelativeLocation(LocalPos);

		const float ShimmerScale = (0.14f + 0.06f * (0.5f + 0.5f * FMath::Sin(ElapsedTime * 4.8f + static_cast<float>(Idx))))
			* CurrentAlpha * ScaleRatio;
		Mote->SetRelativeScale3D(FVector(ShimmerScale));
		Mote->SetRelativeRotation(FRotator(
			24.0f * FMath::Sin(PhaseAngle * 2.0f),
			FMath::RadiansToDegrees(PhaseAngle) + 90.0f,
			ElapsedTime * 110.0f * ((Idx % 2 == 0) ? 1.0f : -1.0f)));
	}
}

void AButterflyStoryTextActor::UpdateBrushStrokeReveal(float RevealProgress, bool bShowBrushSpark)
{
	const FString FullStr = DisplayText.ToString();
	const int32 TotalChars = FullStr.Len();
	if (TotalChars <= 0)
	{
		return;
	}

	const bool bCompleted = (RevealProgress >= 0.995f);
	const int32 TargetChars = bCompleted
		? TotalChars
		: FMath::Clamp(FMath::CeilToInt(RevealProgress * static_cast<float>(TotalChars)), 1, TotalChars);
	const bool bAppendSpark = bShowBrushSpark && !bCompleted;

	if (TargetChars == LastRevealedChars && bAppendSpark == bLastAppendedBrushSpark)
	{
		return;
	}

	LastRevealedChars = TargetChars;
	bLastAppendedBrushSpark = bAppendSpark;

	FString Built = (TargetChars >= TotalChars) ? FullStr : FullStr.Left(TargetChars);
	if (bAppendSpark)
	{
		Built += TEXT("、");
	}

	if (UButterflyStoryScrollWidget* ScrollWidget = GetScrollWidget())
	{
		ScrollWidget->SetDisplayedVerseText(FText::FromString(Built));
		if (CalligraphyWidgetComp)
		{
			CalligraphyWidgetComp->RequestRenderUpdate();
		}
	}
}

void AButterflyStoryTextActor::ApplyAlphaAndGlow(float Alpha, float LightCandelasRatio)
{
	CurrentAlpha = FMath::Clamp(Alpha, 0.0f, 1.0f);

	if (UButterflyStoryScrollWidget* ScrollWidget = GetScrollWidget())
	{
		ScrollWidget->SetRenderOpacity(CurrentAlpha);
	}

	if (CalligraphyWidgetComp)
	{
		CalligraphyWidgetComp->SetTintColorAndOpacity(FLinearColor(1.0f, 1.0f, 1.0f, CurrentAlpha));
		CalligraphyWidgetComp->RequestRenderUpdate();
	}

	if (CalligraphyGlowLight)
	{
		const float DesiredCd = FMath::Clamp(
			ButterflyScrollConstants::BaseAuraLightCandelas * CurrentAlpha * LightCandelasRatio,
			0.0f,
			ButterflyScrollConstants::MaxAuraLightCandelas);
		CalligraphyGlowLight->SetIntensity(DesiredCd);
	}
}

void AButterflyStoryTextActor::AdvancePhase(float DeltaSeconds)
{
	PhaseElapsed += DeltaSeconds;

	const float BaseWorldScale = ComputeBaseWidgetWorldScale();
	float ScaleFactor = 1.0f;
	float SealScale = 1.0f;
	float LightRatio = 1.0f;

	switch (Phase)
	{
	case EPhase::FadingIn:
	{
		const float EffectiveDuration = FMath::Max(FadeInDuration, 0.08f);
		const float RawProgress = FMath::Clamp(PhaseElapsed / EffectiveDuration, 0.0f, 1.0f);
		float Alpha = FMath::SmoothStep(0.0f, 1.0f, RawProgress);

		if (TextEffect == ETextEffect::InkWrite ||
			TextEffect == ETextEffect::ParticleGather ||
			TextEffect == ETextEffect::StarlightCoalesce)
		{
			Alpha = FMath::InterpEaseOut(0.0f, 1.0f, FMath::Min(1.0f, RawProgress * 1.45f), 2.2f);
			const float StrokeProgress = FMath::InterpEaseInOut(0.0f, 1.0f, RawProgress, 1.4f);
			UpdateBrushStrokeReveal(StrokeProgress, true);

			if (TextEffect == ETextEffect::ParticleGather || TextEffect == ETextEffect::StarlightCoalesce)
			{
				ScaleFactor = FMath::Lerp(1.28f, 1.0f, Alpha);
				LightRatio = FMath::Lerp(1.30f, 1.02f, Alpha);
			}
		}
		else if (TextEffect == ETextEffect::GoldenSeal)
		{
			// Stamp-impact overshoot bounce from above
			const float Ease = FMath::InterpEaseOut(0.0f, 1.0f, RawProgress, 3.2f);
			const float Overshoot = FMath::Sin(RawProgress * PI) * -0.05f;
			Alpha = Ease;
			ScaleFactor = FMath::Lerp(1.52f, 1.0f, Ease) + Overshoot;
			SealScale = FMath::Lerp(1.90f, 1.0f, Ease);
			LightRatio = FMath::Lerp(1.35f, 1.05f, Ease);
		}
		else if (TextEffect == ETextEffect::GlowPulse)
		{
			LightRatio = 1.08f + 0.18f * FMath::Sin(ElapsedTime * 4.2f);
		}

		if (UButterflyStoryScrollWidget* ScrollWidget = GetScrollWidget())
		{
			ScrollWidget->SetSealScaleAndOpacity(SealScale, Alpha);
		}
		ApplyAlphaAndGlow(Alpha, LightRatio);

		if (PhaseElapsed >= EffectiveDuration)
		{
			UpdateBrushStrokeReveal(1.0f, false);
			if (UButterflyStoryScrollWidget* ScrollWidget = GetScrollWidget())
			{
				ScrollWidget->SetSealScaleAndOpacity(1.0f, 1.0f);
			}
			ScaleFactor = 1.0f;
			ApplyAlphaAndGlow(1.0f, 1.0f);
			Phase = EPhase::Lingering;
			PhaseElapsed = 0.0f;
		}
		break;
	}
	case EPhase::Lingering:
	{
		const float BreathWave = 0.5f + 0.5f * FMath::Sin(ElapsedTime * 3.2f);
		float Alpha = 1.0f;
		if (TextEffect == ETextEffect::GlowPulse)
		{
			Alpha = FMath::Lerp(0.86f, 1.0f, BreathWave);
			LightRatio = FMath::Lerp(0.88f, 1.26f, BreathWave);
			ScaleFactor = FMath::Lerp(0.992f, 1.018f, BreathWave);
		}
		else
		{
			LightRatio = FMath::Lerp(0.92f, 1.15f, BreathWave);
		}

		ApplyAlphaAndGlow(Alpha, LightRatio);

		if (PhaseElapsed >= LingerDuration)
		{
			Phase = EPhase::FadingOut;
			PhaseElapsed = 0.0f;
		}
		break;
	}
	case EPhase::FadingOut:
	{
		const float EffectiveDuration = FMath::Max(FadeOutDuration, 0.08f);
		const float RawProgress = FMath::Clamp(PhaseElapsed / EffectiveDuration, 0.0f, 1.0f);
		const float Alpha = 1.0f - FMath::SmoothStep(0.0f, 1.0f, RawProgress);
		ScaleFactor = FMath::Lerp(1.0f, 1.06f, RawProgress);
		ApplyAlphaAndGlow(Alpha, Alpha);

		if (PhaseElapsed >= EffectiveDuration)
		{
			Phase = EPhase::Finished;
			if (CalligraphyWidgetComp)
			{
				CalligraphyWidgetComp->SetHiddenInGame(true);
			}
			for (UStaticMeshComponent* Mote : OrbitScaleMotes)
			{
				if (Mote)
				{
					Mote->SetHiddenInGame(true);
				}
			}
			if (CalligraphyGlowLight)
			{
				CalligraphyGlowLight->SetIntensity(0.0f);
			}
			if (bAutoDestroy)
			{
				Destroy();
			}
			return;
		}
		break;
	}
	default:
		break;
	}

	if (CalligraphyWidgetComp)
	{
		CalligraphyWidgetComp->SetRelativeScale3D(FVector(BaseWorldScale * ScaleFactor));
	}
}
