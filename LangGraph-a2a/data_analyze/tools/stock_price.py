import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib as mpl
import numpy as np
from langchain_core.tools import tool

@tool
def analyze_stocks(stock_codes):
    """
    根据股票代码列表获取股票的起始价格，结束价格，区间涨跌幅，最大回撤，年化波动率
    
    Parameters:
    -----------
    stock_codes : list
        股票代码列表
    """

    start_date='20240422'
    end_date='20250422'

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    mpl.rcParams['font.family'] = 'sans-serif'
    
    # 读取数据
    data_path = os.path.join('D:\\workspace\\python\\akshare\\code06\\data', 'all_data.csv')
    df = pd.read_csv(data_path)
    
    # 转换日期格式
    df['日期'] = pd.to_datetime(df['日期'])
    
    # 创建结果列表
    all_results = []
    
    # 创建图表
    plt.figure(figsize=(15, 8))
    
    # 转换日期参数
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    # 为每个股票代码进行分析
    for stock_code in stock_codes:
        try:
            # 筛选股票数据
            print("------stock_code-------")
            print(stock_code)
            print("------------------")
            stock_data = df[df['股票代码'].astype(str).str.zfill(6) == stock_code].copy()
            
            if stock_data.empty:
                print(f"警告: 未找到股票: {stock_code}")
                continue
            
            # 筛选日期范围
            stock_data = stock_data[(stock_data['日期'] >= start_date) & (stock_data['日期'] <= end_date)]
            
            if len(stock_data) < 2:  # 确保至少有两条数据
                print(f"警告: 在指定日期范围内数据不足: {stock_code}")
                continue
            
            # 按日期排序
            stock_data = stock_data.sort_values('日期')
            
            # 计算日收益率
            stock_data['日收益率'] = stock_data['收盘'].pct_change()
            
            # 计算年化波动率 (假设一年252个交易日)
            volatility = stock_data['日收益率'].std() * np.sqrt(252) * 100
            
            # 计算关键指标
            start_price = stock_data.iloc[0]['收盘']
            end_price = stock_data.iloc[-1]['收盘']
            total_return = (end_price - start_price) / start_price * 100
            
            # 计算最大回撤
            stock_data['max_price'] = stock_data['收盘'].cummax()
            stock_data['min_price'] = stock_data['收盘'].cummin()
            stock_data['drawdown'] = (stock_data['max_price'] - stock_data['min_price']) / stock_data['max_price'] * 100
            max_drawdown = stock_data['drawdown'].max()
            
            # 添加到结果列表
            all_results.append({
                '股票代码': stock_code,
                '起始价格': start_price,
                '结束价格': end_price,
                '区间涨跌幅(%)': total_return,
                '最大回撤(%)': max_drawdown,
                '年化波动率(%)': volatility
            })
            
            # 绘制股价走势图
            plt.plot(stock_data['日期'], stock_data['收盘'], label=f'{stock_code}')
            
            # 添加关键价格标注
            plt.annotate(f'{stock_code} 起始价: {start_price:.2f}', 
                        xy=(stock_data['日期'].iloc[0], start_price),
                        xytext=(10, 10), textcoords='offset points')
            plt.annotate(f'{stock_code} 结束价: {end_price:.2f}',
                        xy=(stock_data['日期'].iloc[-1], end_price),
                        xytext=(10, -10), textcoords='offset points')
            
            # 标注最大回撤点
            max_drawdown_idx = stock_data['drawdown'].idxmax()
            if max_drawdown_idx is not None and max_drawdown_idx in stock_data.index:
                plt.annotate(f'{stock_code} 最大回撤: {max_drawdown:.2f}%',
                            xy=(stock_data.loc[max_drawdown_idx, '日期'], stock_data.loc[max_drawdown_idx, '收盘']),
                            xytext=(10, -10), textcoords='offset points')
            
        except Exception as e:
            print(f"处理股票 {stock_code} 时出错: {str(e)}")
            continue
    
    if not all_results:
        raise ValueError("没有找到任何有效的股票数据")
    
    # 创建结果DataFrame
    results = pd.DataFrame(all_results)
    
    # 保存结果到CSV
    output_dir = os.path.join('code06', 'output')
    os.makedirs(output_dir, exist_ok=True)
    results.to_csv(os.path.join(output_dir, 'stocks_analysis.csv'), index=False, encoding='utf-8-sig')
    
    # 完善图表
    plt.title(f'股价走势图 ({start_date.strftime("%Y-%m-%d")} 至 {end_date.strftime("%Y-%m-%d")})')
    plt.xlabel('日期')
    plt.ylabel('价格')
    plt.grid(True)
    plt.legend()
    
    # 调整x轴日期显示
    plt.gcf().autofmt_xdate()
    
    # 保存图表
    plt.savefig(os.path.join(output_dir, 'stocks_price_chart.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    return results

if __name__ == '__main__':
    # 示例使用
    try:
        stock_codes = ['600600','300054','600698','600573']  # 可以替换为您想要分析的股票代码列表
        results = analyze_stocks(stock_codes)
        print("\n分析结果:")
        print(results)
    except Exception as e:
        print(f"错误: {str(e)}")

