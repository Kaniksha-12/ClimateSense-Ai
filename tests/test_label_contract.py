from datetime import date

import pandas as pd
import pytest

from src.label_contract import (
	CoverageEvidence,
	IFI_ASSOCIATION_RULES,
	IFI_NEXT_0_TO_2_DAYS_SPEC_ID,
	IFI_SAME_DAY_SPEC_ID,
	LabelContractError,
	LabelEvidence,
	LabelRecord,
	LabelStatus,
	LabelTarget,
	validate_ifi_association_rows,
	validate_label_record,
)


def _evidence(
	target: LabelTarget,
	evidence_type: str,
	coverage: CoverageEvidence | None = None,
) -> LabelEvidence:
	return LabelEvidence(
		target=target,
		source="synthetic-fixture",
		record_id="record-1",
		evidence_type=evidence_type,
		rule_version="test-rule-v1",
		coverage=coverage,
	)


def _record(
	target: LabelTarget,
	status: LabelStatus,
	evidence: LabelEvidence | None = None,
	**overrides: object,
) -> LabelRecord:
	values: dict[str, object] = {
		"target": target,
		"status": status,
		"training_eligible": False,
		"evaluation_eligible": False,
		"evidence": evidence,
	}
	values.update(overrides)
	return LabelRecord(**values)  # type: ignore[arg-type]


def test_valid_positive_ifi_association_record_is_accepted():
	record = _record(
		LabelTarget.IFI_REPORT_ASSOCIATION,
		LabelStatus.POSITIVE,
		_evidence(LabelTarget.IFI_REPORT_ASSOCIATION, "ifi_event_match"),
		training_eligible=True,
		evaluation_eligible=True,
	)

	assert validate_label_record(record) is record


def test_ifi_non_match_is_unknown_for_flood_occurrence():
	record = _record(
		LabelTarget.OBSERVED_INUNDATION,
		LabelStatus.UNKNOWN,
		_evidence(LabelTarget.OBSERVED_INUNDATION, "no_ifi_match"),
	)

	assert validate_label_record(record).status is LabelStatus.UNKNOWN


def test_negative_without_coverage_evidence_is_rejected():
	record = _record(
		LabelTarget.OBSERVED_INUNDATION,
		LabelStatus.NEGATIVE,
		_evidence(LabelTarget.OBSERVED_INUNDATION, "validated_no_inundation"),
	)

	with pytest.raises(LabelContractError, match="explicit target-specific coverage"):
		validate_label_record(record)


def test_negative_is_accepted_with_target_specific_coverage_attestation():
	target = LabelTarget.OBSERVED_INUNDATION
	coverage = CoverageEvidence(
		target=target,
		rule_id="study-area-coverage-v1",
		reference="synthetic-coverage-record",
		satisfied=True,
	)
	record = _record(
		target,
		LabelStatus.NEGATIVE,
		_evidence(target, "validated_no_inundation", coverage),
		training_eligible=True,
		evaluation_eligible=True,
	)

	assert validate_label_record(record) is record


@pytest.mark.parametrize(
	("target", "positive_type", "negative_type"),
	[
		(LabelTarget.IFI_REPORT_ASSOCIATION, "ifi_event_match", "ifi_inventory_snapshot_no_match"),
		(LabelTarget.OBSERVED_INUNDATION, "validated_inundation", "validated_no_inundation"),
		(LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE, "gauge_threshold_exceedance", "gauge_below_threshold"),
	],
)
def test_each_target_accepts_its_documented_positive_and_negative_evidence(
	target, positive_type, negative_type
):
	coverage = CoverageEvidence(target, "coverage-rule-v1", "coverage-record", True)
	positive = _record(
		target,
		LabelStatus.POSITIVE,
		_evidence(target, positive_type),
		training_eligible=True,
	)
	negative = _record(
		target,
		LabelStatus.NEGATIVE,
		_evidence(target, negative_type, coverage),
		evaluation_eligible=True,
	)

	assert validate_label_record(positive) is positive
	assert validate_label_record(negative) is negative


@pytest.mark.parametrize(
	"target",
	[
		LabelTarget.IFI_REPORT_ASSOCIATION,
		LabelTarget.OBSERVED_INUNDATION,
		LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE,
	],
)
def test_positive_rejects_evidence_types_for_other_targets(target):
	for other_target in LabelTarget:
		if other_target is target:
			continue
		evidence_type = {
			LabelTarget.IFI_REPORT_ASSOCIATION: "ifi_event_match",
			LabelTarget.OBSERVED_INUNDATION: "validated_inundation",
			LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE: "gauge_threshold_exceedance",
		}[other_target]
		record = _record(
			target,
			LabelStatus.POSITIVE,
			_evidence(target, evidence_type),
		)

		with pytest.raises(LabelContractError, match="requires evidence_type"):
			validate_label_record(record)


