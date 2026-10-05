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

## セットアップ手順

### 1. CUR 2.0 の export を作る (Billing and Cost Management コンソール)

1. Data Exports → Create export → Standard data export → **CUR 2.0** を選ぶ
2. Additional export content で次の 2 つを **ON** にする
   - Include resource IDs
   - Include caller identity (IAM principal) allocation data
3. Report data integration で **Amazon Athena** を選ぶ (Parquet で配信される)

作成した時点以降の利用分しか入らない。初回の配信までは最大 24 時間かかる。

### 2. Athena のテーブルを作る

- **データベース名 `cur`、テーブル名 `cur2` は変えない。** データセットの SQL (`quick/dataset.sql`) が `cur.cur2` を前提にしている
- テーブルは **Quick を使うリージョン (= スタックをデプロイするリージョン) の Athena** で作る。CUR のバケットが us-east-1 にあっても、Athena は別リージョンでよい
- クエリエディタの Data source は **`AwsDataCatalog`** を選ぶ (S3 Tables のカタログでは外部テーブルを作れない)
- 使うワークグループに、クエリ結果の保存先 S3 を設定しておく

1. `athena/01-create-database.sql` を実行する
2. `athena/02-create-table.sql` の `<bucket>` / `<prefix>` / `<export-name>` を自分の export の値に置き換えて実行する
3. 動作確認として `athena/queries/user-cost-this-month.sql` を実行する

### 3. Amazon Quick を準備する

1. Amazon Quick (Enterprise) のアカウントを用意する
2. デプロイするリージョンで **SPICE 容量を購入**する (1 GB 程度)。容量が 0 だとデータセットの作成に失敗する
3. アカウントを管理 → AWS リソース で次を許可する
   - Amazon Athena
   - Amazon S3: CUR のバケット、Athena の結果バケット (結果バケットは **Athena Workgroup の書き込み許可も ON**)
4. 所有者にする Quick ユーザーの ARN を調べる。`--region` には Quick の ID リージョンを指定する

   ```sh
   aws quicksight list-users --aws-account-id <アカウント ID> --namespace default \
     --region <ID リージョン> --query 'UserList[].[UserName,Arn]' --output text
   ```

### 4. CloudFormation でデプロイする

```sh
aws cloudformation deploy \
  --region <Quick と Athena のリージョン> \
  --stack-name bedrock-cur2-dashboard \
  --template-file cloudformation/quick-dashboard.json \
  --parameter-overrides \
    QuickUserArn=<手順 3 で調べた ARN> \
    IdentityRegion=<Quick の ID リージョン> \
    DataSourceWorkGroup=<手順 2 のワークグループ>
```

| パラメータ | 必須 | 説明 | 既定値 |
|---|---|---|---|
| `QuickUserArn` | ○ | データソース・データセット・ダッシュボードの所有者にする Quick ユーザーの ARN | なし |
| `IdentityRegion` | | Quick の ID リージョン | `ap-northeast-1` |
| `DataSourceWorkGroup` | | クエリ結果の保存先を設定済みの Athena ワークグループ | `primary` |
| `ResourceIdPrefixForAllResources` | | 同じアカウントに複数作るときのリソース ID の接頭辞 | 空 |

表示名 (ダッシュボード「Bedrock ユーザー別コスト」など) はパラメータにせず、テンプレートに直接書いている。CloudFormation のコンソールはパラメータの既定値を取得するときに日本語を `?` に置き換えてしまうため。名前を変えたい場合は、作成後に Quick の画面で変更する。

スタックを作成すると、データセットの初回取り込みが自動で走る (1〜2 分)。以降は毎日 17:06 (Asia/Tokyo) にフル更新する。取り込みの結果は次で確認できる。

```sh
aws quicksight list-ingestions --aws-account-id <アカウント ID> --region <リージョン> \
  --data-set-id bedrock-user-cost-dataset \
  --query 'Ingestions[0].[IngestionStatus,RowInfo.RowsIngested,ErrorInfo.Message]' --output text
```

## ダッシュボードの中身

- **全体サマリー**: 選択月の金額、最新月の金額 (前月比)、利用ユーザー数、合計トークン数、ユーザー別の金額 (モデル種別)、モデル別の金額 (トークン種別)、月次推移、日次推移、ユーザー × 月の表
- **個人別**: ユーザーを 1 人選んで、金額・トークン数・使ったモデル数、モデル × トークン種別の表、日次推移 (モデル別)、モデル種別の構成比、月次推移

## 注意

- 金額は定価ベース (unblended) の概算。Partner 経由の請求書の金額とは一致しない
- 日付は UTC 基準
- 個人別シートでは誰でも他のユーザーを選べる。本人の分だけ見せたい場合は行レベルセキュリティ (RLS) が別途必要
