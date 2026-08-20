# 서울시 대기환경정보 MCP (seoul-air-quality-mcp)

서울 열린데이터광장에서 제공하는 서울시 대기환경 관련 오픈API를 Claude에서 바로
조회할 수 있도록 하는 MCP(Model Context Protocol) 서버입니다.

> ⚠️ **이번 확장 작업 중 기존 도구명 오류를 발견해 함께 수정했습니다.** 기존
> `get_realtime_air_quality`는 이름과 달리 실제로는 "서울시 실시간 자치구별
> 대기환경 현황"이 아니라 **"서울시 권역별 실시간 대기환경 현황"(RealtimeCityAir)**을
> 호출하고 있었습니다. 이 도구는 `get_zonal_realtime_air_quality`로 개명했고,
> `get_realtime_air_quality`라는 이름은 진짜 "서울시 실시간 자치구별 대기환경
> 현황"(ListAirQualityByDistrictService)에 새로 부여해 신규 구현했습니다.
> 자세한 경위는 아래 "배포 검증 이력"을 참고하세요.

- **배포 URL**: `https://seoul-air-quality-mcp.fly.dev/mcp`
- **GitHub**: `github.com/hlucent/seoul-air-quality-mcp` (공개, MIT License)
- **배포 인프라**: Fly.io (도쿄 리전)
- **전체 도구 수**: 21개

---

## Dataset Registry

이 MCP에 통합된 원본 데이터셋 전체 목록입니다. 왼쪽 열은 서울 열린데이터광장
목록 화면에 표시되는 명칭을 그대로 옮겨 적었습니다 — 웹사이트 화면과 이 표를
나란히 놓고 바로 대조할 수 있도록 축약 없이 전부 나열합니다.

### 기후환경본부 대기정책과 제공 (11개, 오기재 1건 정정 포함, 자치구별 1건 신규) + 자원회수시설과 제공 (1개)

| 열린데이터광장 화면 표시명 | 제공부서(화면 표시 그대로) | 이 MCP 포함 여부 | 서비스명(SERVICE) |
|---|---|---|---|
| 서울시 권역별 실시간 대기환경 현황 | 기후환경본부 대기정책과 | 포함 (`get_zonal_realtime_air_quality`, 舊 `get_realtime_air_quality` 개명) | RealtimeCityAir |
| 서울시 실시간 자치구별 대기환경 현황 | 기후환경본부 대기정책과 | 포함 (신규) | ListAirQualityByDistrictService |
| 서울시 시간 평균 대기오염도 정보 | 기후환경본부 대기정책과 | 포함 | TimeAverageAirQuality |
| 서울시 굴뚝 측정 정보 | 기후환경본부 자원회수시설추진단 자원회수시설과 | 포함 (`get_chimney_emission_measurement`, "운휴중" 등 비숫자 측정값 안전 파싱 추가) | CleanSYSService |
| 서울시 일별 평균 대기오염도 정보 | 기후환경본부 대기정책과 | 포함 | DailyAverageAirQuality |
| 서울시 월별 평균 대기오염도 정보 | 기후환경본부 대기정책과 | 포함 | MonthlyAverageAirQuality |
| 서울시 실시간 대기환경 평균 현황 | 기후환경본부 대기정책과 | 포함 | ListAvgOfSeoulAirQualityService |
| 서울시 기간별 시간평균 대기환경 정보 | 기후환경본부 대기정책과 | 포함 | TimeAverageCityAir |
| 서울시 기간별 일평균 대기환경 정보 | 기후환경본부 대기정책과 | 포함 | DailyAverageCityAir |
| 서울시 도로변/입체대기 측정소별 실시간 대기환경 현황 | 기후환경본부 대기정책과 | 포함 | RealtimeRoadsideStation |
| 서울시 도로변/입체대기 기간별 일평균 대기환경 현황 | 기후환경본부 대기정책과 | 포함 | DailyAverageRoadside |
| 서울시 연도별 미세먼지(PM10)경보발령 현황 | 기후환경본부 대기정책과 | 포함 | YearlyPM10Issue |

