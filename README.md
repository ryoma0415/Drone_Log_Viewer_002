# StampFly Flight Log & Video Synchronizer

StampFlyのホバリング実験で取得したOptiTrackログとスマートフォンで撮影した飛行映像を同期し、計測値と映像を並列表示したダッシュボード動画を生成するツール群です。元データは別リポジトリ「MoCap_Hovering_Control_for_StampFly」の`flight_logs/`出力と、同タイムスタンプで撮影したMP4動画を使用します。

---

## プロジェクトの狙い
- ドローンの挙動を「映像」「位置」「制御量」「マーカー検出状況」で同時に可視化し、ホバリング制御の安定性を素早く評価できるようにする。
- OptiTrackロガーの100 Hz CSVと30 fpsの映像を滑らかに同期させ、トリミングやオフセット調整を最小限に抑える。
- 実験後のレビューを円滑にし、チューニングや不具合調査の時間を短縮する。

---

## 主な機能
- CSVと動画の読み込み・フレーム補間・同期処理（100 Hz → 30 fps）
- Matplotlibベースの複数パネルプロットとOpenCV動画合成
- 6パネル版（`flight_video_synchronizer.py`）と7パネル版（`flight_video_synchronizer_v2.py`）の2種類を収録
- 生成動画はFHD（1920x1080）、H.264 (`yuv420p`) でエクスポート
- CSVのサマリー（`NEW_LOG_STRUCTURE.md`）を付属し、ログの列意味をドキュメント化

---

## ディレクトリ構成
```
Flight_Viewer/
├─ CSV_to_Graph/
│  ├─ flight_video_synchronizer.py        # 6パネル版スクリプト
│  ├─ flight_video_synchronizer_v2.py     # 7パネル版（StampFlyフィードバック追加）
│  ├─ requirements.txt                    # Python依存パッケージ
│  ├─ flight_logs/                        # MoCapロガーが吐き出すCSV
│  ├─ smartphone_videos/                  # 同期させるスマホ動画
│  ├─ animation_results/                  # 生成された動画の保存先
│  └─ README_video_sync.md                # スクリプト個別の簡易説明
└─ NEW_LOG_STRUCTURE.md                   # CSV列仕様の詳細解説
```
> `.gitignore` で `animation_results/` と `smartphone_videos/` 配下を無視しているため、ローカルの大容量ファイルを誤ってコミットする心配がありません。

---

## 動作環境
- Python 3.9 以上（3.11で動作確認済み）
- FFmpeg（`ffmpeg` コマンドが PATH 上にあること）
- macOS / Windows / Linux いずれも可  
  - macOSではMatplotlibフォントとしてHiragino Sansを自動指定
  - WindowsはMS Gothic、LinuxはDejaVu Sansを利用

### Python依存ライブラリ
`Flight_Viewer/CSV_to_Graph/requirements.txt` に記載：
```
pandas>=1.3.0
numpy>=1.21.0
matplotlib>=3.4.0
opencv-python>=4.5.0
ffmpeg-python>=0.2.0
```

---

## セットアップ手順
1. 仮想環境を作成・有効化（例: `python -m venv .venv` → `source .venv/bin/activate`）
2. 依存パッケージをインストール  
   ```bash
   pip install -r Flight_Viewer/CSV_to_Graph/requirements.txt
   ```
