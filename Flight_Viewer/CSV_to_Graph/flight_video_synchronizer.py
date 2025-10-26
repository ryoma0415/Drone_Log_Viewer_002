"""
ドローン飛行データとスマホ動画の同期ビジュアライゼーション生成スクリプト
OptiTrackのCSVデータ(100Hz)とスマホ動画(30fps)を同期させて、
6パネルの統合ビジュアライゼーション動画を生成する
"""

import os
import pandas as pd
import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from datetime import datetime
import warnings
import platform
warnings.filterwarnings('ignore')

# OS別フォント設定
system = platform.system()
if system == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'Hiragino Sans'
elif system == 'Windows':
    plt.rcParams['font.family'] = 'MS Gothic'
else:  # Linux
    plt.rcParams['font.family'] = 'DejaVu Sans'

plt.rcParams['axes.unicode_minus'] = False

class FlightVideoSynchronizer:
    def __init__(self, csv_path, video_path, output_path=None):
        """
        初期化

        Args:
            csv_path: CSVファイルパス
            video_path: スマホ動画ファイルパス
            output_path: 出力動画パス（省略時は自動生成）
        """
        self.csv_path = csv_path
        self.video_path = video_path
        self.output_path = output_path

        # データ読み込み
        self.df = None
        self.video_cap = None
        self.video_fps = 30
        self.video_frame_count = 0
        self.video_width = 0
        self.video_height = 0

        # 出力設定
        self.output_fps = 30
        self.output_width = 1920
        self.output_height = 1080

        # プロット設定
        self.trail_length = 100  # 軌跡の長さ
        self.colors = {
            'p': '#FF6B6B',  # P成分: 赤系
            'i': '#4ECDC4',  # I成分: 青緑系
            'd': '#95E77E',  # D成分: 黄緑系
            'trajectory': '#3498db',  # 軌跡: 青系
            'current': '#e74c3c',  # 現在位置: 赤
            'marker': '#2ecc71'  # マーカー: 緑
        }

    def load_data(self):
        """CSVデータと動画を読み込む"""
        print("データを読み込み中...")

        # CSV読み込み
        self.df = pd.read_csv(self.csv_path)
        print(f"CSVデータ: {len(self.df)}行読み込み完了")

        # 動画読み込み
        self.video_cap = cv2.VideoCapture(self.video_path)
        if not self.video_cap.isOpened():
            raise ValueError(f"動画ファイルを開けません: {self.video_path}")

        self.video_fps = self.video_cap.get(cv2.CAP_PROP_FPS)
        self.video_frame_count = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"動画情報: {self.video_width}x{self.video_height}, {self.video_fps}fps, {self.video_frame_count}フレーム")

        # 時間同期の計算
        csv_duration = self.df['elapsed_time'].iloc[-1]
        video_duration = self.video_frame_count / self.video_fps

        # CSVデータの終了時刻に合わせて動画をカット
        self.sync_frame_count = int(csv_duration * self.video_fps)
        self.sync_frame_count = min(self.sync_frame_count, self.video_frame_count)

        print(f"同期情報: CSV={csv_duration:.2f}秒, 動画={video_duration:.2f}秒")
        print(f"出力フレーム数: {self.sync_frame_count}")

    def create_figure(self):
        """6パネルのFigureを作成"""
        # 高DPI設定で高品質な図を作成
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        fig.patch.set_facecolor('#1e1e1e')

        # GridSpecで柔軟なレイアウト
        gs = fig.add_gridspec(3, 3,
                              left=0.05, right=0.98,
                              top=0.95, bottom=0.05,
                              wspace=0.15, hspace=0.25,
                              width_ratios=[1.2, 1, 1],
                              height_ratios=[1, 1, 1])

        # 1. スマホ映像（左上、大きめ）
        ax_video = fig.add_subplot(gs[0:2, 0])
        ax_video.set_title('ドローン飛行映像', fontsize=14, color='white', pad=10)
        ax_video.axis('off')

        # 2. 2D座標プロット（右上）
        ax_2d = fig.add_subplot(gs[0, 1:])
        ax_2d.set_title('2D位置座標 (X-Y平面)', fontsize=12, color='white')
        ax_2d.set_xlabel('X [m]', fontsize=10, color='white')
        ax_2d.set_ylabel('Y [m]', fontsize=10, color='white')
        ax_2d.grid(True, alpha=0.3, color='gray')
        ax_2d.set_facecolor('#2e2e2e')

        # 3. 指令角度（中段左）
        ax_angle = fig.add_subplot(gs[1, 1])
        ax_angle.set_title('指令角度 [deg]', fontsize=12, color='white')
        ax_angle.set_xlabel('時間 [s]', fontsize=10, color='white')
        ax_angle.set_ylabel('角度 [deg]', fontsize=10, color='white')
        ax_angle.grid(True, alpha=0.3, color='gray')
        ax_angle.set_facecolor('#2e2e2e')

        # 4. X軸PID成分（中段右）
        ax_pid_x = fig.add_subplot(gs[1, 2])
        ax_pid_x.set_title('X軸 PID成分', fontsize=12, color='white')
        ax_pid_x.set_xlabel('時間 [s]', fontsize=10, color='white')
        ax_pid_x.set_ylabel('出力値', fontsize=10, color='white')
        ax_pid_x.grid(True, alpha=0.3, color='gray')
        ax_pid_x.set_facecolor('#2e2e2e')

        # 5. Y軸PID成分（下段左）
        ax_pid_y = fig.add_subplot(gs[2, 0])
        ax_pid_y.set_title('Y軸 PID成分', fontsize=12, color='white')
        ax_pid_y.set_xlabel('時間 [s]', fontsize=10, color='white')
        ax_pid_y.set_ylabel('出力値', fontsize=10, color='white')
        ax_pid_y.grid(True, alpha=0.3, color='gray')
        ax_pid_y.set_facecolor('#2e2e2e')

        # 6. マーカー検出数（下段中央）
        ax_markers = fig.add_subplot(gs[2, 1:])
        ax_markers.set_title('検出マーカー数', fontsize=12, color='white')
        ax_markers.set_xlabel('時間 [s]', fontsize=10, color='white')
        ax_markers.set_ylabel('マーカー数', fontsize=10, color='white')
        ax_markers.grid(True, alpha=0.3, color='gray')
        ax_markers.set_facecolor('#2e2e2e')

        # 軸の色を白に設定
        for ax in [ax_2d, ax_angle, ax_pid_x, ax_pid_y, ax_markers]:
            ax.tick_params(colors='white', labelsize=9)
            for spine in ax.spines.values():
                spine.set_edgecolor('gray')

        return fig, {
            'video': ax_video,
            '2d': ax_2d,
            'angle': ax_angle,
            'pid_x': ax_pid_x,
            'pid_y': ax_pid_y,
            'markers': ax_markers
        }

    def interpolate_csv_to_video_fps(self):
        """CSVデータ(100Hz)を動画FPS(30fps)に補間"""
        # CSVのタイムスタンプ
        csv_times = self.df['elapsed_time'].values

        # 動画のタイムスタンプ
        video_times = np.arange(0, self.sync_frame_count) / self.video_fps

        # 補間用のインデックスを作成
        interpolated_data = pd.DataFrame()
        interpolated_data['elapsed_time'] = video_times

        # 各列を補間
        for col in self.df.columns:
            if col == 'elapsed_time':
                continue
            elif col == 'timestamp':
                # timestampは文字列なので補間せず、最近傍のインデックスを使用
                indices = np.searchsorted(csv_times, video_times)
                indices = np.clip(indices, 0, len(self.df) - 1)
                interpolated_data[col] = self.df[col].iloc[indices].values
            elif col in ['frame_number', 'marker_count', 'send_success', 'control_active']:
                # 整数値は最近傍補間
                interpolated_data[col] = np.interp(video_times, csv_times, self.df[col].values)
                interpolated_data[col] = interpolated_data[col].round().astype(int)
            else:
                # 実数値は線形補間（数値でない場合はスキップ）
                try:
                    interpolated_data[col] = np.interp(video_times, csv_times, self.df[col].values)
                except (TypeError, ValueError):
                    # 数値でない列はスキップ
                    print(f"警告: 列 '{col}' は数値でないためスキップします")
                    continue

        return interpolated_data

    def animate(self, frame_idx, axes, interpolated_df, video_frames):
        """アニメーションの各フレームを更新"""
        # 現在のデータ
        current_data = interpolated_df.iloc[frame_idx]
        current_time = current_data['elapsed_time']

        # 履歴データ（軌跡用）
        history_start = max(0, frame_idx - self.trail_length)
        history_data = interpolated_df.iloc[history_start:frame_idx+1]

        # 1. スマホ映像の更新
        if frame_idx < len(video_frames):
            axes['video'].clear()
            axes['video'].imshow(video_frames[frame_idx])
            axes['video'].set_title(f'ドローン飛行映像 (t={current_time:.2f}s)',
                                   fontsize=14, color='white', pad=10)
            axes['video'].axis('off')

        # 2. 2D座標プロット
        axes['2d'].clear()
        axes['2d'].set_title('2D位置座標 (X-Y平面)', fontsize=12, color='white')
        axes['2d'].set_xlabel('X [m]', fontsize=10, color='white')
        axes['2d'].set_ylabel('Y [m]', fontsize=10, color='white')

        # 軌跡をグラデーションで描画
        if len(history_data) > 1:
            for i in range(len(history_data) - 1):
                alpha = (i + 1) / len(history_data) * 0.7
                axes['2d'].plot(history_data['pos_x'].iloc[i:i+2],
                               history_data['pos_y'].iloc[i:i+2],
                               color=self.colors['trajectory'], alpha=alpha, linewidth=2)

        # 現在位置
        axes['2d'].scatter(current_data['pos_x'], current_data['pos_y'],
                          color=self.colors['current'], s=100, zorder=5,
                          edgecolors='white', linewidth=2, label='現在位置')

        # 原点（目標位置）
        axes['2d'].scatter(0, 0, color='yellow', marker='x', s=100,
                          linewidth=3, label='目標位置', zorder=4)

        # データ範囲に基づく動的なスケール設定
        x_margin = 0.8
        y_margin = 0.85
        axes['2d'].set_xlim(-0.2 - x_margin, 0.2 + x_margin)
        axes['2d'].set_ylim(-0.15 - y_margin, 0.15 + y_margin)
        axes['2d'].grid(True, alpha=0.3, color='gray')
        axes['2d'].legend(loc='upper right', fontsize=8, framealpha=0.8)
        axes['2d'].set_facecolor('#2e2e2e')

        # 3. 指令角度
        axes['angle'].clear()
        axes['angle'].set_title('指令角度 [deg]', fontsize=12, color='white')
        axes['angle'].set_xlabel('時間 [s]', fontsize=10, color='white')
        axes['angle'].set_ylabel('角度 [deg]', fontsize=10, color='white')

        axes['angle'].plot(history_data['elapsed_time'], history_data['roll_ref_deg'],
                          color='#FF6B6B', label='Roll', linewidth=2, alpha=0.9)
        axes['angle'].plot(history_data['elapsed_time'], history_data['pitch_ref_deg'],
                          color='#4ECDC4', label='Pitch', linewidth=2, alpha=0.9)

        axes['angle'].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        axes['angle'].set_xlim(current_time - 5, current_time + 0.5)
        axes['angle'].set_ylim(-5, 5)
        axes['angle'].grid(True, alpha=0.3, color='gray')
        axes['angle'].legend(loc='upper right', fontsize=8, framealpha=0.8)
        axes['angle'].set_facecolor('#2e2e2e')

        # 4. X軸PID成分
        axes['pid_x'].clear()
        axes['pid_x'].set_title('X軸 PID成分', fontsize=12, color='white')
        axes['pid_x'].set_xlabel('時間 [s]', fontsize=10, color='white')
        axes['pid_x'].set_ylabel('出力値', fontsize=10, color='white')

        axes['pid_x'].plot(history_data['elapsed_time'], history_data['pid_x_p'],
                          color=self.colors['p'], label='P', linewidth=2, alpha=0.9)
        axes['pid_x'].plot(history_data['elapsed_time'], history_data['pid_x_i'],
                          color=self.colors['i'], label='I', linewidth=2, alpha=0.9)
        axes['pid_x'].plot(history_data['elapsed_time'], history_data['pid_x_d'],
                          color=self.colors['d'], label='D', linewidth=2, alpha=0.9)

        axes['pid_x'].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        axes['pid_x'].set_xlim(current_time - 5, current_time + 0.5)
        # PIDデータの実際の範囲に基づく設定
        axes['pid_x'].set_ylim(-0.1, 0.1)
        axes['pid_x'].grid(True, alpha=0.3, color='gray')
        axes['pid_x'].legend(loc='upper right', fontsize=8, framealpha=0.8)
        axes['pid_x'].set_facecolor('#2e2e2e')

        # 5. Y軸PID成分
        axes['pid_y'].clear()
        axes['pid_y'].set_title('Y軸 PID成分', fontsize=12, color='white')
        axes['pid_y'].set_xlabel('時間 [s]', fontsize=10, color='white')
        axes['pid_y'].set_ylabel('出力値', fontsize=10, color='white')

        axes['pid_y'].plot(history_data['elapsed_time'], history_data['pid_y_p'],
                          color=self.colors['p'], label='P', linewidth=2, alpha=0.9)
        axes['pid_y'].plot(history_data['elapsed_time'], history_data['pid_y_i'],
                          color=self.colors['i'], label='I', linewidth=2, alpha=0.9)
        axes['pid_y'].plot(history_data['elapsed_time'], history_data['pid_y_d'],
                          color=self.colors['d'], label='D', linewidth=2, alpha=0.9)

        axes['pid_y'].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        axes['pid_y'].set_xlim(current_time - 5, current_time + 0.5)
        # PIDデータの実際の範囲に基づく設定
        axes['pid_y'].set_ylim(-0.1, 0.1)
        axes['pid_y'].grid(True, alpha=0.3, color='gray')
        axes['pid_y'].legend(loc='upper right', fontsize=8, framealpha=0.8)
        axes['pid_y'].set_facecolor('#2e2e2e')

        # 6. マーカー検出数
        axes['markers'].clear()
        axes['markers'].set_title('検出マーカー数', fontsize=12, color='white')
        axes['markers'].set_xlabel('時間 [s]', fontsize=10, color='white')
        axes['markers'].set_ylabel('マーカー数', fontsize=10, color='white')

        # バーチャートで表示
        axes['markers'].fill_between(history_data['elapsed_time'], 0,
                                     history_data['marker_count'],
                                     color=self.colors['marker'], alpha=0.6)
        axes['markers'].plot(history_data['elapsed_time'], history_data['marker_count'],
                            color=self.colors['marker'], linewidth=2)

        # 現在のマーカー数を強調
        axes['markers'].axvline(x=current_time, color='red', linestyle='--', alpha=0.7)
        axes['markers'].text(current_time, 4.5, f'{int(current_data["marker_count"])}個',
                            ha='center', fontsize=14, color='white',
                            bbox=dict(boxstyle='round', facecolor='red', alpha=0.7))

        axes['markers'].set_xlim(current_time - 10, current_time + 1)
        axes['markers'].set_ylim(0, 5)
        axes['markers'].grid(True, alpha=0.3, color='gray')
        axes['markers'].set_facecolor('#2e2e2e')

        # 軸の色を再設定
        for ax in axes.values():
            if ax != axes['video']:
                ax.tick_params(colors='white', labelsize=9)
                for spine in ax.spines.values():
                    spine.set_edgecolor('gray')

        return []

    def generate_video(self):
        """統合ビジュアライゼーション動画を生成"""
        print("\n動画生成を開始します...")

        # データ読み込み
        self.load_data()

        # CSVデータを動画FPSに補間
        print("データを補間中...")
        interpolated_df = self.interpolate_csv_to_video_fps()

        # 動画フレームを事前に読み込み（メモリに余裕がある場合）
        print("動画フレームを読み込み中...")
        video_frames = []
        for i in range(self.sync_frame_count):
            ret, frame = self.video_cap.read()
            if ret:
                # BGRからRGBに変換
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                video_frames.append(frame_rgb)
            else:
                break

            if i % 100 == 0:
                print(f"  フレーム {i}/{self.sync_frame_count} 読み込み完了")

        self.video_cap.release()

        # Figure作成
        print("グラフを初期化中...")
        fig, axes = self.create_figure()


        # 出力パスの設定
        if self.output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.output_path = os.path.join('animation_results',
                                           f'synchronized_flight_{timestamp}.mp4')

        # 出力ディレクトリ作成
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        # アニメーション作成
        print(f"アニメーション生成中... (出力: {self.output_path})")

        # FFMpegWriterの設定
        writer = FFMpegWriter(fps=self.output_fps,
                             metadata={'title': 'Flight Data Visualization'},
                             codec='libx264',
                             bitrate=8000,
                             extra_args=['-pix_fmt', 'yuv420p'])

        # アニメーションをファイルに書き出し
        with writer.saving(fig, self.output_path, dpi=100):
            for frame_idx in range(len(interpolated_df)):
                self.animate(frame_idx, axes, interpolated_df, video_frames)
                writer.grab_frame()

                if frame_idx % 30 == 0:
                    progress = (frame_idx / len(interpolated_df)) * 100
                    print(f"  進捗: {progress:.1f}% ({frame_idx}/{len(interpolated_df)})")

        plt.close(fig)
        print(f"\n動画生成完了: {self.output_path}")

        return self.output_path


