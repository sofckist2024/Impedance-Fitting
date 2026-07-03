"""Round-trip self test: generate synthetic data, fit it, check recovery.

Run:  python selftest.py
"""
import numpy as np

from impedance_fit import (
    parse_z_file,
    fit_impedance,
    circuit_impedance,
    remove_inductance,
)

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

    # --- inductance-correction round trip ---------------------------------- #
    corr = remove_inductance(data, res, weighting="modulus")
    w = data.omega
    # the corrected imaginary part must equal measured - w*L exactly
    imag_ok = np.allclose(corr.data_corr.z_imag, data.z_imag - w * corr.L)
    # re-fit must find ~no inductance left and recover Rs / Rp
    L_left = float(corr.fit.params[0])
    Rp_true = TRUE["R1"] + TRUE["R2"]
    rs_err = abs(corr.Rs - TRUE["Rs"]) / TRUE["Rs"] * 100
    rp_err = abs(corr.Rp_total - Rp_true) / Rp_true * 100
    print("\n-- inductance correction --")
    print(f"L removed        : {corr.L:.4g} H   (residual after refit {L_left:.2e} H)")
    print(f"Rs   true {TRUE['Rs']:8.4g}  corrected {corr.Rs:8.4g}   rel.err {rs_err:6.2f}%")
    print(f"Rp   true {Rp_true:8.4g}  corrected {corr.Rp_total:8.4g}   rel.err {rp_err:6.2f}%")
    corr_ok = imag_ok and rs_err < 5 and rp_err < 5 and L_left < 1e-20

    all_ok = ok and res.success and corr_ok
    print("\nRESULT:", "PASS" if all_ok else "CHECK")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
