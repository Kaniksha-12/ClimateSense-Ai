"""Fail-closed validation for explicitly evidenced binary-label records.

This module validates metadata consistency and eligibility assertions. It does
not independently verify source records or decide whether a coverage rule is
scientifically adequate; callers must identify the applicable target-specific
rule and retain its evidence reference. IFI association specifications below
are implementation-level, versioned definitions for inventory matching only;
they are not verified flood-occurrence definitions or an external scientific
approval. Other target enum values remain identifiers, not complete approved
specifications.
"""

import math
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from numbers import Real
from typing import Mapping, Sequence


class LabelContractError(ValueError):
	"""Raised when a label record violates the label contract."""


class LabelTarget(str, Enum):
	IFI_REPORT_ASSOCIATION = "ifi_report_association"
	OBSERVED_INUNDATION = "observed_inundation"
	GAUGE_THRESHOLD_EXCEEDANCE = "gauge_threshold_exceedance"


class LabelStatus(str, Enum):
	POSITIVE = "positive"
	NEGATIVE = "negative"
	UNKNOWN = "unknown"
	AMBIGUOUS = "ambiguous"


IFI_REPORT_ASSOCIATION_TARGET_ID = LabelTarget.IFI_REPORT_ASSOCIATION.value
IFI_SAME_DAY_SPEC_ID = "ifi_event_start_district_day_v1"
IFI_NEXT_0_TO_2_DAYS_SPEC_ID = "ifi_event_start_district_day_t_to_t_plus_2_v1"
IFI_ASSOCIATION_RULES = {
	IFI_SAME_DAY_SPEC_ID: ("ifi_lgd_code_event_start_date", "1.0.0"),
	IFI_NEXT_0_TO_2_DAYS_SPEC_ID: ("ifi_lgd_code_event_start_date_t_to_t_plus_2", "1.0.0"),
}
IFI_ASSOCIATION_SPECIFICATIONS = {
	IFI_SAME_DAY_SPEC_ID: (
		"Unit: district-day. Positive: the IFI event start calendar date, interpreted as "
		"encoded in the source without timezone conversion, matches the observation date and "
		"the event's LGD district code matches the observation district. Negative: no such "
		"match exists in the declared inventory snapshot under the declared matching rule. "
		"Neither status establishes flood occurrence or absence."
	),
	IFI_NEXT_0_TO_2_DAYS_SPEC_ID: (
		"Unit: district-day at prediction date t. Positive: an IFI event's source calendar "
		"start date, interpreted as encoded without timezone conversion, is t, t+1, or t+2 "
		"(inclusive), and its LGD district code matches the observation district. Negative: "
		"no such match exists in the declared inventory snapshot under the declared matching "
		"rule. Neither status establishes flood occurrence or absence."
	),
}


_POSITIVE_EVIDENCE_TYPES = {
	LabelTarget.IFI_REPORT_ASSOCIATION: "ifi_event_match",
	LabelTarget.OBSERVED_INUNDATION: "validated_inundation",
	LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE: "gauge_threshold_exceedance",
}
_NEGATIVE_EVIDENCE_TYPES = {
	LabelTarget.IFI_REPORT_ASSOCIATION: "ifi_inventory_snapshot_no_match",
	LabelTarget.OBSERVED_INUNDATION: "validated_no_inundation",
	LabelTarget.GAUGE_THRESHOLD_EXCEEDANCE: "gauge_below_threshold",
}
_DECISIVE_EVIDENCE_TYPES = set(_POSITIVE_EVIDENCE_TYPES.values()) | set(_NEGATIVE_EVIDENCE_TYPES.values())


@dataclass(frozen=True)
class CoverageEvidence:
	"""A target-specific, documented assertion that negative coverage is met."""

	target: LabelTarget
	rule_id: str
	reference: str
	satisfied: bool


@dataclass(frozen=True)
class LabelEvidence:
	"""Traceable evidence supporting a status for one named target."""

	target: LabelTarget
	source: str
	record_id: str
	evidence_type: str
	rule_version: str
	coverage: CoverageEvidence | None = None