### 기타(위치·시설) 제공 (3개)

| 열린데이터광장 화면 표시명 | 제공부서(화면 표시 그대로) | 이 MCP 포함 여부 | 서비스명(SERVICE) |
|---|---|---|---|
| 서울시 대기오염물질 측정소 높이 정보 | 기후환경본부 대기정책과 | 포함 | airHgt |
| 서울시 대기오염전광판 위치정보 | 기후환경본부 대기정책과 | 포함 | airPollutionBrdInfo |
| 서울시 대기오염물질배출시설설치사업장 인허가 정보 | 기후환경본부 대기정책과 | 포함 | LOCALDATA_093008 |

### 서울시 보건환경연구원 제공 (3개)

| 열린데이터광장 화면 표시명 | 제공부서(화면 표시 그대로) | 이 MCP 포함 여부 | 서비스명(SERVICE) |
|---|---|---|---|
| 서울시 대기오염 측정항목 정보 | 보건환경연구원 대기질통합분석센터 | 포함 | airPolutionMeasuringItem |
| 서울시 대기오염 측정소 정보 | 보건환경연구원 대기질통합분석센터 | 포함 | airPolutionMeasuringPlace |
| 서울시 대기오염 측정정보 | 보건환경연구원 대기질통합분석센터 | 포함 | airPolutionMeasuring1Hour |

### 신규 추가 — 이번 확장분 (5개, 위 표의 "서울시 실시간 자치구별 대기환경 현황" 포함)

| 열린데이터광장 화면 표시명 | 제공부서(화면 표시 그대로) | 이 MCP 포함 여부 | 서비스명(SERVICE) |
|---|---|---|---|
| 서울시 실시간 자치구별 대기환경 현황 | 기후환경본부 대기정책과 | 포함 | ListAirQualityByDistrictService |
| 서울시 연도별 오존 경보발령 현황 | 기후환경본부 대기정책과 | 포함 | YearlyOzoneIssue |
| 서울시 지역 구별 측정소 행정코드 정보 | 기후환경본부 대기정책과 | 포함 | SearchMeasuringSTNOfAirQualityService |
| 서울시 년도별 평균 대기오염도 정보 | 기후환경본부 대기정책과 | 포함 | YearlyAverageAirQuality |
| 서울시 초미세먼지 연도별 발령정보 | 기후환경본부 대기정책과 | 포함 | yearMicroDustInfo |

※ "서울시 권역별 실시간 대기환경 현황"(RealtimeCityAir)은 신규 추가가 아니라
기존 도구(`get_realtime_air_quality` → `get_zonal_realtime_air_quality`)의
개명·정정 대상입니다. 위 "대기정책과 제공" 표 첫 행 참고.

※ "서울시 굴뚝 측정 정보"(CleanSYSService)도 신규 추가가 아닙니다. 구현
착수 시점에 코드를 확인한 결과 기존 `get_chimney_emission_measurement` 도구가
이미 이 서비스를 정상 호출하고 있음을 발견했습니다 — DEVPLAN.md 초안 작성
시점에는 이 사실이 반영되지 않아 신규 추가 대상으로 잘못 계획되어 있었습니다.
중복 신규 함수를 만드는 대신 기존 도구에 3-3절의 "운휴중" 등 비숫자 측정값
안전 파싱 로직만 추가했습니다. 위 "대기정책과 제공" 표에 별도 행으로 반영.

**총 21개 데이터셋, 21개 도구가 이 MCP에 포함되어 있습니다** (기존 16개 + 신규 5개.
"권역별 실시간"은 기존 도구 개명, "굴뚝 측정 정보"는 기존 도구 개선이며 둘 다
신규 도구 수에 포함하지 않음 — 순수 신규 구현은 자치구별 실시간, 오존 경보,
측정소 행정코드, 년도별 평균, 초미세먼지 연도별 발령정보 5개).

### 새 데이터셋을 봤을 때 이 표만 보고 판단하는 법

