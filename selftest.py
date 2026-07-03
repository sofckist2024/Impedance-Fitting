"""Round-trip self test: generate synthetic data, fit it, check recovery.

Run:  python selftest.py
"""
import numpy as np

from impedance_fit import parse_z_file, fit_impedance, circuit_impedance

TRUE = dict(L=1.0e-6, Rs=10.0,
            R1=100.0, Q1=2.0e-5, n1=0.85,
            R2=300.0, Q2=1.0e-3, n2=0.75)


def build_z_text():
    f = np.logspace(6, -1, 60)
    w = 2 * np.pi * f
    jw = 1j * w
    Z = 1j * w * TRUE["L"] + TRUE["Rs"]
    Z += TRUE["R1"] / (1 + TRUE["R1"] * TRUE["Q1"] * jw ** TRUE["n1"])
    Z += TRUE["R2"] / (1 + TRUE["R2"] * TRUE["Q2"] * jw ** TRUE["n2"])
    lines = ["ZPlot2- test", "End Comments"]
    for i, (fi, zi) in enumerate(zip(f, Z)):
        lines.append(f"{i},{fi:.8g},0,0,{zi.real:.8g},{zi.imag:.8g}")
    return "\n".join(lines)


def main():
    data = parse_z_file(build_z_text())
    assert len(data) == 60, f"expected 60 points, got {len(data)}"

    res = fit_impedance(data, n_elem=2, weighting="modulus")
    got = dict(zip(
        ["L", "Rs", "R1", "Q1", "n1", "R2", "Q2", "n2"],
        res.params,
    ))

    print(f"success={res.success}  chi2={res.chi_square:.3e}  chi2/dof={res.chi_square_reduced:.3e}")
    print(f"{'param':6s} {'true':>12s} {'fit':>12s} {'rel.err%':>10s}")
    ok = True
    for k in ["L", "Rs", "R1", "Q1", "n1", "R2", "Q2", "n2"]:
        rel = abs(got[k] - TRUE[k]) / abs(TRUE[k]) * 100
        flag = "" if rel < 5 else "  <-- off"
        if rel >= 5:
            ok = False
        print(f"{k:6s} {TRUE[k]:12.5g} {got[k]:12.5g} {rel:10.2f}{flag}")

    # residual sanity
    zf = circuit_impedance(res.params, data.freq, 2)
    rms = np.sqrt(np.mean(np.abs(data.z - zf) ** 2)) / np.mean(np.abs(data.z)) * 100
    print(f"\nrelative RMS residual: {rms:.3f}%")
    print("RESULT:", "PASS" if ok and res.success else "CHECK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
