"""Quick のアセットバンドル (CloudFormation JSON) を配布用に整える。

使い方:
  python3 scripts/make-cfn-template.py <export.json> cloudformation/quick-dashboard.json

- 自動生成の論理 ID / リソース ID / パラメータ名を読みやすい名前に置き換える
- 権限の Principal をエクスポート元のユーザーから QuickUserArn パラメータに置き換える
- 作成順序 (DataSource -> DataSet -> Dashboard / RefreshSchedule) を DependsOn で明示する
"""
import json
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()

# 論理 ID (パラメータ名の接頭辞にも使われている) と、リソース ID の置き換え
renames = {
    "bedrockusercost06B642": "Dashboard",
    "d80fe8dadf72474296ce93EE19": "DataSource",
    "f3e601e758f947f2899198E5EF": "DataSet",
    "f3e601e758f947f289912C752E": "RefreshSchedule",
    "d80fe8da-df72-4742-96ce-bf2dadab0d27": "bedrock-cur2-athena",
    "f3e601e7-58f9-47f2-8991-481e8fd1f59b": "bedrock-user-cost-dataset",
    "2c44cd01-7103-4526-a0cd-2e002b04abfc": "daily-refresh",
}
for old, new in renames.items():
    text = text.replace(old, new)

t = json.loads(text)
t["Description"] = ("Amazon Quick dashboard: Bedrock cost per IAM principal from CUR 2.0 "
                    "(requires Athena table cur.cur2)")

params = t["Parameters"]
params["DataSourceWorkGroup"]["Description"] = "Athena workgroup that has a query result location"
params["QuickUserArn"] = {
    "Type": "String",
    "Description": "ARN of the Quick user who owns the assets "
                   "(e.g. arn:aws:quicksight:ap-northeast-1:111122223333:user/default/your-user)",
}
params["IdentityRegion"]["Description"] = "Quick identity region of this account"

res = t["Resources"]
for r in res.values():
    for perm in r["Properties"].get("Permissions", []):
        perm["Principal"] = {"Ref": "QuickUserArn"}
res["DataSet"]["DependsOn"] = ["DataSource"]
res["Dashboard"]["DependsOn"] = ["DataSet"]

# CLI の --template-body は 51,200 バイトまでなので、インデント 1 で収める
out = json.dumps(t, ensure_ascii=False, indent=1)
assert len(out.encode()) < 51200, f"template too large for --template-body: {len(out.encode())} bytes"
# 説明文の例に使っているダミーのアカウント ID (111122223333) は除外する
leftover = [v for v in re.findall(r"AWSReservedSSO_[^\"/]*|ssouser\d+|\b\d{12}\b", out) if v != "111122223333"]
assert not leftover, f"account specific values remain: {set(leftover)}"
open(dst, "w", encoding="utf-8").write(out + "\n")
print(f"wrote {dst}")
