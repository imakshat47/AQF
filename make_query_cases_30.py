from __future__ import annotations
import json
from pathlib import Path

COMP = "openEHR-EHR-COMPOSITION.outpatient_high_complexity_procedures.v1"

# -----------------------------
# Entry archetypes
# -----------------------------
ENTRY_HCPA = "openEHR-EHR-ADMIN_ENTRY.high_complexity_procedures_sus.v1"
ENTRY_DISCHARGE = "openEHR-EHR-ADMIN_ENTRY.patient_discharge.v1"
ENTRY_DIAG = "openEHR-EHR-EVALUATION.problem_diagnosis-sus.v1"
ENTRY_PROC = "openEHR-EHR-ACTION.procedure-sus.v1"
ENTRY_BARI = "openEHR-EHR-EVALUATION.bariatric_surgery_evaluation.v1"
ENTRY_BMI = "openEHR-EHR-OBSERVATION.body_mass_index.v1"
ENTRY_WEIGHT = "openEHR-EHR-OBSERVATION.body_weight.v1"
ENTRY_HEIGHT = "openEHR-EHR-OBSERVATION.height.v1"

# -----------------------------
# Helper constructors
# -----------------------------
def fk(entry_arch: str, subgroup: str, element_name: str, at_code: str) -> str:
    return f"{COMP}|{entry_arch}|{subgroup}|{element_name}|{at_code}"

def crit(field_key, operator, value, entry_name, subgroup, element_name):
    row = {
        "field_key": field_key,
        "operator": operator,
        "entry_name": entry_name,
        "cluster_path_str": subgroup,
        "element_name": element_name
    }
    if value is not None:
        row["value"] = value
    return row

def out(field_key, name, entry_name, subgroup, element_name, dv_type):
    return {
        "field_key": field_key,
        "name": name,
        "entry_name": entry_name,
        "cluster_path_str": subgroup,
        "element_name": element_name,
        "dv_type": dv_type
    }

def sort_spec(field_key, direction, entry_name, subgroup, element_name):
    return {
        "field_key": field_key,
        "direction": direction,
        "entry_name": entry_name,
        "cluster_path_str": subgroup,
        "element_name": element_name
    }

ADV_DEFAULT = {
    "occurrence_semantics": "ALL",
    "include_unknown": False,
    "slice_size": 200,
    "result_limit": 100
}

# -----------------------------
# Reusable field keys
# -----------------------------
FK_STATE = fk(ENTRY_HCPA, "General data", "State", "at0028")
FK_REASON = fk(ENTRY_HCPA, "General data", "reason for encounter", "at0010")
FK_AGE = fk(ENTRY_HCPA, "General data", "patient age", "at0012")
FK_ISSUE_DATE = fk(ENTRY_HCPA, "General data", "issue date", "at0009")

FK_CHEMO_SCHEMA = fk(ENTRY_HCPA, "chemotherapy", "schema", "at0014")
FK_CHEMO_DURATION = fk(ENTRY_HCPA, "chemotherapy", "duration of treatment", "at0013")
FK_CHEMO_START = fk(ENTRY_HCPA, "chemotherapy", "date of beginning of chemotherapy", "at0031")

FK_RADIO_START = fk(ENTRY_HCPA, "radiotherapy", "date of beginning of radiotherapy", "at0032")

FK_TRANSPLANT_IND = fk(ENTRY_HCPA, "transplantation", "indicator of transplantation", "at0029")
FK_TRANSPLANT_NUM = fk(ENTRY_HCPA, "transplantation", "number of transplantations", "at0022")
FK_TRANSPLANT_ENROLLED = fk(ENTRY_HCPA, "transplantation", "enrolled for transplantation", "at0021")

FK_ULTRASOUND = fk(ENTRY_HCPA, "renal therapy", "abdominal ultrasonography", "at0026")
FK_DIALYSIS_DATE = fk(ENTRY_HCPA, "renal therapy", "date of first dialysis", "at0030")
FK_FISTULA = fk(ENTRY_HCPA, "renal therapy", "venous fistula amount", "at0027")

