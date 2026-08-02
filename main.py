"""
서울시 대기환경정보 MCP 서버
- 원본 데이터: 서울 열린데이터광장 (data.seoul.go.kr)
- 담당부서: 서울특별시 기후환경본부 대기정책과

인증키 주입 방식:
  [필수] 쿼리 파라미터 방식 — 키 없이 접속하면 차단됨
        https://서버주소/mcp?key={서울열린데이터광장API키}
        예) https://seoul-air-quality-mcp.fly.dev/mcp?key=abc123xyz

인증키는 코드에 절대 하드코딩하지 않는다.
"""

import contextvars
import os

import httpx
import uvicorn
from fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

# ─────────────────────────────────────────────────────────────
# 요청별 API 키 — ?key=... 쿼리 파라미터에서 추출
# ─────────────────────────────────────────────────────────────
_request_api_key: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_api_key", default=""
)


def _get_api_key() -> str:
    """현재 요청의 ?key= 쿼리 파라미터에서 추출한 API 키를 반환한다."""
    return _request_api_key.get()


BASE_URL = "http://openapi.seoul.go.kr:8088"

mcp = FastMCP(
    "seoul-air-quality-mcp",
    instructions=(
        "이 서버의 모든 도구는 응답에 \"_citation_required\" 필드(출처 문장 전체)를 포함한다. "
        "다음 두 규칙은 예외 없이 항상 지킬 것.\n"
        "\n"
        "[규칙 1] 원문 링크는 반드시 URL 문자열 그대로 노출한다. "
        "[원문 링크](https://...) 같은 마크다운 하이퍼링크로 감싸거나, '원문 링크'라는 "
        "글자 뒤에 링크를 숨기는 형태로 표시하지 말 것. 반드시 "
        "\"원문 링크: https://data.seoul.go.kr/...\" 처럼 URL 전체 문자열이 화면에 그대로 보여야 한다.\n"
        "\n"
        "[규칙 2] 한 번의 답변에서 이 서버의 도구를 2개 이상 호출했다면, 각 도구가 반환한 "
        "\"_citation_required\" 문장을 하나로 요약하거나 병합해서 새로 쓰지 말고, 각 도구별로 "
        "완전한 문장을 줄바꿈해서 전부 따로 출력할 것 (예: 도구 A 출처 문장 한 줄, 도구 B 출처 "
        "문장 한 줄). 병합 과정에서 요약하다가 링크나 기준일자가 누락되는 실수가 실제로 있었으니 "
        "특히 주의할 것.\n"
        "\n"
        "이 두 규칙을 어기면(링크 누락, 하이퍼링크로 은폐, 여러 출처를 하나로 뭉개기) 공무원 "
        "보고서의 데이터 출처 추적이 불가능해지므로 절대 허용되지 않는다."
    ),
)


def _check_key():
    if not _get_api_key():
        raise RuntimeError(
            "API 키가 없습니다. URL에 ?key=본인키 를 붙여서 연결하세요.\n"
            "연결 URL 형식: https://seoul-air-quality-mcp.fly.dev/mcp?key=본인서울API키\n"
            "API 키 발급: https://data.seoul.go.kr (회원가입 후 인증키 관리 메뉴)"
        )