@pytest.mark.parametrize(
	"target",
	[
		LabelTarget.IFI_REPORT_ASSOCIATION,
		LabelTarget.OBSERVED_INUNDATION,
		LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE,
	],
)
def test_negative_rejects_evidence_types_for_other_targets(target):
	coverage = CoverageEvidence(target, "coverage-rule-v1", "coverage-record", True)
	for other_target in LabelTarget:
		if other_target is target:
			continue
		evidence_type = {
			LabelTarget.IFI_REPORT_ASSOCIATION: "ifi_inventory_snapshot_no_match",
			LabelTarget.OBSERVED_INUNDATION: "validated_no_inundation",
			LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE: "gauge_below_threshold",
		}[other_target]
		record = _record(
			target,
			LabelStatus.NEGATIVE,
			_evidence(target, evidence_type, coverage),
		)

		with pytest.raises(LabelContractError, match="requires evidence_type"):
			validate_label_record(record)


def test_negative_rejects_unsatisfied_coverage_attestation():
	target = LabelTarget.OBSERVED_INUNDATION
	coverage = CoverageEvidence(target, "coverage-rule-v1", "coverage-record", False)
	record = _record(
		target,
		LabelStatus.NEGATIVE,
		_evidence(target, "validated_no_inundation", coverage),
	)

	with pytest.raises(LabelContractError, match="coverage.satisfied=True"):
		validate_label_record(record)


def test_negative_rejects_coverage_for_a_different_target():
	target = LabelTarget.OBSERVED_INUNDATION
	coverage = CoverageEvidence(
		LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE,
		"coverage-rule-v1",
		"coverage-record",
		True,
	)
	record = _record(
		target,
		LabelStatus.NEGATIVE,
		_evidence(target, "validated_no_inundation", coverage),
	)

	with pytest.raises(LabelContractError, match="coverage target must match"):
		validate_label_record(record)


@pytest.mark.parametrize(
	("rule_id", "reference"),
	[("", "coverage-record"), ("   ", "coverage-record"), ("coverage-rule-v1", ""), ("coverage-rule-v1", " \t")],
)
def test_negative_rejects_empty_coverage_rule_or_reference(rule_id, reference):
	target = LabelTarget.OBSERVED_INUNDATION
	coverage = CoverageEvidence(target, rule_id, reference, True)
	record = _record(
		target,
		LabelStatus.NEGATIVE,
		_evidence(target, "validated_no_inundation", coverage),
	)

	with pytest.raises(LabelContractError, match="coverage (rule_id|reference) must be a non-empty string"):
		validate_label_record(record)


def test_negative_rejects_malformed_coverage_object():
	target = LabelTarget.OBSERVED_INUNDATION
	record = _record(
		target,
		LabelStatus.NEGATIVE,
		_evidence(target, "validated_no_inundation", "not-coverage-evidence"),  # type: ignore[arg-type]
	)

	with pytest.raises(LabelContractError, match="coverage must be a CoverageEvidence"):
		validate_label_record(record)


@pytest.mark.parametrize(
	("coverage", "error"),
	[
		(CoverageEvidence("observed_inundation", "rule-v1", "ref-1", True), "coverage target must match"),
		(CoverageEvidence(LabelTarget.OBSERVED_INUNDATION, None, "ref-1", True), "coverage rule_id"),
		(CoverageEvidence(LabelTarget.OBSERVED_INUNDATION, "rule-v1", None, True), "coverage reference"),
		(CoverageEvidence(LabelTarget.OBSERVED_INUNDATION, "rule-v1", "ref-1", 1), "coverage satisfied"),
	],
)
def test_negative_rejects_malformed_coverage_fields(coverage, error):
	target = LabelTarget.OBSERVED_INUNDATION
	record = _record(
		target,
		LabelStatus.NEGATIVE,
		_evidence(target, "validated_no_inundation", coverage),
	)

	with pytest.raises(LabelContractError, match=error):
		validate_label_record(record)


@pytest.mark.parametrize(
	("target", "positive_type"),
	[
		(LabelTarget.IFI_REPORT_ASSOCIATION, "ifi_event_match"),
		(LabelTarget.OBSERVED_INUNDATION, "validated_inundation"),
		(LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE, "gauge_threshold_exceedance"),
	],
)
def test_positive_validates_optional_coverage_metadata(target, positive_type):
	record = _record(
		target,
		LabelStatus.POSITIVE,
		_evidence(target, positive_type, "not-coverage-evidence"),  # type: ignore[arg-type]
	)

	with pytest.raises(LabelContractError, match="coverage must be a CoverageEvidence"):
		validate_label_record(record)


