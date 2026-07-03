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
- 코드 변경 후에는 `python selftest.py` 로 피팅 회귀 확인.
- 코드/UI 문자열은 한국어. 기존 스타일(주석 밀도, 네이밍) 유지.
