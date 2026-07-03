"""
Streamlit UI for EIS equivalent-circuit fitting.

Model:  L - Rs - (R1-CPE1) - (R2-CPE2) - ... - (Rn-CPEn)

Run with:   streamlit run app.py
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from impedance_fit import (
    parse_z_file,
    preview_columns,
    suggest_columns,
    fit_impedance,
    circuit_impedance,
    initial_guess,
    param_labels,
    remove_inductance,
    detect_hf_artifact,
    subset,
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

    st.header("3. 고주파 처리")
    auto_hf = st.checkbox(
        "고주파 꼬임 구간 자동 제외", value=True,
        help="인덕턴스 영향으로 수직으로 올라오는 부분만 남기고, 고주파에서 "
             "수직선에서 벗어나 돌아가며(꼬이며) 나온 구간을 피팅에서 제외합니다.",
    )
    hf_tol = st.slider(
        "수직 판정 허용폭 (아크 대비 %)", 1, 30, 8, disabled=not auto_hf,
        help="Z'가 수직선(Z'≈Rs)에서 이 값(아크 폭 대비 %)보다 더 벗어나면 "
             "'꼬임'으로 보고 제외합니다. 작을수록 더 엄격하게(더 많이) 제외.",
    ) / 100.0

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

# --- high-frequency artifact exclusion ------------------------------------- #
# `keep` marks the points used for fitting; excluded points are the high-freq
# "twist" that curls off the vertical inductive line.
if auto_hf:
    keep = detect_hf_artifact(data, tol_frac=hf_tol)
else:
    keep = np.ones(len(data), dtype=bool)
excl = ~keep
data_fit = subset(data, keep)

if excl.any():
    f_excl = data.freq[excl]
    st.warning(
        f"고주파 꼬임 구간 **{int(excl.sum())}점** 을 피팅에서 제외했습니다 "
        f"(f ≥ {f_excl.min():.3g} Hz). 피팅은 남은 {len(data_fit)}점으로 수행됩니다. "
        "좌측 ‘고주파 처리’에서 끄거나 허용폭을 조절할 수 있습니다."
    )

# --------------------------------------------------------------------------- #
#  Fit
# --------------------------------------------------------------------------- #
do_fit = st.button("피팅 실행 ▶", type="primary")

if do_fit:
    with st.spinner("피팅 중..."):
        result = fit_impedance(data_fit, int(n_elem), weighting=weighting)
    st.session_state["result"] = result
    st.session_state["n_elem_fit"] = int(n_elem)

result = st.session_state.get("result")
# discard a stale fit that belongs to a previously loaded / differently mapped
# dataset (or a changed high-frequency exclusion)
if result is not None and len(result.z_fit) != len(data_fit):
    result = None


# --------------------------------------------------------------------------- #
#  Interactive plots (Plotly: 드래그=확대, 더블클릭=원위치, 휠=확대/축소)
# --------------------------------------------------------------------------- #
PLOT_CONFIG = {"scrollZoom": True, "displaylogo": False,
               "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def nyquist_fig(traces, height=480):
    """traces: list of (name, z_real, z_imag, freq, color, is_line[, symbol])."""
    fig = go.Figure()
    for tr in traces:
        name, zr, zi, freq, color, is_line = tr[:6]
        symbol = tr[6] if len(tr) > 6 else "circle"
        fig.add_trace(go.Scatter(
            x=zr, y=-np.asarray(zi),
            name=name,
            mode="lines" if is_line else "markers",
            line=dict(color=color, width=2),
            marker=dict(color=color, size=7, symbol=symbol),
            customdata=freq,
            hovertemplate="Z'=%{x:.4g} Ω<br>-Z''=%{y:.4g} Ω"
                          "<br>f=%{customdata:.4g} Hz<extra>" + name + "</extra>",
        ))
    fig.update_layout(
        height=height, hovermode="closest", dragmode="zoom",
        margin=dict(l=60, r=20, t=10, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
    )
    fig.update_xaxes(title_text="Z'  (Ω)", showgrid=True, zeroline=False)
    # equal aspect so the arcs keep their true (semi-circular) shape
    fig.update_yaxes(title_text="-Z''  (Ω)", showgrid=True, zeroline=False,
                     scaleanchor="x", scaleratio=1)
    return fig


def bode_fig(series, height=480):
    """series: list of (name, freq, z_complex, color, is_line[, symbol])."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07)
    for s in series:
        name, freq, z, color, is_line = s[:5]
        symbol = s[5] if len(s) > 5 else "circle"
        mode = "lines" if is_line else "markers"
        fig.add_trace(go.Scatter(
            x=freq, y=np.abs(z), name=name, mode=mode,
            line=dict(color=color, width=2), marker=dict(color=color, size=6, symbol=symbol),
            hovertemplate="f=%{x:.4g} Hz<br>|Z|=%{y:.4g} Ω<extra>" + name + "</extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=freq, y=np.degrees(np.angle(z)), name=name, mode=mode,
            line=dict(color=color, width=2), marker=dict(color=color, size=6, symbol=symbol),
            showlegend=False,
            hovertemplate="f=%{x:.4g} Hz<br>phase=%{y:.3g}°<extra>" + name + "</extra>",
        ), row=2, col=1)
    fig.update_layout(
        height=height, hovermode="closest",
        margin=dict(l=60, r=20, t=10, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
    )
    fig.update_xaxes(type="log", showgrid=True)
    fig.update_xaxes(title_text="frequency (Hz)", row=2, col=1)
    fig.update_yaxes(type="log", title_text="|Z| (Ω)", showgrid=True, row=1, col=1)
    fig.update_yaxes(title_text="phase (°)", showgrid=True, row=2, col=1)
    return fig


st.caption("📈 그래프는 **드래그하면 확대**, **더블클릭하면 원위치**, 마우스 휠로도 확대/축소됩니다. "
           "오른쪽 위 도구막대에서 이동(pan)·이미지 저장(PNG)도 할 수 있습니다.")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Nyquist")
    tr = [("data (피팅)", data_fit.z_real, data_fit.z_imag, data_fit.freq, "#1f77b4", False)]
    if excl.any():
        tr.append(("제외 (고주파 꼬임)", data.z_real[excl], data.z_imag[excl],
                   data.freq[excl], "#999999", False, "x"))
    if result is not None:
        zf = result.z_fit
        tr.append(("fit", zf.real, zf.imag, data_fit.freq, "#d62728", True))
    st.plotly_chart(nyquist_fig(tr), use_container_width=True, config=PLOT_CONFIG)

with col_right:
    st.subheader("Bode")
    ser = [("data (피팅)", data_fit.freq, data_fit.z, "#1f77b4", False)]
    if excl.any():
        ser.append(("제외 (고주파 꼬임)", data.freq[excl], data.z[excl],
                    "#999999", False, "x"))
    if result is not None:
        ser.append(("fit", data_fit.freq, result.z_fit, "#d62728", True))
    st.plotly_chart(bode_fig(ser), use_container_width=True, config=PLOT_CONFIG)


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
        "freq_Hz": data_fit.freq,
        "Zreal_data": data_fit.z_real,
        "Zimag_data": data_fit.z_imag,
        "Zreal_fit": zf.real,
        "Zimag_fit": zf.imag,
        "residual_real": data_fit.z_real - zf.real,
        "residual_imag": data_fit.z_imag - zf.imag,
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
        corr_key = (tuple(np.round(result.params, 12)), len(data_fit), result.weighting)
        if st.session_state.get("corr_key") != corr_key:
            with st.spinner("인덕턴스 제거 후 재피팅 중..."):
                st.session_state["corr"] = remove_inductance(
                    data_fit, result, weighting=result.weighting)
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
            # 보정 data 는 아크(–Z'' ≥ 0)만 표시: 고주파의 음수(유도성) 구간은 제외
            arc = dc.z_imag <= 0
            tr_c = [
                ("원본 data", data_fit.z_real, data_fit.z_imag, data_fit.freq, "#b0b0b0", False),
                ("보정 data", dc.z_real[arc], dc.z_imag[arc], dc.freq[arc], "#1f77b4", False),
            ]
            st.plotly_chart(nyquist_fig(tr_c), use_container_width=True, config=PLOT_CONFIG)

        with cp_right:
            st.markdown("**Bode (보정 후)**")
            ser_c = [
                ("보정 data", dc.freq, dc.z, "#1f77b4", False),
            ]
            st.plotly_chart(bode_fig(ser_c), use_container_width=True, config=PLOT_CONFIG)

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