3. FFmpegをインストール  
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt-get install ffmpeg`
   - Windows: 公式サイトからバイナリを取得し、`ffmpeg.exe` のパスを環境変数に追加
4. Matplotlibが使用する日本語フォントが環境に存在するか確認（必要であれば既定フォントを置換）

---

## データの準備
1. **CSVログ**  
   - MoCap制御リポジトリでホバリング実験を実行すると `log_YYYYMMDD_HHMMSS.csv` が作成される。  
   - 生成されたCSVを `Flight_Viewer/CSV_to_Graph/flight_logs/` にコピーする。
2. **スマホ動画 (MP4)**  
   - 30 fps / 1920x1080 推奨。  
   - CSVと同じタイムスタンプ形式（`flight_YYYYMMDD_HHMMSS.mp4`）で保存すると識別しやすい。  
   - ファイルは `Flight_Viewer/CSV_to_Graph/smartphone_videos/` に配置。
3. **サンプルデータ**  
   - リポジトリには複数の CSV と MP4、生成済み動画が含まれているので、環境確認に利用できる。

---

## クイックスタート
```bash
cd Flight_Viewer/CSV_to_Graph
python flight_video_synchronizer_v2.py
```
1. CLI が `flight_logs/*.csv` を列挙するので対象ファイルを番号で選択。
2. 続いて `smartphone_videos/*.mp4` から対応する映像を選択。
3. `y` を入力すると動画生成が始まり、進捗が30フレームごとに表示される。
4. 出力先は `animation_results/synchronized_flight_YYYYMMDD_HHMMSS.mp4`。

> 6パネル構成で十分な場合は `flight_video_synchronizer.py` を実行してください。

---

## 生成動画のパネル構成
### 7パネル版 (`flight_video_synchronizer_v2.py`)
1. **スマホ映像**（左上 2×2 パネル相当）  
   - OpenCVで読み込んだフレームをRGBに変換し、そのまま表示。
2. **2D位置軌跡**  
   - `raw_pos_x/raw_pos_y` もしくは `pos_x/pos_y` を使用。最新100フレームをグラデーション軌跡で描画。
   - 目標位置は `DEFAULT_TARGET_POSITION`（初期値 `(0.325, -0.325)`）として黄色の×で表示。
3. **指令角度 (Roll/Pitch)**  
   - `roll_ref_deg`, `pitch_ref_deg` の履歴を5秒窓で表示。0°ラインを破線表示。
4. **StampFly目標姿勢 (Feedback)**  
   - `feedback_roll_rad/pitch` を度に変換し、フィードバック応答を確認できる。
5. **X軸 PID 成分 (Roll)**  
   - `pid_x_p/i/d` の各成分を表示。縦軸は ±0.05 で固定。
6. **Y軸 PID 成分 (Pitch)**  
   - `pid_y_p/i/d` の各成分を表示。縦軸は ±0.05 で固定。
7. **検出マーカー数**  
   - `marker_count` の履歴を塗りつぶしで表示し、最新値をラベル表示。縦軸上限はデータにあわせて自動調整。

### 6パネル版 (`flight_video_synchronizer.py`)
フィードバック（StampFly目標姿勢）パネルを除いた構成。その他の仕様は同様。

---

## CSVログの主な列
詳細は `Flight_Viewer/NEW_LOG_STRUCTURE.md` を参照。ここでは可視化で頻用する列だけ抜粋します。

| カテゴリ | 列名 | 説明 |
| --- | --- | --- |
| 時刻 | `timestamp`, `elapsed_time` | ログ時刻、開始からの経過秒 |
| 位置 | `pos_x`, `pos_y`, `raw_pos_x`, `raw_pos_y` | フィルタ済み／未フィルタの平面位置 |
| 誤差 | `error_x`, `error_y` | 目標位置からのずれ（m） |
| 指令 | `roll_ref_deg`, `pitch_ref_deg` | ESP32に送ったロール／ピッチ指令 |
| フィードバック | `feedback_roll_rad`, `feedback_pitch_rad` | StampFlyから返却された角度 |
| PID | `pid_x_p/i/d`, `pid_y_p/i/d` | 各軸のPID内訳 |
| トラッキング | `marker_count`, `tracking_valid`, `rb_marker_count` | Motive側のトラッキング健全性 |
| 制御管理 | `send_success`, `control_active`, `loop_time_ms` | コマンド送信成功、外側ループON/OFF、制御周期 |

---

## カスタマイズのヒント
- **目標位置の変更**  
  `flight_video_synchronizer_v2.py` の `DEFAULT_TARGET_POSITION` を編集するか、`FlightVideoSynchronizer` に任意の `(x, y)` を渡してください。
- **表示窓や色の調整**  
  `trail_length`（軌跡の長さ）、`axes['pid_x'].set_ylim(...)` などを変更してスケーリングをチューニングできます。
- **複数動画のバッチ化**  
  現状はインタラクティブCLIですが、ファイル選択部（`select_files`）を差し替えれば自動処理にも対応できます。

---

## トラブルシューティング
- **FFmpegが見つからない**  
  `writer = FFMpegWriter(...)` 実行時に失敗します。`ffmpeg -version` が実行できるようPATHを設定してください。
- **フォントの警告/文字化け**  
  OS固有フォントが見つからない場合は `matplotlib.rcParams['font.family']` を手動で設定。
- **メモリ不足**  
  長時間動画を処理するとRGBフレームを全読み込みするためメモリを消費します。動画を短尺に分割するか、フレームを都度読み込むようロジックを変更してください。
- **同期のズレが気になる**  
  CSVと動画が同時スタートしていることを前提にしているため、開始タイミングが異なる場合は動画編集ソフトでトリミングするか、将来的にオフセット入力を追加してください。

---

## 今後の発展アイデア
- CLIオプション化（`--csv`, `--video`, `--offset` 等）
- 音声や注釈レイヤの追加
- マーカーの消失と制御応答の相関を自動抽出する分析スクリプト
- Webベースでのインタラクティブ再生ビューア

---

## 参考資料
- MoCap制御実験コード：`MoCap_Hovering_Control_for_StampFly`
- ログ列仕様：`Flight_Viewer/NEW_LOG_STRUCTURE.md`
- スクリプト別README：`Flight_Viewer/CSV_to_Graph/README_video_sync.md`

このREADMEが、StampFlyホバリング実験のレビュー・解析ワークフロー構築に役立てば幸いです。

