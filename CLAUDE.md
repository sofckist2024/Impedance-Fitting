# 임피던스 피팅 (EIS Equivalent-Circuit Fitting)

임피던스(EIS) 데이터를 등가회로로 피팅하는 Streamlit 웹 앱.

## 등가회로 모델

```
L – Rs – (R1-CPE1) – (R2-CPE2) – … – (Rn-CPEn)
```

Z(ω) = jωL + Rs + Σ Rᵢ / (1 + Rᵢ Qᵢ (jω)^nᵢ),  CPE: Z = 1/(Q(jω)^n)

## 파일 구조

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit UI. 업로드 → 열 매핑 → element 개수 선택 → 피팅 → Nyquist/Bode 그래프 · 결과표 · CSV 다운로드 |
| `impedance_fit.py` | 핵심 로직. `.z` 파서, 회로 모델(`circuit_impedance`), 초기값(`initial_guess`), 최소자승 피팅(`fit_impedance`) |
| `make_sample.py` | 테스트용 합성 `.z` 파일(`sample.z`) 생성 |
| `selftest.py` | 합성 데이터로 피팅 정확도 자체 검증 (PASS/FAIL) |

## 실행

```powershell
cd "F:\프로그램\임피던스 피팅"
pip install -r requirements.txt
streamlit run app.py          # 또는 임피던스_피팅_실행.bat
```

## 개발 메모

- Python 3.12, scipy `least_squares`(`x_scale="jac"`)로 피팅. 경계: L,Rs,R,Q ≥ 0, 0 ≤ n ≤ 1.
- 가중치: `modulus`(1/|Z|, EIS 표준) · `proportional` · `unit`.
- `.z` 파서는 ZView/ZPlot export의 `End Comments` 이후 숫자 블록에서 표준 열 배치(4:Z', 5:Z'')를 자동 인식. 3열 텍스트도 지원. 열 배치가 다르면 UI에서 수동 지정.
- 그래프는 **Plotly** 인터랙티브(드래그 확대·휠 줌·pan). Nyquist는 `scaleanchor`로 등비율. 헬퍼 `nyquist_fig`/`bode_fig`(app.py).
- **인덕턴스 보정**: `remove_inductance` — 피팅 L만 뺀 뒤 `fit_impedance(fix_L=True)`로 재피팅해 Rs·Rp 재추출. 고정 파라미터는 야코비안 0열이라 공분산 계산 시 감도 있는 열만 사용.
- **고주파 꼬임 제외**: `detect_hf_artifact` — 인덕턴스 수직선(Z'≈Rs)에서 벗어나 꼬이는 최고주파 구간을 keep-mask로 제외. `subset()`으로 부분집합 만들어 피팅. UI 사이드바 ‘3. 고주파 처리’에서 on/off·허용폭 조절.
- 코드 변경 후에는 `python selftest.py` 로 회귀 확인(피팅·인덕턴스 보정·고주파 감지 모두 PASS).
- 코드/UI 문자열은 한국어. 기존 스타일(주석 밀도, 네이밍) 유지.
