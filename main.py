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


# 각 도구가 사용하는 원본 데이터셋 정보 (공무원 보고서 작성 시 출처 확인용)
# 응답에 "_data_source" 필드로 함께 반환되어, 이 수치가 어느 데이터셋에서 나왔는지
# 언제나 명확히 추적할 수 있도록 한다.
_DATASET_INFO = {
    "OA-1200": {
        "dataset_name": "서울시 실시간 자치구별 대기환경 현황",
        "dataset_id": "OA-1200",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-1200/S/1/datasetView.do",
    },
    "OA-2275": {
        "dataset_name": "서울시 시간 평균 대기오염도 정보",
        "dataset_id": "OA-2275",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-2275/S/1/datasetView.do",
    },
    "OA-2223": {
        "dataset_name": "서울시 도로변/입체대기 측정소별 실시간 대기환경 현황",
        "dataset_id": "OA-2223",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-2223/S/1/datasetView.do",
    },
    "OA-2221": {
        "dataset_name": "서울시 기간별 시간평균 대기환경 정보",
        "dataset_id": "OA-2221",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-2221/S/1/datasetView.do",
    },
    "OA-2228": {
        "dataset_name": "서울시 연도별 미세먼지(PM10) 경보발령 현황",
        "dataset_id": "OA-2228",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-2228/S/1/datasetView.do",
        # 포털 데이터셋 상세페이지에 표기된 갱신일자(사람이 직접 확인해서 기록한 값).
        # API 응답 자체에는 갱신일자가 없어서, 이 값은 자동 계산이 아니라 수동 확인값이다.
        "portal_last_verified": "2025-11-04 (확인일 2026-08-02 기준)",
    },
    "OA-12855": {
        "dataset_name": "서울시 대기오염물질 측정소 높이 정보",
        "dataset_id": "OA-12855",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-12855/S/1/datasetView.do",
        # 이 데이터셋은 API 응답에 측정일시/갱신일자 필드가 전혀 없는 정적 참고정보다.
        # 기준일자를 자동으로 계산할 수 없으므로, 그 사실 자체를 응답에 명시한다.
        "static_reference_note": (
            "이 데이터셋은 실시간 측정값이 아닌 정적 참고정보(측정소 채취구 높이)이며, "
            "API 응답에 갱신일자 필드가 없습니다. 최신 여부는 원문 링크의 데이터셋 상세페이지에서 "
            "직접 확인해야 합니다."
        ),
    },
    "OA-1201": {
        "dataset_name": "서울시 실시간 대기환경 평균 현황",
        "dataset_id": "OA-1201",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-1201/S/1/datasetView.do",
        # 이 API는 매시간 갱신되지만(갱신주기: 정기/1시간단위), 응답 필드 자체에는
        # 측정일시(MSRDT 등) 필드가 없다. 실제 측정시각을 알 수 없으므로 지어내지 않고,
        # "조회 시점 기준"이라는 사실을 그대로 명시한다.
        "static_reference_note": (
            "이 데이터셋은 매시간 갱신되지만 API 응답에 측정일시 필드가 없습니다. "
            "따라서 아래 수치는 '조회한 시점 기준 최신값'이며, 정확한 측정시각이 필요하면 "
            "원문 링크의 실시간 화면에서 직접 확인해야 합니다."
        ),
    },
    "OA-2220": {
        "dataset_name": "서울시 기간별 일평균 대기환경 정보",
        "dataset_id": "OA-2220",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-2220/S/1/datasetView.do",
    },
    "OA-2218": {
        "dataset_name": "서울시 일별 평균 대기오염도 정보",
        "dataset_id": "OA-2218",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-2218/S/1/datasetView.do",
    },
}

# 측정일시로 흔히 쓰이는 필드명 후보 (데이터셋마다 이름이 조금씩 다르다)
_DATETIME_FIELD_CANDIDATES = ["MSRDT", "MSRMT_DT", "MSRDATE", "MSRMT_YMD"]


def _format_msrdt(raw: str) -> str:
    """'YYYYMMDDHHMM' 또는 'YYYYMMDDHH', 'YYYYMMDD' 형식의 문자열을 사람이 읽기 좋은 형태로 바꾼다."""
    s = str(raw)
    try:
        if len(s) >= 12:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"
        if len(s) >= 10:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}시"
        if len(s) >= 8:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    except Exception:
        pass
    return s


