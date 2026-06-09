import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_coverage_vs_complexity(path):
    df=pd.read_csv(path/'coverage_complexity.csv')
    for m,g in df.groupby('method'):
        plt.plot(g['form_complexity_elements'],g['strict_coverage'],label=m)
    plt.xlabel('Complexity')
    plt.ylabel('Strict Coverage')
    plt.legend()
    plt.savefig(path/'coverage_vs_complexity.png')
    plt.clf()

def plot_efficiency(path):
    df=pd.read_csv(path/'final_metrics_enhanced.csv')
    plt.bar(df['method'],df['field_efficiency'])
    plt.xticks(rotation=45,ha='right')
    plt.ylabel('Field Efficiency')
    plt.savefig(path/'field_efficiency.png')
    plt.clf()

if __name__=='__main__':
    base=Path('results/aqf_eval')
    plot_coverage_vs_complexity(base)
    plot_efficiency(base)