def test_district_metadata_is_validated_when_identity_is_optional():
	record = _record(
		LabelTarget.IFI_REPORT_ASSOCIATION,
		LabelStatus.POSITIVE,
		_evidence(LabelTarget.IFI_REPORT_ASSOCIATION, "ifi_event_match"),
		district_lgd_code=True,
	)

	with pytest.raises(LabelContractError, match="district_lgd_code must be a positive integer"):
		validate_label_record(record)


def test_district_resolution_metadata_must_be_boolean_when_supplied():
	record = _record(
		LabelTarget.IFI_REPORT_ASSOCIATION,
		LabelStatus.POSITIVE,
		_evidence(LabelTarget.IFI_REPORT_ASSOCIATION, "ifi_event_match"),
		district_identity_resolved="yes",
	)

	with pytest.raises(LabelContractError, match="district_identity_resolved must be a boolean"):
		validate_label_record(record)


def test_resolved_district_identity_requires_lgd_code():
	record = _record(
		LabelTarget.IFI_REPORT_ASSOCIATION,
		LabelStatus.POSITIVE,
		_evidence(LabelTarget.IFI_REPORT_ASSOCIATION, "ifi_event_match"),
		district_identity_resolved=True,
	)

	with pytest.raises(LabelContractError, match="resolved district identity requires district_lgd_code"):
		validate_label_record(record)


@pytest.mark.parametrize("status", [LabelStatus.UNKNOWN, LabelStatus.AMBIGUOUS])
@pytest.mark.parametrize("eligibility", ["training_eligible", "evaluation_eligible"])
def test_unknown_and_ambiguous_cannot_be_binary_eligible(status, eligibility):
	record = _record(LabelTarget.OBSERVED_INUNDATION, status, **{eligibility: True})

	with pytest.raises(LabelContractError, match="cannot be eligible"):
		validate_label_record(record)


def test_missing_status_fails_validation():
	record = _record(LabelTarget.OBSERVED_INUNDATION, None)  # type: ignore[arg-type]

	with pytest.raises(LabelContractError, match="status must be"):
		validate_label_record(record)


def test_invalid_status_fails_validation():
	record = _record(LabelTarget.OBSERVED_INUNDATION, "no_flood")  # type: ignore[arg-type]

	with pytest.raises(LabelContractError, match="status must be"):
		validate_label_record(record)


def test_eligibility_conflicting_with_unknown_status_fails():
	record = _record(
		LabelTarget.OBSERVED_INUNDATION,
		LabelStatus.UNKNOWN,
		training_eligible=True,
	)

	with pytest.raises(LabelContractError, match="unknown labels cannot be eligible"):
		validate_label_record(record)


def test_ifi_association_evidence_cannot_label_observed_inundation():
	record = _record(
		LabelTarget.OBSERVED_INUNDATION,
		LabelStatus.POSITIVE,
		_evidence(LabelTarget.IFI_REPORT_ASSOCIATION, "ifi_event_match"),
	)

	with pytest.raises(LabelContractError, match="evidence target must match"):
		validate_label_record(record)


@pytest.mark.parametrize(
	("district_lgd_code", "district_identity_resolved"),
	[(None, None), (486, False)],
)
def test_missing_or_unresolved_district_identity_is_rejected_when_required(
	district_lgd_code, district_identity_resolved
):
	record = _record(
		LabelTarget.IFI_REPORT_ASSOCIATION,
		LabelStatus.POSITIVE,
		_evidence(LabelTarget.IFI_REPORT_ASSOCIATION, "ifi_event_match"),
		district_lgd_code=district_lgd_code,
		district_identity_resolved=district_identity_resolved,
	)

	with pytest.raises(LabelContractError, match="district identity is required"):
		validate_label_record(record, require_district_identity=True)


def test_repeated_validation_is_deterministic():
	target = LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE
	coverage = CoverageEvidence(
		target=target,
		rule_id="gauge-coverage-v1",
		reference="synthetic-gauge-observation",
		satisfied=True,
	)
	record = _record(
		target,
		LabelStatus.NEGATIVE,
		_evidence(target, "gauge_below_threshold", coverage),
		district_lgd_code=486,
		district_identity_resolved=True,
	)

	assert validate_label_record(record, require_district_identity=True) == validate_label_record(
		record, require_district_identity=True
	)