def _latest_reference_datetime(rows: list) -> str | None:
    """행 데이터에 측정일시 필드가 있으면, 그 중 가장 최신 값을 '기준일자'로 계산해 반환한다."""
    values = []
    for r in rows:
        for field in _DATETIME_FIELD_CANDIDATES:
            if r.get(field):
                values.append(str(r[field]))
                break
    if not values:
        return None
    return _format_msrdt(max(values))


def _citation(dataset_id: str, rows: list | None = None, year_field: str | None = None) -> dict:
    """
    출처(_data_source)와, 답변 끝에 그대로 출력해야 하는 완성 문장(_citation_required)을 생성한다.

    기준일자 결정 순서:
    1. rows에 측정일시 필드(MSRDT 등)가 있으면 → 그 중 최신값을 기준일자로 사용 (실시간/시간평균류)
    2. year_field가 지정되어 있으면 → 조회된 연도 범위를 기준일자로 사용 (연도별 통계류)
    3. 둘 다 없으면 → _DATASET_INFO의 static_reference_note를 기준일자 자리에 사용
       (=API에 갱신일자 정보 자체가 없다는 사실을 그대로 답변에 노출시킨다. 임의로 날짜를 지어내지 않는다.)

    이 함수가 반환하는 "citation_text"는 반드시 답변 맨 끝에 그대로("출처: ..." 문장 전체) 포함해야 한다.
    생략, 요약, 재구성 금지.
    """
    info = dict(_DATASET_INFO.get(
        dataset_id,
        {"dataset_name": "미등록 데이터셋", "dataset_id": dataset_id,
         "provider": "확인 필요", "source_url": ""},
    ))

    reference_date = None
    if rows:
        reference_date = _latest_reference_datetime(rows)

    if not reference_date and year_field and rows:
        years = sorted({str(r.get(year_field)) for r in rows if r.get(year_field)})
        if years:
            reference_date = f"{years[0]}~{years[-1]}년 (연도별 통계, 개별 연도는 데이터 참조)"

    if not reference_date:
        reference_date = info.get(
            "static_reference_note",
            "이 데이터셋에는 자동 갱신일자 정보가 없습니다 — 원문 링크에서 직접 확인 필요",
        )

    citation_text = (
        f"출처: {info.get('dataset_name')} ({dataset_id}, {info.get('provider')}) "
        f"| 기준일자: {reference_date} "
        f"| 원문 링크: {info.get('source_url')}"
    )
    if info.get("portal_last_verified"):
        citation_text += f" | 포털 등록 갱신일: {info['portal_last_verified']}"

    info["reference_date"] = reference_date
    info["citation_text"] = citation_text
    return info


def _source(dataset_id: str) -> dict:
    """하위호환용. 새 도구는 _citation()을 사용할 것."""
    return _citation(dataset_id)


# 농도값(PM10/PM2.5/오존 등)을 반환하는 도구들에 공통으로 붙는 경고문구.
# 측정소 채취구 높이가 지상보다 높은 경우, 실제 보행자가 지표면 근처에서 체감하는
# 농도와 차이가 날 수 있다는 대표성 한계를 항상 명시한다.
# (공무원 보고서 작성 시 "이 수치를 그대로 인용해도 되는지"를 즉시 판단할 수 있도록,
#  선택 정보가 아니라 응답에 항상 포함되는 기본 정보로 취급한다.)
_HEIGHT_CAVEAT = (
    "⚠️ 대표성 참고: 각 측정소 행의 station_intake_height_m(채취구 높이, m 단위 실측값)과 "
    "station_location_address(측정소 위치)를 함께 확인하세요. '높다/낮다'로 뭉뚱그리지 말고, "
    "실제 수치와 주소를 답변에 명시할 것. 채취구가 지상보다 높은 곳에 설치된 경우, 실제 보행자가 "
    "지표면 근처에서 체감하는 농도와 다를 수 있습니다(특히 미세먼지는 지표면에 가까울수록 농도가 높은 경향)."
)


