from backend.database.session import SessionLocal, engine
from backend.database.base_class import Base
from backend.repositories.common import source_repo

def test_crud_source():
    """
    Test generic repository capabilities using the Source model.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Test Create
        source_in = {"name": "Test Repository Source", "type": "Test", "url": "http://test.repo"}
        source = source_repo.create(db, obj_in=source_in)
        assert source.id is not None
        assert source.name == "Test Repository Source"
        
        # 2. Test Get
        fetched_source = source_repo.get(db, id=source.id)
        assert fetched_source is not None
        assert fetched_source.id == source.id
        
        # 3. Test Update
        update_in = {"name": "Updated Repo Source", "type": "Updated Test"}
        updated_source = source_repo.update(db, db_obj=fetched_source, obj_in=update_in)
        assert updated_source.name == "Updated Repo Source"
        
        # Check that update persisted by re-fetching
        refetched_source = source_repo.get(db, id=source.id)
        assert refetched_source.name == "Updated Repo Source"
        
        # 4. Test List (get_multi)
        # Create a second one to test lists
        source_repo.create(db, obj_in={"name": "Second Source", "type": "Test"})
        sources = source_repo.get_multi(db, limit=10)
        assert len(sources) >= 2
        
        # 5. Test Delete (remove)
        deleted_source = source_repo.remove(db, id=source.id)
        assert deleted_source.id == source.id
        
        # Verify it's actually deleted
        missing_source = source_repo.get(db, id=source.id)
        assert missing_source is None
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
