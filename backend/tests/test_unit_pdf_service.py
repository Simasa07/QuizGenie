"""
Unit tests for app/services/pdf_service.py. extract_text_from_pdf itself
needs a real file on disk (covered by the document-upload integration test
instead); these test the pure text-processing functions in isolation.
"""
from app.services.pdf_service import clean_text, chunk_text, select_relevant_chunks


class TestCleanText:
    def test_strips_whitespace_and_drops_empty_lines(self):
        raw = "  Hello world  \n\n\n   \nSecond line   \n"
        assert clean_text(raw) == "Hello world\nSecond line"

    def test_empty_input_gives_empty_output(self):
        assert clean_text("") == ""
        assert clean_text("   \n\n   ") == ""


class TestChunkText:
    def test_short_text_is_a_single_chunk(self):
        text = "line one\nline two\nline three"
        chunks = chunk_text(text, max_chars=3000)
        assert len(chunks) == 1
        assert "line one" in chunks[0]
        assert "line three" in chunks[0]

    def test_long_text_is_split_into_multiple_chunks(self):
        # Each line is ~50 chars; with max_chars=100 this must split.
        lines = [f"this is line number {i} of the document" for i in range(20)]
        text = "\n".join(lines)
        chunks = chunk_text(text, max_chars=100)
        assert len(chunks) > 1
        # nothing from the original text should be lost across the split
        rejoined = "\n".join(chunks)
        for line in lines:
            assert line in rejoined

    def test_no_chunk_exceeds_the_limit_by_much(self):
        lines = [f"line {i}" * 5 for i in range(50)]
        text = "\n".join(lines)
        chunks = chunk_text(text, max_chars=200)
        # a single line can push a chunk slightly over, but not by a lot
        for chunk in chunks:
            assert len(chunk) <= 250

    def test_empty_text_gives_no_chunks(self):
        assert chunk_text("") == []


class TestSelectRelevantChunks:
    def test_returns_first_n_chunks(self):
        chunks = [f"chunk-{i}" for i in range(10)]
        selected = select_relevant_chunks(chunks, max_chunks=3)
        assert selected == ["chunk-0", "chunk-1", "chunk-2"]

    def test_fewer_chunks_than_max_returns_all(self):
        chunks = ["only-one"]
        assert select_relevant_chunks(chunks, max_chunks=6) == ["only-one"]

    def test_empty_input_gives_empty_output(self):
        assert select_relevant_chunks([], max_chunks=6) == []
