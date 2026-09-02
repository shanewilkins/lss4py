# Extending LSS4PY: Building Custom Adapters

LSS4PY is designed to accept data from many sources through a stable adapter interface.
This guide explains how to build external adapters (e.g., database-specific, cloud-specific)
without modifying LSS4PY core.

## Architecture

LSS4PY's adapter layer normalizes data from any source into two contracts:

- **Tabular data** (measurements, durations, dimensions) → `pd.DataFrame | pl.DataFrame` + `AdapterSchema`
- **Event logs** (case ID, activity, timestamp) → `EventLog` domain model + `AdapterSchema`

Adapters sit between your data source and LSS4PY analytics. They translate source-specific
schemas and error handling into LSS4PY's canonical formats.

```
Your Data Source
    ↓ (custom SDK/API)
External Adapter
    ↓ (returns DataFrame + AdapterSchema)
LSS4PY Calculations
    ↓
AnalyticalResult
```

## Building a Tabular Adapter

All tabular adapters inherit from `lss4py.adapters.TabularAdapter`.

### Example: PostgreSQL Adapter

```python
# my_company/lss4py_postgres_adapter.py

from pathlib import Path
from typing import Literal

import psycopg2
import narwhals as nw
from lss4py.adapters import TabularAdapter, AdapterSchema


class PostgresTabularAdapter(TabularAdapter):
    """Load process measurements from a PostgreSQL database."""
    
    def __init__(self, connection_string: str, table_name: str):
        """
        Args:
            connection_string: psycopg2 connection string
            table_name: table to load
        """
        self.connection_string = connection_string
        self.table_name = table_name
        self._connection = None
    
    def schema(self) -> AdapterSchema:
        """Inspect table schema without loading full data."""
        conn = psycopg2.connect(self.connection_string)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT * FROM {self.table_name} LIMIT 0")
            columns = [desc[0] for desc in cursor.description]
            
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            row_count = cursor.fetchone()[0]
            
            # Infer types from column info
            column_types = {}
            for col in columns:
                cursor.execute(
                    f"""
                    SELECT data_type FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                    """,
                    (self.table_name, col),
                )
                pg_type = cursor.fetchone()[0]
                column_types[col] = self._pg_to_narwhals_type(pg_type)
            
            return AdapterSchema(
                column_names=frozenset(columns),
                column_types=column_types,
                row_count=row_count,
                key_columns=[],  # Infer from your use case
            )
        
        finally:
            cursor.close()
            conn.close()
    
    def load(
        self,
        backend: Literal["pandas", "polars"] = "pandas",
    ) -> tuple:
        """Load and normalize data.
        
        Returns:
            (DataFrame, AdapterSchema) where DataFrame is native to backend
        """
        import pandas as pd
        
        conn = psycopg2.connect(self.connection_string)
        
        try:
            df = pd.read_sql(f"SELECT * FROM {self.table_name}", conn)
            schema = self._build_schema(df)
            
            # Convert to requested backend
            if backend == "pandas":
                return df, schema
            elif backend == "polars":
                import polars as pl
                return pl.from_pandas(df), schema
        
        finally:
            conn.close()
    
    def _build_schema(self, df) -> AdapterSchema:
        """Build AdapterSchema from loaded DataFrame."""
        column_types = {col: str(df[col].dtype) for col in df.columns}
        return AdapterSchema(
            column_names=frozenset(df.columns),
            column_types=column_types,
            row_count=len(df),
            key_columns=[],
        )
    
    @staticmethod
    def _pg_to_narwhals_type(pg_type: str) -> str:
        """Map PostgreSQL type to Narwhals type string."""
        mapping = {
            "integer": "int64",
            "bigint": "int64",
            "numeric": "float64",
            "double precision": "float64",
            "text": "string",
            "timestamp": "datetime[μs]",
            "date": "date",
        }
        return mapping.get(pg_type, "string")
```

### Usage

