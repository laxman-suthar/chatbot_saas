import os
from django.conf import settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)
from langchain.schema import Document as LCDocument
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from chat.utils import FlattenedGemini


# initialize embeddings globally
embeddings = GoogleGenerativeAIEmbeddings(
    model=settings.GOOGLE_EMBEDDING_MODEL,
    google_api_key=settings.GOOGLE_API_KEY
)


def get_vectorstore(website_id: str) -> Chroma:
    return Chroma(
        collection_name=f"website_{str(website_id).replace('-', '_')}",
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR
    )


def get_document_loader(file_path: str, file_type: str):
    if file_type == 'application/pdf':
        return PyPDFLoader(file_path)
    elif file_type == 'text/plain':
        return TextLoader(file_path)
    elif 'word' in file_type or 'document' in file_type:
        return Docx2txtLoader(file_path)
    else:
        return TextLoader(file_path)


def ingest_document(website_id: str, file_path: str, file_type: str, doc_id: str) -> int:
    loader = get_document_loader(file_path, file_type)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = splitter.split_documents(pages)

    for chunk in chunks:
        chunk.metadata['website_id'] = str(website_id)
        chunk.metadata['doc_id'] = str(doc_id)

    vectorstore = get_vectorstore(website_id)
    vectorstore.add_documents(chunks)
    vectorstore.persist()

    return len(chunks)


def ingest_text(website_id: str, text_content: str, doc_id: str) -> int:
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
        }
    )
    chunks = splitter.split_documents([raw_doc])

    for chunk in chunks:
        chunk.metadata['website_id'] = str(website_id)
        chunk.metadata['doc_id'] = str(doc_id)

    vectorstore = get_vectorstore(website_id)
    vectorstore.add_documents(chunks)
    vectorstore.persist()

    return len(chunks)


def delete_document_chunks(website_id: str, doc_id: str):
    vectorstore = get_vectorstore(website_id)
    vectorstore._collection.delete(
        where={'doc_id': str(doc_id)}
    )
    vectorstore.persist()


def query_knowledge_base(website_id: str, question: str, chat_history: list = None) -> str:
    if chat_history is None:
        chat_history = []

    vectorstore = get_vectorstore(website_id)

    if vectorstore._collection.count() == 0:
        return "No knowledge base documents found."

    prompt_template = """You are a helpful customer support assistant.
Use the following context to answer the question.
If you don't know the answer, say so honestly.

Context:
{context}

Question: {question}

Answer:"""

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=['context', 'question']
    )

    llm = FlattenedGemini(
        model=settings.GOOGLE_TEXT_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.3,
        convert_system_message_to_human=True
    )

    retriever = vectorstore.as_retriever(
        search_type='similarity',
        search_kwargs={'k': 4}
    )

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=retriever,
        chain_type_kwargs={'prompt': prompt},
        return_source_documents=False
    )

    result = chain.invoke({'query': question})

    if isinstance(result, dict):
        answer = result.get('result', '')
    else:
        answer = str(result)

    if isinstance(answer, list):
        answer = ' '.join(str(item) for item in answer)

    return str(answer).strip()