@dataclass(frozen=True)
class LabelRecord:
	"""One target-specific observation and its separate eligibility flags."""

	target: LabelTarget
	status: LabelStatus
	training_eligible: bool
	evaluation_eligible: bool
	evidence: LabelEvidence | None = None
	district_lgd_code: int | None = None
	district_identity_resolved: bool | None = None


@dataclass(frozen=True)
class IFIAssociationEligibility:
	"""Validated row values and independent training/evaluation eligibility flags."""

	label_values: list[int | None]
	training_eligible: list[bool]
	evaluation_eligible: list[bool]


def _require_text(value: str, field: str) -> None:
	if not isinstance(value, str) or not value.strip():
		raise LabelContractError(f"{field} must be a non-empty string.")


def _is_null_scalar(value: object) -> bool:
	return value is None or (
		isinstance(value, Real) and not isinstance(value, bool) and math.isnan(value)
	)


def _validate_coverage(coverage: CoverageEvidence, target: LabelTarget) -> None:
	if not isinstance(coverage, CoverageEvidence):
		raise LabelContractError("coverage must be a CoverageEvidence record.")
	if not isinstance(coverage.target, LabelTarget) or coverage.target is not target:
		raise LabelContractError("coverage target must match the label target exactly.")
	_require_text(coverage.rule_id, "coverage rule_id")
	_require_text(coverage.reference, "coverage reference")
	if type(coverage.satisfied) is not bool:
		raise LabelContractError("coverage satisfied must be a boolean.")


def validate_label_record(
	record: LabelRecord,
	*,
	require_district_identity: bool = False,
) -> LabelRecord:
	"""Validate one record; unknown or ambiguous labels can never be binary eligible.

	For negative labels, ``coverage.satisfied`` must explicitly attest that the
	named target-specific coverage rule is met. The validator does not prescribe
	a universal coverage threshold or independently audit that attestation.
	"""
	if not isinstance(record, LabelRecord):
		raise LabelContractError("record must be a LabelRecord.")
	if not isinstance(record.target, LabelTarget):
		raise LabelContractError("target must be a supported LabelTarget.")
	if not isinstance(record.status, LabelStatus):
		raise LabelContractError("status must be positive, negative, unknown, or ambiguous.")
	if type(record.training_eligible) is not bool:
		raise LabelContractError("training_eligible must be a boolean.")
	if type(record.evaluation_eligible) is not bool:
		raise LabelContractError("evaluation_eligible must be a boolean.")
	if type(require_district_identity) is not bool:
		raise LabelContractError("require_district_identity must be a boolean.")

	if record.district_lgd_code is not None and (
		type(record.district_lgd_code) is not int or record.district_lgd_code <= 0
	):
		raise LabelContractError("district_lgd_code must be a positive integer when supplied.")
	if record.district_identity_resolved is not None and type(record.district_identity_resolved) is not bool:
		raise LabelContractError("district_identity_resolved must be a boolean when supplied.")
	if record.district_identity_resolved is True and record.district_lgd_code is None:
		raise LabelContractError("a resolved district identity requires district_lgd_code.")
	if require_district_identity and (
		record.district_lgd_code is None or record.district_identity_resolved is not True
	):
		raise LabelContractError(
			"district identity is required and must have a positive LGD code with a resolved crosswalk."
		)

	if record.status in (LabelStatus.UNKNOWN, LabelStatus.AMBIGUOUS) and (
		record.training_eligible or record.evaluation_eligible
	):
		raise LabelContractError(
			f"{record.status.value} labels cannot be eligible for binary training or evaluation."
		)

	evidence = record.evidence
	if record.status in (LabelStatus.POSITIVE, LabelStatus.NEGATIVE) and evidence is None:
		raise LabelContractError(f"{record.status.value} labels require target-specific evidence.")
	if evidence is None:
		return record

	if not isinstance(evidence, LabelEvidence):
		raise LabelContractError("evidence must be a LabelEvidence record.")
	if not isinstance(evidence.target, LabelTarget) or evidence.target is not record.target:
		raise LabelContractError("evidence target must match the label target exactly.")
	_require_text(evidence.source, "evidence source")
	_require_text(evidence.record_id, "evidence record_id")
	_require_text(evidence.evidence_type, "evidence evidence_type")
	_require_text(evidence.rule_version, "evidence rule_version")
	if evidence.coverage is not None:
		_validate_coverage(evidence.coverage, record.target)

	if record.status is LabelStatus.POSITIVE:
		expected_type = _POSITIVE_EVIDENCE_TYPES[record.target]
		if evidence.evidence_type != expected_type:
			raise LabelContractError(
				f"positive {record.target.value} requires evidence_type={expected_type!r}."
			)
	elif record.status is LabelStatus.NEGATIVE:
		expected_type = _NEGATIVE_EVIDENCE_TYPES[record.target]
		if evidence.evidence_type != expected_type:
			raise LabelContractError(
				f"negative {record.target.value} requires evidence_type={expected_type!r}."
			)
		coverage = evidence.coverage
		if coverage is None:
			raise LabelContractError("negative labels require explicit target-specific coverage evidence.")
		if not coverage.satisfied:
			raise LabelContractError("negative labels require coverage.satisfied=True.")
	elif evidence.evidence_type in _DECISIVE_EVIDENCE_TYPES:
		raise LabelContractError(
			f"{record.status.value} status conflicts with decisive evidence_type={evidence.evidence_type!r}."
		)

	return record


