import pandas as pd
from pathlib import Path
from aqf_eval.advanced_metrics import field_efficiency, redundancy_ratio, coverage_vs_complexity

def main():
    base=Path('results/aqf_eval')
    summary=pd.read_csv(base/'benchmark_coverage_summary.csv')
    comp=pd.read_csv(base/'complexity_breakdown.csv')

    df=comp.merge(summary[['method','strict_coverage']],on='method')
    df=field_efficiency(df)
    df.to_csv(base/'final_metrics_enhanced.csv',index=False)

    cov=coverage_vs_complexity(summary,comp)
    cov.to_csv(base/'coverage_complexity.csv',index=False)

if __name__=='__main__': main()