FK_DISCHARGE_DATE = fk(ENTRY_DISCHARGE, "(no cluster)", "date of discharge", "at0002")
FK_DISCHARGE_REASON = fk(ENTRY_DISCHARGE, "(no cluster)", "reason for discharge", "at0003")

FK_PROBLEM = fk(ENTRY_DIAG, "(no cluster)", "Problem", "at0002.1")
FK_SECONDARY = fk(ENTRY_DIAG, "(no cluster)", "Secondary Diagnosis", "at0.1")
FK_ASSOC = fk(ENTRY_DIAG, "(no cluster)", "Associated causes", "at0.2")
FK_LYMPH = fk(ENTRY_DIAG, "(no cluster)", "Invaded regional linphonodes", "at0.4")

FK_CLIN_STAGE = fk(ENTRY_DIAG, "Tumour - TNM Cancer staging / Clinical (cTNM)", "Clinical staging", "at0010")
FK_PATH_GRADE = fk(ENTRY_DIAG, "Tumour - TNM Cancer staging / Pathological (pTNM)", "Histopathological grading (G)", "at0035")
FK_PATH_DATE = fk(ENTRY_DIAG, "Tumour - TNM Cancer staging / Pathological (pTNM)", "date of pathological identification", "at0.44")
FK_TOPOGRAPHY = fk(ENTRY_DIAG, "Tumour - TNM Cancer staging", "topography", "at0.43")

FK_PROCEDURE = fk(ENTRY_PROC, "(no cluster)", "Procedure", "at0002")
FK_IRRAD1 = fk(ENTRY_PROC, "(no cluster)", "irradiated area 1", "at0.59")
FK_IRRAD2 = fk(ENTRY_PROC, "(no cluster)", "irradiated area 2", "at0.59")
FK_FIELDS1 = fk(ENTRY_PROC, "(no cluster)", "fields/insertions 1", "at0.61")
FK_ACCESS = fk(ENTRY_PROC, "(no cluster)", "vascular access", "at0.63")

FK_FOLLOWUP = fk(ENTRY_BARI, "(no cluster)", "duration of follow-up (months)", "at0002")
FK_BAROS_SCORE = fk(ENTRY_BARI, "(no cluster)", "Baros score", "at0003")
FK_BAROS_TABLE = fk(ENTRY_BARI, "(no cluster)", "Baros table", "at0004")

FK_BMI = fk(ENTRY_BMI, "(no cluster)", "Body Mass Index", "at0004")
FK_WEIGHT = fk(ENTRY_WEIGHT, "(no cluster)", "Weight", "at0004")
FK_HEIGHT = fk(ENTRY_HEIGHT, "(no cluster)", "Height/Length", "at0004")

# -----------------------------
# Query groups
# -----------------------------
queries = []

