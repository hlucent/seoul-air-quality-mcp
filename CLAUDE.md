# CLAUDE.md — 서울시 대기환경정보 MCP 확장 작업 지침

## 1. 절대 규칙

- DEVPLAN.md 하나만 먼저 읽고 시작. 다른 문서 재탐색 금지.
- 웹서치 금지 (API 스펙은 DEVPLAN.md에 이미 있음).
- 불확실하면 추측성 재설계 대신 기본값 1개로 구현 후 DEVLOG.md에 "확인 필요"로 기록.
- 동일 오류 최대 3회까지만 재시도. 3회 실패 시 기록하고 사용자에게 보고.
- **이번 작업은 신규 프로젝트가 아니라 기존 `seoul-air-quality-mcp` 저장소에 대한
  확장 작업이다.** 새 폴더/새 저장소를 만들지 않는다. 반드시 기존 프로젝트 폴더
  (`C:\Users\hwang\Projects\seoul-air-quality-mcp`) 안에서 작업한다.
- `fly launch`, `fly secrets set`, `flyctl deploy`, `fly logs` 등 fly.io 관련 명령은
  Claude Code가 절대 스스로 실행하지 않는다.
- 배포 준비(코드 구현, 로컬 테스트, git commit/push)가 끝나면 정지하고, 사용자에게
  PowerShell에서 `flyctl deploy`를 직접 실행하도록 안내한다.

## 2. 작업 순서

**0단계(중요, 반드시 먼저 읽을 것)**: DEVPLAN.md 0-1절에 기존 코드의 버그가
기록되어 있다. 기존 `get_realtime_air_quality` 함수가 실제로는
`RealtimeCityAir`(권역별 데이터)를 호출하고 있으며, 이는 "자치구별"이라는
이름·설명과 맞지 않는다. 이번 작업은 이 버그의 **개명 정정**과 **진짜
자치구별 데이터셋 신규 구현**을 함께 수행한다. 아래 순서를 반드시 지킨다
(순서가 바뀌면 함수명이 충돌한다).

1. 기존 저장소 구조를 먼저 파악한다 — `main.py`, API 호출 공통 함수,
   `_DATASET_INFO`류 메타데이터 딕셔너리가 있는지 확인. 특히 `main.py` 528행
   부근의 기존 `get_realtime_air_quality` 함수 정의부를 정확히 찾아둔다.
2. **개명을 먼저 수행한다**: 기존 `get_realtime_air_quality` 함수명을
   `get_zonal_realtime_air_quality`로 변경한다. 함수 내부의 API 호출 URL,
   파싱 로직은 **절대 변경하지 않는다** — 이미 `RealtimeCityAir`를 정상
   호출하고 있으므로 그대로 둔다. docstring과 함수 설명만 "서울시 권역별
   실시간 대기환경 현황"에 맞게 정정한다. 이 저장소에 도구 목록을 등록하는
   곳(FastMCP 데코레이터, `_DATASET_INFO` 등)이 있다면 그곳의 이름도 함께
   변경한다.
3. **개명이 끝난 뒤에만** 신규 6개 도구를 구현한다 (DEVPLAN.md 2-2절). 이때
   `get_realtime_air_quality`라는 이름을 진짜 "서울시 실시간 자치구별
   대기환경 현황"(`ListAirQualityByDistrictService`)에 새로 부여해 신규
   함수로 구현한다. 2단계가 먼저 끝나 있지 않으면 이름이 겹친다.
4. 각 함수는 기존 공통 API 호출 함수(JSON 우선, XML `<CODE>`/`<MESSAGE>` 폴백 파싱
   포함)를 재사용한다. 새로 만들지 않는다.
5. docstring에 필드명·단위·출처 표기 필수 문구를 기존 도구들과 동일한 형식으로 삽입한다.
6. 로컬 실측 테스트 — 아래 3절 "실측 필요 항목" 순서대로 진행. **개명된
   `get_zonal_realtime_air_quality`가 개명 전과 동일하게 정상 동작하는지
   회귀 테스트를 반드시 포함한다.**
7. `_DATASET_INFO`(또는 동등한 메타데이터 구조)에 신규 6개 항목 등록 — 서비스명,
   제공부서, 원본 URL 포함. 개명된 항목의 메타데이터도 "권역별"에 맞게 갱신.
8. README.md의 Dataset Registry 표를 16개 → 22개로 갱신. **DEVPLAN.md 1-8절의
   "서울시 시간 평균 대기오염도 정보" 표기 정정(붙여쓰기 → 띄어쓰기)도 이 시점에
   함께 반영한다.** "배포 검증 이력" 절에 이번 버그 발견·수정 사실을 날짜와
   함께 명확히 기록한다 — 과거 README에 잘못 기재된 서비스명 매핑이 어떻게
   틀렸었는지, 무엇으로 바로잡았는지 남겨서 향후 재발을 막는다.
