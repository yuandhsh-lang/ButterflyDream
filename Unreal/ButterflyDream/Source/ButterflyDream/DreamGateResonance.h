#pragma once

#include "CoreMinimal.h"
#include "DreamGateResonance.generated.h"

UENUM(BlueprintType)
enum class EDreamGateState : uint8
{
	Idle,
	Resonating,
	Opening,
	Ready,
	Traversing,
	Loading,
	Error
};

struct FDreamGateResonance
{
	static constexpr int32 TunnelRingCount = 10;
	static constexpr float DefaultChargeSeconds = 2.0f;
	static constexpr float DefaultOpeningSeconds = 0.8f;
	static constexpr float SafeOpenAlpha = 0.90f;
	static constexpr float BackoutY = -20.0f;

	EDreamGateState State = EDreamGateState::Idle;
	float Charge = 0.0f;
	float OpenAlpha = 0.0f;
	float ChargeSeconds = DefaultChargeSeconds;
	float OpeningSeconds = DefaultOpeningSeconds;
	FString LastFailure;

	static float GetTunnelRingSpacing(bool bRotary)
	{
		return bRotary ? 13.0f : 30.0f;
	}

	static float GetTunnelExitDistance(bool bRotary)
	{
		return GetTunnelRingSpacing(bRotary) * static_cast<float>(TunnelRingCount + 1);
	}

	static bool IsFiniteVector(const FVector& Value)
	{
		return FMath::IsFinite(Value.X) && FMath::IsFinite(Value.Y) && FMath::IsFinite(Value.Z);
	}

	static bool IsInsideAperture(
		const FVector& LocalPoint,
		float HalfWidth,
		float HalfHeight,
		float CapsuleRadius,
		float CapsuleHalfHeight)
	{
		if (!IsFiniteVector(LocalPoint) || !FMath::IsFinite(HalfWidth) || !FMath::IsFinite(HalfHeight) ||
			!FMath::IsFinite(CapsuleRadius) || !FMath::IsFinite(CapsuleHalfHeight) ||
			HalfWidth <= 0.0f || HalfHeight <= 0.0f || CapsuleRadius < 0.0f || CapsuleHalfHeight < 0.0f)
		{
			return false;
		}

		const float EffectiveWidth = HalfWidth - CapsuleRadius;
		const float EffectiveHeight = HalfHeight - CapsuleHalfHeight;
		if (EffectiveWidth <= KINDA_SMALL_NUMBER || EffectiveHeight <= KINDA_SMALL_NUMBER)
		{
			return false;
		}

		const float NormalizedX = LocalPoint.X / EffectiveWidth;
		const float NormalizedZ = LocalPoint.Z / EffectiveHeight;
		return NormalizedX * NormalizedX + NormalizedZ * NormalizedZ <= 1.0f + KINDA_SMALL_NUMBER;
	}

	static bool TryGetForwardPlaneIntersection(
		const FVector& PreviousLocalPosition,
		const FVector& CurrentLocalPosition,
		float PlaneY,
		float HalfWidth,
		float HalfHeight,
		float CapsuleRadius,
		float CapsuleHalfHeight,
		FVector& OutIntersection)
	{
		if (!IsFiniteVector(PreviousLocalPosition) || !IsFiniteVector(CurrentLocalPosition) ||
			!FMath::IsFinite(PlaneY) || !(PreviousLocalPosition.Y < PlaneY) || !(CurrentLocalPosition.Y >= PlaneY))
		{
			return false;
		}

		const float DeltaY = CurrentLocalPosition.Y - PreviousLocalPosition.Y;
		if (!FMath::IsFinite(DeltaY) || DeltaY <= KINDA_SMALL_NUMBER)
		{
			return false;
		}

		const float Alpha = (PlaneY - PreviousLocalPosition.Y) / DeltaY;
		if (Alpha < 0.0f || Alpha > 1.0f || !FMath::IsFinite(Alpha))
		{
			return false;
		}

		OutIntersection = FMath::Lerp(PreviousLocalPosition, CurrentLocalPosition, Alpha);
		return IsInsideAperture(OutIntersection, HalfWidth, HalfHeight, CapsuleRadius, CapsuleHalfHeight);
	}