def validate_ifi_association_rows(
	rows: Sequence[Mapping[str, object]],
	*,
	target_spec_id: str,
	prefix: str = "label",
) -> IFIAssociationEligibility:
	"""Validate IFI-association metadata; never infer it from a legacy binary label.

	Eligible IFI negatives mean only no matching record in the named inventory
	snapshot under the declared rule. They are not verified flood absences.
	Metadata, evidence references, and eligibility flags are caller-supplied;
	this validator does not independently verify their sources or truth.
	"""
	_require_text(target_spec_id, "target_spec_id")
	if target_spec_id not in IFI_ASSOCIATION_SPECIFICATIONS:
		raise LabelContractError(f"unsupported IFI-association target specification: {target_spec_id!r}.")
	_require_text(prefix, "field prefix")

	required_fields = (
		"target_id",
		"target_spec_id",
		"district_identity_resolved",
		"status",
		"value",
		"training_eligible",
		"training_eligibility_reason",
		"evaluation_eligible",
		"evaluation_eligibility_reason",
		"inventory_snapshot_id",
		"matching_rule_id",
		"matching_rule_version",
		"evidence_type",
		"evidence_reference",
		"source_record_id",
	)
	label_values: list[int | None] = []
	training_eligible: list[bool] = []
	evaluation_eligible: list[bool] = []
	source_context: set[tuple[str, str, str]] = set()
	for row_number, row in enumerate(rows):
		if not isinstance(row, Mapping):
			raise LabelContractError(f"row {row_number}: IFI label row must be a mapping.")
		for name in required_fields:
			key = f"{prefix}_{name}"
			if key not in row:
				raise LabelContractError(f"row {row_number}: missing required field {key!r}.")

		def field(name: str) -> object:
			key = f"{prefix}_{name}"
			if key not in row:
				raise LabelContractError(f"row {row_number}: missing required field {key!r}.")
			return row[key]

		district_code = row.get("lgd_code")
		if (
			not isinstance(district_code, Real)
			or isinstance(district_code, bool)
			or not math.isfinite(district_code)
			or district_code <= 0
			or not float(district_code).is_integer()
		):
			raise LabelContractError(f"row {row_number}: lgd_code must be a positive integer.")
		district_resolved = field("district_identity_resolved")
		if type(district_resolved) is not bool or not district_resolved:
			raise LabelContractError(
				f"row {row_number}: district_identity_resolved must be True for IFI association."
			)
		observation_date = row.get("date")
		if not isinstance(observation_date, (date, datetime)) or (
			isinstance(observation_date, datetime) and math.isnan(observation_date.year)
		):
			raise LabelContractError(f"row {row_number}: date must be a valid district-day.")
		observation_year = row.get("year")
		if (
			not isinstance(observation_year, Real)
			or isinstance(observation_year, bool)
			or not math.isfinite(observation_year)
			or not float(observation_year).is_integer()
			or int(observation_year) != observation_date.year
		):
			raise LabelContractError(f"row {row_number}: year must match the district-day date.")

		target_id = field("target_id")
		if target_id != IFI_REPORT_ASSOCIATION_TARGET_ID:
			raise LabelContractError(
				f"row {row_number}: target_id must be {IFI_REPORT_ASSOCIATION_TARGET_ID!r}."
			)
		row_spec_id = field("target_spec_id")
		if row_spec_id != target_spec_id:
			raise LabelContractError(
				f"row {row_number}: target_spec_id must be {target_spec_id!r}."
			)

		raw_status = field("status")
		try:
			status = raw_status if isinstance(raw_status, LabelStatus) else LabelStatus(raw_status)
		except (TypeError, ValueError):
			raise LabelContractError(
				f"row {row_number}: status must be positive, negative, unknown, or ambiguous."
			) from None

		raw_value = field("value")
		value: int | None
		if _is_null_scalar(raw_value):
			value = None
		elif isinstance(raw_value, Real) and not isinstance(raw_value, bool) and raw_value in (0, 1):
			value = int(raw_value)
		else:
			raise LabelContractError(f"row {row_number}: label value must be 0, 1, or null.")

		raw_training = field("training_eligible")
		raw_evaluation = field("evaluation_eligible")
		if type(raw_training) is not bool or type(raw_evaluation) is not bool:
			raise LabelContractError(
				f"row {row_number}: training_eligible and evaluation_eligible must be booleans."
			)
		_require_text(field("training_eligibility_reason"), f"row {row_number} {prefix}_training_eligibility_reason")
		_require_text(field("evaluation_eligibility_reason"), f"row {row_number} {prefix}_evaluation_eligibility_reason")

		context_fields = ("inventory_snapshot_id", "matching_rule_id", "matching_rule_version")
		for name in (*context_fields, "evidence_type", "evidence_reference"):
			_require_text(field(name), f"row {row_number} {prefix}_{name}")
		expected_rule_id, expected_rule_version = IFI_ASSOCIATION_RULES[target_spec_id]
		if field("matching_rule_id") != expected_rule_id or field("matching_rule_version") != expected_rule_version:
			raise LabelContractError(
				f"row {row_number}: matching rule must be {expected_rule_id!r} version {expected_rule_version!r}."
			)
		source_context.add(tuple(str(field(name)).strip() for name in context_fields))
		source_record_id = field("source_record_id")
		if not _is_null_scalar(source_record_id):
			_require_text(source_record_id, f"row {row_number} {prefix}_source_record_id")

		if status is LabelStatus.POSITIVE:
			if value != 1 or field("evidence_type") != "ifi_event_match":
				raise LabelContractError(
					f"row {row_number}: positive IFI association requires value=1 and evidence_type='ifi_event_match'."
				)
			_require_text(source_record_id, f"row {row_number} {prefix}_source_record_id")
		elif status is LabelStatus.NEGATIVE:
			if value != 0 or field("evidence_type") != "ifi_inventory_snapshot_no_match":
				raise LabelContractError(
					f"row {row_number}: negative IFI association requires value=0 and evidence_type='ifi_inventory_snapshot_no_match'."
				)
			if not _is_null_scalar(source_record_id):
				raise LabelContractError(
					f"row {row_number}: a no-match record cannot include a matched source_record_id."
				)
		else:
			if value is not None:
				raise LabelContractError(
					f"row {row_number}: unknown and ambiguous statuses require a null label value."
				)
			if status is LabelStatus.UNKNOWN and field("evidence_type") in _DECISIVE_EVIDENCE_TYPES:
				raise LabelContractError(
					f"row {row_number}: unknown status conflicts with decisive IFI association evidence."
				)
			if raw_training or raw_evaluation:
				raise LabelContractError(
					f"row {row_number}: unknown and ambiguous labels cannot be training- or evaluation-eligible."
				)

		label_values.append(value)
		training_eligible.append(raw_training)
		evaluation_eligible.append(raw_evaluation)

	if len(source_context) > 1:
		raise LabelContractError(
			f"{prefix} rows must use one inventory snapshot and matching-rule version."
		)
	return IFIAssociationEligibility(label_values, training_eligible, evaluation_eligible)
