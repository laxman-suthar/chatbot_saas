import os
from django.conf import settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)
from langchain.schema import Document as LCDocument
from knowledge_base.models import DocumentChunk, Document
from django.db.models import F
from pgvector.django import L2Distance
import logging

logger = logging.getLogger(__name__)

# Initialize embeddings globally
embeddings = GoogleGenerativeAIEmbeddings(
    model=settings.GOOGLE_EMBEDDING_MODEL,
    google_api_key=settings.GOOGLE_API_KEY
)


def get_document_loader(file_path: str, file_type: str):
    """Get appropriate loader based on file type"""
    if file_type == 'application/pdf':
        return PyPDFLoader(file_path)
    elif file_type == 'text/plain':
        return TextLoader(file_path)
    elif 'word' in file_type or 'document' in file_type:
        return Docx2txtLoader(file_path)
    else:
        return TextLoader(file_path)


def ingest_document(website_id: str, file_path: str, file_type: str, doc_id: str) -> int:
    """
    Load file → chunk → embed → store in pgvector
    Returns chunk count
    """
    logger.info(f"⚙️  Ingesting document {doc_id} from file: {file_path}")
    
    try:
        loader = get_document_loader(file_path, file_type)
        pages = loader.load()
    except Exception as e:
        logger.error(f"❌ Failed to load document: {e}")
        raise

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = splitter.split_documents(pages)

    doc = Document.objects.get(id=doc_id)
    chunk_count = 0

    for chunk in chunks:
        try:
            # Get embedding from Google Gemini
            embedding_vector = embeddings.embed_query(chunk.page_content)

            # Store in pgvector
            DocumentChunk.objects.create(
                document=doc,
                website_id=website_id,
                content=chunk.page_content,
                embedding=embedding_vector,
                metadata={
                    'doc_id': str(doc_id),
                    'website_id': str(website_id),
                    'source': file_path,
                    'page': chunk.metadata.get('page', 0),
                }
            )
            chunk_count += 1
        except Exception as e:
            logger.error(f"❌ Failed to store chunk: {e}")
            continue

    logger.info(f"✅ Ingested {chunk_count} chunks for document {doc_id}")
    return chunk_count


def ingest_text(website_id: str, text_content: str, doc_id: str) -> int:
    """
    Paste text → chunk → embed → store in pgvector
    Returns chunk count
    """
    logger.info(f"⚙️  Ingesting text document {doc_id}")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )

    raw_doc = LCDocument(
        page_content=text_content,
        metadata={
            'website_id': str(website_id),
            'doc_id': str(doc_id),
            'source': 'text_paste',
        }
    )
    chunks = splitter.split_documents([raw_doc])

    doc = Document.objects.get(id=doc_id)
    chunk_count = 0

    for chunk in chunks:
        try:
            # Get embedding from Google Gemini
            embedding_vector = embeddings.embed_query(chunk.page_content)

            # Store in pgvector
            DocumentChunk.objects.create(
                document=doc,
                website_id=website_id,
                content=chunk.page_content,
                embedding=embedding_vector,
                metadata={
                    'doc_id': str(doc_id),
                    'website_id': str(website_id),
                    'source': 'text_paste',
                }
            )
            chunk_count += 1
        except Exception as e:
            logger.error(f"❌ Failed to store chunk: {e}")
            continue

    logger.info(f"✅ Ingested {chunk_count} chunks for text document {doc_id}")
    return chunk_count


def delete_document_chunks(website_id: str, doc_id: str) -> int:
    """Delete all chunks for a document"""
    logger.info(f"🗑️  Deleting chunks for document {doc_id}")
    
    deleted_count, _ = DocumentChunk.objects.filter(
        website_id=website_id,
        document_id=doc_id
    ).delete()
    
    logger.info(f"✅ Deleted {deleted_count} chunks")
    return deleted_count


def query_knowledge_base(website_id: str, question: str, limit: int = 4) -> list:
    """
    Query pgvector for similar chunks
    Returns list of chunks with distance
    """
    logger.info(f"🔍 Querying knowledge base for website {website_id}")
    
    try:
        # Get embedding for question
        query_embedding = embeddings.embed_query(question)
    except Exception as e:
        logger.error(f"❌ Failed to get embedding: {e}")
        raise

    try:
        # Search pgvector with RLS automatically enforced
        chunks = DocumentChunk.objects.filter(
            website_id=website_id
        ).annotate(
            distance=L2Distance('embedding', query_embedding)
        ).order_by('distance')[:limit]

        results = [
            {
                'id': str(chunk.id),
                'content': chunk.content,
                'distance': float(chunk.distance),
                'document_id': str(chunk.document_id),
                'metadata': chunk.metadata,
            }
            for chunk in chunks
        ]

        logger.info(f"✅ Found {len(results)} similar chunks")
        return results

    except Exception as e:
        logger.error(f"❌ Failed to query knowledge base: {e}")
        raise


def get_context_for_llm(website_id: str, question: str, limit: int = 4) -> str:
    """
    Get context string for LLM (joined chunk contents)
    """
    results = query_knowledge_base(website_id, question, limit)
    
    if not results:
        return "No relevant documents found in knowledge base."
    
    context = "\n\n".join([f"Document: {r['content']}" for r in results])
    return context