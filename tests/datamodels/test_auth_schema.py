"""Auth tables live in the dedicated ``auth`` schema (#580)."""

from ca_biositing.datamodels.models import ApiKey, ApiUser


def test_auth_tables_are_in_auth_schema():
    assert ApiUser.__table__.schema == "auth"
    assert ApiKey.__table__.schema == "auth"


def test_api_key_foreign_key_targets_auth_schema():
    (fk,) = ApiKey.__table__.c.api_user_id.foreign_keys
    assert fk.target_fullname == "auth.api_user.id"
