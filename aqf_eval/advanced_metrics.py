import pandas as pd

def field_efficiency(df):
    df=df.copy()
    df['field_efficiency']=df['strict_coverage']/(df['field_count']+1e-9)
    df['operator_efficiency']=df['strict_coverage']/(df['operator_count']+1e-9)
    return df

def redundancy_ratio(detail_df, forms):
    used=set()
    for _,r in detail_df.iterrows():
        for f in (r.get('matched_fields') or []): used.add(f)
    out=[]
    for form in forms:
        fields=[f.get('field_id') for f in form.get('fields',[])]
        unused=len([f for f in fields if f not in used])
        out.append({'method':form['method'],'redundancy_ratio':unused/(len(fields) or 1)})
    return pd.DataFrame(out)

def coverage_vs_complexity(summary, complexity):
    df=complexity.merge(summary[['method','strict_coverage']],on='method')
    return df[['method','form_complexity_elements','strict_coverage']]