def _ifi_row(
	status: str = "positive",
	value: int | None = 1,
	spec_id: str = IFI_SAME_DAY_SPEC_ID,
	**overrides: object,
) -> dict[str, object]:
	rule_id, rule_version = IFI_ASSOCIATION_RULES[spec_id]
	row: dict[str, object] = {
		"date": date(2001, 6, 1),
		"year": 2001,
		"lgd_code": 482,
		"label_target_id": "ifi_report_association",
		"label_target_spec_id": spec_id,
		"label_district_identity_resolved": True,
		"label_status": status,
		"label_value": value,
		"label_training_eligible": True,
		"label_training_eligibility_reason": "synthetic target-qualified evidence",
		"label_evaluation_eligible": True,
		"label_evaluation_eligibility_reason": "synthetic target-qualified evidence",
		"label_inventory_snapshot_id": "ifi-release-16994648",
		"label_matching_rule_id": rule_id,
		"label_matching_rule_version": rule_version,
		"label_evidence_type": "ifi_event_match",
		"label_evidence_reference": "synthetic://ifi/record-1",
		"label_source_record_id": "UEI-1",
	}
	row.update(overrides)
	return row


def test_ifi_association_positive_requires_versioned_provenance():
	result = validate_ifi_association_rows(
		[_ifi_row()],
		target_spec_id=IFI_SAME_DAY_SPEC_ID,
	)

	assert result.label_values == [1]
	assert result.training_eligible == [True]
	assert result.evaluation_eligible == [True]


def test_ifi_association_next_two_days_uses_its_distinct_specification():
	row = _ifi_row(spec_id=IFI_NEXT_0_TO_2_DAYS_SPEC_ID)

	result = validate_ifi_association_rows(
		[row],
		target_spec_id=IFI_NEXT_0_TO_2_DAYS_SPEC_ID,
	)

	assert result.label_values == [1]


def test_ifi_gate_preserves_null_unknown_values_from_in_memory_dataframe():
	unknown = _ifi_row(
		status="unknown",
		value=None,
		label_training_eligible=False,
		label_training_eligibility_reason="unknown status",
		label_evaluation_eligible=False,
		label_evaluation_eligibility_reason="unknown status",
		label_evidence_type="insufficient_evidence",
		label_source_record_id=None,
	)
	frame = pd.DataFrame([_ifi_row(), unknown])

	result = validate_ifi_association_rows(
		frame.to_dict(orient="records"),
		target_spec_id=IFI_SAME_DAY_SPEC_ID,
	)

	assert result.label_values == [1, None]
	assert result.training_eligible == [True, False]


def test_ifi_association_negative_means_snapshot_nonmatch_only():
	row = _ifi_row(
		status="negative",
		value=0,
		label_evidence_type="ifi_inventory_snapshot_no_match",
		label_source_record_id=None,
	)

	result = validate_ifi_association_rows(
		[row],
		target_spec_id=IFI_SAME_DAY_SPEC_ID,
	)

	assert result.label_values == [0]


@pytest.mark.parametrize("status", ["unknown", "ambiguous"])
def test_ifi_unknown_and_ambiguous_rows_are_ineligible_and_null(status):
	row = _ifi_row(
		status=status,
		value=None,
		label_training_eligible=False,
		label_evaluation_eligible=False,
		label_training_eligibility_reason=f"{status} status is not binary-eligible",
		label_evaluation_eligibility_reason=f"{status} status is not binary-eligible",
		label_evidence_type="insufficient_or_conflicting_evidence",
		label_source_record_id=None,
	)

	result = validate_ifi_association_rows(
		[row],
		target_spec_id=IFI_SAME_DAY_SPEC_ID,
	)

	assert result.label_values == [None]
	assert result.training_eligible == [False]
	assert result.evaluation_eligible == [False]


@pytest.mark.parametrize(
	("status", "value", "evidence_type"),
	[
		("positive", 0, "ifi_event_match"),
		("negative", 1, "ifi_inventory_snapshot_no_match"),
		("positive", 1, "ifi_inventory_snapshot_no_match"),
		("negative", 0, "ifi_event_match"),
		("unknown", 0, "insufficient_evidence"),
		("ambiguous", 1, "conflicting_evidence"),
	],
)
def test_ifi_status_value_and_evidence_must_agree(status, value, evidence_type):
	row = _ifi_row(
		status=status,
		value=value,
		label_evidence_type=evidence_type,
		label_source_record_id=None if status != "positive" else "UEI-1",
		label_training_eligible=False if status in {"unknown", "ambiguous"} else True,
		label_evaluation_eligible=False if status in {"unknown", "ambiguous"} else True,
	)

	with pytest.raises(LabelContractError):
		validate_ifi_association_rows([row], target_spec_id=IFI_SAME_DAY_SPEC_ID)