async def _get_station_heights() -> dict:
    """
    측정소 채취구 높이 정보(OA-12855, 서비스명 airHgt)를 조회해
    측정소명 → {height_m, address, category} 매핑으로 반환한다.

    농도값을 반환하는 도구들이 "높다/낮다" 같은 뭉뚱그린 표현 대신, 실제 수치(m)와
    위치를 응답에 직접 병합하기 위해 내부적으로 호출한다. 조회 실패 시에도 전체 응답이
    깨지지 않도록 빈 dict를 반환한다(농도 조회 자체는 항상 성공해야 하므로).
    """
    try:
        _check_key()
        url = f"{BASE_URL}/{SEOUL_API_KEY}/json/airHgt/1/100/"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return {}

    rows = data.get("airHgt", {}).get("row", [])
    heights = {}
    for r in rows:
        name = str(r.get("MSRSTN_NM", "")).strip()
        if name:
            heights[name] = {
                "height_m": r.get("MSRSTN_HGT"),
                "address": r.get("ROAD_NM_ADDR"),
                "category": r.get("SE"),
            }
    return heights


def _attach_station_info(rows: list, heights: dict, station_field: str = "MSRSTN_NM") -> list:
    """
    각 행에 실제 채취구 높이(station_intake_height_m, m)와 측정소 위치(station_location_address)를 붙인다.
    이름이 정확히 일치하지 않으면 부분일치(포함 관계)로 한 번 더 시도한다.
    매칭되는 정보가 없으면 그 사실 자체를 필드에 명시한다(값을 비워서 조용히 생략하지 않는다).
    """
    for r in rows:
        name = str(r.get(station_field, "")).strip()
        info = heights.get(name)
        if not info:
            for h_name, h_info in heights.items():
                if h_name and (h_name in name or name in h_name):
                    info = h_info
                    break
        if info:
            r["station_intake_height_m"] = info.get("height_m")
            r["station_location_address"] = info.get("address")
        else:
            r["station_intake_height_m"] = None
            r["station_location_address"] = "채취구 높이/위치 정보 없음 (OA-12855에서 매칭되는 측정소를 찾지 못함)"
    return rows


def _with_height_caveat(result: dict) -> dict:
    """농도값 반환 도구의 응답에 채취구 높이 대표성 경고문구를 항상 붙인다. 생략 금지."""
    result["_measurement_representativeness"] = _HEIGHT_CAVEAT
    return result


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

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    이 문장에는 출처·기준일자(데이터의 실제 측정 시각)·원문 링크가 이미 모두 포함되어 있다.
    요약하거나 일부만 옮기지 말고 문장 전체를 그대로 쓸 것.

    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    측정소 채취구 높이 때문에 이 수치가 보행자 실제 체감농도와 다를 수 있다는 대표성 한계이며,
    보고서 작성자가 이 데이터를 그대로 인용해도 될지 판단하는 데 필요한 기본 정보다.

    ⚠️ 필수(생략 불가): 각 행에 포함된 station_intake_height_m(채취구 높이, m)과
    station_location_address(측정소 위치 주소)를 답변에 반드시 함께 표시하라. "높다/낮다" 같은
    정성적 표현으로 뭉뚱그리지 말고, 실제 수치(예: "19.3m")와 주소를 그대로 옮길 것. 매칭되는
    높이정보가 없는 측정소는 station_intake_height_m이 null이며, 이 경우에도 "높이정보 없음"이라고
    명시해야 한다(조용히 생략 금지).

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

    heights = await _get_station_heights()
    rows = _attach_station_info(rows, heights)

    citation = _citation("OA-1200", rows=rows)
    return _with_height_caveat({
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    })


