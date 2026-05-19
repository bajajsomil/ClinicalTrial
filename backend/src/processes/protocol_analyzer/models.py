from typing import List, Any, Dict, Union, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, DirectoryPath, constr, validator, model_validator


class BlobUploadInput(BaseModel):
    container_name: constr(strip_whitespace=True, min_length=1)
    filepath: DirectoryPath
    file_name: constr(strip_whitespace=True, min_length=1)

class FieldResult(BaseModel):
    """Generic field result for extracted items."""
    page_number: Union[int, str, None] = None
    context: Optional[str] = None
    extracted_text: Optional[str] = None


class ChunkResult(BaseModel):
    """Main container for protocol-level extraction results."""

    duration: List[FieldResult] = Field(default_factory=list)
    region: List[FieldResult] = Field(default_factory=list)
    number_of_sites: List[FieldResult] = Field(default_factory=list)
    participants: List[FieldResult] = Field(default_factory=list)
    pivotal_study: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    key_requirements: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    risk_factors: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    vendor_categories: List[FieldResult] = Field(default_factory=list)
    
    error: Optional[str] = None


class BaseNoNoneModel(BaseModel):
    model_config = {
        "extra": "allow",
        "from_attributes": True,
        "populate_by_name": True,
        "exclude_none": True
    }

class FieldOutput(BaseNoNoneModel):
    value: Union[str, int, List[str], None] = None
        # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None



class PivotalStudy(BaseNoNoneModel):
    pivotal_study: Optional[str] = Field(None, description="Exact pivotal or confirmatory study designation, e.g., 'Pivotal Study: Phase III'")
    note: Optional[str] = Field(None, description="Clarifies whether pivotal/confirmatory designation was found or absent")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None


class VendorCategoryOutput(BaseModel):
    key_capabilities: Dict[str, Any] = Field(default_factory=dict)
    technical_requirements: Dict[str, Any] = Field(default_factory=dict)
    risk_factors: Dict[str, Any] = Field(default_factory=dict)
    critical_success_factors: Dict[str, Any] = Field(default_factory=dict)
    
# --- 2. The Parent: Metadata + Dynamic Vendors ---
class VendorCategoriesBlock(BaseModel):
    # A. Explicit Metadata Fields (These belong here!)
    # defined explicitly so Pydantic grabs them first
    page_number: Optional[List[Union[int, str]]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    # B. Allow "Extra" fields (This is where "Vendor A", "Vendor B" land)
    class Config:
        extra = "allow"

    # C. Validation Logic: 
    # This separates the "Vendors" from the "Metadata"
    @model_validator(mode='after')
    def validate_extra_vendors(self):
        # We look at the 'extra' fields that Pydantic found
        if self.__pydantic_extra__:
            for key, value in self.__pydantic_extra__.items():
                # We ensure these extra keys are treated as Vendor Objects
                # AND we ensure we aren't accidentally trying to convert metadata
                if isinstance(value, dict):
                    self.__pydantic_extra__[key] = VendorCategoryOutput(**value)
        return self



class FinalResult(BaseModel):
    error: Optional[str] = None
    duration: FieldOutput = Field(default_factory=FieldOutput)
    region: FieldOutput = Field(default_factory=FieldOutput)
    number_of_sites: FieldOutput = Field(default_factory=FieldOutput)
    participants: FieldOutput = Field(default_factorśy=FieldOutput)
    pivotal_study: PivotalStudy = Field(default_factory=PivotalStudy)
    key_requirements: FieldOutput = Field(default_factory=FieldOutput)
    risk_factors: FieldOutput = Field(default_factory=FieldOutput)
    vendor_categories: VendorCategoriesBlock = Field(default_factory=VendorCategoriesBlock)
    

# ----------------------------
# Base field (safe defaults)
# ----------------------------
class ExtractedField(BaseModel):
    page_number: Union[int, str, None] = None
    context: Optional[str] = None
    extracted_text: Optional[str] = None


# ----------------------------
# Nested sections (safe defaults)
# ----------------------------
class StudyDesignAndMethodology(BaseModel):
    study_type: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    phase: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    randomization: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    blinding: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])


class VisitScheduleAndProcedures(BaseModel):
    pre_screening: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    screening_period: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    treatment_period: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])