9. DEVLOG.md에 이번 확장 작업(버그 수정 포함) 기록 추가.
10. `python3 -m py_compile` 등으로 구문 검증.
11. git add/commit/push까지 수행 (본인 소유 저장소 백업이므로 자동 진행 가능).
    커밋 메시지에 이번 작업이 "기능 추가"뿐 아니라 "버그 수정"을 포함한다는
    점을 명시한다 (예: `fix: 잘못 명명된 get_realtime_air_quality를
    get_zonal_realtime_air_quality로 정정, 진짜 자치구별 API 신규 추가`).
12. **여기서 정지** — 배포는 사용자가 PowerShell에서 직접 수행.

## 3. 실측 필요 항목 (반드시 조합별로 테스트)

### 3-1. 빈 값 처리 (오존 경보 / 초미세먼지 발령정보)
`YearlyOzoneIssue`, `yearMicroDustInfo` 두 서비스 모두, 발령 횟수가 0인 연도에는
`MAX_DNST` 필드가 `<MAX_DNST/>`처럼 빈 값으로 온다. 이 경우:
```python
def _safe_float(v):
    if v is None or v == "":
        return None  # 또는 0.0 — 실측 후 어느 쪽이 더 적절한지 판단해 DEVLOG.md에 기록
    return float(v)
```
숫자 0(정상적으로 측정된 0)과 "값 없음"(발령 자체가 없어 측정 안 됨)을 혼동하지 않도록
None으로 구분하는 것을 우선 검토한다.

### 3-2. 필수 파라미터 (년도별 평균 대기오염도)
`YearlyAverageAirQuality`는 `MSRMT_YR`(측정년도)이 **필수**다. 이 값을 빠뜨리면
ERROR-300이 재현되는지 먼저 확인하고, 도구 함수 시그니처에서도 이 파라미터를
필수로 강제한다(다른 신규 도구들의 선택 파라미터와 다른 점이므로 실수하기 쉽다).

### 3-3. 비숫자 측정값 (굴뚝 측정 정보)
`CleanSYSService`의 `MSRMT_VL`은 시설 운휴 시간대에 **"운휴중"이라는 문자열**로 온다
(실측 예제로 확인됨). 숫자 파싱 전에 이 문자열 케이스를 먼저 걸러내는 로직을 넣는다:
```python
def _parse_measurement_value(v):
    if v in ("운휴중", "점검중", ""):  # 실측 중 다른 상태 문자열 발견 시 추가
        return {"status": v, "value": None}
    try:
        return {"status": "정상", "value": float(v)}
    except (ValueError, TypeError):
        return {"status": "알수없음", "value": v}
```
실측 단계에서 "운휴중" 외 다른 상태 문자열이 나오는지 여러 시설/시간대로 조회해보고
발견되면 DEVLOG.md에 기록 후 위 목록에 추가한다.

### 3-4. 권역별 실시간 대기환경 현황 — 중복 여부 최종 확인
`RealtimeCityAir` 서비스가 기존 16개 도구(`get_zonal_hourly_air_quality` 등, 서비스명
`TimeAverageCityAir` 계열) 및 별도 프로젝트인 `seoul-realtime-air-by-region-mcp`와
겹치지 않는지, 실제 코드 구현 전에 서비스명 기준으로 다시 한번 확인한다. 겹치지
않음이 DEVPLAN.md 1-6절에서 이미 확인되었으나, 구현 직전 재확인을 원칙으로 한다
(9절 "규칙-코드 정합성 점검 원칙"과 동일한 취지 — 문서상 결론과 실제 코드 상태를
항상 대조한다).

## 4. 하지 말 것

- 새 저장소/새 프로젝트 폴더 생성 금지 (기존 저장소에 통합)
- 기존 16개 도구의 동작 방식이나 docstring을 임의로 변경하지 않기 (표기 정정
  대상인 `get_hourly_air_quality`의 화면 표시명 문구, 그리고 개명 대상인
  `get_realtime_air_quality`→`get_zonal_realtime_air_quality` 제외)
- **개명 작업 중 `get_zonal_realtime_air_quality`(구 `get_realtime_air_quality`)의
  API 호출 로직(URL, 파싱)을 함께 수정하지 않기** — 이 함수는 이미 `RealtimeCityAir`를
  정상적으로 호출하고 있다. 문제는 이름과 문서였지, 동작이 아니었다. 로직까지
  건드리면 불필요한 회귀 위험이 생긴다.
- **개명과 신규 구현 순서를 바꾸지 않기** — 개명(기존 이름 비우기)을 먼저 하지
  않고 신규 `get_realtime_air_quality`를 만들면 함수명이 충돌한다.
- 인증키 하드코딩 금지
- `fly launch` / `fly secrets set` / `flyctl deploy` / `fly logs` 자동 실행 금지
- 발령 횟수 0을 "정상 측정값 0"과 같은 것으로 취급해 안전 변환 없이 그대로 저장하지 않기