@mcp.tool()
async def get_seoul_average_air_quality(cai_grade: str = "", start: int = 1, end: int = 5) -> dict:
    """
    서울시 25개 자치구의 대기환경정보 측정수치를 합산·평균낸 "서울시 전체 평균" 현황을 조회한다.
    (OA-1201 기반, 서비스명: ListAvgOfSeoulAirQualityService)

    ※ 자치구별/측정소별 개별 수치가 아니라, 서울시 전체를 하나의 값으로 합산한 도시 단위
    지표이다. 특정 자치구나 측정소의 수치가 필요하면 이 도구 대신 get_realtime_air_quality를
    사용할 것. 이 둘을 혼동해서 "서울시 평균"을 "특정 자치구 수치"인 것처럼 답변하지 말 것.

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    ※ 이 API 응답에는 측정일시 필드가 없다. "_citation_required" 문장에는 실제 측정시각
    대신 "조회 시점 기준" 안내문이 이미 담겨 있으니, 임의로 시각을 지어내지 말고 그 문장을
    그대로 출력할 것.

    ※ 이 데이터셋은 통합대기환경지수(CAI)와 등급(CAI_GRD), 지배오염물질(CRST_SBSTN)을
    서울시가 자체적으로 이미 계산해 제공한다. 다른 도구(get_realtime_air_quality 등)처럼
    Claude가 개별 오염물질 값으로 CAI를 다시 계산하지 않고, 원본 값을 그대로 사용하고
    인용할 것 (중복 계산으로 인한 값 불일치 방지).

    응답 필드 의미 (data.seoul.go.kr 예제 기준으로 확인):
        CAI_GRD: 통합대기환경지수 등급 (좋음/보통/나쁨/매우나쁨)
        CAI: 통합대기환경지수 (수치)
        CRST_SBSTN: 지수를 결정한 오염물질명
        NTDX: 이산화질소 평균 (ppm)
        OZON: 오존 평균 (ppm)
        CBMX: 일산화탄소 평균 (ppm)
        SPDX: 아황산가스 평균 (ppm)
        PM: 미세먼지 PM10 평균 (μg/m³)
        FPM: 초미세먼지 PM2.5 평균 (μg/m³)

    각 행에는 CAI_GRD 값에 대응하는 cai_guidance(야외활동 행동요령 안내문)가 함께 담겨 있다.

    Args:
        cai_grade: 통합대기환경지수 등급으로 필터링 (예: "좋음", "보통", "나쁨", "매우나쁨"). 비워두면 전체.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 5)
    """
    _check_key()

    parts = [BASE_URL, SEOUL_API_KEY, "json", "ListAvgOfSeoulAirQualityService", str(start), str(end)]
    if cai_grade:
        parts.append(cai_grade)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("ListAvgOfSeoulAirQualityService", {}).get("row", [])

    for r in rows:
        grade = r.get("CAI_GRD")
        if grade in _GRADE_GUIDANCE:
            r["cai_guidance"] = _GRADE_GUIDANCE[grade]

    citation = _citation("OA-1201", rows=rows)
    return {
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    }


