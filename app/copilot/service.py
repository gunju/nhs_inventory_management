"""
Copilot service — orchestrates context building, RAG retrieval, LLM call, response parsing.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.copilot.context_builder import ContextBuilder
from app.copilot.llm_client import LLMMessage, get_llm_client
from app.copilot.prompts import get_prompt
from app.core.logging import log
from app.models.rag import (
    ConversationMessage, ConversationSession, CopilotAnswer,
)
from app.schemas.copilot import CopilotResponse, EvidenceRef


class CopilotService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = get_llm_client()

    def chat(
        self,
        question: str,
        trust_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
    ) -> CopilotResponse:
        # Get or create session
        session = self._get_or_create_session(session_id, trust_id, user_id)

        # Build grounded context from DB
        ctx_builder = ContextBuilder(self.db, trust_id)
        context, evidence_refs = ctx_builder.build_for_question(question)

        # RAG retrieval from documents
        rag_context, rag_evidence = self._rag_retrieve(question, trust_id)
        if rag_context:
            context = context + "\n\n" + rag_context
            evidence_refs.extend(rag_evidence)

        # Build prompt
        system_prompt = get_prompt("chat_qa_system_prompt")
        user_prompt = get_prompt("grounded_inventory_answer_prompt").format(
            context=context,
            question=question,
        )

        # LLM call
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        llm_response = self.llm.chat(messages)

        # Parse structured response
        parsed = self._parse_llm_response(llm_response.content, evidence_refs)

        # Persist
        self._save_turn(session, question, parsed, llm_response.model)

        return CopilotResponse(
            session_id=session.id,
            answer=parsed["answer"],
            confidence=parsed.get("confidence"),
            reason_codes=parsed.get("reason_codes", []),
            evidence=[EvidenceRef(**e) for e in parsed.get("evidence", evidence_refs)],
            recommended_actions=parsed.get("recommended_actions", []),
            follow_up_questions=parsed.get("follow_up_questions", []),
            grounded=parsed.get("grounded", True),
        )

    def _get_or_create_session(
        self, session_id: uuid.UUID | None, trust_id: uuid.UUID, user_id: uuid.UUID | None
    ) -> ConversationSession:
        if session_id:
            session = self.db.get(ConversationSession, session_id)
            if session and session.trust_id == trust_id:
                return session

        session = ConversationSession(trust_id=trust_id, user_id=user_id)
        self.db.add(session)
        self.db.flush()
        return session

    def _rag_retrieve(
        self, question: str, trust_id: uuid.UUID
    ) -> tuple[str, list[dict]]:
        """Retrieve relevant document chunks via vector similarity."""
        try:
            from app.rag.retriever import DocumentRetriever
            retriever = DocumentRetriever(self.db)
            chunks = retriever.retrieve(question, trust_id=trust_id)
            if not chunks:
                return "", []
            context_parts = [
                f"[DOC: {c.source_filename}]\n{c.content}"
                for c in chunks
            ]
            evidence = [
                {
                    "type": "document",
                    "id": str(c.chunk_id),
                    "label": c.source_filename,
                    "value": None,
                }
                for c in chunks
            ]
            return "## Policy / SOP Documents\n" + "\n---\n".join(context_parts), evidence
        except Exception as exc:
            log.warning("rag_retrieval_failed", error=str(exc))
            return "", []

    def _parse_llm_response(self, raw: str, fallback_evidence: list[dict]) -> dict:
        """Parse JSON from LLM, fall back gracefully if malformed."""
        try:
            # strip markdown code fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:])
                if clean.endswith("```"):
                    clean = clean[:-3]
            parsed = json.loads(clean)
            # Ensure evidence has proper shape
            if "evidence" not in parsed or not parsed["evidence"]:
                parsed["evidence"] = fallback_evidence
            return parsed
        except json.JSONDecodeError:
            log.warning("llm_response_not_json", raw_preview=raw[:200])
            return {
                "answer": raw,
                "confidence": None,
                "reason_codes": ["UNSTRUCTURED_RESPONSE"],
                "evidence": fallback_evidence,
                "recommended_actions": [],
                "follow_up_questions": [],
                "grounded": False,
            }

    def _save_turn(
        self, session: ConversationSession, question: str, parsed: dict, model_version: str
    ) -> None:
        # Count existing messages for sequence
        seq = len(session.messages) if session.messages else 0

        user_msg = ConversationMessage(
            session_id=session.id,
            role="user",
            content=question,
            sequence=seq,
        )
        self.db.add(user_msg)
        self.db.flush()

        assistant_msg = ConversationMessage(
            session_id=session.id,
            role="assistant",
            content=parsed["answer"],
            sequence=seq + 1,
        )
        self.db.add(assistant_msg)
        self.db.flush()

        answer = CopilotAnswer(
            session_id=session.id,
            message_id=assistant_msg.id,
            trust_id=session.trust_id,
            answer=parsed["answer"],
            confidence=parsed.get("confidence"),
            reason_codes=json.dumps(parsed.get("reason_codes", [])),
            evidence_json=json.dumps(parsed.get("evidence", [])),
            recommended_actions=json.dumps(parsed.get("recommended_actions", [])),
            follow_up_questions=json.dumps(parsed.get("follow_up_questions", [])),
            model_version=model_version,
            grounded=parsed.get("grounded", True),
        )
        self.db.add(answer)
        self.db.commit()
