// 기업별 국유특허 기술이전 제안서(.docx) 생성 — 기술요약서는 붙임으로 첨부
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  ShadingType, AlignmentType, BorderStyle, PageBreak, Footer, PageNumber,
  LevelFormat, VerticalAlign,
} = require("docx");

const DIR = __dirname;
const OUT = path.join(DIR, "..", "제안서");
const matches = JSON.parse(fs.readFileSync(path.join(DIR, "matches.json"), "utf8"));
const companies = JSON.parse(fs.readFileSync(path.join(DIR, "companies.json"), "utf8"));

const FONT = "맑은 고딕";
const NAVY = "1F3864";
const HEAD_FILL = "DCE6F2";
const LABEL_FILL = "F2F2F2";
const DATE = "2026. 10. 26.";
const ORG = "한국농업기술진흥원 기술거래이전팀";
const TEL = "063-919-1325";
const NUM = "①②③④⑤";
const W = 9638; // A4, 좌우 여백 1134 DXA

const border = { style: BorderStyle.SINGLE, size: 4, color: "8C8C8C" };
const borders = { top: border, bottom: border, left: border, right: border };

const run = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 21, bold: o.bold, color: o.color });
const para = (text, o = {}) => new Paragraph({
  children: Array.isArray(text) ? text : [run(text, o)],
  alignment: o.align, spacing: { before: o.before || 0, after: o.after ?? 80, line: 300 },
  numbering: o.bullet ? { reference: "bullets", level: 0 } : undefined,
});
const heading = (text) => new Paragraph({
  children: [run(text, { size: 25, bold: true, color: NAVY })],
  spacing: { before: 280, after: 120 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 2 } },
});

function cell(text, width, o = {}) {
  const lines = String(text ?? "").split("\n");
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    columnSpan: o.span,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: lines.map((l) => para(l, { bold: o.bold, align: o.align, size: o.size || 19, after: 0 })),
  });
}
const table = (widths, rows) => new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: widths,
  rows: rows.map((cells) => new TableRow({ children: cells, cantSplit: true })),
});
// 라벨 | 값 형태의 2열 표
const kvTable = (pairs, lw = 1900) => table([lw, W - lw],
  pairs.map(([k, v]) => [cell(k, lw, { fill: LABEL_FILL, bold: true, align: AlignmentType.CENTER }), cell(v, W - lw)]));

const patentNo = (p) => [p.app && `출원 ${p.app}`, p.reg && `등록 ${p.reg}`].filter(Boolean).join("\n");