# =========================================================
# 10 SIMPLE QUERIES
# =========================================================
queries.extend([
    {
        "name": "simple_01_state_equals_sp",
        "form_state": {
            "criteria": [crit(FK_STATE, "=", "SÃO PAULO", "HCPA", "General data", "State")],
            "output_fields": [
                out(FK_STATE, "HCPA → General data → State", "HCPA", "General data", "State", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_02_state_equals_rj",
        "form_state": {
            "criteria": [crit(FK_STATE, "=", "RIO DE JANEIRO", "HCPA", "General data", "State")],
            "output_fields": [
                out(FK_STATE, "HCPA → General data → State", "HCPA", "General data", "State", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_03_reason_equals_quimio",
        "form_state": {
            "criteria": [crit(FK_REASON, "=", "QUIMIOTERAPIA", "HCPA", "General data", "reason for encounter")],
            "output_fields": [
                out(FK_REASON, "HCPA → General data → reason for encounter", "HCPA", "General data", "reason for encounter", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_04_reason_equals_radio",
        "form_state": {
            "criteria": [crit(FK_REASON, "=", "RADIOTERAPIA", "HCPA", "General data", "reason for encounter")],
            "output_fields": [
                out(FK_REASON, "HCPA → General data → reason for encounter", "HCPA", "General data", "reason for encounter", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_05_patient_age_gt_70",
        "form_state": {
            "criteria": [crit(FK_AGE, ">", 70, "HCPA", "General data", "patient age")],
            "output_fields": [
                out(FK_AGE, "HCPA → General data → patient age", "HCPA", "General data", "patient age", "DV_COUNT")
            ],
            "sort": sort_spec(FK_AGE, "desc", "HCPA", "General data", "patient age"),
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_06_chemo_schema_contains_tmx",
        "form_state": {
            "criteria": [crit(FK_CHEMO_SCHEMA, "contains", "TMX", "HCPA", "chemotherapy", "schema")],
            "output_fields": [
                out(FK_CHEMO_SCHEMA, "HCPA → chemotherapy → schema", "HCPA", "chemotherapy", "schema", "DV_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_07_procedure_contains_radioterapia",
        "form_state": {
            "criteria": [crit(FK_PROCEDURE, "contains", "RADIOTERAPIA", "Procedure undertaken", "(no cluster)", "Procedure")],
            "output_fields": [
                out(FK_PROCEDURE, "Procedure undertaken → Procedure", "Procedure undertaken", "(no cluster)", "Procedure", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_08_problem_contains_c50_9",
        "form_state": {
            "criteria": [crit(FK_PROBLEM, "contains", "C50.9", "Problem/Diagnosis", "(no cluster)", "Problem")],
            "output_fields": [
                out(FK_PROBLEM, "Problem/Diagnosis → Problem", "Problem/Diagnosis", "(no cluster)", "Problem", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_09_clinical_staging_equals_3",
        "form_state": {
            "criteria": [crit(FK_CLIN_STAGE, "=", "3", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Clinical (cTNM)", "Clinical staging")],
            "output_fields": [
                out(FK_CLIN_STAGE, "Problem/Diagnosis → Tumour - TNM Cancer staging / Clinical (cTNM) → Clinical staging", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Clinical (cTNM)", "Clinical staging", "DV_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "simple_10_regional_lymph_nodes_true",
        "form_state": {
            "criteria": [crit(FK_LYMPH, "=", "true", "Problem/Diagnosis", "(no cluster)", "Invaded regional linphonodes")],
            "output_fields": [
                out(FK_LYMPH, "Problem/Diagnosis → Invaded regional linphonodes", "Problem/Diagnosis", "(no cluster)", "Invaded regional linphonodes", "DV_BOOLEAN")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    }
])

# =========================================================
# 10 MEDIUM QUERIES (two criteria)
# =========================================================
queries.extend([
    {
        "name": "medium_01_state_sp_and_radioterapia",
        "form_state": {
            "criteria": [
                crit(FK_STATE, "=", "SÃO PAULO", "HCPA", "General data", "State"),
                crit(FK_REASON, "=", "RADIOTERAPIA", "HCPA", "General data", "reason for encounter")
            ],
            "output_fields": [
                out(FK_STATE, "HCPA → General data → State", "HCPA", "General data", "State", "DV_CODED_TEXT"),
                out(FK_REASON, "HCPA → General data → reason for encounter", "HCPA", "General data", "reason for encounter", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_02_state_rj_and_quimioterapia",
        "form_state": {
            "criteria": [
                crit(FK_STATE, "=", "RIO DE JANEIRO", "HCPA", "General data", "State"),
                crit(FK_REASON, "=", "QUIMIOTERAPIA", "HCPA", "General data", "reason for encounter")
            ],
            "output_fields": [
                out(FK_STATE, "HCPA → General data → State", "HCPA", "General data", "State", "DV_CODED_TEXT"),
                out(FK_REASON, "HCPA → General data → reason for encounter", "HCPA", "General data", "reason for encounter", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_03_age_gt_60_and_state_pr",
        "form_state": {
            "criteria": [
                crit(FK_AGE, ">", 60, "HCPA", "General data", "patient age"),
                crit(FK_STATE, "=", "PARANÁ", "HCPA", "General data", "State")
            ],
            "output_fields": [
                out(FK_AGE, "HCPA → General data → patient age", "HCPA", "General data", "patient age", "DV_COUNT"),
                out(FK_STATE, "HCPA → General data → State", "HCPA", "General data", "State", "DV_CODED_TEXT")
            ],
            "sort": sort_spec(FK_AGE, "desc", "HCPA", "General data", "patient age"),
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_04_chemo_tmx_and_duration_gt_12",
        "form_state": {
            "criteria": [
                crit(FK_CHEMO_SCHEMA, "contains", "TMX", "HCPA", "chemotherapy", "schema"),
                crit(FK_CHEMO_DURATION, ">", 12, "HCPA", "chemotherapy", "duration of treatment")
            ],
            "output_fields": [
                out(FK_CHEMO_SCHEMA, "HCPA → chemotherapy → schema", "HCPA", "chemotherapy", "schema", "DV_TEXT"),
                out(FK_CHEMO_DURATION, "HCPA → chemotherapy → duration of treatment", "HCPA", "chemotherapy", "duration of treatment", "DV_QUANTITY")
            ],
            "sort": sort_spec(FK_CHEMO_DURATION, "desc", "HCPA", "chemotherapy", "duration of treatment"),
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_05_problem_c50_9_and_stage_3",
        "form_state": {
            "criteria": [
                crit(FK_PROBLEM, "contains", "C50.9", "Problem/Diagnosis", "(no cluster)", "Problem"),
                crit(FK_CLIN_STAGE, "=", "3", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Clinical (cTNM)", "Clinical staging")
            ],
            "output_fields": [
                out(FK_PROBLEM, "Problem/Diagnosis → Problem", "Problem/Diagnosis", "(no cluster)", "Problem", "DV_CODED_TEXT"),
                out(FK_CLIN_STAGE, "Problem/Diagnosis → Tumour - TNM Cancer staging / Clinical (cTNM) → Clinical staging", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Clinical (cTNM)", "Clinical staging", "DV_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_06_problem_c53_9_and_procedure_radio",
        "form_state": {
            "criteria": [
                crit(FK_PROBLEM, "contains", "C53.9", "Problem/Diagnosis", "(no cluster)", "Problem"),
                crit(FK_PROCEDURE, "contains", "RADIOTERAPIA", "Procedure undertaken", "(no cluster)", "Procedure")
            ],
            "output_fields": [
                out(FK_PROBLEM, "Problem/Diagnosis → Problem", "Problem/Diagnosis", "(no cluster)", "Problem", "DV_CODED_TEXT"),
                out(FK_PROCEDURE, "Procedure undertaken → Procedure", "Procedure undertaken", "(no cluster)", "Procedure", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_07_discharge_evasao_and_state_sp",
        "form_state": {
            "criteria": [
                crit(FK_DISCHARGE_REASON, "contains", "evasão", "Patient discharge", "(no cluster)", "reason for discharge"),
                crit(FK_STATE, "=", "SÃO PAULO", "HCPA", "General data", "State")
            ],
            "output_fields": [
                out(FK_DISCHARGE_REASON, "Patient discharge → reason for discharge", "Patient discharge", "(no cluster)", "reason for discharge", "DV_CODED_TEXT"),
                out(FK_STATE, "HCPA → General data → State", "HCPA", "General data", "State", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_08_path_grade_unknown_and_problem_c50_9",
        "form_state": {
            "criteria": [
                crit(FK_PATH_GRADE, "is_unknown", None, "Problem/Diagnosis", "Tumour - TNM Cancer staging / Pathological (pTNM)", "Histopathological grading (G)"),
                crit(FK_PROBLEM, "contains", "C50.9", "Problem/Diagnosis", "(no cluster)", "Problem")
            ],
            "output_fields": [
                out(FK_PATH_GRADE, "Problem/Diagnosis → Tumour - TNM Cancer staging / Pathological (pTNM) → Histopathological grading (G)", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Pathological (pTNM)", "Histopathological grading (G)", "NULL_FLAVOUR"),
                out(FK_PROBLEM, "Problem/Diagnosis → Problem", "Problem/Diagnosis", "(no cluster)", "Problem", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_09_topography_c50_9_and_lymph_true",
        "form_state": {
            "criteria": [
                crit(FK_TOPOGRAPHY, "contains", "C50.9", "Problem/Diagnosis", "Tumour - TNM Cancer staging", "topography"),
                crit(FK_LYMPH, "=", "true", "Problem/Diagnosis", "(no cluster)", "Invaded regional linphonodes")
            ],
            "output_fields": [
                out(FK_TOPOGRAPHY, "Problem/Diagnosis → Tumour - TNM Cancer staging → topography", "Problem/Diagnosis", "Tumour - TNM Cancer staging", "topography", "DV_CODED_TEXT"),
                out(FK_LYMPH, "Problem/Diagnosis → Invaded regional linphonodes", "Problem/Diagnosis", "(no cluster)", "Invaded regional linphonodes", "DV_BOOLEAN")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "medium_10_radio_start_after_2011",
        "form_state": {
            "criteria": [
                crit(FK_REASON, "=", "RADIOTERAPIA", "HCPA", "General data", "reason for encounter"),
                crit(FK_RADIO_START, ">", "2011-01-01", "HCPA", "radiotherapy", "date of beginning of radiotherapy")
            ],
            "output_fields": [
                out(FK_REASON, "HCPA → General data → reason for encounter", "HCPA", "General data", "reason for encounter", "DV_CODED_TEXT"),
                out(FK_RADIO_START, "HCPA → radiotherapy → date of beginning of radiotherapy", "HCPA", "radiotherapy", "date of beginning of radiotherapy", "DV_DATE")
            ],
            "sort": sort_spec(FK_RADIO_START, "desc", "HCPA", "radiotherapy", "date of beginning of radiotherapy"),
            "advanced": ADV_DEFAULT
        }
    }
])

# =========================================================
# 10 HARD / SPECIALIZED QUERIES
# =========================================================
queries.extend([
    {
        "name": "hard_01_transplant_true_and_number_one",
        "form_state": {
            "criteria": [
                crit(FK_TRANSPLANT_IND, "=", "true", "HCPA", "transplantation", "indicator of transplantation"),
                crit(FK_TRANSPLANT_NUM, "=", 1, "HCPA", "transplantation", "number of transplantations")
            ],
            "output_fields": [
                out(FK_TRANSPLANT_IND, "HCPA → transplantation → indicator of transplantation", "HCPA", "transplantation", "indicator of transplantation", "DV_BOOLEAN"),
                out(FK_TRANSPLANT_NUM, "HCPA → transplantation → number of transplantations", "HCPA", "transplantation", "number of transplantations", "DV_COUNT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_02_renal_dialysis_known_ultrasound_false",
        "form_state": {
            "criteria": [
                crit(FK_DIALYSIS_DATE, "is_known", None, "HCPA", "renal therapy", "date of first dialysis"),
                crit(FK_ULTRASOUND, "=", "false", "HCPA", "renal therapy", "abdominal ultrasonography")
            ],
            "output_fields": [
                out(FK_DIALYSIS_DATE, "HCPA → renal therapy → date of first dialysis", "HCPA", "renal therapy", "date of first dialysis", "DV_DATE"),
                out(FK_ULTRASOUND, "HCPA → renal therapy → abdominal ultrasonography", "HCPA", "renal therapy", "abdominal ultrasonography", "DV_BOOLEAN")
            ],
            "sort": sort_spec(FK_DIALYSIS_DATE, "desc", "HCPA", "renal therapy", "date of first dialysis"),
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_03_bari_followup_gt_6_bmi_gt_40",
        "form_state": {
            "criteria": [
                crit(FK_FOLLOWUP, ">", 6, "Bariatric surgery evaluation", "(no cluster)", "duration of follow-up (months)"),
                crit(FK_BMI, ">", 40, "Body mass index", "(no cluster)", "Body Mass Index")
            ],
            "output_fields": [
                out(FK_FOLLOWUP, "Bariatric surgery evaluation → duration of follow-up (months)", "Bariatric surgery evaluation", "(no cluster)", "duration of follow-up (months)", "DV_COUNT"),
                out(FK_BMI, "Body mass index → Body Mass Index", "Body mass index", "(no cluster)", "Body Mass Index", "DV_QUANTITY")
            ],
            "sort": sort_spec(FK_FOLLOWUP, "desc", "Bariatric surgery evaluation", "(no cluster)", "duration of follow-up (months)"),
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_04_state_sp_reason_quimio_age_gt_60",
        "form_state": {
            "criteria": [
                crit(FK_STATE, "=", "SÃO PAULO", "HCPA", "General data", "State"),
                crit(FK_REASON, "=", "QUIMIOTERAPIA", "HCPA", "General data", "reason for encounter"),
                crit(FK_AGE, ">", 60, "HCPA", "General data", "patient age")
            ],
            "output_fields": [
                out(FK_STATE, "HCPA → General data → State", "HCPA", "General data", "State", "DV_CODED_TEXT"),
                out(FK_AGE, "HCPA → General data → patient age", "HCPA", "General data", "patient age", "DV_COUNT"),
                out(FK_REASON, "HCPA → General data → reason for encounter", "HCPA", "General data", "reason for encounter", "DV_CODED_TEXT")
            ],
            "sort": sort_spec(FK_AGE, "desc", "HCPA", "General data", "patient age"),
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_05_state_rj_reason_radio_problem_c53_9",
        "form_state": {
            "criteria": [
                crit(FK_STATE, "=", "RIO DE JANEIRO", "HCPA", "General data", "State"),
                crit(FK_REASON, "=", "RADIOTERAPIA", "HCPA", "General data", "reason for encounter"),
                crit(FK_PROBLEM, "contains", "C53.9", "Problem/Diagnosis", "(no cluster)", "Problem")
            ],
            "output_fields": [
                out(FK_STATE, "HCPA → General data → State", "HCPA", "General data", "State", "DV_CODED_TEXT"),
                out(FK_REASON, "HCPA → General data → reason for encounter", "HCPA", "General data", "reason for encounter", "DV_CODED_TEXT"),
                out(FK_PROBLEM, "Problem/Diagnosis → Problem", "Problem/Diagnosis", "(no cluster)", "Problem", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_06_problem_c50_9_stage_3_lymph_true",
        "form_state": {
            "criteria": [
                crit(FK_PROBLEM, "contains", "C50.9", "Problem/Diagnosis", "(no cluster)", "Problem"),
                crit(FK_CLIN_STAGE, "=", "3", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Clinical (cTNM)", "Clinical staging"),
                crit(FK_LYMPH, "=", "true", "Problem/Diagnosis", "(no cluster)", "Invaded regional linphonodes")
            ],
            "output_fields": [
                out(FK_PROBLEM, "Problem/Diagnosis → Problem", "Problem/Diagnosis", "(no cluster)", "Problem", "DV_CODED_TEXT"),
                out(FK_CLIN_STAGE, "Problem/Diagnosis → Tumour - TNM Cancer staging / Clinical (cTNM) → Clinical staging", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Clinical (cTNM)", "Clinical staging", "DV_TEXT"),
                out(FK_LYMPH, "Problem/Diagnosis → Invaded regional linphonodes", "Problem/Diagnosis", "(no cluster)", "Invaded regional linphonodes", "DV_BOOLEAN")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_07_chemo_tmx_duration_gt_12_start_after_2011",
        "form_state": {
            "criteria": [
                crit(FK_CHEMO_SCHEMA, "contains", "TMX", "HCPA", "chemotherapy", "schema"),
                crit(FK_CHEMO_DURATION, ">", 12, "HCPA", "chemotherapy", "duration of treatment"),
                crit(FK_CHEMO_START, ">", "2011-01-01", "HCPA", "chemotherapy", "date of beginning of chemotherapy")
            ],
            "output_fields": [
                out(FK_CHEMO_SCHEMA, "HCPA → chemotherapy → schema", "HCPA", "chemotherapy", "schema", "DV_TEXT"),
                out(FK_CHEMO_DURATION, "HCPA → chemotherapy → duration of treatment", "HCPA", "chemotherapy", "duration of treatment", "DV_QUANTITY"),
                out(FK_CHEMO_START, "HCPA → chemotherapy → date of beginning of chemotherapy", "HCPA", "chemotherapy", "date of beginning of chemotherapy", "DV_DATE")
            ],
            "sort": sort_spec(FK_CHEMO_START, "desc", "HCPA", "chemotherapy", "date of beginning of chemotherapy"),
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_08_procedure_radio_and_irrad1_c50_9",
        "form_state": {
            "criteria": [
                crit(FK_PROCEDURE, "contains", "RADIOTERAPIA", "Procedure undertaken", "(no cluster)", "Procedure"),
                crit(FK_IRRAD1, "contains", "C50.9", "Procedure undertaken", "(no cluster)", "irradiated area 1")
            ],
            "output_fields": [
                out(FK_PROCEDURE, "Procedure undertaken → Procedure", "Procedure undertaken", "(no cluster)", "Procedure", "DV_CODED_TEXT"),
                out(FK_IRRAD1, "Procedure undertaken → irradiated area 1", "Procedure undertaken", "(no cluster)", "irradiated area 1", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_09_discharge_date_unknown_reason_alta",
        "form_state": {
            "criteria": [
                crit(FK_DISCHARGE_DATE, "is_unknown", None, "Patient discharge", "(no cluster)", "date of discharge"),
                crit(FK_DISCHARGE_REASON, "contains", "Alta", "Patient discharge", "(no cluster)", "reason for discharge")
            ],
            "output_fields": [
                out(FK_DISCHARGE_DATE, "Patient discharge → date of discharge", "Patient discharge", "(no cluster)", "date of discharge", "NULL_FLAVOUR"),
                out(FK_DISCHARGE_REASON, "Patient discharge → reason for discharge", "Patient discharge", "(no cluster)", "reason for discharge", "DV_CODED_TEXT")
            ],
            "sort": None,
            "advanced": ADV_DEFAULT
        }
    },
    {
        "name": "hard_10_topography_c50_9_path_grade_unknown_path_date_after_2010",
        "form_state": {
            "criteria": [
                crit(FK_TOPOGRAPHY, "contains", "C50.9", "Problem/Diagnosis", "Tumour - TNM Cancer staging", "topography"),
                crit(FK_PATH_GRADE, "is_unknown", None, "Problem/Diagnosis", "Tumour - TNM Cancer staging / Pathological (pTNM)", "Histopathological grading (G)"),
                crit(FK_PATH_DATE, ">", "2010-01-01", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Pathological (pTNM)", "date of pathological identification")
            ],
            "output_fields": [
                out(FK_TOPOGRAPHY, "Problem/Diagnosis → Tumour - TNM Cancer staging → topography", "Problem/Diagnosis", "Tumour - TNM Cancer staging", "topography", "DV_CODED_TEXT"),
                out(FK_PATH_GRADE, "Problem/Diagnosis → Tumour - TNM Cancer staging / Pathological (pTNM) → Histopathological grading (G)", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Pathological (pTNM)", "Histopathological grading (G)", "NULL_FLAVOUR"),
                out(FK_PATH_DATE, "Problem/Diagnosis →   Tumour - TNM Cancer staging / Pathological (pTNM) → date of pathological identification", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Pathological (pTNM)", "date of pathological identification", "DV_DATE")
            ],
            "sort": sort_spec(FK_PATH_DATE, "desc", "Problem/Diagnosis", "Tumour - TNM Cancer staging / Pathological (pTNM)", "date of pathological identification"),
            "advanced": ADV_DEFAULT
        }
    }
])

assert len(queries) == 30, f"Expected 30 queries, found {len(queries)}"

out_path = Path("query_cases_30.json")
with out_path.open("w", encoding="utf-8") as f:
    json.dump(queries, f, indent=2, ensure_ascii=False)

print(f"[OK] Wrote {len(queries)} queries to {out_path.resolve()}")