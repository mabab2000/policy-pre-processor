#!/usr/bin/env python3
"""Database migration script for policy-pre-processor."""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not configured")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("Creating document_processed_data table...")
    
    # Create table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_processed_data (
            id SERIAL PRIMARY KEY,
            document_id UUID NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index on document_id for faster queries
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_processed_data_document_id 
        ON document_processed_data(document_id)
    """)
    
    # Create index on created_at for sorting
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_processed_data_created_at 
        ON document_processed_data(created_at DESC)
    """)
    
    conn.commit()
    print("✓ Migration completed successfully!")
    print("✓ Table 'document_processed_data' created")
    print("✓ Indexes created for optimized queries")
    
    cur.close()
    conn.close()
    
except psycopg2.Error as e:
    print(f"Database error: {e}")
    exit(1)
except Exception as e:
    print(f"Error: {e}")
    exit(1)