def select_files():
    """CSVファイルと動画ファイルを選択する対話型インターフェース"""
    import glob

    print("\n=== ドローン飛行データ同期ビジュアライゼーション ===\n")

    # CSVファイル選択
    csv_files = sorted(glob.glob('flight_logs/*.csv'))
    if not csv_files:
        print("エラー: flight_logsフォルダにCSVファイルが見つかりません")
        return None, None

    print("利用可能なCSVファイル:")
    for i, csv_file in enumerate(csv_files):
        filename = os.path.basename(csv_file)
        print(f"  {i+1}. {filename}")

    while True:
        try:
            csv_choice = input(f"\nCSVファイルを選択してください (1-{len(csv_files)}): ")
            csv_idx = int(csv_choice) - 1
            if 0 <= csv_idx < len(csv_files):
                selected_csv = csv_files[csv_idx]
                break
            else:
                print("無効な選択です。もう一度お試しください。")
        except ValueError:
            print("数値を入力してください。")

    # 動画ファイル選択
    video_files = sorted(glob.glob('smartphone_videos/*.mp4'))
    if not video_files:
        print("\n注意: smartphone_videosフォルダに動画ファイルが見つかりません")
        print("スマホで撮影した動画ファイル(MP4)をsmartphone_videosフォルダに配置してください。")
        return None, None

    print("\n利用可能な動画ファイル:")
    for i, video_file in enumerate(video_files):
        filename = os.path.basename(video_file)
        print(f"  {i+1}. {filename}")

    while True:
        try:
            video_choice = input(f"\n動画ファイルを選択してください (1-{len(video_files)}): ")
            video_idx = int(video_choice) - 1
            if 0 <= video_idx < len(video_files):
                selected_video = video_files[video_idx]
                break
            else:
                print("無効な選択です。もう一度お試しください。")
        except ValueError:
            print("数値を入力してください。")

    print(f"\n選択されたファイル:")
    print(f"  CSV: {os.path.basename(selected_csv)}")
    print(f"  動画: {os.path.basename(selected_video)}")

    return selected_csv, selected_video


def main():
    """メイン実行関数"""
    # ファイル選択
    csv_path, video_path = select_files()

    if csv_path is None or video_path is None:
        print("\nファイル選択がキャンセルされました。")
        return

    # 確認
    confirm = input("\n動画生成を開始しますか？ (y/n): ")
    if confirm.lower() != 'y':
        print("キャンセルされました。")
        return

    try:
        # ビジュアライゼーション生成
        synchronizer = FlightVideoSynchronizer(csv_path, video_path)
        output_path = synchronizer.generate_video()

        print("\n=== 処理完了 ===")
        print(f"生成された動画: {output_path}")
        print("\n動画を確認してください。")

    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()