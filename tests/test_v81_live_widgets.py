from blackterm_recon.desktop.live_widgets import StageSequence


def test_stage_sequence_class_exposes_expected_signals():
    assert hasattr(StageSequence, "stage_started")
    assert hasattr(StageSequence, "stage_finished")
    assert hasattr(StageSequence, "sequence_finished")
