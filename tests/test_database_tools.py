"""Tests for Database tools in Groq CLI Custom."""

import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from iabuilder.tools.database_tools import (
    DatabaseConnectorTool,
    DatabaseMigrationTool,
    DatabaseSchemaTool,
    QueryExecutorTool,
)


class TestDatabaseTools(unittest.TestCase):
    """Test cases for Database tools."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"

        # Create a test SQLite database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create test tables
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                title TEXT NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Insert test data
        cursor.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("John Doe", "john@example.com"),
        )
        cursor.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("Jane Smith", "jane@example.com"),
        )
        cursor.execute(
            "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
            (1, "First Post", "Hello World"),
        )

        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_database_connector_tool_sqlite(self):
        """Test DatabaseConnectorTool with SQLite."""
        tool = DatabaseConnectorTool()

        # Test successful connection
        result = tool.execute(
            database_type="sqlite",
            connection_string=str(self.db_path),
            test_connection=True,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["database_type"], "sqlite")
        self.assertIn("version", result)
        self.assertIn("tables", result)
        self.assertEqual(len(result["tables"]), 2)  # users and posts
        self.assertIn("users", result["tables"])
        self.assertIn("posts", result["tables"])

        # Test auto-detection
        os.chdir(self.test_dir)
        result = tool.execute(database_type="sqlite", test_connection=True)
        self.assertTrue(result["success"])

        # Test non-existent file
        result = tool.execute(
            database_type="sqlite",
            connection_string="/nonexistent/database.db",
            test_connection=True,
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "DatabaseFileNotFound")

        # Test connection without testing
        result = tool.execute(
            database_type="sqlite",
            connection_string=str(self.db_path),
            test_connection=False,
        )
        self.assertTrue(result["success"])
        self.assertNotIn("tables", result)

    def test_database_connector_tool_postgresql(self):
        """Test DatabaseConnectorTool with PostgreSQL (without actual connection)."""
        tool = DatabaseConnectorTool()

        # Test missing psycopg2
        result = tool.execute(
            database_type="postgresql",
            host="localhost",
            username="test_user",
            password="test_pass",
            test_connection=True,
        )
        # Should fail because psycopg2 is not installed in test environment
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingDependency")
        self.assertIn("psycopg2", result["error"])

        # Test missing username
        result = tool.execute(database_type="postgresql", test_connection=False)
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingParameter")

    def test_database_connector_tool_mysql(self):
        """Test DatabaseConnectorTool with MySQL (without actual connection)."""
        tool = DatabaseConnectorTool()

        # Test missing mysql-connector
        result = tool.execute(
            database_type="mysql",
            host="localhost",
            username="test_user",
            password="test_pass",
            test_connection=True,
        )
        # Should fail because mysql-connector is not installed in test environment
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingDependency")
        self.assertIn("mysql-connector", result["error"])

    def test_query_executor_tool_sqlite(self):
        """Test QueryExecutorTool with SQLite."""
        tool = QueryExecutorTool()

        # Test SELECT query
        result = tool.execute(
            query="SELECT * FROM users ORDER BY id",
            database_type="sqlite",
            connection_string=str(self.db_path),
        )
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["name"], "John Doe")
        self.assertEqual(result["data"][1]["name"], "Jane Smith")
        self.assertIn("id", result["columns"])
        self.assertIn("name", result["columns"])
        self.assertIn("email", result["columns"])

        # Test query with limit
        result = tool.execute(
            query="SELECT * FROM users",
            database_type="sqlite",
            connection_string=str(self.db_path),
            limit=1,
        )
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 1)

        # Test COUNT query
        result = tool.execute(
            query="SELECT COUNT(*) as user_count FROM users",
            database_type="sqlite",
            connection_string=str(self.db_path),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["data"][0]["user_count"], 2)

        # Test INSERT in safe mode (should be blocked)
        result = tool.execute(
            query="INSERT INTO users (name, email) VALUES ('Test', 'test@example.com')",
            database_type="sqlite",
            connection_string=str(self.db_path),
            safe_mode=True,
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "DestructiveQueryBlocked")

        # Test INSERT with safe mode disabled
        result = tool.execute(
            query="INSERT INTO users (name, email) VALUES ('Test User', 'test@example.com')",
            database_type="sqlite",
            connection_string=str(self.db_path),
            safe_mode=False,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["affected_rows"], 1)

        # Test invalid query
        result = tool.execute(
            query="SELECT * FROM nonexistent_table",
            database_type="sqlite",
            connection_string=str(self.db_path),
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "SQLiteQueryError")

        # Test auto-detection of database
        os.chdir(self.test_dir)
        result = tool.execute(
            query="SELECT COUNT(*) as count FROM users",
            database_type="sqlite",
        )
        self.assertTrue(result["success"])

    def test_database_schema_tool_sqlite(self):
        """Test DatabaseSchemaTool with SQLite."""
        tool = DatabaseSchemaTool()

        # Test full schema inspection
        result = tool.execute(
            database_type="sqlite",
            connection_string=str(self.db_path),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["database_type"], "sqlite")
        self.assertEqual(result["table_count"], 2)
        self.assertIn("users", result["tables"])
        self.assertIn("posts", result["tables"])

        # Check users table structure
        users_table = result["tables"]["users"]
        self.assertEqual(users_table["column_count"], 4)
        self.assertTrue(users_table["row_count"] >= 2)

        column_names = [col["name"] for col in users_table["columns"]]
        self.assertIn("id", column_names)
        self.assertIn("name", column_names)
        self.assertIn("email", column_names)
        self.assertIn("created_at", column_names)

        # Check primary key
        id_column = next(col for col in users_table["columns"] if col["name"] == "id")
        self.assertTrue(id_column["primary_key"])

        # Test specific table inspection
        result = tool.execute(
            database_type="sqlite",
            connection_string=str(self.db_path),
            table_name="posts",
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["table_count"], 1)
        self.assertIn("posts", result["tables"])
        self.assertNotIn("users", result["tables"])

        # Test with sample data
        result = tool.execute(
            database_type="sqlite",
            connection_string=str(self.db_path),
            table_name="users",
            include_data_sample=True,
        )
        self.assertTrue(result["success"])
        users_table = result["tables"]["users"]
        self.assertIn("sample_data", users_table)
        self.assertTrue(len(users_table["sample_data"]) > 0)
        self.assertIn("name", users_table["sample_data"][0])

        # Test nonexistent database
        result = tool.execute(
            database_type="sqlite",
            connection_string="/nonexistent/database.db",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingDatabaseFile")

    def test_database_migration_tool(self):
        """Test DatabaseMigrationTool."""
        tool = DatabaseMigrationTool()
        migrations_dir = Path(self.test_dir) / "migrations"

        # Test create migration
        result = tool.execute(
            action="create",
            migration_name="add_user_profile",
            migration_content="ALTER TABLE users ADD COLUMN profile TEXT;",
            migrations_dir=str(migrations_dir),
        )
        self.assertTrue(result["success"])
        self.assertIn("migration_file", result)
        self.assertIn("add_user_profile", result["filename"])

        # Verify migration file was created
        migration_file = Path(result["migration_file"])
        self.assertTrue(migration_file.exists())
        content = migration_file.read_text()
        self.assertIn("ALTER TABLE users ADD COLUMN profile TEXT;", content)

        # Test create migration without content (template)
        result = tool.execute(
            action="create",
            migration_name="another_migration",
            migrations_dir=str(migrations_dir),
        )
        self.assertTrue(result["success"])
        self.assertIn("-- Migration: another_migration", result["content"])

        # Test list migrations
        result = tool.execute(
            action="list",
            migrations_dir=str(migrations_dir),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["total_migrations"], 2)
        self.assertTrue(len(result["migrations"]) == 2)

        migration_names = [m["name"] for m in result["migrations"]]
        self.assertIn("add_user_profile", migration_names)
        self.assertIn("another_migration", migration_names)

        # Test migration status (before execution)
        result = tool.execute(
            action="status",
            database_type="sqlite",
            connection_string=str(self.db_path),
            migrations_dir=str(migrations_dir),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["executed_count"], 0)
        self.assertEqual(result["pending_count"], 2)

        # Test execute migrations
        result = tool.execute(
            action="execute",
            database_type="sqlite",
            connection_string=str(self.db_path),
            migrations_dir=str(migrations_dir),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["executed_migrations"], 1)  # Only the valid one

        # Test migration status (after execution)
        result = tool.execute(
            action="status",
            database_type="sqlite",
            connection_string=str(self.db_path),
            migrations_dir=str(migrations_dir),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["executed_count"], 1)
        self.assertEqual(
            result["pending_count"], 1
        )  # The template one is still pending

        # Verify the migration was actually applied
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        self.assertIn("profile", columns)
        conn.close()

        # Test invalid action
        result = tool.execute(action="invalid_action")
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "InvalidAction")

        # Test missing migration name for create
        result = tool.execute(
            action="create",
            migrations_dir=str(migrations_dir),
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingParameter")

    def test_tools_integration(self):
        """Test that database tools work together properly."""
        connector_tool = DatabaseConnectorTool()
        query_tool = QueryExecutorTool()
        schema_tool = DatabaseSchemaTool()

        # Connect to database
        connect_result = connector_tool.execute(
            database_type="sqlite",
            connection_string=str(self.db_path),
            test_connection=True,
        )
        self.assertTrue(connect_result["success"])

        # Inspect schema
        schema_result = schema_tool.execute(
            database_type="sqlite",
            connection_string=str(self.db_path),
        )
        self.assertTrue(schema_result["success"])
        initial_table_count = schema_result["table_count"]

        # Execute a query to create a new table
        create_result = query_tool.execute(
            query="CREATE TABLE test_integration (id INTEGER PRIMARY KEY, data TEXT)",
            database_type="sqlite",
            connection_string=str(self.db_path),
            safe_mode=False,
        )
        self.assertTrue(create_result["success"])

        # Verify new table exists
        schema_result = schema_tool.execute(
            database_type="sqlite",
            connection_string=str(self.db_path),
        )
        self.assertTrue(schema_result["success"])
        self.assertEqual(schema_result["table_count"], initial_table_count + 1)
        self.assertIn("test_integration", schema_result["tables"])

        # Insert data
        insert_result = query_tool.execute(
            query="INSERT INTO test_integration (data) VALUES ('test data')",
            database_type="sqlite",
            connection_string=str(self.db_path),
            safe_mode=False,
        )
        self.assertTrue(insert_result["success"])

        # Query the data back
        select_result = query_tool.execute(
            query="SELECT * FROM test_integration",
            database_type="sqlite",
            connection_string=str(self.db_path),
        )
        self.assertTrue(select_result["success"])
        self.assertEqual(len(select_result["data"]), 1)
        self.assertEqual(select_result["data"][0]["data"], "test data")


class TestDatabaseToolsWithoutDependencies(unittest.TestCase):
    """Test Database tools behavior when dependencies are missing."""

    def test_postgresql_without_psycopg2(self):
        """Test PostgreSQL tools gracefully handle missing psycopg2."""
        query_tool = QueryExecutorTool()
        schema_tool = DatabaseSchemaTool()

        # Test query execution
        result = query_tool.execute(
            query="SELECT 1",
            database_type="postgresql",
            host="localhost",
            username="test",
            password="test",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingDependency")
        self.assertIn("psycopg2", result["error"])

        # Test schema inspection
        result = schema_tool.execute(
            database_type="postgresql",
            host="localhost",
            username="test",
            password="test",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingDependency")

    def test_mysql_without_connector(self):
        """Test MySQL tools gracefully handle missing mysql-connector."""
        query_tool = QueryExecutorTool()
        schema_tool = DatabaseSchemaTool()

        # Test query execution
        result = query_tool.execute(
            query="SELECT 1",
            database_type="mysql",
            host="localhost",
            username="test",
            password="test",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingDependency")
        self.assertIn("mysql-connector", result["error"])

        # Test schema inspection
        result = schema_tool.execute(
            database_type="mysql",
            host="localhost",
            username="test",
            password="test",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingDependency")

    def test_unsupported_database_type(self):
        """Test tools handle unsupported database types."""
        tools = [
            DatabaseConnectorTool(),
            QueryExecutorTool(),
            DatabaseSchemaTool(),
        ]

        for tool in tools:
            if isinstance(tool, QueryExecutorTool):
                result = tool.execute(
                    query="SELECT 1",
                    database_type="unsupported_db",
                )
            else:
                result = tool.execute(database_type="unsupported_db")

            self.assertFalse(result["success"])
            self.assertEqual(result["error_type"], "UnsupportedDatabaseType")


class TestDatabaseToolsSQLiteEdgeCases(unittest.TestCase):
    """Test SQLite-specific edge cases."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_empty_database(self):
        """Test tools with empty SQLite database."""
        empty_db = Path(self.test_dir) / "empty.db"

        # Create empty database
        conn = sqlite3.connect(str(empty_db))
        conn.close()

        connector_tool = DatabaseConnectorTool()
        schema_tool = DatabaseSchemaTool()

        # Test connection to empty database
        result = connector_tool.execute(
            database_type="sqlite",
            connection_string=str(empty_db),
        )
        self.assertTrue(result["success"])
        self.assertEqual(len(result["tables"]), 0)

        # Test schema inspection of empty database
        result = schema_tool.execute(
            database_type="sqlite",
            connection_string=str(empty_db),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["table_count"], 0)
        self.assertEqual(len(result["tables"]), 0)

    def test_corrupted_database(self):
        """Test tools with corrupted SQLite database."""
        corrupted_db = Path(self.test_dir) / "corrupted.db"

        # Create a file that's not a valid SQLite database
        corrupted_db.write_text("This is not a SQLite database")

        connector_tool = DatabaseConnectorTool()

        result = connector_tool.execute(
            database_type="sqlite",
            connection_string=str(corrupted_db),
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "SQLiteError")

    def test_no_database_files_in_directory(self):
        """Test auto-detection when no database files exist."""
        os.chdir(self.test_dir)

        query_tool = QueryExecutorTool()
        result = query_tool.execute(
            query="SELECT 1",
            database_type="sqlite",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingDatabaseFile")


if __name__ == "__main__":
    unittest.main()