1. 데이터셋명이 이미 표에 있는가? → 있으면 중복이므로 아무 작업도 하지 않음
2. 제공부서·원본시스템이 표의 다른 항목들과 같은가? → 같으면 이 MCP에 툴 추가 검토
3. 제공부서가 다른가? → 이 MCP와 무관, 별개 MCP 프로젝트로 진행

---

## 도구 목록 (21개)

### 대기정책과 (11개)
- `get_zonal_realtime_air_quality` — 서울시 권역별 실시간 대기환경 현황 (舊 `get_realtime_air_quality`, 이름 오류 정정)
- `get_realtime_air_quality` — 서울시 실시간 자치구별 대기환경 현황 (신규 구현. 개명 전 舊 도구가 쓰던 이름을 이번에 이 진짜 자치구별 데이터셋에 부여함)
- `get_hourly_air_quality` — 서울시 시간 평균 대기오염도 정보
- `get_daily_air_quality` — 서울시 일별 평균 대기오염도 정보
- `get_monthly_air_quality` — 서울시 월별 평균 대기오염도 정보
- `get_seoul_average_air_quality` — 서울시 실시간 대기환경 평균 현황
- `get_zonal_hourly_air_quality` — 서울시 기간별 시간평균 대기환경 정보
- `get_zonal_daily_air_quality` — 서울시 기간별 일평균 대기환경 정보
- `get_roadside_air_quality` — 서울시 도로변/입체대기 측정소별 실시간 대기환경 현황
- `get_roadside_daily_air_quality` — 서울시 도로변/입체대기 기간별 일평균 대기환경 현황
- `get_yearly_pm10_alerts` — 서울시 연도별 미세먼지(PM10)경보발령 현황

### 자원회수시설과 (1개)
- `get_chimney_emission_measurement` — 서울시 굴뚝 측정 정보 (이번 확장 작업에서 "운휴중" 등 비숫자 측정값 안전 파싱 로직 추가)

### 기타(위치·시설) (3개)
- `get_station_height_info` — 서울시 대기오염물질 측정소 높이 정보
- `get_air_pollution_board_locations` — 서울시 대기오염전광판 위치정보
- `get_air_pollutant_emission_facilities` — 서울시 대기오염물질배출시설설치사업장 인허가 정보

### 보건환경연구원 (3개)
- `get_air_pollution_item_info` — 서울시 대기오염 측정항목 정보
- `get_air_pollution_station_info` — 서울시 대기오염 측정소 정보
- `get_air_pollution_measurement` — 서울시 대기오염 측정정보

### 신규 추가분 (5개, 위 대기정책과 목록의 `get_realtime_air_quality` 포함)
- `get_realtime_air_quality` — 서울시 실시간 자치구별 대기환경 현황
- `get_yearly_ozone_alerts` — 서울시 연도별 오존 경보발령 현황
- `get_station_admin_codes` — 서울시 지역 구별 측정소 행정코드 정보
- `get_yearly_air_quality` — 서울시 년도별 평균 대기오염도 정보
- `get_yearly_pm25_alerts` — 서울시 초미세먼지 연도별 발령정보

※ `get_zonal_realtime_air_quality`(서울시 권역별 실시간 대기환경 현황)는
신규가 아니라 위 "대기정책과" 목록에 있는 기존 도구 개명 대상입니다.
※ `get_chimney_emission_measurement`(서울시 굴뚝 측정 정보)도 신규가 아니라
기존 도구 개선 대상입니다 — 위 "신규 추가분"에서 제외.

---

## 알려진 제약사항 (실측으로 확인된 내용)

- **`get_zonal_realtime_air_quality`(舊 `get_realtime_air_quality`)**: 2026-08-20
  이전에는 "서울시 실시간 자치구별 대기환경 현황"으로 잘못 문서화되어 있었으나,
  실제로는 처음부터 "서울시 권역별 실시간 대기환경 현황"(RealtimeCityAir)을
  호출하고 있었음이 실측으로 확인됨. 도구명·문서만 정정했으며 API 호출 로직은
  변경하지 않음 — 과거에 이 도구를 "자치구별"로 알고 사용한 이력이 있다면
  실제로는 "권역별" 데이터였다는 점에 유의할 것.
