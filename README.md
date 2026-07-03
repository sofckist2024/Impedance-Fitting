# 임피던스 피팅 (EIS Equivalent-Circuit Fitting)

임피던스(EIS) 데이터를 아래 등가회로로 피팅하는 Streamlit 웹 앱입니다.

```
L – Rs – (R1-CPE1) – (R2-CPE2) – … – (Rn-CPEn)
```

$$Z(\omega) = j\omega L + R_s + \sum_i \frac{R_i}{1 + R_i Q_i (j\omega)^{n_i}}$$

- **CPE**: $Z_{CPE} = 1 / (Q\,(j\omega)^n)$
- ZView/ZPlot `.z` 파일을 업로드하고, (R-CPE) element 개수를 선택하면 자동 피팅합니다.

## 구성 파일

| 파일 | 설명 |
|------|------|
| `app.py` | Streamlit UI (업로드 · element 개수 선택 · 그래프 · 결과 표) |
| `impedance_fit.py` | 핵심 로직 (`.z` 파서 · 회로 모델 · 최소자승 피팅) |
| `make_sample.py` | 테스트용 합성 `.z` 파일 생성 |
| `selftest.py` | 합성 데이터로 피팅 정확도 자체 검증 |
| `requirements.txt` | 의존 패키지 |

## 설치 & 실행

Python 3.9+ 가 필요합니다.

```powershell
cd "F:\프로그램\임피던스 피팅"
pip install -r requirements.txt
streamlit run app.py
```

브라우저가 자동으로 열립니다(기본 http://localhost:8501).

### 자체 검증 (선택)

```powershell
python make_sample.py   # sample.z 생성
python selftest.py      # 피팅 정확도 확인 (PASS 출력)
```

## 사용법

1. 좌측 사이드바에서 `.z` 파일 업로드
2. **(R-CPE) element 개수** 선택 (1~8)
3. 가중치 선택 (기본 `modulus` = 1/|Z|, EIS 표준)
4. **피팅 실행 ▶** 클릭
5. Nyquist · Bode 그래프에 피팅 곡선이 겹쳐지고, 파라미터 값과 표준오차(χ²)가 표로 표시됩니다.
6. 파라미터 / 피팅 곡선을 CSV로 다운로드할 수 있습니다.

## `.z` 파일 형식

ZView/ZPlot 표준 export 를 가정합니다. `End Comments` 이후의 숫자 블록에서
표준 열 배치(`0:Time 1:Freq 2:Ampl 3:Bias 4:Z' 5:Z''`)를 자동 인식합니다.
- 3열 텍스트(`freq, Z', Z''`)도 자동 인식됩니다.
- 열 배치가 다르면 앱의 **"열 매핑 확인/수정"** 에서 직접 지정할 수 있습니다.
- 파일이 $-Z''$ 로 저장된 경우 **"Z'' 부호 반전"** 체크박스를 사용하세요.

## 파라미터 초기값 / 경계

- `Rs` ≈ 고주파 실수 절편, `L` ≈ 고주파 유도성 성분, `Rp` 를 element 수로 분배
- 각 element 의 특성 주파수를 측정 주파수 범위에 로그 균등 분포
- 경계: `L,Rs,R,Q ≥ 0`, `0 ≤ n ≤ 1`
- `x_scale="jac"` 로 파라미터 스케일 자동 보정(Q 가 여러 자릿수 차이 나도 안정)
