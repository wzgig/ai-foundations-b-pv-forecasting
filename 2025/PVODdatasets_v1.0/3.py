# -*- coding: utf-8 -*-
"""
Created on 2025/5/24 19:57

@author: Prince
"""
# -*- coding: utf-8 -*-
"""
Created on 2025/5/24 15:54

@author: Prince
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import mean_squared_error, mean_absolute_error
from scipy import stats
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.dates as mdates
from matplotlib import rcParams
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False  # 修复负号显示问题


# ==================== 全局配置 ====================
class Config:
    # 数据配置
    DATA_PATH = "station00.csv"
    TEST_MONTHS = [2, 5, 8, 11]
    INPUT_LENGTH = 96
    FORECAST_LENGTH = 96

    # 模型配置
    HIDDEN_DIM = 64
    NUM_LAYERS = 2
    BATCH_SIZE = 64
    EPOCHS = 50
    PATIENCE = 5
    LR = 0.001

    # 可视化配置
    PLOT_STYLE = "whitegrid"
    COLOR_PALETTE = ["#2c7bb6", "#d7191c", "#fdae61", "#abdda4"]

    @classmethod
    def setup_environment(cls):
        rcParams['font.family'] = 'SimHei'
        rcParams['axes.unicode_minus'] = False
        sns.set_theme(style=cls.PLOT_STYLE)
        plt.rcParams.update({
            'figure.figsize': (10, 5),
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'grid.linestyle': '--',
            'figure.dpi': 150
        })


# ==================== 数据处理器 ====================
class DataProcessor:
    def __init__(self):
        self.df = None
        self.train_X = None
        self.train_Y = None
        self.test_X = None
        self.test_Y = None
        self.test_timestamps = None

    def load_and_preprocess(self):
        """加载并预处理数据（完整修复版本）"""
        # 加载数据
        self.df = pd.read_csv(Config.DATA_PATH)

        # 转换日期时间列
        self.df['date_time'] = pd.to_datetime(self.df['date_time'])

        # 创建date列并确保类型正确
        self.df['date'] = pd.to_datetime(self.df['date_time'].dt.date)

        self._add_time_features()  # 调用统一的方法
        self._split_train_test()
        self._create_sequences()
        self._validate_data()

    def _add_time_features(self):
        """统一处理所有时间相关特征"""
        # 确保date_time列是datetime类型
        self.df['date_time'] = pd.to_datetime(self.df['date_time'])

        # 添加派生时间特征
        self.df['month'] = self.df['date_time'].dt.month
        self.df['day'] = self.df['date_time'].dt.day
        self.df['date'] = self.df['date_time'].dt.normalize()  # 等效于.date但返回datetime类型
        self.df['is_daytime'] = self.df['power'] > 0.05

    def _split_train_test(self):
        """划分训练测试集（完整修复版本）"""
        test_dates = []

        try:
            # 获取唯一日期并确保类型
            unique_dates = pd.to_datetime(self.df['date'].unique())

            for month in Config.TEST_MONTHS:
                # 筛选月份
                month_mask = unique_dates.month == month
                month_dates = unique_dates[month_mask]

                if len(month_dates) >= 7:
                    test_dates.extend(month_dates[-7:].tolist())

            # 创建set列
            self.df['set'] = np.where(
                self.df['date'].isin(test_dates),
                'test',
                'train'
            )

        except Exception as e:
            print(f"划分数据集时发生错误: {str(e)}")
            print("当前date列样例数据:", self.df['date'].head())
            raise

    def _validate_data(self):
        """数据验证"""
        # 验证日期类型
        if not pd.api.types.is_datetime64_any_dtype(self.df['date']):
            raise TypeError("date列最终数据类型错误: {}".format(self.df['date'].dtype))

        # 验证set列值
        valid_sets = {'train', 'test'}
        if not set(self.df['set'].unique()).issubset(valid_sets):
            raise ValueError("set列包含无效值")

    def _create_sequences(self):
        """创建时序样本"""
        # 训练序列
        train_X, train_Y = [], []
        values = self.df['power'].values
        set_flags = self.df['set'].values

        for i in range(len(values) - Config.INPUT_LENGTH - Config.FORECAST_LENGTH):
            if set_flags[i] == 'train' and set_flags[i + Config.INPUT_LENGTH + Config.FORECAST_LENGTH - 1] == 'train':
                train_X.append(values[i:i + Config.INPUT_LENGTH])
                train_Y.append(values[i + Config.INPUT_LENGTH:i + Config.INPUT_LENGTH + Config.FORECAST_LENGTH])

        self.train_X = np.array(train_X)
        self.train_Y = np.array(train_Y)

        # 测试序列
        test_dates = self.df[self.df['set'] == 'test']['date'].unique()
        strict_test_X, strict_test_Y, strict_test_timestamps = [], [], []

        for test_day in test_dates:
            prev_day = test_day - pd.Timedelta(days=1)
            input_seq = self.df[self.df['date'] == prev_day]['power'].values
            output_seq = self.df[self.df['date'] == test_day]['power'].values

            if len(input_seq) == Config.INPUT_LENGTH and len(output_seq) == Config.FORECAST_LENGTH:
                strict_test_X.append(input_seq)
                strict_test_Y.append(output_seq)
                strict_test_timestamps.append(pd.Timestamp(test_day))

        self.test_X = np.array(strict_test_X)
        self.test_Y = np.array(strict_test_Y)
        self.test_timestamps = np.array(strict_test_timestamps)


# ==================== 模型构建器 ====================
class ModelBuilder:
    @staticmethod
    def build_model(model_type='fusion', input_len=96):
        """模型工厂方法"""
        if model_type == 'lstm':
            return LSTMBranch(input_len)
        elif model_type == 'tcn':
            return TCNBranch(input_len)
        elif model_type == 'mlp':
            return MLPBranch(input_len)
        else:
            return FusionModel(input_len)


class LSTMBranch(nn.Module):
    def __init__(self, input_len, hidden_dim=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, input_len)

    def forward(self, x):
        x = x.unsqueeze(-1)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


class TCNBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, dilation=1):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size,
                              padding=(kernel_size - 1) * dilation // 2, dilation=dilation)
        self.bn = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class TCNBranch(nn.Module):
    def __init__(self, input_len):
        super().__init__()
        self.net = nn.Sequential(
            TCNBlock(1, 16, dilation=1),
            TCNBlock(16, 32, dilation=2),
            TCNBlock(32, 64, dilation=4)
        )
        self.fc = nn.Linear(64, input_len)

    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.net(x)
        return self.fc(x.mean(dim=2))


class MLPBranch(nn.Module):
    def __init__(self, input_len):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_len, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, input_len)
        )

    def forward(self, x):
        return self.fc(x)


class FusionModel(nn.Module):
    def __init__(self, input_len=96):
        super().__init__()
        self.lstm_branch = LSTMBranch(input_len)
        self.tcn_branch = TCNBranch(input_len)
        self.mlp_branch = MLPBranch(input_len)

        self.attn = nn.Sequential(
            nn.Linear(3 * input_len, 128),
            nn.ReLU(),
            nn.Linear(128, 3),
            nn.Softmax(dim=1)
        )
        self.output_layer = nn.Linear(input_len, input_len)

    def forward(self, x):
        lstm_out = self.lstm_branch(x)
        tcn_out = self.tcn_branch(x)
        mlp_out = self.mlp_branch(x)

        concat = torch.cat([lstm_out, tcn_out, mlp_out], dim=1)
        weights = self.attn(concat)
        out = (weights[:, 0:1] * lstm_out +
               weights[:, 1:2] * tcn_out +
               weights[:, 2:3] * mlp_out)
        return self.output_layer(out)


# ==================== 模型训练器 ====================
class ModelTrainer:
    def __init__(self, model, data_processor):
        self.model = model
        self.data_processor = data_processor
        self.max_power = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def train(self):
        """执行训练流程"""
        self._prepare_data()
        self.model.to(self.device)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=Config.LR)
        criterion = nn.MSELoss()

        train_loader, val_loader = self._create_loaders()
        best_loss = float('inf')
        patience_counter = 0

        for epoch in range(Config.EPOCHS):
            # 训练阶段
            self.model.train()
            train_loss = self._run_epoch(train_loader, optimizer, criterion)

            # 验证阶段
            self.model.eval()
            val_loss = self._run_epoch(val_loader, None, criterion)

            # 早停机制
            if val_loss < best_loss:
                best_loss = val_loss
                patience_counter = 0
                torch.save(self.model.state_dict(), 'models/best_model.pth')
            else:
                patience_counter += 1
                if patience_counter >= Config.PATIENCE:
                    break

            print(f"Epoch {epoch + 1}: Train Loss={train_loss:.4f}, Val Loss={val_loss:.4f}")

        self.model.load_state_dict(torch.load('models/best_model.pth'))
        return self.model

    def _prepare_data(self):
        """数据归一化处理"""
        self.max_power = self.data_processor.train_X.max()
        self.data_processor.train_X /= self.max_power
        self.data_processor.train_Y /= self.max_power

    def _create_loaders(self):
        """创建数据加载器"""
        val_size = int(len(self.data_processor.train_X) * 0.1)
        indices = np.random.permutation(len(self.data_processor.train_X))

        train_set = TensorDataset(
            torch.tensor(self.data_processor.train_X[indices[val_size:]], dtype=torch.float32),
            torch.tensor(self.data_processor.train_Y[indices[val_size:]], dtype=torch.float32)
        )
        val_set = TensorDataset(
            torch.tensor(self.data_processor.train_X[indices[:val_size]], dtype=torch.float32),
            torch.tensor(self.data_processor.train_Y[indices[:val_size]], dtype=torch.float32)
        )

        return (
            DataLoader(train_set, batch_size=Config.BATCH_SIZE, shuffle=True),
            DataLoader(val_set, batch_size=Config.BATCH_SIZE)
        )

    def _run_epoch(self, loader, optimizer, criterion):
        """执行单个epoch"""
        total_loss = 0
        for xb, yb in loader:
            xb, yb = xb.to(self.device), yb.to(self.device)

            if optimizer:
                optimizer.zero_grad()
                loss = criterion(self.model(xb), yb)
                loss.backward()
                optimizer.step()
            else:
                with torch.no_grad():
                    loss = criterion(self.model(xb), yb)

            total_loss += loss.item() * xb.size(0)

        return total_loss / len(loader.dataset)


# ==================== 模型评估器 ====================
class ModelEvaluator:
    def __init__(self, model, data_processor, max_power):
        self.model = model
        self.data_processor = data_processor
        self.max_power = max_power
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def evaluate(self):
        """执行完整评估"""
        preds = self._get_predictions()
        metrics = self._calculate_metrics(preds)
        self._export_results(preds)
        return preds, metrics

    def _get_predictions(self):
        """获取模型预测结果"""
        self.model.eval()
        X_tensor = torch.tensor(self.data_processor.test_X / self.max_power,
                                dtype=torch.float32).to(self.device)
        with torch.no_grad():
            preds = self.model(X_tensor).cpu().numpy() * self.max_power
        return preds

    def _calculate_metrics(self, preds):
        """计算评估指标"""
        # 白昼时段指标
        day_true, day_pred = self._get_daytime_values(preds)
        rmse = np.sqrt(mean_squared_error(day_true, day_pred))
        mae = mean_absolute_error(day_true, day_pred)
        mape = np.mean(np.abs((day_true - day_pred) / (day_true + 1e-5))) * 100

        # 附件1指标
        capacity = 6600 / 1000  # MW
        err = (day_true - day_pred) / capacity
        metrics = {
            'RMSE': rmse,
            'MAE': mae,
            'MAPE': mape,
            'E_rmse': np.sqrt(np.mean(err ** 2)),
            'E_mae': np.mean(np.abs(err)),
            'C_R': (1 - np.sqrt(np.mean(err ** 2))) * 100
        }
        return metrics

    def _get_daytime_values(self, preds):
        """提取白昼时段的真实值和预测值"""
        day_true, day_pred = [], []
        for i, ts in enumerate(self.data_processor.test_timestamps):
            mask = (self.data_processor.df['date_time'] >= ts) & \
                   (self.data_processor.df['date_time'] < ts + pd.Timedelta(days=1))
            is_daytime = self.data_processor.df.loc[mask, 'is_daytime'].values[:96]
            day_pred.extend(preds[i][is_daytime])
            day_true.extend(self.data_processor.test_Y[i][is_daytime])
        return np.array(day_true), np.array(day_pred)

    def _export_results(self, preds):
        """导出预测结果"""
        records = []
        df = self.data_processor.df.copy()

        for i, ts in enumerate(self.data_processor.test_timestamps):
            start_time = pd.to_datetime(ts)
            for j in range(96):
                forecast_time = start_time + pd.Timedelta(days=1) + pd.Timedelta(minutes=15 * j)
                real_val = df[df['date_time'] == forecast_time]['power'].values
                records.append({
                    "起报时间": start_time.replace(hour=0, minute=0, second=0),
                    "预报时间": forecast_time,
                    "实际功率 (MW)": real_val[0] if len(real_val) > 0 else np.nan,
                    "预测功率 (MW)": preds[i, j]
                })

        pd.DataFrame(records).to_csv('prediction_results.csv', index=False)


# ==================== 可视化器 ====================
class Visualizer:
    def __init__(self, data_processor):
        self.df = data_processor.df
        self.test_timestamps = data_processor.test_timestamps
        self.test_Y = data_processor.test_Y

    def plot_all(self, preds, metrics):
        """执行全套可视化"""
        self.basic_plots(preds)
        self.professional_plots(preds, metrics)
        self.interactive_plot(preds)

    def basic_plots(self, preds):
        """基础可视化"""
        self._plot_time_series_comparison(preds)
        self._plot_error_distribution(preds)
        self._plot_scatter(preds)

    def professional_plots(self, preds, metrics):
        """专业可视化"""
        self._plot_error_analysis(preds)
        self._plot_metrics_dashboard(metrics)

    def interactive_plot(self, preds):
        """交互式可视化"""
        fig = go.Figure()
        sample_idx = 0
        ts = self.test_timestamps[sample_idx]

        # 添加实际值轨迹
        self._add_trace(fig, ts, self.test_Y[sample_idx],
                        '实际功率', '#1f77b4')

        # 添加预测值轨迹
        self._add_trace(fig, ts, preds[sample_idx],
                        '预测功率', '#ff7f0e', dash='dot')

        fig.update_layout(
            title=f'交互式可视化 - {ts.strftime("%Y-%m-%d")}',
            xaxis_title='时间',
            yaxis_title='功率 (MW)',
            template='plotly_white',
            height=500
        )
        fig.show()

    def _add_trace(self, fig, ts, values, name, color, dash=None):
        """添加轨迹辅助方法"""
        mask = (self.df['date_time'] >= ts) & \
               (self.df['date_time'] < ts + pd.Timedelta(days=1))
        time_points = self.df.loc[mask, 'date_time'].values
        is_daytime = self.df.loc[mask, 'is_daytime'].values[:96]

        min_len = min(len(time_points), len(values))
        fig.add_trace(go.Scatter(
            x=time_points[:min_len][is_daytime[:min_len]],
            y=values[:min_len][is_daytime[:min_len]],
            name=name,
            line=dict(color=color, width=3, dash=dash),
            mode='lines+markers'
        ))

    def _plot_time_series_comparison(self, preds):
        """时间序列对比图"""
        plt.figure(figsize=(14, 6))
        sample_idx = 0
        ts = self.test_timestamps[sample_idx]

        # 获取数据
        mask = (self.df['date_time'] >= ts) & \
               (self.df['date_time'] < ts + pd.Timedelta(days=1))
        is_daytime = self.df.loc[mask, 'is_daytime'].values[:96]
        time_axis = self.df.loc[mask, 'date_time'].values[:96][is_daytime]
        pred_values = preds[sample_idx][is_daytime]
        true_values = self.test_Y[sample_idx][is_daytime]

        plt.plot(time_axis, true_values, label='真实功率',
                 color='#2c7bb6', linewidth=2)
        plt.plot(time_axis, pred_values, label='预测功率',
                 color='#d7191c', linewidth=2, linestyle='--')

        plt.title('功率预测对比')
        plt.xlabel('时间')
        plt.ylabel('功率 (MW)')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    def _plot_error_distribution(self, preds):
        """误差分布图"""
        errors = preds - self.test_Y
        plt.figure(figsize=(10, 6))
        sns.histplot(errors.flatten(), kde=True, bins=50,
                     color='#2c7bb6', edgecolor='white')
        plt.axvline(x=0, color='#d7191c', linestyle='--')
        plt.title('预测误差分布')
        plt.xlabel('误差 (MW)')
        plt.ylabel('频率')
        plt.tight_layout()
        plt.show()

    def _plot_scatter(self, preds):
        """预测-实际散点图"""
        plt.figure(figsize=(8, 6))
        flat_true = self.test_Y.flatten()
        flat_pred = preds.flatten()

        plt.scatter(flat_true, flat_pred, alpha=0.5,
                    color='#2c7bb6', edgecolor='none')
        max_val = max(flat_true.max(), flat_pred.max())
        plt.plot([0, max_val], [0, max_val], '--', color='#d7191c')
        plt.title('预测值 vs 实际值')
        plt.xlabel('实际功率 (MW)')
        plt.ylabel('预测功率 (MW)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    def _plot_error_analysis(self, preds):
        """误差分析矩阵"""
        errors = preds - self.test_Y
        plt.figure(figsize=(16, 12))

        # 误差分布
        plt.subplot(2, 2, 1)
        sns.boxplot(x=errors.flatten(), color='#2c7bb6')
        plt.title('误差分布')

        # 误差趋势
        plt.subplot(2, 2, 2)
        pd.Series(errors.flatten()).rolling(100).mean().plot(
            color='#d7191c', linewidth=2)
        plt.title('误差滑动平均趋势')

        # 正态概率图
        plt.subplot(2, 2, 3)
        stats.probplot(errors.flatten(), dist="norm", plot=plt)
        plt.title('正态概率图')

        # 残差分析
        plt.subplot(2, 2, 4)
        sns.residplot(x=self.test_Y.flatten(), y=preds.flatten(),
                      lowess=True, color='#2c7bb6',
                      line_kws={'color': '#d7191c'})
        plt.title('残差分析')
        plt.tight_layout()
        plt.show()

    def _plot_metrics_dashboard(self, metrics):
        """指标仪表盘"""
        fig = plt.figure(figsize=(12, 8))
        metrics = {
            'RMSE': metrics['RMSE'],
            'MAE': metrics['MAE'],
            'MAPE': f"{metrics['MAPE']:.1f}%",
            'C_R': f"{metrics['C_R']:.1f}%"
        }

        plt.barh(list(metrics.keys()), list(metrics.values()),
                 color=['#2c7bb6', '#d7191c', '#fdae61', '#abdda4'])
        plt.title('模型性能指标')
        plt.xlabel('数值')
        plt.grid(True, axis='x', alpha=0.3)
        plt.tight_layout()
        plt.show()


# ==================== 主程序 ====================
class Main:
    def __init__(self):
        Config.setup_environment()

    def run(self):
        # 初始化组件
        data_processor = DataProcessor()
        data_processor.load_and_preprocess()

        # 模型训练
        model = ModelBuilder.build_model()
        trainer = ModelTrainer(model, data_processor)
        trained_model = trainer.train()

        # 模型评估
        evaluator = ModelEvaluator(trained_model, data_processor, trainer.max_power)
        preds, metrics = evaluator.evaluate()

        # 结果可视化
        visualizer = Visualizer(data_processor)
        visualizer.plot_all(preds, metrics)


if __name__ == "__main__":
    main = Main()
    main.run()