@pytest.mark.parametrize(
	("field", "value"),
	[
		("label_target_id", "observed_inundation"),
		("label_target_spec_id", IFI_NEXT_0_TO_2_DAYS_SPEC_ID),
		("label_inventory_snapshot_id", "  "),
		("label_matching_rule_id", ""),
		("label_matching_rule_id", "different-rule"),
		("label_matching_rule_version", "2.0.0"),
		("label_evidence_reference", ""),
		("label_source_record_id", ""),
		("label_training_eligibility_reason", " "),
		("label_evaluation_eligibility_reason", ""),
	])
def test_ifi_gate_rejects_wrong_target_spec_or_missing_provenance(field, value):
	row = _ifi_row()
	row[field] = value

	with pytest.raises(LabelContractError):
		validate_ifi_association_rows([row], target_spec_id=IFI_SAME_DAY_SPEC_ID)


def test_ifi_gate_rejects_unknown_or_missing_binary_status():
	for status in ("missing", None):
		row = _ifi_row(label_status=status)
		with pytest.raises(LabelContractError, match="status must be"):
			validate_ifi_association_rows([row], target_spec_id=IFI_SAME_DAY_SPEC_ID)


def test_ifi_gate_rejects_unsupported_specification_id():
	with pytest.raises(LabelContractError, match="unsupported IFI-association target specification"):
		validate_ifi_association_rows([], target_spec_id="observed_inundation_v1")


def test_ifi_gate_rejects_missing_legacy_metadata_instead_of_using_flood_risk():
	with pytest.raises(LabelContractError, match="missing required field"):
		validate_ifi_association_rows(
			[{"flood_risk": 0, "event_ueis": ""}],
			target_spec_id=IFI_SAME_DAY_SPEC_ID,
		)


def test_ifi_gate_rejects_unknown_and_ambiguous_eligibility_conflicts():
	for status in ("unknown", "ambiguous"):
		row = _ifi_row(
			status=status,
			value=None,
			label_training_eligible=True,
			label_evaluation_eligible=False,
			label_training_eligibility_reason=f"{status} labels are ineligible",
			label_evaluation_eligibility_reason=f"{status} labels are ineligible",
			label_evidence_type="insufficient_or_conflicting_evidence",
			label_source_record_id=None,
		)
		with pytest.raises(LabelContractError, match="cannot be training- or evaluation-eligible"):
			validate_ifi_association_rows([row], target_spec_id=IFI_SAME_DAY_SPEC_ID)


def test_unknown_status_rejects_decisive_ifi_evidence():
	row = _ifi_row(
		status="unknown",
		value=None,
		label_training_eligible=False,
		label_training_eligibility_reason="unknown status",
		label_evaluation_eligible=False,
		label_evaluation_eligibility_reason="unknown status",
		label_evidence_type="ifi_event_match",
	)

	with pytest.raises(LabelContractError, match="unknown status conflicts with decisive"):
		validate_ifi_association_rows([row], target_spec_id=IFI_SAME_DAY_SPEC_ID)


@pytest.mark.parametrize(
	("field", "value"),
	[
		("lgd_code", None),
		("lgd_code", 0),
		("lgd_code", True),
		("label_district_identity_resolved", False),
		("label_district_identity_resolved", None),
		("date", None),
		("year", 2000),
	])
def test_ifi_gate_rejects_missing_or_unresolved_district_day_identity(field, value):
	row = _ifi_row()
	row[field] = value

	with pytest.raises(LabelContractError):
		validate_ifi_association_rows([row], target_spec_id=IFI_SAME_DAY_SPEC_ID)


def test_ifi_gate_rejects_mixed_inventory_or_matching_rule_versions():
	first = _ifi_row()
	second = _ifi_row()
	second["label_inventory_snapshot_id"] = "other-snapshot"

	with pytest.raises(LabelContractError, match="one inventory snapshot and matching-rule version"):
		validate_ifi_association_rows(
			[first, second],
			target_spec_id=IFI_SAME_DAY_SPEC_ID,
		)


def test_ifi_gate_keeps_training_and_evaluation_eligibility_separate():
	row = _ifi_row(
		label_training_eligible=True,
		label_evaluation_eligible=False,
		label_evaluation_eligibility_reason="held out from evaluation",
	)

	result = validate_ifi_association_rows(
		[row],
		target_spec_id=IFI_SAME_DAY_SPEC_ID,
	)

	assert result.training_eligible == [True]
	assert result.evaluation_eligible == [False]
