import json
import os

DS_ARN = os.environ["DATASET_ARN"]  # 例: arn:aws:quicksight:ap-northeast-1:111122223333:dataset/<id>
DS = "cost"
S1 = "sheet-summary"
S2 = "sheet-user"
OUT = os.path.join(os.path.dirname(__file__), "definition.json")

USD = {"CurrencyDisplayFormatConfiguration": {"Symbol": "USD", "DecimalPlacesConfiguration": {"DecimalPlaces": 2}}}


def col(name):
    return {"DataSetIdentifier": DS, "ColumnName": name}


def dim(fid, name):
    return {"CategoricalDimensionField": {"FieldId": fid, "Column": col(name)}}


def date_dim(fid, name, gran):
    return {"DateDimensionField": {"FieldId": fid, "Column": col(name), "DateGranularity": gran}}


def cost(fid):
    return {"NumericalMeasureField": {"FieldId": fid, "Column": col("cost_usd"),
                                      "AggregationFunction": {"SimpleNumericalAggregation": "SUM"},
                                      "FormatConfiguration": {"FormatConfiguration": USD}}}


def tokens(fid):
    return {"NumericalMeasureField": {"FieldId": fid, "Column": col("tokens"),
                                      "AggregationFunction": {"SimpleNumericalAggregation": "SUM"}}}


def distinct(fid, name):
    return {"CategoricalMeasureField": {"FieldId": fid, "Column": col(name), "AggregationFunction": "DISTINCT_COUNT"}}


def title(t):
    return {"Visibility": "VISIBLE", "FormatText": {"PlainText": t}}


def kpi(vid, t, value, trend=None):
    conf = {"FieldWells": {"Values": [value]}}
    if trend:
        conf["FieldWells"]["TrendGroups"] = [trend]
        conf["KPIOptions"] = {"Comparison": {"ComparisonMethod": "PERCENT_DIFFERENCE"},
                              "PrimaryValueDisplayType": "ACTUAL"}
    return {"KPIVisual": {"VisualId": vid, "Title": title(t), "ChartConfiguration": conf}}


def bar(vid, t, category, value, colors=None, horizontal=True, sort="value"):
    wells = {"Category": [category], "Values": [value]}
    if colors:
        wells["Colors"] = [colors]
    conf = {"Orientation": "HORIZONTAL" if horizontal else "VERTICAL",
            "FieldWells": {"BarChartAggregatedFieldWells": wells}}
    if colors:
        conf["BarsArrangement"] = "STACKED"
    # sort="value": 金額の大きい順 / sort="category": 軸の値 (日付) の昇順
    if sort == "value":
        vfid = next(iter(value.values()))["FieldId"]
        conf["SortConfiguration"] = {"CategorySort": [{"FieldSort": {"FieldId": vfid, "Direction": "DESC"}}]}
    elif sort == "category":
        cfid = next(iter(category.values()))["FieldId"]
        conf["SortConfiguration"] = {"CategorySort": [{"FieldSort": {"FieldId": cfid, "Direction": "ASC"}}]}
    return {"BarChartVisual": {"VisualId": vid, "Title": title(t), "ChartConfiguration": conf}}


def line(vid, t, category, value, colors=None):
    wells = {"Category": [category], "Values": [value]}
    if colors:
        wells["Colors"] = [colors]
    return {"LineChartVisual": {"VisualId": vid, "Title": title(t),
                                "ChartConfiguration": {"Type": "LINE", "FieldWells": {"LineChartAggregatedFieldWells": wells}}}}


def pivot(vid, t, rows, columns, values):
    return {"PivotTableVisual": {"VisualId": vid, "Title": title(t), "ChartConfiguration": {
        "FieldWells": {"PivotTableAggregatedFieldWells": {"Rows": rows, "Columns": columns, "Values": values}}}}}


def donut(vid, t, category, value):
    return {"PieChartVisual": {"VisualId": vid, "Title": title(t), "ChartConfiguration": {
        "FieldWells": {"PieChartAggregatedFieldWells": {"Category": [category], "Values": [value]}},
        "DonutOptions": {"ArcOptions": {"ArcThickness": "MEDIUM"}}}}}


def el(eid, etype, cs, rs):
    return {"ElementId": eid, "ElementType": etype, "ColumnSpan": cs, "RowSpan": rs}