# ─────────────────────────────────────────────────────────────
# ?key=... 쿼리 파라미터에서 API 키를 추출하는 ASGI 미들웨어
# 키가 없으면 HTTP 401로 차단 — 서버 비용 보호
# ─────────────────────────────────────────────────────────────
class APIKeyExtractorMiddleware:
    """
    모든 HTTP 요청의 ?key= 쿼리 파라미터에서 서울 API 키를 추출한다.
    키가 없으면 HTTP 401 응답을 돌려보내고 서버(FastMCP)로 전달하지 않는다.

    연결 URL 예시: https://seoul-air-quality-mcp.fly.dev/mcp?key=abc123xyz
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            # 쿼리 파라미터 파싱
            query_string = scope.get("query_string", b"").decode("utf-8")
            params: dict[str, str] = {}
            for part in query_string.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k.strip()] = v.strip()

            api_key = params.get("key", "").strip()

            if not api_key:
                # API 키 없음 → 즉시 401 반환, FastMCP에 전달 안 함
                body = (
                    "❌ API 키가 필요합니다.\n\n"
                    "연결 URL 형식:\n"
                    "  https://seoul-air-quality-mcp.fly.dev/mcp?key=본인서울API키\n\n"
                    "API 키 발급:\n"
                    "  https://data.seoul.go.kr → 회원가입 → 인증키 관리\n"
                ).encode("utf-8")
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"text/plain; charset=utf-8"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return

            # 키를 요청 컨텍스트에 저장 후 FastMCP로 전달
            token = _request_api_key.set(api_key)
            try:
                await self.app(scope, receive, send)
            finally:
                _request_api_key.reset(token)
            return

        # HTTP 외(WebSocket 등)는 그대로 통과
        await self.app(scope, receive, send)


# 각 도구가 사용하는 원본 데이터셋 정보 (공무원 보고서 작성 시 출처 확인용)
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
        "portal_last_verified": "2025-11-04 (확인일 2026-08-02 기준)",
    },
    "OA-12855": {
        "dataset_name": "서울시 대기오염물질 측정소 높이 정보",
        "dataset_id": "OA-12855",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-12855/S/1/datasetView.do",
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
    "OA-2217": {
        "dataset_name": "서울시 월별 평균 대기오염도 정보",
        "dataset_id": "OA-2217",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-2217/S/1/datasetView.do",
    },
    "OA-2224": {
        "dataset_name": "서울시 도로변/입체대기 기간별 일평균 대기환경 현황",
        "dataset_id": "OA-2224",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-2224/S/1/datasetView.do",
    },
    "OA-15140": {
        "dataset_name": "서울시 대기오염전광판 위치정보",
        "dataset_id": "OA-15140",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-15140/S/1/datasetView.do",
        "static_reference_note": (
            "이 데이터셋은 실시간 측정값이 아닌 정적 참고정보(대기오염전광판 설치 위치·좌표)이며, "
            "API 응답에 갱신일자 필드가 없습니다. 최신 여부는 원문 링크의 데이터셋 상세페이지에서 "
            "직접 확인해야 합니다."
        ),
    },
    "OA-16122": {
        "dataset_name": "서울시 대기오염물질배출시설설치사업장 인허가 정보",
        "dataset_id": "OA-16122",
        "provider": "서울특별시 기후환경본부 대기정책과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-16122/S/1/datasetView.do",
        "static_reference_note": (
            "이 데이터셋은 대기질 수치가 아니라 사업장 인허가/영업상태 스냅샷이며, "
            "포털 설명에 따르면 3일 전 자료 기준으로 제공됩니다. 정확한 기준일자는 각 행의 "
            "LAST_MDFCN_YMD(최종수정일자)·DATA_UPDT_YMD(데이터갱신일자)를 확인해야 합니다."
        ),
    },
    "OA-15515": {
        "dataset_name": "서울시 대기오염 측정항목 정보",
        "dataset_id": "OA-15515",
        "provider": "서울특별시 보건환경연구원 대기질통합분석센터",
        "source_url": "https://data.seoul.go.kr/dataList/OA-15515/S/1/datasetView.do",
        "static_reference_note": (
            "이 데이터셋은 실시간 측정값이 아닌 측정항목 코드 정의표(단위·소수점자리수·"
            "경보색상별 기준치 등)이며, 다른 도구들과 제공기관도 다릅니다(보건환경연구원 "
            "대기질통합분석센터). 실제 측정값을 조회하려면 대기정책과 제공 도구를 사용하고, "
            "이 도구는 그 수치를 해석하기 위한 참고 정보로만 사용하세요."
        ),
    },
    "OA-15516": {
        "dataset_name": "서울시 대기오염 측정소 정보",
        "dataset_id": "OA-15516",
        "provider": "서울특별시 보건환경연구원 대기질통합분석센터",
        "source_url": "https://data.seoul.go.kr/dataList/OA-15516/S/1/datasetView.do",
        "static_reference_note": (
            "이 데이터셋은 실시간 측정값이 아닌 측정소 메타정보(측정소명·주소·공인코드)이며, "
            "제공기관은 보건환경연구원 대기질통합분석센터입니다. 이 데이터셋에는 좌표(위도/경도) "
            "필드가 없으므로, 지도 표시가 필요하면 MSRSTN_ADDR(주소)를 별도 지오코딩해야 합니다."
        ),
    },
    "OA-15526": {
        "dataset_name": "서울시 대기오염 측정정보(1시간단위)",
        "dataset_id": "OA-15526",
        "provider": "서울특별시 보건환경연구원 대기질통합분석센터",
        "source_url": "https://data.seoul.go.kr/dataList/OA-15526/S/1/datasetView.do",
    },
    "OA-1256": {
        "dataset_name": "서울시 굴뚝 측정 정보",
        "dataset_id": "OA-1256",
        "provider": "서울특별시 기후환경본부 자원회수시설추진단 자원회수시설과",
        "source_url": "https://data.seoul.go.kr/dataList/OA-1256/S/1/datasetView.do",
    },
}

_DATETIME_FIELD_CANDIDATES = ["MSRDT", "MSRMT_DT", "MSRDATE", "MSRMT_YMD", "MSRMT_MM"]


def _format_msrdt(raw: str) -> str:
    s = str(raw)
    try:
        if len(s) >= 12:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"
        if len(s) >= 10:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}시"
        if len(s) >= 8:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
        if len(s) == 6:
            return f"{s[0:4]}-{s[4:6]}"
    except Exception:
        pass
    return s


def _latest_reference_datetime(rows: list) -> str | None:
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
        f"| 원문 링크(URL 문자열 그대로 표시, 하이퍼링크로 가리지 말 것): {info.get('source_url')}"
    )
    if info.get("portal_last_verified"):
        citation_text += f" | 포털 등록 갱신일: {info['portal_last_verified']}"

    info["reference_date"] = reference_date
    info["citation_text"] = citation_text
    return info


def _source(dataset_id: str) -> dict:
    return _citation(dataset_id)


_HEIGHT_CAVEAT = (
    "⚠️ 대표성 참고: 각 측정소 행의 station_intake_height_m(채취구 높이, m 단위 실측값)과 "
    "station_location_address(측정소 위치)를 함께 확인하세요. '높다/낮다'로 뭉뚱그리지 말고, "
    "실제 수치와 주소를 답변에 명시할 것. 채취구가 지상보다 높은 곳에 설치된 경우, 실제 보행자가 "
    "지표면 근처에서 체감하는 농도와 다를 수 있습니다(특히 미세먼지는 지표면에 가까울수록 농도가 높은 경향)."
)


async def _get_station_heights() -> dict:
    try:
        _check_key()
        url = f"{BASE_URL}/{_get_api_key()}/json/airHgt/1/100/"
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
    result["_measurement_representativeness"] = _HEIGHT_CAVEAT
    return result


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
    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    ⚠️ 필수(생략 불가): 각 행의 station_intake_height_m(채취구 높이, m)과
    station_location_address(측정소 위치 주소)를 답변에 반드시 함께 표시하라.

    Args:
        district: 자치구 이름 (예: "강남구"). 비워두면 전체 자치구 반환.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 25)
    """
    _check_key()
    url = f"{BASE_URL}/{_get_api_key()}/json/RealtimeCityAir/{start}/{end}/"

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
    서울시 25개 자치구의 대기환경정보를 합산·평균낸 "서울시 전체 평균" 현황을 조회한다.
    (OA-1201 기반, 서비스명: ListAvgOfSeoulAirQualityService)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        cai_grade: 통합대기환경지수 등급으로 필터링 (예: "좋음", "보통", "나쁨", "매우나쁨").
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 5)
    """
    _check_key()

    parts = [BASE_URL, _get_api_key(), "json", "ListAvgOfSeoulAirQualityService", str(start), str(end)]
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
    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    ⚠️ 필수(생략 불가): 각 행의 station_intake_height_m과 station_location_address를 표시하라.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801")
        hour: 특정 시(00~23) 두 자리 숫자로 (예: "13"). 비워두면 해당 날짜의 전체 시간대 조회.
        district: 자치구 이름 (예: "종로구"). 비워두면 서울시 전체.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()
    date_param = date + hour

    parts = [BASE_URL, _get_api_key(), "json", "TimeAverageAirQuality", str(start), str(end), date_param]
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

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.
    ⚠️ 필수(생략 불가): 각 행의 station_intake_height_m과 station_location_address를 표시하라.

    Args:
        road: 도로변구분 (예: "일반도로", "전용차로", "중앙차로"). 비워두면 전체.
        station_name: 측정소명 (예: "서울역"). 비워두면 전체.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 25)
    """
    _check_key()

    parts = [BASE_URL, _get_api_key(), "json", "RealtimeRoadsideStation", str(start), str(end)]
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
async def get_roadside_daily_air_quality(
    date: str = "", road: str = "", station_name: str = "", start: int = 1, end: int = 25
) -> dict:
    """
    서울시 도로변/입체대기 측정소별 일평균 대기환경 현황을 조회한다. (OA-2224 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801"). road/station_name을 쓰려면 필수.
        road: 도로변구분 (예: "일반도로"). date와 함께 지정할 것.
        station_name: 측정소명 (예: "서울역"). date와 함께 지정할 것.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 25)
    """
    _check_key()

    parts = [BASE_URL, _get_api_key(), "json", "DailyAverageRoadside", str(start), str(end)]
    if date:
        parts.append(date)
        if road:
            parts.append(road)
        if station_name:
            parts.append(station_name)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("DailyAverageRoadside", {}).get("row", [])
    rows = [_add_air_quality_grade(r) for r in rows]
    heights = await _get_station_heights()
    rows = _attach_station_info(rows, heights)

    citation = _citation("OA-2224", rows=rows)
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
    특정 날짜·시각의 권역별/측정소별 시간평균 대기환경 정보를 조회한다. (OA-2221 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.
    ⚠️ 필수(생략 불가): 응답의 "_measurement_representativeness" 문구도 답변에 함께 안내하라.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801")
        hour: 시(01~24) 두 자리 숫자로 (예: "11"). 24는 해당 날짜의 마지막 시간.
        sarea: 권역명 (예: "도심권", "서북권", "동북권", "서남권", "동남권").
        station_name: 측정소명 (예: "종로구").
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()
    msrmt_dt = date + hour + "00"

    parts = [BASE_URL, _get_api_key(), "json", "TimeAverageCityAir", str(start), str(end), msrmt_dt]
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
        r_for_grade["PM"] = r.get("PM_HOUR")
        r_for_grade = _add_air_quality_grade(r_for_grade)
        r_for_grade.pop("PM", None)
        graded_rows.append(r_for_grade)

    heights = await _get_station_heights()
    graded_rows = _attach_station_info(graded_rows, heights)

    citation = _citation("OA-2221", rows=rows)
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
    특정 날짜의 권역별/측정소별 일평균 대기환경 정보를 조회한다. (OA-2220 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801")
        sarea: 권역명 (예: "도심권", "서북권", "동북권", "서남권", "동남권").
        station_name: 측정소명.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()

    parts = [BASE_URL, _get_api_key(), "json", "DailyAverageCityAir", str(start), str(end), date]
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
    특정 날짜의 측정소별 일평균 대기오염도 정보를 조회한다. (OA-2218 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        date: 조회할 날짜, YYYYMMDD 형식 (예: "20260801")
        station_name: 측정소명 (예: "강남구"). 비워두면 전체.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()

    parts = [BASE_URL, _get_api_key(), "json", "DailyAverageAirQuality", str(start), str(end), date]
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
async def get_monthly_air_quality(month: str, station_name: str = "", start: int = 1, end: int = 100) -> dict:
    """
    특정 월의 측정소별 월평균 대기오염도 정보를 조회한다. (OA-2217 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        month: 조회할 월, YYYYMM 형식 (예: "202608")
        station_name: 측정소명 (예: "강남구"). 비워두면 전체.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()

    parts = [BASE_URL, _get_api_key(), "json", "MonthlyAverageAirQuality", str(start), str(end), month]
    if station_name:
        parts.append(station_name)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("MonthlyAverageAirQuality", {}).get("row", [])
    rows = [_add_air_quality_grade(r) for r in rows]
    heights = await _get_station_heights()
    rows = _attach_station_info(rows, heights)

    citation = _citation("OA-2217", rows=rows)
    return _with_height_caveat({
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    })


@mcp.tool()
async def get_air_pollution_board_locations(
    district: str = "", location: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    서울시 대기오염전광판 설치 위치 정보를 조회한다. (OA-15140 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        district: 자치구 이름 (예: "중구"). 비워두면 전체.
        location: 설치위치 문자열 검색 (예: "시청역").
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()

    parts = [BASE_URL, _get_api_key(), "json", "airPollutionBrdInfo", str(start), str(end)]
    if district:
        parts.append(district)
        if location:
            parts.append(location)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("airPollutionBrdInfo", {}).get("row", [])
    if not district and location:
        rows = [r for r in rows if location in r.get("INSTL_PSTN", "")]

    citation = _citation("OA-15140", rows=rows)
    return {
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    }


@mcp.tool()
async def get_air_pollutant_emission_facilities(
    district: str = "", business_name: str = "", status: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    서울시 대기오염물질배출시설설치사업장의 인허가·영업상태 정보를 조회한다. (OA-16122 기반)

    ⚠️ XCRD/YCRD는 위도·경도가 아니라 중부원점TM(EPSG:5174) 좌표계다. 지도에 표시하려면 WGS84로 변환 필요.
    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        district: 주소에 포함될 자치구/지역명 (예: "강남구").
        business_name: 사업장명에 포함될 문자열 (예: "OO공장").
        status: 영업상태명 (예: "영업", "폐업", "휴업").
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()
    url = f"{BASE_URL}/{_get_api_key()}/json/LOCALDATA_093008/{start}/{end}/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("LOCALDATA_093008", {}).get("row", [])

    if district:
        rows = [r for r in rows if district in r.get("LOTNO_ADDR", "") or district in r.get("ROAD_NM_ADDR", "")]
    if business_name:
        rows = [r for r in rows if business_name in r.get("BPLC_NM", "")]
    if status:
        rows = [r for r in rows if status in r.get("SALS_STTS_NM", "")]

    citation = _citation("OA-16122", rows=rows)
    return {
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
        "_coordinate_system_warning": (
            "XCRD/YCRD는 위도·경도가 아니라 중부원점TM(EPSG:5174) 평면좌표입니다. "
            "지도 서비스에 그대로 입력하면 안 되며, 반드시 WGS84로 좌표변환 후 사용해야 합니다."
        ),
    }


@mcp.tool()
async def get_yearly_pm10_alerts(year: str = "", start: int = 1, end: int = 30) -> dict:
    """
    서울시 연도별 미세먼지(PM10) 경보발령 현황을 조회한다. (OA-2228 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    [데이터셋 상태] 확인일: 2026-08-02 / 2007~2025년 전 구간 값이 0으로 조회되어 원본 확인 필요.

    Args:
        year: 조회할 연도 (예: "2024"). 비워두면 전체 연도.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 30)
    """
    _check_key()
    url = f"{BASE_URL}/{_get_api_key()}/json/YearlyPM10Issue/{start}/{end}/"

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
    서울시 대기오염물질 측정소별 채취구 높이 정보를 조회한다. (OA-12855 기반)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        station_name: 측정소명 (예: "종로구"). 비워두면 전체.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 40)
    """
    _check_key()
    url = f"{BASE_URL}/{_get_api_key()}/json/airHgt/{start}/{end}/"

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


@mcp.tool()
async def get_air_pollution_item_info(item_code: str = "", start: int = 1, end: int = 10) -> dict:
    """
    서울시 대기오염 측정항목 코드 정의표를 조회한다. (OA-15515 기반, 보건환경연구원 제공)

    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        item_code: 측정항목 코드 (ITEM_CD). 비워두면 전체.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 10)
    """
    _check_key()
    if item_code:
        url = f"{BASE_URL}/{_get_api_key()}/json/airPolutionMeasuringItem/{start}/{end}/{item_code}/"
    else:
        url = f"{BASE_URL}/{_get_api_key()}/json/airPolutionMeasuringItem/{start}/{end}/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("airPolutionMeasuringItem", {}).get("row", [])
    citation = _citation("OA-15515", rows=rows)
    return {
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    }


@mcp.tool()
async def get_air_pollution_station_info(station_code: str = "", start: int = 1, end: int = 30) -> dict:
    """
    서울시 대기오염 측정소 정보(측정소명·주소·공인코드)를 조회한다. (OA-15516 기반, 보건환경연구원 제공)

    ⚠️ 이 데이터셋에는 위도/경도 좌표 필드가 없다. 지도 표시가 필요하면 주소를 별도 지오코딩해야 한다.
    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        station_code: 측정소 코드 (MSRSTN_CD). 비워두면 전체.
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 30)
    """
    _check_key()
    if station_code:
        url = f"{BASE_URL}/{_get_api_key()}/json/airPolutionMeasuringPlace/{start}/{end}/{station_code}/"
    else:
        url = f"{BASE_URL}/{_get_api_key()}/json/airPolutionMeasuringPlace/{start}/{end}/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("airPolutionMeasuringPlace", {}).get("row", [])
    citation = _citation("OA-15516", rows=rows)
    return {
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    }


@mcp.tool()
async def get_air_pollution_measurement(
    station_code: str = "", item_code: str = "", msrmt_dt: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    서울시 대기오염 측정정보(시간평균 실측값, 잠정치)를 조회한다. (OA-15526 기반, 보건환경연구원 제공)

    ⚠️ 잠정치: 국가(환경부/에어코리아)의 사후 검증을 거친 확정치가 아니다.
    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        station_code: 측정소 코드 (MSRSTN_CD).
        item_code: 측정항목 코드 (ITEM_CD).
        msrmt_dt: 측정일시 (예: "202608022100").
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()
    parts = [BASE_URL, _get_api_key(), "json", "airPolutionMeasuring1Hour", str(start), str(end)]
    if msrmt_dt:
        parts.append(msrmt_dt)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("airPolutionMeasuring1Hour", {}).get("row", [])
    if station_code:
        rows = [r for r in rows if str(r.get("MSRSTN_CD", "")) == str(station_code)]
    if item_code:
        rows = [r for r in rows if str(r.get("ITEM_CD", "")) == str(item_code)]

    citation = _citation("OA-15526", rows=rows)
    return {
        "count": len(rows),
        "data": rows,
        "_data_tier": "실시간 잠정치 (자치구 측정소 자체 보정값, 국가 사후검증 전 — 확정치 아님)",
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    }


@mcp.tool()
async def get_chimney_emission_measurement(
    facility_name: str = "", pollutant: str = "", start: int = 1, end: int = 100
) -> dict:
    """
    서울시 4개 자원회수시설(소각장) 굴뚝의 대기오염물질 자동측정값을 조회한다. (OA-1256 기반)

    ⚠️ 배출허용기준(법적 한도) 없음 — 초과 여부는 이 실측값만으로 단정하지 말 것.
    ⚠️ 필수(생략 불가): 답변 맨 끝 줄에 응답의 "_citation_required" 값을 그대로 출력하라.

    Args:
        facility_name: 시설명 (예: "강남", "노원", "마포", "양천").
        pollutant: 측정항목명 (예: "먼지").
        start: 조회 시작 인덱스 (기본 1)
        end: 조회 종료 인덱스 (기본 100)
    """
    _check_key()
    parts = [BASE_URL, _get_api_key(), "json", "CleanSYSService", str(start), str(end)]
    if facility_name:
        parts.append(facility_name)
        if pollutant:
            parts.append(pollutant)
    url = "/".join(parts) + "/"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("CleanSYSService", {}).get("row", [])
    citation = _citation("OA-1256", rows=rows)
    return {
        "count": len(rows),
        "data": rows,
        "_data_source": citation,
        "_citation_required": citation["citation_text"],
    }


# ─────────────────────────────────────────────────────────────
# 서버 실행
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # FastMCP ASGI 앱 생성 (stateless_http=True: 각 요청을 독립적으로 처리)
    fastmcp_app = mcp.http_app(transport="streamable-http", stateless_http=True)

    # URL /{api_key}/mcp 패턴을 처리하는 미들웨어로 감싸기
    app = APIKeyExtractorMiddleware(fastmcp_app)

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