- **`get_yearly_pm10_alerts`**: 2007~2025년 일부 구간 값이 0으로 조회됨 — 원본 데이터 확인 필요.
- **`get_air_pollutant_emission_facilities`**: 좌표가 WGS84가 아닌 중부원점TM(EPSG:5174) —
  지도 표시 시 좌표변환 필요. 위경도 좌표는 제공되지 않음.
- **`get_air_pollution_station_info`**: 위도/경도 좌표 필드 없음 — 지도 표시하려면
  주소 별도 지오코딩 필요.
- **`get_air_pollution_measurement`**: 잠정치이며, 서울시 보건환경연구원 자체 보정을 거친
  값이나 환경부 대기환경정보(airkorea.or.kr)의 최종확정자료는 아님 — 정책보고서
  인용 시에는 최종확정자료 여부를 별도 확인할 것.
- **`get_yearly_ozone_alerts`, `get_yearly_pm25_alerts`**: 발령 횟수가 0인 연도는
  최대농도(`MAX_DNST`) 필드가 빈 값으로 올 수 있음 — 2026-08-20 실측에서
  `get_yearly_pm25_alerts`의 2016년 행에서 실제로 재현됨(응답의 `max_dnst`
  필드가 `null`). `get_yearly_ozone_alerts`는 1995~2024년 실측 범위에서는
  재현되지 않았으나(전 구간 `MAX_DNST`가 문자열 "0"), 안전 파싱 로직은
  두 도구 모두 동일하게 적용되어 있음.
- **`get_yearly_air_quality`**: `measurement_year`(측정년도)가 함수 시그니처상
  필수 파라미터임. 다만 2026-08-20 실측 결과, 서울시 API 자체는 이 값을 빈
  문자열로 보내도 ERROR-300을 반환하지 않고 전체 데이터를 그대로 반환함을
  확인 — DEVPLAN.md가 전제한 "필수값 누락 시 ERROR-300" 거동은 재현되지
  않았다(확인 필요 항목, DEVLOG.md 참고).
- **`get_chimney_emission_measurement`**: 시설 운휴 시간대에는 측정값(`MSRMT_VL`)이
  숫자가 아니라 "운휴중" 문자열로 옴 — 2026-08-20 실측에서 강남/노원/마포/양천
  4개 시설 전체가 해당 시간대에 "운휴중" 상태였음을 확인. 각 행에 안전 파싱된
  `msrmt_status`/`msrmt_value`가 추가되어 있음. "점검중" 등 다른 상태 문자열은
  이번 실측에서 관측되지 않아 확인 필요 상태로 남아 있음.

---

## 배포 검증 이력

### 2026-08-20 — 도구명 오류 발견 및 정정, 6개 데이터셋 확장 작업 (실제 신규 5개)

이번 확장 작업 착수 과정에서, 기존 도구 `get_realtime_air_quality`(당시
"서울시 실시간 자치구별 대기환경 현황", OA-1200)로 문서화되어 있던 도구가
**실제로는 서비스명 `RealtimeCityAir`를 호출하고 있음**을 확인했습니다.
`RealtimeCityAir`의 진짜 데이터셋은 "서울시 권역별 실시간 대기환경
현황"(도심권/동북권/동남권/서북권/서남권 단위)이며, "자치구별"의 진짜
서비스명은 `ListAirQualityByDistrictService`인데 이 서비스는 그동안
구현된 적이 없었습니다.

**원인**: 개발 초기 단계(2026-08-01 개발 일지)에 두 데이터셋(자치구별 vs
권역별)의 서비스명을 착각해 `RealtimeCityAir`를 "자치구별"로 잘못
연결했고, 이후 문서화도 이 착오를 그대로 답습해 README 최종 표까지
`RealtimeCityAir` = 자치구별로 잘못 기재되어 왔습니다.

