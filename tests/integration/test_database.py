from sqlalchemy import text

def test_database_connection(db_session):
    """Test that we can connect to the database and execute a basic query."""
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1
