#if WITH_DEV_AUTOMATION_TESTS

#include "DreamGateResonance.h"
#include "Misc/AutomationTest.h"

namespace
{
	struct FGateStep
	{
		float Delta = 0.1f;
		bool bNear = true;
		bool bFar = false;
		bool bBoost = false;
		bool bClear = true;
		bool bTargetValid = true;
		bool bSuspended = false;
		FVector Position = FVector(0.0, -100.0, 0.0);
		float HalfWidth = 90.0f;
		float HalfHeight = 105.0f;
		float CapsuleRadius = 10.0f;
		float CapsuleHalfHeight = 10.0f;
		float ExitY = 330.0f;
	};

	void Step(FDreamGateResonance& Gate, const FGateStep& Input = {})
	{
		Gate.Update(
			Input.Delta,
			Input.bNear,
			Input.bFar,
			Input.bBoost,
			Input.bClear,
			Input.bTargetValid,
			Input.bSuspended,
			Input.Position,
			Input.HalfWidth,
			Input.HalfHeight,
			Input.CapsuleRadius,
			Input.CapsuleHalfHeight,
			Input.ExitY);
	}

	void MakeReady(FDreamGateResonance& Gate, const FVector& Position = FVector(0.0, -100.0, 0.0))
	{
		FGateStep Input;
		Input.bBoost = true;
		Input.Position = Position;
		for (int32 Index = 0; Index < 25; ++Index)
		{
			Step(Gate, Input);
		}
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FDreamGateChargeAndOpeningTest,
	"ButterflyDream.Gate.ChargeAndOpening",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDreamGateChargeAndOpeningTest::RunTest(const FString& Parameters)
{
	FDreamGateResonance Gate;
	for (int32 Index = 0; Index < 25; ++Index)
	{
		Step(Gate);
	}
	TestEqual(TEXT("Proximity alone produces no charge"), Gate.Charge, 0.0f);
	TestFalse(TEXT("Proximity alone does not open the gate"), Gate.OpenAlpha > 0.0f);
	TestFalse(TEXT("Proximity alone is not ready"), Gate.State == EDreamGateState::Ready);

	FGateStep Input;
	Input.bBoost = true;
	Input.bSuspended = true;
	for (int32 Index = 0; Index < 10; ++Index)
	{
		Step(Gate, Input);
	}
	TestEqual(TEXT("A suspended menu cannot charge"), Gate.Charge, 0.0f);

	Input.bSuspended = false;
	for (int32 Index = 0; Index < 25; ++Index)
	{
		Step(Gate, Input);
	}
	TestEqual(TEXT("Sustained wing input fills charge"), Gate.Charge, 1.0f);
	TestTrue(TEXT("Safe opening and a clear center produce Ready"), Gate.State == EDreamGateState::Ready);

	Input.bClear = false;
	Step(Gate, Input);
	TestTrue(TEXT("A blocked center moves Ready back to Opening"), Gate.State == EDreamGateState::Opening);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FDreamGatePlaneAndApertureTest,
	"ButterflyDream.Gate.PlaneAndAperture",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDreamGatePlaneAndApertureTest::RunTest(const FString& Parameters)
{
	FDreamGateResonance Gate;
	MakeReady(Gate);
	FGateStep Input;
	Input.Position = FVector(0.0, 100.0, 0.0);
	Step(Gate, Input);
	TestTrue(TEXT("Forward crossing of the open plane starts traversal"), Gate.State == EDreamGateState::Traversing);
	TestFalse(TEXT("The doorway alone does not complete the tunnel"), Gate.ConsumeExitEvent());

	Input.Position = FVector(0.0, 165.0, 0.0);
	Step(Gate, Input);
	TestFalse(TEXT("The middle of the tunnel does not complete it"), Gate.ConsumeExitEvent());
	Input.Position = FVector(0.0, 330.0, 0.0);
	Step(Gate, Input);
	TestTrue(TEXT("The exit plane emits exactly one event"), Gate.ConsumeExitEvent());
	TestFalse(TEXT("The exit event cannot be consumed twice"), Gate.ConsumeExitEvent());
	TestTrue(TEXT("Loading starts once after a reached exit"), Gate.BeginLoading());
	TestFalse(TEXT("Loading cannot start twice"), Gate.BeginLoading());

	FDreamGateResonance SideGate;
	MakeReady(SideGate);
	Input.Position = FVector(300.0, -100.0, 0.0);
	Step(SideGate, Input);
	Input.Position = FVector(300.0, 100.0, 0.0);
	Step(SideGate, Input);
	TestFalse(TEXT("Crossing outside the aperture cannot enter"), SideGate.State == EDreamGateState::Traversing);

	FDreamGateResonance EllipseGate;
	FGateStep EllipseInput;
	EllipseInput.HalfWidth = 17.0f;
	EllipseInput.HalfHeight = 17.0f;
	EllipseInput.CapsuleHalfHeight = 10.0f;
	EllipseInput.ExitY = 143.0f;
	EllipseInput.Position = FVector(6.0, -100.0, 6.0);
	EllipseInput.bBoost = true;
	for (int32 Index = 0; Index < 25; ++Index)
	{
		Step(EllipseGate, EllipseInput);
	}
	EllipseInput.Position = FVector(6.0, 100.0, 6.0);
	Step(EllipseGate, EllipseInput);
	TestFalse(TEXT("A square corner outside the elliptical aperture is rejected"), EllipseGate.State == EDreamGateState::Traversing);

	FDreamGateResonance CapsuleGate;
	MakeReady(CapsuleGate);
	FGateStep CapsuleInput;
	CapsuleInput.CapsuleHalfHeight = 95.0f;
	CapsuleInput.Position = FVector(0.0, -100.0, 50.0);
	Step(CapsuleGate, CapsuleInput);
	CapsuleInput.Position = FVector(0.0, 100.0, 50.0);
	Step(CapsuleGate, CapsuleInput);
	TestFalse(TEXT("The capsule half-height is deducted from the opening"), CapsuleGate.State == EDreamGateState::Traversing);

	FDreamGateResonance InitialBehindGate;
	MakeReady(InitialBehindGate, FVector(0.0, 100.0, 0.0));
	TestFalse(TEXT("Starting behind the gate is not a crossing"), InitialBehindGate.State == EDreamGateState::Traversing);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FDreamGateReturnAndFailureTest,
	"ButterflyDream.Gate.ReturnAndFailure",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDreamGateReturnAndFailureTest::RunTest(const FString& Parameters)
{
	FDreamGateResonance Gate;
	MakeReady(Gate);
	FGateStep Input;
	Input.Position = FVector(0.0, 100.0, 0.0);
	Step(Gate, Input);
	TestTrue(TEXT("The gate is traversing"), Gate.State == EDreamGateState::Traversing);
	Input.Position = FVector(0.0, -25.0, 0.0);
	Step(Gate, Input);
	TestTrue(TEXT("Backing out returns to Ready"), Gate.State == EDreamGateState::Ready);
	TestFalse(TEXT("Backing out clears the exit"), Gate.HasReachedExit());

	Input.Position = FVector(0.0, 100.0, 0.0);
	Step(Gate, Input);
	Input.bSuspended = true;
	Step(Gate, Input);
	TestTrue(TEXT("A suspended frame freezes traversal without an exit event"), Gate.State == EDreamGateState::Traversing && !Gate.ConsumeExitEvent());
	Input.bSuspended = false;
	Step(Gate, Input);
	TestTrue(TEXT("Closing a menu cannot reuse a stale position for a new transition"), Gate.State == EDreamGateState::Traversing && !Gate.ConsumeExitEvent());

	Input.bFar = true;
	Input.Position = FVector(1000.0, 500.0, 0.0);
	Step(Gate, Input);
	TestTrue(TEXT("Leaving the active area fully resets traversal"), Gate.State == EDreamGateState::Idle);
	TestEqual(TEXT("Leaving the active area clears charge"), Gate.Charge, 0.0f);

	FDreamGateResonance InvalidGate;
	FGateStep InvalidInput;
	InvalidInput.bTargetValid = false;
	InvalidInput.bBoost = true;
	for (int32 Index = 0; Index < 25; ++Index)
	{
		Step(InvalidGate, InvalidInput);
	}
	TestTrue(TEXT("An invalid target produces a latched error"), InvalidGate.State == EDreamGateState::Error);
	TestFalse(TEXT("The target error is visible"), InvalidGate.LastFailure.IsEmpty());
	InvalidInput.bTargetValid = true;
	InvalidInput.bBoost = false;
	Step(InvalidGate, InvalidInput);
	TestTrue(TEXT("Returning to the safe side permits a retry"), InvalidGate.State != EDreamGateState::Error);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FDreamGateTimingAndGeometryTest,
	"ButterflyDream.Gate.TimingAndGeometry",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDreamGateTimingAndGeometryTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("Rotary ring spacing matches the visual tunnel"), FDreamGateResonance::GetTunnelRingSpacing(true), 13.0f);
	TestEqual(TEXT("Door ring spacing matches the visual tunnel"), FDreamGateResonance::GetTunnelRingSpacing(false), 30.0f);
	TestEqual(TEXT("The rotary exit is beyond all ten rings"), FDreamGateResonance::GetTunnelExitDistance(true), 143.0f);
	TestEqual(TEXT("The door exit is beyond all ten rings"), FDreamGateResonance::GetTunnelExitDistance(false), 330.0f);

	FDreamGateResonance Gate;
	FGateStep Input;
	Input.Delta = 0.5f;
	Input.bBoost = true;
	for (int32 Index = 0; Index < 4; ++Index)
	{
		Step(Gate, Input);
	}
	TestEqual(TEXT("Low frame rates do not slow linear charge"), Gate.Charge, 1.0f);
	TestTrue(TEXT("Low frame rates do not slow safe opening"), Gate.State == EDreamGateState::Ready);

	const FTransform GateTransform(FQuat(FVector::UpVector, PI * 0.5), FVector(100.0, 200.0, 300.0), FVector(10.0));
	const FVector LocalPoint(12.0, -34.0, 56.0);
	const FVector RoundTrip = GateTransform.InverseTransformPosition(GateTransform.TransformPosition(LocalPoint));
	TestTrue(TEXT("Scaled rotated local transforms round-trip correctly"), RoundTrip.Equals(LocalPoint, 0.001f));

	FGateStep ZeroInput;
	ZeroInput.Delta = 0.0f;
	Step(Gate, ZeroInput);
	TestFalse(TEXT("Zero delta cannot create an exit event"), Gate.ConsumeExitEvent());
	ZeroInput.Delta = -1.0f;
	Step(Gate, ZeroInput);
	TestTrue(TEXT("Negative delta produces an error rather than corrupting state"), Gate.State == EDreamGateState::Error);
	return true;
}

#endif
