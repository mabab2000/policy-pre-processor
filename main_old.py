import os
import re
import json
from uuid import UUID
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment from .env in project root
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

app = FastAPI()


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
            model="gpt-3.5-turbo",
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
        return {'project_id': project_id, 'labels': {}}

    labels = extract_labels(document_content)

    return {'project_id': project_id, 'labels': labels}
import os
import re
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import UUID
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment from add.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'add.env'))

DATABASE_URL = os.getenv('DATABASE_URL')

app = FastAPI()


class DocumentRequest(BaseModel):
    document_id: UUID


def parse_values_from_text(text: str):
    try:
        obj = json.loads(text)
    except Exception:
        obj = None

    def extract_from_obj(o, key):
        if isinstance(o, dict):
            if key in o:
                return o[key]
            for v in o.values():
                r = extract_from_obj(v, key)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for item in o:
                r = extract_from_obj(item, key)
                if r is not None:
                    return r
        return None

    bales = None
    ists = None

    if obj is not None:
        bales = extract_from_obj(obj, 'bales')
        ists = extract_from_obj(obj, 'ists')
    else:
        m = re.search(r'"?bales"?\s*[:=]\s*("[^"]+"|\d+\.?\d*)', text, re.IGNORECASE)
        if m:
            bales = m.group(1).strip('"')
        m2 = re.search(r'"?ists"?\s*[:=]\s*("[^"]+"|\d+\.?\d*)', text, re.IGNORECASE)
        if m2:
            ists = m2.group(1).strip('"')
import os
import re
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import UUID
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment: default .env (if present), then add.env in the project dir
load_dotenv()  # load .env from cwd if present
add_env = os.path.join(os.path.dirname(__file__), 'add.env')
if os.path.exists(add_env):
    load_dotenv(dotenv_path=add_env, override=True)

DATABASE_URL = os.getenv('DATABASE_URL')

app = FastAPI()


class DocumentRequest(BaseModel):
    document_id: UUID


def parse_values_from_text(text: str):
    try:
        obj = json.loads(text)
    except Exception:
        obj = None

    def extract_from_obj(o, key):
        if isinstance(o, dict):
            if key in o:
                return o[key]
            for v in o.values():
                r = extract_from_obj(v, key)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for item in o:
                r = extract_from_obj(item, key)
                if r is not None:
                    return r
        return None

    bales = None
    ists = None

    if obj is not None:
        bales = extract_from_obj(obj, 'bales')
        ists = extract_from_obj(obj, 'ists')
    else:
        m = re.search(r'"?bales"?\s*[:=]\s*("[^"]+"|\d+\.?\d*)', text, re.IGNORECASE)
        if m:
            bales = m.group(1).strip('"')
        m2 = re.search(r'"?ists"?\s*[:=]\s*("[^"]+"|\d+\.?\d*)', text, re.IGNORECASE)
        if m2:
            ists = m2.group(1).strip('"')
import os
import re
import json
from fastapi import FastAPI, HTTPException
import os
import re
import json
from uuid import UUID
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment from .env in project root
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

app = FastAPI()


class DocumentRequest(BaseModel):
    document_id: UUID


def extract_labels(text: str):
    # Try JSON first and flatten structure into key -> value
    def flatten(o, parent=''):
        items = {}
        if isinstance(o, dict):
            for k, v in o.items():
                new_key = f"{parent}.{k}" if parent else k
                items.update(flatten(v, new_key))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                new_key = f"{parent}[{i}]" if parent else f"[{i}]"
                items.update(flatten(v, new_key))
        else:
            items[parent] = o
        return items

    try:
        obj = json.loads(text)
    except Exception:
        obj = None

    labels = {}
    if obj is not None:
        if isinstance(obj, dict):
            labels = flatten(obj)
        elif isinstance(obj, list):
            # flatten each item with index prefix
            for i, item in enumerate(obj):
                part = flatten(item, f'[{i}]')
                labels.update(part)
    else:
        # Fallback: regex find key:value pairs like key: "value" or key = 123
        pattern = re.compile(r'"?([A-Za-z0-9_\- ]+)"?\s*[:=]\s*("([^"]*)"|([0-9]+(?:\.[0-9]+)?))')
        found = {}
        for m in pattern.finditer(text):
            key = m.group(1).strip()
            val = m.group(3) if m.group(3) is not None else m.group(4)
            # convert numeric strings
            if val is None:
                continue
            if re.fullmatch(r'\d+', val):
                val_converted = int(val)
            else:
                try:
                    val_converted = float(val)
                except Exception:
                    val_converted = val
            if key in found:
                # append to list
                if isinstance(found[key], list):
                    found[key].append(val_converted)
                else:
                    found[key] = [found[key], val_converted]
            else:
                found[key] = val_converted
        labels = found

    # Normalize values: single-item lists -> single value
    for k, v in list(labels.items()):
        if isinstance(v, list) and len(v) == 1:
            labels[k] = v[0]

    return labels


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
        return {'project_id': project_id, 'labels': {}}

    labels = extract_labels(document_content)

    return {'project_id': project_id, 'labels': labels}

