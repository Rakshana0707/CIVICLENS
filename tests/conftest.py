import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.api.app import create_app
from backend.models.common import Source, Document, ProcessingStatus

# Use an in-memory SQLite database for blazing fast and isolated tests
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    return create_engine(TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(scope="session")
def tables(engine):
    """Create tables once per test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine, tables):
    """Returns an isolated database session with a rollback strategy for clean tests."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def app():
    """Create a Flask app configured for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def api_client(app):
    """Create a test client for the API."""
    with app.test_client() as client:
        yield client

@pytest.fixture
def sample_source(db_session):
    """Fixture providing a sample Source."""
    source = Source(name="Fixture Source", type="Government")
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source

@pytest.fixture
def sample_document(db_session, sample_source):
    """Fixture providing a sample Document linked to the Source."""
    doc = Document(
        title="Fixture Document", 
        content="This is fixture text content.", 
        source_id=sample_source.id, 
        status=ProcessingStatus.COMPLETED
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc
