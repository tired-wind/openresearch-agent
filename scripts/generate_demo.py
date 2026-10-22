"""CC0 synthetic engineering fixture. No actual patient records or medical claims."""
from pathlib import Path
import numpy as np
import pandas as pd
rng=np.random.default_rng(20261022)
n=320
age=rng.integers(25,80,n)
bmi=rng.normal(27,5,n).round(2)
exercise=rng.uniform(0,6,n).round(2)
noise=rng.normal(0,1,n)
logit=-1+.045*(age-50)+.19*(bmi-27)-.4*(exercise-3)+.4*noise
y=rng.binomial(1,1/(1+np.exp(-logit)))
df=pd.DataFrame({'participant_id':np.arange(n)+1001,'age':age,'bmi':bmi,'exercise_hours':exercise,'smoking':rng.choice(['never','former','current'],n),'sleep_hours':rng.normal(7,1,n).round(2),'noise_marker':noise.round(3),'target_copy':y,'outcome':y})
df.loc[rng.choice(n,15,replace=False),'bmi']=np.nan
out=Path(__file__).resolve().parents[1]/'demo/synthetic_health.csv'
df.to_csv(out,index=False)
print(f'Generated {n} synthetic rows: {out}')
