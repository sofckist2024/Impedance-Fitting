"""
Streamlit UI for EIS equivalent-circuit fitting.

Model:  L - Rs - (R1-CPE1) - (R2-CPE2) - ... - (Rn-CPEn)

Run with:   streamlit run app.py
"""

import io

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from impedance_fit import (
    parse_z_file,
    preview_columns,
    suggest_columns,
    fit_impedance,
    circuit_impedance,
    initial_guess,
    param_labels,
    remove_inductance,
)

st.set_page_config(page_title="임피던스 피팅", layout="wide")

st.title("임피던스 피팅 (EIS Equivalent-Circuit Fitting)")
st.markdown(
    "등가회로 **L – Rs – (R₁-CPE₁) – (R₂-CPE₂) – …** 로 임피던스 데이터를 피팅합니다.\n\n"
    r"$Z(\omega) = j\omega L + R_s + \sum_i \dfrac{R_i}{1 + R_i Q_i (j\omega)^{n_i}}$"
)

# --------------------------------------------------------------------------- #
#  Sidebar: input
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("1. 데이터 입력")
    up = st.file_uploader("z 파일 업로드 (.z, .txt, .csv)", type=["z", "txt", "csv", "dat"])

    st.header("2. 회로 설정")
    n_elem = st.number_input("(R-CPE) element 개수", min_value=1, max_value=8, value=2, step=1)
    weighting = st.selectbox(
        "가중치 (weighting)",
        ["modulus", "proportional", "unit"],
        index=0,
        help="modulus: 1/|Z| (EIS 표준), proportional: 성분별 1/|Z'|,1/|Z''|, unit: 균등",
    )

if up is None:
    st.info("좌측에서 ZView `.z` 파일(또는 freq, Z', Z'' 텍스트 파일)을 업로드하세요.")
    st.stop()

raw = up.getvalue().decode("utf-8", errors="replace")

# --- column preview / manual override ------------------------------------- #
rows, ncol = preview_columns(raw)
with st.expander("열(column) 매핑 확인 / 수정", expanded=False):
    if rows:
        st.caption("감지된 데이터 미리보기 (열 인덱스는 0부터):")
        st.dataframe(pd.DataFrame(rows, columns=[str(i) for i in range(len(rows[0]))]),
                     use_container_width=True)
    d_f, d_r, d_i = suggest_columns(raw)
    st.caption(f"자동 감지된 열 → 주파수: {d_f}, Z': {d_r}, Z'': {d_i}")
    c1, c2, c3 = st.columns(3)
    col_freq = c1.number_input("주파수 열", 0, max(ncol - 1, 0), min(d_f, ncol - 1))
    col_zr = c2.number_input("Z' (실수) 열", 0, max(ncol - 1, 0), min(d_r, ncol - 1))
    col_zi = c3.number_input("Z'' (허수) 열", 0, max(ncol - 1, 0), min(d_i, ncol - 1))
    flip = st.checkbox("Z'' 부호 반전 (파일이 -Z''로 저장된 경우)", value=False)

try:
    data = parse_z_file(raw, int(col_freq), int(col_zr), int(col_zi))
except Exception as e:  # noqa: BLE001
    st.error(f"파일 파싱 오류: {e}")
    st.stop()

if flip:
    data.z_imag = -data.z_imag

st.success(f"데이터 {len(data)} 점 로드 완료  ·  주파수 {data.freq.min():.3g} – {data.freq.max():.3g} Hz")

# --------------------------------------------------------------------------- #
#  Fit
# --------------------------------------------------------------------------- #
do_fit = st.button("피팅 실행 ▶", type="primary")

if do_fit:
    with st.spinner("피팅 중..."):
        result = fit_impedance(data, int(n_elem), weighting=weighting)
    st.session_state["result"] = result
    st.session_state["n_elem_fit"] = int(n_elem)

result = st.session_state.get("result")
# discard a stale fit that belongs to a previously loaded / differently mapped dataset
if result is not None and len(result.z_fit) != len(data):
    result = None