```python
from my_company.lss4py_postgres_adapter import PostgresTabularAdapter
from lss4py import lead_time

# Load data via adapter
adapter = PostgresTabularAdapter(
    "postgresql://user:password@localhost/mydb",
    "process_events",
)

df, schema = adapter.load(backend="polars")

# Validate schema before running analytics
required_fields = ["case_id", "started_at", "completed_at"]
missing = schema.validate_required_fields(required_fields)
if missing:
    raise ValueError(f"Missing required fields: {missing}")

# Run analytics
result = lead_time(
    df,
    case_id_column="case_id",
    started_at_column="started_at",
    completed_at_column="completed_at",
)
print(result)
```

## Building an Event-Log Adapter

Event-log adapters inherit from `lss4py.adapters.EventLogAdapter` and return the
`EventLog` domain model.

```python
from lss4py.adapters import EventLogAdapter
from lss4py.domain.models import EventLog


class KafkaEventLogAdapter(EventLogAdapter):
    """Stream event logs from a Kafka topic."""
    
    def __init__(self, topic: str, bootstrap_servers: list[str]):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
    
    def schema(self) -> AdapterSchema:
        """Peek at a few events to infer schema."""
        # Connect to Kafka, consume 10 events
        ...
    
    def load(self, backend: str = "pandas") -> tuple[EventLog, AdapterSchema]:
        """Consume events and normalize to EventLog."""
        from kafka import KafkaConsumer
        
        consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id="lss4py-adapter",
        )
        
        events = []
        for message in consumer:
            events.append(json.loads(message.value))
        
        # Required fields: case_id, activity, timestamp
        return EventLog(events=events), self._build_schema(events)
```

## Public Adapter API

The following are part of LSS4PY's public adapter contract and are stable across
releases:

```python
from lss4py.adapters import (
    TabularAdapter,         # Base class for tabular adapters
    EventLogAdapter,        # Base class for event-log adapters
    AdapterSchema,          # Schema contract returned by all adapters
)

from lss4py.domain.models import (
    EventLog,               # Event-log domain model
    ProcessModelIR,         # Process model (for reference)
)
```

External adapters should import **only** from `lss4py.adapters` and `lss4py.domain.models`.

Do not import from:
- `lss4py.analytics` (calculations)
- `lss4py.kernels` (numerical code)
- `lss4py.workflows` (end-to-end workflows)
- `lss4py.reporting` (visualization and bundles)

## Testing Your Adapter

```python
import pytest
from my_company.lss4py_postgres_adapter import PostgresTabularAdapter


@pytest.fixture
def adapter():
    """Adapter connected to test database."""
    return PostgresTabularAdapter(
        "postgresql://user:password@localhost/testdb",
        "test_events",
    )


def test_schema_inspection(adapter):
    """Schema should be available without loading full data."""
    schema = adapter.schema()
    assert "case_id" in schema.column_names
    assert schema.row_count >= 0


def test_load_pandas(adapter):
    """Load should return pandas DataFrame."""
    df, schema = adapter.load(backend="pandas")
    assert len(df) == schema.row_count
    assert list(df.columns) == sorted(schema.column_names)


def test_load_polars(adapter):
    """Load should return Polars DataFrame when requested."""
    df, schema = adapter.load(backend="polars")
    # df is now a Polars DataFrame
    assert df.shape[0] == schema.row_count


def test_schema_validation(adapter):
    """Adapter schema should report missing required fields."""
    schema = adapter.schema()
    missing = schema.validate_required_fields(
        ["case_id", "started_at", "completed_at"]
    )
    assert len(missing) == 0  # All present in test data
```

## Packaging and Distribution

Consider distributing your adapter as a separate package:

```toml
# pyproject.toml for my_company.lss4py_postgres_adapter

[project]
name = "lss4py-postgres-adapter"
version = "0.1.0"
description = "PostgreSQL adapter for LSS4PY"
dependencies = [
    "lss4py>=0.2.0",
    "psycopg2-binary>=2.9.0",
    "narwhals>=1.0.0",
]
```

Then users can install:

```bash
uv pip install lss4py-postgres-adapter
```

## Support and Feedback

If you build an adapter, please:
1. Test against the public API surface (listed above)
2. Report issues to the LSS4PY project
3. Consider contributing adapters back if they're general-purpose

Do not:
- Depend on internal LSS4PY modules (those can change)
- Assume pandas-specific behavior (use Narwhals for compatibility)
- Import from workflows, visualization, or kernels
