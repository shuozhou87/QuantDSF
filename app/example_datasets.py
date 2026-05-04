#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Curated manuscript example datasets.

These examples are intentionally limited to datasets used in the manuscript so
reviewers can reproduce the major use cases without browsing the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ExampleDataset:
    id: str
    label: str
    files: tuple[str, ...]
    method: str = "auc"
    channel: str = "ratio"
    thermodynamic_method: str = "isothermal"
    dual_peak: bool = False


MANUSCRIPT_EXAMPLE_DATASETS: tuple[ExampleDataset, ...] = (
    ExampleDataset(
        id="fig1_mpro_screen",
        label="Mpro inhibitor screen",
        files=("SP/MPRO-SCREENING.zip",),
        method="auc",
        channel="ratio",
    ),
    ExampleDataset(
        id="fig2_mpro_boceprevir",
        label="Mpro-Boceprevir weak binder",
        files=("SP/100nM MPRO+5uM BOCEPREVIR_SP_052225.zip",),
        method="boltzmann",
        channel="ratio",
    ),
    ExampleDataset(
        id="fig3a_mpro_nirmatrelvir",
        label="Mpro-Nirmatrelvir dose response",
        files=("DOSE/Nirmatrelvir0.2.zip",),
        method="auc",
        channel="ratio",
    ),
    ExampleDataset(
        id="fig3b_fig5_rpa_ssdna",
        label="RPA-ssDNA dose response and thermodynamics",
        files=("DOSE/RPA-SSDNA.zip",),
        method="auc",
        channel="330",
    ),
    ExampleDataset(
        id="fig3c_psma_zn",
        label="PSMA-Zn dose response",
        files=("DOSE/PSMA-ZN-DOSE.zip",),
        method="auc",
        channel="ratio",
    ),
    ExampleDataset(
        id="fig3d_lamp2_cholesterol",
        label="LAMP2-Cholesterol deconvolution",
        files=("DOSE/Lamp2-Cholesterol-dose.zip",),
        method="derivative",
        channel="330",
        dual_peak=True,
    ),
    ExampleDataset(
        id="fig4_bca2_furosemide",
        label="bCAII-Furosemide fluorescence quenching",
        files=("SFQ/CA2-Fur-DOSE-011526.zip",),
        method="auc",
        channel="330",
    ),
    ExampleDataset(
        id="fig4_hsa_furosemide",
        label="HSA-Furosemide fluorescence quenching",
        files=("SFQ/HSA_Furosemide_dose_012326.zip",),
        method="auc",
        channel="330",
    ),
    ExampleDataset(
        id="fig4_boiled_hsa_furosemide",
        label="denatured HSA-Furosemide control",
        files=("SFQ/Molten_HSA_Furosemide_dose_012326.zip",),
        method="auc",
        channel="330",
    ),
    ExampleDataset(
        id="supp4_mpro_nirmatrelvir_vanthoff",
        label="Mpro-Nirmatrelvir Van't Hoff thermodynamics",
        files=("DOSE/Mpro-Nir-5C.zip",),
        method="boltzmann",
        channel="ratio",
    ),
    ExampleDataset(
        id="fig6a_mz1_single_point",
        label="MZ1 ternary complex single point",
        files=("SP/VCB+BD2+MZ1_CROSS_ANALYSIS_SINGLE_POINT.zip",),
        method="derivative",
        channel="330",
    ),
    ExampleDataset(
        id="fig6b_vhl_protac_screen",
        label="VHL PROTAC screen at 100 nM",
        files=("SP/VCB_BRD3BD2_SINGLE_POINT_CORE_100nM.zip",),
        method="boltzmann",
        channel="330",
    ),
    ExampleDataset(
        id="fig6c_mz1_binary_ternary",
        label="MZ1 binary/ternary dose response",
        files=(
            "DOSE/VCB-MZ1-BINARY-DOSE-051525.zip",
            "DOSE/1uM bd2+1uM VCB + MZ1_TERNARY_DOSE-051625.zip",
        ),
        method="auc",
        channel="330",
    ),
    ExampleDataset(
        id="fig6d_crbn_739_binary_ternary",
        label="CRBN-739 binary/ternary dose response",
        files=(
            "DOSE/CRBN_739_BINARY_DOSE.zip",
            "DOSE/CRBN_BCLXL_TERNARY_739_DOSE.zip",
        ),
        method="auc",
        channel="330",
    ),
    ExampleDataset(
        id="fig7a_753b_bcl2",
        label="753b/VCB/BCL-2 ternary dose response",
        files=("DOSE/BCL2+VCB+753B_TERNARY_DOSE_051625.zip",),
        method="boltzmann",
        channel="330",
    ),
    ExampleDataset(
        id="fig7b_753b_bclxl",
        label="753b/VCB/BCL-xL ternary dose response",
        files=("DOSE/BCLXL+VCB+753B_TERNARY_DOSE_051625.zip",),
        method="boltzmann",
        channel="330",
    ),
    ExampleDataset(
        id="fig7c_dt2216_bcl2",
        label="DT2216/VCB/BCL-2 ternary dose response",
        files=("DOSE/BCL2+VCB+DT2216_TERNARY_DOSE_051625.zip",),
        method="boltzmann",
        channel="330",
    ),
    ExampleDataset(
        id="fig7d_dt2216_bclxl",
        label="DT2216/VCB/BCL-xL ternary dose response",
        files=("DOSE/BCLXL+VCB+DT2216_TERNARY_DOSE_051625.zip",),
        method="boltzmann",
        channel="330",
    ),
)


def get_example_dataset_options() -> list[dict[str, str]]:
    return [{"label": dataset.label, "value": dataset.id} for dataset in MANUSCRIPT_EXAMPLE_DATASETS]


def get_example_dataset(dataset_id: str) -> ExampleDataset | None:
    for dataset in MANUSCRIPT_EXAMPLE_DATASETS:
        if dataset.id == dataset_id:
            return dataset
    return None


def resolve_dataset_files(dataset: ExampleDataset, project_root: Path) -> Iterable[Path]:
    sample_root = project_root / "SampleDataSets"
    for relative_path in dataset.files:
        yield sample_root / relative_path
