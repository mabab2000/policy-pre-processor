import os
import re
import json
from uuid import UUID
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from openai import OpenAI

# Load environment from .env in project root
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DocumentRequest(BaseModel):
    document_id: UUID


def extract_labels(text: str):
    """Extract labels and values from document text using OpenAI."""
    
    if not client:
        # Fallback to simple JSON parsing if OpenAI is not available
        try:
            return json.loads(text)
        except Exception:
            return {}
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Extract all labels and their corresponding values from the given text. Return the result as a flat JSON object where each key is a label and each value is the corresponding value. Convert numeric strings to appropriate number types. If the text is already JSON, flatten nested structures using dot notation for keys (e.g., 'policy.name', 'user.details.age'). Only return valid JSON, no explanations."
                },
                {
                    "role": "user", 
                    "content": text
                }
            ],
            temperature=0,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse the JSON response
        try:
            labels = json.loads(result)
            return labels if isinstance(labels, dict) else {}
        except json.JSONDecodeError:
            # If OpenAI response is not valid JSON, try to extract manually
            return {}
            
    except Exception as e:
        # Fallback to simple parsing if OpenAI fails
        try:
            return json.loads(text)
        except Exception:
            return {}


def extract_key_points(text: str):
    """Extract key points from document text using OpenAI."""
    
    if not client:
        return []
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Extract the key points from the given document text. Return the result as a JSON array of strings, where each string is a concise key point or important information from the document. Focus on the most important facts, decisions, dates, amounts, and actionable items. Only return valid JSON array, no explanations."
                },
                {
                    "role": "user", 
                    "content": text
                }
            ],
            temperature=0,
            max_tokens=800
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse the JSON response
        try:
            key_points = json.loads(result)
            return key_points if isinstance(key_points, list) else []
        except json.JSONDecodeError:
            return []
            
    except Exception as e:
        return []


@app.post('/document')
def get_document(req: DocumentRequest):
    document_id = req.document_id
    document_id_param = str(document_id)

    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail='DATABASE_URL not configured')

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            'SELECT project_id, document_content FROM documents WHERE id = %s LIMIT 1',
            (document_id_param,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Database query failed: {e}')

    if not row:
        raise HTTPException(status_code=404, detail='Document not found')

    project_id = row.get('project_id')
    document_content = row.get('document_content')

    if document_content is None:
        return {'project_id': project_id, 'labels': {}, 'key_points': []}

    labels = extract_labels(document_content)
    key_points = extract_key_points(document_content)
    
    # Filter out labels with null/None values
    filtered_labels = {k: v for k, v in labels.items() if v is not None and v != "" and v != "null"}
    
    # Prepare result data
    result_data = json.dumps({
        'labels': filtered_labels,
        'key_points': key_points
    })
    
    # Save processed data to document_processed_data table
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Create table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_processed_data (
                id SERIAL PRIMARY KEY,
                document_id UUID NOT NULL,
                result TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Upsert processed data to avoid duplicates per document_id
        cur.execute(
            '''
            INSERT INTO document_processed_data (document_id, result)
            VALUES (%s, %s)
            ON CONFLICT (document_id)
            DO UPDATE SET
                result = EXCLUDED.result,
                created_at = CURRENT_TIMESTAMP
            ''',
            (document_id_param, result_data)
        )

        # Mark document as analysed
        cur.execute(
            'UPDATE documents SET analysed = TRUE WHERE id = %s',
            (document_id_param,)
        )
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        # Log error but don't fail the request
        print(f'Warning: Failed to save processed data: {e}')

    return {
        'status': 'success',
        'message': 'Document processed successfully',
        'project_id': project_id,
        'labels': filtered_labels,
        'key_points': key_points
    }


def generate_summary(result_text: str):
    """Generate a designed document summary using OpenAI gpt-4o-mini."""
    
    if not client:
        return "OpenAI client not configured"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional document summarizer. Create a well-structured, concise document summary based on the provided extracted data (labels and key points). Format the summary in clear paragraphs with proper markdown formatting. Include a brief executive overview followed by detailed sections. Make it professional and easy to understand."
                },
                {
                    "role": "user", 
                    "content": f"Based on the following extracted document data, create a professional summary:\n\n{result_text}"
                }
            ],
            temperature=0.5,
            max_tokens=2000
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
            
    except Exception as e:
        return f"Error generating summary: {str(e)}"


class SummaryRequest(BaseModel):
    document_id: UUID


@app.post('/summary')
def get_summary(req: SummaryRequest):
    document_id = req.document_id
    document_id_param = str(document_id)
    
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail='DATABASE_URL not configured')
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Fetch the most recent processed data for this document
        cur.execute(
            'SELECT id, result FROM document_processed_data WHERE document_id = %s ORDER BY created_at DESC LIMIT 1',
            (document_id_param,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Database query failed: {e}')
    
    if not row:
        raise HTTPException(status_code=404, detail='No processed data found for this document')
    
    result_text = row.get('result')
    
    # Generate summary from the processed data
    summary = generate_summary(result_text)
    
    return {
        'status': 'success',
        'message': 'Summary generated successfully',
        'document_id': document_id_param,
        'summary': summary
    }