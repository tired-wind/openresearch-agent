import io
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from backend.analysis import read_table,analyze,InputError

@pytest.fixture
def demo(): return pd.read_csv(Path(__file__).parents[1]/'demo/synthetic_health.csv')

def test_real_classification_and_leakage(demo):
    a=analyze(demo,'outcome')
    assert {'participant_id','target_copy'} <= {x['feature'] for x in a['excluded']}
    assert not set(a['split']['train_indices']) & set(a['split']['test_indices'])
    assert a['n_train']+a['n_test']==320
    assert a['metrics']['roc_auc']>.6
    assert all(np.isfinite(list(a['metrics'].values())))
    assert a['cv']['folds']==3

def test_regression(demo):
    demo['continuous']=2*demo.age+3*demo.bmi.fillna(27)+np.random.default_rng(1).normal(0,8,len(demo))
    a=analyze(demo.drop(columns=['outcome','target_copy']),'continuous','regression')
    assert a['metrics']['rmse']<a['metrics']['baseline_rmse']

def test_duplicates_removed_before_split(demo):
    a=analyze(pd.concat([demo,demo.iloc[:10]]),'outcome')
    assert a['n_analyzed']==320

def test_reject_rare_target(demo):
    demo['outcome']=0;demo.loc[0,'outcome']=1
    with pytest.raises(InputError,match='at least 8'):analyze(demo,'outcome')

@pytest.mark.parametrize('raw',[b'a,a\n1,2',b'a,\n1,2',b'a,b\n',b''])
def test_bad_csv(raw):
    with pytest.raises(InputError):read_table(raw,'.csv')

def test_xlsx_and_formula_rejection():
    import openpyxl
    book=openpyxl.Workbook(); ws=book.active;ws.append(['a','b']);ws.append([1,2]);out=io.BytesIO();book.save(out)
    assert read_table(out.getvalue(),'.xlsx').shape==(1,2)
    ws['A2']='=1+1';out=io.BytesIO();book.save(out)
    with pytest.raises(InputError,match='Formula'):read_table(out.getvalue(),'.xlsx')

def test_zip_bomb_rejected():
    import zipfile
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('xl/fake.xml',b'0'*(31*1024*1024))
    with pytest.raises(InputError,match='expands'):read_table(out.getvalue(),'.xlsx')

def test_unknown_and_small_target(demo):
    with pytest.raises(InputError):analyze(demo,'missing')
    with pytest.raises(InputError):analyze(demo.head(20),'outcome')
