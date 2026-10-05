# Bedrock ユーザー別コストダッシュボード (CUR 2.0 + Athena + Amazon Quick)

CUR 2.0 の IAM プリンシパル列 (`line_item_iam_principal`) を使い、Amazon Bedrock の利用料金をユーザー・モデル・トークン種別ごとに可視化する。

## 構成

```
athena/
  01-create-database.sql     cur データベース
  02-create-table.sql        cur.cur2 テーブル (パーティション射影)
  queries/                   Athena で直接叩く集計クエリ
quick/
  dataset.sql                Quick データセットのカスタム SQL
  build_definition.py        ダッシュボード定義 (JSON) を生成するスクリプト
cloudformation/
  quick-dashboard.json       データソース・データセット・ダッシュボードの CloudFormation テンプレート
scripts/
  make-cfn-template.py       Quick のエクスポート結果を配布用テンプレートに整える
```

## 前提

- CUR 2.0 の export を作成済み (Include resource IDs と Include caller identity (IAM principal) allocation data を ON)
- Athena で `athena/` の SQL を実行し、`cur.cur2` テーブルを作成済み
- Amazon Quick (Enterprise) を作成済みで、次を設定済み
  - SPICE 容量 (1 GB 程度)
  - AWS リソースの権限で Athena と、CUR のバケット・Athena 結果バケットへのアクセスを許可 (結果バケットは Athena Workgroup の書き込み許可も ON)

## デプロイ

```sh
aws cloudformation deploy \
  --region ap-northeast-1 \
  --stack-name bedrock-cur2-dashboard \
  --template-file cloudformation/quick-dashboard.json \
  --parameter-overrides \
    QuickUserArn=arn:aws:quicksight:ap-northeast-1:111122223333:user/default/<Quick ユーザー名> \
    IdentityRegion=ap-northeast-1 \
    DataSourceWorkGroup=primary
```

| パラメータ | 説明 | 既定値 |
|---|---|---|
| `QuickUserArn` | ダッシュボード等の所有者にする Quick ユーザーの ARN | なし (必須) |
| `IdentityRegion` | Quick の ID リージョン | `ap-northeast-1` |
| `DataSourceWorkGroup` | クエリ結果の保存先を設定済みの Athena ワークグループ | `primary` |
| `ResourceIdPrefixForAllResources` | リソース ID の接頭辞 (同じアカウントに複数作る場合) | 空 |
| `DashboardName` / `DataSetName` / `DataSourceName` | 表示名 | |

スタック作成後、データセットの初回取り込みが走る。以降は毎日 17:06 (Asia/Tokyo) にフル更新する。

## 注意

- 金額は定価ベース (unblended) の概算。Partner 経由の請求書の金額とは一致しない
- 日付は UTC 基準