# ----------------------------
# Main model (ChunkResult2)
# ----------------------------
class ChunkResult2(BaseModel):
    error: Optional[str] = None

    study_design_and_methodology: StudyDesignAndMethodology = Field(
        alias="study_design_&_methodology", default_factory=StudyDesignAndMethodology
    )

    primary_objective: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    secondary_objective: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    endpoint: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    target_population: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    sample_size: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    lab_assessments: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])
    dose_modification: List[ExtractedField] = Field(default_factory=lambda: [ExtractedField()])

    visit_schedule_and_procedures: VisitScheduleAndProcedures = Field(
        alias="visit_schedule_&_procedures", default_factory=VisitScheduleAndProcedures
    )

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True

class FieldData(BaseModel):
    value: Union[str, List[str]] = ""
        # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class PreScreeningPeriod(BaseModel):
    period_days: Optional[str] = Field(None, description="Time window for the pre screening period (e.g., Day -28 to -1)")
    assessments: List[str] = Field(default_factory=list, description="List of assessments performed during the pre screening period only")

        # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class ScreeningPeriod(BaseModel):
    period_days: Optional[str] = Field(None, description="Time window for the screening period (e.g., Day -28 to -1)")
    assessments: List[str] = Field(default_factory=list, description="List of assessments performed during the screening period only")

    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class TreatmentPeriod(BaseModel):
    timepoints: Optional[str] = Field(None, description="Time window for the baseline.")
    assessments: List[str] = Field(default_factory=list, description="List of assessments performed during the screening period only")
    
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class LaboratoryAssessment(BaseModel):
    lab_category: Optional[str] = Field(None, description="Name of the lab assessment category (e.g., Safety, Biomarker, PK)")
    tests: List[str] = Field(default_factory=list, description="List of specific laboratory tests or analytes included in this category")
    frequency: Optional[str] = Field(None, description="Timepoints or schedule when these laboratory assessments are performed")

class LaboratoryAssessmentBlock(BaseModel):
    laboratory_assessments: List[LaboratoryAssessment] = Field(default_factory=list, description="All laboratory assessment categories extracted from the protocol")
        # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class PrimaryEndpoint(BaseModel):
    timeframe: Optional[str] = Field(None, alias="Timeframe")
    population: Optional[str] = Field(None, alias="Population")
    endpoint_variable: Optional[str] = Field(None, alias="Endpoint/Variable")
    treatment_of_interest: Optional[str] = Field(None, alias="Treatment of Interest")
    handling_of_intercurrent_events: Optional[str] = Field(None, alias="Handling of intercurrent events")
    summary_measure: Optional[str] = Field(None, alias="The Summary Measure")

    class Config:
        populate_by_name = True

class SecondaryEndpoint(BaseModel):
    timeframe: Optional[str] = Field(None, alias="Timeframe")
    population: Optional[str] = Field(None, alias="Population")
    endpoint_variable: Optional[str] = Field(None, alias="Endpoint/Variable")
    treatment_of_interest: Optional[str] = Field(None, alias="Treatment of Interest")
    handling_of_intercurrent_events: Optional[str] = Field(None, alias="Handling of intercurrent events")
    summary_measure: Optional[str] = Field(None, alias="The Summary Measure")

    class Config:
        populate_by_name = True
        
class SecondaryEndpointsBlock(BaseModel):
    secondary_endpoints: List[SecondaryEndpoint] = Field(default_factory=list)

        # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely


class PrimaryEndpointBlock(BaseModel):
    primary_endpoints: List[PrimaryEndpoint] = Field(default_factory=list)

        # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class FinalResult2(BaseModel):
    error: Optional[str] = None
    study_type: FieldData = Field(default_factory=FieldData)
    phase: FieldData = Field(default_factory=FieldData)
    randomization: FieldData = Field(default_factory=FieldData)
    blinding: FieldData = Field(default_factory=FieldData)
    primary_objective: FieldData = Field(default_factory=FieldData)
    secondary_objective: FieldData = Field(default_factory=FieldData)
    primary_endpoint: PrimaryEndpointBlock = Field(default_factory=PrimaryEndpointBlock)
    secondary_endpoint: SecondaryEndpointsBlock = Field(default_factory=SecondaryEndpointsBlock)
    target_population: FieldData = Field(default_factory=FieldData)
    sample_size: FieldData = Field(default_factory=FieldData)
    lab_assessments: LaboratoryAssessmentBlock = Field(default_factory=LaboratoryAssessmentBlock)
    dose_modification: FieldData = Field(default_factory=FieldData)
    pre_screening: PreScreeningPeriod= Field(default_factory=PreScreeningPeriod)
    screening_period: ScreeningPeriod= Field(default_factory=ScreeningPeriod)
    treatment_period: TreatmentPeriod = Field(default_factory=TreatmentPeriod)



