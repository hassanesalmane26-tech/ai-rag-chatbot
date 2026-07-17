from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os

from app.core.config import settings
from app.database.database import Base, engine
from app.database import models

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database.models import ChatMessage

from fastapi import UploadFile, File
import shutil
from pathlib import Path

from app.rag.vectorstore import vectorstore
from app.rag.search import search_documents
from app.rag.document_manager import (
    save_document,
    rebuild_index,
    list_documents,
    delete_document,
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    root_path="/api",
)

Base.metadata.create_all(bind=engine)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {
        "status": "online",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "Bienvenue sur AI RAG Chatbot 🚀",
    }


@app.post("/chat")
def chat(data: ChatRequest):
    db = SessionLocal()

    try:
        history = (
            db.query(ChatMessage)
            .order_by(ChatMessage.id.desc())
            .limit(10)
            .all()
        )

        history.reverse()

        conversation = []

        for msg in history:
            conversation.append({
                "role": "user",
                "content": msg.user_message,
            })

            conversation.append({
                "role": "assistant",
                "content": msg.ai_response,
            })

        conversation.append({
            "role": "user",
            "content": data.message,
        })

        results = search_documents(data.message)

        relevant_docs = [
            doc
            for doc, score in results
        ]

        context = "\n\n".join(
            doc.page_content
            for doc in relevant_docs
        )

        sources = list(
            {
                doc.metadata.get("source", "Inconnu")
                for doc in relevant_docs
            }
        )

        conversation.insert(
            0,
            {
                "role": "system",
                "content": f"""
        Tu es Nova.

        Réponds en priorité avec les informations présentes dans ce contexte.

        Contexte :

        {context}

        Si le contexte ne contient pas la réponse, indique-le clairement puis réponds avec tes connaissances générales.
        """,
            },
        )

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=conversation,
        )

        ai_reply = response.output_text

        db.add(
            ChatMessage(
                user_message=data.message,
                ai_response=ai_reply,
            )
        )

        db.commit()

        return {
            "reply": ai_reply,
            "sources": sources,
        }
    finally:
        db.close()


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    save_document(file)

    chunks = rebuild_index()

    return {
        "message": "Document indexé avec succès",
        "chunks": chunks,
    }

@app.get("/documents")
def get_documents():
    return {
        "documents": list_documents()
    }


@app.delete("/documents/{filename}")
def remove_document(filename: str):
    delete_document(filename)

    return {
        "message": f"{filename} supprimé avec succès."
    }
