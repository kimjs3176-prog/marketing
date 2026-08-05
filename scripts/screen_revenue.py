#!/usr/bin/env python3
"""사업자등록번호 목록에서 직전연도 매출액 50억 이상 기업을 골라낸다.

    # 1) 목록 정제만 (네트워크 없이 즉시 실행 가능)
    python scripts/screen_revenue.py normalize data/business_numbers.txt

    # 2) 국세청 상태조회로 폐업/간이과세자 걸러내기
    export DATA_GO_KR_API_KEY=...
    python scripts/screen_revenue.py status data/business_numbers.txt -o out/status.csv

    # 3) 매출액까지 조회해 최종 선별 (법인등록번호 매핑 필요)
    python scripts/screen_revenue.py screen data/business_numbers.txt \
        --crno-map data/crno_map.csv -o out/result.csv

    # 4) 응답 필드명 확인용 원본 덤프
    python scripts/screen_revenue.py probe --crno 1101110043221 --biz-year 2025
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import List, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.revenue_screener import (  # noqa: E402
    CSV_COLUMNS,
    DEFAULT_REVENUE_THRESHOLD_KRW,
    ChainedResolver,
    CrnoResolver,
    FscCorpOutlineClient,
    FscFinancialClient,
    FscNameCrnoResolver,
    HttpTransport,
    NtsBusinessStatusClient,
    RevenueScreener,
    ScreeningError,
    ScreeningRow,
    load_brn_table,
    select_qualified,
    summarize,
)

KEY_ENV_VARS = ("DATA_GO_KR_API_KEY", "PUBLIC_DATA_API_KEY", "FSC_BASIC_INFO_API_KEY")


def _resolve_key(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    for name in KEY_ENV_VARS:
        value = os.getenv(name)
        if value:
            return value
    raise SystemExit(
        "공공데이터포털 인증키가 없습니다. --service-key 로 넘기거나 "
        f"다음 환경변수 중 하나를 설정하세요: {', '.join(KEY_ENV_VARS)}"
    )


def _build_transport(args: argparse.Namespace) -> HttpTransport:
    return HttpTransport(
        timeout=args.timeout,
        max_retries=args.retries,
        sleep_between_calls=args.sleep,
    )


def _write_csv(path: str, rows: Sequence[ScreeningRow]) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_dict())


def _report_list(path: str, verify_checksum: bool) -> tuple[List[str], dict]:
    report, names = load_brn_table(path, verify_checksum=verify_checksum)
    print(f"입력 행수        : {report.total_rows:,}")
    print(f"유효 사업자번호  : {len(report.unique):,} (중복 제거 후)")
    print(f"중복 제거된 행수 : {report.duplicate_rows:,}")
    print(f"제외된 행수      : {len(report.rejected):,}")
    for reason, count in report.reason_counts.items():
        print(f"  - {reason:<18} {count:,}")
    if names:
        print(f"기업명 확보      : {len(names):,} / {len(report.unique):,}")
    return report.unique, names


def cmd_normalize(args: argparse.Namespace) -> int:
    unique, _ = _report_list(args.input, not args.no_checksum)
    if args.output:
        directory = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(directory, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write("\n".join(unique) + "\n")
        print(f"\n정제된 목록 저장: {args.output}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    unique, _ = _report_list(args.input, not args.no_checksum)
    client = NtsBusinessStatusClient(
        service_key=_resolve_key(args.service_key),
        transport=_build_transport(args),
    )

    print(f"\n국세청 상태조회 {len(unique):,}건 ({(len(unique) + 99) // 100} 배치)...")
    statuses = client.fetch(unique)

    rows: List[ScreeningRow] = []
    for brn in unique:
        status = statuses.get(brn)
        rows.append(
            ScreeningRow(
                brn=brn,
                formatted=f"{brn[0:3]}-{brn[3:5]}-{brn[5:10]}",
                nts_status=status.status if status else None,
                tax_type=status.tax_type if status else None,
                note="" if status and status.is_registered else "국세청 미등록 번호",
            )
        )

    active = sum(1 for b in statuses.values() if b.is_active)
    simplified = sum(1 for b in statuses.values() if b.cannot_reach_threshold)
    print(f"계속사업자   : {active:,}")
    print(f"간이과세자   : {simplified:,} (50억 미달 확정)")
    print(f"미등록/기타  : {len(unique) - active:,}")

    if args.output:
        _write_csv(args.output, rows)
        print(f"\n저장: {args.output}")
    return 0


def cmd_screen(args: argparse.Namespace) -> int:
    unique, names = _report_list(args.input, not args.no_checksum)
    key = _resolve_key(args.service_key)
    transport = _build_transport(args)

    # 보유 중인 CSV 매핑을 먼저 쓰고, 빠진 건만 기업명으로 조회해 호출량을 줄인다.
    stages = []
    if args.crno_map:
        csv_resolver = CrnoResolver.from_csv(args.crno_map)
        print(f"법인등록번호 매핑: {len(csv_resolver):,}건 로드 (CSV)")
        stages.append(csv_resolver)

    if names and not args.no_name_lookup:
        stages.append(
            FscNameCrnoResolver(
                client=FscCorpOutlineClient(service_key=key, transport=transport),
                names=names,
            )
        )
        print(f"기업명 기반 해석 : {len(names):,}건 대상 (금융위 기업개요조회)")

    if not stages:
        print(
            "\n경고: 법인등록번호를 얻을 경로가 없습니다. 금융위 재무 API는 crno만 받으므로 "
            "매출액 조회가 전부 건너뛰어집니다. 입력 파일에 기업명 컬럼을 추가하거나 "
            "--crno-map 을 지정하세요.",
            file=sys.stderr,
        )

    resolver = ChainedResolver(stages) if len(stages) != 1 else stages[0]

    if args.limit:
        unique = unique[: args.limit]
        print(f"--limit 적용: 상위 {len(unique):,}건만 조회")

    screener = RevenueScreener(
        financial_client=FscFinancialClient(service_key=key, transport=transport),
        status_client=None if args.skip_status else NtsBusinessStatusClient(key, transport=transport),
        resolver=resolver,
        threshold_krw=args.threshold,
        biz_year=args.biz_year,
        fallback_biz_year=None if args.no_fallback else args.biz_year - 1,
    )

    print(f"\n선별 기준: {args.biz_year}년 매출액 >= {args.threshold / 100_000_000:,.0f}억 원")
    try:
        rows = screener.screen(unique)
    except ScreeningError as exc:
        print(f"\n조회 실패: {exc}", file=sys.stderr)
        return 1

    stats = summarize(rows)
    print(f"\n총 {stats['total']:,}건 판정")
    print(f"  기준 충족   : {stats['qualified']:,}")
    print(f"  기준 미달   : {stats['below_threshold']:,}")
    print(f"  판정 불가   : {stats['undetermined']:,}")

    qualified = select_qualified(rows)
    if qualified:
        print(f"\n=== 직전연도 매출액 {args.threshold / 100_000_000:,.0f}억 이상 ===")
        for row in qualified[:50]:
            name = row.corp_name or "(기업명 미확보)"
            print(f"  {row.formatted}  {row.revenue_eok:>12,.1f}억  {name}")
        if len(qualified) > 50:
            print(f"  ... 외 {len(qualified) - 50:,}건 (전체는 CSV 확인)")

    if args.output:
        _write_csv(args.output, rows if args.include_all else qualified)
        print(f"\n저장: {args.output}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    """기업명으로 법인등록번호를 찾아 재사용 가능한 매핑 CSV로 저장한다.

    ``screen`` 을 여러 번 돌릴 때 같은 조회를 반복하지 않도록 분리해 두었다.
    확정되지 않은 건은 ``candidates`` 컬럼에 후보를 남겨 수동 확인을 받는다.
    """
    unique, names = _report_list(args.input, not args.no_checksum)
    if not names:
        print(
            "\n입력 파일에 기업명 컬럼이 없습니다. `사업자등록번호,기업명` 2열 CSV가 필요합니다.",
            file=sys.stderr,
        )
        return 2

    if args.limit:
        unique = unique[: args.limit]

    resolver = FscNameCrnoResolver(
        client=FscCorpOutlineClient(service_key=_resolve_key(args.service_key), transport=_build_transport(args)),
        names=names,
    )

    print(f"\n기업명 {len(unique):,}건 해석 중...")
    resolved, ambiguous, missing = 0, 0, 0
    rows = []
    for index, brn in enumerate(unique, start=1):
        try:
            identity = resolver.resolve(brn)
        except ScreeningError as exc:
            print(f"\n조회 실패({brn}): {exc}", file=sys.stderr)
            return 1

        if identity.crno:
            resolved += 1
        elif identity.is_ambiguous:
            ambiguous += 1
        else:
            missing += 1

        rows.append(
            {
                "brn": brn,
                "crno": identity.crno or "",
                "corp_name": identity.corp_name or names.get(brn, ""),
                "matched_by": identity.matched_by or "",
                "candidates": " | ".join(f"{name}({crno})" for crno, name in identity.candidates),
            }
        )
        if args.progress and index % args.progress == 0:
            print(f"  {index:,}/{len(unique):,} (확정 {resolved:,})")

    print(f"\n확정      : {resolved:,}")
    print(f"후보 다수 : {ambiguous:,} (수동 확인 필요)")
    print(f"미발견    : {missing:,}")

    if args.output:
        directory = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(directory, exist_ok=True)
        with open(args.output, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["brn", "crno", "corp_name", "matched_by", "candidates"]
            )
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n저장: {args.output}  (screen --crno-map 으로 재사용)")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    """응답 원본을 그대로 출력한다. 필드명/단위 확인용."""
    key = _resolve_key(args.service_key)
    transport = _build_transport(args)

    if args.brn:
        print("=== 국세청 사업자등록 상태조회 ===")
        try:
            statuses = NtsBusinessStatusClient(key, transport=transport).fetch([args.brn])
            print(json.dumps({k: vars(v) for k, v in statuses.items()}, ensure_ascii=False, indent=2))
        except ScreeningError as exc:
            print(f"실패: {exc}", file=sys.stderr)

    if args.corp_name:
        print("\n=== 금융위 기업기본정보 기업개요조회 ===")
        try:
            outlines = FscCorpOutlineClient(key, transport=transport).search(args.corp_name)
            if not outlines:
                print("(항목 없음)")
            for outline in outlines:
                print(json.dumps(outline.raw, ensure_ascii=False, indent=2))
                print(f"-> crno={outline.crno} corp_name={outline.corp_name} bizno={outline.bizno}")
            print(
                "\n확인 사항: 응답에 사업자등록번호 필드가 있으면 BIZNO_FIELD_CANDIDATES 에 "
                "추가하십시오. 있으면 동명이인 법인을 교차검증으로 걸러낼 수 있습니다."
            )
        except ScreeningError as exc:
            print(f"실패: {exc}", file=sys.stderr)

    if args.crno:
        print("\n=== 금융위 기업재무정보 요약재무제표 ===")
        try:
            records = FscFinancialClient(key, transport=transport).fetch(args.crno, args.biz_year)
            if not records:
                print("(항목 없음)")
            for record in records:
                print(json.dumps(record.raw, ensure_ascii=False, indent=2))
                print(f"-> 파싱된 매출액: {record.revenue_krw}")
        except ScreeningError as exc:
            print(f"실패: {exc}", file=sys.stderr)

    if not args.brn and not args.crno and not args.corp_name:
        print("--brn, --crno, --corp-name 중 하나는 필요합니다.", file=sys.stderr)
        return 2
    return 0


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--service-key", help="공공데이터포털 인증키 (Decoding 키)")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--sleep", type=float, default=0.0, help="호출 간 대기(초). 트래픽 제한 회피용")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_norm = sub.add_parser("normalize", help="목록 정제/중복제거 (네트워크 불필요)")
    p_norm.add_argument("input")
    p_norm.add_argument("-o", "--output")
    p_norm.add_argument("--no-checksum", action="store_true", help="체크섬 검증 생략")
    p_norm.set_defaults(func=cmd_normalize)

    p_status = sub.add_parser("status", help="국세청 사업자등록 상태조회")
    p_status.add_argument("input")
    p_status.add_argument("-o", "--output")
    p_status.add_argument("--no-checksum", action="store_true")
    _add_common(p_status)
    p_status.set_defaults(func=cmd_status)

    p_screen = sub.add_parser("screen", help="매출액 기준 최종 선별")
    p_screen.add_argument("input")
    p_screen.add_argument("-o", "--output")
    p_screen.add_argument("--no-checksum", action="store_true")
    p_screen.add_argument("--crno-map", help="brn,crno[,corp_name] CSV")
    p_screen.add_argument(
        "--no-name-lookup",
        action="store_true",
        help="기업명으로 법인등록번호를 조회하지 않음 (--crno-map 만 사용)",
    )
    p_screen.add_argument("--threshold", type=float, default=DEFAULT_REVENUE_THRESHOLD_KRW)
    p_screen.add_argument("--biz-year", type=int, default=2025, help="직전 사업연도 (기본 2025)")
    p_screen.add_argument("--no-fallback", action="store_true", help="직전연도 없을 때 전년도로 대체하지 않음")
    p_screen.add_argument("--skip-status", action="store_true", help="국세청 상태조회 건너뛰기")
    p_screen.add_argument("--include-all", action="store_true", help="미달/불가 건도 CSV에 포함")
    p_screen.add_argument("--limit", type=int, help="앞 N건만 조회 (테스트용)")
    _add_common(p_screen)
    p_screen.set_defaults(func=cmd_screen)

    p_resolve = sub.add_parser("resolve", help="기업명 → 법인등록번호 매핑 CSV 생성")
    p_resolve.add_argument("input", help="`사업자등록번호,기업명` 2열 CSV")
    p_resolve.add_argument("-o", "--output")
    p_resolve.add_argument("--no-checksum", action="store_true")
    p_resolve.add_argument("--limit", type=int, help="앞 N건만 조회")
    p_resolve.add_argument("--progress", type=int, default=100, help="N건마다 진행 상황 출력")
    _add_common(p_resolve)
    p_resolve.set_defaults(func=cmd_resolve)

    p_probe = sub.add_parser("probe", help="응답 원본 덤프 (필드명/단위 확인)")
    p_probe.add_argument("--brn", help="사업자등록번호 10자리")
    p_probe.add_argument("--crno", help="법인등록번호 13자리")
    p_probe.add_argument("--corp-name", help="기업명 (기업개요조회 확인용)")
    p_probe.add_argument("--biz-year", type=int, default=2025)
    _add_common(p_probe)
    p_probe.set_defaults(func=cmd_probe)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