function build(c) {
  const m = matches[c.code];
  const ps = m.patents;
  const who = c.name || `기업코드 ${c.code}`;
  const strong = ps.some((p) => p.fit === "상");
  const body = [];

  body.push(new Paragraph({
    children: [run("국유특허 기술이전 제안서", { size: 36, bold: true, color: NAVY })],
    alignment: AlignmentType.CENTER, spacing: { after: 80 },
  }));
  body.push(para(`강원센터 제2차 집담회 참석기업 맞춤 제안`, { align: AlignmentType.CENTER, color: "595959", after: 240 }));
  body.push(kvTable([
    ["수     신", c.name ? `${c.name} 대표님 귀하` : `${who} 귀하`],
    ["사업 분야", [c.cat, c.field, c.sub].filter(Boolean).join(" > ")],
    ["사업 아이템", c.item],
    ["센터 담당", c.manager],
    ["제안 기관", `${ORG} (☎ ${TEL})`],
    ["제 안 일", DATE],
  ]));

  body.push(heading("1. 제안 배경 및 목적"));
  body.push(para(`귀사의 사업 아이템 「${c.item}」을 검토하여, 농촌진흥청이 보유한 국유특허 가운데 기술이전이 가능한 기술을 매칭하였습니다.`));
  body.push(para(m.pitch, { bold: true }));
  body.push(para(strong
    ? "국유특허는 통상실시권 계약으로 이전받을 수 있어, 자체 연구개발 대비 개발 기간과 비용을 줄이고 제품의 기술 신뢰도를 높일 수 있습니다."
    : "다만 귀사 아이템과 직접 일치하는 국유특허가 확인되지 않아, 아래 기술은 인접 기술로서 제품 차별화·공동연구 출발점으로 검토해 주시기 바랍니다."));

  body.push(heading("2. 추천 국유특허"));
  const tw = [550, 4288, 2300, 1500, 1000];
  body.push(table(tw, [
    ["No", "기술명", "출원/등록번호", "권리상태", "적합도"].map((h, i) => cell(h, tw[i], { fill: HEAD_FILL, bold: true, align: AlignmentType.CENTER })),
    ...ps.map((p, i) => [
      cell(NUM[i], tw[0], { align: AlignmentType.CENTER }),
      cell(p.title, tw[1]),
      cell(patentNo(p), tw[2], { align: AlignmentType.CENTER, size: 18 }),
      cell(p.status, tw[3], { align: AlignmentType.CENTER, size: 18 }),
      cell(p.fit, tw[4], { align: AlignmentType.CENTER, bold: true }),
    ]),
  ]));
  body.push(para("※ 적합도: 상(핵심 기술로 바로 적용) · 중(제품 확장·보완에 활용) · 하(인접 기술, 참고·공동연구용)", { size: 17, color: "595959", before: 60 }));

  body.push(heading("3. 기술별 활용 방안"));
  const uw = [2600, 4038, 3000];
  body.push(table(uw, [
    ["기술", "귀사 적용 방안", "기대 효과"].map((h, i) => cell(h, uw[i], { fill: HEAD_FILL, bold: true, align: AlignmentType.CENTER })),
    ...ps.map((p, i) => [cell(`${NUM[i]} ${p.title}`, uw[0], { size: 18 }), cell(p.use, uw[1]), cell(p.effect, uw[2])]),
  ]));

  body.push(heading("4. 기술이전 추진 방안"));
  [
    "이전 방식 : 국유특허 통상실시권 허여(실시 기간·범위·실시료는 관련 규정에 따라 협의·산정)",
    "추진 절차 : ① 기술 상담·수요 확인 → ② 기술이전 신청 → ③ 실시계약 체결 → ④ 연구자 기술지도 및 사업화 연계",
    "연계 지원 : 기술이전 기업 대상 사업화 지원사업 및 후속 기술지도 연계 안내",
  ].forEach((t) => body.push(para(t, { bullet: true })));

  body.push(heading("5. 유의사항"));
  [
    "권리상태는 공개 특허정보 기준이며, 계약 전 KIPRIS로 등록 유지·존속기간을 최종 확인합니다.",
    "공동소유 특허는 공동권리자와의 실시 협의가 필요하며, 출원(심사 중) 특허는 등록 시 권리 범위가 달라질 수 있습니다.",
    "특허의 청구 용도와 귀사 제품 용도(예: 식품→사료)가 다른 경우 실시 범위를 별도로 협의합니다.",
  ].forEach((t) => body.push(para(t, { bullet: true })));

  body.push(para(`붙임  기술요약서 ${ps.length}부.  끝.`, { bold: true, before: 240 }));

  ps.forEach((p, i) => {
    body.push(new Paragraph({ children: [new PageBreak()] }));
    body.push(para(`[붙임 ${i + 1}]`, { bold: true, color: NAVY, after: 40 }));
    body.push(new Paragraph({
      children: [run("기 술 요 약 서", { size: 30, bold: true })],
      alignment: AlignmentType.CENTER, spacing: { after: 200 },
    }));
    body.push(kvTable([
      ["기 술 명", p.title],
      ["출원번호", p.app || "-"],
      ["등록번호", p.reg || "-"],
      ["권 리 자", p.owner],
      ["권리상태", p.status],
      ["기술 개요", p.summary],
      ["기대 효과", p.effect],
      ["활용 분야\n(귀사 적용)", p.use],
      ["매칭 적합도", `${p.fit}  (사업 아이템: ${c.item})`],
      ["정보 출처", p.src],
    ]));
  });

  return new Document({
    styles: { default: { document: { run: { font: FONT, size: 21 } } } },
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 260 } } } }] }] },
    sections: [{
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ font: FONT, size: 16, color: "808080", children: [`${ORG} · 국유특허 기술이전 제안서 · `, PageNumber.CURRENT] }),
      ] })] }) },
      children: body,
    }],
  });
}

fs.mkdirSync(OUT, { recursive: true });
(async () => {
  for (const [i, c] of companies.entries()) {
    const name = `${String(i + 1).padStart(2, "0")}_${c.code}_국유특허_기술이전_제안서.docx`;
    fs.writeFileSync(path.join(OUT, name), await Packer.toBuffer(build(c)));
    console.log(name);
  }
})();