**수정 내용**:
1. `get_realtime_air_quality` → `get_zonal_realtime_air_quality`로 개명.
   API 호출 URL/파싱 로직은 변경하지 않았습니다(이미 `RealtimeCityAir`를
   정상 호출하고 있었으므로 문제는 이름과 문서였을 뿐, 동작이 아니었습니다).
2. `get_realtime_air_quality`라는 이름을 진짜 자치구별 데이터셋
   (`ListAirQualityByDistrictService`)에 새로 부여해 신규 구현했습니다.
3. 과거에 이 도구를 "자치구별" 데이터로 알고 인용한 기록이 있다면, 실제로는
   "권역별" 데이터였을 가능성이 있으므로 재검토를 권장합니다.

또한 구현 착수 시점에 신규 추가 대상이던 "서울시 굴뚝 측정 정보"
(`CleanSYSService`)가 이미 기존 도구 `get_chimney_emission_measurement`로
구현되어 있음을 발견해, 중복 신규 함수를 만드는 대신 기존 도구에 비숫자
측정값("운휴중" 등) 안전 파싱 로직만 추가했습니다. 이에 따라 최종 신규
도구는 계획된 6개가 아니라 5개이며, 전체 도구 수는 22개가 아니라 21개입니다.

자세한 실측 테스트 결과와 확인 필요 항목은 DEVLOG.md 2026-08-20 항목을
참고하세요.

### 2026-08-20 (추가) — 미확인 서비스명 5건 명세서 확보 및 정정

Dataset Registry 표에서 "실측 확인 필요"로 비워두었던 아래 5개 데이터셋의
서비스명을 명세서 원본으로 확인해 갱신했습니다. 코드 변경은 없으며 문서
정정만 반영합니다.

- 서울시 대기오염물질 측정소 높이 정보 → `airHgt` (제공부서: 기후환경본부 대기정책과)
- 서울시 대기오염전광판 위치정보 → `airPollutionBrdInfo` (제공부서: 기후환경본부 대기정책과)
- 서울시 대기오염물질배출시설설치사업장 인허가 정보 → `LOCALDATA_093008`
  (제공부서: 기후환경본부 대기정책과, 원본시스템: 공공데이터포털 지방행정
  인허가정보 — 다른 서울시 자체 API와 원본시스템이 다르다는 점에 유의)
- 서울시 대기오염 측정항목 정보 → `airPolutionMeasuringItem`
  (제공부서: 보건환경연구원 대기질통합분석센터; 화면 표시명이 기존
  "서울시대기오염측정항목정보"에서 "서울시 대기오염 측정항목 정보"로 정정됨)
- 서울시 대기오염 측정소 정보 → `airPolutionMeasuringPlace`
  (제공부서: 보건환경연구원 대기질통합분석센터)

**참고로 발견된 사항**:
- "서울시 대기오염 측정정보"(`airPolutionMeasuring1Hour`)의 서비스설명에
  따르면 이 데이터는 "보정 후" 값이며 국가 최종확정자료가 아니라는 점이
  명세서에 명시되어 있어, 위 "알려진 제약사항"의 관련 문구를 이에 맞춰
  구체화함.
- "서울시 대기오염물질배출시설설치사업장 인허가 정보"는 원본시스템이
  다른 대기정책과 API들과 달리 "공공데이터포털(지방행정 인허가정보)"이며,
  좌표는 중부원점TM(EPSG:5174)이고 위경도는 제공되지 않음이 명세서로
  재확인됨(기존 "알려진 제약사항" 서술과 일치).

---

## 환경변수

| 변수명 | 설명 |
|---|---|
| `SEOUL_API_KEY` | 서울 열린데이터광장에서 발급받은 인증키 |

---

## 라이선스

- 코드: MIT License
- 데이터: 공공누리 1유형 출처표시 (상업적 이용 및 변경 가능)

---

## 설치/실행/배포

이 MCP는 이미 배포되어 있으며, Claude.ai > 설정 > 커넥터에서 아래 주소로 연결합니다.

```
https://seoul-air-quality-mcp.fly.dev/mcp
```

코드 수정 후 재배포는 저장소 소유자가 로컬 PowerShell에서 `flyctl deploy`로 수행합니다.
