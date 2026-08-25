# weather-ics

気象庁の天気予報データを、カレンダーに購読登録できるICSファイルに変換して配信する個人プロジェクト。

- 現在の対象: **高知県中部（高知市）** → `public/kochi.ics`
- 今日から7日先まで、1日1件の終日イベント
- 今日・明日は「天気・最高/最低気温・降水確率」の詳細つき（例: `晴れ時々くもり。最高34℃、最低26℃、降水確率20％の予報です。`）
- GitHub Actionsが毎日3回（JST 5:40 / 11:40 / 17:40、気象庁の発表直後）に自動再生成

## 仕組み

```
気象庁 予報JSON ──→ scripts/build_weather.py ──→ public/kochi.ics
                          │
                    scripts/validate_weather.py（機械検査。落ちたら公開されない）
                          │
                    GitHub Actions が毎日3回実行 → GitHub Pages で配信
```

- データ源: `https://www.jma.go.jp/bosai/forecast/data/forecast/390000.json`
- 今日の最低気温は朝の発表以降は気象庁から配信されないため、その場合は自動的に「最高◯℃、降水確率◯％」の表記になります
- イベントのUID（`{日付}-weather-kochi@weather-ics`）は安定運用。**変更禁止**（購読側で別イベントになるため）

## 公開手順（初回のみ・手動）

1. GitHubで新しいリポジトリ `weather-ics` を作成（**Public**。Actionsを無制限無料で使うため）
2. このフォルダをpush:
   ```
   git remote add origin https://github.com/<ユーザー名>/weather-ics.git
   git push -u origin main
   ```
3. リポジトリの Settings → Pages → Source を「Deploy from a branch」、Branch を `main` / `/ (root)` にして保存
4. Settings → Actions → General → Workflow permissions を「Read and write permissions」にする（Actionsがcommit/pushするため）
5. 数分後、次のURLでICSが配信される:
   ```
   https://<ユーザー名>.github.io/weather-ics/public/kochi.ics
   ```

## カレンダーへの登録

- **Googleカレンダー**: 設定 → カレンダーを追加 → URLで追加 → 上記URLを貼る
  - 注意: Googleは購読カレンダーを8〜24時間間隔でしか再取得しないため、朝の最新発表の反映が遅れることがあります（仕様）
- **iPhone**: 設定 → カレンダー → アカウント追加 → その他 → 照会カレンダーを追加 → 上記URLを貼る

## 全国版への拡張

`scripts/build_weather.py` 冒頭の地域設定ブロック（PREF_CODE / CLASS10_CODE / TEMP_STATION_CODE / CAL_NAME / UID_AREA / OUTPUT）を地域リスト化してループさせる設計。費用は全国版でもゼロ（気象庁データは無料、公開リポジトリのActionsは無料、Pagesの転送量も余裕）。

## 出典・利用規約

- 本カレンダーのデータは**気象庁**の発表する天気予報をもとにしています
- 気象庁コンテンツの利用は「公共データ利用規約（第1.0版）」（CC BY 4.0互換）に準拠
- 本プロジェクトは気象庁の発表内容を形式変換して転載するものであり、独自の予報は行いません