# --------------------------------------------------------------------------- #
#  Plots
# --------------------------------------------------------------------------- #
def nyquist_ax(ax):
    ax.set_xlabel("Z'  (Ω)")
    ax.set_ylabel("-Z''  (Ω)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)


col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Nyquist")
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(data.z_real, -data.z_imag, "o", ms=4, label="data", color="#1f77b4")
    if result is not None:
        zf = result.z_fit
        ax.plot(zf.real, -zf.imag, "-", lw=2, label="fit", color="#d62728")
    nyquist_ax(ax)
    ax.legend()
    st.pyplot(fig)

with col_right:
    st.subheader("Bode")
    fig2, (axm, axp) = plt.subplots(2, 1, figsize=(5, 5), sharex=True)
    mod = np.abs(data.z)
    phase = np.degrees(np.angle(data.z))
    axm.loglog(data.freq, mod, "o", ms=4, color="#1f77b4", label="data")
    axp.semilogx(data.freq, phase, "o", ms=4, color="#1f77b4")
    if result is not None:
        zf = result.z_fit
        axm.loglog(data.freq, np.abs(zf), "-", lw=2, color="#d62728", label="fit")
        axp.semilogx(data.freq, np.degrees(np.angle(zf)), "-", lw=2, color="#d62728")
    axm.set_ylabel("|Z|  (Ω)")
    axm.grid(True, which="both", alpha=0.3)
    axm.legend()
    axp.set_ylabel("phase (°)")
    axp.set_xlabel("frequency (Hz)")
    axp.grid(True, which="both", alpha=0.3)
    st.pyplot(fig2)


# --------------------------------------------------------------------------- #
#  Results table
# --------------------------------------------------------------------------- #
if result is not None:
    st.subheader("피팅 결과")

    c1, c2, c3 = st.columns(3)
    c1.metric("χ² (weighted SS)", f"{result.chi_square:.4g}")
    c2.metric("χ²/dof", f"{result.chi_square_reduced:.4g}")
    c3.metric("수렴", "성공" if result.success else "경고")

    rows_out = []
    for name, val, err in result.as_rows():
        rel = (err / abs(val) * 100) if (np.isfinite(err) and val != 0) else np.nan
        rows_out.append({"parameter": name, "value": val,
                         "std. error": err, "error %": rel})
    df = pd.DataFrame(rows_out)
    st.dataframe(
        df.style.format({"value": "{:.6g}", "std. error": "{:.3g}", "error %": "{:.2f}"}),
        use_container_width=True,
    )

    if not result.success:
        st.warning(f"최적화 메시지: {result.message}\n\n"
                   "element 개수를 바꾸거나 데이터 품질/열 매핑을 확인해 보세요.")

    # downloadable outputs -------------------------------------------------- #
    csv_params = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("파라미터 CSV 다운로드", csv_params,
                       file_name="fit_parameters.csv", mime="text/csv")

    zf = result.z_fit
    fit_table = pd.DataFrame({
        "freq_Hz": data.freq,
        "Zreal_data": data.z_real,
        "Zimag_data": data.z_imag,
        "Zreal_fit": zf.real,
        "Zimag_fit": zf.imag,
        "residual_real": data.z_real - zf.real,
        "residual_imag": data.z_imag - zf.imag,
    })
    st.download_button("피팅 곡선 CSV 다운로드",
                       fit_table.to_csv(index=False).encode("utf-8-sig"),
                       file_name="fit_curve.csv", mime="text/csv")

    # ----------------------------------------------------------------------- #
    #  Inductance (L) correction
    # ----------------------------------------------------------------------- #
    st.divider()
    st.subheader("인덕턴스(L) 보정")
    st.caption(
        "피팅으로 얻은 인덕턴스 성분 $j\\omega L$ 만 측정값에서 제거한 뒤, "
        "$L=0$ 으로 재피팅하여 오믹 저항 $R_s$ 와 분극 저항 $R_p$ 를 다시 추출합니다. "
        "배선/리드 인덕턴스가 만드는 고주파 꼬리(Nyquist에서 실수축 아래로 내려가는 부분)가 사라집니다."
    )

    do_corr = st.checkbox("인덕턴스 보정 수행", value=False)
    if do_corr:
        # cache: only re-fit when the underlying fit / data actually changed
        corr_key = (tuple(np.round(result.params, 12)), len(data), result.weighting)
        if st.session_state.get("corr_key") != corr_key:
            with st.spinner("인덕턴스 제거 후 재피팅 중..."):
                st.session_state["corr"] = remove_inductance(
                    data, result, weighting=result.weighting)
            st.session_state["corr_key"] = corr_key
        corr = st.session_state["corr"]

        m1, m2, m3 = st.columns(3)
        m1.metric("제거한 L (H)", f"{corr.L:.4g}")
        m2.metric("Rs · 오믹 저항 (Ω)", f"{corr.Rs:.6g}")
        m3.metric("Rp · 분극 저항 합계 (Ω)", f"{corr.Rp_total:.6g}")

        dc = corr.data_corr
        zc_fit = corr.fit.z_fit
        cp_left, cp_right = st.columns(2)

        with cp_left:
            st.markdown("**Nyquist (보정 후)**")
            figc, axc = plt.subplots(figsize=(5, 5))
            axc.plot(data.z_real, -data.z_imag, "o", ms=3, alpha=0.35,
                     color="#888888", label="원본 data")
            axc.plot(dc.z_real, -dc.z_imag, "o", ms=4,
                     color="#1f77b4", label="보정 data")
            axc.plot(zc_fit.real, -zc_fit.imag, "-", lw=2,
                     color="#2ca02c", label="보정 fit")
            nyquist_ax(axc)
            axc.legend()
            st.pyplot(figc)

        with cp_right:
            st.markdown("**Bode (보정 후)**")
            figc2, (axcm, axcp) = plt.subplots(2, 1, figsize=(5, 5), sharex=True)
            axcm.loglog(dc.freq, np.abs(dc.z), "o", ms=4, color="#1f77b4", label="보정 data")
            axcm.loglog(dc.freq, np.abs(zc_fit), "-", lw=2, color="#2ca02c", label="보정 fit")
            axcp.semilogx(dc.freq, np.degrees(np.angle(dc.z)), "o", ms=4, color="#1f77b4")
            axcp.semilogx(dc.freq, np.degrees(np.angle(zc_fit)), "-", lw=2, color="#2ca02c")
            axcm.set_ylabel("|Z|  (Ω)")
            axcm.grid(True, which="both", alpha=0.3)
            axcm.legend()
            axcp.set_ylabel("phase (°)")
            axcp.set_xlabel("frequency (Hz)")
            axcp.grid(True, which="both", alpha=0.3)
            st.pyplot(figc2)

        # before / after comparison of Rs and each Rp -------------------------- #
        comp_rows = [{
            "항목": "Rs (오믹, Ω)",
            "원본 피팅": result.params[1],
            "보정 후": corr.Rs,
            "보정 후 오차": corr.fit.perror[1],
        }]
        for k in range(result.n_elem):
            comp_rows.append({
                "항목": f"R{k + 1} (분극, Ω)",
                "원본 피팅": result.params[2 + 3 * k],
                "보정 후": corr.Rp_list[k],
                "보정 후 오차": corr.fit.perror[2 + 3 * k],
            })
        rp_orig = float(sum(result.params[2 + 3 * k] for k in range(result.n_elem)))
        comp_rows.append({
            "항목": "Rp 합계 (Ω)", "원본 피팅": rp_orig,
            "보정 후": corr.Rp_total, "보정 후 오차": np.nan,
        })
        comp_df = pd.DataFrame(comp_rows)
        st.dataframe(
            comp_df.style.format(
                {"원본 피팅": "{:.6g}", "보정 후": "{:.6g}", "보정 후 오차": "{:.3g}"}),
            use_container_width=True,
        )

        if not corr.fit.success:
            st.warning(f"재피팅 수렴 경고: {corr.fit.message}")

        # downloadable corrected spectrum ------------------------------------- #
        corr_table = pd.DataFrame({
            "freq_Hz": dc.freq,
            "Zreal_corr": dc.z_real,
            "Zimag_corr": dc.z_imag,
            "Zreal_fit": zc_fit.real,
            "Zimag_fit": zc_fit.imag,
        })
        st.download_button("보정 스펙트럼 CSV 다운로드",
                           corr_table.to_csv(index=False).encode("utf-8-sig"),
                           file_name="inductance_corrected.csv", mime="text/csv")
else:
    st.caption("‘피팅 실행’ 을 누르면 결과가 여기에 표시됩니다.")
