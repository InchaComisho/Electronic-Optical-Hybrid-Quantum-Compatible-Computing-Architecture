#!/usr/bin/env python3
"""
Theoretical Binary vs Electronic-Optical Hybrid Comparison Simulator

This simulator compares binary symbolic representation with multi-valued
optical / electronic-optical hybrid symbolic representation at a theoretical
model level.

Important framing:
- This is NOT a hardware benchmark.
- This is NOT a FLOPS comparison with real supercomputers.
- This is NOT a quantum advantage simulation.
- This does NOT prove that hybrid optical computing is superior to binary computing.

The goal is narrower:
- quantify how many bits are represented per symbol for a state alphabet of size M,
- estimate how many symbols are needed for a fixed payload,
- expose when multi-valued symbols help or lose after interface overhead,
- compare against a binary baseline under explicit assumptions.

Run:
    python simulator/theoretical_binary_hybrid_comparison.py
    python simulator/theoretical_binary_hybrid_comparison.py --payload-bits 1000000 --max-state 1024
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List


DEFAULT_STATES = [2, 4, 8, 10, 16, 32, 40, 64, 128, 256, 512, 1024]


@dataclass(frozen=True)
class Scenario:
    name: str
    binary_bit_energy: float
    binary_memory_multiplier: float
    binary_latency_per_bit: float
    optical_source_energy: float
    detector_energy: float
    electronic_control_energy: float
    correction_energy_per_bit: float
    optical_latency_per_symbol: float
    correction_latency_per_bit: float


SCENARIOS = [
    Scenario(
        name="low_optical_overhead",
        binary_bit_energy=1.0,
        binary_memory_multiplier=3.0,
        binary_latency_per_bit=1.0,
        optical_source_energy=1.2,
        detector_energy=1.0,
        electronic_control_energy=0.4,
        correction_energy_per_bit=0.08,
        optical_latency_per_symbol=1.5,
        correction_latency_per_bit=0.05,
    ),
    Scenario(
        name="moderate_overhead",
        binary_bit_energy=1.0,
        binary_memory_multiplier=3.0,
        binary_latency_per_bit=1.0,
        optical_source_energy=3.0,
        detector_energy=2.0,
        electronic_control_energy=0.7,
        correction_energy_per_bit=0.20,
        optical_latency_per_symbol=3.0,
        correction_latency_per_bit=0.15,
    ),
    Scenario(
        name="high_optical_overhead",
        binary_bit_energy=1.0,
        binary_memory_multiplier=3.0,
        binary_latency_per_bit=1.0,
        optical_source_energy=8.0,
        detector_energy=5.0,
        electronic_control_energy=1.5,
        correction_energy_per_bit=0.50,
        optical_latency_per_symbol=7.0,
        correction_latency_per_bit=0.35,
    ),
]


@dataclass(frozen=True)
class ComparisonRow:
    scenario: str
    state_count: int
    bits_per_symbol: float
    payload_bits: int
    binary_symbols: int
    hybrid_symbols: int
    ideal_symbol_reduction_x: float
    binary_energy_units: float
    hybrid_energy_units: float
    energy_ratio_hybrid_over_binary: float
    binary_latency_units_serial: float
    hybrid_latency_units: float
    latency_ratio_hybrid_over_binary_serial: float
    note: str


def hybrid_energy_per_symbol(bits_per_symbol: float, scenario: Scenario) -> float:
    return (
        scenario.optical_source_energy
        + scenario.detector_energy
        + scenario.electronic_control_energy
        + scenario.correction_energy_per_bit * bits_per_symbol
    )


def hybrid_latency_per_symbol(bits_per_symbol: float, scenario: Scenario) -> float:
    return scenario.optical_latency_per_symbol + scenario.correction_latency_per_bit * bits_per_symbol


def compare_for_state_count(payload_bits: int, state_count: int, scenario: Scenario) -> ComparisonRow:
    if state_count < 2:
        raise ValueError("state_count must be >= 2")

    bits_per_symbol = math.log2(state_count)
    binary_symbols = payload_bits
    hybrid_symbols = math.ceil(payload_bits / bits_per_symbol)

    # Binary baseline is a simplified serial symbolic baseline with a memory/data-movement multiplier.
    # It is a proxy, not a real supercomputer benchmark.
    binary_energy = payload_bits * scenario.binary_bit_energy * scenario.binary_memory_multiplier
    binary_latency = payload_bits * scenario.binary_latency_per_bit

    hybrid_energy = hybrid_symbols * hybrid_energy_per_symbol(bits_per_symbol, scenario)
    hybrid_latency = hybrid_symbols * hybrid_latency_per_symbol(bits_per_symbol, scenario)

    energy_ratio = hybrid_energy / binary_energy if binary_energy else float("inf")
    latency_ratio = hybrid_latency / binary_latency if binary_latency else float("inf")
    ideal_symbol_reduction = binary_symbols / hybrid_symbols if hybrid_symbols else 0.0

    if state_count == 2:
        note = "Binary reference point."
    elif state_count == 40:
        note = "RGBW x 10-state SCD example; theoretical 5.32 bits/symbol before overhead."
    elif state_count >= 256:
        note = "High state count; practical separability may become difficult under real noise."
    else:
        note = "Theoretical multi-valued symbol model."

    return ComparisonRow(
        scenario=scenario.name,
        state_count=state_count,
        bits_per_symbol=bits_per_symbol,
        payload_bits=payload_bits,
        binary_symbols=binary_symbols,
        hybrid_symbols=hybrid_symbols,
        ideal_symbol_reduction_x=ideal_symbol_reduction,
        binary_energy_units=binary_energy,
        hybrid_energy_units=hybrid_energy,
        energy_ratio_hybrid_over_binary=energy_ratio,
        binary_latency_units_serial=binary_latency,
        hybrid_latency_units=hybrid_latency,
        latency_ratio_hybrid_over_binary_serial=latency_ratio,
        note=note,
    )


def run_comparison(payload_bits: int, state_counts: Iterable[int]) -> List[ComparisonRow]:
    rows: List[ComparisonRow] = []
    for scenario in SCENARIOS:
        for state_count in state_counts:
            rows.append(compare_for_state_count(payload_bits, state_count, scenario))
    return rows


def write_csv(rows: List[ComparisonRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def print_summary(rows: List[ComparisonRow], focus_state: int = 40) -> None:
    print("Theoretical Binary vs Electronic-Optical Hybrid Comparison")
    print("---------------------------------------------------------")
    print("Important: theoretical proxy only; not a hardware benchmark or quantum advantage claim.")
    print()

    for row in rows:
        if row.state_count == focus_state:
            print(f"Scenario: {row.scenario}")
            print(f"  State count: {row.state_count}")
            print(f"  Bits per symbol: {row.bits_per_symbol:.3f}")
            print(f"  Hybrid symbols for payload: {row.hybrid_symbols}")
            print(f"  Ideal symbol reduction vs binary: {row.ideal_symbol_reduction_x:.3f}x")
            print(f"  Hybrid/Binary energy ratio: {row.energy_ratio_hybrid_over_binary:.3f}")
            print(f"  Hybrid/Binary serial-latency ratio: {row.latency_ratio_hybrid_over_binary_serial:.3f}")
            print(f"  Note: {row.note}")
            print()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Theoretical binary vs hybrid state comparison.")
    parser.add_argument("--payload-bits", type=int, default=1_000_000, help="Payload size in bits.")
    parser.add_argument("--states", type=str, default=",".join(map(str, DEFAULT_STATES)), help="Comma-separated state counts.")
    parser.add_argument("--max-state", type=int, default=None, help="Optional max state count; generates powers of two up to this value plus 40.")
    parser.add_argument("--csv", type=Path, default=Path("simulator/results/theoretical_binary_hybrid_comparison.csv"), help="CSV output path.")
    return parser


def parse_state_counts(args: argparse.Namespace) -> List[int]:
    if args.max_state is not None:
        if args.max_state < 2:
            raise ValueError("--max-state must be >= 2")
        states = []
        value = 2
        while value <= args.max_state:
            states.append(value)
            value *= 2
        if 40 not in states and args.max_state >= 40:
            states.append(40)
        return sorted(set(states))

    states = [int(x.strip()) for x in args.states.split(",") if x.strip()]
    return sorted(set(states))


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.payload_bits <= 0:
        raise ValueError("--payload-bits must be positive")

    state_counts = parse_state_counts(args)
    rows = run_comparison(args.payload_bits, state_counts)
    write_csv(rows, args.csv)
    print_summary(rows)
    print(f"CSV written to: {args.csv}")


if __name__ == "__main__":
    main()
