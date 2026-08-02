"""
서울시 대기환경정보 MCP 서버
- 원본 데이터: 서울 열린데이터광장 (data.seoul.go.kr)
- 담당부서: 서울특별시 기후환경본부 대기정책과

인증키는 반드시 환경변수(SEOUL_API_KEY)로만 주입한다. 코드에 절대 하드코딩하지 않는다.
"""

import os
import httpx
from fastmcp import FastMCP

SEOUL_API_KEY = os.environ.get("SEOUL_API_KEY")
BASE_URL = "http://openapi.seoul.go.kr:8088"

mcp = FastMCP("seoul-air-quality-mcp")


def _check_key():
    if not SEOUL_API_KEY:
        raise RuntimeError(
            "SEOUL_API_KEY 환경변수가 설정되지 않았습니다. "
            "data.seoul.go.kr에서 발급받은 인증키를 환경변수로 등록하세요."
        )


# 통합대기환경지수(CAI) 산정 기준 (환경부 공식 등급기준)
# 형식: (구간최솟값, 구간최댓값, 지수최솟값, 지수최댓값)
_CAI_BREAKPOINTS = {
    "PM10": [(0, 30, 0, 50), (31, 80, 51, 100), (81, 150, 101, 250), (151, 600, 251, 500)],
    "PM25": [(0, 15, 0, 50), (16, 35, 51, 100), (36, 75, 101, 250), (76, 500, 251, 500)],
    "O3": [(0, 0.030, 0, 50), (0.031, 0.090, 51, 100), (0.091, 0.150, 101, 250), (0.151, 0.600, 251, 500)],
    "NO2": [(0, 0.030, 0, 50), (0.031, 0.060, 51, 100), (0.061, 0.200, 101, 250), (0.201, 2.000, 251, 500)],
    "CO": [(0, 2.00, 0, 50), (2.01, 9.00, 51, 100), (9.01, 15.00, 101, 250), (15.01, 50.00, 251, 500)],
    "SO2": [(0, 0.020, 0, 50), (0.021, 0.050, 51, 100), (0.051, 0.150, 101, 250), (0.151, 1.000, 251, 500)],
}

_CAI_FIELD_MAP = {"PM10": "PM", "PM25": "FPM", "O3": "OZON", "NO2": "NTDX", "CO": "CBMX", "SO2": "SPDX"}

_GRADE_GUIDANCE = {
    "좋음": "야외활동 하기 좋은 날입니다.",
    "보통": "대부분의 사람에게 영향이 없는 수준입니다. 매우 민감한 분은 장시간 야외활동을 줄이는 것이 좋습니다.",
    "나쁨": "어린이·노약자·호흡기환자는 야외활동을 자제하고, 일반인도 장시간 야외활동을 줄이는 것이 좋습니다.",
    "매우나쁨": "민감군은 실내활동을, 일반인도 야외활동을 가급적 자제하는 것이 좋습니다.",
}


def _grade_from_index(index: float) -> str:
    if index <= 50:
        return "좋음"
    if index <= 100:
        return "보통"
    if index <= 250:
        return "나쁨"
    return "매우나쁨"


