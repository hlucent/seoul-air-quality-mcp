"""
서울시 대기환경 정보 MCP 서버
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


@mcp.tool()
async def get_realtime_air_quality(district: str = "", start: int = 1, end: int = 25) -> dict:
    """
    서울시 25개 자치구의 실시간 대기환경 현황을 조회한다. (OA-1200 기반)

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
        PM: 미세먼지 PM10 (㎍/㎥)
        FPM: 초미세먼지 PM2.5 (㎍/㎥)

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
    return {"count": len(rows), "data": rows}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