def category_filter(fgid, fid, column, scopes):
    return {"FilterGroupId": fgid, "CrossDataset": "SINGLE_DATASET", "Status": "ENABLED",
            "Filters": [{"CategoryFilter": {"FilterId": fid, "Column": col(column), "Configuration": {
                "FilterListConfiguration": {"MatchOperator": "CONTAINS", "SelectAllOptions": "FILTER_ALL_VALUES"}}}}],
            "ScopeConfiguration": {"SelectedSheets": {"SheetVisualScopingConfigurations": scopes}}}


def scope(sheet, visual_ids=None):
    if visual_ids is None:
        return {"SheetId": sheet, "Scope": "ALL_VISUALS"}
    return {"SheetId": sheet, "Scope": "SELECTED_VISUALS", "VisualIds": visual_ids}


# formatDate は 'yyyy-MM' に対応していないので、年と月の数字から 'YYYY-MM' を組み立てる
MONTH_LABEL = ("concat(toString(extract('YYYY', {billing_month})), '-', "
               "ifelse(extract('MM', {billing_month}) < 10, "
               "concat('0', toString(extract('MM', {billing_month}))), "
               "toString(extract('MM', {billing_month}))))")

MODEL_FAMILY = ("ifelse("
                "locate(toLower({model_id}), 'fable') > 0, 'Fable', "
                "locate(toLower({model_id}), 'opus') > 0, 'Opus', "
                "locate(toLower({model_id}), 'sonnet') > 0, 'Sonnet', "
                "locate(toLower({model_id}), 'haiku') > 0, 'Haiku', "
                "locate(toLower({model_id}), 'kimi') > 0, 'Kimi', "
                "'Other')")

NOTE = ("<text-box>金額は定価ベース (unblended) の概算です。Partner 経由の請求書の金額とは一致しません。"
        "日付は UTC 基準です。CUR は 1 日 1 回程度の配信のため、当日分は翌日以降に反映されます。</text-box>")

# --- シート 1: 全体サマリー ---
s1_visuals = [
    kpi("s1-kpi-cost", "選択月の金額", cost("s1kc")),
    kpi("s1-kpi-mom", "最新月の金額 (前月比)", cost("s1km"), date_dim("s1km_m", "billing_month", "MONTH")),
    kpi("s1-kpi-users", "利用ユーザー数", distinct("s1ku", "user_name")),
    kpi("s1-kpi-tokens", "合計トークン数", tokens("s1kt")),
    bar("s1-bar-user", "ユーザー別の金額 (モデル種別)", dim("s1bu_u", "user_name"), cost("s1bu_c"),
        colors=dim("s1bu_f", "model_family")),
    bar("s1-bar-model", "モデル別の金額 (トークン種別)", dim("s1bm_m", "model_id"), cost("s1bm_c"),
        colors=dim("s1bm_k", "token_kind")),
    bar("s1-bar-month", "月次推移 (ユーザー別)", date_dim("s1mo_m", "billing_month", "MONTH"), cost("s1mo_c"),
        colors=dim("s1mo_u", "user_name"), horizontal=False, sort="category"),
    line("s1-line-daily", "日次推移 (全体)", date_dim("s1ld_d", "usage_date", "DAY"), cost("s1ld_c")),
    pivot("s1-pivot", "ユーザー × 月", [dim("s1pv_u", "user_name")],
          [date_dim("s1pv_m", "billing_month", "MONTH")], [cost("s1pv_c")]),
]
# 月フィルターを効かせないビジュアル (全期間を見せたいもの)
s1_all_months = {"s1-kpi-mom", "s1-bar-month", "s1-pivot"}
s1_month_scoped = [v[next(iter(v))]["VisualId"] for v in s1_visuals
                   if v[next(iter(v))]["VisualId"] not in s1_all_months]
s1_layout = [
    el("s1-kpi-cost", "VISUAL", 9, 5), el("s1-kpi-mom", "VISUAL", 9, 5),
    el("s1-kpi-users", "VISUAL", 9, 5), el("s1-kpi-tokens", "VISUAL", 9, 5),
    el("s1-bar-user", "VISUAL", 18, 10), el("s1-bar-model", "VISUAL", 18, 10),
    el("s1-bar-month", "VISUAL", 18, 10), el("s1-line-daily", "VISUAL", 18, 10),
    el("s1-pivot", "VISUAL", 36, 10),
    el("s1-note", "TEXT_BOX", 36, 2),
]

