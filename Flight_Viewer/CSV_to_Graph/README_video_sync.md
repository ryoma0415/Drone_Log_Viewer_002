# ドローン飛行データ・動画同期ビジュアライゼーション

## 概要
OptiTrackで記録したドローン飛行データ（CSV、100Hz）とスマホで撮影した飛行動画（MP4、30fps）を同期させて、6パネルの統合ビジュアライゼーション動画を生成するツールです。

## 機能
- スマホ動画とCSVデータの自動同期
- 6つのビジュアライゼーションパネル：
  1. スマホ撮影映像
  2. 2D座標プロット（X-Y平面）
  3. 指令角度（Roll/Pitch）
  4. X軸PID成分（P/I/D）
  5. Y軸PID成分（P/I/D）
  6. 検出マーカー数

## セットアップ

### 1. 必要なライブラリのインストール
```bash
pip install -r requirements.txt
```

### 2. FFmpegのインストール
動画処理にFFmpegが必要です：

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
[FFmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロード

**Linux:**
```bash
sudo apt-get install ffmpeg
```

## 使用方法

### 1. データの準備
- **CSVファイル**: `flight_logs/`フォルダに配置（自動的に検出）
- **スマホ動画**: `smartphone_videos/`フォルダにMP4ファイルを配置

### 2. 実行
```bash
python flight_video_synchronizer.py
```

### 3. ファイル選択
1. 利用可能なCSVファイルのリストから選択
2. 利用可能な動画ファイルのリストから選択
3. 確認後、動画生成開始

### 4. 出力
生成された動画は`animation_results/`フォルダに保存されます。
ファイル名: `synchronized_flight_YYYYMMDD_HHMMSS.mp4`

## 注意事項
- CSVデータと動画の開始時刻は同じと仮定
- CSVデータの終了時刻で動画もカット
- 音声は含まれません
- 出力解像度：1920x1080（FHD）

## トラブルシューティング

### 動画が生成されない
- FFmpegが正しくインストールされているか確認
- `smartphone_videos/`フォルダに動画ファイルが存在するか確認

### メモリエラー
- 長時間の動画の場合、メモリ使用量が大きくなります
- 必要に応じて動画を分割して処理

### 同期がずれる
- CSVと動画の開始タイミングを確認
- 将来的に手動オフセット調整機能を追加予定

## 開発者向け情報
- CSVサンプリング：100Hz
- 動画FPS：30fps（一般的なスマホ）
- データ補間：線形補間を使用
- グラフ更新：フレームごとに再描画