from app.database import SessionLocal
from app.main import agentic_stack


def test_agentic_stack_contract() -> None:
    with SessionLocal() as db:
        result = agentic_stack(query='automation mcp', limit=3, db=db)

    assert isinstance(result, dict)
    assert 'checked_at' in result
    assert 'technologies' in result
    assert 'agents' in result
    assert 'rag_hits' in result

    technologies = result['technologies']
    assert 'llm' in technologies
    assert 'rag' in technologies
    assert 'mcp' in technologies
    assert 'awx' in technologies
    assert 'langgraph' in technologies
    assert technologies['rag']['documents_indexed'] >= 0


def test_agentic_stack_respects_rag_limit() -> None:
    with SessionLocal() as db:
        result = agentic_stack(query='automation', limit=2, db=db)

    assert result['rag_query'] == 'automation'
    assert isinstance(result['rag_hits'], list)
    assert len(result['rag_hits']) <= 2

    for hit in result['rag_hits']:
        assert 'path' in hit
        assert 'score' in hit
        assert 'snippet' in hit
