-- Migration: Update document_processed_data table
-- Date: 2026-01-20
-- Changes:
--   1. Change id column from SERIAL to UUID
--   2. Add project_id column
--   3. Add unique constraint on document_id for upsert operations

-- Step 1: Add project_id column
ALTER TABLE document_processed_data 
ADD COLUMN IF NOT EXISTS project_id UUID;

-- Step 2: Drop the old id column and recreate as UUID
-- First, drop the constraint and column
ALTER TABLE document_processed_data 
DROP CONSTRAINT IF EXISTS document_processed_data_pkey;

ALTER TABLE document_processed_data 
DROP COLUMN IF EXISTS id;

-- Step 3: Add new UUID id column with default
ALTER TABLE document_processed_data 
ADD COLUMN id UUID PRIMARY KEY DEFAULT gen_random_uuid();

-- Step 4: Add unique constraint on document_id for ON CONFLICT clause
ALTER TABLE document_processed_data 
ADD CONSTRAINT document_processed_data_document_id_key UNIQUE (document_id);

-- Step 5: Create index on project_id for better query performance
CREATE INDEX IF NOT EXISTS idx_document_processed_data_project_id 
ON document_processed_data(project_id);

-- Migration complete