# --- シート 2: 個人別 ---
s2_visuals = [
    kpi("s2-kpi-cost", "金額", cost("s2kc")),
    kpi("s2-kpi-tokens", "トークン数", tokens("s2kt")),
    kpi("s2-kpi-models", "使ったモデル数", distinct("s2km", "model_id")),
    pivot("s2-pivot", "モデル × トークン種別", [dim("s2pv_m", "model_id")],
          [dim("s2pv_k", "token_kind")], [cost("s2pv_c"), tokens("s2pv_t")]),
    bar("s2-bar-daily", "日次推移 (モデル別)", date_dim("s2bd_d", "usage_date", "DAY"), cost("s2bd_c"),
        colors=dim("s2bd_m", "model_id"), horizontal=False, sort="category"),
    donut("s2-donut", "モデル種別の構成比 (金額)", dim("s2dn_f", "model_family"), cost("s2dn_c")),
    bar("s2-bar-month", "月次推移", date_dim("s2mo_m", "billing_month", "MONTH"), cost("s2mo_c"),
        horizontal=False, sort="category"),
]
s2_month_scoped = [v[next(iter(v))]["VisualId"] for v in s2_visuals
                   if v[next(iter(v))]["VisualId"] != "s2-bar-month"]
s2_layout = [
    el("s2-kpi-cost", "VISUAL", 12, 5), el("s2-kpi-tokens", "VISUAL", 12, 5), el("s2-kpi-models", "VISUAL", 12, 5),
    el("s2-pivot", "VISUAL", 36, 10),
    el("s2-bar-daily", "VISUAL", 24, 10), el("s2-donut", "VISUAL", 12, 10),
    el("s2-bar-month", "VISUAL", 36, 8),
    el("s2-note", "TEXT_BOX", 36, 2),
]

definition = {
    "DataSetIdentifierDeclarations": [{"Identifier": DS, "DataSetArn": DS_ARN}],
    "CalculatedFields": [{"DataSetIdentifier": DS, "Name": "month_label",
                          "Expression": MONTH_LABEL},
                         {"DataSetIdentifier": DS, "Name": "model_family", "Expression": MODEL_FAMILY}],
    "FilterGroups": [
        category_filter("fg-s1-month", "f-s1-month", "month_label", [scope(S1, s1_month_scoped)]),
        category_filter("fg-s2-month", "f-s2-month", "month_label", [scope(S2, s2_month_scoped)]),
        category_filter("fg-s2-user", "f-s2-user", "user_name", [scope(S2)]),
    ],
    "Sheets": [
        {"SheetId": S1, "Name": "全体サマリー", "Visuals": s1_visuals,
         "FilterControls": [{"Dropdown": {"FilterControlId": "s1-ctl-month", "Title": "請求月",
                                          "SourceFilterId": "f-s1-month", "Type": "SINGLE_SELECT"}}],
         "TextBoxes": [{"SheetTextBoxId": "s1-note", "Content": NOTE}],
         "SheetControlLayouts": [{"Configuration": {"GridLayout": {"Elements": [
             el("s1-ctl-month", "FILTER_CONTROL", 3, 1)]}}}],
         "Layouts": [{"Configuration": {"GridLayout": {"Elements": s1_layout}}}]},
        {"SheetId": S2, "Name": "個人別", "Visuals": s2_visuals,
         "FilterControls": [
             {"Dropdown": {"FilterControlId": "s2-ctl-user", "Title": "ユーザー",
                           "SourceFilterId": "f-s2-user", "Type": "SINGLE_SELECT"}},
             {"Dropdown": {"FilterControlId": "s2-ctl-month", "Title": "請求月",
                           "SourceFilterId": "f-s2-month", "Type": "SINGLE_SELECT"}}],
         "TextBoxes": [{"SheetTextBoxId": "s2-note", "Content": NOTE}],
         "SheetControlLayouts": [{"Configuration": {"GridLayout": {"Elements": [
             el("s2-ctl-user", "FILTER_CONTROL", 3, 1), el("s2-ctl-month", "FILTER_CONTROL", 3, 1)]}}}],
         "Layouts": [{"Configuration": {"GridLayout": {"Elements": s2_layout}}}]},
    ],
}

json.dump(definition, open(OUT, "w"), ensure_ascii=False, indent=1)
print("ok")
