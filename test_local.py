"""
로컬 동작 확인용 테스트 스크립트.
MCP 서버 전체를 띄우지 않고, main.py에 정의된 도구 함수를 직접 호출해서
실제 서울시 API에서 데이터가 잘 오는지만 빠르게 확인한다.

실행 전 준비:
    export SEOUL_API_KEY="발급받은_인증키"      (윈도우 PowerShell: $env:SEOUL_API_KEY="발급받은_인증키")
    pip install -r requirements.txt

실행:
    python test_local.py
"""

import asyncio
import json
from datetime import date

from main import get_realtime_air_quality, get_hourly_air_quality


async def main():
    print("=" * 60)
    print("1) get_realtime_air_quality 테스트 (자치구 실시간 대기환경)")
    print("=" * 60)
    try:
        result = await get_realtime_air_quality(district="종로구")
        print(json.dumps(result, ensure_ascii=False, indent=2)[:1000])
        print(f"\n✅ 성공 - {result.get('count', 0)}건 조회됨\n")
    except Exception as e:
        print(f"❌ 실패: {e}\n")

    print("=" * 60)
    print("2) get_hourly_air_quality 테스트 (시간평균 대기오염도)")
    print("=" * 60)
    today = date.today().strftime("%Y%m%d")
    try:
        result = await get_hourly_air_quality(date=today, district="종로구")
        print(json.dumps(result, ensure_ascii=False, indent=2)[:1000])
        print(f"\n✅ 성공 - {result.get('count', 0)}건 조회됨\n")
    except Exception as e:
        print(f"❌ 실패: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
