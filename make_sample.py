"""Generate a synthetic ZView-style .z file for testing the fitter.

True circuit:  L - Rs - (R1-CPE1) - (R2-CPE2)
"""
import numpy as np

# ground-truth parameters
L = 1.0e-6          # H
Rs = 10.0           # Ohm
R1, Q1, n1 = 100.0, 2.0e-5, 0.85
R2, Q2, n2 = 300.0, 1.0e-3, 0.75

f = np.logspace(6, -1, 60)          # 1 MHz -> 0.1 Hz
w = 2 * np.pi * f
jw = 1j * w

Z = 1j * w * L + Rs
Z += R1 / (1 + R1 * Q1 * jw ** n1)
Z += R2 / (1 + R2 * Q2 * jw ** n2)

# add 0.5 % noise
rng = np.random.default_rng(0)
Z = Z * (1 + 0.005 * rng.standard_normal(Z.shape)) \
      + 1j * 0.005 * np.abs(Z) * rng.standard_normal(Z.shape)

with open("sample.z", "w", encoding="utf-8") as fh:
    fh.write("ZPlot2- SCRIBNER ASSOCIATES INC.- 3.1c (synthetic)\n")
    fh.write("  Synthetic test spectrum: L-Rs-(R1-CPE1)-(R2-CPE2)\n")
    fh.write("End Comments\n")
    # columns: Time, Freq, Ampl, Bias, Z', Z''  (standard ZView layout)
    for i, (fi, zi) in enumerate(zip(f, Z)):
        fh.write(f"{i*1.0:.4g},{fi:.6g},0,0,{zi.real:.6g},{zi.imag:.6g}\n")

print("wrote sample.z with", len(f), "points")
print("true params: L=%.3g Rs=%.3g R1=%.3g Q1=%.3g n1=%.3g R2=%.3g Q2=%.3g n2=%.3g"
      % (L, Rs, R1, Q1, n1, R2, Q2, n2))
