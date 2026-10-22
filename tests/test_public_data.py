import pytest
from backend.analysis import read_table
from scripts.fetch_public_data import prepare


def test_heart_target_removed_and_categories_survive_csv():
    raw = b'63,1,1,145,233,1,2,150,0,2.3,3,?,6,0\n67,1,4,160,286,0,2,108,1,1.5,2,3,?,2\n'
    prepared, _ = prepare(raw, 'heart')
    loaded = read_table(prepared.to_csv(index=False).encode(), '.csv')
    assert 'num' not in loaded.columns
    assert loaded.disease_present.tolist() == [0, 1]
    assert loaded.cp.tolist() == ['cp_1', 'cp_4']
    assert loaded.ca.isna().sum() == 1 and loaded.thal.isna().sum() == 1


def test_invalid_outcome_is_not_silently_binarized():
    with pytest.raises(ValueError, match='outcome'):
        prepare(b'63,1,1,145,233,1,2,150,0,2.3,3,0,6,9\n', 'heart')


def test_breast_id_removed_and_feature_order_preserved():
    raw = ('123,M,' + ','.join(str(x) for x in range(30)) + '\n').encode()
    df, _ = prepare(raw, 'breast')
    assert 'patient_id' not in df.columns
    assert df.loc[0, 'diagnosis'] == 'M'
    assert df.loc[0, 'radius_mean'] == 0
    assert df.loc[0, 'radius_se'] == 10
    assert df.loc[0, 'fractal_dimension_worst'] == 29