class ChunkResult3(BaseModel):
    stratification_factors: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    safety_follow_up: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    end_of_treatment: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    visit_windows: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    rescue_therapy: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    interim_analyses: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    assays: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    primary_efficacy_assessments: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    patient_reported_outcomes: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    background_therapy: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    operational_excellence: List[FieldResult] = Field(default_factory=lambda: [FieldResult()])
    error: Optional[str] = None
    
class Assay(BaseModel):
    assay_name: str
    assay_type: Optional[str] = None
    analyte: Optional[str] = None
    sample_matrix: Optional[str] = None
    purpose: Optional[str] = None
    timing: Optional[str] = None
    population: Optional[str] = None


class AssayBlock(BaseModel):
    assays: List[Assay] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class PrimaryEfficacyAssessments(BaseModel):
    assessment_name: str
    assessment_short_description: Optional[str] = None
    assessment_frequency: Optional[str] = None

class PrimaryEfficacyAssessmentsBlock(BaseModel):
    primary_efficacy_assessments: List[PrimaryEfficacyAssessments] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class PatientReportedOutcomes(BaseModel):
    pro_name: str
    pro_description: Optional[str] = None
    pro_frequency: Optional[str] = None


class PatientReportedOutcomesBlock(BaseModel):
    patient_reported_outcomes: List[PatientReportedOutcomes] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class TherapyItem(BaseModel):
    therapy_name: Optional[str] = Field(None, description="Exact name of the drug or therapy class")
    therapy_details: Optional[str] = Field(None, description="Dose, duration, stability, or usage rule")


class BackgroundTherapy(BaseModel):
    applicable_to: Optional[str] = Field(None, description="Which arm or population the background therapy applies to")
    therapies: List[TherapyItem] = Field(default_factory=list, description="List of therapy items with details")


class BackgroundTherapyBlock(BaseModel):
    background_therapy: List[BackgroundTherapy] = Field(default_factory=list, description="List of background therapy groups by applicability")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class EndOfTreatment(BaseModel):
    timepoint: Optional[str] = Field(None, description="Scheduled timing of the End of Treatment visit (e.g., 'Week 24', 'Visit 8')")
    assessments: List[str] = Field(default_factory=list, description="List of assessments or procedures conducted at End of Treatment")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class SafetyFollowUp(BaseModel):
    timepoints: Optional[str] = Field(None, description="Scheduled timing of the Safety Follow-Up period (e.g., 'Week 28, 32, 36', '30 days post last dose')")
    assessments: List[str] = Field(default_factory=list, description="List of safety-related assessments during follow-up")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class OperationalExcellence(BaseModel):
    component_name: Optional[str] = Field(None, description="Name of the operational component (e.g., Site Network, CROs, Central Labs, Imaging, Drug Supply)")
    description: Optional[str] = Field(None, description="Operational structure or vendor description (vendor name or functional responsibility)")

class OperationalExcellenceBlock(BaseModel):
    operational_excellence: List[OperationalExcellence] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class FinalResult3(BaseModel):
    error: Optional[str] = None
    stratification_factors: FieldOutput = Field(default_factory=lambda: FieldOutput())
    safety_follow_up: SafetyFollowUp = Field(default_factory=lambda: SafetyFollowUp())
    end_of_treatment: EndOfTreatment = Field(default_factory=lambda: EndOfTreatment())
    visit_windows: FieldOutput = Field(default_factory=lambda: FieldOutput())
    rescue_therapy: FieldOutput = Field(default_factory=lambda: FieldOutput())
    interim_analyses: FieldOutput = Field(default_factory=lambda: FieldOutput())
    assays: AssayBlock = Field(default_factory=lambda: AssayBlock())
    primary_efficacy_assessments: PrimaryEfficacyAssessmentsBlock = Field(default_factory=lambda: PrimaryEfficacyAssessmentsBlock())
    patient_reported_outcomes: PatientReportedOutcomesBlock = Field(default_factory=lambda: PatientReportedOutcomesBlock())
    background_therapy: BackgroundTherapyBlock = Field(default_factory=lambda: BackgroundTherapyBlock())
    operational_excellence: OperationalExcellenceBlock = Field(default_factory=lambda: OperationalExcellenceBlock())

