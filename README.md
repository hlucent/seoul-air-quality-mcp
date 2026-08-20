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
- **전체 도구 수**: 22개

---

## Dataset Registry

이 MCP에 통합된 원본 데이터셋 전체 목록입니다. 왼쪽 열은 서울 열린데이터광장
목록 화면에 표시되는 명칭을 그대로 옮겨 적었습니다 — 웹사이트 화면과 이 표를
나란히 놓고 바로 대조할 수 있도록 축약 없이 전부 나열합니다.

### 기후환경본부 대기정책과 제공 (11개 — 기존 10개는 오기재 1건 정정 포함, 자치구별 1건 신규)

| 열린데이터광장 화면 표시명 | 제공부서(화면 표시 그대로) | 이 MCP 포함 여부 | 서비스명(SERVICE) |
|---|---|---|---|
| 서울시 권역별 실시간 대기환경 현황 | 기후환경본부 대기정책과 | 포함 (`get_zonal_realtime_air_quality`, 舊 `get_realtime_air_quality` 개명) | RealtimeCityAir |
| 서울시 실시간 자치구별 대기환경 현황 | 기후환경본부 대기정책과 | 포함 (신규) | ListAirQualityByDistrictService |
| 서울시 시간 평균 대기오염도 정보 | 기후환경본부 대기정책과 | 포함 | TimeAverageAirQuality |
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
| 서울시 대기오염물질 측정소 높이 정보 | (실측 확인 필요) | 포함 | (실측 확인 필요) |
| 서울시 대기오염전광판 위치정보 | (실측 확인 필요) | 포함 | (실측 확인 필요) |
| 서울시대기오염물질배출시설설치사업장인허가정보 | (실측 확인 필요) | 포함 | (실측 확인 필요) |

### 서울시 보건환경연구원 제공 (3개)

| 열린데이터광장 화면 표시명 | 제공부서(화면 표시 그대로) | 이 MCP 포함 여부 | 서비스명(SERVICE) |
|---|---|---|---|
| 서울시대기오염측정항목정보 | 보건환경연구원 | 포함 | (실측 확인 필요) |
| 서울시 대기오염 측정소정보 | 보건환경연구원 | 포함 | (실측 확인 필요) |
| 서울시 대기오염 측정정보 | 보건환경연구원 | 포함 | airPolutionMeasuring1Hour |

### 신규 추가 — 이번 확장분 (6개, 위 표의 "서울시 실시간 자치구별 대기환경 현황" 포함)

| 열린데이터광장 화면 표시명 | 제공부서(화면 표시 그대로) | 이 MCP 포함 여부 | 서비스명(SERVICE) |
|---|---|---|---|
| 서울시 실시간 자치구별 대기환경 현황 | 기후환경본부 대기정책과 | 포함 | ListAirQualityByDistrictService |
| 서울시 연도별 오존 경보발령 현황 | 기후환경본부 대기정책과 | 포함 | YearlyOzoneIssue |
| 서울시 지역 구별 측정소 행정코드 정보 | 기후환경본부 대기정책과 | 포함 | SearchMeasuringSTNOfAirQualityService |
| 서울시 년도별 평균 대기오염도 정보 | 기후환경본부 대기정책과 | 포함 | YearlyAverageAirQuality |
| 서울시 초미세먼지 연도별 발령정보 | 기후환경본부 대기정책과 | 포함 | yearMicroDustInfo |
| 서울시 굴뚝 측정 정보 | 기후환경본부 자원회수시설추진단 자원회수시설과 | 포함 | CleanSYSService |

※ "서울시 권역별 실시간 대기환경 현황"(RealtimeCityAir)은 신규 추가가 아니라
기존 도구(`get_realtime_air_quality` → `get_zonal_realtime_air_quality`)의
개명·정정 대상입니다. 위 "대기정책과 제공" 표 첫 행 참고.

**총 22개 데이터셋, 22개 도구가 이 MCP에 포함되어 있습니다** (기존 16개 + 신규 6개,
그중 1개는 기존 도구 개명이 아니라 자치구별 신규 구현이며, 개명 자체는 기존
16개 안에서 이름만 바뀐 것이므로 전체 개수에는 영향 없음).

> ⚠️ "기타(위치·시설)"와 "보건환경연구원" 항목 중 일부는 서비스명(SERVICE)이 이번
> 정리 과정에서 실측 재확인되지 않았습니다("실측 확인 필요"로 표기). 기존 배포
> 코드(`server.py`/`_DATASET_INFO`)를 열어 정확한 서비스명으로 채워 넣는 작업이
> 필요합니다 — 11절 문서 편집 재검증 원칙에 따라, 이 표를 최종본으로 확정하기 전에
> 실제 코드와 대조할 것을 권장합니다.

### 새 데이터셋을 봤을 때 이 표만 보고 판단하는 법

1. 데이터셋명이 이미 표에 있는가? → 있으면 중복이므로 아무 작업도 하지 않음
2. 제공부서·원본시스템이 표의 다른 항목들과 같은가? → 같으면 이 MCP에 툴 추가 검토
3. 제공부서가 다른가? → 이 MCP와 무관, 별개 MCP 프로젝트로 진행

---

## 도구 목록 (22개)

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

### 기타(위치·시설) (3개)
- `get_station_height_info` — 서울시 대기오염물질 측정소 높이 정보
- `get_air_pollution_board_locations` — 서울시 대기오염전광판 위치정보
- `get_air_pollutant_emission_facilities` — 서울시대기오염물질배출시설설치사업장인허가정보

### 보건환경연구원 (3개)
- `get_air_pollution_item_info` — 서울시대기오염측정항목정보
- `get_air_pollution_station_info` — 서울시 대기오염 측정소정보
- `get_air_pollution_measurement` — 서울시 대기오염 측정정보

### 신규 추가분 (6개, 위 대기정책과 목록의 `get_realtime_air_quality` 포함)
- `get_realtime_air_quality` — 서울시 실시간 자치구별 대기환경 현황
- `get_yearly_ozone_alerts` — 서울시 연도별 오존 경보발령 현황
- `get_station_admin_codes` — 서울시 지역 구별 측정소 행정코드 정보
- `get_yearly_air_quality` — 서울시 년도별 평균 대기오염도 정보
- `get_yearly_pm25_alerts` — 서울시 초미세먼지 연도별 발령정보
- `get_chimney_emission_info` — 서울시 굴뚝 측정 정보

※ `get_zonal_realtime_air_quality`(서울시 권역별 실시간 대기환경 현황)는
신규가 아니라 위 "대기정책과" 목록에 있는 기존 도구 개명 대상입니다.

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
  지도 표시 시 좌표변환 필요.
- **`get_air_pollution_station_info`**: 위도/경도 좌표 필드 없음 — 지도 표시하려면
  주소 별도 지오코딩 필요.
- **`get_air_pollution_measurement`**: 잠정치이며 국가(환경부/에어코리아) 사후 검증을
  거친 확정치 아님 — 정책보고서 인용 시 주의.
- **`get_yearly_ozone_alerts`, `get_yearly_pm25_alerts`**: 발령 횟수가 0인 연도는
  최대농도(`MAX_DNST`) 필드가 빈 값으로 옴.
- **`get_yearly_air_quality`**: `MSRMT_YR`(측정년도)가 필수 파라미터임 — START_INDEX/END_INDEX만으로는
  조회 불가.
- **`get_chimney_emission_info`**: 시설 운휴 시간대에는 측정값(`MSRMT_VL`)이 숫자가
  아니라 "운휴중" 문자열로 옴.

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
