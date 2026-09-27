# Budget Repository Layer

The budget repository (`backend.repositories.budget.budget_repo`) provides a clean, abstract interface for the application layer to interact with the underlying budget database tables. It strictly adheres to the Repository Pattern, ensuring business logic (e.g., API route handlers) does not contain raw SQLAlchemy ORM queries.

## Key Capabilities

1. **`get_records(...)`**: 
   - Retrieves `BudgetRecord` rows joined with `BudgetScheme` and `BudgetDepartment` for fully hydrated relationships.
   - **Pagination**: Supports `skip` and `limit` to handle massive queries safely without crashing the backend.
   - **Filtering**: Safely parameterized queries allow filtering by `financial_year`, `budget_stage`, `department_name`, `department_id`, `scheme_name`, and `scheme_id`. Missing filters are safely ignored.

2. **Metadata Queries**:
   - **`get_available_years()`**: Returns a distinct, descending list of all financial years present in the dataset (useful for dropdown menus).
   - **`get_departments()`**: Returns a list of departments, with optional string matching.
   - **`get_schemes()`**: Returns a list of schemes, optionally constrained by a specific `department_id`.

## Usage Example

```python
from backend.database.session import SessionLocal
from backend.repositories.budget import budget_repo

db = SessionLocal()

# Fetch page 2 of budget estimates for the Health department
records, total_count = budget_repo.get_records(
    db, 
    skip=100, 
    limit=100, 
    department_name="health", 
    budget_stage=BudgetStage.budget_estimate
)

print(f"Showing 100 out of {total_count} records")
```