class ChunkResult4(BaseModel):
    prohibited_medications: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    imaging_studies: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    active_treatment_arm: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    control_arm: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    exploratory_endpoints: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    safety_endpoints: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    regulatory_frameworks: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    safety_monitoring: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    data_management_quality: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    statistical_analytical_plan: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    protocol_version_history: Optional[List[FieldResult]] = Field(default_factory=lambda: [FieldResult()])
    error: Optional[str] = None
    

class ProhibitedMedication(BaseModel):
    category: Optional[str] = Field(None, description="Medication category or grouping (e.g., Biologics, Other)")
    items: List[str] = Field(default_factory=list, description="List of specific prohibited drugs or classes")
    details: Optional[str] = Field(None, description="Restriction details, e.g., timing or conditions of prohibition")

class ProhibitedMedicationsBlock(BaseModel):
    prohibited_medications: List[ProhibitedMedication] = Field(default_factory=list, description="List of prohibited medication groups")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class ImagingStudy(BaseModel):
    imaging_type: Optional[str] = Field(None, description="Type or modality of the imaging study (e.g., Radiographic Assessment, MRI, Ultrasound)")
    description: Optional[str] = Field(None, description="Purpose, anatomic focus, scoring method, or other imaging details")
    frequency: Optional[str] = Field(None, description="Timing or schedule when imaging is performed")

class ImagingStudiesBlock(BaseModel):
    imaging_studies: List[ImagingStudy] = Field(default_factory=list, description="All imaging studies extracted from the protocol")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class ActiveTreatmentArm(BaseModel):
    arm_type: Optional[str] = Field(None, description="Type of arm (Experimental / Investigational)")
    population_size: Optional[str] = Field(None, description="Sample size if specified (e.g., n=375)")
    drug_name: Optional[str] = Field(None, description="Investigational drug name")
    drug_description: Optional[str] = Field(None, description="Short description or drug class")
    dose: Optional[str] = Field(None, description="Dose and frequency of administration")
    route: Optional[str] = Field(None, description="Route of administration")
    timing: Optional[str] = Field(None, description="Dosing schedule or time of administration")
    duration: Optional[str] = Field(None, description="Treatment duration")
    packaging: Optional[str] = Field(None, description="Packaging or dispensing details")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class ControlArm(BaseModel):
    arm_type: Optional[str] = Field(None, description="Type of control (Placebo / Active Comparator)")
    population_size: Optional[str] = Field(None, description="Sample size if specified (e.g., n=375)")
    drug_name: Optional[str] = Field(None, description="Name or description of control drug or placebo")
    drug_description: Optional[str] = Field(None, description="Short description or drug class")
    dose: Optional[str] = Field(None, description="Dose and frequency of administration")
    route: Optional[str] = Field(None, description="Route of administration")
    timing: Optional[str] = Field(None, description="Timing or dosing schedule")
    duration: Optional[str] = Field(None, description="Treatment duration")
    packaging: Optional[str] = Field(None, description="Packaging or dispensing details")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class ExploratoryEndpoint(BaseModel):
    endpoint: str = Field(
        ...,
        description="Exact name of the exploratory endpoint"
    )
    endpoint_description: List[str] = Field(
        ...,
        description="List of bullet points describing measurement details, timeframe, analysis method, population, or other relevant information"
    )

class ExploratoryEndpointBlock(BaseModel):
    exploratory_endpoints: List[ExploratoryEndpoint] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class SafetyEndpoint(BaseModel):
    endpoint: str = Field(
        ...,
        description="Exact name or category of the safety endpoint"
    )
    endpoint_description: List[str] = Field(
        ...,
        description="List of bullet points describing criteria, grading, timeframe, population, or analysis details"
    )

class SafetyEndpointBlock(BaseModel):
    safety_endpoints: List[SafetyEndpoint] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class RegulatoryFramework(BaseModel):
    agency_name: Optional[str] = Field(None, description="Name of the regulatory authority or framework (e.g., FDA, EMA, GCP Compliance)")
    details: Optional[str] = Field(None, description="Regulatory status, designation, or compliance details")


class RegulatoryFrameworkBlock(BaseModel):
    regulatory_frameworks: List[RegulatoryFramework] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely


class SafetyMonitoring(BaseModel):
    monitoring_component: Optional[str] = Field(None, description="Name of the safety monitoring component or mechanism")
    description: Optional[str] = Field(None, description="Short description of the monitoring activity or rule")


class SafetyMonitoringBlock(BaseModel):
    safety_monitoring: List[SafetyMonitoring] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class DataManagementQuality(BaseModel):
    component_name: Optional[str] = Field(None, description="Name of the data management or quality system/process")
    description: Optional[str] = Field(None, description="Brief description of the data management component or quality process")


class DataManagementQualityBlock(BaseModel):
    data_management_quality: List[DataManagementQuality] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class ProtocolVersionHistory(BaseModel):
    version_number: Optional[str] = Field(None, description="Version or amendment identifier (e.g., Version 3.0, Amendment 1)")
    version_date: Optional[str] = Field(None, description="Date of approval or issue for that version")
    changes_summary: Optional[str] = Field(None, description="Summary of updates or rationale for changes")

class ProtocolVersionHistoryBlock(BaseModel):
    protocol_version_history: List[ProtocolVersionHistory] = Field(default_factory=list)
    note: Optional[str] = Field(None, description="Message noting absence of version history or special condition")
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely
        
class StatisticalAnalyticalPlan(BaseModel):
    parameter_name: Optional[str] = Field(None, description="Name of the statistical or analytical plan parameter")
    parameter_value: Optional[str] = Field(None, description="Content or value associated with the parameter")


class StatisticalAnalyticalPlanBlock(BaseModel):
    statistical_analytical_plan: List[StatisticalAnalyticalPlan] = Field(default_factory=list)
    # ---- OPTIONAL METADATA (top-level, not nested) ----
    page_number: Optional[List[int | str]] = None
    context: Optional[List[str]] = None
    extracted_text: Optional[List[str]] = None

    class Config:
        extra = "allow"  # allow future metadata safely

class FinalResult4(BaseModel):
    error: Optional[str] = None
    prohibited_medications: ProhibitedMedicationsBlock = Field(default_factory=lambda: ProhibitedMedicationsBlock())
    imaging_studies: ImagingStudiesBlock = Field(default_factory=lambda: ImagingStudiesBlock())
    active_treatment_arm: ActiveTreatmentArm = Field(default_factory=lambda: ActiveTreatmentArm())
    control_arm: ControlArm = Field(default_factory=lambda: ControlArm())
    exploratory_endpoints: ExploratoryEndpointBlock = Field(default_factory=lambda: ExploratoryEndpointBlock())
    safety_endpoints: SafetyEndpointBlock = Field(default_factory=lambda: SafetyEndpointBlock())
    regulatory_frameworks: RegulatoryFrameworkBlock = Field(default_factory=lambda: RegulatoryFrameworkBlock())
    safety_monitoring: SafetyMonitoringBlock = Field(default_factory=lambda: SafetyMonitoringBlock())
    data_management_quality: DataManagementQualityBlock = Field(default_factory=lambda: DataManagementQualityBlock())
    statistical_analytical_plan: StatisticalAnalyticalPlanBlock = Field(default_factory=lambda: StatisticalAnalyticalPlanBlock())
    protocol_version_history: ProtocolVersionHistoryBlock = Field(default_factory=lambda: ProtocolVersionHistoryBlock())

class ProcessPDFResponse(BaseModel):
    status: str
    result: Optional[Dict[str, dict]] = None  # allow dicts after renaming
    metric_result: Optional[Dict[str, Union[Dict[str, Optional[float]], Optional[float]]]] = Field(default=None, exclude=True)
    error: Optional[str] = None

    model_config = {
        "exclude_none": True
    }

    def model_dump(self, **kwargs):
        exclude = kwargs.pop("exclude", set())
        if self.metric_result is None:
            exclude = set(exclude) | {"metric_result"}
        return super().model_dump(exclude=exclude, **kwargs)

# --- Helper Model ---
class ExtractionField(BaseModel):
    value: Optional[str] = None
    # These metadata fields exist here so we can read them from input
    context: Optional[List[Optional[str]]] = None
    page_number: Optional[List[Optional[str]]] = None
    extracted_text: Optional[List[Optional[str]]] = None

class FinalResult5(BaseModel):
    Protocol_Number: Optional[ExtractionField] = None
    Trial_Code: Optional[ExtractionField] = None
    Program: Optional[ExtractionField] = None
    Indication: Optional[ExtractionField] = None
    error: Optional[str] = None