def _pollutant_subindex(pollutant: str, value) -> float | None:
    """개별 오염물질 농도를 환경부 CAI 세부지수로 환산한다."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v < 0:
        return None

    bps = _CAI_BREAKPOINTS.get(pollutant)
    if not bps:
        return None

    for bp_lo, bp_hi, idx_lo, idx_hi in bps:
        if bp_lo <= v <= bp_hi:
            return round(idx_lo + (idx_hi - idx_lo) * (v - bp_lo) / (bp_hi - bp_lo), 1)

    if v > bps[-1][1]:
        return 500.0
    return None


def _add_air_quality_grade(row: dict) -> dict:
    """
    측정 데이터에 PM10/PM2.5/오존/이산화질소/일산화탄소/아황산가스 값이 있으면
    통합대기환경지수(CAI)를 직접 계산하여 등급·지배오염물질·행동요령을 함께 붙여준다.
    (원본 API가 지수를 따로 제공하지 않거나 값이 비어 있는 경우에도 항상 동일한 기준으로 계산한다.)
    """
    subindices = {}
    for pollutant, field in _CAI_FIELD_MAP.items():
        idx = _pollutant_subindex(pollutant, row.get(field))
        if idx is not None:
            subindices[pollutant] = idx

    if not subindices:
        return row

    determining = max(subindices, key=subindices.get)
    overall_index = subindices[determining]
    grade = _grade_from_index(overall_index)

    row["cai_index"] = overall_index
    row["cai_grade"] = grade
    row["cai_determining_pollutant"] = determining
    row["cai_guidance"] = _GRADE_GUIDANCE[grade]
    return row


@mcp.tool()
async def get_realtime_air_quality(district: str = "", start: int = 1, end: int = 25) -> dict:
    """
    서울시 25개 자치구의 실시간 대기환경 현황을 조회한다. (OA-1200 기반)

    각 자치구 데이터에는 환경부 통합대기환경지수(CAI) 기준으로 직접 계산한
    cai_index(지수), cai_grade(좋음/보통/나쁨/매우나쁨), cai_determining_pollutant(지배오염물질),
    cai_guidance(야외활동 행동요령)가 함께 담겨 있어, 단순히 원시 수치를 해석하지 않아도
    바로 활동 여부를 판단할 수 있다.

    Args:
        district: 자치구 이름 (예: "강남구"). 비워두면 전체 자치구 반환.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 25, 전체 자치구 수)
    """
    _check_key()
    url = f"{BASE_URL}/{SEOUL_API_KEY}/json/RealtimeCityAir/{start}/{end}/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("RealtimeCityAir", {}).get("row", [])

    if district:
        rows = [r for r in rows if district in r.get("MSRSTN_NM", "")]

    rows = [_add_air_quality_grade(r) for r in rows]

    return {
        "count": len(rows),
        "data": rows,
    }


@mcp.tool()
async def get_hourly_air_quality(
    date: str, hour: str = "", district: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    특정 날짜(또는 특정 시)의 자치구별 시간평균 대기오염도를 조회한다. (OA-2275 기반)

    응답 필드 의미 (data.seoul.go.kr 예제 기준으로 확인):
        MSRMT_DT: 측정일시 (YYYYMMDDHH)
        MSRSTN_NM: 측정소명(자치구명)
        NTDX: 이산화질소 농도 (ppm)
        OZON: 오존 농도 (ppm)
        CBMX: 일산화탄소 농도 (ppm)
        SPDX: 아황산가스 농도 (ppm)
        PM: 미세먼지 PM10 (μg/m³)
        FPM: 초미세먼지 PM2.5 (μg/m³)

    각 행에는 환경부 통합대기환경지수(CAI) 기준으로 직접 계산한
    cai_index(지수), cai_grade(좋음/보통/나쁨/매우나쁨), cai_determining_pollutant(지배오염물질),
    cai_guidance(야외활동 행동요령)가 함께 담겨 있다.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801")
        hour: 특정 시(00~23)를 지정하려면 두 자리 숫자로 (예: "13"). 비워두면 해당 날짜의 전체 시간대 조회.
        district: 자치구 이름 (예: "종로구"). 비워두면 서울시 전체 자치구.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()

    date_param = date + hour  # hour가 있으면 YYYYMMDDHH, 없으면 YYYYMMDD

    parts = [BASE_URL, SEOUL_API_KEY, "json", "TimeAverageAirQuality", str(start), str(end), date_param]
    if district:
        parts.append(district)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("TimeAverageAirQuality", {}).get("row", [])
    rows = [_add_air_quality_grade(r) for r in rows]
    return {"count": len(rows), "data": rows}


@mcp.tool()
async def get_roadside_air_quality(
    road: str = "", station_name: str = "", start: int = 1, end: int = 25
) -> dict:
    """
    서울시 도로변/입체대기 측정소별 실시간 대기환경 현황을 조회한다. (OA-2223 기반)
    ※ 자치구 도시대기측정망과는 별도로, 도로변(일반도로/전용차로/중앙차로)에 설치된
    측정소에서 측정한 값이며 최종검증 전 실시간(잠정치) 자료이다.

    응답 필드 의미 (data.seoul.go.kr 예제 기준으로 확인):
        MSRMT_DT: 측정일시
        ROAD: 도로변구분 (일반도로/전용차로/중앙차로)
        MSRSTN_NM: 측정소명
        PM: 미세먼지 PM10 (μg/m³)
        OZON: 오존 농도 (ppm)
        NTDX: 이산화질소 농도 (ppm)
        CBMX: 일산화탄소 농도 (ppm)
        SPDX: 아황산가스 농도 (ppm)
        FPM: 초미세먼지 PM2.5 (μg/m³)

    각 행에는 환경부 통합대기환경지수(CAI) 기준으로 직접 계산한
    cai_index(지수), cai_grade(좋음/보통/나쁨/매우나쁨), cai_determining_pollutant(지배오염물질),
    cai_guidance(야외활동 행동요령)가 함께 담겨 있다.

    Args:
        road: 도로변구분 (예: "일반도로", "전용차로", "중앙차로"). 비워두면 전체.
        station_name: 측정소명 (예: "서울역"). 비워두면 전체 측정소.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 25)
    """
    _check_key()

    parts = [BASE_URL, SEOUL_API_KEY, "json", "RealtimeRoadsideStation", str(start), str(end)]
    if road:
        parts.append(road)
    if station_name:
        parts.append(station_name)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("RealtimeRoadsideStation", {}).get("row", [])
    rows = [_add_air_quality_grade(r) for r in rows]
    return {"count": len(rows), "data": rows}


@mcp.tool()
async def get_zonal_hourly_air_quality(
    date: str, hour: str, sarea: str = "", station_name: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    특정 날짜·시각의 권역별/측정소별 시간평균 대기환경 정보를 조회한다. (OA-2221 기반, 서비스명: TimeAverageCityAir)
    ※ 데이터셋 이름은 "기간별"이지만 실제로는 여러 날짜를 한 번에 조회하는 것이 아니라,
    지정한 "특정 한 시각"의 데이터를 조회하는 API이다. 여러 시각을 보려면 이 도구를 반복 호출해야 한다.

    ⚠️ 시간(hour) 표기가 get_hourly_air_quality(00~23)와 다르다. 이 API는 01~24이며,
    24는 해당 날짜의 마지막 시간(자정)을 의미한다. 헷갈리지 않도록 주의할 것.

    자치구 단위가 아니라 권역(SAREA_NM, 예: 도심권/서북권/동북권/서남권/동남권) 단위로 묶여서 나오며,
    기존 도구에는 없는 미세먼지 24시간 평균값(PM_ALDY)도 함께 제공한다.

    응답 필드 의미 (data.seoul.go.kr 예제 기준으로 확인):
        MSRMT_DT: 측정일시
        SAREA_CD: 권역코드
        SAREA_NM: 권역명
        MSRSTN_CD: 측정소코드
        MSRSTN_NM: 측정소명
        PM_HOUR: 미세먼지 1시간 평균 (μg/m³)
        PM_ALDY: 미세먼지 24시간 평균 (μg/m³)
        FPM: 초미세먼지 (μg/m³)
        OZON: 오존 농도 (ppm)
        NTDX: 이산화질소 농도 (ppm)
        CBMX: 일산화탄소 농도 (ppm)
        SPDX: 아황산가스 농도 (ppm)

    각 행에는 PM_HOUR(1시간 평균)를 기준으로 환경부 통합대기환경지수(CAI)를 직접 계산한
    cai_index(지수), cai_grade(좋음/보통/나쁨/매우나쁨), cai_determining_pollutant(지배오염물질),
    cai_guidance(야외활동 행동요령)가 함께 담겨 있다.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801")
        hour: 시(01~24) 두 자리 숫자로 (예: "11"). 24는 해당 날짜의 마지막 시간을 의미.
        sarea: 권역명 (예: "도심권", "서북권", "동북권", "서남권", "동남권"). 비워두면 전체 권역.
        station_name: 측정소명 (예: "종로구"). 비워두면 전체 측정소.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()

    msrmt_dt = date + hour + "00"  # YYYYMMDDHHMM, 분은 항상 00

    parts = [BASE_URL, SEOUL_API_KEY, "json", "TimeAverageCityAir", str(start), str(end), msrmt_dt]
    if sarea:
        parts.append(sarea)
    if station_name:
        parts.append(station_name)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("TimeAverageCityAir", {}).get("row", [])

    graded_rows = []
    for r in rows:
        r_for_grade = dict(r)
        r_for_grade["PM"] = r.get("PM_HOUR")  # CAI 계산용: 1시간 평균값을 PM10 기준으로 사용
        r_for_grade = _add_air_quality_grade(r_for_grade)
        r_for_grade.pop("PM", None)  # 원본 응답에 없던 임시 필드는 제거
        graded_rows.append(r_for_grade)

    return {"count": len(graded_rows), "data": graded_rows}


@mcp.tool()
async def get_yearly_pm10_alerts(year: str = "", start: int = 1, end: int = 30) -> dict:
    """
    서울시 연도별 미세먼지(PM10) 경보발령 현황을 조회한다. (OA-2228 기반)
    자치구 구분 없이 서울시 전체 기준 연도별 통계입니다.

    [데이터셋 상태] 확인일: 2026-08-02 / 검증 결과: 검증 필요
    2007~2025년 전 구간 발령횟수/발령일수/최댓농도값이 0으로 조회됨.
    데이터갱신일자는 최근(2025.11.04)이나 실제 값이 비어있어 원본 확인이 필요한 상태.

    Args:
        year: 조회할 연도 (예: "2024"). 비워두면 전체 연도 반환.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 30, 전체 연도 수)
    """
    _check_key()
    url = f"{BASE_URL}/{SEOUL_API_KEY}/json/YearlyPM10Issue/{start}/{end}/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("YearlyPM10Issue", {}).get("row", [])

    if year:
        rows = [r for r in rows if r.get("YR", "") == year]

    warning = None
    if rows:
        recent = [r for r in rows if r.get("YR", "0") >= "2020"]
        if recent and all(float(r.get("APNT_NMTM", 0)) == 0 for r in recent):
            warning = (
                "최근 5개년도 발령횟수가 모두 0입니다. 실제로 경보가 없었거나, "
                "이 데이터셋 값이 채워지지 않았을 수 있습니다. "
                "원본(data.seoul.go.kr)에서 직접 확인을 권장합니다."
            )

    result = {
        "count": len(rows),
        "data": rows,
    }
    if warning:
        result["_data_quality_warning"] = warning
    return result


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
