"""
Integration tests for app/api/documents.py: real PDF upload, duplicate
filename blocking, and - most importantly - that one user can never see
or touch another user's documents.
"""


class TestUpload:
    def test_upload_a_real_pdf_extracts_text_and_marks_processed(self, client, signup, upload_document):
        user = signup()
        doc = upload_document(user["headers"])
        assert doc["filename"] == "sample.pdf"
        assert doc["status"] == "processed"

    def test_non_pdf_content_type_is_rejected(self, client, signup):
        user = signup()
        r = client.post(
            "/documents/upload",
            headers=user["headers"],
            files={"file": ("notes.txt", b"just some text", "text/plain")},
        )
        assert r.status_code == 400

    def test_upload_without_a_token_is_rejected(self, client, sample_pdf_bytes):
        r = client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert r.status_code == 401

    def test_same_filename_twice_for_the_same_user_is_blocked(self, client, signup, upload_document):
        user = signup()
        upload_document(user["headers"], filename="networking.pdf")
        r = client.post(
            "/documents/upload",
            headers=user["headers"],
            files={"file": ("networking.pdf", b"different bytes but same name", "application/pdf")},
        )
        assert r.status_code == 409

    def test_same_filename_is_fine_for_two_different_users(self, client, signup, upload_document):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        upload_document(alice["headers"], filename="networking.pdf")
        # Bob uploading a file with the same name should NOT be blocked -
        # the duplicate check is scoped per-user, not global.
        doc = upload_document(bob["headers"], filename="networking.pdf")
        assert doc["filename"] == "networking.pdf"


class TestListMine:
    def test_lists_only_the_caller_s_own_documents(self, client, signup, upload_document):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        upload_document(alice["headers"], filename="alice_doc.pdf")
        upload_document(bob["headers"], filename="bob_doc.pdf")

        r = client.get("/documents/mine", headers=alice["headers"])
        filenames = [d["filename"] for d in r.json()]
        assert filenames == ["alice_doc.pdf"]


class TestGetByIdAndOwnership:
    def test_owner_can_fetch_their_own_document(self, client, signup, upload_document):
        user = signup()
        doc = upload_document(user["headers"])
        r = client.get(f"/documents/{doc['id']}", headers=user["headers"])
        assert r.status_code == 200
        assert r.json()["id"] == doc["id"]

    def test_other_user_cannot_fetch_it_by_id(self, client, signup, upload_document):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        doc = upload_document(alice["headers"], filename="alice_private.pdf")

        r = client.get(f"/documents/{doc['id']}", headers=bob["headers"])
        assert r.status_code == 404  # not 403 - never confirm it exists at all

    def test_nonexistent_document_id_gives_404(self, client, signup):
        user = signup()
        r = client.get("/documents/999999", headers=user["headers"])
        assert r.status_code == 404