@mcp.tool()
async def get_hourly_air_quality(
    date: str, hour: str = "", district: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    특정 날짜(또는 특정 시)의 자치구별 시간평균 대기오염도를 조회한다. (OA-2275 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    이 문장에는 출처·기준일자(데이터의 실제 측정 시각)·원문 링크가 이미 모두 포함되어 있다.
    요약하거나 일부만 옮기지 말고 문장 전체를 그대로 쓸 것.

    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    측정소 채취구 높이 때문에 이 수치가 보행자 실제 체감농도와 다를 수 있다는 대표성 한계이며,
    보고서 작성자가 이 데이터를 그대로 인용해도 될지 판단하는 데 필요한 기본 정보다.

    ⚠️ 필수(생략 불가): 각 행에 포함된 station_intake_height_m(채취구 높이, m)과
    station_location_address(측정소 위치 주소)를 답변에 반드시 함께 표시하라. "높다/낮다" 같은
    정성적 표현으로 뭉뚱그리지 말고, 실제 수치(예: "19.3m")와 주소를 그대로 옮길 것. 매칭되는
    높이정보가 없는 측정소는 station_intake_height_m이 null이며, 이 경우에도 "높이정보 없음"이라고
    명시해야 한다(조용히 생략 금지).

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

    heights = await _get_station_heights()
    rows = _attach_station_info(rows, heights)

    citation = _citation("OA-2275", rows=rows)
    return _with_height_caveat({
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    })


@mcp.tool()
async def get_roadside_air_quality(
    road: str = "", station_name: str = "", start: int = 1, end: int = 25
) -> dict:
    """
    서울시 도로변/입체대기 측정소별 실시간 대기환경 현황을 조회한다. (OA-2223 기반)
    ※ 자치구 도시대기측정망과는 별도로, 도로변(일반도로/전용차로/중앙차로)에 설치된
    측정소에서 측정한 값이며 최종검증 전 실시간(잠정치) 자료이다.

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    이 문장에는 출처·기준일자(데이터의 실제 측정 시각)·원문 링크가 이미 모두 포함되어 있다.
    요약하거나 일부만 옮기지 말고 문장 전체를 그대로 쓸 것.

    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    측정소 채취구 높이 때문에 이 수치가 보행자 실제 체감농도와 다를 수 있다는 대표성 한계이며,
    보고서 작성자가 이 데이터를 그대로 인용해도 될지 판단하는 데 필요한 기본 정보다.

    ⚠️ 필수(생략 불가): 각 행에 포함된 station_intake_height_m(채취구 높이, m)과
    station_location_address(측정소 위치 주소)를 답변에 반드시 함께 표시하라. "높다/낮다" 같은
    정성적 표현으로 뭉뚱그리지 말고, 실제 수치(예: "19.3m")와 주소를 그대로 옮길 것. 매칭되는
    높이정보가 없는 측정소는 station_intake_height_m이 null이며, 이 경우에도 "높이정보 없음"이라고
    명시해야 한다(조용히 생략 금지).

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

    heights = await _get_station_heights()
    rows = _attach_station_info(rows, heights)

    citation = _citation("OA-2223", rows=rows)
    return _with_height_caveat({
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    })


@mcp.tool()
async def get_zonal_hourly_air_quality(
    date: str, hour: str, sarea: str = "", station_name: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    특정 날짜·시각의 권역별/측정소별 시간평균 대기환경 정보를 조회한다. (OA-2221 기반, 서비스명: TimeAverageCityAir)
    ※ 데이터셋 이름은 "기간별"이지만 실제로는 여러 날짜를 한 번에 조회하는 것이 아니라,
    지정한 "특정 한 시각"의 데이터를 조회하는 API이다. 여러 시각을 보려면 이 도구를 반복 호출해야 한다.

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    이 문장에는 출처·기준일자(데이터의 실제 측정 시각)·원문 링크가 이미 모두 포함되어 있다.
    요약하거나 일부만 옮기지 말고 문장 전체를 그대로 쓸 것.

    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    측정소 채취구 높이 때문에 이 수치가 보행자 실제 체감농도와 다를 수 있다는 대표성 한계이며,
    보고서 작성자가 이 데이터를 그대로 인용해도 될지 판단하는 데 필요한 기본 정보다.

    ⚠️ 필수(생략 불가): 각 행에 포함된 station_intake_height_m(채취구 높이, m)과
    station_location_address(측정소 위치 주소)를 답변에 반드시 함께 표시하라. "높다/낮다" 같은
    정성적 표현으로 뭉뚱그리지 말고, 실제 수치(예: "19.3m")와 주소를 그대로 옮길 것. 매칭되는
    높이정보가 없는 측정소는 station_intake_height_m이 null이며, 이 경우에도 "높이정보 없음"이라고
    명시해야 한다(조용히 생략 금지).

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

    citation = _citation("OA-2221", rows=rows)

    heights = await _get_station_heights()
    graded_rows = _attach_station_info(graded_rows, heights)

    return _with_height_caveat({
        "count": len(graded_rows),
        "data": graded_rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    })


@mcp.tool()
async def get_zonal_daily_air_quality(
    date: str, sarea: str = "", station_name: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    특정 날짜의 권역별/측정소별 일평균 대기환경 정보를 조회한다. (OA-2220 기반, 서비스명: DailyAverageCityAir)
    ※ get_zonal_hourly_air_quality(OA-2221, 시간평균)의 "하루 단위" 버전이다. 시간별 변화가
    아니라 그 날 하루 전체의 평균값이 필요할 때 이 도구를 사용할 것.

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    이 문장에는 출처·기준일자(조회한 날짜)·원문 링크가 이미 모두 포함되어 있다.
    요약하거나 일부만 옮기지 말고 문장 전체를 그대로 쓸 것.

    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    측정소 채취구 높이 때문에 이 수치가 보행자 실제 체감농도와 다를 수 있다는 대표성 한계이며,
    보고서 작성자가 이 데이터를 그대로 인용해도 될지 판단하는 데 필요한 기본 정보다.

    ⚠️ 필수(생략 불가): 각 행에 포함된 station_intake_height_m(채취구 높이, m)과
    station_location_address(측정소 위치 주소)를 답변에 반드시 함께 표시하라. "높다/낮다" 같은
    정성적 표현으로 뭉뚱그리지 말고, 실제 수치(예: "19.3m")와 주소를 그대로 옮길 것. 매칭되는
    높이정보가 없는 측정소는 station_intake_height_m이 null이며, 이 경우에도 "높이정보 없음"이라고
    명시해야 한다(조용히 생략 금지).

    자치구 단위가 아니라 권역(SAREA_NM, 예: 도심권/서북권/동북권/서남권/동남권) 단위로 묶여서 나온다.

    응답 필드 의미 (data.seoul.go.kr 예제 기준으로 확인):
        MSRMT_YMD: 측정일자 (YYYYMMDD)
        SAREA_NM: 권역명
        MSRSTN_NM: 측정소명
        PM: 미세먼지 일평균 (μg/m³)
        FPM: 초미세먼지 일평균 (μg/m³)
        OZON: 오존 일평균 (ppm)
        NTDX: 이산화질소 일평균 (ppm)
        CBMX: 일산화탄소 일평균 (ppm)
        SPDX: 아황산가스 일평균 (ppm)

    각 행에는 환경부 통합대기환경지수(CAI) 기준으로 직접 계산한
    cai_index(지수), cai_grade(좋음/보통/나쁨/매우나쁨), cai_determining_pollutant(지배오염물질),
    cai_guidance(야외활동 행동요령)가 함께 담겨 있다.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801")
        sarea: 권역명 (예: "도심권", "서북권", "동북권", "서남권", "동남권"). 비워두면 전체 권역.
        station_name: 측정소명 (예: "강남구"). 비워두면 전체 측정소.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()

    parts = [BASE_URL, SEOUL_API_KEY, "json", "DailyAverageCityAir", str(start), str(end), date]
    if sarea:
        parts.append(sarea)
    if station_name:
        parts.append(station_name)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("DailyAverageCityAir", {}).get("row", [])
    rows = [_add_air_quality_grade(r) for r in rows]

    heights = await _get_station_heights()
    rows = _attach_station_info(rows, heights)

    citation = _citation("OA-2220", rows=rows)
    return _with_height_caveat({
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    })


@mcp.tool()
async def get_daily_air_quality(date: str, station_name: str = "", start: int = 1, end: int = 100) -> dict:
    """
    특정 날짜의 측정소별(자치구 측정소 + 도로변 측정소 포함) 일평균 대기오염도 정보를 조회한다.
    (OA-2218 기반, 서비스명: DailyAverageAirQuality)
    ※ get_hourly_air_quality(OA-2275, 시간평균)의 "하루 단위" 버전이다. 시간별 변화가 아니라
    그 날 하루 전체의 평균값이 필요할 때 이 도구를 사용할 것.
    ※ get_zonal_daily_air_quality(OA-2220)와 달리 권역(SAREA_NM) 구분이 없고, 개별 측정소명
    (자치구명 또는 도로변 측정소명)으로만 조회된다.

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    이 문장에는 출처·기준일자(조회한 날짜)·원문 링크가 이미 모두 포함되어 있다.
    요약하거나 일부만 옮기지 말고 문장 전체를 그대로 쓸 것.

    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    측정소 채취구 높이 때문에 이 수치가 보행자 실제 체감농도와 다를 수 있다는 대표성 한계이며,
    보고서 작성자가 이 데이터를 그대로 인용해도 될지 판단하는 데 필요한 기본 정보다.

    ⚠️ 필수(생략 불가): 각 행에 포함된 station_intake_height_m(채취구 높이, m)과
    station_location_address(측정소 위치 주소)를 답변에 반드시 함께 표시하라. "높다/낮다" 같은
    정성적 표현으로 뭉뚱그리지 말고, 실제 수치(예: "19.3m")와 주소를 그대로 옮길 것. 매칭되는
    높이정보가 없는 측정소는 station_intake_height_m이 null이며, 이 경우에도 "높이정보 없음"이라고
    명시해야 한다(조용히 생략 금지).

    응답 필드 의미 (data.seoul.go.kr 예제 기준으로 확인):
        MSRMT_DT: 측정일자 (YYYYMMDD)
        MSRSTN_NM: 측정소명 (자치구명 또는 도로변 측정소명)
        NTDX: 이산화질소 일평균 (ppm)
        OZON: 오존 일평균 (ppm)
        CBMX: 일산화탄소 일평균 (ppm)
        SPDX: 아황산가스 일평균 (ppm)
        PM: 미세먼지 일평균 (μg/m³)
        FPM: 초미세먼지 일평균 (μg/m³)

    각 행에는 환경부 통합대기환경지수(CAI) 기준으로 직접 계산한
    cai_index(지수), cai_grade(좋음/보통/나쁨/매우나쁨), cai_determining_pollutant(지배오염물질),
    cai_guidance(야외활동 행동요령)가 함께 담겨 있다.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801")
        station_name: 측정소명 (예: "강남구", "강변북로"). 비워두면 전체 측정소.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()

    parts = [BASE_URL, SEOUL_API_KEY, "json", "DailyAverageAirQuality", str(start), str(end), date]
    if station_name:
        parts.append(station_name)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("DailyAverageAirQuality", {}).get("row", [])
    rows = [_add_air_quality_grade(r) for r in rows]

    heights = await _get_station_heights()
    rows = _attach_station_info(rows, heights)

    citation = _citation("OA-2218", rows=rows)
    return _with_height_caveat({
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    })


@mcp.tool()
async def get_yearly_pm10_alerts(year: str = "", start: int = 1, end: int = 30) -> dict:
    """
    서울시 연도별 미세먼지(PM10) 경보발령 현황을 조회한다. (OA-2228 기반)
    자치구 구분 없이 서울시 전체 기준 연도별 통계입니다.

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    이 문장에는 출처·기준일자(조회된 연도 범위 + 포털 등록 갱신일)·원문 링크가 이미 모두 포함되어 있다.
    요약하거나 일부만 옮기지 말고 문장 전체를 그대로 쓸 것.

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

    citation = _citation("OA-2228", rows=rows, year_field="YR")
    result = {
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    }
    if warning:
        result["_data_quality_warning"] = warning
    return result


@mcp.tool()
async def get_station_height_info(station_name: str = "", start: int = 1, end: int = 40) -> dict:
    """
    서울시 대기오염물질 측정소별 채취구 높이 정보를 조회한다. (OA-12855 기반, 서비스명: airHgt)
    ※ 이 데이터셋은 대기질 수치(농도) 자체가 아니라, 각 측정소의 채취구가 지상에서
    얼마나 높은 곳에 설치되어 있는지를 알려주는 참고 정보이다. 측정값을 해석할 때
    "이 수치가 지표면 근처 공기인지, 높은 곳 공기인지"를 감안하는 용도로 쓴다.

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    ※ 이 데이터셋은 API 응답에 측정일시/갱신일자 필드가 없는 정적 참고정보이므로,
    "_citation_required" 문장에는 실제 날짜 대신 "이 데이터셋에는 자동 갱신일자가 없다"는
    사실과 원문 링크가 담겨 있다. 이 경우에도 문장을 임의로 바꾸거나 날짜를 지어내지 말고,
    주어진 문장을 그대로 출력할 것.

    응답 필드 의미 (data.seoul.go.kr 예제 기준으로 확인):
        SEQ: 순서
        MSRSTN_NM: 측정소명
        ROAD_NM_ADDR: 도로명주소
        MSRSTN_HGT: 채취구 높이 (m)
        SE: 구분

    Args:
        station_name: 측정소명 (예: "종로구"). 비워두면 전체 측정소.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 40)
    """
    _check_key()
    url = f"{BASE_URL}/{SEOUL_API_KEY}/json/airHgt/{start}/{end}/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("airHgt", {}).get("row", [])

    if station_name:
        rows = [r for r in rows if station_name in r.get("MSRSTN_NM", "")]

    citation = _citation("OA-12855", rows=rows)
    return {
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