	bool Update(
		float DeltaSeconds,
		bool bNearGate,
		bool bBeyondResetDistance,
		bool bResonating,
		bool bCenterSweepClear,
		bool bTargetMapValid,
		bool bSuspended,
		const FVector& CurrentLocalPosition,
		float HalfWidth,
		float HalfHeight,
		float CapsuleRadius,
		float CapsuleHalfHeight,
		float ExitY)
	{
		if (!FMath::IsFinite(DeltaSeconds) || DeltaSeconds < 0.0f || !IsFiniteVector(CurrentLocalPosition) ||
			!FMath::IsFinite(ExitY) || ExitY <= 0.0f)
		{
			Fail(TEXT("Invalid gate frame or delta."));
			return false;
		}

		if (bSuspended || State == EDreamGateState::Loading)
		{
			ForgetPosition();
			bExitEventPending = false;
			return false;
		}

		if (bBeyondResetDistance)
		{
			Reset();
			PreviousLocalPosition = CurrentLocalPosition;
			bHasPreviousPosition = true;
			return false;
		}

		if (State == EDreamGateState::Error)
		{
			if (bHasPreviousPosition && CurrentLocalPosition.Y < BackoutY)
			{
				Retry();
			}
			else
			{
				PreviousLocalPosition = CurrentLocalPosition;
				bHasPreviousPosition = true;
				return false;
			}
		}

		if (State == EDreamGateState::Traversing && CurrentLocalPosition.Y < BackoutY)
		{
			State = EDreamGateState::Ready;
			bReachedExit = false;
			bExitEventPending = false;
		}

		if (State != EDreamGateState::Traversing && State != EDreamGateState::Ready)
		{
			const float ChargeRate = 1.0f / FMath::Max(0.01f, ChargeSeconds);
			const float ChargeDelta = (bNearGate && bResonating) ? DeltaSeconds * ChargeRate : -DeltaSeconds * ChargeRate * 0.5f;
			Charge = FMath::Clamp(Charge + ChargeDelta, 0.0f, 1.0f);

			const float TargetOpen = Charge >= 1.0f ? 1.0f : 0.0f;
			OpenAlpha = FMath::FInterpConstantTo(
				OpenAlpha,
				TargetOpen,
				DeltaSeconds,
				1.0f / FMath::Max(0.01f, OpeningSeconds));

			if (Charge >= 1.0f)
			{
				State = (OpenAlpha >= SafeOpenAlpha && bCenterSweepClear && bTargetMapValid)
					? EDreamGateState::Ready
					: EDreamGateState::Opening;
			}
			else
			{
				State = (bNearGate && bResonating) ? EDreamGateState::Resonating : EDreamGateState::Idle;
			}
		}
		else if (State == EDreamGateState::Ready && (!bCenterSweepClear || !bTargetMapValid))
		{
			State = EDreamGateState::Opening;
		}

		if (Charge >= 1.0f && !bTargetMapValid && State != EDreamGateState::Traversing && State != EDreamGateState::Loading)
		{
			Fail(TEXT("Target map does not exist or is unavailable."));
			PreviousLocalPosition = CurrentLocalPosition;
			bHasPreviousPosition = true;
			return false;
		}

		if (State == EDreamGateState::Ready && bHasPreviousPosition)
		{
			FVector Intersection;
			if (TryGetForwardPlaneIntersection(
				PreviousLocalPosition,
				CurrentLocalPosition,
				0.0f,
				HalfWidth,
				HalfHeight,
				CapsuleRadius,
				CapsuleHalfHeight,
				Intersection))
			{
				State = EDreamGateState::Traversing;
				bReachedExit = false;
				bExitEventPending = false;
			}
		}

		if (State == EDreamGateState::Traversing && bHasPreviousPosition && !bReachedExit)
		{
			FVector Intersection;
			if (TryGetForwardPlaneIntersection(
				PreviousLocalPosition,
				CurrentLocalPosition,
				ExitY,
				HalfWidth,
				HalfHeight,
				CapsuleRadius,
				CapsuleHalfHeight,
				Intersection))
			{
				bReachedExit = true;
				bExitEventPending = true;
			}
		}

		PreviousLocalPosition = CurrentLocalPosition;
		bHasPreviousPosition = true;
		return bExitEventPending;
	}

	bool ConsumeExitEvent()
	{
		const bool bResult = bExitEventPending && bReachedExit && State == EDreamGateState::Traversing;
		bExitEventPending = false;
		return bResult;
	}

	bool BeginLoading()
	{
		if (State != EDreamGateState::Traversing || !bReachedExit)
		{
			return false;
		}
		State = EDreamGateState::Loading;
		bExitEventPending = false;
		ForgetPosition();
		return true;
	}

	void NotifyLoadFailed(const FString& Failure)
	{
		if (State == EDreamGateState::Loading)
		{
			Fail(Failure);
		}
	}

	void Fail(const FString& Failure)
	{
		State = EDreamGateState::Error;
		LastFailure = Failure.IsEmpty() ? TEXT("Unknown gate failure.") : Failure;
		bReachedExit = false;
		bExitEventPending = false;
		ForgetPosition();
	}

	void Retry()
	{
		if (State != EDreamGateState::Error)
		{
			return;
		}
		LastFailure.Reset();
		bReachedExit = false;
		bExitEventPending = false;
		State = Charge >= 1.0f
			? (OpenAlpha >= SafeOpenAlpha ? EDreamGateState::Ready : EDreamGateState::Opening)
			: EDreamGateState::Idle;
		ForgetPosition();
	}

	void Reset()
	{
		State = EDreamGateState::Idle;
		Charge = 0.0f;
		OpenAlpha = 0.0f;
		LastFailure.Reset();
		bReachedExit = false;
		bExitEventPending = false;
		ForgetPosition();
	}

	void ForgetPosition()
	{
		bHasPreviousPosition = false;
		PreviousLocalPosition = FVector::ZeroVector;
	}

	bool HasPreviousPosition() const { return bHasPreviousPosition; }
	bool HasReachedExit() const { return bReachedExit; }
	const FVector& GetPreviousLocalPosition() const { return PreviousLocalPosition; }

private:
	FVector PreviousLocalPosition = FVector::ZeroVector;
	bool bHasPreviousPosition = false;
	bool bReachedExit = false;
	bool bExitEventPending = false;
};
