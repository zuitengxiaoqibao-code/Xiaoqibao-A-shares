import type { LatestTipItem } from "./types";


export type LatestTipPresentation = {
  fact: string;
  impact: string;
  watch: string;
  rawEvidence: string;
};

function cleanEvidence(value: string): string {
  return value
    .replace(/☆?\d{6}[^|\n]{0,24}更新日期[^|\n]*通达信(?:沪深京)?F10/gi, " ")
    .replace(/通达信(?:沪深京)?F10/gi, " ")
    .replace(/[★☆]?本栏包括(?:【\d+\.[^】]+】)+/g, " ")
    .replace(/【\d+\.[^】]+】/g, " ")
    .replace(/[|｜┌┬┐├┼┤└┴┘─━═]{2,}/g, " ")
    .replace(/\s*[|｜]\s*/g, "；")
    .replace(/(?:；\s*){2,}/g, "；")
    .replace(/\s+/g, " ")
    .replace(/^[；\s]+|[；\s]+$/g, "");
}

function financialPresentation(item: LatestTipItem): Pick<LatestTipPresentation, "impact" | "watch"> {
  if (item.tone === "positive") return {
    impact: "收入与利润同比改善，说明本期经营表现向好；是否形成持续趋势仍需后续报告验证。",
    watch: "核对下一报告期增速、经营现金流与利润增速是否匹配。",
  };
  if (item.tone === "risk") return {
    impact: "收入或利润出现下滑，经营表现承压；当前事实不能单独解释下滑原因。",
    watch: "等待正式财报，核对毛利率、费用、现金流和下滑原因。",
  };
  return {
    impact: "收入与利润方向不一致，经营质量暂时无法用单一结论概括。",
    watch: "核对正式财报中的毛利率、费用率、经营现金流和一次性损益。",
  };
}

export function presentLatestTip(item: LatestTipItem): LatestTipPresentation {
  const fact = cleanEvidence(item.summary) || "来源仅提供事件标题，细节待原文核验。";
  const rawEvidence = cleanEvidence(item.raw_text) || fact;
  const text = `${item.title} ${fact}`;
  let impact = "当前只有事件事实，缺少规模或执行结果，影响待确认。";
  let watch = "继续核验后续公告、执行进度和可量化影响。";

  if (item.category === "业绩预告") {
    ({ impact, watch } = financialPresentation(item));
  } else if (/解禁|限售股上市流通/.test(text)) {
    impact = "新增可流通股份可能带来潜在供给压力，但不等同于股东一定减持。";
    watch = "观察解禁规模占比、相关股东的实际减持公告和成交量变化。";
  } else if (/减持/.test(text)) {
    impact = "减持计划可能增加阶段性供给和情绪压力，实际影响取决于比例与执行节奏。";
    watch = "核对计划减持比例、时间窗口、已实施数量和减持进度公告。";
  } else if (/回购/.test(text)) {
    impact = "回购表达公司资金安排，但效果取决于回购金额、价格上限和实际完成度。";
    watch = "观察已回购金额、股份数量、执行进度及资金来源。";
  } else if (/质押|融资|定增|增发|配股/.test(text)) {
    impact = "资本事项可能改变资金结构或股份供给，当前不能仅凭标题判断利好或利空。";
    watch = "核对融资规模、用途、摊薄比例、质押比例和实施进度。";
  } else if (item.category === "公告与合同") {
    impact = item.tone === "positive"
      ? "事件可能形成业务催化，但合同签署或中标不等同于收入已经确认。"
      : "公告事实已确认，经营影响取决于金额、执行条件和收入确认节奏。";
    watch = "核对事件金额占营收比例、履约条件、执行周期和后续收入确认。";
  } else if (item.category === "交易异动") {
    impact = "价格或交易行为出现异常，只能说明波动上升，不能证明基本面发生变化。";
    watch = "观察公司澄清公告、成交量、换手率和异常波动是否延续。";
  } else if (item.tone === "risk") {
    impact = "已识别风险事项，影响程度仍取决于涉及金额、比例和处理进展。";
    watch = "核对正式公告、影响范围、处置进展和是否触发进一步风险。";
  }

  return { fact, impact, watch, rawEvidence };
}
